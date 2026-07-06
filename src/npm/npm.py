from __future__ import annotations

import json
from pathlib import Path

# third-party imports
from depsight.core.plugins.base import BasePlugin
from depsight.core.plugins.dependency import Dependency


class NpmPlugin(BasePlugin):
    """Third-party npm plugin for depsight."""

    def __init__(self) -> None:
        self.dependencies: list[Dependency] = []

    @property
    def name(self) -> str:
        return "npm"

    @property
    def dependency_files(self) -> tuple[str, ...]:
        return ("package-lock.json",)

    @property
    def default_file(self) -> str:
        return self.dependency_files[0]

    def collect(self, project_dir: str | Path, file: str | None = None) -> None:
        """Parse dependencies from a ``package-lock.json`` file."""
        file = file or self.default_file
        lockfile = Path(project_dir) / file

        self.dependencies = []

        if not lockfile.is_file():
            return

        with lockfile.open(encoding="utf-8") as fh:
            data = json.load(fh)

        lockfile_path = str(lockfile)

        packages = data.get("packages")
        if packages:
            self._collect_from_packages(packages, lockfile_path)
        else:
            self._collect_from_dependencies(
                data.get("dependencies", {}), lockfile_path
            )

    def _collect_from_packages(
        self, packages: dict[str, dict], lockfile_path: str
    ) -> None:
        """Collect dependencies from the ``packages`` field (npm v2/v3)."""
        root = packages.get("", {})
        direct = root.get("dependencies", {})
        dev_direct = root.get("devDependencies", {})
        constraints = {**direct, **dev_direct}

        seen: set[str] = set()
        for key, meta in packages.items():
            # Skip the root entry and anything not installed under node_modules.
            if key == "" or "node_modules/" not in key:
                continue

            name = key.split("node_modules/")[-1]
            version = meta.get("version")
            if not version or name in seen:
                continue
            seen.add(name)

            is_dev = bool(meta.get("dev")) or name in dev_direct
            self.dependencies.append(
                Dependency(
                    name=name,
                    version=version,
                    constraint=constraints.get(name),
                    tool_name=self.name,
                    registry=meta.get("resolved"),
                    file=lockfile_path,
                    category="dev" if is_dev else "prod",
                    is_transitive=name not in direct and name not in dev_direct,
                )
            )

    def _collect_from_dependencies(
        self, dependencies: dict[str, dict], lockfile_path: str
    ) -> None:
        """Collect dependencies from the nested ``dependencies`` field (npm v1)."""
        seen: set[str] = set()

        def walk(deps: dict[str, dict], is_transitive: bool) -> None:
            for name, meta in deps.items():
                version = meta.get("version")
                if version and name not in seen:
                    seen.add(name)
                    self.dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            tool_name=self.name,
                            registry=meta.get("resolved"),
                            file=lockfile_path,
                            category="dev" if meta.get("dev") else "prod",
                            is_transitive=is_transitive,
                        )
                    )
                nested = meta.get("dependencies")
                if nested:
                    walk(nested, True)

        walk(dependencies, False)

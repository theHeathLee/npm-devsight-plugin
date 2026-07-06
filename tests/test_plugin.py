from __future__ import annotations

import csv
from pathlib import Path

# third-party imports
from depsight.core.plugins.base import BasePlugin

from npm.npm import NpmPlugin

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestCollect:
    """Verify collect() populates dependencies correctly."""

    def test_plugin_implements_base_plugin_contract(self):
        plugin = NpmPlugin()

        assert isinstance(plugin, BasePlugin)
        assert isinstance(plugin.default_file, str)
        assert plugin.default_file.strip()
        assert Path(plugin.default_file).name == plugin.default_file
        assert plugin.default_file not in {".", ".."}
        assert plugin.default_file in plugin.dependency_files

        assert plugin.name == "npm"
        assert plugin.default_file == "package-lock.json"
        assert "package-lock.json" in plugin.dependency_files

    def test_collect_dependency_details(self):
        plugin = NpmPlugin()

        plugin.collect(FIXTURES_DIR, file="package-lock.json")

        express, lodash = plugin.dependencies
        assert (express.name, express.version, express.tool_name) == (
            "express",
            "4.18.2",
            "npm",
        )
        assert express.category == "prod"
        assert express.is_transitive is False

        assert (lodash.name, lodash.version, lodash.tool_name) == (
            "lodash",
            "4.17.21",
            "npm",
        )
        assert lodash.category == "dev"
        assert lodash.is_transitive is False


class TestExport:
    """Verify export() writes a valid CSV."""

    def test_export_csv(self, tmp_path: Path):
        plugin = NpmPlugin()

        plugin.collect(FIXTURES_DIR, file="package-lock.json")
        csv_path = plugin.export(FIXTURES_DIR, tmp_path)
        assert csv_path.exists()

        assert csv_path.name == "npm_fixtures.csv"

        with csv_path.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))

        assert len(rows) == 2
        assert rows[0]["name"] == "express"
        assert rows[1]["name"] == "lodash"

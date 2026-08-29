"""projects.json のロードと配布先解決の検証。"""
import json
import tempfile
import unittest
from pathlib import Path

from deployer.config import ConfigError, load_projects, resolve_target


class LoadProjectsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)

    def _write_projects(self, data):
        (self.repo / "projects.json").write_text(json.dumps(data), encoding="utf-8")

    def test_expands_tilde(self):
        self._write_projects({"portfolio": "~/github/portfolio"})
        projects = load_projects(self.repo)
        self.assertEqual(projects["portfolio"], Path.home() / "github" / "portfolio")

    def test_resolves_relative_path_from_repo_root(self):
        self._write_projects({"portfolio": "sibling/portfolio"})
        projects = load_projects(self.repo)
        self.assertEqual(projects["portfolio"], self.repo / "sibling" / "portfolio")

    def test_keeps_absolute_path_as_is(self):
        self._write_projects({"portfolio": "/tmp/portfolio"})
        projects = load_projects(self.repo)
        self.assertEqual(projects["portfolio"], Path("/tmp/portfolio"))

    def test_missing_file_suggests_copying_the_example(self):
        with self.assertRaises(ConfigError) as ctx:
            load_projects(self.repo)
        self.assertIn("cp projects.example.json projects.json", str(ctx.exception))

    def test_malformed_json_raises(self):
        (self.repo / "projects.json").write_text("{ not json", encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_projects(self.repo)

    def test_non_string_value_raises(self):
        self._write_projects({"portfolio": 123})
        with self.assertRaises(ConfigError):
            load_projects(self.repo)


class ResolveTargetTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_returns_path_for_existing_directory(self):
        self.assertEqual(resolve_target({"portfolio": self.root}, "portfolio"), self.root)

    def test_unknown_name_lists_available_names(self):
        projects = {"portfolio": self.root, "blog": self.root}
        with self.assertRaises(ConfigError) as ctx:
            resolve_target(projects, "unknown")
        message = str(ctx.exception)
        self.assertIn("blog", message)
        self.assertIn("portfolio", message)

    def test_missing_target_raises(self):
        with self.assertRaises(ConfigError):
            resolve_target({"portfolio": self.root / "nope"}, "portfolio")

    def test_target_that_is_a_file_raises(self):
        path = self.root / "afile"
        path.write_text("x", encoding="utf-8")
        with self.assertRaises(ConfigError):
            resolve_target({"portfolio": path}, "portfolio")


if __name__ == "__main__":
    unittest.main()

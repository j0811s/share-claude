"""build_plan + apply_plan のエンドツーエンド検証。"""
import io
import json
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from deployer.apply import apply_plan
from deployer.plan import build_plan


def _write(path, content, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _snapshot(root):
    """配布先の全ファイルを {相対パス: 内容} で写し取る。"""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class SmokeTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.repo = root / "repo"
        self.target = root / "target"
        self.target.mkdir(parents=True)
        self._build_fixture()

    def _build_fixture(self):
        _write(self.repo / "common/skills/.gitkeep", "")
        _write(self.repo / "common/skills/shared/SKILL.md", "# shared skill")
        _write(self.repo / "common/hooks/common-hook.sh", "#!/bin/sh\necho common\n", executable=True)
        _write(
            self.repo / "common/settings.json",
            json.dumps({"model": "opus", "permissions": {"allow": ["Bash(git status)"]}}),
        )
        _write(self.repo / "project/portfolio/skills/only-project/SKILL.md", "# project skill")
        _write(self.repo / "project/portfolio/rules/rule.md", "# rule")
        _write(
            self.repo / "project/portfolio/settings.json",
            json.dumps({"permissions": {"allow": ["Bash(npm test)"]}}),
        )
        _write(self.repo / "project/portfolio/CLAUDE.md", "# portfolio\n")

        # 配布先にもともとあるもの
        _write(self.target / ".claude/settings.local.json", '{"local": true}')
        _write(self.target / ".claude/skills/stale/OLD.md", "消えるべき")

    def _deploy(self, dry_run=False):
        plan = build_plan(self.repo, "portfolio", self.target)
        with redirect_stdout(io.StringIO()) as out:
            changed = apply_plan(plan, self.target, dry_run=dry_run)
        return changed, out.getvalue()

    def test_expected_tree_exists_after_deploy(self):
        self._deploy()
        for rel in [
            ".claude/skills/shared/SKILL.md",
            ".claude/skills/only-project/SKILL.md",
            ".claude/hooks/common-hook.sh",
            ".claude/rules/rule.md",
            ".claude/settings.json",
            "CLAUDE.md",
        ]:
            self.assertTrue((self.target / rel).is_file(), rel)

    def test_hook_script_keeps_executable_bit(self):
        self._deploy()
        mode = (self.target / ".claude/hooks/common-hook.sh").stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)

    def test_settings_local_json_survives(self):
        self._deploy()
        local = self.target / ".claude/settings.local.json"
        self.assertTrue(local.is_file())
        self.assertEqual(json.loads(local.read_text(encoding="utf-8")), {"local": True})

    def test_settings_json_is_merged_from_both_sides(self):
        self._deploy()
        settings = json.loads((self.target / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["permissions"]["allow"], ["Bash(git status)", "Bash(npm test)"])
        self.assertEqual(settings["model"], "opus")

    def test_excluded_names_never_reach_the_target(self):
        self._deploy()
        names = {path.name for path in self.target.rglob("*")}
        self.assertNotIn(".gitkeep", names)
        self.assertNotIn(".DS_Store", names)

    def test_stale_file_and_its_empty_directory_are_removed(self):
        self._deploy()
        self.assertFalse((self.target / ".claude/skills/stale/OLD.md").exists())
        self.assertFalse((self.target / ".claude/skills/stale").exists())

    def test_dry_run_changes_nothing(self):
        before = _snapshot(self.target)
        changed, output = self._deploy(dry_run=True)
        self.assertEqual(_snapshot(self.target), before)
        self.assertGreater(changed, 0)
        self.assertIn("dry-run", output)

    def test_second_deploy_reports_no_changes(self):
        self._deploy()
        changed, _ = self._deploy()
        self.assertEqual(changed, 0)


if __name__ == "__main__":
    unittest.main()

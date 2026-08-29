"""build_plan の検証。ファイルシステムのフィクスチャを一時ディレクトリに作る。"""
import json
import tempfile
import unittest
from pathlib import Path

from deployer.plan import build_plan


def _write(path, content):
    """親ディレクトリごとファイルを作り、その Path を返す。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class BuildPlanTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.repo = root / "repo"
        self.target = root / "target"
        self.target.mkdir(parents=True)

    def _plan(self):
        return build_plan(self.repo, "portfolio", self.target)

    def _dsts(self, kind=None):
        return {a.dst for a in self._plan() if kind is None or a.kind == kind}

    def test_excluded_names_are_not_copied(self):
        _write(self.repo / "common/skills/.gitkeep", "")
        _write(self.repo / "common/skills/.DS_Store", "")
        _write(self.repo / "common/skills/real.md", "x")
        copied = {a.dst.name for a in self._plan() if a.kind == "copy"}
        self.assertEqual(copied, {"real.md"})

    def test_project_file_wins_over_common(self):
        _write(self.repo / "common/skills/a.md", "common")
        _write(self.repo / "project/portfolio/skills/a.md", "project")
        copies = [a for a in self._plan() if a.kind == "copy"]
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0].src.read_text(encoding="utf-8"), "project")

    def test_stale_target_file_is_deleted(self):
        _write(self.repo / "common/skills/a.md", "x")
        stale = _write(self.target / ".claude/skills/old.md", "old")
        self.assertIn(stale, self._dsts("delete"))

    def test_unmanaged_directory_is_untouched(self):
        # repo に project/portfolio/rules/ が無いので rules は未管理
        _write(self.repo / "common/skills/a.md", "x")
        keeper = _write(self.target / ".claude/rules/hand-written.md", "keep")
        self.assertNotIn(keeper, self._dsts())

    def test_source_dir_with_only_gitkeep_does_not_delete_target_files(self):
        # .gitkeep しか無いディレクトリを管理下と見なすと、配布0件のまま
        # 同期が走って配布先を全削除してしまう
        _write(self.repo / "common/skills/.gitkeep", "")
        keeper = _write(self.target / ".claude/skills/hand-written.md", "keep")
        self.assertNotIn(keeper, self._dsts("delete"))

    def test_identical_file_is_unchanged(self):
        _write(self.repo / "common/skills/a.md", "same")
        _write(self.target / ".claude/skills/a.md", "same")
        statuses = {a.status for a in self._plan() if a.kind == "copy"}
        self.assertEqual(statuses, {"unchanged"})

    def test_differing_file_is_update(self):
        _write(self.repo / "common/skills/a.md", "new")
        _write(self.target / ".claude/skills/a.md", "old")
        statuses = {a.status for a in self._plan() if a.kind == "copy"}
        self.assertEqual(statuses, {"update"})

    def test_settings_local_is_not_deleted(self):
        _write(self.repo / "common/skills/a.md", "x")
        local = _write(self.target / ".claude/settings.local.json", "{}")
        self.assertNotIn(local, self._dsts("delete"))

    def test_nested_skill_structure_is_preserved(self):
        _write(self.repo / "common/skills/my-skill/SKILL.md", "x")
        self.assertIn(self.target / ".claude/skills/my-skill/SKILL.md", self._dsts("copy"))

    def test_directory_left_empty_is_deleted(self):
        _write(self.repo / "common/skills/a.md", "x")
        _write(self.target / ".claude/skills/dead/old.md", "old")
        deletes = self._dsts("delete")
        self.assertIn(self.target / ".claude/skills/dead/old.md", deletes)
        self.assertIn(self.target / ".claude/skills/dead", deletes)

    def test_settings_are_merged_into_one_write_action(self):
        _write(
            self.repo / "common/settings.json",
            json.dumps({"model": "opus", "permissions": {"allow": ["a"]}}),
        )
        _write(
            self.repo / "project/portfolio/settings.json",
            json.dumps({"permissions": {"allow": ["b"]}}),
        )
        writes = [a for a in self._plan() if a.kind == "write"]
        self.assertEqual(len(writes), 1)
        merged = json.loads(writes[0].content)
        self.assertEqual(merged["permissions"]["allow"], ["a", "b"])
        self.assertEqual(merged["model"], "opus")

    def test_single_sided_settings_is_written_as_is(self):
        _write(self.repo / "common/settings.json", json.dumps({"model": "opus"}))
        writes = [a for a in self._plan() if a.kind == "write"]
        self.assertEqual(json.loads(writes[0].content), {"model": "opus"})

    def test_no_settings_source_produces_no_write(self):
        _write(self.repo / "common/skills/a.md", "x")
        self.assertEqual([a for a in self._plan() if a.kind == "write"], [])

    def test_project_claude_md_is_copied_to_target_root(self):
        _write(self.repo / "project/portfolio/CLAUDE.md", "# rules")
        self.assertIn(self.target / "CLAUDE.md", self._dsts("copy"))

    def test_build_plan_does_not_write_anything(self):
        _write(self.repo / "common/skills/a.md", "x")
        before = sorted(p.name for p in self.target.rglob("*"))
        self._plan()
        self.assertEqual(sorted(p.name for p in self.target.rglob("*")), before)

    def test_non_utf8_settings_raises_config_error(self):
        from deployer.config import ConfigError

        path = self.repo / "common/settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes('{"model": "オパス"}'.encode("shift_jis"))
        with self.assertRaises(ConfigError):
            self._plan()


if __name__ == "__main__":
    unittest.main()

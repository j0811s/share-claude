"""build_plan の検証。ファイルシステムのフィクスチャを一時ディレクトリに作る。"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from deployer.config import ConfigError
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

    def test_symlinked_mirror_root_raises_when_managed(self):
        # common/skills にファイルがあるので .claude/skills は管理下。
        # それがシンボリックリンクだと rglob がリンクの先を辿ってしまい、
        # 配布先の外にある実ファイルを削除しかねない（C1）。
        _write(self.repo / "common/skills/a.md", "x")
        victim = self.target.parent / "victim"
        victim.mkdir(parents=True)
        (self.target / ".claude").mkdir(parents=True)
        os.symlink(str(victim), str(self.target / ".claude/skills"))
        with self.assertRaises(ConfigError):
            self._plan()

    def test_symlinked_mirror_root_with_nothing_to_distribute_is_noop(self):
        # 配布するファイルが無ければ管理下ではないので、シンボリックリンクの
        # ままでも例外を出さず、単に何もしない（ガードが管理下判定の後にある証拠）。
        victim = self.target.parent / "victim"
        victim.mkdir(parents=True)
        (self.target / ".claude").mkdir(parents=True)
        os.symlink(str(victim), str(self.target / ".claude/skills"))
        self.assertEqual(self._plan(), [])

    def test_symlinked_claude_dir_raises_and_preserves_linked_contents(self):
        # .claude 自体がシンボリックリンクだと、.claude/skills は symlink 経由で
        # 実体解決すると通常のディレクトリに見えてしまい、狭い is_symlink()
        # チェックでは検知できない（C3）。rglob がリンク先を辿って配布先の
        # 外にある既存ファイルを削除しかねない。
        _write(self.repo / "common/skills/a.md", "x")
        global_dir = self.target.parent / "global"
        victim = _write(global_dir / "skills/my-skill/SKILL.md", "precious")
        os.symlink(str(global_dir), str(self.target / ".claude"))
        with self.assertRaises(ConfigError):
            self._plan()
        self.assertTrue(victim.exists())
        self.assertEqual(victim.read_text(encoding="utf-8"), "precious")

    def test_symlinked_claude_dir_with_nothing_to_distribute_is_noop(self):
        # 配布するファイルが無ければ管理下ではないので、.claude がシンボリック
        # リンクのままでも例外を出さず、単に何もしない（ガードが管理下判定の
        # 後にある証拠）。
        global_dir = self.target.parent / "global"
        global_dir.mkdir(parents=True)
        os.symlink(str(global_dir), str(self.target / ".claude"))
        self.assertEqual(self._plan(), [])

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

    def test_unreadable_target_settings_is_treated_as_update(self):
        _write(self.repo / "common/settings.json", json.dumps({"model": "opus"}))
        dst = self.target / ".claude/settings.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes('{"model": "オパス"}'.encode("shift_jis"))
        writes = [a for a in self._plan() if a.kind == "write"]
        self.assertEqual(writes[0].status, "update")

    def test_delete_actions_are_ordered_for_rmdir(self):
        _write(self.repo / "common/skills/live.md", "x")
        _write(self.target / ".claude/skills/dead/a/b/deep.md", "old")
        _write(self.target / ".claude/skills/dead/top.md", "old")
        deletes = [a.dst for a in self._plan() if a.kind == "delete"]
        skills = self.target / ".claude/skills"
        # ファイルは全てディレクトリより先に削除される
        last_file = max(deletes.index(p) for p in [
            skills / "dead/a/b/deep.md", skills / "dead/top.md"
        ])
        first_dir = min(deletes.index(p) for p in [
            skills / "dead/a/b", skills / "dead/a", skills / "dead"
        ])
        self.assertLess(last_file, first_dir)
        # ディレクトリは深い順（rmdir は空でないと失敗する）
        self.assertLess(deletes.index(skills / "dead/a/b"), deletes.index(skills / "dead/a"))
        self.assertLess(deletes.index(skills / "dead/a"), deletes.index(skills / "dead"))


if __name__ == "__main__":
    unittest.main()

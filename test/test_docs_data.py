"""docs_data の検証。ファイルシステムのフィクスチャを一時ディレクトリに作る。"""
import json
import tempfile
import unittest
from pathlib import Path

from deployer.docs_data import (
    build_docs_data,
    export_hooks,
    export_permissions,
    export_skills,
    parse_frontmatter,
    script_description,
)


def _write(path, content):
    """親ディレクトリごとファイルを作り、その Path を返す。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class DocsDataTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        self.repo.mkdir(parents=True)

    def test_parse_frontmatter_strips_quotes(self):
        fm = parse_frontmatter('---\nname: x\nargument-hint: "[n]"\n---\n# body')
        self.assertEqual(fm, {"name": "x", "argument-hint": "[n]"})

    def test_parse_frontmatter_without_block(self):
        self.assertEqual(parse_frontmatter("# no fm"), {})

    def test_project_skill_overrides_common(self):
        _write(self.repo / "common/skills/foo/SKILL.md", "---\nname: foo\ndescription: c\n---\n")
        _write(self.repo / "project/p/skills/foo/SKILL.md", "---\nname: foo\ndescription: p\n---\n")
        skills = export_skills(self.repo, "p")
        self.assertEqual([(s["name"], s["origin"], s["description"]) for s in skills], [("foo", "project", "p")])
        self.assertEqual(skills[0]["path"], "project/p/skills/foo/SKILL.md")

    def test_skill_without_frontmatter_uses_dir_name(self):
        _write(self.repo / "common/skills/bar/SKILL.md", "# bar")
        s = export_skills(self.repo, "p")[0]
        self.assertEqual((s["name"], s["description"], s["manualOnly"]), ("bar", None, False))

    def test_manual_only_and_argument_hint(self):
        _write(self.repo / "project/p/skills/z/SKILL.md",
               '---\nname: z\ndescription: d\nargument-hint: "[n]"\ndisable-model-invocation: true\n---\n')
        s = export_skills(self.repo, "p")[0]
        self.assertEqual((s["argumentHint"], s["manualOnly"]), ("[n]", True))

    def test_references_are_not_listed_as_skills(self):
        _write(self.repo / "common/skills/a/SKILL.md", "---\nname: a\n---\n")
        _write(self.repo / "common/skills/a/references/x.md", "x")
        self.assertEqual([s["name"] for s in export_skills(self.repo, "p")], ["a"])

    def test_script_description(self):
        self.assertEqual(script_description("#!/bin/sh\n# 説明: .env を守る\ninput=$(cat)\n"), ".env を守る")
        self.assertIsNone(script_description("#!/bin/sh\ninput=$(cat)\n"))

    def test_hooks_resolve_script_and_origin(self):
        _write(self.repo / "common/hooks/a.sh", "#!/bin/sh\n# 説明: A\n")
        _write(self.repo / "common/settings.json", json.dumps({"hooks": {"PreToolUse": [
            {"matcher": "Edit", "hooks": [{"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/a.sh"}]}]}}))
        _write(self.repo / "project/p/settings.json", json.dumps({"hooks": {"PostToolUse": [
            {"hooks": [{"type": "command", "command": "npx foo"}]}]}}))
        hooks = export_hooks(self.repo, "p")
        self.assertEqual(hooks[0], {"event": "PreToolUse", "matcher": "Edit",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/a.sh", "origin": "common",
            "script": {"path": "common/hooks/a.sh", "description": "A"}})
        self.assertEqual((hooks[1]["matcher"], hooks[1]["script"], hooks[1]["origin"]), (None, None, "project"))

    def test_permissions_origin(self):
        _write(self.repo / "common/settings.json", json.dumps({"permissions": {"deny": ["X"]}}))
        _write(self.repo / "project/p/settings.json", json.dumps({"permissions": {"deny": ["X", "Y"], "allow": ["Z"]}}))
        self.assertEqual(export_permissions(self.repo, "p"), {
            "deny": [{"rule": "X", "origin": "common"}, {"rule": "Y", "origin": "project"}],
            "ask": [], "allow": [{"rule": "Z", "origin": "project"}]})

    def test_no_settings_anywhere(self):
        (self.repo / "project/p").mkdir(parents=True)
        self.assertEqual(export_hooks(self.repo, "p"), [])
        self.assertEqual(export_permissions(self.repo, "p"), {"deny": [], "ask": [], "allow": []})

    def test_build_docs_data_lists_projects_and_files(self):
        _write(self.repo / "project/b/CLAUDE.md", "x")
        _write(self.repo / "project/a/rules/.gitkeep", "")
        data = build_docs_data(self.repo)
        self.assertEqual([p["name"] for p in data["projects"]], ["a", "b"])
        self.assertEqual((data["projects"][0]["claudeMd"], data["projects"][0]["rules"]), (None, []))
        self.assertEqual(data["projects"][1]["claudeMd"], "project/b/CLAUDE.md")


if __name__ == "__main__":
    unittest.main()

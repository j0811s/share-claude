"""docs_data の検証。ファイルシステムのフィクスチャを一時ディレクトリに作る。"""
import tempfile
import unittest
from pathlib import Path

from deployer.docs_data import export_skills, parse_frontmatter


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


if __name__ == "__main__":
    unittest.main()

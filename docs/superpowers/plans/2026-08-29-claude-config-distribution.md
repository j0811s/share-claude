# CLAUDE設定配信システム 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** share-claude リポジトリから各プロジェクトへ Claude Code の設定（skills / hooks / rules / settings.json / CLAUDE.md）を配布する Push 型 CLI を実装する。

**Architecture:** `common/` と `project/<name>/` を重ね合わせ（project が優先）、配布アクション列を組み立てる `build_plan()` と、それを実行する `apply_plan()` に分離する。dry-run は plan を表示するだけで、別のコードパスを持たない。settings.json はキー形状ごとのポリシーでマージする。

**Tech Stack:** Python 3.9.6（`/usr/bin/python3`）、標準ライブラリのみ、`unittest`

**Spec:** `docs/superpowers/specs/2026-08-28-claude-config-distribution-design.md`

## Global Constraints

- 実行環境は `/usr/bin/python3`（Python 3.9.6）。**標準ライブラリのみ**を使う（`json`, `pathlib`, `shutil`, `filecmp`, `argparse`, `unittest`, `tempfile`, `collections`）
- 外部依存（jq / pytest / PyYAML 等）を追加してはならない
- `tomllib` は Python 3.11+ のため使用不可。設定ファイルは JSON
- 型アノテーションを書く場合は Python 3.9 互換にすること（`list[str]` 等の組み込みジェネリクスは実行時に失敗する）。本計画のコードはアノテーションを使わない
- テストは `unittest`。リポジトリルートで `python3 -m unittest discover test` で実行する
- ユーザ向けメッセージ・コード内コメントは日本語で書く
- **`<target>/.claude/` 全体をミラーしてはならない。** 所有するのは `.claude/skills/`, `.claude/hooks/`, `.claude/rules/` の3ディレクトリと、`.claude/settings.json`, `CLAUDE.md` の2ファイルのみ
- 除外ファイル名: `.gitkeep`, `.DS_Store`
- 配布先パスに `Path.resolve()` を**使わない**。macOS では `/var` が `/private/var` へのシンボリックリンクであり、`tempfile` が返すパスと解決後のパスが一致せずテストが壊れるため
- 同名ファイルは常に `project/<name>/` 側が勝つ

## 設計書からの変更点

設計書では argparse を `bin/deploy.py` に置くとしていたが、`bin/` は Python パッケージではないためテストからの import が脆くなる。`main()` は `deployer/cli.py` に置き、`bin/deploy.py` は `sys.path` 追加と `main()` 呼び出しだけの薄いシムとする。設計書の意図（ロジックを `deployer/` に集約し、エントリポイントは薄く）は保たれている。

## File Structure

| ファイル | 責務 |
|---|---|
| `deployer/__init__.py` | 空。パッケージ宣言のみ |
| `deployer/merge.py` | settings.json のマージポリシー。dict を受け取り dict を返す純粋関数。ファイル I/O を持たない |
| `deployer/config.py` | `projects.json` のロード・パス解決・配布先の検証。`ConfigError` を定義 |
| `deployer/plan.py` | `build_plan()`。ソース群と配布先を読んでアクション列を返す。**書き込みは行わない** |
| `deployer/apply.py` | `apply_plan()`。アクション列を表示し、dry-run でなければ実行する |
| `deployer/cli.py` | `main()`。argparse と各モジュールの結線、エラーの exit code 変換 |
| `bin/deploy.py` | 実行可能シム。`sys.path` 追加 → `main()` |
| `test/test_merge.py` | マージポリシーの単体テスト |
| `test/test_config.py` | projects.json 解決の単体テスト |
| `test/test_plan.py` | plan 構築の単体テスト（一時ディレクトリのフィクスチャを使用） |
| `test/test_smoke.py` | エンドツーエンド検証と CLI の結線検証 |
| `.gitignore` | `projects.json` を除外 |
| `projects.example.json` | 配布先マッピングの雛形 |
| `README.md` | セットアップと使い方 |
| `CLAUDE.md` | このリポジトリを編集する際の指示 |

---

### Task 1: settings.json のマージポリシー

**Files:**
- Create: `deployer/__init__.py`
- Create: `deployer/merge.py`
- Test: `test/test_merge.py`

**Interfaces:**
- Consumes: なし（最初のタスク）
- Produces: `deployer.merge.merge_settings(base, overlay)` → 新しい dict。`base`（common）に `overlay`（project）を重ねる。引数はいずれも変更しない

- [ ] **Step 1: `deployer/__init__.py` を空ファイルとして作成する**

```bash
mkdir -p deployer test
touch deployer/__init__.py
```

- [ ] **Step 2: 失敗するテストを書く**

`test/test_merge.py`:

```python
"""settings.json のマージポリシーの検証。"""
import unittest

from deployer.merge import merge_settings


class MergeSettingsTest(unittest.TestCase):
    def test_permissions_allow_is_concatenated_base_first(self):
        base = {"permissions": {"allow": ["Bash(git status)", "Bash(git diff)"]}}
        overlay = {"permissions": {"allow": ["Bash(npm test)"]}}
        merged = merge_settings(base, overlay)
        self.assertEqual(
            merged["permissions"]["allow"],
            ["Bash(git status)", "Bash(git diff)", "Bash(npm test)"],
        )

    def test_permissions_allow_duplicates_are_removed_keeping_order(self):
        base = {"permissions": {"allow": ["a", "b"]}}
        overlay = {"permissions": {"allow": ["b", "c"]}}
        merged = merge_settings(base, overlay)
        self.assertEqual(merged["permissions"]["allow"], ["a", "b", "c"])

    def test_hooks_are_concatenated_with_base_entries_first(self):
        base = {"hooks": {"SessionStart": [{"matcher": "*", "hooks": [{"type": "command", "command": "base.sh"}]}]}}
        overlay = {"hooks": {"SessionStart": [{"matcher": "*", "hooks": [{"type": "command", "command": "project.sh"}]}]}}
        merged = merge_settings(base, overlay)
        commands = [entry["hooks"][0]["command"] for entry in merged["hooks"]["SessionStart"]]
        self.assertEqual(commands, ["base.sh", "project.sh"])

    def test_identical_hook_entries_are_deduplicated(self):
        entry = {"matcher": "*", "hooks": [{"type": "command", "command": "same.sh"}]}
        merged = merge_settings({"hooks": {"SessionStart": [entry]}}, {"hooks": {"SessionStart": [dict(entry)]}})
        self.assertEqual(len(merged["hooks"]["SessionStart"]), 1)

    def test_nested_dict_is_merged_recursively_with_overlay_winning(self):
        base = {"enabledPlugins": {"a@x": True, "b@x": False}}
        overlay = {"enabledPlugins": {"b@x": True, "c@x": True}}
        merged = merge_settings(base, overlay)
        self.assertEqual(merged["enabledPlugins"], {"a@x": True, "b@x": True, "c@x": True})

    def test_scalar_is_overridden_by_overlay(self):
        merged = merge_settings({"model": "sonnet"}, {"model": "opus"})
        self.assertEqual(merged["model"], "opus")

    def test_unknown_list_is_replaced_by_overlay(self):
        merged = merge_settings({"somethingNew": [1, 2, 3]}, {"somethingNew": [9]})
        self.assertEqual(merged["somethingNew"], [9])

    def test_key_present_only_in_base_survives(self):
        merged = merge_settings({"statusLine": {"type": "command"}}, {"model": "opus"})
        self.assertEqual(merged["statusLine"], {"type": "command"})

    def test_key_present_only_in_overlay_is_added(self):
        merged = merge_settings({"model": "opus"}, {"tui": "fullscreen"})
        self.assertEqual(merged["tui"], "fullscreen")

    def test_empty_side_returns_the_other_side(self):
        self.assertEqual(merge_settings({}, {"a": 1}), {"a": 1})
        self.assertEqual(merge_settings({"a": 1}, {}), {"a": 1})

    def test_type_mismatch_lets_overlay_win(self):
        merged = merge_settings({"x": {"nested": 1}}, {"x": [1, 2]})
        self.assertEqual(merged["x"], [1, 2])

    def test_inputs_are_not_mutated(self):
        base = {"permissions": {"allow": ["a"]}}
        overlay = {"permissions": {"allow": ["b"]}}
        merge_settings(base, overlay)
        self.assertEqual(base, {"permissions": {"allow": ["a"]}})
        self.assertEqual(overlay, {"permissions": {"allow": ["b"]}})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: テストを実行して失敗を確認する**

Run: `python3 -m unittest discover test -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deployer.merge'`

- [ ] **Step 4: `deployer/merge.py` を実装する**

```python
"""settings.json のマージポリシー。

素朴な再帰 dict.update() は配列を置換するため、project 側に hooks を1つ
書いただけで common の permissions.allow が全消滅する。それを避けるため、
キーパスの形状ごとにポリシーを分ける。
"""
import json

# リストを連結するキーパス。これ以外のリストは overlay が置換する。
CONCAT_PATHS = frozenset(
    {
        ("permissions", "allow"),
        ("permissions", "deny"),
        ("permissions", "ask"),
    }
)


def merge_settings(base, overlay, _path=()):
    """common(base) に project(overlay) を重ねた設定を返す。引数は変更しない。"""
    if not isinstance(base, dict) or not isinstance(overlay, dict):
        return overlay

    merged = dict(base)
    for key, overlay_value in overlay.items():
        path = _path + (key,)
        if key not in base:
            merged[key] = overlay_value
            continue

        base_value = base[key]
        if (
            _is_concat_path(path)
            and isinstance(base_value, list)
            and isinstance(overlay_value, list)
        ):
            merged[key] = _concat_unique(base_value, overlay_value)
        elif isinstance(base_value, dict) and isinstance(overlay_value, dict):
            merged[key] = merge_settings(base_value, overlay_value, path)
        else:
            merged[key] = overlay_value
    return merged


def _is_concat_path(path):
    """このキーパスがリスト連結の対象かを返す。"""
    if path in CONCAT_PATHS:
        return True
    # hooks.<EventName> は任意のイベント名を取るのでパターンで判定する
    return len(path) == 2 and path[0] == "hooks"


def _concat_unique(base_list, overlay_list):
    """base を先に置いて連結し、完全一致する要素の重複を除く。"""
    merged = []
    seen = set()
    for item in list(base_list) + list(overlay_list):
        key = json.dumps(item, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged
```

- [ ] **Step 5: テストを実行して成功を確認する**

Run: `python3 -m unittest discover test -v`
Expected: PASS — 12 tests OK

- [ ] **Step 6: コミット**

```bash
git add deployer/__init__.py deployer/merge.py test/test_merge.py
git commit -m "feat: settings.json のマージポリシーを実装

キー形状ごとにポリシーを分け、permissions.* と hooks.<Event> は
リスト連結、それ以外は overlay 優先とする。素朴な再帰 update が
配列を置換して common の設定を消す事故を防ぐ。"
```

---

### Task 2: projects.json のロードと配布先の検証

**Files:**
- Create: `deployer/config.py`
- Test: `test/test_config.py`

**Interfaces:**
- Consumes: なし
- Produces:
  - `deployer.config.ConfigError` — ユーザ向けメッセージを持つ例外
  - `deployer.config.load_projects(repo_root)` → `{プロジェクト名: 配布先 Path}`。存在検証はしない
  - `deployer.config.resolve_target(projects, name)` → 検証済みの配布先 `Path`

- [ ] **Step 1: 失敗するテストを書く**

`test/test_config.py`:

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m unittest discover test -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deployer.config'`

- [ ] **Step 3: `deployer/config.py` を実装する**

```python
"""projects.json のロードと配布先の検証。"""
import json
from pathlib import Path


class ConfigError(Exception):
    """設定の不備を、ユーザにそのまま見せられるメッセージ付きで表す。"""


def load_projects(repo_root):
    """projects.json を読み、{プロジェクト名: 配布先 Path} を返す。

    パスは展開・絶対化するだけで、存在の検証は resolve_target が行う。
    """
    path = repo_root / "projects.json"
    if not path.is_file():
        raise ConfigError(
            "projects.json が見つかりません: {}\n"
            "gitignore されているため初回は存在しません。"
            "次のコマンドで作成してください:\n"
            "  cp projects.example.json projects.json".format(path)
        )

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError("projects.json の JSON が不正です: {}".format(exc)) from exc

    if not isinstance(raw, dict):
        raise ConfigError("projects.json はオブジェクトである必要があります")

    projects = {}
    for name, value in raw.items():
        if not isinstance(value, str):
            raise ConfigError(
                "projects.json の '{}' の値は文字列である必要があります".format(name)
            )
        projects[name] = _to_path(repo_root, value)
    return projects


def _to_path(repo_root, raw):
    """~ を展開し、相対パスならリポジトリルート起点で絶対化する。

    Path.resolve() は使わない。macOS では /var が /private/var への
    シンボリックリンクであり、解決するとテストの一時ディレクトリと
    パスが一致しなくなるため。
    """
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path


def resolve_target(projects, name):
    """プロジェクト名を、存在を検証済みの配布先 Path に解決する。"""
    if name not in projects:
        available = ", ".join(sorted(projects)) or "(なし)"
        raise ConfigError(
            "プロジェクト '{}' は projects.json にありません。\n"
            "利用可能: {}".format(name, available)
        )

    target = projects[name]
    if not target.exists():
        raise ConfigError("配布先が存在しません: {}".format(target))
    if not target.is_dir():
        raise ConfigError("配布先がディレクトリではありません: {}".format(target))
    return target
```

- [ ] **Step 4: テストを実行して成功を確認する**

Run: `python3 -m unittest discover test -v`
Expected: PASS — 22 tests OK（Task 1 の 12 件 + 今回の 10 件）

- [ ] **Step 5: コミット**

```bash
git add deployer/config.py test/test_config.py
git commit -m "feat: projects.json のロードと配布先検証を実装

projects.json は gitignore するため、不在時は不正扱いにせず
projects.example.json のコピーを促すメッセージを出す。
macOS の /var シンボリックリンク対策として Path.resolve() は使わない。"
```

---

### Task 3: 配布アクション列の構築

**Files:**
- Create: `deployer/plan.py`
- Test: `test/test_plan.py`

**Interfaces:**
- Consumes: `deployer.config.ConfigError`、`deployer.merge.merge_settings(base, overlay)`
- Produces:
  - `deployer.plan.Action` — `namedtuple("Action", ["kind", "dst", "src", "content", "status"])`
    - `kind`: `"copy"` / `"write"` / `"delete"`
    - `dst`: 配布先の `Path`
    - `src`: `copy` のときソースの `Path`、他は `None`
    - `content`: `write` のとき書き込む文字列、他は `None`
    - `status`: `"new"` / `"update"` / `"unchanged"` / `"delete"`
  - `deployer.plan.EXCLUDED_NAMES` — `frozenset({".gitkeep", ".DS_Store"})`
  - `deployer.plan.build_plan(repo_root, project_name, target)` → `Action` のリスト。**書き込みを一切行わない**

- [ ] **Step 1: 失敗するテストを書く**

`test/test_plan.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m unittest discover test -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deployer.plan'`

- [ ] **Step 3: `deployer/plan.py` を実装する**

```python
"""配布アクション列の構築。ファイルシステムへの書き込みは一切行わない。"""
import filecmp
import json
from collections import namedtuple
from pathlib import Path

from deployer.config import ConfigError
from deployer.merge import merge_settings

Action = namedtuple("Action", ["kind", "dst", "src", "content", "status"])

# 配布先に持ち込みたくないファイル名
EXCLUDED_NAMES = frozenset({".gitkeep", ".DS_Store"})


def build_plan(repo_root, project_name, target):
    """配布に必要な Action のリストを返す。読み取りのみを行う。"""
    actions = []
    for target_rel, source_dirs in _mirror_specs(repo_root, project_name):
        actions.extend(_mirror_actions(target / target_rel, source_dirs))

    settings = _settings_action(repo_root, project_name, target)
    if settings is not None:
        actions.append(settings)

    claude_md = repo_root / "project" / project_name / "CLAUDE.md"
    if claude_md.is_file():
        dst = target / "CLAUDE.md"
        actions.append(Action("copy", dst, claude_md, None, _copy_status(claude_md, dst)))

    return actions


def _mirror_specs(repo_root, project_name):
    """(配布先の相対パス, 重ねるソースディレクトリ) の組を返す。後のソースが勝つ。"""
    common = repo_root / "common"
    project = repo_root / "project" / project_name
    return [
        (Path(".claude/skills"), [common / "skills", project / "skills"]),
        (Path(".claude/hooks"), [common / "hooks", project / "hooks"]),
        (Path(".claude/rules"), [project / "rules"]),
    ]


def _mirror_actions(dst_root, source_dirs):
    """1つのミラー対象ディレクトリについて copy と delete のアクションを組み立てる。"""
    sources = {}
    for source_dir in source_dirs:
        if not source_dir.is_dir():
            continue
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or path.name in EXCLUDED_NAMES:
                continue
            sources[path.relative_to(source_dir)] = path

    # 管理下かどうかはディレクトリの存在ではなく、配布するファイルの有無で決める。
    # ディレクトリの存在で判定すると .gitkeep しか無いディレクトリが管理下と
    # 見なされ、配布0件のまま同期が走って配布先の既存ファイルを全削除する。
    if not sources:
        return []

    actions = []
    for rel in sorted(sources):
        dst = dst_root / rel
        actions.append(Action("copy", dst, sources[rel], None, _copy_status(sources[rel], dst)))
    actions.extend(_stale_actions(dst_root, set(sources)))
    return actions


def _stale_actions(dst_root, placed_rels):
    """配布先にあってソースに無いファイルと、空になるディレクトリの削除を組み立てる。"""
    if not dst_root.is_dir():
        return []

    placed = {dst_root / rel for rel in placed_rels}

    # 残すべきディレクトリ = 配置するファイルの祖先
    kept_dirs = set()
    for path in placed:
        parent = path.parent
        while parent != dst_root:
            kept_dirs.add(parent)
            parent = parent.parent

    actions = [
        Action("delete", path, None, None, "delete")
        for path in sorted(dst_root.rglob("*"))
        if path.is_file() and path not in placed
    ]

    # 深い順に削除する。rmdir は空でないと失敗するため順序が要る
    dead_dirs = [
        path for path in dst_root.rglob("*") if path.is_dir() and path not in kept_dirs
    ]
    dead_dirs.sort(key=lambda path: len(path.parts), reverse=True)
    actions.extend(Action("delete", path, None, None, "delete") for path in dead_dirs)
    return actions


def _settings_action(repo_root, project_name, target):
    """settings.json の write アクションを返す。ソースが無ければ None。"""
    base = _load_json(repo_root / "common" / "settings.json")
    overlay = _load_json(repo_root / "project" / project_name / "settings.json")
    if base is None and overlay is None:
        return None

    if base is None:
        merged = overlay
    elif overlay is None:
        merged = base
    else:
        merged = merge_settings(base, overlay)

    content = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
    dst = target / ".claude" / "settings.json"
    return Action("write", dst, None, content, _write_status(content, dst))


def _load_json(path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError("{} の JSON が不正です: {}".format(path, exc)) from exc


def _copy_status(src, dst):
    if not dst.exists():
        return "new"
    if filecmp.cmp(str(src), str(dst), shallow=False):
        return "unchanged"
    return "update"


def _write_status(content, dst):
    if not dst.is_file():
        return "new"
    if dst.read_text(encoding="utf-8") == content:
        return "unchanged"
    return "update"
```

- [ ] **Step 4: テストを実行して成功を確認する**

Run: `python3 -m unittest discover test -v`
Expected: PASS — 37 tests OK（Task 1・2 の 22 件 + 今回の 15 件）

- [ ] **Step 5: コミット**

```bash
git add deployer/plan.py test/test_plan.py
git commit -m "feat: 配布アクション列の構築を実装

common と project を重ねて copy/write/delete のアクション列を返す。
書き込みは行わないため dry-run は plan の表示だけで済む。
ソースディレクトリが存在しない場合は未管理として配布先に触れない。"
```

---

### Task 4: アクションの実行と表示

**Files:**
- Create: `deployer/apply.py`
- Test: `test/test_smoke.py`

**Interfaces:**
- Consumes: `deployer.plan.build_plan(repo_root, project_name, target)`、`deployer.plan.Action`
- Produces:
  - `deployer.apply.apply_plan(plan, target, dry_run=False)` → 変更したアクション数（int）。標準出力に内訳とサマリを表示する

- [ ] **Step 1: 失敗するテストを書く**

`test/test_smoke.py`:

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m unittest discover test -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deployer.apply'`

- [ ] **Step 3: `deployer/apply.py` を実装する**

```python
"""アクション列の実行と表示。"""
import shutil

STATUS_LABELS = {
    "new": "追加",
    "update": "更新",
    "unchanged": "変更なし",
    "delete": "削除",
}


def apply_plan(plan, target, dry_run=False):
    """アクション列を実行し、変更したアクション数を返す。

    dry_run が True のときは表示だけ行い、ファイルシステムに触れない。
    """
    changed = [action for action in plan if action.status != "unchanged"]
    for action in changed:
        print("  {} {}".format(STATUS_LABELS[action.status], _display(action.dst, target)))
        if not dry_run:
            _execute(action)

    prefix = "[dry-run] " if dry_run else ""
    print(
        "{}変更 {} 件 / 変更なし {} 件".format(prefix, len(changed), len(plan) - len(changed))
    )
    return len(changed)


def _display(path, target):
    """配布先からの相対パスで表示する。外れる場合は絶対パスのまま。"""
    try:
        return str(path.relative_to(target))
    except ValueError:
        return str(path)


def _execute(action):
    if action.kind == "copy":
        action.dst.parent.mkdir(parents=True, exist_ok=True)
        # copy2 はモードを保つ。hook はシェルスクリプトなので実行ビットが要る
        shutil.copy2(action.src, action.dst)
    elif action.kind == "write":
        action.dst.parent.mkdir(parents=True, exist_ok=True)
        action.dst.write_text(action.content, encoding="utf-8")
    elif action.kind == "delete":
        if action.dst.is_dir():
            action.dst.rmdir()
        else:
            action.dst.unlink()
    else:
        raise ValueError("未知のアクション種別: {}".format(action.kind))
```

- [ ] **Step 4: テストを実行して成功を確認する**

Run: `python3 -m unittest discover test -v`
Expected: PASS — 45 tests OK（Task 1〜3 の 37 件 + 今回の 8 件）

- [ ] **Step 5: コミット**

```bash
git add deployer/apply.py test/test_smoke.py
git commit -m "feat: アクションの実行と表示を実装

dry-run は plan の表示だけを行い、実行と同じコードパスを通る。
shutil.copy2 でモードを保ち、hook スクリプトの実行ビットを維持する。"
```

---

### Task 5: CLI

**Files:**
- Create: `deployer/cli.py`
- Create: `bin/deploy.py`
- Modify: `test/test_smoke.py`（CLI の結線テストを追記）

**Interfaces:**
- Consumes: `load_projects`, `resolve_target`, `ConfigError`, `build_plan`, `apply_plan`
- Produces: `deployer.cli.main(argv=None, repo_root=None)` → exit code（`0` 成功 / `1` 設定エラー）。`repo_root` はテストからフィクスチャを差し込むための引数で、省略時はリポジトリルートを `__file__` から求める

- [ ] **Step 1: 失敗するテストを `test/test_smoke.py` の末尾（`if __name__` ブロックの直前）に追記する**

```python
class CliTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.repo = root / "repo"
        self.target = root / "target"
        self.target.mkdir(parents=True)
        _write(self.repo / "common/skills/a.md", "x")
        _write(self.repo / "projects.json", json.dumps({"portfolio": str(self.target)}))

    def _run(self, argv):
        from deployer.cli import main

        with redirect_stdout(io.StringIO()) as out:
            code = main(argv, repo_root=self.repo)
        return code, out.getvalue()

    def test_deploys_named_project(self):
        code, _ = self._run(["portfolio"])
        self.assertEqual(code, 0)
        self.assertTrue((self.target / ".claude/skills/a.md").is_file())

    def test_all_flag_deploys_every_project(self):
        code, _ = self._run(["--all"])
        self.assertEqual(code, 0)
        self.assertTrue((self.target / ".claude/skills/a.md").is_file())

    def test_dry_run_does_not_write(self):
        code, output = self._run(["--dry-run", "portfolio"])
        self.assertEqual(code, 0)
        self.assertFalse((self.target / ".claude/skills/a.md").exists())
        self.assertIn("dry-run", output)

    def test_unknown_project_returns_error_code(self):
        import contextlib

        with contextlib.redirect_stderr(io.StringIO()):
            code, _ = self._run(["nope"])
        self.assertEqual(code, 1)

    def test_missing_projects_json_returns_error_code(self):
        import contextlib

        (self.repo / "projects.json").unlink()
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code, _ = self._run(["portfolio"])
        self.assertEqual(code, 1)
        self.assertIn("projects.example.json", err.getvalue())

    def test_requires_exactly_one_of_project_or_all(self):
        from deployer.cli import main

        import contextlib

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main([], repo_root=self.repo)
            with self.assertRaises(SystemExit):
                main(["portfolio", "--all"], repo_root=self.repo)
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m unittest discover test -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deployer.cli'`

- [ ] **Step 3: `deployer/cli.py` を実装する**

```python
"""CLI の結線。argparse と各モジュールをつなぎ、エラーを exit code に変換する。"""
import argparse
import sys
from pathlib import Path

from deployer.apply import apply_plan
from deployer.config import ConfigError, load_projects, resolve_target
from deployer.plan import build_plan


def main(argv=None, repo_root=None):
    """CLI 本体。exit code を返す。repo_root はテストからの差し込み用。"""
    parser = argparse.ArgumentParser(
        prog="deploy.py",
        description="share-claude の設定を各プロジェクトへ配布する",
    )
    parser.add_argument("project", nargs="?", help="配布先のプロジェクト名")
    parser.add_argument("--all", action="store_true", help="全プロジェクトへ配布する")
    parser.add_argument(
        "--dry-run", action="store_true", help="差分を表示するだけで書き込まない"
    )
    args = parser.parse_args(argv)

    if bool(args.project) == args.all:
        parser.error("プロジェクト名か --all のどちらか一方を指定してください")

    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    try:
        projects = load_projects(repo_root)
        names = sorted(projects) if args.all else [args.project]
        for name in names:
            target = resolve_target(projects, name)
            print("{} -> {}".format(name, target))
            plan = build_plan(repo_root, name, target)
            apply_plan(plan, target, dry_run=args.dry_run)
    except ConfigError as exc:
        print("エラー: {}".format(exc), file=sys.stderr)
        return 1
    return 0
```

- [ ] **Step 4: `bin/deploy.py` を実装して実行権限を付ける**

```python
#!/usr/bin/env python3
"""share-claude の設定を各プロジェクトへ配布するエントリポイント。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deployer.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
```

```bash
chmod +x bin/deploy.py
```

- [ ] **Step 5: テストを実行して成功を確認する**

Run: `python3 -m unittest discover test -v`
Expected: PASS — 51 tests OK（Task 1〜4 の 45 件 + 今回の 6 件）

- [ ] **Step 6: CLI が実際に起動することを確認する**

Run: `./bin/deploy.py --help`
Expected: usage が表示され、exit code 0

Run: `./bin/deploy.py portfolio`
Expected: `projects.json` がまだ無いため
`エラー: projects.json が見つかりません` と `cp projects.example.json projects.json` を含むメッセージが stderr に出て exit code 1

- [ ] **Step 7: コミット**

```bash
git add deployer/cli.py bin/deploy.py test/test_smoke.py
git commit -m "feat: CLI を実装

main() は deployer/cli.py に置き、bin/deploy.py は sys.path 追加と
呼び出しだけのシムとする。bin/ はパッケージではないためテストから
直接 import できず、ロジックを bin 側に置くとテストが脆くなる。"
```

---

### Task 6: リポジトリの整備

**Files:**
- Create: `.gitignore`
- Create: `projects.example.json`
- Modify: `README.md`
- Modify: `CLAUDE.md`（現在は空ファイル）

**Interfaces:**
- Consumes: `deployer.cli.main` の CLI 仕様（`<project>` / `--all` / `--dry-run`）
- Produces: なし（ドキュメントと設定ファイル）

- [ ] **Step 1: `.gitignore` を作成する**

```
# 配布先パスはマシンごとに異なるローカル設定
projects.json

# macOS
.DS_Store

# Python
__pycache__/
*.pyc
```

- [ ] **Step 2: `projects.example.json` を作成する**

```json
{
  "portfolio": "~/path/to/portfolio"
}
```

- [ ] **Step 3: `README.md` を書く**

````markdown
# share-claude

各プロジェクトリポジトリへ Claude Code の設定（skills / hooks / rules /
settings.json / CLAUDE.md）を配信するリポジトリ。

共通設定を `common/` に、プロジェクト固有の設定を `project/<name>/` に置き、
`common` に `project` を重ねて配布する。同名ファイルは `project` 側が勝つ。

## セットアップ

```bash
cp projects.example.json projects.json
```

`projects.json` に配布先を書く。`projects.json` は gitignore されている。

```json
{
  "portfolio": "~/github/portfolio"
}
```

## 使い方

```bash
./bin/deploy.py portfolio             # 単一プロジェクトへ配布
./bin/deploy.py --all                 # 全プロジェクトへ配布
./bin/deploy.py --dry-run portfolio   # 差分を表示するだけ
```

配布前に `--dry-run` で差分を確認することを推奨する。

## 配布されるもの

| ソース | 配布先 |
|---|---|
| `common/skills/` + `project/<name>/skills/` | `<配布先>/.claude/skills/` |
| `common/hooks/` + `project/<name>/hooks/` | `<配布先>/.claude/hooks/` |
| `project/<name>/rules/` | `<配布先>/.claude/rules/` |
| `common/settings.json` + `project/<name>/settings.json` | `<配布先>/.claude/settings.json` |
| `project/<name>/CLAUDE.md` | `<配布先>/CLAUDE.md` |

`.gitkeep` と `.DS_Store` は配布されない。

### 上書きと削除の範囲

`.claude/skills/`, `.claude/hooks/`, `.claude/rules/` の3ディレクトリは
このリポジトリが所有し、**リポジトリ側に無いファイルは配布先から削除される**。

`.claude/` 直下のそれ以外のファイルには触れない。配布先固有の設定は
`.claude/settings.local.json` に置くこと（`settings.json` は毎回上書きされる）。

ソース側にディレクトリが存在しない場合、その配布先ディレクトリは未管理として
一切触れない。例えば `project/<name>/rules/` を作っていなければ、配布先の
`.claude/rules/` は削除されない。

### settings.json のマージ

`common` と `project` の両方にある場合、キーの形状ごとに扱いを変える。

| キー | 扱い |
|---|---|
| `permissions.allow` / `deny` / `ask` | 連結（common が先）・重複除去 |
| `hooks.<イベント名>` | 連結（common が先）・重複除去 |
| その他の入れ子オブジェクト | 再帰マージ、同じキーは project が勝つ |
| その他の配列・スカラー | project が勝つ |

hook スクリプトを参照するときは絶対パスではなく
`$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.sh` を使うこと。

## 開発

```bash
python3 -m unittest discover test
```

Python 3.9 以上、標準ライブラリのみで動く。外部依存は追加しない。

設計書: `docs/superpowers/specs/2026-08-28-claude-config-distribution-design.md`
````

- [ ] **Step 4: `CLAUDE.md` を書く**

```markdown
# CLAUDE.md

各プロジェクトへ Claude Code の設定を配信するリポジトリ。

## 構成

- `common/` — 全プロジェクト共通の設定（skills / hooks / settings.json）
- `project/<name>/` — プロジェクト固有の設定（skills / hooks / rules / settings.json / CLAUDE.md）
- `deployer/` — 配布ロジック
- `bin/deploy.py` — CLI エントリポイント

## このファイルについて

このファイルは **share-claude 自身**を編集するときの指示であり、配布されない。
配布されるテンプレートは `project/<name>/CLAUDE.md` の方。

## 開発ルール

- Python 3.9（`/usr/bin/python3`）の標準ライブラリのみを使う。外部依存を追加しない
- テストは `unittest`。`python3 -m unittest discover test` で実行する
- 配布先の `.claude/` 全体をミラーしてはならない。所有するのは
  `skills/` `hooks/` `rules/` の3ディレクトリと `settings.json` `CLAUDE.md` の2ファイルのみ
- 配布先パスに `Path.resolve()` を使わない（macOS の `/var` シンボリックリンクでテストが壊れる）
```

- [ ] **Step 5: テストが通ることを再確認する**

Run: `python3 -m unittest discover test -v`
Expected: PASS — 51 tests OK

- [ ] **Step 6: `projects.json` が gitignore されていることを確認する**

```bash
cp projects.example.json projects.json
git status --short
```

Expected: `projects.json` が `git status` に現れない

- [ ] **Step 7: コミット**

```bash
git add .gitignore projects.example.json README.md CLAUDE.md
git status --short
git commit -m "docs: セットアップ手順と gitignore を整備

projects.json は gitignore し、projects.example.json を雛形として置く。
README に配布範囲・削除の範囲・settings.json のマージ規則を書く。"
```

---

## Self-Review

**1. Spec coverage**

| 設計書の要求 | 対応タスク |
|---|---|
| リポジトリ構成 | Task 1〜6（各ファイル作成） |
| `common/rules` を置かない | 実施済み（ブレスト時に削除・コミット済み） |
| 配布先マッピング5種 | Task 3（`_mirror_specs`, `_settings_action`, CLAUDE.md） |
| 所有範囲を3ディレクトリ+2ファイルに限定 | Task 3（`_mirror_specs` が `.claude` 全体を対象にしない）、Task 4 のテスト `test_settings_local_json_survives` |
| 未管理の判定（配布ファイルの有無で決める） | Task 3（`_mirror_actions` の `if not sources`）、テスト `test_unmanaged_directory_is_untouched` と `test_source_dir_with_only_gitkeep_does_not_delete_target_files` |
| projects.json の形式と `~` 展開 | Task 2 |
| projects.json の gitignore | Task 6 |
| settings.json マージポリシー5行 | Task 1（テスト12件がポリシー表を網羅） |
| 片側しか存在しない場合 | Task 3（`_settings_action`）、テスト `test_single_sided_settings_is_written_as_is` |
| hook パス規約 | Task 6（README / CLAUDE.md に記載） |
| plan/apply 分離 | Task 3・4 |
| Action の形 | Task 3 |
| 除外セット | Task 3 |
| 空ディレクトリの削除 | Task 3（`_stale_actions` の `dead_dirs`） |
| CLI 4形態 | Task 5 |
| エラー処理6種 | Task 2（4種）、Task 3（JSON 不正）、Task 5（exit code 変換） |
| `--all` 中の失敗で停止 | Task 5（`try` が for を囲むため例外で即座に抜ける） |
| test_config / test_merge / test_plan / test_smoke | Task 1〜5 |

未対応の要求なし。

**2. Placeholder scan**

「TBD」「適切に処理する」「Task N と同様」等のプレースホルダなし。全コードステップに実際のコードを記載済み。

**3. Type consistency**

- `Action` のフィールド順 `(kind, dst, src, content, status)` は Task 3 の定義と Task 4 の `_execute` / `apply_plan` の参照で一致
- `merge_settings(base, overlay)` は Task 1 の定義と Task 3 の呼び出しで一致
- `load_projects(repo_root)` / `resolve_target(projects, name)` は Task 2 の定義と Task 5 の呼び出しで一致
- `build_plan(repo_root, project_name, target)` は Task 3 の定義と Task 4・5 の呼び出しで一致
- `apply_plan(plan, target, dry_run=False)` は Task 4 の定義と Task 5 の呼び出しで一致
- `ConfigError` は Task 2 で定義、Task 3・5 で使用
- status 文字列 `"new"/"update"/"unchanged"/"delete"` は Task 3 の生成側と Task 4 の `STATUS_LABELS` で一致
- kind 文字列 `"copy"/"write"/"delete"` は Task 3 の生成側と Task 4 の `_execute` で一致

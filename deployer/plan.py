"""配布アクション列の構築。ファイルシステムへの書き込みは一切行わない。"""
import filecmp
import json
import os
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
        actions.extend(_mirror_actions(target / target_rel, source_dirs, target))

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


def _mirror_actions(dst_root, source_dirs, target):
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

    # dst_root 自体、あるいはその祖先（.claude など）がシンボリックリンクだと
    # 実体は配布先の外にある可能性がある。is_symlink() は dst_root 自身しか
    # 見ないため、一段上のディレクトリがリンクだと見逃してしまう（rglob が
    # リンクの先を辿り、配布先の外を削除しかねない）。realpath で両者を解決し、
    # 実体が配布先の内側に収まっているかを見る方が確実。
    real_dst_root = os.path.realpath(str(dst_root))
    real_target = os.path.realpath(str(target))
    if real_dst_root != real_target and not real_dst_root.startswith(real_target + os.sep):
        raise ConfigError(
            "配布先の {} がシンボリックリンク経由で配布先ディレクトリの外を指しています。"
            "シンボリックリンクで配布先の外に出るミラー対象ディレクトリへの配布はサポートしていません"
            "（リンクの先を辿って配布先の外を削除してしまうため）。".format(dst_root)
        )

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

    # シンボリックリンクは指す先がファイルでもディレクトリでも
    # ここでファイル扱いにする（削除は unlink、rmdir はしない）。
    # is_dir()/is_file() はリンクを辿った先の種別を返すため、リンクを
    # 見分けずに判定するとリンク先ディレクトリを rmdir しようとして失敗する。
    actions = [
        Action("delete", path, None, None, "delete")
        for path in sorted(dst_root.rglob("*"))
        if (path.is_symlink() or path.is_file()) and path not in placed
    ]

    # 深い順に削除する。rmdir は空でないと失敗するため順序が要る
    dead_dirs = [
        path
        for path in dst_root.rglob("*")
        if path.is_dir() and not path.is_symlink() and path not in kept_dirs
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
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        raise ConfigError(
            "{} を読めません（UTF-8 で保存されているか確認してください）: {}".format(path, exc)
        ) from exc

    try:
        return json.loads(text)
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
    try:
        current = dst.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        # 読めない配布先ファイルは内容を確認できないので、上書き対象として扱う
        return "update"
    if current == content:
        return "unchanged"
    return "update"

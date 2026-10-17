"""ドキュメントサイト向けのデータ書き出し。配布時と同じ重ね合わせ規則を使う。"""

from pathlib import Path

from deployer.config import ConfigError
from deployer.plan import _load_json, collect_sources, merged_settings

# サイト上で共通ページの URL（/common/）に使うため、プロジェクト名には使えない
COMMON_SECTION = "common"


def _source_dirs(repo_root, project_name, kind):
    """重ねるソースディレクトリ。project_name が None なら common だけ。"""
    dirs = [repo_root / "common" / kind]
    if project_name is not None:
        dirs.append(repo_root / "project" / project_name / kind)
    return dirs


def _settings(repo_root, project_name):
    """配布される settings。project_name が None なら common のみ。"""
    if project_name is None:
        return _common_settings(repo_root)
    return merged_settings(repo_root, project_name) or {}


def parse_frontmatter(text):
    """先頭の --- 〜 --- 内の `key: value` 行を dict にする。無ければ {}。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    result = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        key, sep, value = line.partition(":")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        result[key.strip()] = value
    # 閉じの --- が無い場合は frontmatter とみなさない
    return {}


def export_skills(repo_root, project_name):
    """配布されるスキルの一覧を name 昇順で返す。project_name が None なら common のみ。"""
    source_dirs = _source_dirs(repo_root, project_name, "skills")
    common_dir = source_dirs[0]
    sources = collect_sources(source_dirs)

    skills = []
    for rel, path in sources.items():
        if len(rel.parts) != 2 or rel.parts[1] != "SKILL.md":
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        origin = "common" if common_dir in path.parents else "project"
        skills.append({
            "name": fm.get("name") or rel.parts[0],
            # name は重複しうるが、ディレクトリ名は配布先で一意。ページのパスに使う
            "dir": rel.parts[0],
            "description": fm.get("description"),
            "argumentHint": fm.get("argument-hint"),
            "manualOnly": fm.get("disable-model-invocation") == "true",
            "origin": origin,
            "path": path.relative_to(repo_root).as_posix(),
        })
    skills.sort(key=lambda s: s["name"])
    return skills


HOOK_COMMAND_PREFIX = "$CLAUDE_PROJECT_DIR/.claude/hooks/"
PERMISSION_KINDS = ("deny", "ask", "allow")


def script_description(text):
    """シェバン直後に続く `#` コメント行を連結した説明文を返す。無ければ None。"""
    lines = text.splitlines()
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]

    parts = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("#"):
            break
        body = stripped.lstrip("#").strip()
        if not parts and body.startswith("説明:"):
            body = body[len("説明:"):].strip()
        if body:
            parts.append(body)
    return " ".join(parts) or None


def _common_settings(repo_root):
    return _load_json(repo_root / "common" / "settings.json") or {}


def export_hooks(repo_root, project_name):
    """マージ後 settings の hooks を平坦化して返す。project_name が None なら common のみ。"""
    merged = _settings(repo_root, project_name)
    common_hooks = _common_settings(repo_root).get("hooks", {})
    hooks_dir = collect_sources(_source_dirs(repo_root, project_name, "hooks"))

    result = []
    for event, groups in merged.get("hooks", {}).items():
        for group in groups:
            origin = "common" if group in common_hooks.get(event, []) else "project"
            for hook in group.get("hooks", []):
                command = hook.get("command")
                result.append({
                    "event": event,
                    "matcher": group.get("matcher"),
                    "command": command,
                    "origin": origin,
                    "script": _resolve_script(repo_root, hooks_dir, command),
                })
    return result


def _resolve_script(repo_root, hooks_dir, command):
    if not command or not command.startswith(HOOK_COMMAND_PREFIX):
        return None
    path = hooks_dir.get(Path(command[len(HOOK_COMMAND_PREFIX):]))
    if path is None:
        return None
    return {
        "path": path.relative_to(repo_root).as_posix(),
        "description": script_description(path.read_text(encoding="utf-8")),
    }


def export_permissions(repo_root, project_name):
    """deny / ask / allow を、ルールごとの由来つきで返す。project_name が None なら common のみ。"""
    merged = _settings(repo_root, project_name)
    common = _common_settings(repo_root).get("permissions", {})

    result = {}
    for kind in PERMISSION_KINDS:
        common_rules = common.get(kind, [])
        result[kind] = [
            {"rule": rule, "origin": "common" if rule in common_rules else "project"}
            for rule in merged.get("permissions", {}).get(kind, [])
        ]
    return result


def build_docs_data(repo_root):
    """全プロジェクトのドキュメント用データを組み立てる。"""
    project_root = repo_root / "project"
    names = sorted(p.name for p in project_root.iterdir() if p.is_dir()) if project_root.is_dir() else []
    if COMMON_SECTION in names:
        raise ConfigError(
            "project/{} はドキュメントサイトの共通ページと名前が衝突します。"
            "別のプロジェクト名にしてください。".format(COMMON_SECTION)
        )

    projects = []
    for name in names:
        claude_md = project_root / name / "CLAUDE.md"
        rules = collect_sources([project_root / name / "rules"])
        projects.append({
            "name": name,
            "skills": export_skills(repo_root, name),
            "hooks": export_hooks(repo_root, name),
            "permissions": export_permissions(repo_root, name),
            "claudeMd": claude_md.relative_to(repo_root).as_posix() if claude_md.is_file() else None,
            "rules": sorted(path.relative_to(repo_root).as_posix() for path in rules.values()),
        })
    common = {
        "skills": export_skills(repo_root, None),
        "hooks": export_hooks(repo_root, None),
        "permissions": export_permissions(repo_root, None),
    }
    return {"common": common, "projects": projects}

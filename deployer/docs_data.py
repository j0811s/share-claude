"""ドキュメントサイト向けのデータ書き出し。配布時と同じ重ね合わせ規則を使う。"""

from deployer.plan import collect_sources


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
    """配布されるスキルの一覧を name 昇順で返す。"""
    common_dir = repo_root / "common" / "skills"
    project_dir = repo_root / "project" / project_name / "skills"
    sources = collect_sources([common_dir, project_dir])

    skills = []
    for rel, path in sources.items():
        if len(rel.parts) != 2 or rel.parts[1] != "SKILL.md":
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        origin = "common" if common_dir in path.parents else "project"
        skills.append({
            "name": fm.get("name") or rel.parts[0],
            "description": fm.get("description"),
            "argumentHint": fm.get("argument-hint"),
            "manualOnly": fm.get("disable-model-invocation") == "true",
            "origin": origin,
            "path": path.relative_to(repo_root).as_posix(),
        })
    skills.sort(key=lambda s: s["name"])
    return skills

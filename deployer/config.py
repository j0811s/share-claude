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
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        raise ConfigError(
            "projects.json を読めません（UTF-8 で保存されているか確認してください）: {}".format(exc)
        ) from exc

    try:
        raw = json.loads(text)
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

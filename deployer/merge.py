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

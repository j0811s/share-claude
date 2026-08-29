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

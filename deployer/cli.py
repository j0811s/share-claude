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
    except OSError as exc:
        print(
            "エラー: 配布処理中にファイル操作が失敗しました: {}\n"
            "配布先が中途半端な状態になっている可能性があります。"
            "内容を確認してから再実行してください。".format(exc),
            file=sys.stderr,
        )
        return 1
    return 0

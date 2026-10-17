#!/usr/bin/env python3
"""ドキュメントサイト向けに、配布内容を JSON として書き出す。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deployer.config import ConfigError  # noqa: E402
from deployer.docs_data import build_docs_data  # noqa: E402


def main(argv):
    if len(argv) != 2:
        print("usage: export-docs-data.py <出力パス>", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parent.parent
    try:
        data = build_docs_data(repo_root)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    out = Path(argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

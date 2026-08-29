#!/usr/bin/env python3
"""share-claude の設定を各プロジェクトへ配布するエントリポイント。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deployer.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

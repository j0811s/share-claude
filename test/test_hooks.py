""".env 書き込みブロック hook の判定の検証。"""
import json
import subprocess
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "common" / "hooks" / "block-env-write.sh"


def run_hook(tool_input):
    payload = json.dumps({"tool_name": "Edit", "tool_input": tool_input})
    return subprocess.run(["sh", str(HOOK)], input=payload, text=True, capture_output=True).returncode


class BlockEnvWriteTest(unittest.TestCase):
    def test_blocks_env_files(self):
        for path in ["/repo/.env", "/repo/.env.local", "/repo/apps/web/.env.production"]:
            with self.subTest(path=path):
                self.assertEqual(run_hook({"file_path": path, "content": "X=1"}), 2)

    def test_allows_process_env_in_content(self):
        tool_input = {
            "file_path": "/repo/src/route.ts",
            "old_string": "const a = 1;",
            "new_string": "const key = process.env.RESEND_API_KEY;",
        }
        self.assertEqual(run_hook(tool_input), 0)

    def test_allows_ordinary_files(self):
        self.assertEqual(run_hook({"file_path": "/repo/src/environment.ts", "content": "x"}), 0)


if __name__ == "__main__":
    unittest.main()

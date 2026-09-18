#!/bin/sh
input=$(cat)
if echo "$input" | grep -q '"file_path"[^}]*\.env'; then
  echo 'BLOCKED: .env ファイルへの書き込みは禁止されています' >&2
  exit 2
fi
exit 0

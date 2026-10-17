#!/bin/sh
# 説明: src/ 配下のファイルを編集した後に Biome でチェックし、結果を表示する
input=$(cat)
file=$(printf '%s' "$input" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
case "$file" in
  "$CLAUDE_PROJECT_DIR"/src/*)
    cd "$CLAUDE_PROJECT_DIR" && npx biome check "$file" 2>&1 | tail -20
    ;;
esac
exit 0

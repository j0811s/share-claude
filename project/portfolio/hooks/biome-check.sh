#!/bin/sh
input=$(cat)
file=$(printf '%s' "$input" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
case "$file" in
  "$CLAUDE_PROJECT_DIR"/src/*)
    cd "$CLAUDE_PROJECT_DIR" && npx biome check "$file" 2>&1 | tail -20
    ;;
esac
exit 0

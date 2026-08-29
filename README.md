# share-claude

各プロジェクトリポジトリへ Claude Code の設定（skills / hooks / rules /
settings.json / CLAUDE.md）を配信するリポジトリ。

共通設定を `common/` に、プロジェクト固有の設定を `project/<name>/` に置き、
`common` に `project` を重ねて配布する。同名ファイルは `project` 側が勝つ。

## セットアップ

```bash
cp projects.example.json projects.json
```

`projects.json` に配布先を書く。`projects.json` は gitignore されている。

```json
{
  "portfolio": "~/github/portfolio"
}
```

## 使い方

```bash
./bin/deploy.py portfolio             # 単一プロジェクトへ配布
./bin/deploy.py --all                 # 全プロジェクトへ配布
./bin/deploy.py --dry-run portfolio   # 差分を表示するだけ
```

配布前に `--dry-run` で差分を確認することを推奨する。

## 配布されるもの

| ソース | 配布先 |
|---|---|
| `common/skills/` + `project/<name>/skills/` | `<配布先>/.claude/skills/` |
| `common/hooks/` + `project/<name>/hooks/` | `<配布先>/.claude/hooks/` |
| `project/<name>/rules/` | `<配布先>/.claude/rules/` |
| `common/settings.json` + `project/<name>/settings.json` | `<配布先>/.claude/settings.json` |
| `project/<name>/CLAUDE.md` | `<配布先>/CLAUDE.md` |

`.gitkeep` と `.DS_Store` は配布されない。

### 上書きと削除の範囲

`.claude/skills/`, `.claude/hooks/`, `.claude/rules/` の3ディレクトリは
このリポジトリが所有し、**リポジトリ側に無いファイルは配布先から削除される**。

`.claude/` 直下のそれ以外のファイルには触れない。配布先固有の設定は
`.claude/settings.local.json` に置くこと（`settings.json` は毎回上書きされる）。

配布するファイルが1つも無いディレクトリは未管理として一切触れない。判定は
「ソースディレクトリが存在するか」ではなく「**除外を適用した後に配布するファイルがあるか**」で
行う。例えば `project/<name>/rules/` を作っていなければ、配布先の `.claude/rules/` は
削除されない。`.gitkeep` しか入っていないディレクトリも同様に未管理となる。

この判定の結果として、いったん配布したディレクトリのソースを空にしても
（全ファイルを消す、あるいは `.gitkeep` だけ残す）、配布先に残ったファイルは
削除されずそのまま残る。最後の1ファイルまで消したい場合は配布先で手動削除する。

### settings.json のマージ

`common` と `project` の両方にある場合、キーの形状ごとに扱いを変える。

| キー | 扱い |
|---|---|
| `permissions.allow` / `deny` / `ask` | 連結（common が先）・重複除去 |
| `hooks.<イベント名>` | 連結（common が先）・重複除去 |
| その他の入れ子オブジェクト | 再帰マージ、同じキーは project が勝つ |
| その他の配列・スカラー | project が勝つ |

hook スクリプトを参照するときは絶対パスではなく
`$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.sh` を使うこと。

## 開発

```bash
python3 -m unittest discover test
```

Python 3.9 以上、標準ライブラリのみで動く。外部依存は追加しない。

設計書: `docs/superpowers/specs/2026-08-28-claude-config-distribution-design.md`
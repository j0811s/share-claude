---
name: ship-issue
description: GitHub Issue の実装から PR・マージ・GitHub Release 作成までを扱う。Issue を起点に実装を始めるとき、または Issue 対応中のブランチ・PR の続き（CI 待ち・マージ・リリース）を再開するときに使う。引数に Issue 番号を取る（例: /ship-issue 12）。
argument-hint: "[issue-number]"
---

# Ship Issue

GitHub Issue → 実装 → PR → マージ → GitHub Release までを1本のワークフローで進める。
GitHub 操作はすべて `gh` CLI で行う（GitHub MCP は使わない）。

**🛑 STOP と書かれた箇所では必ず停止し、ユーザーの承認を得てから次へ進む。** 承認なしにまとめて進めない。

以下のチェックリストを応答にコピーし、進捗に合わせてチェックしていく：

```
Ship Issue #<N>:
- [ ] 0. Issue 特定・再開判定
- [ ] 1. 実装方針の承認 🛑
- [ ] 2. ブランチ作成
- [ ] 3. 実装
- [ ] 4. /pre-push 通過
- [ ] 5. コミット・PR 作成の承認 🛑 → push・PR 作成
- [ ] 6. CI 通過
- [ ] 7. マージの承認 🛑 → マージ
- [ ] 8. バージョンの承認 🛑 → Release 作成
- [ ] 9. 完了報告
```

## 0. Issue の特定と再開判定

- 引数が無ければ `gh issue list --state open` を表示し、どれに着手するか聞く。
- 既存の進捗を確認し、該当フェーズから再開する：

```bash
git branch --list "*/<N>-*"
gh pr list --state all --search "<N> in:body"
```

| 状態 | 再開フェーズ |
|------|-------------|
| ブランチ・PR なし | 1 |
| ブランチあり・PR なし | 3 |
| PR open | 6 |
| PR merged・未リリース | 8 |

## 1. Issue の読み込みと方針決定

```bash
gh issue view <N> --json title,body,labels,comments
```

要件・受け入れ条件・影響範囲（関連ファイル）を整理し、実装方針を提示する。
規模が大きい・設計判断を含む場合は `superpowers:brainstorming` → `superpowers:writing-plans` を使う。

🛑 **STOP: 実装方針の承認を得る。**

## 2. ブランチ作成

```bash
git switch main && git pull --ff-only
git switch -c <type>/<N>-<slug>   # 例: feat/12-blog-rss, fix/15-toc-anchor
```

`<type>` はラベルから決める（`bug` → `fix`、`enhancement` → `feat`、`documentation` → `docs`、その他 → `chore`）。

## 3. 実装

`.claude/reference/workflow.md` に従う（編集時の Biome フック、`tests/` 編集後の test / e2e、ドキュメント更新）。
途中で main に追従する必要があれば `git merge origin/main` を使う（rebase + force push は禁止）。

## 4. 品質ゲート

**`/pre-push` を実行する。** Must 指摘が残る限り次へ進まない。手順を独自に省略・再実装しない。

## 5. コミット・push・PR 作成

コミットは Conventional Commits 形式・日本語 subject（`wrap-up` スキルの型表に準拠）、末尾に Co-Authored-By 行。

🛑 **STOP: コミット内容と PR タイトル・本文の承認を得る。**

```bash
git push -u origin <branch>
gh pr create --base main --title "<type>: <subject>" --body "<body>"
```

PR 本文に必ず含める：概要、変更点、テスト結果（`/pre-push` のサマリー表）、`Closes #<N>`、末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)`。

## 6. CI 待ち

```bash
gh pr checks <PR> --watch
```

`Check` が失敗したらログ（`gh run view --log-failed`）を確認し、フェーズ3に戻って修正・push する。

## 7. マージ

🛑 **STOP: マージの承認を得る。**

```bash
gh pr merge <PR> --merge --delete-branch   # このリポジトリは merge commit のみ許可
git switch main && git pull --ff-only
```

**`--admin` は絶対に使わない。** CI が通らない PR をブランチ保護を迂回してマージしない。

## 8. リリース

前回タグ以降のコミットからバージョンを決める（タグが無ければ初回は `v1.0.0`）：

```bash
git fetch --tags
git describe --tags --abbrev=0            # 前回タグ
git log <前回タグ>..main --oneline
```

| 含まれるコミット | 上げる桁 |
|-----------------|---------|
| `BREAKING CHANGE` / `!:` | major |
| `feat` | minor |
| それ以外のみ | patch |

🛑 **STOP: バージョン番号の承認を得る。**

```bash
gh release create v<X.Y.Z> --target main --generate-notes
git fetch --tags
```

`package.json` の `version` は更新しない（バージョンはタグで管理）。デプロイは Vercel の main 自動デプロイに任せる。

## 9. 完了報告

Issue（自動クローズされたか `gh issue view <N> --json state` で確認）・PR・Release の URL をまとめて報告する。

## よくある間違い

| 間違い | 正しい対応 |
|--------|-----------|
| `gh pr merge --squash` / `--rebase` | このリポジトリでは失敗する。`--merge` を使う |
| `--delete-branch` を付け忘れる | 自動削除は無効なので、ブランチが残り続ける |
| CI 失敗中に `--admin` でマージ | 禁止。修正して CI を通す |
| main への直接 push でバージョンを上げる | ブランチ保護違反。バージョンはタグのみ |
| PR 本文に `Closes #N` が無い | Issue が自動クローズされない |

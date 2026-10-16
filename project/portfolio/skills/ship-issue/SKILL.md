---
name: ship-issue
description: GitHub Issue の実装から PR 作成・CI 通過までを扱い、人間のマージ後に自動リリースを確認する。Issue を起点に実装を始めるとき、または Issue 対応中のブランチ・PR の続き（CI 待ち・マージ後の確認）を再開するときに使う。引数に Issue 番号を取る（例: /ship-issue 12）。
argument-hint: "[issue-number]"
---

# Ship Issue

GitHub Issue → 実装 → PR → CI 通過までを進め、マージは人間に委ねる。
マージ後の GitHub Release は `.github/workflows/release.yml` が自動作成する。
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
- [ ] 7. 人間にマージを依頼 🛑
- [ ] 8. マージ後の確認（Release・後片付け）
```

## 0. Issue の特定と再開判定

- 引数が無ければ `gh issue list --state open` を表示し、どれに着手するか聞く。
- 既存の進捗を確認し、該当フェーズから再開する：

```bash
git branch --list "*/<N>-*"
gh pr list --state all --search "<N> in:body" --json number,state,headRefName
```

| 状態 | 再開フェーズ |
|------|-------------|
| ブランチ・PR なし | 1 |
| ブランチあり・PR なし | 3 |
| PR open | 6 |
| PR merged | 8 |

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
**コミットの型がリリースのバージョンを決める**（`feat` → minor、`fix` → patch、`!:` / `BREAKING CHANGE` → major、それ以外のみ → リリースなし）ので、型は変更内容に正確に合わせる。

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

`check` が失敗したらログ（`gh run view <run-id> --log-failed`）を確認し、フェーズ3に戻って修正・push する。

## 7. 人間にマージを依頼

**Claude はマージしない（`gh pr merge` を実行しない）。** 以下を報告して停止する：

- PR の URL と CI 結果
- レビューしてほしい点（設計判断・影響範囲・目視確認すべき画面）
- マージ後に自動リリースされる見込みのバージョン（前回タグ以降のコミットの型から）

🛑 **STOP: ユーザーがマージしたと伝えるまで待つ。**

## 8. マージ後の確認

```bash
gh pr view <PR> --json state,mergedAt        # MERGED を確認
git switch main && git pull --ff-only
git branch -d <branch>
git push origin --delete <branch> 2>/dev/null || true   # GitHub 側で削除済みなら何もしない
gh run list -w release.yml -L 1               # 自動リリースの実行結果
gh release view --json tagName,url            # 最新 Release
gh issue view <N> --json state                # Closes #N で CLOSED になったか
```

- `release.yml` が失敗していたらログを確認して報告する（Release を手動で作り直さない）。
- `docs` / `chore` 等のみでリリースが作られなかった場合は、その旨を報告する。

Issue・PR・Release（またはリリースなし）の結果をまとめて報告する。

## よくある間違い

| 間違い | 正しい対応 |
|--------|-----------|
| Claude が `gh pr merge` でマージする | マージは人間が行う。フェーズ7で停止する |
| `gh release create` で手動リリースする | Release は `release.yml` が作る。重複させない |
| 実質 `feat` の変更を `chore` でコミット | リリースされない。型を変更内容に合わせる |
| main に直接 push する | ルールセットで禁止。必ず PR 経由 |
| PR 本文に `Closes #N` が無い | Issue が自動クローズされない |

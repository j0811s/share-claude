---
name: pre-push
description: git push前に品質ゲート（check → build → test → e2e → コードレビュー）を一括実行し、全てパスしたことを確認してから push を促す。
---

# Pre-Push Quality Gate

## 概要

git push / PR 作成の前に、品質チェックとコードレビューを一括実行する。
編集中の自動チェックは PostToolUse フック（編集ファイルのみ）に任せ、
`src/` 全体の品質確認とコードレビューは本スキルに集約されている。

## 実行手順

### 1. ステージング状態の確認

```bash
git status
git add -A
git status
```

変更ファイルを確認し、意図しないファイルが含まれていないかチェックする。

### 2. Biome チェック

```bash
npm run check
```

エラーがあれば `/biome-autofix` を実行する。
修正不可能なエラーがある場合はここで停止してユーザーに報告する。

### 3. プロダクションビルド

```bash
npm run build
```

ビルドエラーがあれば修正を提案する。

### 4. テストの実行（変更内容に応じて）

`tests/unit/` 配下のファイルが関係する場合：

```bash
npm run test -- --run
```

`tests/e2e/` 配下のファイルが関係する場合：

```bash
npm run e2e
```

### 5. コードレビュー

1. `git diff HEAD` で変更内容を確認する（未コミット変更が無い場合は `git diff main...HEAD`）
2. `.tsx` / `.jsx` の変更がある場合は `/react-doctor` を実行し、優先度「高」「中」の問題が消えるまで修正する（「低」は許容）
3. `code-reviewer` エージェントを起動する（常時）
4. 変更内容に応じて追加エージェントを起動する：

   | 変更内容 | エージェント |
   |---------|-------------|
   | catch ブロック・エラーハンドリング | `pr-review-toolkit:silent-failure-hunter` |
   | 型定義の追加・変更 | `pr-review-toolkit:type-design-analyzer` |
   | テストの追加・変更 | `pr-review-toolkit:pr-test-analyzer` |
   | JSDoc・コメントの追加 | `pr-review-toolkit:comment-analyzer` |
   | 認証・API・フォーム変更 | `security-reviewer` |

5. 最後に `/difit-review` を起動してユーザーによるレビューを依頼する

### 6. 結果サマリーの報告

全ステップの結果を表にまとめて報告する：

| ステップ | 結果 |
|---------|------|
| Biome check | ✅ / ❌ |
| Build | ✅ / ❌ |
| Unit test | ✅ / ❌ / スキップ |
| E2E test | ✅ / ❌ / スキップ |
| レビュー | Must 指摘 n 件 / 問題なし |

Must（要修正）の指摘が残っている場合は push を促さず、修正を提案する。

## 注意事項

- `git commit` と `git push` はこのスキルでは実行しない。ユーザーが判断する。
- ビルドキャッシュが原因の誤検知を避けるため、`npm run build` の前に `.next/` の削除は行わない（必要ならユーザーが指示する）。
- PR 作成前にさらに包括的なレビューを行いたい場合は `/pr-review-toolkit:review-pr` を使う（対象を絞る例: `/pr-review-toolkit:review-pr errors tests`）。

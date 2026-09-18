---
name: biome-autofix
description: Biome の自動修正可能な lint/format エラーを一括適用し、手動対応が必要な残存エラーのみ報告する。npm run check の失敗後に使う。
---

# Biome Autofix

## 概要

`npm run check` でエラーが出たとき、自動修正できるものをまず適用してから
残った問題だけをピンポイントで報告する。

## 実行手順

### 1. 現在のエラー数を把握

```bash
npm run check 2>&1 | tail -5
```

エラー件数と警告件数を記録する。

### 2. フォーマット自動修正

```bash
npm run format
```

### 3. Lint 自動修正

```bash
npm run lint:fix
```

### 4. 残存エラーを確認

```bash
npm run check
```

### 5. 結果を報告

- 自動修正された件数（ステップ1との差分）
- 残存エラーの一覧（ファイル・行番号・内容）
- 残存エラーの修正方針を提案

## 自動修正できない代表的なエラーへの対応方針

| エラー種別 | 対応方針 |
|-----------|---------|
| `noExplicitAny` | 型を明示する |
| `useConsistentMemberAccessibility` | `public`/`private` を明示する |
| `noUnusedVariables` | 変数・インポートを削除 |
| CSS ネスト構文 | フラットなセレクターに書き直す（プロジェクト規約） |

## 注意事項

- `lint:fix` は `src/` 配下のみに適用される（`biome.json` の設定による）
- CSS の自動修正は Biome の対応状況によって限定的。手動修正が必要なケースあり
- このスキル実行後は必ず `git diff` でステージングされていない変更を確認すること

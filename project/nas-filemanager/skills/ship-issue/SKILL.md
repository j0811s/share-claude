---
name: ship-issue
description: GitHub Issue を起点に、方針決定・実装・品質ゲート・レビューを経て main へのコミットまで進める。Issue に着手するとき、または途中まで進めた Issue 対応を再開するときに使う。引数に Issue 番号を取る（例: /ship-issue 12）。Issue がまだ無い場合は先に /propose-issues を使う。
argument-hint: "[issue-number]"
disable-model-invocation: true
---

# Ship Issue

GitHub Issue → 方針 → 実装 → 品質ゲート → レビュー → main へのコミットまで進める。
このリポジトリは **main 直接運用**（ブランチ・PR を作らない）。**push は人間が行う**ので、Claude は `git push` を実行しない。
GitHub 操作はすべて `gh` CLI で行う。

**🛑 STOP と書かれた箇所では必ず停止し、ユーザーの承認を得てから次へ進む。** 承認なしにまとめて進めない。

以下のチェックリストを応答にコピーし、進捗に合わせてチェックしていく：

```
Ship Issue #<N>:
- [ ] 0. Issue 特定・再開判定
- [ ] 1. 実装方針の承認 🛑
- [ ] 2. 設計 doc・実装計画（規模が大きい場合のみ）
- [ ] 3. 実装（TDD）
- [ ] 4. 品質ゲート通過
- [ ] 5. コードレビュー
- [ ] 6. コミットの承認 🛑 → コミット
- [ ] 7. 完了報告
```

## 0. Issue の特定と再開判定

- 引数が無ければ `gh issue list --state open` を表示し、どれに着手するか聞く。open な Issue が無ければ `/propose-issues` を案内する。
- 既存の進捗を確認する：

```bash
gh issue view <N> --json state,title
git log --oneline origin/main..HEAD --grep "Closes #<N>"
git status --short
ls docs/superpowers/specs docs/superpowers/plans
```

| 状態 | 再開フェーズ |
|------|-------------|
| Issue が CLOSED | 対応済み。ユーザーに報告して終了 |
| `Closes #<N>` を含むコミットが未 push | 7（push 待ち） |
| 関連する plan があり、未完了タスクが残る | 3（plan の続きから） |
| 関連する spec のみある | 2 |
| 上記いずれも無い | 1 |

未コミットの変更が残っている場合は、それが今回の Issue のものかユーザーに確認してから進める。

## 1. Issue の読み込みと方針決定

```bash
gh issue view <N> --json title,body,labels,comments
```

要件・受け入れ条件・影響範囲（関連ファイル）を整理する。`docs/spec.md` の該当セクション（API 設計・セキュリティ必須事項など）を必ず読み、方針に反映する。

規模を判定して方針を提示する：

| 規模 | 目安 | 進め方 |
|---|---|---|
| 小 | 1〜2 ファイルの修正、設計判断なし | フェーズ 2 を飛ばして 3 へ |
| 大 | 新しい feature・API 追加、複数ワークスペースにまたがる、設計判断を含む | フェーズ 2 で設計 doc と実装計画を作る |

🛑 **STOP: 実装方針（規模の判定を含む）の承認を得る。**

## 2. 設計 doc・実装計画（規模が大きい場合のみ）

`docs/roadmap.md` の進め方に従う：

1. `superpowers:brainstorming` で設計を詰め、`docs/superpowers/specs/YYYY-MM-DD-<slug>.md` に書く
2. `superpowers:writing-plans` で実装計画を `docs/superpowers/plans/YYYY-MM-DD-<slug>.md` に書く
3. 両 doc の冒頭に対象 Issue（`#<N>`）を記す

各スキル内の承認ステップはそのスキルの指示に従う。doc は `docs:` 型で個別にコミットしてよい（フェーズ 6 の承認手順に従う。`Closes` は付けない）。

## 3. 実装

- `superpowers:test-driven-development` に従い、テストを先に書く。plan がある場合は `superpowers:executing-plans` か `superpowers:subagent-driven-development` で plan のタスク順に進める。
- 新しい feature ディレクトリを作るときは `/new-feature` を使う。

## 4. 品質ゲート

pre-commit（lint-staged）は test と build を実行しないため、ここで明示的に全部実行する：

```bash
npm run typecheck
npm run lint
npm run fmt:check
npm run test
npm run build
```

1 つでも失敗したら修正して全部やり直す。`fmt:check` の失敗は `npm run fmt`、lint の自動修正可能なものは `npm run lint:fix` で直してよい。
UI の変更があれば `/run` などで実際の画面を確認する。Claude が確認できないもの（Pi 実機・実機 Safari 等）は手動 QA 項目としてフェーズ 7 で報告する。

## 5. コードレビュー

1. `git diff HEAD` で変更内容を確認する（フェーズ 2 で doc をコミット済みなら、その後の差分）。
2. `apps/web` の `.tsx` を変更した場合は `/react-doctor` を実行し、優先度「高」「中」の問題を修正する。
3. `pr-review-toolkit:code-reviewer` エージェントを起動する（常時）。
4. 変更内容に応じて追加エージェントを起動する：

   | 変更内容 | エージェント |
   |---------|-------------|
   | catch ブロック・エラーハンドリング | `pr-review-toolkit:silent-failure-hunter` |
   | 型定義の追加・変更（`packages/shared` 含む） | `pr-review-toolkit:type-design-analyzer` |
   | テストの追加・変更 | `pr-review-toolkit:pr-test-analyzer` |
   | ファイルパス・認証・アップロード／ダウンロード | `/security-review` |

修正が必要な指摘は直し、フェーズ 4 の品質ゲートを再実行する。採用しなかった指摘は理由をフェーズ 6 で報告する。

## 6. コミット

CLAUDE.md の規約に従う：Conventional Commits、**接頭辞は英語・本文は日本語**（例: `feat: ファイル一覧APIを追加`）。scope は付けない。
型はラベルと変更内容から決める（`bug` → `fix`、`enhancement` → `feat`、`documentation` → `docs`。変更内容と食い違う場合は内容を優先）。

変更が論理的に分かれる場合は複数コミットに分ける。**最後のコミットの本文にだけ `Closes #<N>` を入れる**（人間が push した時点で Issue が自動クローズされる）。

対応する `docs/roadmap.md` の項目があれば `[x]` に更新し、同じコミットに含める。

🛑 **STOP: コミットの分け方・メッセージ・対象ファイルの承認を得る。**

承認後に `git add <対象ファイル>` → `git commit`。pre-commit フックが失敗したら原因を直して新しくコミットし直す（`--no-verify` で回避しない、`--amend` しない）。

## 7. 完了報告

次をまとめて報告して終了する：

- コミット一覧（`git log --oneline origin/main..HEAD`）
- 品質ゲートとレビューの結果（採用しなかった指摘とその理由を含む）
- 手動 QA が必要な項目（Pi 実機・実機ブラウザなど）
- push はユーザーが行うこと、push すると `Closes #<N>` で Issue が自動クローズされること

## よくある間違い

| 間違い | 正しい対応 |
|--------|-----------|
| ブランチを切る・PR を作る | main 直接運用。main にコミットする |
| Claude が `git push` する | push は人間が行う。フェーズ 7 で案内して終わる |
| すべてのコミットに `Closes #N` を付ける | 最後のコミットだけに付ける |
| `feat(files): ...` のように scope を付ける・英語本文 | 接頭辞のみ英語、本文は日本語 |
| typecheck と lint だけで品質ゲートを済ませる | test と build も必ず実行する（pre-commit では走らない） |
| spec.md を読まずに実装する | フェーズ 1 で該当セクションを読む（特にセキュリティ必須事項） |

---
name: ship
description: 変更をブランチにコミットして PR を作り、CI を見届ける。引数に merged を渡すと、マージ後の本番デプロイを見届ける。
disable-model-invocation: true
---

引数: $ARGUMENTS

## 引数が `merged` のとき（ユーザーが PR をマージした後）

1. `git switch main && git pull --ff-only`。マージ済みのローカルブランチは `git branch -d` で消す。
2. 最新の Deploy の実行を見届ける:
   `R=$(gh run list --workflow Deploy --branch main --limit 1 --json databaseId -q '.[0].databaseId'); gh run watch $R --exit-status`
3. 結果を報告し、失敗なら `gh run view $R --log-failed` で原因を調べる。成功したら、`tag` ジョブが付けたタグを `git fetch --tags` で取り、`git describe --tags` で確かめて報告する（版はマージした PR のブランチ名で決まる。`feature/` は真ん中、`fix/` は右端が上がり、`docs/`・`chore/`・`test/`・`ci/` ではタグは付かないのが正しい）。本番で確かめてほしいことがあれば、手順として書く。

## それ以外（PR を作る）

1. main にいるなら、内容に合うブランチを切る。**版はこのブランチ名で自動で決まる**（README「バージョン」）ので、名前を中身に合わせる:
   - `feature/...`：機能を足す・振る舞いを変える（真ん中が上がる。1.2.0 → 1.3.0）
   - `fix/...`：直しだけ（右端が上がる。1.2.0 → 1.2.1）
   - `docs/...`・`chore/...`・`test/...`・`ci/...`：文書・依存・テスト・CI だけ（上げない）
   ほかの名前の PR は CI（`scripts/check-branch.ts`）で落ちる。迷ったらユーザーに聞く。今のブランチ名が中身と合わなくなったら、PR を作る前にブランチを切り直す（PR の途中で直しから機能に広がったなど）。
2. `package.json` の version は触らない（使わない）。PR の本文の「## 変更」の最後に、マージで上がる見込みの版を 1 行書く（最新のタグは `git describe --tags --abbrev=0`）。
3. `/verify` と同じ検査を通す。通らなければ直してから進む。
4. コミットする。メッセージは日本語で、何を・なぜを 1 行目に書く。
5. `git push -u origin <branch>`。force push はしない。
6. `gh pr create` で PR を作る。本文は日本語で「## 変更」「## 確認」の見出しを使う。
7. `gh pr checks <番号> --watch` で CI を見届け、PR の URL と結果を報告する。

マージはユーザーがする。こちらから `gh pr merge` しない。

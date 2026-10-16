---
name: propose-issues
description: 次に取り組む GitHub Issue の候補を洗い出し、選ばれたものを Issue として作成する。コードベース・セッションの残課題・本番の状態・依存パッケージを調べる。「次に何をやるか」「Issue のネタ」「改善点を洗い出して」と言われたとき、または /ship-issue に渡す Issue が無いときに使う。
argument-hint: "[code] [sessions] [prod] [deps]（省略時は全部）"
disable-model-invocation: true
---

# Propose Issues

複数の情報源から Issue 候補を集め、優先度順に提示する。**ユーザーが選んだ候補だけ** `gh issue create` で作成する。
作った Issue はそのまま `/ship-issue <番号>` で着手できる形にする。

引数で情報源を絞れる（`code` / `sessions` / `prod` / `deps`）。引数が無ければ全部を調べる。

```
Propose Issues:
- [ ] 1. 既存 Issue の取得
- [ ] 2. 情報源ごとに候補を収集
- [ ] 3. 重複・解決済みの除外
- [ ] 4. 候補一覧の提示 🛑
- [ ] 5. 選ばれた候補の Issue 作成
```

## 1. 既存 Issue の取得

```bash
gh issue list --state all --limit 200 --json number,title,state,labels
```

候補を作るたびにこの一覧と突き合わせ、同じ内容の Issue があれば候補から外す（open なら「既存 #N」と注記するだけ）。

## 2. 候補の収集

各情報源で見つけたものは、**根拠（ファイル:行・コマンド出力・URL）を必ず控える**。根拠を示せないものは候補にしない。

### code: コードベース

```bash
npm run check 2>&1 | tail -40                          # Biome の warning
npx -y react-doctor@latest . --verbose 2>&1 | tail -60  # React の問題（優先度「高」「中」のみ採用）
git grep -n -E 'TODO|FIXME|HACK|XXX' -- src tests
```

あわせて、`README.md` と `.claude/reference/*.md` の記述が実装と食い違っている箇所を確認する（ルート・API エンドポイント・フィーチャー構成など）。

### sessions: セッションの残課題

`docs/sessions/*.md` の「残課題」セクションを読み、現在のコード・git log で**まだ未解決のものだけ**を候補にする。

### prod: 本番の状態

- **Vercel**: `list_projects` で portfolio プロジェクトを特定し、`get_runtime_errors`（直近7日）で発生頻度の高いエラーを確認する。本番 URL は `list_project_domains` で取得する。
- **Lighthouse**: chrome-devtools MCP の `lighthouse_audit` を本番 URL に対して実行し、Performance / Accessibility / Best Practices / SEO の失点項目を見る。サイトは認証必須なので、未ログインで到達できるページ（`/auth`・`/offline`）だけを対象とする。認証情報は使わない。
- MCP が接続できない場合は、その情報源を「未確認」として報告し、ほかの情報源の調査は続ける。

### deps: 依存パッケージ

```bash
npm outdated --json || true    # 更新がある場合 exit 1 になるため
npm audit --json || true
```

- `npm audit` の high / critical は個別の候補にする。
- メジャーバージョンが上がっているものは、パッケージごとに個別の候補にする。破壊的変更の調査が必要なため。
- マイナー・パッチの更新はまとめて1件の候補にする。

## 3. 候補の整理

- 同じ原因の指摘は1件にまとめる。
- 既存 Issue と重複するもの、すでに解決済みのものは除外する。
- 優先度を付ける：

| 優先度 | 基準 |
|---|---|
| 高 | 本番エラー、セキュリティ（audit high 以上）、機能の不具合 |
| 中 | a11y・性能の明確な失点、react-doctor の高・中、ドキュメントと実装の食い違い |
| 低 | warning・TODO・マイナー更新・リファクタリング |

## 4. 候補の提示

次の表で提示し、作成する候補をユーザーに選んでもらう（番号で複数選択）。

| # | 優先度 | タイトル案 | ラベル | 情報源 | 根拠 |
|---|---|---|---|---|---|

- タイトル案は、Issue のタイトルとしてそのまま使える形にする。
- ラベルは既存のもの（`bug` / `enhancement` / `documentation`）から選ぶ。`/ship-issue` はラベルからブランチ名の型を決めるため。
- 除外した候補（重複・解決済み）と未確認の情報源は、表の下に1行ずつ記す。

🛑 **STOP: 作成する候補の選択を待つ。** 選ばれなかった候補は作らない。

## 5. Issue の作成

選ばれた候補ごとに作成する：

```bash
gh issue create --label <label> --title "<タイトル>" --body "<本文>"
```

本文は次の構成にする（`/ship-issue` のフェーズ1でそのまま方針を立てられるようにするため）：

```markdown
## 背景
<なぜ問題か>

## 根拠
<ファイル:行・コマンド出力の抜粋・URL>

## 要件
- <やること>

## 受け入れ条件
- <完了を確認する方法>
```

作成した Issue の番号と URL を一覧で報告し、着手するときは `/ship-issue <番号>` を使うよう案内する。

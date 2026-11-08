---
name: propose-issues
description: 次に取り組むタスクの候補を洗い出し、選ばれたものを GitHub Issue として作成する（タスク化）。roadmap・spec の未実装部分、コード上の TODO や lint warning、依存パッケージを調べる。「次に何をやるか」「タスク化して」「Issue にして」「改善点を洗い出して」と言われたとき、または /ship-issue に渡す Issue が無いときに使う。
argument-hint: "[roadmap] [code] [deps]（省略時は全部）"
disable-model-invocation: true
---

# Propose Issues

複数の情報源から Issue 候補を集め、優先度順に提示する。**ユーザーが選んだ候補だけ** `gh issue create` で作成する。
作った Issue はそのまま `/ship-issue <番号>` で着手できる形にする。GitHub 操作はすべて `gh` CLI で行う。

引数で情報源を絞れる（`roadmap` / `code` / `deps`）。引数が無ければ全部を調べる。
ユーザーが具体的なタスク内容を伝えている場合は、手順 2 の情報源調査だけを省き、その内容を候補として手順 1・3・4・5 を行う。

```
Propose Issues:
- [ ] 1. 既存 Issue の取得
- [ ] 2. 情報源ごとに候補を収集
- [ ] 3. 重複・解決済みの除外と優先度付け
- [ ] 4. 候補一覧の提示 🛑
- [ ] 5. 選ばれた候補の Issue 作成
```

## 1. 既存 Issue の取得

```bash
gh issue list --state all --limit 200 --json number,title,state,labels
```

候補を作るたびにこの一覧と突き合わせ、同じ内容の Issue があれば候補から外す（open なら「既存 #N」と注記するだけ）。

## 2. 候補の収集

各情報源で見つけたものは、**根拠（ファイル:行・コマンド出力・ドキュメントの節）を必ず控える**。根拠を示せないものは候補にしない。

### roadmap: ロードマップと仕様

- `docs/roadmap.md` の未チェック項目（`- [ ]`）
- `docs/spec.md` に書かれているが未実装の機能。実装済みかどうかはコード（`apps/*/src/features/`）と `git log` で確かめる
- `docs/superpowers/specs/` の設計 doc のうち、対応する plan や実装コミットが無いもの

Pi 実機での検証など **Claude が実行できない項目**は、候補にする場合「手動 QA」と注記し、受け入れ条件に人間が行う確認手順を書く。

### code: コードベース

```bash
git grep -n -E 'TODO|FIXME|HACK|XXX' -- apps packages
npm run lint 2>&1 | tail -40
```

`apps/web` の React コードについては `/react-doctor` の優先度「高」「中」も候補にしてよい。

### deps: 依存パッケージ

```bash
npm outdated --json || true    # 更新がある場合 exit 1 になるため
npm audit --json || true
```

- `npm audit` の high / critical は個別の候補にする。
- メジャーバージョンが上がっているものは、パッケージごとに個別の候補にする（破壊的変更の調査が必要なため）。
- マイナー・パッチの更新はまとめて 1 件の候補にする。

## 3. 候補の整理

- 同じ原因の指摘は 1 件にまとめる。
- 既存 Issue と重複するもの、すでに解決済みのものは除外する。
- 1 件の Issue は「1 回の `/ship-issue` で完了できる大きさ」にする。roadmap の 1 項目が大きすぎる場合は分割案を出す。
- 優先度を付ける：

| 優先度 | 基準 |
|---|---|
| 高 | 機能の不具合、セキュリティ（audit high 以上、spec のセキュリティ必須事項の未達） |
| 中 | roadmap の次フェーズの項目、spec と実装の食い違い、react-doctor の高・中 |
| 低 | lint warning・TODO・マイナー更新・リファクタリング |

## 4. 候補の提示

次の表で提示し、作成する候補をユーザーに選んでもらう（番号で複数選択）。

| # | 優先度 | タイトル案 | ラベル | 情報源 | 根拠 |
|---|---|---|---|---|---|

- タイトル案は Issue のタイトルとしてそのまま使える日本語の一文にする。
- ラベルは既存のもの（`bug` / `enhancement` / `documentation`）から選ぶ。`/ship-issue` はラベルからコミットの型を決めるため。
- 除外した候補（重複・解決済み）と、調べられなかった情報源は表の下に 1 行ずつ記す。

🛑 **STOP: 作成する候補の選択を待つ。** 選ばれなかった候補は作らない。

## 5. Issue の作成

選ばれた候補ごとに作成する。本文は一時ファイルに書いて `--body-file` で渡す（改行やバッククォートを安全に渡すため）：

```bash
gh issue create --label <label> --title "<タイトル>" --body-file <本文ファイル>
```

本文は次の構成にする（`/ship-issue` のフェーズ 1 でそのまま方針を立てられるようにするため）：

```markdown
## 背景
<なぜ必要か・何が問題か>

## 根拠
<ファイル:行・コマンド出力の抜粋・docs/roadmap.md や docs/spec.md の該当節>

## 要件
- <やること>

## 受け入れ条件
- <完了を確認する方法（テスト・コマンド・手動 QA の手順）>
```

作成した Issue の番号と URL を一覧で報告し、着手するときは `/ship-issue <番号>` を使うよう案内する。

# ドキュメントサイト（Astro Starlight）設計書

- 日付: 2026-10-17
- ステータス: ドラフト（承認待ち）

## 目的

新しくプロジェクトに入ったメンバーが「このプロジェクトでは Claude Code の何が使えるか」
（スキル・自動で動く hooks・禁止/許可）を調べられる案内サイトを、このリポジトリの
内容から自動生成して GitHub Pages で公開する。

成功の姿: メンバーが自分のプロジェクトのページを開くだけで、使えるスキルの呼び方と
用途、裏で自動的に動くもの、禁止されている操作が一通りわかる。スキルを追加・変更すれば
手作業なしで次のデプロイに反映される。

## 非目標

- スキル本文（SKILL.md の手順部分）や references/ の表示。本文は GitHub へのリンクで案内する
- 多言語対応（日本語のみ）
- Starlight 標準機能（サイドバー・検索・ダーク/ライト）を超える独自 UI
- 配布ロジック（`deployer/`）の挙動変更

## アンチゴール（動いても失敗とみなすもの）

- サイトの内容が実際に配布される内容とずれる（例: 専用スキルで上書きされた共通スキルが
  両方表示される、settings のマージ結果が配布と違う）
- スキルを追加するたびに手でページを書く必要がある
- 配布先に `site/` 等の無関係なファイルが配られる

## 決定事項

### ユーザーが決めたこと

- 対象読者: 新しくプロジェクトに入ったメンバー。用途は「どんなスキルが使えるか調べる」
- 公開先: GitHub Pages。リポジトリ `j0811s/share-claude` は public 化済み
- 構成: **プロジェクト単位**で区切る。プロジェクトのページで共通＋専用を重ねた結果を見せ、
  各項目に「共通 / 専用」を示す
- スキルの個別ページは**要点カードのみ**（呼び方・いつ使うか・共通/専用・自動起動の可否）＋
  GitHub 上のソースへのリンク
- GitHub 設定:
  - main のブランチ保護: PR 必須、CI 通過必須、force push 禁止、ブランチ削除禁止、
    承認レビューは必須にしない（一人運用で自分の PR を承認できないため）。
    オーナー（admin）には適用しない（`enforce_admins: false`。オーナーは従来どおり main に
    直接 push できる）
  - PR の作成をコラボレーター限定にする
  - Issue の作成をコラボレーター限定にする

### Claude の判断で決めたこと（ユーザーに提示済み、異論なし）

- 置き場所: このリポジトリの `site/`（Astro + Starlight の独立した npm プロジェクト）
- データの作り方: **Python のエクスポータ**（`bin/export-docs-data.py`、標準ライブラリのみ）が
  `deployer` の重ね合わせ規則・`merge_settings` をそのまま使って、プロジェクトごとの
  「配布される結果」を JSON に書き出す。Astro はその JSON を読んでページを生成する。
  マージ規則を TypeScript に二重実装しないため（アンチゴール 1 の回避）
- 同名スキルは配布と同じく project 側が勝つ（表示上は「専用」）
- hooks ページ: settings.json（マージ後）の `hooks` から「いつ（イベント＋matcher）→ 何を
  （スクリプト名）」の表を作る。スクリプト冒頭のコメント行があれば説明として使い、
  なければスクリプトへの GitHub リンクのみ
- 禁止・許可ページ: マージ後 settings.json の `permissions.deny / ask / allow` を
  「禁止 / 実行前に確認 / 確認なしで実行」の表にする
- CLAUDE.md・rules: プロジェクトのトップページから GitHub 上のファイルへリンクする。
  rules が空のプロジェクトでは rules の項目を出さない
- 手書きページは「はじめに」（サイトの見方、スキルの呼び方 `/name args`、
  共通/専用の意味）だけ
- デプロイ: main への push で GitHub Actions がエクスポート → ビルド → Pages へデプロイ。
  PR では `python3 -m unittest discover test` とサイトのビルドを CI で実行し、これを
  ブランチ保護の必須チェックにする
- 表示言語は日本語
- GitHub 設定は Claude が `gh api` で適用する（ユーザー了承済み）。順序: ワークフローを含む
  ブランチを main に入れて CI を一度走らせる → Pages のソースを「GitHub Actions」に切り替える →
  そのチェック名を必須にしてブランチ保護を入れる。PR/Issue のコラボレーター限定は恒久的な
  リポジトリ設定（2026-02 / 2026-06 の GitHub Changelog）。API で設定できない場合は
  Settings 画面での手順をユーザーに渡す
- 「共通 / 専用」はスキル・hooks・permissions の各行に付ける。hooks と permissions は
  common の settings.json に同じ要素があれば「共通」、なければ「専用」と判定する
  （配布時の連結は重複を除くので、両方にあっても実体は1つ）
- hooks の説明文: 配布対象の2スクリプトの shebang 直後に `# 説明: ...` の1行コメントを追加する
  （動作は変わらない）。エクスポータは shebang の次から連続する `#` 行を説明として読む

## 構成

```
share-claude/
├── bin/export-docs-data.py        # 新規: プロジェクトごとの配布結果を JSON に出力
├── deployer/                       # 既存（必要なら読み取り用の関数を公開する程度）
├── site/                           # 新規: Astro Starlight
│   ├── package.json
│   ├── astro.config.mjs            # base: '/share-claude'
│   └── src/
│       ├── content/docs/index.mdx  # はじめに（手書き）
│       └── ...                     # JSON からページを生成するルート/ローダ
├── test/test_export_docs.py        # 新規: エクスポータのテスト（unittest）
└── .github/workflows/
    ├── ci.yml                      # PR: unittest + サイトビルド
    └── pages.yml                   # main push: ビルド + Pages デプロイ
```

`deployer` は `common/` と `project/<name>/` しか読まないため、`site/` が配布される心配はない。

## データ（エクスポータの出力）

プロジェクトごとに次を含む JSON（形は実装者に任せる）:

- スキル一覧: `name`, `description`, `argument-hint`（あれば）,
  `disable-model-invocation`（あれば）, 出どころ（common / project）, ソースの相対パス
- hooks: マージ後 settings の `hooks` の各エントリ（イベント, matcher, command）と、
  command から特定できるスクリプトの相対パス・冒頭コメント
- permissions: マージ後の deny / ask / allow
- CLAUDE.md・rules ファイルの相対パス（存在するもののみ）

プロジェクト一覧は `project/` 直下のディレクトリから取る（`projects.json` はローカル専用で
gitignore されているため使わない）。

frontmatter は単純な `key: value` 行（値がダブルクォートで囲まれる場合あり）だけを扱う
最小パーサで読む。PyYAML は使わない。

## ページ

- `/` はじめに
- `/<project>/` プロジェクトのトップ: スキル一覧表（呼び方・概要・共通/専用・手動のみ）、
  hooks と禁止・許可へのリンク、CLAUDE.md / rules への GitHub リンク
- `/<project>/skills/<name>/` スキルの要点カード
- `/<project>/hooks/` 自動で動くもの
- `/<project>/permissions/` 禁止・許可

サイドバー: はじめに → プロジェクトごとのグループ（トップ / スキル各種 / hooks / 禁止・許可）。

## 実装者に任せること

- Astro にページを生やす方法（content loader / 動的ルート / ビルド前の MDX 生成 など）
- JSON のスキーマ詳細と出力先
- 見た目の細部（バッジの表現など）
- Node / Astro / Starlight のバージョン（現行安定版）

## 制約

- Python 側は 3.9 標準ライブラリのみ、テストは unittest（既存ルール）
- 配布先パスに `Path.resolve()` を使わない（既存ルール。エクスポータは配布先を扱わないが踏襲）
- `CLAUDE.md`（リポジトリ自身向け）の構成欄に `site/` とエクスポータを追記する

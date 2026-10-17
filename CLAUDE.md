# CLAUDE.md

各プロジェクトへ Claude Code の設定を配信するリポジトリ。

## 構成

- `common/` — 全プロジェクト共通の設定（skills / hooks / settings.json）
- `project/<name>/` — プロジェクト固有の設定（skills / hooks / rules / settings.json / CLAUDE.md）
- `deployer/` — 配布ロジック
- `bin/deploy.py` — CLI エントリポイント
- `bin/export-docs-data.py` — ドキュメントサイト用に配布結果を JSON へ書き出す
- `site/` — Astro + Starlight のドキュメントサイト（Node プロジェクト）

## このファイルについて

このファイルは **share-claude 自身**を編集するときの指示であり、配布されない。
配布されるテンプレートは `project/<name>/CLAUDE.md` の方。

## 開発ルール

- Python 3.9（`/usr/bin/python3`）の標準ライブラリのみを使う。外部依存を追加しない。
  この縛りは `deployer/` と `bin/` が対象。`site/` は Node プロジェクトなので対象外
- テストは `unittest`。`python3 -m unittest discover test` で実行する
- 配布先の `.claude/` 全体をミラーしてはならない。所有するのは
  `skills/` `hooks/` `rules/` の3ディレクトリと `settings.json` `CLAUDE.md` の2ファイルのみ
- 配布先パスに `Path.resolve()` を使わない（macOS の `/var` シンボリックリンクでテストが壊れる）

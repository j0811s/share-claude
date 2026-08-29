# CLAUDE設定配信システム 設計書

- 日付: 2026-08-28
- ステータス: 承認済み（実装計画待ち）

## 目的

複数のプロジェクトリポジトリに対して、Claude Code の設定（skills / hooks / rules / settings.json / CLAUDE.md）を
このリポジトリ（share-claude）から一元的に配信する。

共通設定は一箇所で管理し、プロジェクト固有の設定はそれに重ねる。
配信は Push 型 — share-claude 側でコマンドを実行し、配布先へ書き込みに行く。

## 非目標

- Pull 型（配布先から取得する仕組み）
- 双方向同期（配布先での編集を share-claude に戻す）
- 外部依存（jq、pytest、PyYAML 等）の導入
- 配布先が git リポジトリであることの強制

## リポジトリ構成

```
share-claude/
├── CLAUDE.md                  # このリポジトリ自身への指示（配布物ではない）
├── README.md
├── .gitignore                 # projects.json を除外
├── projects.example.json      # 配布先マッピングの雛形（コミットする）
├── projects.json              # 配布先マッピング（gitignore、各マシンで作る）
├── bin/
│   └── deploy.py              # CLI エントリポイント
├── deployer/                  # ロジック本体（Python パッケージ）
│   ├── __init__.py
│   ├── config.py              # projects.json のロードと検証
│   ├── merge.py               # settings.json のマージポリシー
│   ├── plan.py                # build_plan: ソース群 → アクション列
│   └── apply.py               # apply_plan: アクション列 → FS / dry-run 表示
├── common/
│   ├── skills/
│   ├── hooks/
│   └── settings.json
├── project/
│   └── portfolio/
│       ├── CLAUDE.md
│       ├── skills/
│       ├── hooks/
│       ├── rules/
│       └── settings.json
├── test/
│   ├── test_config.py
│   ├── test_merge.py
│   ├── test_plan.py
│   └── test_smoke.py
└── docs/superpowers/specs/
```

### CLAUDE.md の2つの役割

紛らわしいので明示する。

| パス | 役割 |
|---|---|
| `share-claude/CLAUDE.md` | このリポジトリを編集する際の Claude への指示。**配布されない** |
| `share-claude/project/<name>/CLAUDE.md` | 配布されるテンプレート本体。`<target>/CLAUDE.md` になる |

### common/rules を置かない理由

共通ルールは既にユーザのグローバル設定 `~/.claude/CLAUDE.md` に存在し、全プロジェクトで自動的に読み込まれる。
share-claude が共通ルールを重複して配布する必要はない。
rules はプロジェクト固有のもの（`project/<name>/rules/`）のみを扱う。

初期スキャフォールドに含まれる `common/rules/.gitkeep` は削除する（`git rm --cached` + ディレクトリ削除）。

## 配布先マッピング

| ソース | 配布先 | 同期方式 |
|---|---|---|
| `common/skills/` + `project/<n>/skills/` | `<target>/.claude/skills/` | ミラー（不要ファイル削除あり） |
| `common/hooks/` + `project/<n>/hooks/` | `<target>/.claude/hooks/` | ミラー（不要ファイル削除あり） |
| `project/<n>/rules/` | `<target>/.claude/rules/` | ミラー（不要ファイル削除あり） |
| `common/settings.json` ⊕ `project/<n>/settings.json` | `<target>/.claude/settings.json` | 単体書き込み |
| `project/<n>/CLAUDE.md` | `<target>/CLAUDE.md` | 単体コピー |

同名ファイルが common と project の両方にある場合、**project 側が勝つ**。

### 所有範囲

`<target>/.claude/` **全体**をミラーしてはならない。配布先固有のファイル（`settings.local.json` 等）を削除してしまうため。

share-claude が所有し、不要ファイル削除まで行うのは以下の3ディレクトリのみ：

- `<target>/.claude/skills/`
- `<target>/.claude/hooks/`
- `<target>/.claude/rules/`

以下の2ファイルは上書きするが、周囲のファイルには触れない：

- `<target>/.claude/settings.json`
- `<target>/CLAUDE.md`

`settings.json` は share-claude が正となる全上書きのため、配布先固有の設定は `settings.local.json` に置く。
これが配布先側のエスケープハッチとなる。

### 「未管理」と「管理下だが空」の区別

ミラー対象ディレクトリについて：

- ソース側のディレクトリが **common / project のどちらにも存在しない** → そのディレクトリは未管理。配布先に一切触れない
- ソース側に存在する（中身が空でも） → 管理下。配布先を空にする方向で同期する

この規則により、`project/<n>/rules/` を作っていないプロジェクトの `<target>/.claude/rules/` を誤って削除することがない。

## projects.json

プロジェクト名から配布先の絶対パスへのマッピング。

```json
{
  "portfolio": "~/github/portfolio"
}
```

- `~` は `os.path.expanduser` で展開する
- 相対パスは share-claude リポジトリルートからの相対として解決する

### git 管理

`projects.json` は **gitignore する**。配布先パスはマシンやユーザごとに異なるローカルな設定であり、
リポジトリが持つべき内容ではないため。

代わりに `projects.example.json` を同じ形式でコミットし、初回セットアップ時にこれをコピーして使う。

```
cp projects.example.json projects.json
```

`projects.example.json` の中身は、実在のパスを含まないプレースホルダとする。

```json
{
  "portfolio": "~/path/to/portfolio"
}
```

## settings.json のマージ

### なぜマージするか

common と project を重ねることがこのリポジトリの存在理由であり、hooks は配布する3種の1つ。
丸ごと差し替え方式にすると「hook を1つ追加したいだけ」のプロジェクトが common の settings.json 全体を
複製する必要が生じ、このリポジトリが解消するはずの重複が発生する。

### 素朴な再帰マージが不可な理由

再帰的な `dict.update()` は配列を**置換**する。
project 側に hooks を1つ書いただけで common の `permissions.allow` が全消滅し、
丸ごと差し替えより悪い結果になる。よってキー形状ごとにポリシーを定める。

### マージポリシー

`merge(base, overlay)` — base = common、overlay = project。

| キーパス | ポリシー |
|---|---|
| `permissions.allow` / `permissions.deny` / `permissions.ask` | リスト連結。base が先。完全一致で重複除去、出現順を保持 |
| `hooks.<EventName>`（任意のイベント名） | リスト連結。base が先。完全一致で重複除去（`json.dumps(x, sort_keys=True)` で比較） |
| 上記以外の dict（`enabledPlugins`, `extraKnownMarketplaces`, `permissions` 自体 等） | 再帰マージ。同一キーの葉は overlay が勝つ |
| 上記以外の list（未知のキー） | overlay が base を置換する |
| スカラー（`model`, `effortLevel`, `tui`, `permissions.defaultMode` 等） | overlay が勝つ |

- base にのみ存在するキーはそのまま残る
- overlay にのみ存在するキーはそのまま追加される
- 型が食い違う場合（base が dict で overlay が list 等）は overlay が勝つ

### 片側しか存在しない場合

- 両方存在しない → `<target>/.claude/settings.json` に触れない
- 片方のみ存在 → そのファイルの内容をそのまま書き出す
- 両方存在 → 上記ポリシーでマージ

### 配布される settings.json の hook パス規約

配布先の settings.json 内で hook スクリプトを参照する際は `$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.sh` を使う。
グローバル設定で使われている絶対パス（`/Users/sato/.claude/hooks/...`）は配布物では機能しない。

## 処理フロー

### plan / apply の分離

`build_plan()` はファイルシステムに一切書き込まず、アクション列を返す。
`apply_plan()` がそれを実行する。dry-run は「別のコードパス」ではなく「plan を表示するだけ」になる。

```python
Action = namedtuple("Action", ["kind", "dst", "src", "content", "status"])
```

| kind | 意味 | src | content |
|---|---|---|---|
| `copy` | ファイルをコピー | ソースパス | None |
| `write` | 生成した内容を書き込む（マージ済み settings.json） | None | JSON 文字列 |
| `delete` | 配布先の不要ファイルを削除 | None | None |

`status` は表示用: `new` / `update` / `unchanged` / `delete`。
`build_plan` は配布先を**読んで** status を判定する（読み取りのみ、書き込みなし）。

### build_plan の手順

1. `projects.json` から `<name>` → 配布先パスを解決
2. ミラー対象3ディレクトリそれぞれについて:
   a. 下表のソースディレクトリを順に**再帰的に**走査し、相対パスをキーとしてファイルを収集する。
      後のソース（project）が同一相対パスを上書きする
   b. 除外セットに該当するファイルを落とす
   c. 各ファイルに `copy` アクションを生成
   d. 配布先を再帰的に走査し、上記で配置しないファイルに `delete` アクションを生成
3. settings.json を解決（両方 / 片方 / なし）し、必要なら `write` アクションを生成
4. `project/<n>/CLAUDE.md` があれば `copy` アクションを生成

#### ミラー対象ディレクトリのソース定義

| 配布先 | ソース（この順に重ねる） |
|---|---|
| `<target>/.claude/skills/` | `common/skills/`, `project/<n>/skills/` |
| `<target>/.claude/hooks/` | `common/hooks/`, `project/<n>/hooks/` |
| `<target>/.claude/rules/` | `project/<n>/rules/` のみ |

走査は再帰的に行い、ディレクトリ構造を保持する。
skills は Claude Code の仕様上 `<skill-name>/SKILL.md` のようなサブディレクトリ構造を持つため、
フラットなファイル列挙では不十分である。

#### 空になったディレクトリの扱い

`delete` によって配布先のディレクトリが空になった場合、そのディレクトリ自体も削除する
（所有する3ディレクトリの内側に限る。3ディレクトリ自体は空になっても残す）。
リポジトリから削除したスキルのディレクトリが配布先に残り続けるのを防ぐため。

### 除外セット

`.gitkeep`, `.DS_Store`

現状すべてのディレクトリの唯一の中身が `.gitkeep` であり、素直にミラーすると
全配布先に `.claude/skills/.gitkeep` が着弾する。plan 構築時点で除外する。

### apply_plan の手順

- dry-run 時: `status != unchanged` のアクションのみ表示し、末尾にサマリ（変更 N 件 / 未変更 M 件）を出す
- 実行時: `unchanged` は no-op、それ以外を実行。必要な親ディレクトリは作成する
- ファイルコピーは `shutil.copy2` を使う（モードを保持する。hook はシェルスクリプトのため実行ビットの保持が必須）

## CLI

```
bin/deploy.py <project-name>            # 単一プロジェクトへ配布
bin/deploy.py --all                     # projects.json の全プロジェクトへ配布
bin/deploy.py --dry-run <project-name>  # 差分を表示するのみ
bin/deploy.py --dry-run --all
```

`bin/deploy.py` は薄いエントリポイント（argparse とリポジトリルートの `sys.path` 追加のみ）とし、
ロジックは `deployer/` パッケージに置く。

### エラー処理（いずれも exit code 1 で停止）

- `projects.json` が存在しない
  → gitignore されており初回は存在しないのが正常なため、
  `cp projects.example.json projects.json` を促すメッセージを出す
- `projects.json` が JSON として不正
- 指定されたプロジェクト名が `projects.json` に無い（利用可能な名前を列挙して表示）
- 配布先パスが存在しない
- 配布先パスがディレクトリでない
- `common/settings.json` または `project/<n>/settings.json` が JSON として不正

`--all` 実行時に個別プロジェクトが失敗した場合は、そこで停止する（部分適用状態を分かりにくくしないため）。

## 実行環境

- `/usr/bin/python3` (Python 3.9.6, macOS Xcode Command Line Tools 管理)
- 標準ライブラリのみ（`json`, `pathlib`, `shutil`, `filecmp`, `argparse`, `unittest`）
- `tomllib` は 3.11+ のため使用不可 → 設定ファイルは JSON

Xcode CLT 管理の Python に依存する点は、個人用ツールとしては許容範囲と判断した。

## テスト

`unittest`（標準ライブラリ）を使う。実行は リポジトリルートで `python3 -m unittest discover test`。

### test_config.py — projects.json の解決と検証

1. `~` を含むパスが展開される
2. 相対パスがリポジトリルート起点で解決される
3. `projects.json` が存在しない場合、`projects.example.json` のコピーを促すメッセージを含むエラーになる
4. JSON として不正な場合にエラーになる
5. 存在しないプロジェクト名を指定した場合、利用可能な名前を列挙したエラーになる
6. 配布先パスが存在しない / ディレクトリでない場合にエラーになる

### test_merge.py — マージポリシーの検証

ポリシー表の各行に対応するテストを持つ。

1. `permissions.allow` が連結され、重複が除去され、base 優先の順序が保たれる
2. `hooks.SessionStart` が連結され、base の要素が先に来る
3. `hooks` の完全一致重複が除去される
4. `enabledPlugins` が再帰マージされ、同一キーは project が勝つ
5. スカラー（`model`）は project が勝つ
6. 未知の配列は project が base を置換する
7. base にのみ存在するキーが残る
8. overlay にのみ存在するキーが追加される
9. 片側が空 dict の場合、もう片方がそのまま返る

### test_plan.py — plan 構築の検証

一時ディレクトリにフィクスチャのリポジトリ構造と配布先を作って検証する。

1. `.gitkeep` / `.DS_Store` がアクションに含まれない
2. common と project に同名ファイルがある場合、project 側がソースになる
3. 配布先にのみ存在するファイルに `delete` アクションが生成される
4. ソース側にディレクトリが存在しない場合、その配布先ディレクトリにアクションが生成されない（未管理）
5. 内容が同一のファイルは `unchanged` になる
6. `<target>/.claude/settings.local.json` に対して `delete` が生成されない
7. サブディレクトリを持つ skill（`<skill-name>/SKILL.md`）が構造を保ったままコピーされる
8. 配布先で空になるディレクトリに削除アクションが生成される

### test_smoke.py — エンドツーエンド検証

1. 一連の apply 後、期待されるツリー構造が配布先に出来ている
2. hook スクリプトの実行ビットが保持されている
3. `settings.local.json` が生き残っている
4. 除外セットのファイルが配布先に1つも存在しない
5. dry-run 実行後に配布先が一切変化していない

## 実装順序（実装計画で詳細化する）

1. `deployer/merge.py` とそのテスト（最も規則が込み入っており、単体で完結する）
2. `deployer/config.py` とそのテスト
3. `deployer/plan.py` とそのテスト
4. `deployer/apply.py`
5. `bin/deploy.py`（CLI 結線）
6. `test/test_smoke.py`
7. `.gitignore`（`projects.json` を除外）、`projects.example.json`、`README.md`（セットアップ手順）の整備

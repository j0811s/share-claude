---
name: review-api-route
description: API の経路（src/ の Hono の app.get/post/patch/delete）を足したり、パス・メソッド・権限を変えたりしたときのレビュー。コミットや PR の前に、本番だけで起きる食い違い（API Gateway の認証の登録漏れなど）を一つずつ確かめる。
---

API の経路を足した・変えたときに、テストでは見つからず本番で初めて壊れるものを確かめる。対象: $ARGUMENTS（省略時は `git diff main...HEAD` で足した・変えた経路）

## なぜ要るか

テスト用のアプリ（`test/fakes/test-app.ts`）とローカルの API（`src/local.ts`）は、Hono のアプリを直接呼ぶ。本番だけは、その前に CloudFront（`/api/*`）と API Gateway（JWT の認可）がある。ここの登録が漏れても単体テスト・E2E・ローカルではすべて通る。

実際にあった例: ゴミ箱の 3 つの経路を API Gateway の JWT のルートに足し忘れた。認証なしの予備の経路（`ANY /{proxy+}`）に落ちて 401 になり、画面は「ログインが切れた」とみなしてログインへ移った。設定タブを開くたびにログインを求められ、ループした。

## 手順

1. 足した・変えた経路を一覧にする: `git diff main...HEAD -- src` から、`app.get/post/put/patch/delete("...")` を拾う。メソッドとパスを `METHOD /api/...` の形で書き出す（各ルーターは `/api` の下に付く。`src/app.ts`）。
2. 下の表を、経路ごとに一つずつ確かめる。確かめた根拠（ファイルと行、走らせたコマンド）を添えて、OK / 直した / 該当なし で報告する。推測で OK にしない。
3. 直したら、`/verify` と同じ検査をすべて通す。

| # | 確かめること | どこを見るか |
|---|---|---|
| 1 | **API Gateway の JWT のルートに載っているか。** ログインが要る経路は、`protectedRoutes` に、同じメソッド（か `ANY`）とパスの形（`{id}`・`{proxy+}`）で入っていること。入っていないと 401 になる | `infra/media-api-stack.ts` の `protectedRoutes`。`npx vitest run test/infra/media-api-stack.test.ts -t "JWT のルートに載っている"` が通ること |
| 2 | **ログインなしで届くべき経路が、JWT のルートに入っていないか。** トークンが無いときに呼ぶもの（例: ログアウト後の `DELETE /api/media-cookie`）は、JWT のルートに入れると届かない | 同じテストの `publicRoutes` と、`DELETE /api/media-cookie` のテスト |
| 3 | **アプリ側の認可。** `loggedIn`・`memberOnly`・`adminOnly` のどれを付けたか。持ち主の判定（`canEditMedia` など）を、ストレージや DB に触れる前にしているか。閲覧者・他人・未ログインで 403/401 になるテストがあるか | 経路の定義と、`test/` のテスト |
| 4 | **入力の検証。** id は `requireValidId`、本文と検索パラメータは zod（`validate`）で確かめているか。不正なカーソルは 500 ではなく 400 か | 経路の定義。`InvalidCursorError` の扱い |
| 5 | **応答のキャッシュ。** ログインが要る応答に `Cache-Control: private, no-store`（`noStore`）が付くか | 経路の定義 |
| 6 | **型の共有と互換。** 応答と本文の型を `src/contract.ts` に置き、画面はそれを使っているか。既存の経路の応答の形を変えるなら、デプロイの途中で古い画面が新しい API を呼んでも壊れないか（項目は足すだけ、省略時は今までの振る舞い） | `src/contract.ts`、`web/src/api/queries.ts` |
| 7 | **画面からの呼び出し。** `apiGet`・`apiSend` に `auth: true` を付けているか（401 でログインに移る仕組みはこれに付く）。共通の画面（設定タブ・枠）から呼ぶなら、そこが開くたびに呼ばれることを分かったうえか | `web/src/api/queries.ts`、呼び出す部品 |
| 8 | **画面のテストの偽の応答。** msw は未処理の要求で落ちるので、共通の画面から呼ぶ経路は `web/src/admin/test-helpers.tsx` の既定の応答にも足したか。E2E の偽のバックエンド（`web/e2e/fixtures.ts`）にも足したか（足さないと 404 になり、E2E は外への通信として落ちる） | 各ファイル |
| 9 | **Lambda の権限と時間。** 新しく触る S3 の操作・接頭辞、DynamoDB、ほかのサービスの権限を API の関数に足したか。API の Lambda は 25 秒で切れる。大きなファイルを読む・書く処理が収まるか | `infra/media-api-stack.ts` の `fn.addToRolePolicy`、`test/infra` の権限のテスト |
| 10 | **CloudFront。** `/api/*` 以外のパスを足していないか（足すなら CloudFront の振り分けも要る）。`/media/*` のような配信のパスに関わるなら、キャッシュの無効化を考えたか | `infra/media-api-stack.ts` の `additionalBehaviors` |
| 11 | **本番との差分。** `cdk diff` で、ルート・統合・Lambda の呼び出し権限が経路の数だけ増えているか。作り直し・削除が無いか | `npx cdk diff MediaApiStack -c budgetEmail=... -c appUrl=...`（認証が切れていればユーザーに `aws sso login` を頼む） |
| 12 | **文書。** README の「API 一覧」に、メソッド・パス・誰が使えるか・応答を書いたか。構成が変わるなら「このアプリについて」も直したか | `README.md`、`web/src/admin/about/content.ts` |

## デプロイ後の確かめ方

- 本番の API のアクセスログ（ロググループ `MediaApiStack-ApiAccessLogs...`）で、足した経路の `routeKey` が `ANY /{proxy+}` ではなく、足したルート（例: `GET /api/trash`）になっていること、`status` が 401 でないことを見る（読み取りだけ）:
  `aws logs filter-log-events --region ap-northeast-1 --log-group-name <ロググループ> --start-time <ミリ秒> --filter-pattern '"<パスの一部>"'`
- ユーザーには、その経路を呼ぶ画面を開いて、ログインに戻されないことを確かめてもらう。

## 報告の形

経路ごとに、表の 12 項目を「OK（根拠）/ 直した（何を）/ 該当なし（理由）」で並べる。直したものがあれば、最後に検査の結果（終了コード）を書く。

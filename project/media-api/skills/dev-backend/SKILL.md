---
name: dev-backend
description: API（src/ の Hono on Lambda）・動画の処理・インフラ（infra/ の CDK）を作る・直すときの手順。API の追加や変更、DynamoDB・S3・CloudFront の設定変更、本番データの作り直しで使う。
---

API とインフラの変更を、ブランチを切ってから本番に出るまで進める手順。依頼: $ARGUMENTS

## 1. 始める前に

- main にいたら、内容に合うブランチ（`feature/...`・`fix/...`・`chore/...`・`ci/...` など）を切る。main に直接コミットしない。版はこの名前で自動で決まる（`feature/` は真ん中、`fix/` は右端を上げ、`docs/`・`chore/`・`test/`・`ci/` は上げない。ほかの名前の PR は CI で落ちる。`/ship`・README「バージョン」）ので、中身に合わせる。`package.json` の version は触らない。
- 新しい機能や振る舞いの変更なら、作る前に何を作るかをユーザーと決める。本番稼働中なので、今あるデータ（DynamoDB の記録・S3 の `media/`）と、デプロイの途中で古い画面と新しい API が混ざる時間をどう扱うかも決めておく。
- 置き場所: API の入口は `src/app.ts`、機能ごとに `src/media/`・`src/folders/`・`src/catalog/`（DynamoDB）・`src/users/`（Cognito）・`src/video/`（動画の Lambda）。API と画面の型は `src/contract.ts`。インフラは `infra/`（`media-api-stack.ts` が本体）。
- 不具合なら、直す前に原因を確かめる。本番のログは読み取りの AWS CLI（`aws logs`・`describe`・`list`、`s3 cp` で scratchpad に落とす）で見てよい。

## 2. 作る（テストから）

- 先に失敗するテストを書き、落ちるのを見てから直す。テストは `test/` に、`src/` と同じ分け方で置く。テスト名は日本語。
- AWS に触れる部分は差し替えのための偽物を使う（`test/fakes/`。`test-app.ts` でアプリを組む）。単体テストは AWS も Docker も要らないこと。
- DynamoDB のクエリを変えたら、結合テストも走らせる: `npm run db:local && DYNAMODB_ENDPOINT=http://localhost:8000 npm run test:integration`（Docker が要る）。
- 新しい API の経路を足したら、`infra/media-api-stack.ts` の `protectedRoutes`（JWT のルート）にも足す。足し忘れると認証なしの予備の経路に落ちて 401 になり、画面はログインがループする（`test/infra/media-api-stack.test.ts` が見張る）。 経路を足した・変えたら、PR の前に `/review-api-route` で確かめる。
- API の形を変えたら `src/contract.ts` を直し、`web/` 側の型検査とテストも通す（画面も直すなら dev-frontend の手順）。古い画面が新しい API を呼んでも壊れないようにする（項目は足すだけにする、省略時は今までの振る舞い、など）。
- 守っていること（README「設計で工夫した点」）を崩さない: 確かめた版（ETag・VersionId）だけを公開する、メタデータを除いたものだけを `media/` に置く、`/media` は署名付き Cookie がないと見られない、権限は管理者・編集者・閲覧者で分ける。
- 動画の処理を変えたら、`test/video/video.ffmpeg.test.ts` をローカルの ffmpeg で走らせる（無いと飛ばされるが、CI では必須）。
- インフラを変えたら `test/infra/` のテストを直し、`npx cdk diff MediaApiStack -c budgetEmail=<メール> -c appUrl=<アプリの URL>` で差分が意図どおりかを見る（値は README「デプロイ手順」。`build/ffmpeg-layer` が要る）。置き換え（replace）や削除が出たら、進める前にユーザーに伝える。認証が切れていたら、ユーザーに `aws sso login` を頼む。

## 3. 本番への書き込み

- 本番のデータや設定への書き込み（DynamoDB・S3 の書き換え、`scripts/` の `--apply`、CloudFront の無効化、`cdk deploy`）は、こちらから実行しない。コマンドを示して、ユーザーに `! <コマンド>` で実行してもらうか、「実行して」と明示されてから実行する。
- データを作り直すスクリプトは、既定を数えるだけ（dry-run）にし、`--apply` で書き込む形にする（例: `scripts/regenerate-display.ts`）。実行の前後で件数を確かめる。
- 表示用画像の作り方を変えたら `src/media/routes.ts` の `DISPLAY_VERSION` を上げる（`/media/*` は 1 年キャッシュ）。

## 4. 仕上げ

- 機能・API・構成を変えたら、README の関係する箇所（「API 一覧」「使っている AWS サービス」「設計で工夫した点」など）を同じ PR で直す。構成や実測の数字を変えたら「このアプリについて」（`web/src/admin/about/content.ts`）も直す。
- `npm run fix` のあと、/verify と同じ検査を全部通す（成否は終了コードで見る）。
- /ship で PR を作り、CI を見届ける。マージはユーザーがする。main へのマージで本番に自動デプロイされるので、マージ後は `/ship merged` でデプロイを見届け、本番で確かめてほしいことを手順で書く。

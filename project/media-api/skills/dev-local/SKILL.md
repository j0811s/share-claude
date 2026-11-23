---
name: dev-local
description: ローカル開発環境（DynamoDB Local・ローカルの API・Vite の開発サーバー）を起動し、止めて片付ける手順。ローカルで API や画面を動かしたい、手元で確かめたいときに使う。
---

ローカルで API と画面を動かす手順。依頼: $ARGUMENTS

S3 は本番バケットを共用する（ローカルの代替はない）。ローカルで完了通知した写真は本番の `media/` に置かれ、本番にログインできる人にも見える。DynamoDB Local は `-inMemory` なので、止めると記録が消え、消せないファイルが S3 に残る。この 2 点を、起動の前にユーザーへ一言伝える。

## 1. 前提を確かめる

- Node.js 24 以上（`node -v`）、Docker が動いている（`docker info` の終了コード）。
- AWS の認証情報: `aws sts get-caller-identity` が通ること。通らなければユーザーに `aws sso login` を頼む（こちらでは実行しない）。
- 依存: `node_modules` と `web/node_modules` がなければ `npm ci` と `npm --prefix web ci`。
- `.env` は使わない・作らない。環境変数はコマンドの前にインラインで渡す。

## 2. 起動する（それぞれバックグラウンドで）

1. DynamoDB Local とテーブル: `npm run db:local`（`docker compose up -d` で `localhost:8000`、テーブル `media-local` を作る。作成済みなら飛ばされる）。
2. バケット名を本番スタックの出力から読む（読み取りだけ）:
   `aws cloudformation describe-stacks --stack-name MediaApiStack --region ap-northeast-1 --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text`
3. API（`http://127.0.0.1:3000`）:
   `TABLE_NAME=media-local DYNAMODB_ENDPOINT=http://localhost:8000 BUCKET_NAME=<2 の値> npm run dev`
   - `DYNAMODB_ENDPOINT` がローカルを指していないと起動しない（本番テーブルを守るため）。
   - `Authorization: Bearer dev` で管理者、`Bearer dev-member` で編集者として扱われる（ローカルだけ）。動作確認は `requests.http`（README「requests.http の使い方」）か、`Bearer dev` を付けた要求で。
4. 画面（`http://localhost:5173`）: `npm run web:dev`。`/api` と `/media` は `127.0.0.1:3000` に中継される。
   - 管理画面のログインを試すときだけ、`web/public/config.json`（Git 管理外）が要る。値は本番スタックの出力 `UserPoolId`・`UserPoolClientId` と `"region": "ap-northeast-1"`。無ければ作ってよいかユーザーに確かめる。
   - ログインなしで画面の見た目だけ見たいなら、dev-frontend の「見た目を確かめる」の一時の確認ページを使う方が早い。

起動したら、それぞれの出力に待ち受けの行が出たことを確かめてから、ユーザーに URL を伝える。

## 3. 止めて片付ける

1. ローカルで写真・動画を送ったなら、DynamoDB Local を止める前に API の `DELETE` で消す（止めた後では API から消せず、本番の S3 に残る。残ったら S3 から手で消すことになるので、ユーザーに伝える）。
2. API と Vite を止める（バックグラウンドのタスクを止める）。
3. `docker compose down` で DynamoDB Local を止める。
4. `git status` で、`web/public/config.json` や確認用のファイルがコミットに入っていないことを確かめる。

## うまくいかないとき

- `環境変数が不正です: ...`: 名前が出た変数を渡し忘れている（値は表示されない）。
- 3000・5173・8000 番が使用中: 前に起動したものが残っていないか確かめ、残っていれば止める。
- S3 で `AccessDenied` や認証のエラー: SSO の期限切れ。ユーザーに `aws sso login` を頼む。

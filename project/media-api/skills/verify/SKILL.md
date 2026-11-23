---
name: verify
description: CI と同じ検査（API と web の check・typecheck・test・build と画面の E2E）を順に走らせ、終了コードで成否を報告する。コミット・PR の前や、変更が通るか確かめたいときに使う。
---

リポジトリのルートで、次を 1 つずつ実行する。各コマンドの成否は終了コードで判断し、出力の最後の行だけで判断しない。

1. `npm run check`
2. `npm run typecheck`
3. `npm test`
4. `npm --prefix web run typecheck`
5. `npm --prefix web test`
6. `npm --prefix web run build`
7. `npm --prefix web run e2e`（Playwright。ビルドしてから Chromium と WebKit で走らせる。ローカルで 10 秒ほど）

- 失敗したら、そこで止めずに残りも実行し、最後に失敗した項目とその出力の要点をまとめる。
- `npm run check` の失敗が整形だけなら、`npm run fix` で直してからもう一度 check する。
- DynamoDB の結合テスト（`npm run test:integration`）は CI の `integration` ジョブで走る。Docker が動いていれば `npm run db:local && DYNAMODB_ENDPOINT=http://localhost:8000 npm run test:integration` も走らせ、動いていなければ「飛ばした」と書く。
- ffmpeg がローカルに無いと `test/video/video.ffmpeg.test.ts` は飛ばされる。飛ばされた場合はそのことを報告に書く（CI では必須）。
- 7 でブラウザが無いと言われたら、`npm --prefix web exec -- playwright install chromium webkit` で入れてからやり直す（入れられなければ「飛ばした」と書く）。
- `tsc -b` などで `web/tsconfig.tsbuildinfo` ができたら消す（コミットしない）。

報告は日本語で、項目ごとに 成功 / 失敗 / 飛ばした を 1 行ずつ。

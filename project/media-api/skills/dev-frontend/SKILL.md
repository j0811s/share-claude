---
name: dev-frontend
description: 画面（web/ の React + Vite）を作る・直すときの手順。ギャラリー・管理画面・エラーページの変更、見た目の調整、画面の不具合の修正で使う。
---

画面（`web/`）の変更を、ブランチを切ってから PR を作るまで進める手順。依頼: $ARGUMENTS

## 1. 始める前に

- main にいたら、内容に合うブランチ（`feature/...`・`fix/...` など）を切る。main に直接コミットしない。版はこの名前で自動で決まる（`feature/` は真ん中、`fix/` は右端を上げ、`docs/`・`chore/`・`test/`・`ci/` は上げない。ほかの名前の PR は CI で落ちる。`/ship`・README「バージョン」）ので、中身に合わせる。`package.json` の version は触らない。
- 新しい機能や振る舞いの変更なら、作る前に何を作るかをユーザーと決める（見た目なら、どこに何を置くかを短く確かめる）。小さな見た目の直しは、そのまま進めてよい。
- 置き場所: ギャラリーは `web/src/gallery/`、管理画面は `web/src/admin/`（ルートは `web/src/admin-routes.ts`、遅延読み込み）、API の呼び出しは `web/src/api/`、エラーと障害の画面は `web/src/errors/` と `web/public/error-page/`。部品は `web/src/components/ui/`（shadcn の生成物。手で直さない、Biome の対象外）。
- 型は API と共有する（`@contract` = `src/contract.ts`）。画面の都合で API の形を変えるときは dev-backend の手順も使う。

## 2. 作る（テストから）

- 先に失敗するテストを書き、落ちるのを見てから直す。テストは対象の隣（`*.test.tsx`）。テスト名は日本語。
- API は msw で用意する。`setupServer()` を `server.listen({ onUnhandledFrame: "error" })` で動かし、未処理の要求で落ちるようにする（このバージョンに `onUnhandledRequest` はない）。共通の値と要求は `web/src/test/handlers.ts`、管理画面のログイン済みの状態と `renderAt` などは `web/src/admin/test-helpers.tsx`。
- 画面の文言・コメントは日本語。写真と動画が混ざる文言は「写真 2 枚・動画 1 本」のように言い分ける（`web/src/lib/mediaCount.ts`）。
- スマートフォンの縦画面（幅 360〜430px）を最優先にする。iPhone のホーム画面のアプリ（Safari）で使われる。`100svh` と `env(safe-area-inset-*)` に気をつける。大きな画像をそのまま `<img>` や object URL で何百枚も出さない（メモリ不足で真っ白になった。`web/src/admin/upload/thumbnails.ts`）。
- ダークモードでも読めるよう、色は Tailwind のテーマの色（`bg-card`・`text-muted-foreground`・`stroke-border` など）を使い、色の値を直接書かない。
- ギャラリーに管理画面や Amplify を読み込ませない（ルート単位のコード分割を崩さない）。新しい依存は、必要なときだけユーザーに確かめて足す。

- 画面をまたぐ流れ（ログイン・アップロード・一覧の切り替えなど）やスマートフォン幅の崩れは、E2E（Playwright）でも確かめる。置き場所は `web/e2e/*.spec.ts`、走らせ方は `npm --prefix web run e2e`（ビルドして `vite preview` で配り、Chromium と WebKit の 390×844 で動かす。`-- --project chromium-mobile` で片方だけ）。
  - 本番の AWS にはつながない。`/config.json`・`/api/*`・`/media/*`・Cognito・S3 への送信は `web/e2e/fixtures.ts` の `page.route` で偽の応答を返す（型は `@contract`）。新しい API を呼ぶ画面を足したら、ここに偽の応答を足す。
  - 偽の応答の無い `/api`・`/media` と、localhost 以外への通信は止めて記録し、1 件でもあればテストは失敗する。
  - ログイン済みは `signedIn`（Amplify の localStorage に偽のトークン）、未ログインは `backend` のフィクスチャを使う。役割は `backend.me` を書き換える。

## 3. 見た目を確かめる

- テストが通っても、見た目は実物で確かめる。ログインが要らない形で見るには、一時の確認ページを作る:
  - `web/src/__preview/<名前>.tsx` で対象の部品を `createRoot` で描き（`../index.css` を読む）、`web/<名前>-preview.html` から読み込む。
  - `cd web && npx vite --port 5199 --strictPort` をバックグラウンドで動かし、Chrome DevTools で開く。幅 360・390px（mobile, touch）と、広い画面（1024px など）、`#dark` やダークモードの両方を見る。
  - 幅が足りるかは、要素の `getBoundingClientRect()` で数字で確かめる（目分量で済ませない）。
  - 終わったら、確認ページのファイルを消し、vite を止める。コミットに入れない。
- ローカルの API と組み合わせて見るときは README「ローカル開発」の手順（`npm run dev` と `npm run web:dev`。S3 は本番バケット）。

## 4. 仕上げ

- 機能や見た目の振る舞いを変えたら、README の関係する箇所（多くは「画面とログイン」）を同じ PR で直す。構成や数字を変えたら「このアプリについて」（`web/src/admin/about/content.ts`）も直す。
- `npm run fix` のあと、/verify と同じ検査を全部通す（成否は終了コードで見る）。web だけの変更でも、ルートの `npm run check` は Biome が web も見るので外さない。
- /ship で PR を作り、CI を見届ける。マージはユーザーがする。報告には、本番で確かめてほしいこと（どの画面で、何をすると、どうなるか）を手順で書く。

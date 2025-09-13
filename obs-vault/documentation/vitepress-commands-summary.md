---
tags:
  - vitepress
  - cli
  - commands
  - cheatsheet
---

# VitePressの主要コマンドまとめ

VitePressで使用するコマンドとオプションのまとめ。

🌟 基本コマンド
* vitepress dev [root]
    * 開発サーバーを起動する
    * デフォルトは http://localhost:5173
* vitepress build [root]
    * 静的サイトをビルドし、dist/ に出力する
* vitepress serve [root]
    * ビルドしたサイトをローカルでプレビューする

🌟 よく使われるオプション
dev
* --host
    * サーバーのホスト名（例：--host 0.0.0.0 で外部からのアクセスを許可）
* --port
    * ポート番号を指定（例：--port 4000）
* --open
    * サーバー起動時にブラウザを自動で開く
* --base `<path>`
    * サイトのベースパスを指定（デフォルトは /）
build
* --outDir `<dir>`
    * 出力ディレクトリ（デフォルトは .vitepress/dist）
* --base `<path>`
    * サイトのベースパスを指定
* --clean
    * ビルド前に出力ディレクトリを削除する
* --watch
    * ファイルの変更を監視して自動でリビルドする
serve
* --port
    * プレビューサーバーのポート番号を指定
* --host
    * プレビューサーバーのホスト名を指定
* --open
    * 起動時にブラウザを開く

🌟 その他
* vitepress --help
    * 全コマンドとオプションのヘルプを表示
* vitepress dev --help
    * dev コマンドのヘルプ
* vitepress build --help
    * build コマンドのヘルプ
* vitepress serve --help
    * serve コマンドのヘルプ

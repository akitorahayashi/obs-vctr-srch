---
tags:
  - python
  - automation
  - web-scraping
  - beautifulsoup
  - requests
---

# PythonによるWebスクレイピング入門：RequestsとBeautifulSoupの活用

## はじめに：Webスクレイピングとは？

Webスクレイピングは、ウェブサイトから自動的に情報を抽出し、データを収集する技術です。手作業でデータをコピー＆ペーストする代わりに、プログラムを使って情報を構造化された形式（例：CSVファイル）で保存できます。市場調査、価格比較、ニュース収集など、多くのビジネスシーンで活用されています。

**倫理的な注意点:** スクレイピングを行う際は、対象サイトの利用規約（`robots.txt`など）を必ず確認し、サーバーに過度な負荷をかけないように注意しましょう。非公開情報や個人情報の無断収集は法律に触れる可能性があります。本ガイドは、公開情報の収集を目的としています。

---

## パート1：Webページを取得する - `requests`ライブラリ

スクレイピングの最初のステップは、対象となるWebページのHTMLコンテンツを取得することです。これには`requests`ライブラリが非常に便利です。

まず、ライブラリをインストールします。
```bash
pip install requests
```

次に、Pythonスクリプトで特定のURLのコンテンツを取得します。

```python
import requests

# 対象のURL
url = 'http://example.com' # 実際のスクレイピングでは対象サイトのURLに置き換える

try:
    # GETリクエストを送信
    response = requests.get(url)

    # ステータスコードが200（成功）か確認
    response.raise_for_status()

    # 文字化けを防ぐためにエンコーディングを設定
    response.encoding = response.apparent_encoding

    # HTMLコンテンツを取得
    html_content = response.text
    print("HTMLコンテンツの取得に成功しました。")
    # print(html_content) # 全文を表示したい場合はコメントアウトを外す

except requests.exceptions.RequestException as e:
    print(f"エラーが発生しました: {e}")

```
`response.raise_for_status()`は、リクエストが失敗した場合（ステータスコードが4xxや5xxなど）に例外を発生させ、エラーハンドリングを容易にします。

---

## パート2：HTMLを解析する - `BeautifulSoup`ライブラリ

取得したHTMLは単なる文字列です。ここから特定の情報（例：記事のタイトル、リンクなど）を抽出するために、HTMLを解析（パース）する必要があります。`BeautifulSoup`ライブラリは、このプロセスを非常に簡単にします。

まず、ライブラリをインストールします。
```bash
pip install beautifulsoup4 lxml
```
(`lxml`は高速なHTMLパーサーです)

次に、`requests`で取得したHTMLコンテンツを`BeautifulSoup`に渡して解析します。

```python
from bs4 import BeautifulSoup
import requests # 前のステップから継続

# ... (requestsでhtml_contentを取得するコード) ...

# BeautifulSoupオブジェクトを作成
soup = BeautifulSoup(html_content, 'lxml')

# 整形されたHTMLを出力
# print(soup.prettify())

# ページのタイトルを取得
page_title = soup.title.string
print(f"ページのタイトル: {page_title}")

# すべての<h1>タグを検索し、そのテキストを取得
h1_tag = soup.find('h1')
if h1_tag:
    print(f"最初のH1タグの内容: {h1_tag.get_text()}")

# すべての<p>（段落）タグを検索
all_paragraphs = soup.find_all('p')
print(f"段落の数: {len(all_paragraphs)}")
for p in all_paragraphs:
    print(f"- {p.get_text(strip=True)}")

```

### `find()`と`find_all()`

*   `soup.find('タグ名')`: 条件に一致する最初のタグを一つだけ返します。
*   `soup.find_all('タグ名')`: 条件に一致するすべてのタグをリストとして返します。

### 特定の属性を持つタグを検索する

クラス名やIDを使って、より具体的に要素を絞り込むことができます。

```python
# 例：<div class="content">...</div> を検索
content_div = soup.find('div', class_='content')

# 例：<p id="summary">...</p> を検索
summary_p = soup.find('p', id='summary')

# 例：すべての<a>（リンク）タグを取得
all_links = soup.find_all('a')
for link in all_links:
    # href属性（リンク先URL）を取得
    href = link.get('href')
    # リンクのテキストを取得
    text = link.string
    if href and text:
        print(f"テキスト: {text.strip()}, URL: {href}")
```
**注意:** `class`はPythonの予約語なので、`BeautifulSoup`では`class_`という引数名を使います。

---

## パート3：実践：データをCSVファイルに保存する

収集したデータをCSVファイルとして保存することで、Excelなどで簡単に利用できます。ここでは、架空のニュースサイトから記事のタイトルとURLを抽出し、CSVに保存する例を考えます。

```python
import requests
from bs4 import BeautifulSoup
import csv

# --- Step 1: データ取得 ---
# 架空のニュースサイトのURL
url = 'http://example-news.com' # このURLは存在しません
# 実際のHTMLをここに模倣します
html_content = """
<html>
<head><title>今日のニュース</title></head>
<body>
  <h1>最新ニュース</h1>
  <div class="news-list">
    <div class="article">
      <h2><a href="/news/1">最初のニュース</a></h2>
      <p>これは最初のニュースの概要です。</p>
    </div>
    <div class="article">
      <h2><a href="/news/2">2番目のニュース</a></h2>
      <p>これは2番目のニュースの概要です。</p>
    </div>
    <div class="article">
      <h2><a href="/news/3">3番目のニュース</a></h2>
      <p>これは3番目のニュースの概要です。</p>
    </div>
  </div>
</body>
</html>
"""

# --- Step 2: データ解析 ---
soup = BeautifulSoup(html_content, 'lxml')

articles = []
# classが"article"のdivタグをすべて検索
for item in soup.find_all('div', class_='article'):
    # その中のh2タグ内のaタグを探す
    title_tag = item.find('h2').find('a')
    if title_tag:
        title = title_tag.get_text(strip=True)
        link = title_tag.get('href')
        # 完全なURLを組み立てる
        full_link = requests.compat.urljoin(url, link)
        articles.append({'title': title, 'link': full_link})

# --- Step 3: CSVに保存 ---
csv_filename = 'news_articles.csv'

try:
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        # CSVのヘッダー（列名）を定義
        fieldnames = ['title', 'link']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # ヘッダーを書き込む
        writer.writeheader()

        # データを書き込む
        writer.writerows(articles)

    print(f"データが '{csv_filename}' に正常に保存されました。")

except IOError:
    print("I/Oエラー: ファイルへの書き込みに失敗しました。")

```

このスクリプトを実行すると、`news_articles.csv`というファイルが作成され、以下のような内容で保存されます。

```csv
title,link
最初のニュース,http://example-news.com/news/1
2番目のニュース,http://example-news.com/news/2
3番目のニュース,http://example-news.com/news/3
```

---

## まとめ

本ガイドでは、`requests`を使ってWebページのHTMLを取得し、`BeautifulSoup`を使ってその中から必要な情報を抽出し、最終的にCSVファイルとして保存する、Webスクレイピングの基本的なワークフローを学びました。

この技術を応用すれば、様々なウェブサイトからデータを収集し、ビジネスや研究に役立てることができます。重要なのは、常に倫理的な配慮を忘れず、対象サイトのルールを守ることです。ここからさらに、JavaScriptで動的に生成されるコンテンツのスクレイピング（Seleniumなどの利用）や、APIの活用など、より高度なトピックへ進むことができます。

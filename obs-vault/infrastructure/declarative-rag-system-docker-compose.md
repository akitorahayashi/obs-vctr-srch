---
tags:
  - infrastructure
  - docker
  - docker-compose
  - rag
  - llm
  - ollama
  - langchain
  - chromadb
---
# Docker ComposeによるRAGシステムの宣言的構築

## 序章：なぜDocker Composeなのか？- AIアプリケーションにおけるマイクロサービス化への第一歩

### 単一コンテナから完全なアプリケーションスタックへ

docker runコマンドを使いこなし、単一のコンテナを自在に操れるようになったエンジニアが次に向き合うべき壁、それは「複数のサービスが連携するアプリケーション」の構築です。特に現代のAIアプリケーションは、単一のプログラムで完結することは稀です。多くの場合、それぞれが専門的な役割を持つ複数のサービスが協調して動作する、複雑なシステムとして設計されます。
本章では、その典型例として[[../lang-chain/application-patterns/rag-architectures|Retrieval-Augmented Generation (RAG)]] システムを取り上げます。RAGシステムは、ユーザーの質問に対して、外部の知識ソースを参照してより正確な回答を生成するAI技術です。このシステムは、最低でも以下の3つのコンポーネントから構成されます。
- **大規模言語モデル（LLM）サーバー**: 回答生成の頭脳となる部分。
- **ベクトルデータベース**: 外部知識を高速に検索可能にするためのデータベース。
- **APIサーバー**: 全体のロジックを制御し、ユーザーとのインターフェースとなる部分。

これら3つのサービスを個別のdocker runコマンドで起動し、ネットワーク設定を手動で行い、起動順序を気にかけるのは、非常に煩雑で間違いやすい作業です。ここで登場するのが、本章の主役であるDocker Composeです。

### 宣言的インフラストラクチャ（Infrastructure as Code）の力

Docker Composeは、複数のコンテナで構成されるアプリケーションを、単一のYAMLファイル（compose.yamlまたはdocker-compose.yml）で定義し、管理するためのツールです。
docker runコマンドを一つ一つ実行していく「命令的（Imperative）」なアプローチとは対照的に、Docker Composeでは「アプリケーションは『こうあるべきだ』」という最終的な状態をYAMLファイルに「宣言的（Declarative）」に記述します。このファイルは、アプリケーションのインフラ全体をコードとして表現する「Infrastructure as Code (IaC)」の中核的な実践例です。このアプローチにより、環境構築のプロセスが簡素化され、開発環境とテスト環境での一貫性が保証され、アプリケーション全体のポータビリティが劇的に向上します。

この宣言的なアプローチへの移行は、単なる利便性の向上以上の意味を持ちます。それは、開発者の思考様式を「個々のプログラム」から「相互接続されたサービスの集合体としてのアプリケーションシステム」へと進化させる、重要なステップです。ローカル開発でapiやdbといったサービス名を定義し、それらの関係性をコードで記述する経験は、Kubernetesのような本番環境で利用される、より高度なコンテナオーケストレーションツールを理解するための基礎的なメンタルモデルを構築します。したがって、Docker Composeの習得は、単なるローカル開発スキルの獲得に留まらず、クラウドネイティブなデプロイメントへと続く学習の旅路において、不可欠なマイルストーンとなるのです。

### 本章の目標とロードマップ

本章を終える頃には、読者はRAGのような複雑なAIアプリケーションのアーキテクチャを理解し、その構成要素と依存関係をdocker-compose.ymlファイルに定義し、docker-compose upという単一のコマンドでシステム全体を起動できるようになることを目指します。
本章は以下の構成で進みます。
- RAGシステムのアーキテクチャを理解する: なぜRAGが必要なのか、どのようなコンポーネントで構成されるのかを学びます。
- 各コンポーネントの準備: APIサーバーやLLMサーバーなど、各サービスのDockerfileを作成します。
- Docker Composeによる宣言的オーケストレーション: docker-compose.ymlを書き、サービス間の連携、ネットワーク、データ永続化を定義します。
- システム全体の起動とテスト: 実際にシステムを起動し、RAGパイプラインが正しく動作することを確認します。

## 第1部：RAGシステムのアーキテクチャを理解する

Docker Composeでシステムを構築する前に、まずは私たちが構築しようとしているRAGシステムがどのようなもので、なぜ必要なのかを理解することが重要です。

### 課題：LLMは限定的な知識しか持たない

ChatGPTのような大規模言語モデル（LLM）は非常に強力ですが、その知識は学習に使われたデータセットに限定されており、特定の時点（ナレッジ・カットオフ）で静的なものとなっています。そのため、最新の出来事や、社内のドキュメントのようなプライベートで専門的な情報については答えることができません。
この制約により、LLMは事実に基づかない情報を生成する「ハルシネーション（幻覚）」を起こしたり、特定の質問に答えられなかったりします。RAGは、LLMに回答を生成させる際に、関連する外部情報を「カンニングペーパー」としてリアルタイムで提供することで、この問題を解決するアーキテクチャパターンです。

### RAGソリューション：2段階のプロセス

RAGの仕組みは、大きく分けて「インデックス作成」と「検索・生成」の2つのフェーズで構成されます。
- **インデックス作成 (Indexing / オフライン処理)**: このフェーズは、事前に一度だけ行われる準備段階です。まず、社内ドキュメントやWebサイトの記事などの知識ソースとなる文書を収集します。次に、これらの文書を扱いやすいサイズ（例えば、段落ごと）の「チャンク」に分割します。そして、「埋め込みモデル（Embedding Model）」と呼ばれる特殊なAIモデルを使い、各チャンクを意味を捉えた数値の配列（ベクトル）に変換します。最後に、これらのベクトルを専門の「ベクトルデータベース」に保存し、高速に検索できるように索引付けします。
- **検索と生成 (Retrieval & Generation / オンライン処理)**: このフェーズは、ユーザーが質問をするたびに実行されます。
  1. ユーザーがAPIに質問（クエリ）を送信します。
  2. システムは、インデックス作成時と同じ埋め込みモデルを使い、ユーザーの質問もベクトルに変換します。
  3. この質問ベクトルを使ってベクトルデータベースを検索し、意味的に最も類似している（関連性が高い）ドキュメントのチャンクをいくつか取り出します。これが「検索（Retrieval）」のステップです。
  4. 元の質問と、検索で得られたチャンクを組み合わせ、「あなたの知識と、この参考情報を基に、以下の質問に答えてください」という形式の新しいプロンプト（拡張プロンプト）を作成します。
  5. この拡張プロンプトをLLMに送り、事実に基づいた回答を生成させます。これが「生成（Generation）」のステップです。

この一連の流れを図で示すと、以下のようになります。
```
[ユーザー] -> [APIサーバー] -> (質問をベクトル化) -> ^
|                                                | (類似チャンク検索)
v                                                |
(回答)                                          |
[LLMサーバー] <- (拡張プロンプト) <- [APIサーバー] <- (チャンク取得)
```

### 私たちの技術スタック

このRAGシステムを実装するために、本章では以下のオープンソース技術を選定します。各コンポーネントの役割と選択した技術を明確に理解することは、後のdocker-compose.ymlの設計に不可欠です。

| コンポーネントの役割 | 選択した技術 | システム内での主要な機能 |
| :--- | :--- | :--- |
| LLMサーバー | [[../python/aider-ollama-mastery-guide|Ollama]] | 中核となる生成能力を提供。拡張プロンプトを受け取り、人間らしい回答を生成する。 |
| ベクトルデータベース | ChromaDB | 知識ソースとなる文書のベクトル表現（埋め込み）を保存・インデックス化し、効率的な類似性検索を実現する。 |
| API & ロジック | FastAPI & [[../lang-chain/index_lang-chain|LangChain]] | ユーザーからのクエリを受け付けるエンドポイントを公開。LangChainを使い、検索と生成のステップを連携させるRAGのコアロジックを実装する。 |

## 第2部：各コンポーネントの準備 - Dockerfileの作成

アーキテクチャを理解したところで、次はいよいよ各コンポーネントをコンテナ化するための準備、すなわちDockerfileの作成に取り掛かります。

### 2.1 APIサーバーの構築 (FastAPI & LangChain)

まず、RAGシステムの司令塔となるAPIサーバーを構築します。

#### アプリケーションコード (rag_app/main.py)

FastAPIアプリケーションのPythonコードを以下に示します。このコードは、データのインデックス作成を行う/ingestエンドポイントと、質問応答を行う/ragエンドポイントを提供します。
```python
# rag_app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain.schema.output_parser import StrOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough

# サービス名をホスト名として使用
CHROMA_HOST = "chroma"
OLLAMA_HOST = "ollama"

# LangChainのコンポーネントを初期化
embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=f"http://{OLLAMA_HOST}:11434")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)
llm = ChatOllama(model="llama3", base_url=f"http://{OLLAMA_HOST}:11434")

# ChromaDBクライアントの初期化
vectorstore = Chroma(
    collection_name="rag-collection",
    embedding_function=embeddings,
    client_settings={
        "host": CHROMA_HOST,
        "port": 8000,
        "ssl": False,
    }
)
retriever = vectorstore.as_retriever()

# RAGプロンプトテンプレート
template = """Answer the question based only on the following context:
{context}

Question: {question}
"""
prompt = ChatPromptTemplate.from_template(template)

# FastAPIアプリケーションのインスタンス化
app = FastAPI()

class IngestRequest(BaseModel):
    text: str

@app.post("/ingest")
def ingest_data(request: IngestRequest):
    """ドキュメントを分割し、ベクトル化してChromaDBに保存する"""
    chunks = text_splitter.split_text(request.text)
    vectorstore.add_texts(chunks)
    return {"status": "success", "message": f"Ingested {len(chunks)} chunks."}

@app.get("/rag")
def query_rag(query: str):
    """RAGチェーンを実行して質問に回答する"""
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    answer = chain.invoke(query)
    return {"answer": answer}
```
このコードで最も重要な点は、ChatOllamaとChromaのクライアント接続ロジックです。`base_url=f"http://{OLLAMA_HOST}:11434"`や`host=CHROMA_HOST`のように、ホスト名として`ollama`や`chroma`といった文字列を指定しています。これらは、後ほどdocker-compose.ymlで定義するサービス名に対応します。Docker Composeが提供する内部ネットワーク機能により、コンテナはこのサービス名を使って他のコンテナと通信できます。

#### 依存関係 (rag_app/requirements.txt)

アプリケーションが必要とするPythonパッケージをリストアップします。
```
fastapi
uvicorn
langchain
langchain-community
langchain-ollama
chromadb-client
sentence-transformers
pydantic
```

#### Dockerfile (rag_app/Dockerfile)

最後に、このFastAPIアプリケーションをコンテナイメージ化するためのDockerfileを作成します。
```dockerfile
# rag_app/Dockerfile
# 1. 軽量なPythonイメージをベースにする
FROM python:3.9-slim

# 2. コンテナ内の作業ディレクトリを設定
WORKDIR /app

# 3. 依存関係ファイルをコピー
COPY requirements.txt .

# 4. 依存関係をインストール（--no-cache-dirでイメージサイズを削減）
RUN pip install --no-cache-dir -r requirements.txt

# 5. アプリケーションコードをコピー
COPY . .

# 6. コンテナ起動時にUvicornサーバーを実行
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
このDockerfileの各ステップは、効率的なイメージ構築のために最適化されています。特に、変更頻度の低い`requirements.txt`を先にコピーして`pip install`を実行し、変更頻度の高いアプリケーションコード（`COPY . .`）を後にコピーすることで、Dockerのビルドキャッシュが最大限に活用され、開発サイクルが高速化します。

### 2.2 LLMサーバーの準備 (Ollama)

多くの一般的なサービスでは、Docker Hubで公開されている公式イメージをそのまま利用できます。これはChromaDBで採用するアプローチです。しかし、Ollamaについては、より堅牢で使いやすいサービスを構築するために、少し手を加えたカスタムイメージを作成します。
ここでの目標は、コンテナが起動した時点で、私たちが使用したいLLM（llama3）が自動的にダウンロードされ、即座にリクエストを処理できる状態にすることです。これにより、APIサーバーが起動してもLLMがまだ準備できていない、という競合状態を避けることができます。
この「サービスの自己完結性を高める」という考え方は、マイクロサービス設計における重要な原則です。サービスが必要な初期設定を自身のコンテナイメージに内包することで、オーケストレーター（Docker Compose）はサービスの内部的なセットアップ手順を意識する必要がなくなり、システム全体の信頼性と管理性が向上します。

#### カスタムDockerfile (ollama/Dockerfile)

`ollama/ollama`公式イメージをベースに、モデルを自動的にプルするスクリプトを実行するDockerfileを作成します。
```dockerfile
# ollama/Dockerfile
FROM ollama/ollama:latest

# 使用するモデル名を環境変数で定義
ENV OLLAMA_MODEL=llama3

# エントリーポイントスクリプトをコピーして実行権限を付与
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# エントリーポイントとしてスクリプトを指定
ENTRYPOINT ["/entrypoint.sh"]

# デフォルトのポートを公開
EXPOSE 11434

# コンテナが実行し続けるためのデフォルトコマンド
CMD ["serve"]
```

#### エントリーポイントスクリプト (ollama/entrypoint.sh)

このスクリプトは、コンテナ起動時にモデルのプルとサーバーの起動を順序正しく実行します。
```bash
#!/bin/bash
set -e

# Ollamaサーバーをバックグラウンドで起動
/bin/ollama serve &
pid=$!

# サーバーが起動するのを待つ
sleep 5

# 環境変数で指定されたモデルをプル
echo "Pulling model: $OLLAMA_MODEL"
ollama pull $OLLAMA_MODEL

# モデルのプルが完了したら、バックグラウンドのプロセスを停止
kill $pid
wait $pid

# 最後に、フォアグラウンドでOllamaサーバーを再起動してコンテナを維持
exec /bin/ollama serve
```

### 2.3 ベクトルデータベースの準備 (ChromaDB)

ベクトルデータベースについては、シンプルにDocker Hubの公式イメージ`chromadb/chroma`を利用します。ポートのマッピングやデータの永続化といった重要な設定は、次のセクションで`docker-compose.yml`ファイル内で直接行います。

## 第3部：Docker Composeによる宣言的オーケストレーション

各コンポーネントのDockerfileが準備できたので、いよいよオーケストラの指揮者である`docker-compose.yml`を作成し、システム全体を宣言的に定義します。

### 3.1 サービスの定義

まず、`docker-compose.yml`ファイルの骨格として、`api`、`ollama`、`chroma`の3つのサービスを定義します。
```yaml
# docker-compose.yml (初期段階)
version: '3.8'

services:
  # APIサーバー (FastAPI & LangChain)
  api:
    build: ./rag_app
    container_name: rag_api

  # LLMサーバー (Custom Ollama)
  ollama:
    build: ./ollama
    container_name: ollama_server

  # ベクトルデータベース (ChromaDB)
  chroma:
    image: chromadb/chroma:latest
    container_name: chroma_db
```
`api`と`ollama`サービスでは`build`キーを使い、先ほど作成したDockerfileからイメージをビルドするよう指示します。一方、`chroma`サービスでは`image`キーを使い、Docker Hubから公式イメージをプルするよう指示しています。

### 3.2 ネットワークとデータ永続化

#### ネットワーク

Docker Composeは、デフォルトで全てのサービスを単一のカスタムブリッジネットワークに接続します。この機能のおかげで、`api`サービスのPythonコードは`http://chroma:8000`のようにサービス名をホスト名として使用するだけで、`chroma`コンテナにアクセスできます。Composeが内部的にサービス名をコンテナのIPアドレスに解決してくれるため、複雑なネットワーク設定は不要です。
外部からAPIにアクセスできるように、`api`サービスのポートをホストマシンにマッピングします。
```yaml
# apiサービスに追記
ports:
  - "8000:8000"
```

#### ボリュームによるデータ永続化

コンテナは本質的に一時的なものであり、停止・削除すると内部のデータは失われます。しかし、ベクトルデータベースにインデックス化したデータは永続化させる必要があります。そのために`volumes`を使用します。
トップレベルに`volumes`キーを定義し、`chroma-data`という名前付きボリュームを作成します。そして、`chroma`サービスでこのボリュームをコンテナ内のデータ保存ディレクトリ（`/chroma/chroma`）にマウントします。
```yaml
# docker-compose.yml ファイルの末尾に追記
volumes:
  chroma-data:
    driver: local

# chromaサービスに追記
volumes:
  - chroma-data:/chroma/chroma
```

### 3.3 依存関係と起動順序の制御

複数のサービスが連携するシステムでは、起動順序が非常に重要です。例えば、`api`サービスは起動時に`chroma`サービスに接続しようとしますが、もし`chroma`がまだ準備できていなければ、`api`はエラーでクラッシュしてしまいます。

#### depends_onの落とし穴

多くの初学者は、この問題を解決するために`depends_on`を使います。
```yaml
# apiサービスに追記 (不完全な例)
depends_on:
  - chroma
  - ollama
```
しかし、この単純な`depends_on`には大きな落とし穴があります。これは、依存先コンテナの起動を待つだけで、コンテナ内部のアプリケーションがリクエストを受け付けられる準備が完了するのを待つわけではないのです。

#### 堅牢な解決策：healthcheckとcondition

この問題を正しく解決するには、`healthcheck`と`depends_on`の`condition`オプションを組み合わせます。`healthcheck`は、サービスが正常に機能しているかを定期的にチェックする仕組みです。
まず、`chroma`サービスにヘルスチェックを追加します。ChromaDBは`/api/v2/heartbeat`というヘルスチェック用のAPIエンドポイントを提供しているため、これを利用します。
```yaml
# chromaサービスに追記
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 30s
```
次に、`ollama`サービスにもヘルスチェックを追加します。Ollamaは`/api/health`エンドポイントを持っています。
```yaml
# ollamaサービスに追記
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:11434/api/health"]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 30s
```
最後に、`api`サービスの`depends_on`を、このヘルスチェックの結果を待つように変更します。
```yaml
# apiサービスのdepends_onを修正
depends_on:
  chroma:
    condition: service_healthy
  ollama:
    condition: service_healthy
```
`condition: service_healthy`と指定することで、Docker Composeは`chroma`と`ollama`のヘルスチェックが「healthy」状態になるまで`api`サービスの起動を待機します。これにより、サービスの準備が整う前に接続しようとして失敗する、という問題を確実に防ぐことができます。

#### docker-compose.ymlの主要ディレクティブまとめ

| ディレクティブ | 例 | 目的 |
| :--- | :--- | :--- |
| `services` | `services: api:...` | アプリケーションを構成する全コンポーネント（コンテナ）の定義を格納するトップレベルキー。 |
| `build` | `build: ./rag_app` | Dockerfileを含むディレクトリへのパスを指定。Composeはそこからイメージをビルドする。 |
| `image` | `image: chromadb/chroma:latest` | レジストリ（Docker Hubなど）からプルするビルド済みイメージの名前を指定する。 |
| `ports` | `"8000:8000"` | ホストマシンのポート (HOST:CONTAINER) をコンテナ内のポートにマッピングする。 |
| `volumes` | `chroma-data:/chroma/chroma` | データを永続化するため、ホストのパスまたは名前付きボリュームをコンテナ内にマウントする。 |
| `networks` | `networks: - my-network` | サービスを指定されたネットワークに接続する。デフォルトでは全サービスが単一のプロジェクトネットワークに参加する。 |
| `depends_on` | `depends_on: chroma: condition: service_healthy` | サービス間の依存関係を定義し、起動順序を制御する。`service_healthy`条件は、依存先のヘルスチェックが成功するまで待機する。 |
| `healthcheck` | `healthcheck: test: ...` | サービスが正常でトラフィックを処理できる状態かを確認するために、コンテナ内で実行するコマンドを定義する。 |

## 第4部：システム全体の起動とテスト

すべての準備が整いました。最後に、作成した設定ファイルを使ってRAGシステム全体を起動し、実際に動作をテストしてみましょう。

### プロジェクト構造のレビュー

最終的なプロジェクトのディレクトリ構造は以下のようになっているはずです。すべてのファイルが正しい場所に配置されているか確認してください。
```
.
├── docker-compose.yml
├── ollama/
│   ├── Dockerfile
│   └── entrypoint.sh
└── rag_app/
    ├── Dockerfile
    ├── main.py
    └── requirements.txt
```

### 最終的な設定ファイル

以下に、最終的な設定ファイルをすべて掲載します。コピー＆ペーストして利用してください。

#### docker-compose.yml
```yaml
version: '3.8'

services:
  # APIサーバー (FastAPI & LangChain)
  api:
    build: ./rag_app
    container_name: rag_api
    ports:
      - "8000:8000"
    depends_on:
      chroma:
        condition: service_healthy
      ollama:
        condition: service_healthy
    restart: unless-stopped

  # LLMサーバー (Custom Ollama)
  ollama:
    build: ./ollama
    container_name: ollama_server
    volumes:
      - ollama-data:/root/.ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s
    restart: unless-stopped

  # ベクトルデータベース (ChromaDB)
  chroma:
    image: chromadb/chroma:latest
    container_name: chroma_db
    volumes:
      - chroma-data:/chroma/chroma
    ports:
      - "8001:8000" # ホストの8000番はAPIが使うため、8001にマッピング
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s
    restart: unless-stopped

volumes:
  chroma-data:
    driver: local
  ollama-data:
    driver: local
```
その他のファイル（`rag_app/main.py`, `rag_app/Dockerfile`, `ollama/Dockerfile`, `ollama/entrypoint.sh`）は、第2部で提示したものと同一です。

### システムに命を吹き込む

#### 魔法のコマンド

プロジェクトのルートディレクトリに移動し、以下のコマンドを実行します。
```bash
docker-compose up --build -d
```
- `--build`: このフラグは、Docker ComposeにDockerfileからイメージを強制的に再ビルドさせます。これにより、コードの変更が確実に反映されます。
- `-d`: コンテナを「デタッチモード」（バックグラウンド）で実行します。

#### スタックの確認

`docker-compose ps`コマンドを実行して、サービスのステータスを確認します。3つのサービスすべてが`running`または`healthy`状態になっているはずです。
```bash
docker-compose ps
```

#### ログの調査

`docker-compose logs`は、デバッグに不可欠なコマンドです。`docker-compose logs -f api`のように特定のサービスのログを追跡することで、起動シーケンスやエラーを確認できます。

### RAGパイプラインのテスト

システムが起動したら、実際にRAGパイプラインが機能するかをテストします。

#### ステップ1：データの投入 (Ingestion)

まず、知識ソースとなるテキストデータを`/ingest`エンドポイントにPOSTリクエストで送信します。
```bash
curl -X POST "http://localhost:8000/ingest" \
-H "Content-Type: application/json" \
-d '{"text": "Docker Compose is a tool for defining and running multi-container Docker applications. It uses a YAML file to configure an application’s services and creates and starts all the services from that configuration with a single command."}'
```
成功すると、`{"status":"success",...}`というレスポンスが返ってきます。

#### ステップ2：質問応答 (Query)

次に、投入したデータに関連する質問を`/rag`エンドポイントにGETリクエストで送信します。
```bash
curl "http://localhost:8000/rag?query=What%20is%20Docker%20Compose"
```
システムが正しく機能していれば、以下のようなJSONレスポンスが返ってくるはずです。これは、APIリクエストからChromaDBでの検索、そしてOllamaによる生成までの全パイプラインが成功したことを示しています。
```json
{
  "answer": "Docker Compose is a tool used for defining and running multi-container Docker applications. It utilizes a YAML file to configure the services of an application, and with a single command, it creates and starts all the configured services."
}
```

### システムの停止

最後に、以下のコマンドでプロジェクトが作成したすべてのコンテナ、ネットワーク、ボリュームを停止・削除します。
```bash
docker-compose down -v
```
`-v`フラグは、`chroma-data`のような名前付きボリュームも一緒に削除するために重要です。これを付けないと、データがホスト上に残り続けます。

## 結論：ローカル環境からその先へ

### 達成事項の振り返り

本章を通じて、読者は単なるDockerユーザーから、アプリケーションアーキテクトへと大きな一歩を踏み出しました。具体的には、以下の強力なスキルセットを習得しました。
- RAGシステムのアーキテクチャの理解
- Pythonアプリケーションのコンテナ化
- 特定の要件に合わせたカスタムサービスイメージの作成
- Docker Composeを用いた、複雑なマルチサービスアプリケーションスタックの宣言的な定義と管理

### 本番環境への架け橋

このセットアップはローカルでの開発やテストには最適ですが、本番環境ではより強力なオーケストレーションツールが使われるのが一般的です。その業界標準がKubernetesです。
しかし、ここで学んだ中核的な概念（サービス、コンテナイメージ、ネットワーク、ヘルスチェック）は、Kubernetesに直接応用できます。作成したDockerfileは、変更なしでKubernetesにデプロイ可能です。そして、`docker-compose.yml`で記述したサービスの定義は、Kubernetesのマニフェストファイル（Deployment, Service, PersistentVolumeClaimなど）を理解するための優れた概念的な青写真となります。

### さらなる探求へ

意欲的な読者のための次のステップとして、以下のようなテーマを探求することをお勧めします。
- より高度なRAG技術（リランキング、クエリ変換など）の調査
- Ollamaで異なるLLMや、他のベクトルデータベースを試す
- `docker-compose.yml`をKubernetesのオブジェクトに変換する方法の学習
- Komposeのような、この変換を自動化するツールの調査

本章で得た知識と経験は、現代的で洗練されたAIシステムを構築し、管理するための確かな基盤となります。この一歩が、あなたのエンジニアとしてのキャリアを新たな高みへと導くことを確信しています。

---
tags:
  - langchain
  - application-pattern
  - rag
  - architecture
---
# アプリケーションパターン：RAGアーキテクチャ

Retrieval-Augmented Generation (RAG) は、大規模言語モデル（LLM）の能力を、外部の信頼できる知識源で補強し、その応答を特定の事実に「グラウンディング（接地）」させるための、最も重要かつ広く利用されているアーキテクチャです。

## 1. RAGの設計思想

### 1.1. 基本的なプロセス

RAGのプロセスは、2つの主要なフェーズで構成されます。
1.  **Retrieval（取得）**: ユーザーの質問に関連する情報を、ドキュメント、データベース、APIといった外部の知識源から検索・取得します。
2.  **Generation（生成）**: 取得した情報をコンテキスト（文脈）としてLLMに与え、そのコンテキストに基づいて回答を生成させます。

このアーキテクチャは、LLMが学習していないプライベートな情報や、最新の情報について、正確かつ検証可能な回答を生成する上で決定的に重要です。LLMが自身の内部知識のみで回答しようとすると、事実に基づかない情報を生成する「ハルシネーション（幻覚）」のリスクが常に伴います。RAGは、LLMに参照すべき明確な情報源を提供することで、このリスクを大幅に低減し、回答の信頼性と説明責任を確保します。

### 1.2. LLMの役割の再定義：「神託」から「制約付き推論エンジン」へ

RAGアーキテクチャを導入する上で最も重要な概念的転換は、LLMの役割を「全知全能の神託（Oracle）」から「高度な制約付き推論エンジン（Constrained Reasoner）」へと捉え直すことです。

この考え方は、以下のプロセスを経て具体化されます。
1.  **課題**: 企業内のドキュメントや最新のウェブ情報など、LLMの事前学習データには含まれていない情報について回答を生成したい。
2.  **RAGによる解決策**: RAGは、この問題を「知識ベース（情報を格納したベクトルストアなど）」と「推論エンジン（LLM）」を明確に分離することで解決します。
3.  **プロセスの具体化**: ユーザーの質問がシステムに入力されると、LLMがその質問を見る前に、まずシステムは知識ベースから最も関連性の高いテキスト断片（チャンク）を取得します。
4.  **プロンプトによる制約**: 次に、LLMに渡されるプロンプトは、「**以下のコンテキスト情報のみを使用して**、質問に答えてください」という形式で意図的に構築されます。
5.  **タスクの変換**: これにより、LLMのタスクは、漠然とした「知識の想起」から、与えられた文章に対する「制約付きの読解と要約」へと変化します。このタスクは、LLMにとって遥かに制御しやすく、信頼性が高く、そして監査可能なものとなり、エンタープライズ環境での利用に適した形となるのです。

---

## 2. インジェストパイプライン：知識のインデックス化

RAGシステムの品質は、生の情報を検索可能な知識インデックスに変換するための、重要な前処理ステップである**インジェスト（取り込み）パイプライン**の設計によって大きく左右されます。

### 2.1. データの読み込み (Document Loaders)

最初のステップは、知識源となるドキュメントを読み込むことです。LangChainは、PDF (`PyMuPDFLoader`)、Webページ (`WebBaseLoader`)、CSV (`CSVLoader`) など、様々な形式のデータを読み込むための`Document Loader`を提供しています。

**重要なのはコンテキストの保存です。** 優れたローダーは単にテキストを抽出するだけでなく、元の資料が持つ構造的なコンテキスト（例：ファイル名、ページ番号、URL）を`metadata`として`Document`オブジェクトに保存します。このメタデータが、後工程での「回答の根拠提示」機能を実現するための鍵となります。

```python
from langchain_community.document_loaders import PyMuPDFLoader

# 例：PDFローダー
loader = PyMuPDFLoader("data/example-document.pdf")
documents = loader.load()

# メタデータには出典情報が含まれる
# print(documents[0].metadata)
# -> {'source': 'data/example-document.pdf', 'file_path': '...', 'page': 0, ...}
```

### 2.2. テキストの分割 (Text Splitters)

読み込んだドキュメントは、LLMが扱いやすいサイズのかたまり（チャンク）に分割する必要があります。`RecursiveCharacterTextSplitter`は、意味的に関連性の高い文章や段落を可能な限り維持しようとするため、最も汎用性が高く推奨されるスプリッターです。

*   `chunk_size`: 1つのチャンクの最大サイズ（文字数）。
*   `chunk_overlap`: 連続するチャンク間で共有される文字数。文脈の断絶を防ぎます。

`chunk_size`の選択は重要なチューニング項目です。小さすぎると文脈が失われ、大きすぎると検索精度が低下する（lost in the middle問題）ため、500〜1500文字程度が良い出発点とされています。

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = text_splitter.split_documents(documents)
```

### 2.3. テキストのベクトル化 (Text Embedding Models)

テキストチャンクは、そのままではコンピュータが意味を理解できません。**テキスト埋め込み（エンベディング）モデル**は、これらのチャンクを数値の配列、すなわち**ベクトル**に変換します。このプロセスにより、意味的に類似したテキストは、高次元のベクトル空間上で互いに近い位置に配置され、セマンティック検索（意味に基づいた検索）が可能になります。

選択肢は、主にAPIベースかローカル実行かに分かれます。

| 特徴 | APIベース (例: OpenAI) | ローカル (例: HuggingFace) |
| :---- | :---- | :---- |
| **性能** | 非常に高い | 高い（モデルによる） |
| **コスト** | 従量課金制 | 無料（ハードウェアコスト除く） |
| **データプライバシー** | 外部サーバーにデータを送信 | 組織内で完結 |
| **セットアップ** | 容易（APIキー設定のみ） | 中程度（ライブラリとモデルのDL） |

### 2.4. ベクトルストアへの格納 (Vector Stores)

**ベクトルストア**は、生成されたベクトル表現を効率的に保存し、高速な類似度検索を実行するために特化したデータベースです。

*   **FAISS**: インメモリでの高速検索に優れ、プロトタイピングに最適。
*   **Chroma**: ディスクへの永続化が容易で、プロトタイプから本番運用への移行がスムーズ。

どちらのベクトルストアを使用するにせよ、`.as_retriever()`メソッドを呼び出すことで、ベクトルストアを「リトリーバー」というLangChain標準のインターフェースに変換できます。これにより、アプリケーションの他の部分は、背後にあるベクトルストアの実装を意識することなく、統一された方法でデータ取得を行えるようになります。

```python
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# ローカルエンベディングとChromaを使用する例
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="db/chroma_db"
)

# リトリーバーとして利用
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
```

---

## 3. 生成パイプライン：LLMとの対話

インジェストパイプラインで準備した知識インデックスを使い、最終的な回答を生成します。

### 3.1. モデルの選択 (Chat Models)

アプリケーションの核となるLLMを選択します。ここでもAPIベースかローカル実行かの選択があります。

*   **ChatOpenAI**: GPT-4oのような最先端モデルにアクセス可能。最高の回答品質が期待できるが、データプライバシーとコストの懸念がある。
*   **ChatOllama**: Llama 3のようなオープンソースモデルをローカルで実行。データ主権を確保でき、コストを固定化できる。

LangChainは両モデルに対して共通の`Runnable`インターフェースを提供するため、アプリケーションのロジックを変更することなく、両者を交換してテストすることが可能です。

### 3.2. プロンプトの設計 (Prompt Templates)

プロンプトの設計は、LLMに意図通りの振る舞いをさせる上で極めて重要です。RAGのための堅牢なプロンプトは、単に質問をするだけでなく、LLMの行動を設計するための**ガードレール**として機能します。

```python
from langchain_core.prompts import ChatPromptTemplate

RAG_PROMPT_TEMPLATE = """あなたは質問に回答する、誠実で正確なアシスタントです。
提供された以下の「コンテキスト」の情報のみに基づいて、ユーザーの「質問」に日本語で回答してください。
コンテキストに答えが記載されていない場合は、決して推測で回答せず、「提供された情報からは分かりません」と明確に回答してください。

コンテキスト:
{context}

質問:
{question}
```

このプロンプトは、以下の重要なテクニックを駆使しています。
*   **役割設定**: 「誠実で正確なアシスタント」というペルソナを設定。
*   **スコープの限定**: 「コンテキストの情報のみに基づいて」という指示で、知識の範囲を限定。
*   **否定的制約（ガードレール）**: 「分かりませんと明確に回答してください」という指示で、ハルシネーションを禁止し、安全な「出口」を提供。

### 3.3. 出力の整形 (Output Parsers)

アウトプットパーサーは、LLMからの非構造的なテキスト応答を、アプリケーションが確実に利用できる、予測可能な形式に変換します。

*   **StrOutputParser**: 最もシンプル。LLMの応答から文字列コンテンツのみを抽出します。
*   **JsonOutputParser**: LLMに構造化されたJSONオブジェクトを返すよう強制できます。LLMの出力をプログラムで利用する必要がある場合に不可欠です。これはLLMに対する堅牢な「API契約」として機能します。

## 4. 全体の組み立て：汎用RAGチェーン

これまでのコンポーネントをLCELで統合し、汎用的なRAGチェーンを構築します。

```python
# このスクリプトは、汎用的なドキュメントQ&AシステムのRAGパイプラインを示します。

import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

# --- 1. インジェストパイプライン ---
# (この部分は通常、一度だけ実行し、ベクトルストアを永続化する)

# PDF_PATH = "data/example-document.pdf"
# PERSIST_DIRECTORY = 'db/chroma_db'

# loader = PyMuPDFLoader(PDF_PATH)
# documents = loader.load()
# text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
# chunks = text_splitter.split_documents(documents)
# embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
# vectorstore = Chroma.from_documents(
#     documents=chunks, embedding=embeddings, persist_directory=PERSIST_DIRECTORY
# )

# --- 2. 生成パイプラインの構築 ---

# 既存のベクトルストアを読み込む
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
vectorstore = Chroma(persist_directory='db/chroma_db', embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# プロンプトテンプレートの定義
RAG_PROMPT_TEMPLATE = """提供されたコンテキストのみに基づき、質問に答えてください。
コンテキストに答えがなければ「分かりません」と回答してください。

コンテキスト:
{context}

質問:
{question}
"""
rag_prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

# LLMの初期化
llm = ChatOllama(model="llama3", temperature=0)

# アウトプットパーサー
output_parser = StrOutputParser()

# --- 3. LCELによるRAGチェーンの組み立て ---

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    RunnableParallel(
        context=(retriever | format_docs),
        question=RunnablePassthrough()
    )
    | rag_prompt
    | llm
    | output_parser
)

# --- 4. チェーンの実行 ---
if __name__ == "__main__":
    query = "このドキュメントの要点は何ですか？"
    response = rag_chain.invoke(query)
    print(response)
```

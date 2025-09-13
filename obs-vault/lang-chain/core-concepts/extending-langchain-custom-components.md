---
tags:
  - langchain
  - core-concept
  - customization
  - runnable
  - tool
  - retriever
---
# LangChainの拡張：カスタムコンポーネントの構築

LangChainは、既製のコンポーネントを組み合わせることで迅速にAIアプリケーションを構築できる強力なフレームワークですが、その真の力は**拡張性**にあります。エンタープライズ環境では、社内独自のAPI、特殊なデータソース、または特定のビジネスロジックをLangChainのエコシステムに統合する必要が頻繁に生じます。

この記事では、LangChainの核心である`Runnable`プロトコルを実装し、カスタムLLM、カスタムRetriever、そしてカスタムToolを作成する方法を解説します。これにより、開発者はLangChainを自身の環境に完全に適合させることができます。

---

## 1. Runnableプロトコル：カスタムコンポーネントの心臓部

LCEL（LangChain Expression Language）でコンポーネントを `|` パイプで繋げられるのは、全てのコンポーネントが`Runnable`という共通のインターフェースを実装しているからです。カスタムコンポーネントを作成するということは、本質的には`Runnable`プロトコルに準拠したクラスを作成することです。

`Runnable`を継承し、`invoke`メソッド（または非同期の`ainvoke`）を実装するだけで、そのクラスはLCELチェーンの一部として振る舞えるようになります。

```python
from typing import Any, Dict, Iterator
from langchain_core.runnables import Runnable, RunnableConfig

class MyCustomRunnable(Runnable):
    """
    Runnableプロトコルを実装した最もシンプルなカスタムコンポーネント。
    入力を受け取り、加工して出力します。
    """
    def invoke(self, input: Dict[str, Any], config: RunnableConfig | None = None) -> Dict[str, Any]:
        # ここに独自のロジックを実装
        processed_output = f"入力されたメッセージは「{input['message']}」でした。"
        return {"response": processed_output}

# カスタムコンポーネントのインスタンス化
custom_runnable = MyCustomRunnable()

# LCELチェーンに組み込む
# response = custom_runnable.invoke({"message": "こんにちは"})
# print(response)
# -> {'response': '入力されたメッセージは「こんにちは」でした。'}
```
このシンプルな実装だけで、`.stream()`, `.batch()`, `.ainvoke()` といった強力な本番運用機能が自動的に付与されます。これが`Runnable`プロトコルの力です。

---

## 2. カスタムLLMの作成

LangChainがネイティブサポートしていないLLM（例：社内開発の推論API、特殊なオープンソースモデル）を使いたい場合、`_llm_type`を定義し、`_call`メソッドを実装することで、独自のLLMクラスを作成できます。

`SimpleLLM`を継承するのが最も簡単な方法です。

```python
from typing import Any, List, Optional
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.llms import SimpleLLM
import requests # 例としてrequestsを使用

class MyCustomLLM(SimpleLLM):
    """
    社内の独自APIを叩くカスタムLLMの例。
    """
    api_url: str = "http://my-internal-llm-api/generate"

    @property
    def _llm_type(self) -> str:
        return "my_custom_llm"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        # ここで独自APIを呼び出す
        try:
            response = requests.post(
                self.api_url,
                json={"prompt": prompt, "stop": stop, **kwargs},
                timeout=10 # タイムアウトを設定
            )
            response.raise_for_status() # HTTPエラーチェック
            return response.json()["text"]
        except requests.RequestException as e:
            return f"API呼び出しエラー: {e}"

# カスタムLLMをチェーンで使用
# llm = MyCustomLLM()
# response = llm.invoke("自己紹介してください。")
# print(response)
```

これで、この`MyCustomLLM`は`ChatOpenAI`などと同様に、プロンプトテンプレートやアウトプットパーサーと自由に組み合わせることができます。

---

## 3. カスタムRetrieverの作成

RAGにおいて、情報はベクトルストア以外にも存在します（例：SQLデータベース、Elasticsearch、社内ドキュメントAPI）。`BaseRetriever`を継承することで、あらゆるソースからドキュメントを取得するカスタムリトリーバーを作成できます。

重要なのは、`_get_relevant_documents`メソッドを実装することです。

```python
from typing import List
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

class SqlDatabaseRetriever(BaseRetriever):
    """
    SQLデータベースから直接ドキュメントを検索するカスタムリトリーバーの例。
    """
    db_connection: Any # 実際のDB接続オブジェクトを想定

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        # SQLインジェクション対策を必ず行うこと！
        # ここでは例として単純なクエリを実行
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT content, source FROM documents WHERE content LIKE %s", (f"%{query}%",))

        docs = []
        for row in cursor.fetchall():
            content, source = row
            docs.append(Document(page_content=content, metadata={"source": source}))

        return docs

# RAGチェーンでの使用
# db_retriever = SqlDatabaseRetriever(db_connection=my_db_conn)
# retrieved_docs = db_retriever.get_relevant_documents("特定のキーワード")
# print(retrieved_docs)
```
この`SqlDatabaseRetriever`は、LCELの`RunnableParallel`と組み合わせることで、標準的なRAGパイプラインにシームレスに組み込むことができます。

---

## 4. カスタムToolの作成

エージェントに独自の能力を付与するには、カスタムツールを作成します。最も簡単な方法は`@tool`デコレータを使うことです。

### 4.1. `@tool`デコレータによるシンプルなツール

```python
from langchain_core.tools import tool
import datetime

@tool
def get_current_datetime(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    現在の日時を指定されたフォーマットで返します。
    引数がない場合は、デフォルトのフォーマットが使用されます。
    """
    return datetime.datetime.now().strftime(format)

# エージェントに渡すツールのリストに含める
# tools = [get_current_datetime]
```
LangChainは関数のdocstringを読み取り、ツール名、説明、引数スキーマを自動的に推論し、LLMに提供します。

### 4.2. `BaseTool`を継承した高度なツール

より複雑な入力スキーマ（例：複数の引数）や、非同期実行を制御したい場合は、`BaseTool`を継承します。入力スキーマはPydanticモデルで定義するのがベストプラクティスです。

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

class SearchCustomerInput(BaseModel):
    customer_id: str = Field(description="検索対象の顧客ID")
    include_history: bool = Field(default=False, description="取引履歴を含めるかどうか")

class CustomerSearchTool(BaseTool):
    name = "search_customer_info"
    description = "顧客IDで顧客情報を検索します。"
    args_schema: Type[BaseModel] = SearchCustomerInput

    def _run(self, customer_id: str, include_history: bool = False) -> dict:
        # ここで社内DBやCRM APIを呼び出すロジックを実装
        return {
            "customer_id": customer_id,
            "name": "山田 太郎",
            "status": "active",
            "history": [...] if include_history else "not requested"
        }

# エージェントに渡すツールのリストに含める
# tools = [CustomerSearchTool()]
```
Pydanticモデルを使うことで、LLMはより構造化された方法でツールを呼び出すことができ、入力のバリデーションも自動的に行われます。

## まとめ

LangChainの拡張性は、プロトタイピングから本番システムへの移行を成功させるための鍵です。`Runnable`プロトコルを理解し、カスタムコンポーネントを作成する能力を身につけることで、開発者はLangChainをあらゆるビジネス要件や技術的制約に適応させることができます。

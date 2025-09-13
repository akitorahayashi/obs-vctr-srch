---
tags:
  - langchain
  - application-pattern
  - agent
  - tool
---
# アプリケーションパターン：エージェント設計とツールの利用

RAGが外部知識を用いてLLMの応答を強化するのに対し、**エージェント**はLLMを単なるテキスト生成器としてではなく、**推論エンジン（reasoning engine）**として活用し、与えられた目標を達成するために自律的に行動するシステムです。

エージェントは、固定された処理経路をたどるのではなく、実行時に自ら経路を決定します。高レベルの目標を与えられると、その目標を達成するために必要なサブタスクを自ら計画し、利用可能な**ツール**を取捨選択し、実行します。

## 1. エージェントの思考フレームワーク

### 1.1. ReAct：推論と行動のループ

エージェントの自律的な判断を支える最も基本的な概念が **ReAct (Reasoning and Acting)** フレームワークです。その核心的なアイデアは、LLMの生成プロセスに**推論の軌跡（reasoning traces）**、すなわち「思考」と、**タスク固有の行動（task-specific actions）**、すなわち「ツールの使用」を交互に織り交ぜることにあります。

この認知サイクルは、**思考 → 行動 → 観察 (Thought → Action → Observation)** という3つのステップの反復によって構成されます。

1.  **思考 (Thought):** エージェントはまず、要求を分析し、行動計画を立てます。「私は2つの情報を見つける必要がある。まずAを検索し、次にBを検索しよう。」
2.  **行動 (Action):** この思考に基づき、エージェントは特定のツールを使用することを決定し、`Action: search(query="A")` のような構造化された行動を生成します。
3.  **観察 (Observation):** ツールの実行結果を観察します。「AはXであることがわかった。」
4.  **反復:** この観察結果に基づき、次の思考を巡らせます。「Aはわかった。次にBを調べよう。」そして、新たな行動 `Action: search(query="B")` を生成します。このループは、当初の目標を達成するまで続きます。

### 1.2. ReAct vs ネイティブTool-Calling

ReActはプロンプト技術だけでエージェントの思考ループを実現する画期的な方法ですが、現代の高性能なLLM（OpenAI, Google, Anthropicのモデルなど）は、より効率的な**ネイティブTool-Calling**（またはFunction-Calling）機能をモデル自体に組み込んでいます。

以下の表は、両者のアプローチを比較したものです。

| 特徴 | ReActエージェント (`create_react_agent`) | ネイティブTool-Callingエージェント (`create_tool_calling_agent`) |
| :---- | :---- | :---- |
| **メカニズム** | LLMがテキストで「思考」と「行動」を生成し、フレームワークがそれを解析してツールを実行する。 | LLMがツール利用の必要性を検知し、呼び出すべき関数名と引数を構造化されたJSONオブジェクトとして直接出力する。 |
| **効率性** | 比較的非効率。思考プロセスをテキストで記述するため、トークン消費量と遅延が大きい。 | 効率的。一度のやり取りで複数のツール呼び出しを計画できることもあり、トークン使用量と遅延が少ない。 |
| **LLM互換性** | 高い。強力な指示追従能力を持つLLMであれば、どのモデルでも動作する可能性がある。 | 低い。専用のTool-Calling APIを持つようにファインチューニングされたモデルでのみ動作する。 |
| **透明性** | 非常に高い。思考プロセス全体が明示的に出力されるため、デバッグが容易。 | デフォルトでは低い。推論はモデル内部で行われる。LangSmithのようなツールでの観察が重要。 |
| **理想的な用途** | 教育目的や、推論プロセスの最大限の透明性が必要な場合。Tool-Calling非対応モデルを使う場合。 | 効率、速度、信頼性が最優先される本番アプリケーション。**現代的な開発における推奨アプローチ。** |

ReActのパラダイムを理解することはエージェントの仕組みを学ぶ上で不可欠ですが、実用的なアプリケーションでは、対応モデルを使用している限り、ネイティブTool-Callingがより優れた選択肢となります。

## 2. エージェントの実行エンジン：AgentExecutor

`AgentExecutor`は、エージェントに生命を吹き込む中核コンポーネントです。前述の「思考 → 行動 → 観察」ループを実際に実行する役割を担います。

その責務は以下の通りです。
1.  エージェント（LLM、プロンプト、ツール群の集合体）を呼び出し、次の`Action`を取得する。
2.  その`Action`を、対応するツールを呼び出すことで実行する。
3.  ツールの出力を`Observation`として捕捉する。
4.  その`Observation`をエージェントにフィードバックする。
5.  エージェントが最終的な回答（`AgentFinish`）を出力するまでこのプロセスを繰り返す。

```python
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor

# 1. ツールの準備
tools = [TavilySearchResults(max_results=1)]

# 2. LLMとプロンプトの準備
prompt = hub.pull("hwchase17/react")
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# 3. エージェントの作成
agent = create_react_agent(llm, tools, prompt)

# 4. AgentExecutorの初期化
# verbose=Trueにすると、思考プロセスがコンソールに出力される
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 5. 実行
# response = agent_executor.invoke({"input": "2024年の夏季オリンピックはどこで開催されますか？"})
```

`AgentExecutor`は単一エージェントのループ処理に特化しています。複数のエージェントが協調するような、より複雑なワークフローには**LangGraph**が適しています。

## 3. 能力の拡張：カスタムツールの作成

エージェントの能力は、利用できるツールの質と量に直結します。LangChainでは、簡単なPython関数からカスタムツールを容易に作成できます。

### 3.1. `@tool`デコレータによるツール作成

最もPythonicで推奨される方法は`@tool`デコレータを使用することです。このデコレータは、Python関数からLLMが理解できるツールのスキーマを賢く推論します。

*   **関数名**が`tool.name`になります。
*   **関数のdocstring**が`tool.description`になります。**これは最も重要です。** LLMはこの説明を読んで、いつ、なぜこのツールを使うべきかを判断します。
*   **関数の型ヒント**と`Annotated`型が、`tool.args_schema`（引数の仕様）を自動的に生成します。

```python
from langchain_core.tools import tool
from typing import Annotated
import yfinance as yf

@tool
def get_stock_price(
    symbol: Annotated[str, "The stock ticker symbol for a public company, e.g., 'AAPL' for Apple."]
) -> str:
    """
    Fetches the current stock price for a given ticker symbol.
    Use this tool when you need to find the latest financial market price of a public company.
    """
    try:
        ticker = yf.Ticker(symbol)
        todays_data = ticker.history(period='1d')
        if not todays_data.empty:
            return f"${todays_data['Close'].iloc[-1]:.2f}"
        else:
            info = ticker.info
            price = info.get('regularMarketPrice')
            return f"${price:.2f}" if price else "Price not available"
    except Exception as e:
        return f"Error fetching stock price for {symbol}: {e}"

# これで、このツールをエージェントのツールリストに追加できる
# new_tools = [TavilySearchResults(max_results=1), get_stock_price]
```
この例は、**質の高い、クリーンで、十分に文書化されたPythonコードを書くことが、効果的なAIエージェントツールを作成することに直結する**という強力な関係性を示しています。

### 3.2. カスタムツール設計のベストプラクティス

効果的なツールを作成するための設計原則を以下にまとめます。

| 原則 | 説明 | 悪い例 | 良い例 |
| :---- | :---- | :---- | :---- |
| **説明的な命名** | ツールの名前は、その行動を明確に示す動詞-名詞のペアであるべきです。 | `data_getter` | `get_user_profile` |
| **正確な説明** | 説明はLLMにとっての唯一の真実の源です。ツールが*何をするか*だけでなく、*いつ*、*なぜ*使うべきかを説明する必要があります。 | `"""ユーザープロファイルを取得する。"""` | `"""ユーザー名、メールアドレス、登録日を含むユーザープロファイル情報を取得します。特定のユーザーIDに基づいてユーザーの詳細を取得する必要がある場合に使用してください。"""` |
| **具体的な引数スキーマ** | すべての引数に型ヒントと`Annotated`による説明を使用します。これにより、LLMはどのような種類のデータをどのような形式で提供すべきかを正確に理解します。 | `def get_user(id):` | `def get_user(user_id: Annotated[int, "ユーザーの一意な数値識別子。"]):` |
| **堅牢なエラー処理** | ツールはエージェントをクラッシュさせてはいけません。例外を捕捉し、エージェントが自己修正に利用できるような、役立つ説明的なエラーメッセージを返すべきです。 | `return api.get(id)` | `try:... except APIError as e: return f"エラー: ID {user_id} のユーザーが見つかりませんでした。{e}"` |
| **単一責任の原則** | ツールは一つのことをうまくやるべきです。複数の関連しないアクションを実行するモノリシックなツールを作成することは避けてください。 | `user_and_product_tool()` | `get_user_profile()` と `get_product_details()` |

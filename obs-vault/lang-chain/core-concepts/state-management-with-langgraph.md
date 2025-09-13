---
tags:
  - langchain
  - core-concept
  - langgraph
  - state-management
---
# LangGraphによる状態管理：エージェントのためのステートマシン構築

LCELが直線的なワークフロー（DAG）の構築に優れているのに対し、自律的なエージェントは、試行錯誤（ループ）や状況に応じた判断（分岐）といった、より複雑な振る舞いを必要とします。LangGraphは、このようなエージェント的振る舞いを実現するために、LLMアプリケーションを**ステートマシン**または**巡回可能なグラフ（Cyclic Graph）**としてモデル化する、新しいパラダイムを提供します。

このアーキテクチャの中心にあるのが、堅牢な**状態（State）管理**です。

## LangGraphのコアコンポーネント

LangGraphアプリケーションは、主に`State`、`Node`、`Edge`という3つの基本要素を、`StateGraph`（または`StatefulGraph`）というキャンバス上に配置していくことで構築されます。

### 1. StateGraph：エージェントの設計図

`StateGraph`は、ワークフローを構築するための中心的なクラスです。これは実質的にステートマシンビルダーであり、このオブジェクトにノードとエッジを追加していくことで、エージェントの振る舞いを定義します。グラフの構造を定義した後、`.compile()`メソッドを呼び出すことで、実行可能な`CompiledGraph`オブジェクトが生成されます。

```python
from langgraph.graph import StateGraph

# まずStateのスキーマを定義する必要がある（後述）
# class AgentState(TypedDict):
#     ...

workflow = StateGraph(AgentState)
```

### 2. State：エージェントの共有メモリと世界観

LangGraphにおいて最も重要な概念が**State**です。これは、グラフ全体で共有される単一のオブジェクトであり、すべてのノードに引数として渡されます。各ノードは現在の状態を読み取り、自身の処理結果を反映させるためにこのStateオブジェクトを更新します。Stateはアプリケーションの「唯一の真実の源（Single Source of Truth）」として機能します。

Stateのスキーマは、主にPython標準の`TypedDict`または、より堅牢な`pydantic.BaseModel`を用いて定義されます。

#### Stateを`TypedDict`で定義する

`TypedDict`は、軽量かつパフォーマンスに優れたState定義方法であり、公式ドキュメントでも標準的なアプローチとして紹介されています。特に、会話履歴のようにリストに要素を追加していくケースでは、`Annotated`と`add_messages`を組み合わせることで、Stateの更新が上書きではなく**追記**になるように指定できます。

```python
from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# StateをTypedDictで定義
class AgentState(TypedDict):
    # messagesキーには会話のメッセージリストを保持
    # add_messagesは、新しいメッセージをリストに追記することを指定する
    messages: Annotated[List[BaseMessage], add_messages]

    # 他のState変数も自由に追加できる
    # 例：リサーチ結果のサマリー
    research_summary: str
```

### 3. Nodes：アクションの実行単位

**Node**は、グラフ内で具体的な処理を行う「作業単位」です。実体は、Stateオブジェクトを引数として受け取り、そのStateを更新するための**部分的なState辞書**を返す、単純なPython関数またはLangChainの`Runnable`です。

以下は、LLMを呼び出してStateの`messages`を更新するノードの典型的な例です。返される辞書のキーは、更新対象のStateのキーと一致している必要があります。

```python
from langchain_openai import ChatOpenAI

# LLMの初期化
llm = ChatOpenAI(model="gpt-4o")

# ノードはStateを引数に取り、更新内容を辞書で返す関数
def call_llm_node(state: AgentState) -> dict:
    messages = state['messages']
    # LLMを呼び出す
    response = llm.invoke(messages)
    # 更新するStateのキー（'messages'）と値を返す
    # AgentStateの`add_messages`指定により、このレスポンスがリストに追加される
    return {"messages": [response]}

# "llm_caller"という名前でノードをグラフに追加
# workflow.add_node("llm_caller", call_llm_node)
```

### 4. Edges：ロジックと制御の経路

**Edge**は、ノード間の遷移を定義し、エージェントの制御フローを司ります。

#### シンプルなエッジ

`add_edge()`メソッドは、あるノードの処理が終わった後、次にどのノードを実行するかを固定的に定義します。`START`と`END`という特別な名前を使って、グラフの開始点と終了点を指定します。

```python
from langgraph.graph import START, END

# STARTから"llm_caller"ノードへ遷移するエッジを追加
# workflow.add_edge(START, "llm_caller")

# "llm_caller"ノードからENDへ遷移するエッジを追加
# workflow.add_edge("llm_caller", END)
```

#### 条件付きエッジ：エージェント知能の心臓部

エージェントが自律的に振る舞うための鍵となるのが**Conditional Edge**です。`add_conditional_edges()`メソッドは、あるノードの実行結果（State）に基づいて、次に進むべきパスを動的に決定することを可能にします。これにより、**ループ**や**分岐**が実現されます。

条件付きエッジは、3つの要素で構成されます：
1.  **分岐元のノード名**：このノードの実行後に判断が行われます。
2.  **判断関数（Decider Function）**：Stateを引数に取り、次に進むべきエッジの名前を文字列で返します。
3.  **マッピング辞書**：判断関数の返す文字列と、遷移先のノード名を対応付けます。

以下のコードは、LLMがツールを呼び出すべきか判断し、処理を分岐させる典型的な例です。

```python
from typing import Literal
from langchain_core.messages import AIMessage

# 判断関数：Stateを調べて、次の遷移先を決定する
def should_use_tool(state: AgentState) -> Literal["use_tool", "__end__"]:
    # 最後のメッセージを取得
    last_message = state['messages'][-1]
    # AIMessageにtool_calls属性があればツール使用と判断
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "use_tool" # "use_tool"という名前のエッジに進む
    else:
        return "__end__" # "__end__"という名前のエッジ（グラフの終端）に進む

# tool_executorノード（ダミー）を定義
def dummy_tool_node(state: AgentState) -> dict:
    # 実際にはここでツールを実行し、結果をToolMessageとして返す
    print("ツールを実行しました。")
    # この例ではStateを更新しないが、実際はToolMessageを返す
    # return {"messages": [ToolMessage(...)]}
    return {}

# workflow.add_node("tool_executor", dummy_tool_node)

# 条件付きエッジをグラフに追加
# "llm_caller"ノードの後に、should_use_tool関数で判断を行う
# workflow.add_conditional_edges(
#     "llm_caller",          # 分岐元のノード
#     should_use_tool,       # 判断関数
#     {
#         "use_tool": "tool_executor", # "use_tool"と返されたら"tool_executor"ノードへ
#         "__end__": END               # "__end__"と返されたらグラフを終了
#     }
# )

# ツール実行後は再びLLMに判断を仰ぐためのエッジを追加し、ループを完成させる
# workflow.add_edge("tool_executor", "llm_caller")
```

LangGraphのこの構造は、開発者に優れたソフトウェア設計を半ば強制します。巨大で複雑なプロンプトを持つ一つの万能エージェントを作るのではなく、問題を個別の論理的なステップ（Node）に分解し、共有すべきデータを明確に定義し（State）、そして制御フローを明示的に設計する（Edge）ことを促します。これは、LLMアプリケーション開発を、場当たり的なプロンプトエンジニアリングから、テスト可能で保守性の高いコンポーネントを組み合わせる体系的なソフトウェアアーキテクチャの設計へと引き上げる、強力なデザインパターンなのです。

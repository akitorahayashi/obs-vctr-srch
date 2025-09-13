---
tags:
  - langchain
  - application-pattern
  - multi-agent
  - langgraph
  - architecture
---
# アプリケーションパターン：マルチエージェント・オーケストレーション

単一のエージェントでも、ツールとループ（自己修正）を組み合わせることで多くのタスクをこなせますが、より複雑で大規模な問題を解決するためには、複数の専門エージェントがチームとして協調する**マルチエージェントシステム（Multi-Agent System, MAS）**の構築が必要になります。

## 1. なぜマルチエージェントなのか？

一つのエージェントにあまりにも多くのツールや責任を持たせると、どのツールをいつ使うべきかの判断が困難になり、性能が低下します。これは「認知過負荷」とも呼べる問題です。マルチエージェントシステムは、この問題を**モジュール性**と**専門性**によって解決します。

*   **モジュール性と専門性**: システムを専門的な役割を持つ複数のエージェントに分割することで、各エージェントはより少ないツールセットと、より焦点を絞ったプロンプトでタスクに取り組むことができます。例えば、コンテンツ制作において、「リサーチ担当」「執筆担当」「校正担当」を分けることで、各エージェントの性能が向上し、システム全体の開発、テスト、保守が容易になります。
*   **制御とスケーラビリティ**: エージェント間の情報伝達やタスクの引き渡しを明示的に制御できます。将来的に新しい機能（例：「画像生成エージェント」）を追加したい場合も、既存のシステムを壊すことなく、新しいエージェントを独立したコンポーネントとしてワークフローに組み込むだけで済みます。

## 2. なぜLangGraphが必要なのか？

このようなマルチエージェントの協調動作、特にレビューによる差し戻し（ループ）や、状況に応じたタスクの割り振り（条件分岐）は、LCELの直線的なパイプライン（DAG）では表現できません。

LangGraphは、エージェントシステムを**巡回可能なグラフ（Cyclic Graph）**としてモデル化することで、この課題を解決します。
*   **サイクルの実現**: 「執筆エージェント」が作成したドラフトを「校正エージェント」がレビューし、問題があればフィードバックを付けて差し戻す、といったループを自然に構築できます。
*   **明示的な状態管理**: ワークフロー全体の進捗（リサーチ結果、ドラフト、フィードバックなど）を単一の`State`オブジェクトで一元管理し、エージェント間で引き継ぐことができます。
*   **動的な制御フロー**: `State`の内容に応じて、次にどエージェントを呼び出すかを動的に決定できます。

## 3. オーケストレーション・アーキテクチャパターン

マルチエージェントシステムを成功させる鍵は、各エージェントの協調動作をいかにして指揮（オーケストレーション）するかです。LangGraphでは、いくつかの確立されたアーキテクチャパターンを用いてこれを実現します。

### 3.1. スーパーバイザー（監督者）パターン

これは、最も一般的で実用的なパターンであり、ハブ・アンド・スポーク型のモデルと考えることができます。中央に**スーパーバイザー（Supervisor）**となるエージェント（またはルーター関数）を配置し、このスーパーバイザーが全体のタスク管理を行います。

1.  ユーザーからのリクエストをまずスーパーバイザーが受け取ります。
2.  スーパーバイザーはタスクの現状（State）を分析し、次にどの専門エージェントに作業を割り振るべきかを決定します。
3.  指名された専門エージェントは自身のタスクを実行し、結果をStateに書き込みます。
4.  制御が再びスーパーバイザーに戻り、スーパーバイザーは更新されたStateを見て、次のステップを決定します（別のエージェントに引き継ぐか、タスクを完了するか）。

このパターンは、「リサーチ → 構成案作成 → 執筆 → レビュー」といった明確な手順を持つワークフローに最適です。

#### なぜスーパーバイザーが重要なのか？
エージェントが自由に通信しあうと、カオス的で予測不能、かつ高コストな実行パスを生み出す危険性があります。スーパーバイザーは、この問題を解決するための**中央制御プレーン**として機能します。各ステップで「正気度のチェック」を行い、全体の進捗を評価し、目標達成のために次に行うべき最も論理的でコスト効率の良いステップを意図的に選択します。つまり、スーパーバイザーパターンは、システム全体の信頼性、予測可能性、そしてコストを管理するための、極めて重要な設計判断なのです。

### 3.2. その他のパターン

*   **階層（ヒエラルキー）パターン**: スーパーバイザーパターンを一般化し、組織図のように階層化したものです。トップレベルのスーパーバイザーが「チームリーダー」役のサブ・スーパーバイザーを管理し、そのサブ・スーパーバイザーがさらに個々の専門エージェントを管理します。再帰的に分割可能な大規模タスクに適しています。
*   **ネットワーク（協調）パターン**: より分散的なモデルで、エージェントが直接他のエージェントにタスクを引き渡すことができます。次に取るべき行動が予測しにくい、より動的で対話的なシナリオ（例：コーダーとテスターのやり取り）に適していますが、制御が難しくなる可能性があります。

### 3.3. パターン選択ガイド

| パターン | 制御フロー | コミュニケーション | 最適な用途 | 主要な課題 |
| :---- | :---- | :---- | :---- | :---- |
| **スーパーバイザー** | 中央集権型（ハブ＆スポーク） | エージェント → 監督者 → エージェント | 明確なステップを持つ定義済みワークフロー（コンテンツ制作、ソフトウェア開発など） | 監督者がボトルネックになる可能性 |
| **階層型** | ツリー構造 | 監督者 → サブ監督者 → エージェント | 再帰的に分割可能な非常に大規模で複雑なタスク | 複数階層にわたる状態とコンテキストの管理 |
| **ネットワーク型** | 分散型（ピアツーピア） | エージェント → エージェント | 次のステップが予測不能な動的・対話的なタスク | 無限ループの防止とタスク完了の保証 |

## 4. 実装例：スーパーバイザーパターンによるコンテンツ制作ワークフロー

スーパーバイザーパターンを用いて、与えられたトピックに関するコンテンツを生成するワークフローを構築する例を示します。

```python
from langgraph.graph import StateGraph, END
from typing import List, Optional
from pydantic import BaseModel, Field

# 1. ワークフローの状態を定義
class ContentWorkflowState(BaseModel):
    topic: str
    research_data: Optional[List[dict]] = Field(default_factory=list)
    draft_article: Optional[str] = None
    review_feedback: List[str] = Field(default_factory=list)

# 2. 各エージェントをNodeとして定義
def researcher_node(state: ContentWorkflowState) -> dict:
    print("--- 専門エージェント: Researcher ---")
    # Web検索などを実行
    research_data = [{"summary": f"{state['topic']}に関するリサーチ結果"}]
    return {"research_data": research_data}

def writer_node(state: ContentWorkflowState) -> dict:
    print("--- 専門エージェント: Writer ---")
    # リサーチ結果とフィードバックを基に執筆
    draft_article = f"トピック「{state['topic']}」についての記事ドラフトです。"
    if state['review_feedback']:
        draft_article += f"\nフィードバックを反映しました: {state['review_feedback']}"
    return {"draft_article": draft_article, "review_feedback": []}

def reviewer_node(state: ContentWorkflowState) -> dict:
    print("--- 専門エージェント: Reviewer ---")
    # ドラフトをレビュー
    # この例では、初回は必ず修正を要求し、2回目で承認する
    if len(state['review_feedback']) == 0:
        print("レビュー結果: 修正要求")
        return {"review_feedback": ["もっと具体的に記述してください。"]}
    else:
        print("レビュー結果: 承認")
        return {"review_feedback": []}

# 3. スーパーバイザーを条件付きエッジのルーターとして定義
def supervisor_router(state: ContentWorkflowState) -> str:
    print("--- スーパーバイザー: 次のタスクを決定 ---")
    if not state.research_data:
        return "researcher"
    if not state.draft_article or state.review_feedback:
        return "writer"
    if state.draft_article and not state.review_feedback:
        return "reviewer"

def review_router(state: ContentWorkflowState) -> str:
    if state.review_feedback:
        return "writer" # 差し戻し
    else:
        return "__end__" # 完了

# 4. グラフを構築
workflow = StateGraph(ContentWorkflowState)

workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)
workflow.add_node("reviewer", reviewer_node)

# スーパーバイザーを介さずに、固定のフローで接続
workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", "reviewer")

# レビュー後の分岐を定義
workflow.add_conditional_edges(
    "reviewer",
    review_router,
    {
        "writer": "writer",
        "__end__": END
    }
)

# 5. 実行
app = workflow.compile()
final_state = app.invoke({"topic": "マルチエージェントシステムの未来"})

# print(final_state['draft_article'])
```
この例では、固定のフローと条件分岐を組み合わせていますが、より高度なスーパーバイザーは、各ノードの実行後に呼び出され、次に実行すべきノードをLLMの推論によって決定します。これにより、より動的でインテリジェントなタスクの割り振りが可能になります。

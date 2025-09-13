---
tags:
  - langchain
  - core-concept
  - lcel
  - runnable
---
# LCELとRunnableプロトコル：宣言的なAIワークフローの構築

LangChain Expression Language (LCEL) は、AIアプリケーションのコンポーネントを宣言的に組み合わせるための、現代的で強力なフレームワークです。これは、LangChainにおけるアプリケーション構築の標準的な方法であり、その核心には **Runnable** プロトコルが存在します。

## 1. LCELの設計思想とRunnableプロトコル

LCELの基本的な考え方は、プロンプト、モデル、パーサー、リトリーバーといった全ての構成要素を、共通のインターフェースである `Runnable` に準拠させることです。これにより、パイプ演算子 `|` を使って、これらのコンポーネントをまるでシェルのパイプラインのように流れるように繋ぎ合わせ、一連の処理（チェーン）を直感的に構築できます。

LCELは、旧来の`LLMChain`のようなクラスベースのアプローチに代わるものです。古いアプローチではプロンプトなどの内部実装が隠蔽されがちでしたが、LCELは各コンポーネントの連携を明示的に記述するため、透明性、構成可能性、そしてカスタマイズ性が飛躍的に向上しています。

### Runnableプロトコルがもたらす本質的な価値

LCELを採用する最大の利点は、単に構文が簡潔になることだけではありません。それは、LCELでチェーンを定義するだけで、**本番環境で求められる多くの機能が自動的に付与される**点にあります。

この強力な利点は、次のようなシナリオを想定すると明確になります。

1.  **手動実装のシナリオ**: 開発者がRAG（Retrieval-Augmented Generation）の処理フローをPythonの関数として手動で実装したとします。この関数は、リトリーバーを呼び出し、結果を整形し、LLM APIを呼び出して結果を返します。
2.  **要件変更1（ストリーミング）**: 次に、プロダクトマネージャーから「ユーザー体験向上のため、回答をトークン単位でリアルタイムに表示したい」という要求が来たとします。手動実装の場合、この要求に応えるには、非同期ジェネレータを使うなど、関数全体を根本的に書き直す必要があります。
3.  **要件変更2（バッチ処理）**: さらに、データサイエンスチームから「1万件のサンプル質問を一晩で処理したい」という要求が来たとします。これには、並列処理やバッチ処理のロジックを追加するために、再びコードを書き直す必要があります。
4.  **LCELによる解決**: LCELは、この種の複雑性を抽象化します。開発者は `my_chain = ...` のようにチェーンを宣言的に定義することで、「何を」するかを記述し、「どのように」実行するかはLangChainフレームワークに委ねます。
5.  **実行インターフェースの多様性**: 全てのコンポーネントが`Runnable`インターフェースに準拠しているため、LangChainが実行ロジックを提供します。したがって、**全く同じ`my_chain`オブジェクト**に対して、以下のような異なるメソッドを呼び出すだけで、様々な実行方法に対応できます。
    *   `.invoke()`: 単一の同期的な呼び出し
    *   `.stream()`: トークンのストリーミング配信用イテレータの取得
    *   `.batch()`: 入力リストの並列処理
    *   `.ainvoke()`: 単一の非同期的な呼び出し
    *   `.astream()`: 非同期ストリーミング
    *   `.abatch()`: 非同期バッチ処理

このように、LCELで構築されたチェーンは、定義したその瞬間から、APIサーバー、リアルタイムチャットボット、バッチ処理ジョブといった多様な本番環境に本質的に対応可能です。これは、プロトタイプから本番稼働までの道のりを加速させる強力な特徴です。

## 2. 非線形データフローの実現

LCELは直線的なパイプラインだけでなく、より複雑なデータフローもエレガントに扱うことができます。特にRAGのようなアプリケーションでは、ユーザーの入力（質問）を、リトリーバーへの入力と、最終的なプロンプトへの入力の両方で使う必要があります。このような分岐・合流は `RunnableParallel` と `RunnablePassthrough` を使って実現します。

### RunnableParallelとRunnablePassthrough

*   **RunnablePassthrough**: チェーンのあるステップで入力を変更せずにそのまま次のステップに渡すための、シンプルですが不可欠なユーティリティです。
*   **RunnableParallel**: 辞書形式 `{...}` で表現され、複数のRunnableを並行して実行し、その結果をキーに対応する値として持つ辞書を生成します。

RAGチェーン構築における中心的な課題は、初期入力であるユーザーの質問が、(1)リトリーバーによるドキュメント検索と、(2)LLMへの最終的なプロンプト作成、という2つの異なる段階で必要になることです。単純な線形パイプ`(question | retriever | prompt)`では、リトリーバーが`Document`オブジェクトのリストを出力した時点で元の質問文字列が失われてしまうため、この課題を解決できません。

この課題に対するLCELの洗練された解決策が、`RunnableParallel`と`RunnablePassthrough`の組み合わせです。

```python
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

# retrieverは事前に定義されたRunnableとする
# retriever = vectorstore.as_retriever()

setup_and_retrieval = RunnableParallel(
    context=retriever,
    question=RunnablePassthrough()
)
```

この並列ステップがユーザーの質問文字列で呼び出されると、LangChainは両方のパスを並行して実行します。

1.  `retriever.invoke(question)` を呼び出し、その結果（ドキュメントのリスト）を`context`キーに割り当てます。
2.  `RunnablePassthrough.invoke(question)` を呼び出し、入力された質問文字列をそのまま返し、それを`question`キーに割り当てます。

この並列ステップの出力は `{"context": [docs], "question": "original_question"}` という形式の辞書になります。この辞書は、後続のプロンプトが必要とする入力スキーマと完全に一致するため、チェーンはスムーズに処理を続行できます。このエレガントなパターンは、LCELで複雑な非線形データフローを構築するための基本です。

### 完全なチェーンの組み立て

上記の並列処理を組み込むと、典型的なRAGチェーンは以下のようになります。

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

# 事前に定義されているとする
# retriever = ...
# prompt = ChatPromptTemplate.from_template(...)
# llm = ChatOpenAI(...)

def format_docs(docs):
    """取得したドキュメントを結合して単一の文字列にする"""
    return "\n\n".join(doc.page_content for doc in docs)

# 並列処理でコンテキストと質問を準備
setup_and_retrieval = RunnableParallel(
    context=(retriever | format_docs),
    question=RunnablePassthrough()
)

# 完全なRAGチェーン
rag_chain = (
    setup_and_retrieval
    | prompt
    | llm
    | StrOutputParser()
)

# 実行
# response = rag_chain.invoke("ユーザーの質問をここに入力")
```

このように、LCELは単純なシーケンシャル処理から、分岐や合流を含む複雑なワークフローまで、一貫した宣言的な構文で表現する能力を提供します。これは、読みやすく、保守しやすく、そして拡張性の高いAIアプリケーションを構築するための強力な基盤となります。

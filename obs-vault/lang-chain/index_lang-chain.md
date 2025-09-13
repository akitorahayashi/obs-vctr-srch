# LangChain 総合ナレッジベース

このナレッジベースは、LangChainを用いたエンタープライズレベルのAIアプリケーション開発における、汎用的な設計原則、アーキテクチャパターン、および運用プラクティスを体系的にまとめたものです。

特定のユースケース（FAQボットなど）から抽象化され、技術レイヤー別に再構成されています。各記事は、理論的背景と実践的なベストプラクティスを両立させることを目指しています。

---

## 1. 基盤レイヤー: Core Concepts

LangChainの根幹をなす概念と思想について解説します。ここから始めることを推奨します。

| 記事名                               | 難易度 | 対象読者                  | 前提知識 |
| ------------------------------------ | ------ | ------------------------- | -------- |
| [[core-concepts/lcel-and-runnable-protocol]] | 初級 | 全てのLangChain開発者 | なし |
| [[core-concepts/state-management-with-langgraph]] | 中級 | 自律型エージェントを構築する開発者 | [[core-concepts/lcel-and-runnable-protocol]] |
| [[core-concepts/extending-langchain-custom-components]] | 中級-上級 | 独自のコンポーネントを実装する開発者 | [[core-concepts/lcel-and-runnable-protocol]] |

---

## 2. アプリケーションレイヤー: Application Patterns

LangChainを用いて構築される代表的なアプリケーションの、汎用的なアーキテクチャパターンを解説します。

| 記事名                               | 難易度 | 対象読者                  | 前提知識 |
| ------------------------------------ | ------ | ------------------------- | -------- |
| [[application-patterns/rag-architectures]] | 初級-中級 | RAGシステムを構築する開発者 | [[core-concepts/lcel-and-runnable-protocol]] |
| [[application-patterns/agent-design-and-tool-use]] | 中級 | 単一の自律型エージェントを構築する開発者 | [[application-patterns/rag-architectures]] |
| [[application-patterns/multi-agent-orchestration]] | 上級 | 複数のエージェントが協調する複雑なワークフローを設計するアーキテクト | [[core-concepts/state-management-with-langgraph]], [[application-patterns/agent-design-and-tool-use]] |

---

## 3. 運用レイヤー: Operations and MLOps

開発したアプリケーションを、信頼性の高い本番システムとして運用するためのプラクティスを解説します。

| 記事名                               | 難易度 | 対象読者                  | 前提知識 |
| ------------------------------------ | ------ | ------------------------- | -------- |
| [[operations-and-mlops/observability-and-debugging]] | 中級 | 本番システムの開発・運用担当者 | [[application-patterns/agent-design-and-tool-use]] |
| [[operations-and-mlops/evaluation-and-testing]] | 中級-上級 | システムの品質保証を担当する開発者、MLOpsエンジニア | [[application-patterns/rag-architectures]] |
| [[operations-and-mlops/production-considerations]] | 上級 | 本番システムの設計・運用を統括するアーキテクト | 全てのApplication Patterns |

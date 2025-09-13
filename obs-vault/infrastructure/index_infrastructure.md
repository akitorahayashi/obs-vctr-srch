---
tags:
  - infrastructure
  - docker
  - rag
  - system-design
---

# インフラストラクチャハブ

## 📋 概要
このハブでは、最新のAIアプリケーションを支えるインフラストラクチャ技術、特にコンテナ化とオーケストレーションに焦点を当てます。DockerやKubernetesを用いた、スケーラブルで再現性の高いシステム設計に関する知見を集約します。

## 🎯 コアコンセプト
- **コンテナ化**: アプリケーションをその依存関係と共にパッケージ化し、あらゆる環境で一貫して実行させる技術。
- **オーケストレーション**: 複数のコンテナのデプロイ、管理、スケーリングを自動化するプロセス。
- **Infrastructure as Code (IaC)**: インフラ構成をコードで管理し、プロビジョニングを自動化するプラクティス。

## 📚 ナレッジマップ

| 記事名 | 難易度 | 対象読者 | 前提知識 |
| :--- | :--- | :--- | :--- |
| [[introduction-to-docker]] | 初級 | これからコンテナ技術を学ぶ開発者 | なし |
| [[network-fundamentals-for-devs]] | 初級 | 開発者 | なし |
| [[declarative-rag-system-docker-compose]] | 中級 | Dockerの基本を理解したエンジニア | Docker, RAG |
| [[llm-api-server-containerization]] | 中級 | Dockerの基本を理解し、LLMをデプロイしたいエンジニア | Docker, LLM |
| [[local-ai-dev-with-docker]] | 中級 | AI/インフラエンジニア | Docker, LLM |
| [[inference-acceleration-with-gpu]] | 上級 | AI/インフラエンジニア | Docker, LLM |
| [[kubernetes-introduction-guide]] | 中級 | インフラ/AIエンジニア | Docker |
| [[kubernetes-ci-cd-for-gpu-workloads]] | 上級 | MLOps/インフラエンジニア | Kubernetes, GPU |
| [[production-monitoring-with-prometheus-grafana]] | 上級 | MLOps/SRE | Kubernetes |

## 🔗 カテゴリ横断リンク
**関連**: [[../lang-chain/index_lang-chain.md|LangChain]] (AIロジック実装), [[../python-tools/index_python-tools.md|Python Tools]] (アプリケーションコード)

## 🏷️ ドメインタグ
`#Infrastructure` `#Docker` `#DockerCompose` `#RAG` `#IaC` `#GPU` `#Kubernetes` `#GitOps` `#CI/CD` `#Monitoring` `#Prometheus` `#Grafana` `#ModelRunner` `#MCPToolkit`

## 📊 クイック統計
**記事数**: 8 | **最終更新日**: 2025-08-20

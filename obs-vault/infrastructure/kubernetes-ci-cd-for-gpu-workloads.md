---
tags:
  - kubernetes
  - gpu
  - gitops
  - argo-cd
  - ci-cd
  - mlops
  - advanced
  - infrastructure
---
# Kubernetes応用：GPUリソース管理とGitOpsによるCI/CD

## 1. はじめに

本章は、Kubernetesの基礎的な管理手法から、大規模言語モデル（LLM）のような要求の厳しいワークロードを支える本番グレードのインフラストラクチャ構築へと移行するための、重要な転換点となります。読者は、本書のこれまでの章で解説されたPod、Deployment、Service、そしてkubectlの基本操作といった[[kubernetes-introduction-guide|Kubernetesの核となる概念]]に習熟していることを前提とします。

現代のAI/MLシステムをKubernetes上で運用する際には、二つの大きな課題が存在します。一つは、計算効率を最大化するための[[inference-acceleration-with-gpu|GPU]]のような**特殊なハードウェアへの依存**です。もう一つは、サービスを中断することなく、モデルやアプリケーションを迅速かつ安全にデプロイするための**運用の速度と安定性の両立**です。

本章は、これら二つの課題を解決するための一貫した物語として構成されています。まず、物理的なハードウェア層であるGPUのプロビジョニングと管理から始めます。次に、その上に宣言的な自動化フレームワーク（GitOpsとArgo CD）を構築します。最後に、このフレームワークを活用して、洗練された安全なデプロイ戦略（Argo Rollouts）を実行します。この流れは、堅牢なMLOpsプラットフォームを構築する際の、現実世界のプロセスを忠実に反映しています。

## 2. KubernetesにおけるGPUリソースの高度な管理

このセクションでは、コンテナ化されたワークロードが特殊なハードウェアを利用可能にするための、基本的な要件について詳述します。

### 2.1. なぜGPU管理が必要か

AI/MLモデルの学習および推論フェーズを加速させる上で、GPUが中心的な役割を担うことは広く知られています。しかし、適切な管理レイヤーがなければ、クラスターノード上のGPUはKubernetesから認識されず、利用不可能な状態にあります。これにより、GPUは単に隔離され、管理されていない資産となってしまいます。

ここで根本的な問題が浮上します。通常、CPUやメモリといった単位でリソースを考えるKubernetesスケジューラが、NVIDIA GPUのようなベンダー固有の有限なハードウェアプールをどのように認識し、管理するのでしょうか。この問いに答えることが、Kubernetes上でAIワークロードを効率的に実行するための第一歩となります。

### 2.2. Kubernetes Device Pluginフレームワーク

Kubernetesは、この課題に対する拡張可能なソリューションとしてDevice Pluginフレームワークを提供しています。このフレームワークにより、サードパーティのベンダーはKubernetesのコアコードを直接変更することなく、自身が提供するハードウェアリソースをクラスタに広告（advertise）できます。

そのメカニズムは、以下のようなワークフローに基づいています。

1.  ベンダー固有のコントローラ（「デバイスプラグイン」）が各ノード上で実行されます。
2.  このプラグインが、ノード上のハードウェア（例：NVIDIA GPU）を検出します。
3.  gRPCサービスを起動し、ホスト上のUnixソケット（通常は`/var/lib/kubelet/device-plugins/`配下）を介して、そのノードのkubeletに自身を登録します。
4.  `nvidia.com/gpu`のようなベンダー固有の拡張リソース名を用いて、リソースを広告します。
5.  kubeletはこのリソース情報をKubernetes APIサーバーに報告し、これにより`cpu`や`memory`と同様に、スケジューリング可能なリソースタイプとして扱われるようになります。

このDevice Pluginフレームワークは、Kubernetesの核となる設計思想、すなわちプラグイン可能で拡張性の高いアーキテクチャの優れた一例です。この設計思想の背景には、Kubernetesを普遍的なオーケストレーターとして維持するための戦略があります。ハードウェアの世界はGPU、FPGA、高性能NICなど多岐にわたり、絶えず進化しています。すべてのデバイスに対するサポートをコアにハードコーディングすることは、プロジェクトを巨大化させ、開発速度を低下させるため、持続可能ではありません。そこで、汎用的なインターフェース（Device Plugin gRPC API）が作成され、あらゆるベンダーが自身のハードウェア管理ロジックを「プラグイン」として提供できるようになりました。この仕組みを理解することは、単にGPUを*どう使うか*だけでなく、*なぜ*Kubernetesがこのように設計されているのかという、より深いアーキテクチャの理解につながります。

### 2.3. NVIDIA GPU Operatorによる環境構築

GPUをノード上で利用可能にするには、NVIDIAドライバ、コンテナランタイムを適応させるNVIDIA Container Toolkit、そして前述のDevice Plugin自体といった、複雑なソフトウェアスタックが必要です。これらの依存関係を手動でクラスタ全体にわたって管理することは、間違いが発生しやすく、各ノードが微妙に異なる構成を持つ「スノーフレーク」ノードを生み出す原因となります。

この課題に対する公式かつ本番環境で推奨される解決策が、NVIDIA GPU Operatorです。Operatorは、このソフトウェアスタック全体の管理を自動化するKubernetesコントローラであり、インストール、アップグレード、管理に関する運用知識をカプセル化しています。

#### 演習: GPU Operatorのインストール

ここでは、GPU OperatorをインストールするためのHelmコマンドを段階的に示します。これは個々のコンポーネントをインストールする複雑さを抽象化する、現代的なベストプラクティスです。

**前提条件:**

*   Helm v3がインストールされていること。
*   Kubernetesクラスタにアクセス可能であること。

**手順:**

1.  **NVIDIA Helmリポジトリの追加と更新**
    まず、NVIDIAの公式Helmリポジトリを追加し、最新のチャート情報を取得します。
```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update
```

2.  **GPU Operatorのインストール**
    次に、`gpu-operator`という名前空間を作成し、そこにOperatorをインストールします。`--wait`フラグは、すべてのリソースが準備完了状態になるまで待機するために使用します。
```bash
helm install --wait --generate-name \
  -n gpu-operator --create-namespace \
  nvidia/gpu-operator
```

**インストールの検証:**
インストールが成功したことを確認するために、以下のkubectlコマンドを実行します。

1.  **Operator Podのステータス確認**
    `gpu-operator`名前空間内のPodがすべて`Running`または`Completed`状態であることを確認します。
```bash
kubectl get pods -n gpu-operator
```
    `nvidia-driver-daemonset`、`nvidia-container-toolkit-daemonset`、`nvidia-device-plugin-daemonset`などのPodが表示されるはずです。
2.  **ノードリソースの確認**
    GPUが搭載されているノードの詳細情報を表示し、リソースが正しく認識されているかを確認します。
```bash
kubectl describe node <your-gpu-node-name>
```
    出力の`Labels`セクションに`nvidia.com/gpu.product=...`のようなラベルが自動的に付与され、`Capacity`および`Allocatable`セクションに`nvidia.com/gpu: 1`（またはGPUの数に応じた値）が表示されていれば、インストールは成功です。これは、ドライバのインストールからDevice Pluginによるリソース広告まで、すべてのスタックが正常に機能していることを示します。

### 2.4. PodへのGPU割り当て

GPU Operatorのインストールによって、クラスタのインフラストラクチャは変革されました。`nvidia.com/gpu`というリソースは、今やKubernetesスケジューリングシステムにおける第一級の市民（first-class citizen）です。これにより、物理的なハードウェアと、開発者が実行したい論理的なワークロードとの間のギャップが埋められました。Operatorが実行される前は、GPUを持つノードもただのノードであり、Kubernetesはその特殊な能力を認識していませんでした。しかし、OperatorがDaemonSetとして各種コンポーネント（ドライバインストーラ、デバイスプラグイン等）をGPU搭載ノードに展開した結果、Device Pluginが`nvidia.com/gpu`リソースをkubeletに正常に登録し、スケジューラは`nvidia.com/gpu`を要求するPodを、それを提供できるノードに割り当てることが可能になりました。

#### 演習: CUDAワークロードの実行

実際にGPUを要求するPodをデプロイし、GPUリソースがコンテナ内から正しく利用できることを確認します。

1.  **Podマニフェストの作成**
    以下の内容で`cuda-pod.yaml`というファイルを作成します。このマニフェストは、1つのGPUを要求するPodを定義します。
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cuda-vector-add
spec:
  restartPolicy: OnFailure
  containers:
    - name: cuda-vector-add
      # NVIDIAが提供するCUDAサンプルイメージ
      image: "nvidia/samples:vectoradd-cuda11.6.2-ubuntu20.04"
      resources:
        limits:
          # 1つのGPUを要求
          nvidia.com/gpu: 1
```
    ここで最も重要なのは`spec.containers.resources.limits`セクションです。`nvidia.com/gpu: 1`と指定することで、このコンテナが1つのGPUリソースを専有することをスケジューラに伝えます。
2.  **Podのデプロイとログの確認**
    作成したマニフェストを適用してPodをデプロイし、そのログを確認します。
```bash
# Podのデプロイ
kubectl apply -f cuda-pod.yaml

# PodのステータスがRunningまたはCompletedになるまで待機
kubectl wait --for=condition=Ready pod/cuda-vector-add --timeout=300s

# Podのログを確認
kubectl logs cuda-vector-add
```
    ログの最後に`[Vector addition of 50000 elements]...Test PASSED`というメッセージが表示されていれば、コンテナがGPUを正常に認識し、CUDAアプリケーションを実行できたことになります。これは、GPUリソースの割り当てが成功したことの具体的な証拠です。

## 3. GitOpsによる宣言的CI/CDパイプライン

ハードウェア管理の基盤が整ったところで、次はこの基盤上でアプリケーションのライフサイクルを自動化する手法に焦点を移します。

### 3.1. GitOpsの原則

GitOpsは、Gitを宣言的なインフラストラクチャとアプリケーションのための**唯一の信頼できる情報源（Single Source of Truth）**として利用する運用フレームワークです。これは単なるツールではなく、システムを管理するためのパラダイムです。GitOpsは、主に以下の4つの基本原則に基づいています。

1.  **宣言的（Declarative）:** システム全体の望ましい状態が、宣言的に（例：KubernetesのYAMLファイルで）記述されている必要があります。
2.  **バージョン管理され不変（Versioned and Immutable）:** 望ましい状態はGitリポジトリに保存され、バージョン管理された、監査可能で不変な情報源を提供します。ロールバックは`git revert`コマンドのようにシンプルになります。
3.  **自動的にプルされる（Pulled Automatically）:** ソフトウェアエージェント（例：Argo CD）が、Gitリポジトリから望ましい状態を自動的に*プル*します。これは、変更をクラスタに*プッシュ*することが多い従来のCI/CDとの重要な違いです。
4.  **継続的に調整される（Continuously Reconciled）:** エージェントは、システムの実際の状態を継続的に監視し、Gitで定義された望ましい状態と一致するように動作します。これにより、設定のドリフト（手動変更による意図しない差異）が自動的に修正されます。

GitOpsはKubernetesに後付けされた異質な概念ではなく、Kubernetes自身の設計思想を自然に拡張したものです。Kubernetesは「望ましい状態」と「実際の状態」を調整するループで動作します。例えば、ユーザーが3つのレプリカを持つDeploymentを宣言すると（望ましい状態）、ReplicaSetコントローラが3つのPodが実行されるように動作します（実際の状態）。GitOpsは、この「望ましい状態」の定義を単にGitリポジトリに外部化するだけです。GitOpsエージェントであるArgo CDは、Gitリポジトリとクラスタの状態という2つのものを監視する特別なコントローラとして機能します。Gitに変更がコミットされると、エージェントはKubernetes内の望ましい状態を更新し、その後はKubernetesのネイティブなコントローラがその状態を実現するために引き継ぎます。この関係性を理解することで、GitOpsを孤立したツールとしてではなく、Kubernetesとの対話方法を強化し、形式化するワークフローとして捉えることができます。

### 3.2. Argo CDアーキテクチャの理解

Argo CDは、GitOpsの原則を忠実に実装した、宣言的な継続的デリバリーツールです。そのアーキテクチャは、主に3つのコアコンポーネントで構成されています。

*   **API Server:** Web UI、CLI、および外部APIからのアクセスを提供するgRPC/RESTサーバーです。認証・認可を処理し、他のコンポーネントへの呼び出しを調整します。
*   **Repository Server:** Gitリポジトリをクローンし、ローカルキャッシュを維持する内部サービスです。HelmチャートのレンダリングやKustomizationの適用などを行い、最終的なKubernetesマニフェストを生成する責務を担います。
*   **Application Controller:** Argo CDの心臓部であり、GitOpsの原則における「ソフトウェアエージェント」です。実行中のアプリケーションのライブ状態を継続的に監視し、Gitリポジトリで定義されたターゲット状態と比較します。差異（`OutOfSync`状態）を検出すると、状態を調整するためのアクションを実行します。

### 3.3. Argo CDの導入とアプリケーションのデプロイ

ここでは、Argo CDを実際にインストールし、GitOpsワークフローを体験します。

#### 演習: Argo CDのインストールとCLIの設定

1.  **Argo CDのインストール**
    標準的な手順に従い、Argo CDを専用の名前空間にインストールします。
```bash
# argocd名前空間の作成
kubectl create namespace argocd

# 安定版のArgo CDマニフェストを適用
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

2.  **Argo CD CLIのインストール**
    `argocd` CLIは、Argo CDを操作するための強力なツールです。macOSの場合はHomebrewで簡単にインストールできます。
```bash
brew install argocd
```
    他のOSについては、公式のインストール手順を参照してください。
3.  **Argo CDへのログイン**
    初期管理者パスワードはKubernetes Secretに保存されています。以下のコマンドでパスワードを取得し、port-forwardを使ってローカルからAPIサーバーにログインします。
```bash
# 初期パスワードを取得
ARGO_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

# 別のターミナルでポートフォワードを実行
kubectl port-forward svc/argocd-server -n argocd 8080:443

# ログイン (パスワードの入力を求められます)
argocd login localhost:8080 --username admin --password $ARGO_PASSWORD --insecure
```

#### 演習: Gitリポジトリの準備

1.  GitHubなどで新しい公開Gitリポジトリを作成します。このリポジトリが、アプリケーションの望ましい状態を管理する「唯一の信頼できる情報源」となります。
2.  リポジトリ内に、`nginx-app`などのディレクトリを作成し、その中にシンプルなWebアプリケーションのマニフェストを作成します。
    **nginx-app/deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.23.3
        ports:
        - containerPort: 80
```
    **nginx-app/service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
```
3.  これらのファイルをGitリポジトリにコミットし、プッシュします。

#### 演習: Argo CD Applicationの作成

Applicationは、Gitリポジトリとターゲットクラスタを紐付けるためのArgo CDのカスタムリソース（CRD）です。

1.  **Applicationマニフェストの作成**
    以下の内容で`argo-application.yaml`ファイルを作成します。各フィールドの役割をコメントで示します。
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  # アプリケーション名
  name: my-web-app
  # Argo CDがインストールされている名前空間
  namespace: argocd
spec:
  # 1. Project: アプリケーションのグルーピングやRBACに使用
  project: default

  # 2. Source: 望ましい状態が定義されている場所
  source:
    # あなたが作成したGitリポジトリのURL
    repoURL: 'https://github.com/your-username/your-gitops-repo.git'
    # リポジトリ内のマニフェストが置かれているパス
    path: 'nginx-app'
    # 追跡するブランチやタグ、コミットハッシュ
    targetRevision: HEAD

  # 3. Destination: アプリケーションをデプロイする場所
  destination:
    # デプロイ先のクラスタURL（ローカルクラスタを指す）
    server: 'https://kubernetes.default.svc'
    # デプロイ先の名前空間
    namespace: 'my-app-namespace'

  # 4. Sync Policy: 同期の方法
  syncPolicy:
    automated:
      # Gitに存在しないリソースをクラスタから削除する
      prune: true
      # 手動変更（ドリフト）を自動的に修正する
      selfHeal: true
    syncOptions:
      # Destinationの名前空間が存在しない場合に作成する
      - CreateNamespace=true
```
2.  **GitOpsループの実証**
    このApplicationマニフェストをクラスタに適用し、GitOpsの動作を確認します。
```bash
# Applicationリソースを適用
kubectl apply -f argo-application.yaml

# アプリケーションの同期状態を確認
argocd app get my-web-app
```
    最初は`SyncStatus`が`OutOfSync`と表示され、その後すぐにArgo CDが自動で同期（Sync）を行い、`Synced`かつ`Healthy`になるはずです。
    次に、Gitリポジトリの`nginx-app/deployment.yaml`を編集し、`replicas`を`3`に、`image`を`nginx:1.24.1`に変更してコミット＆プッシュします。
    数分後、再度`argocd app get my-web-app`を実行すると、Argo CDがGitの変更を検出し、自動的にクラスタの状態を更新したことが確認できます。Argo CDのWeb UI（`http://localhost:8080`）にアクセスすると、この一連の流れを視覚的に追跡することもできます。これは、GitOpsワークフロー全体の強力な実践的デモンストレーションです。

## 4. 高度なデプロイ戦略とゼロダウンタイムリリース

自動化のフレームワークが整った今、本番環境で求められる、より安全で高度なリリースパターンを導入します。

### 4.1. ローリングアップデート戦略

`RollingUpdate`は、KubernetesのDeploymentリソースにおけるデフォルトの更新戦略です。この戦略は、古いバージョンのPodを新しいバージョンのPodで段階的に置き換えることにより、サービスのダウンタイムをゼロに抑えます。

この挙動は、`maxSurge`と`maxUnavailable`という2つの重要なパラメータによって細かく制御できます。

*   `maxUnavailable`: 更新中に利用不可能であってもよいPodの最大数（または割合）。これにより、常に一定数のPodがサービスを提供し続けることが保証されます。
*   `maxSurge`: 望ましいレプリカ数を超えて作成してもよいPodの最大数（または割合）。これにより、新しいPodを起動させてから古いPodを停止させる余裕が生まれ、更新がスムーズに進みます。

Argo CDで管理されているnginxアプリケーションの`image`タグをGitリポジトリで変更すると、このローリングアップデートが自動的にトリガーされます。`kubectl get pods -n my-app-namespace -w`コマンドを実行すれば、古いPodが終了（`Terminating`）し、新しいPodが起動（`Running`）する様子をリアルタイムで監視できます。

### 4.2. 高度なデプロイ戦略の比較

基本的なローリングアップデートは強力ですが、限界もあります。この戦略はPodのReadiness Probeにのみ依存しており、外部メトリクス（例：エラー率、レイテンシ）に基づいた自動分析や、きめ細かなトラフィック制御は行えません。これが、より高度な戦略が求められる理由です。

*   **Blue/Greenデプロイメント:** 同一の環境を2つ（Blue：現行版、Green：新版）用意し、テストが完了したらトラフィックを瞬時に切り替える手法です。
*   **カナリアリリース:** 新しいバージョンをまずごく一部のユーザー（カナリアグループ）に公開し、問題がないことを確認しながら段階的にトラフィックの割合を増やしていく手法です。

高度なエンジニアは、状況に応じて最適なデプロイ戦略を選択できなければなりません。以下の表は、それぞれの戦略のトレードオフをまとめたものです。

| 特徴 | ローリングアップデート | Blue/Greenデプロイメント | カナリアリリース |
| :--- | :--- | :--- | :--- |
| **メカニズム** | Podの段階的な置き換え | 2つの同一環境と瞬時のトラフィック切り替え | 新バージョンへの段階的なトラフィック移行 |
| **ダウンタイム** | ゼロ（正しく設定されていれば） | ほぼゼロ、瞬時に切り替え | ゼロ |
| **リソースコスト** | 低（`maxSurge`分のオーバーヘッドのみ） | 高（本番環境の2倍のインフラが必要） | 中（両方のバージョンを同時に実行する必要がある） |
| **ロールバック** | 自動だが、時間がかかる場合がある | 瞬時（トラフィックを元に戻すだけ） | 高速（トラフィックを旧バージョンに戻すだけ） |
| **リスクプロファイル** | 低〜中（影響範囲が徐々に拡大） | 高（全ユーザーが同時に新バージョンに移行） | 最も低い（影響範囲がカナリアグループに限定） |
| **ユースケース** | 汎用的、シンプルなステートレスアプリ | ミッションクリティカルなアプリ、低いリスク許容度 | 新機能のテスト、パフォーマンス検証 |

### 4.3. Argo Rolloutsによるカナリアリリース

KubernetesネイティブのDeploymentオブジェクトには、真のプログレッシブデリバリー（段階的提供）に必要な、洗練されたトラフィックシェーピングや分析機能が欠けています。本番リリースでは、「Podが起動しているか」だけでなく、「新しいバージョンは本番トラフィック下で良好に動作しているか」という問いに答える必要があります。これには、トラフィックの一部（例：5%）を新バージョンに送り、外部メトリクス（例：Prometheusから取得したレイテンシやエラー率）をクエリし、続行または中止を自動で判断する機能が不可欠です。Deploymentオブジェクトはトラフィックの重み付けやメトリクス分析の概念を持たないため、この機能ギャップを埋めるためにArgo Rolloutsのようなコントローラが生まれました。これは、Kubernetesを拡張してドメイン固有の機能を追加する「Operator」パターンのもう一つの好例です。

Argo Rolloutsは、標準のDeploymentオブジェクトを`Rollout`というカスタムリソースに置き換えることで、高度なデプロイ戦略を提供するKubernetesコントローラです。

#### 演習: カナリアリリースの実践

1.  **Argo Rolloutsのインストール**
    Argo Rolloutsとその`kubectl`プラグインをインストールします。
```bash
# argo-rollouts名前空間の作成
kubectl create namespace argo-rollouts

# Argo Rolloutsのインストール
kubectl apply -n argo-rollouts -f https://raw.githubusercontent.com/argoproj/argo-rollouts/stable/manifests/install.yaml

# kubectlプラグインのインストール (macOS/Homebrew)
brew install argoproj/tap/kubectl-argo-rollouts
```

2.  **DeploymentからRolloutへの変換**
    Gitリポジトリ内の`nginx-app/deployment.yaml`を`nginx-app/rollout.yaml`にリネームし、内容を以下のように変更します。`kind`を`Rollout`に、`apiVersion`を`argoproj.io/v1alpha1`に変更し、`strategy`ブロックを追加します。
    **nginx-app/rollout.yaml:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: nginx-rollout
spec:
  replicas: 5
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.24.1 # ここを更新してリリースをトリガーする
        ports:
        - containerPort: 80
  strategy:
    canary:
      steps:
      # 1. トラフィックの20%を新バージョンに流す
      - setWeight: 20
      # 2. 手動での確認・承認のために無期限で一時停止する
      - pause: {}
      # 3. 承認後、段階的にトラフィックを増やす
      - setWeight: 50
      - pause: {duration: 30s}
      - setWeight: 80
      - pause: {duration: 30s}
```
    Argo CDで管理している`my-web-app`の`path`も`nginx-app/rollout.yaml`を指すように更新し、Gitにプッシュします。Argo CDがこの変更を同期します。
3.  **アップデートのトリガー**
    `nginx-app/rollout.yaml`の`image`タグを`nginx:1.25.1`などに変更し、Gitにプッシュします。Argo CDがこの変更を検知し、Rolloutリソースを更新することで、カナリアリリースが開始されます。
4.  **可視化とプロモーション**
    `kubectl argo rollouts`プラグインを使って、リリースの進行状況をリアルタイムで可視化します。
```bash
kubectl argo rollouts get rollout nginx-rollout -n my-app-namespace --watch
```
    このコマンドは、新旧のReplicaSet、Podの状態、トラフィックの重み付けなどを非常に分かりやすく表示します。`strategy`で定義した通り、`setWeight: 20`のステップに到達すると、`pause: {}`によってリリースが一時停止します。
    この時点で、新バージョンの動作を監視・テストできます。問題がなければ、以下のコマンドでリリースを続行（プロモート）します。
```bash
kubectl argo rollouts promote nginx-rollout -n my-app-namespace
```
    プロモート後、`watch`コマンドの画面で、残りのステップが自動的に進行し、最終的にすべてのトラフィックが新バージョンに切り替わる様子を観察できます。これで、安全で観測可能なカナリアリリースが完了です。

## 5. まとめと次のステップ

本章を通じて、我々はエンドツーエンドの旅を経験しました。まず、Operatorパターンを用いてGPUという特殊なハードウェアを飼いならし、次にGitOpsとArgo CDを使って完全に自動化され、監査可能なアプリケーションデリバリーシステムを構築しました。そして最後に、Argo Rolloutsを活用して本番グレードのカナリアリリースを実行し、安定性を確保しつつリスクを最小限に抑える手法を学びました。

この一連の技術スタック、すなわちGPU管理、GitOps、そしてプログレッシブデリバリーは、現代的で堅牢な**MLOpsプラットフォームの技術的なバックボーン**を形成します。

アプリケーションを確実にデプロイし、更新できるようになった今、次なる論理的なステップは、本番環境におけるそれらの健全性とパフォーマンスを監視することです。本章は、**「AIワークロードのための本番オブザーバビリティ：モニタリング、ロギング、アラート」**といった後続のトピックへの完璧な橋渡しとなります。そこでは、Argo Rolloutsのセクションで示唆されたPrometheusメトリクスのクエリといった概念が、さらに深く探求されることになるでしょう。

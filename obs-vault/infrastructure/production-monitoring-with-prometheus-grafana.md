---
tags:
  - kubernetes
  - monitoring
  - prometheus
  - grafana
  - observability
  - mlops
  - infrastructure
---
# 本番運用のための監視：PrometheusとGrafanaによる可観測性の確保

## 1. はじめに：LLM時代のモニタリングから可観測性へ

AI、特に大規模言語モデル（LLM）を活用したアプリケーションが本番環境で稼働するようになると、その安定運用は極めて重要な課題となります。従来のソフトウェア開発におけるモニタリング手法は、システムの健全性を測る上で依然として有効ですが、LLMがもたらす特有の複雑性に直面したとき、その限界が露呈します。本章では、従来のモニタリングから一歩進んだ「可観測性（Observability）」の概念を導入し、なぜそれがLLMアプリケーションの安定稼働に不可欠なのかを解説します。そして、その実現手段として、業界標準のオープンソースツールであるPrometheusとGrafanaを用いた実践的な監視基盤の構築手法を、具体的なコマンドや設定例を交えながら体系的に学びます。

### 1.1. ブラックボックスという課題：なぜ従来のモニタリングでは不十分なのか

従来のアプリケーションモニタリングは、CPU使用率やメモリ使用量、レスポンスタイムといった定義済みのメトリクスを監視し、システムが「正常」か「異常」かを判断することに主眼を置いていました。しかし、LLMアプリケーションは、その内部動作が複雑で予測不可能な「ブラックボックス」としての側面を色濃く持っています。LLMの出力は決定論的ではなく、同じ入力に対しても異なる応答を生成することがあります。この非決定性が、従来のモニタリング手法だけでは捉えきれない、新たな種類の問題を引き起こします。

LLMアプリケーション特有の障害モードには、以下のようなものが挙げられます：

*   **パフォーマンスの問題**：推論にかかる時間の増大（高レイテンシ）、APIコールごとのトークン消費量に起因する予期せぬコスト増大など。
*   **品質の低下**：事実に基づかない情報を生成する「ハルシネーション（幻覚）」、出力に含まれるバイアスや有害なコンテンツ、時間経過に伴うモデルの性能劣化（モデルドリフト）など。
*   **セキュリティの脆弱性**：悪意のある入力（プロンプト）によってモデルを操り、意図しない情報を引き出す「プロンプトインジェクション」や、機密情報の漏洩など。

これらの問題は、単純な死活監視（/healthzエンドポイントのチェック）や基本的なパフォーマンスメトリクスだけでは検知・分析することが困難です。従来のモニタリングが「システムが稼働しているか（*if*）」を教えてくれるのに対し、LLM時代に求められるのは、「システムがどのように振る舞い（*how*）、なぜその出力を生成したのか（*why*）」を理解する能力、すなわち可観測性です。

### 1.2. 可観測性の定義：システムに問いを立てる能力

可観測性とは、システムの外部出力（テレメトリデータ）から、その内部状態をどれだけ深く理解できるかを示す能力のことです。これは、あらかじめ定義されたダッシュボードを眺めることではありません。むしろ、システムの振る舞いに関して、事前に予測していなかった新たな問いを立て、その答えを得るために必要な、生で高カーディナリティなデータを手元に揃えておくという考え方です。

このアプローチは、いわゆる「未知の未知（unknown-unknowns）」、つまり予期せぬ問題に対処する上で極めて重要です。LLMの文脈では、これは新しいタイプのプロンプトインジェクション攻撃や、RAG（Retrieval-Augmented Generation）コンポーネントとベースモデル間の予期せぬ相互作用などが該当します。可観測性は、MLOps（Machine Learning Operations）やSRE（Site Reliability Engineering）における中核的なプラクティスと位置づけられており、迅速な根本原因分析、パフォーマンス最適化、そして継続的なユーザーエクスペリエンスの向上を実現するための鍵となります。

### 1.3. 3つの柱：洞察を得るための統一フレームワーク

可観測性を実践する上で、その基礎となるのが「メトリクス」「ログ」「トレース」という3種類のテレメトリデータです。これらは「可観測性の3つの柱」として知られ、それぞれが異なる役割を担い、互いに補完し合うことでシステム全体像の深い理解を可能にします。

*   **メトリクス (Metrics)**：数値化された時系列データです。集約可能で、保存やクエリの効率が良いという特徴があります。メトリクスは「**何が**起きているのか？」という問いに答えます（例：「CPU使用率が90%に達した」）。サービスの監視においては、Googleが提唱する「4つのゴールデンシグナル」（レイテンシ、トラフィック、エラー、サチュレーション）が重要な指標となります。
*   **ログ (Logs)**：個別のイベントを記録した、タイムスタンプ付きの不変なレコードです。文脈情報が豊富で、「**なぜ**それが起きたのか？」という問いに答えます（例：「タイムスタンプXで接続拒否エラーが発生した」）。
*   **トレース (Traces)**：分散システム内で、あるリクエストが処理されるまでの一連の経路を表現したものです。トレースは複数のスパン（Span）で構成されます。トレースは「**どこで**問題が発生したのか？」という問いに答えます（例：「リクエストはデータベースへの問い合わせで3秒間待機した後に失敗した」）。

これら3つの柱の真価は、それぞれを個別に使用するのではなく、相互に連携させることで発揮されます。この連携により、明確な診断ワークフローが生まれます。例えば、あるエンジニアがアラートを受け取ったとしましょう。

1.  まず、「P99レイテンシが500msを超過」という**メトリクス**に基づくアラートが通知されます。これにより、エンジニアは「何が」問題なのかを把握します。
2.  ダッシュボードでレイテンシの急上昇を確認したエンジニアは、次に「なぜ」そうなったのかを知る必要があります。
3.  そこで、ロギングプラットフォームに切り替え、問題が発生した時間帯の、該当サービスからの**ログ**をフィルタリングします。すると、`TimeoutException`を示す一連のスタックトレースが見つかります。
4.  これでエラーの種類は特定できましたが、その原因がサービス自体にあるのか、それとも依存する下流サービスにあるのかはまだ不明です。
5.  最後に、トレーシングプラットフォームに切り替え、失敗したリクエストの**トレース**を確認します。トレースビューには、リクエストのタイムアウト5秒のうち、外部API呼び出しのスパンが4.5秒を占めていることが明確に示されます。

このように、メトリクスからログへ、そしてトレースへと分析の軸を移すことで、わずか数ステップで根本原因が特定のサードパーティAPIの遅延にあることを突き止められました。このワークフローこそが、実践における可観測性の本質です。本章では、このワークフローの第一歩であるメトリクスの習得に焦点を当てつつ、ログとトレースへと続く道筋を示します。

**表1：可観測性の3つの柱の比較**

| 柱 | データ型 | 主に答える問い | 強み | 弱み |
| :--- | :--- | :--- | :--- | :--- |
| **メトリクス** | 数値時系列データ | 何が？ | 効率的、集約可能、アラートに適している | 文脈情報が欠如している |
| **ログ** | イベントレコード | なぜ？ | 詳細な文脈情報、根本原因分析に不可欠 | 大量、集約やクエリが困難 |
| **トレース** | リクエスト経路 | どこで？ | エンドツーエンドの可視性、ボトルネック特定 | 計装オーバーヘッド、サンプリングが必要 |

この表は、エンジニアがどのような種類のテレメトリを収集すべきかというアーキテクチャ上の決定を下す際のフレームワークを提供します。例えば、システム全体の負荷に関するアラートを構築する必要がある場合、その効率性からメトリクスが最適な選択肢となります。特定のユーザーのエラーをデバッグする必要がある場合は、ログが不可欠です。そして、複雑なマイクロサービス群における遅延を診断するには、全体像を把握できる唯一のツールであるトレースが必要です。

## 2. 監視スタックのアーキテクチャ設計：Kube-Prometheus-Stackの導入

ここからは理論から実践へと移り、業界標準のツールを用いて、[[kubernetes-introduction-guide|Kubernetes]]上に本番環境グレードの監視基盤を構築します。

### 2.1. 前提条件：Kubernetes実行環境

本章を進めるにあたり、以下の環境が準備されていることを前提とします。

*   稼働中のKubernetesクラスタ（Minikube、Kind、またはEKS、GKE、AKSなどのクラウドサービス）
*   クラスタを操作するための`kubectl`コマンドラインツール
*   Kubernetesの標準的なパッケージマネージャであるHelm v3

### 2.2. Kube-Prometheus-Stackの紹介：統合ソリューション

Prometheus、Grafana、Alertmanager、そして各種エクスポーターを手動で個別に設定し、連携させるのは非常に複雑で、間違いの起こりやすい作業です。そこで登場するのが`kube-prometheus-stack`というHelmチャートです。これは、コミュニティにおける事実上の標準（de-facto standard）と見なされており、エンドツーエンドのKubernetesクラスタ監視に必要なコンポーネント群をバンドルし、事前設定済みの状態で提供してくれます。

`kube-prometheus-stack`は、単にPrometheusをインストールするだけではありません。効果的なKubernetes監視には、ノードの健全性を監視するための`node-exporter`、DeploymentやPodの状態を監視するための`kube-state-metrics`、データを可視化するためのGrafana、そしてこれら全てを`ServiceMonitor`や`PrometheusRule`といったKubernetesネイティブなリソースを通じて宣言的に管理するためのPrometheus Operatorが必要です。この統合スタックは、これら全ての価値を一つのパッケージとして提供します。

**表2：Kube-Prometheus-Stackの主要コンポーネント**

| コンポーネント | 役割 |
| :--- | :--- |
| **Prometheus Operator** | PrometheusやAlertmanagerなどのカスタムリソース（CRD）を管理し、設定を自動化する |
| **Prometheus** | メトリクスを収集（スクレイプ）し、時系列データベースに保存する |
| **Alertmanager** | Prometheusからのアラートを受け取り、重複排除、グルーピング、通知のルーティングを行う |
| **Grafana** | メトリクスデータを可視化し、インタラクティブなダッシュボードを構築する |
| **kube-state-metrics** | Deployment、Pod、Nodeなど、Kubernetes APIオブジェクトの状態に関するメトリクスを公開する |
| **node-exporter** | 各ノードのハードウェアやOSレベルのメトリクス（CPU、メモリなど）を公開する |

### 2.3. ハンズオン：Helmによるスタックのインストール

以下のコマンドを実行して、監視スタックをクラスタに導入します。

1.  **監視用の専用名前空間を作成します。**
```bash
kubectl create namespace monitoring
```
2.  **prometheus-communityのHelmリポジトリを追加します。**
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
```
3.  **リポジトリを更新し、最新のチャート情報を取得します。**
```bash
helm repo update
```
4.  **kube-prometheus-stackチャートをインストールします。**
```bash
helm install prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

インストールが完了したら、以下のコマンドでコンポーネントが正しく起動していることを確認します。

*   **Podの状態を確認します。**
```bash
kubectl get pods -n monitoring
```
    上記の表2に記載されている各コンポーネントのPodが`Running`状態になっていれば成功です。
*   **Prometheus UIにアクセスします。**
    以下のコマンドでポートフォワーディングを実行し、ローカルマシンからPrometheusのダッシュボードにアクセスできるようにします。
```bash
kubectl port-forward svc/prometheus-stack-kube-prom-prometheus 9090 -n monitoring
```
    ブラウザで `http://localhost:9090` を開きます。
    `Status` -> `Targets`ページに移動すると、`kube-state-metrics`や`node-exporter`などのターゲットがすでに自動的に検出され、メトリクスが収集（スクレイプ）されていることが確認できます。

## 3. インフラストラクチャの計装：ノードとGPUメトリクスの収集

監視基盤の土台が整ったので、次はその上でLLMスタックが稼働するインフラ層、特にホストマシンと、最も重要なコンポーネントである[[kubernetes-ci-cd-for-gpu-workloads|GPU]]からのメトリクスを収集します。

### 3.1. node-exporterによるホストレベルのメトリクス収集

`kube-prometheus-stack`をインストールすると、`node-exporter`が自動的にDaemonSetとしてデプロイされます。DaemonSetは、クラスタ内の全ての（または特定のラベルを持つ）ノード上でPodのコピーを1つずつ実行することを保証するKubernetesの仕組みであり、各ノードの情報を収集する`node-exporter`のような用途に最適です。

`node-exporter`は、`node_cpu_seconds_total`（CPU使用時間）、`node_memory_MemAvailable_bytes`（利用可能なメモリ量）、`node_disk_io_time_seconds_total`（ディスクI/O時間）といった基本的なインフラメトリクスを公開します。これらのメトリクスは、システムの基本的な健全性の監視やキャパシティプランニングに不可欠です。

### 3.2. nvidia-dcgm-exporterによる重要なGPUインサイト

LLMスタックにおいて最も高価で性能を左右するリソースはGPUです。しかし、標準的なノードメトリクスでは、このGPUの内部状態を把握することはできません。GPUメモリの枯渇や熱による性能低下（サーマルスロットリング）が原因でアプリケーションが失敗していても、標準のCPUやメモリのメトリクスには何ら異常が現れない可能性があります。したがって、GPU専用のエクスポーターを導入することは、オプションではなく、本番運用のための必須要件と言えます。

LLMの推論や学習はGPUに大きく依存するワークロードです。GPUには、GPU使用率、GPUメモリ使用量、消費電力、温度、GPU間通信トラフィックといった、固有のパフォーマンス特性や障害モードが存在します。これらのメトリクスは`node-exporter`では収集できないため、NVIDIAの公式ツールであるDCGM（Data Center GPU Manager）をベースにした`dcgm-exporter`を導入する必要があります。GPUを監視せずにLLMサービスを運用することは、計器類を見ずに飛行機を操縦するようなものです。

#### ハンズオン：dcgm-exporterのDaemonSetとしてのデプロイ

`dcgm-exporter`は、GPUが搭載された全てのノードで実行される必要があります。これを実現するため、特定のラベル（例：`accelerator=nvidia-gpu`）を持つノードを選択する`nodeSelector`を設定したDaemonSetとしてデプロイします。

まず、以下の内容で`dcgm-exporter.yaml`ファイルを作成します。このマニフェストは`dcgm-exporter`のDaemonSetと、Prometheusがメトリクスを収集するためのServiceを定義します。
```yaml
# dcgm-exporter.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: monitoring
  labels:
    app.kubernetes.io/name: dcgm-exporter
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: dcgm-exporter
  template:
    metadata:
      labels:
        app.kubernetes.io/name: dcgm-exporter
    spec:
      # GPUノードにのみデプロイするための設定
      nodeSelector:
        # ご利用の環境に合わせてGPUノードのラベルを指定してください
        accelerator: nvidia-gpu
      containers:
      - image: nvcr.io/nvidia/k8s/dcgm-exporter:4.2.0-4.1.0-ubuntu22.04
        name: dcgm-exporter
        ports:
        - name: metrics
          containerPort: 9400
          hostPort: 9400
        securityContext:
          privileged: true
        volumeMounts:
        - name: pod-resources
          mountPath: /var/lib/kubelet/pod-resources
      volumes:
      - name: pod-resources
        hostPath:
          path: /var/lib/kubelet/pod-resources
---
apiVersion: v1
kind: Service
metadata:
  name: dcgm-exporter
  namespace: monitoring
  labels:
    # ServiceMonitorがこのServiceを発見するためのラベル
    app.kubernetes.io/name: dcgm-exporter
spec:
  selector:
    app.kubernetes.io/name: dcgm-exporter
  ports:
  - name: metrics
    port: 9400
    targetPort: 9400
```
次に、このマニフェストをクラスタに適用します。
```bash
kubectl apply -f dcgm-exporter.yaml
```

#### ハンズオン：dcgm-exporter用のServiceMonitor作成

次に、Prometheus Operatorに対して、先ほど作成した`dcgm-exporter` Serviceからメトリクスを収集するよう指示するための`ServiceMonitor`リソースを作成します。以下の内容で`dcgm-servicemonitor.yaml`を作成してください。
```yaml
# dcgm-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dcgm-exporter-monitor
  namespace: monitoring
  labels:
    # kube-prometheus-stackがこのServiceMonitorを発見するためのラベル
    release: prometheus-stack
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: dcgm-exporter
  endpoints:
  - port: metrics
    interval: 15s
```
このマニフェストをクラスタに適用します。
```bash
kubectl apply -f dcgm-servicemonitor.yaml
```
これで、Prometheusが自動的に`dcgm-exporter`をターゲットとして認識し、GPUメトリクスの収集を開始します。Prometheus UIの`Targets`ページで新しいターゲットが追加されたことを確認してください。

#### 監視すべき主要なGPUメトリクス

*   `DCGM_FI_DEV_GPU_UTIL`: GPU使用率（%）。GPUがアクティブかどうかの主要な指標です。
*   `DCGM_FI_DEV_FB_USED`: フレームバッファ（GPUメモリ）使用量（MB）。メモリリークやメモリ枯渇の検知に不可欠です。
*   `DCGM_FI_DEV_POWER_USAGE`: 消費電力（W）。効率やコスト分析に役立ちます。
*   `DCGM_FI_DEV_GPU_TEMP`: GPU温度（℃）。サーマルスロットリングやハードウェアの損傷を防ぐために重要です。

## 4. アプリケーションの計装：カスタムLLMメトリクスの公開

インフラ層のメトリクスは重要ですが、それだけではアプリケーションの振る舞いを完全に理解することはできません。「どれくらいのリクエストを処理しているのか？」「その速さは？」「失敗率は？」「トークンはどれくらい消費しているのか？」といった問いに答えるには、アプリケーション自身が生成するカスタムメトリクスが必要です。

### 4.1. アプリケーション固有のシグナルの必要性

LLM APIサービスの健全性を評価するためには、リクエスト数、レイテンシ、エラー率といった標準的なAPIメトリクスに加え、トークン使用量のようなLLM固有のメトリクスを追跡することが不可欠です。これらのメトリクスは、アプリケーションのパフォーマンス、ユーザーエクスペリエンス、そして運用コストを直接反映します。

### 4.2. ハンズオン：Python FastAPIアプリケーションの計装

ここでは、現代的なAIサービスのフレームワークとして代表的なPythonとFastAPIを例に、アプリケーションの計装方法を解説します。Python用のPrometheusクライアントライブラリ`prometheus-client`を使用します。

まず、主要な4つのメトリクスタイプを定義します。

*   **Counter**: リクエスト総数のように、値が単調増加するメトリクス。
*   **Gauge**: 同時リクエスト数ののように、値が増減するメトリクス。
*   **Histogram**: レイテンシのように、値の分布を追跡するメトリクス。
*   **LLM固有のメトリクス**: トークン消費量など。

以下は、これらのメトリクスを収集するためのFastAPIアプリケーションの完全なコード例です。リクエストごとにメトリクスを更新するミドルウェアと、収集したメトリクスを`/metrics`エンドポイントで公開する機能が含まれています。
```python
# main.py
import time
import psutil
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY
)

# FastAPIアプリケーションの初期化
app = FastAPI()

# --- Prometheusメトリクスの定義 ---

# 1. HTTPリクエスト総数 (Counter)
REQUEST_COUNT = Counter(
    'llm_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code']
)

# 2. 処理中のHTTPリクエスト数 (Gauge)
REQUESTS_IN_PROGRESS = Gauge(
    'llm_api_requests_in_progress',
    'Number of API requests in progress',
    ['method', 'endpoint']
)

# 3. HTTPリクエストのレイテンシ (Histogram)
REQUEST_LATENCY = Histogram(
    'llm_api_request_latency_seconds',
    'API request latency in seconds',
    ['method', 'endpoint']
)

# 4. 処理されたトークン総数 (Counter) - LLM固有
TOKENS_PROCESSED = Counter(
    'llm_api_tokens_processed_total',
    'Total number of tokens processed by the LLM'
)

# --- ミドルウェアによるメトリクス収集 ---

@app.middleware("http")
async def track_metrics(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    start_time = time.time()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise e
    finally:
        end_time = time.time()
        latency = end_time - start_time

        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
        REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()

    return response

# --- APIエンドポイントの定義 ---

@app.get("/")
def read_root():
    # ダミーのトークン処理をシミュレート
    TOKENS_PROCESSED.inc(100)
    return {"message": "Hello, this is an LLM API."}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    # ダミーのトークン処理をシミュレート
    TOKENS_PROCESSED.inc(50)
    if item_id == 42:
        # 意図的にエラーを発生させる
        raise ValueError("Invalid item ID")
    return {"item_id": item_id}

# --- Prometheusメトリクス公開エンドポイント ---

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
```

### 4.3. ServiceMonitorによるPrometheusとアプリケーションの接続

Kubernetesネイティブな方法で、Prometheus Operatorに新しいサービスを監視対象として追加させるには、`ServiceMonitor`というカスタムリソース（CRD）を使用します。

まず、FastAPIアプリケーションをデプロイするためのDeploymentと、それをクラスタ内部からアクセス可能にするためのServiceを定義します。次に、そのServiceを監視対象とする`ServiceMonitor`を定義します。`ServiceMonitor`は、`selector`を使って対象のServiceをラベルで選択し、メトリクスを収集するポート名（例：`http`）とパス（`/metrics`）を指定します。

以下のYAMLファイルを`app-monitor.yaml`として保存し、適用します。
```yaml
# app-monitor.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-api-deployment
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: llm-api
  template:
    metadata:
      labels:
        app: llm-api
    spec:
      containers:
      - name: llm-api
        # 上記のFastAPIアプリをコンテナ化したイメージを指定
        image: your-repo/your-fastapi-app:latest
        ports:
        - name: http
          containerPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: llm-api-service
  namespace: monitoring
  labels:
    app: llm-api # ServiceMonitorがこのラベルで選択する
spec:
  selector:
    app: llm-api
  ports:
  - name: http # ServiceMonitorがこのポート名で選択する
    port: 80
    targetPort: 8000
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: llm-api-monitor
  namespace: monitoring
  labels:
    release: prometheus-stack # kube-prometheus-stackがこのServiceMonitorを発見するためのラベル
spec:
  selector:
    matchLabels:
      app: llm-api # 監視対象のServiceのラベル
  endpoints:
  - port: http # 監視対象のServiceのポート名
    path: /metrics # メトリクスが公開されているパス
    interval: 15s
```
```bash
kubectl apply -f app-monitor.yaml
```
適用後、Prometheus UIの`Targets`ページに`llm-api-monitor`という新しいターゲットが表示され、自動検出が機能したことを確認できます。

**表3：LLM APIサービスの主要メトリクス**

| メトリクス名 (PromQL) | メトリクスタイプ | 説明 | ビジネス/運用上の問い |
| :--- | :--- | :--- | :--- |
| `rate(llm_api_requests_total[5m])` | Counter (Rate) | 1秒あたりのリクエスト数（RPS） | サービスのトラフィック量はどれくらいか？ |
| `histogram_quantile(0.99,...)` | Histogram (Quantile) | 99パーセンタイルのリクエストレイテンシ | ユーザー体験のSLOを満たせているか？ |
| `rate(llm_api_requests_total{status_code=~"5.."}[5m])` | Counter (Rate) | 1秒あたりのサーバーエラー数 | サービスの信頼性はどの程度か？ |
| `sum(rate(llm_api_tokens_processed_total[5m]))` | Counter (Rate) | 1秒あたりの処理トークン数 | 運用コストはどれくらいか？ |
| `avg(DCGM_FI_DEV_GPU_UTIL)` | Gauge (Average) | GPUフリートの平均使用率 | 高価なハードウェアは効率的に使われているか？ |

この表は、技術的なメトリクスがどのようにビジネス価値や運用上の意思決定に直結するかを示しています。例えば、`llm_api_tokens_processed_total`は「運用コストはいくらか？」という問いに、`DCGM_FI_DEV_GPU_UTIL`は「最も高価なハードウェアは過剰／過小にプロビジョニングされていないか？」という問いに答えるためのデータを提供します。

## 5. 可視化と分析：GrafanaによるLLM運用ダッシュボードの構築

収集した生のメトリクスデータを、実用的な視覚的インサイトに変換する方法を学びます。

### 5.1. GrafanaへのアクセスとPrometheusデータソースの接続

まず、以下のコマンドでGrafanaのUIにポートフォワーディングします。
```bash
kubectl port-forward svc/prometheus-stack-grafana 3000 -n monitoring
```
ブラウザで `http://localhost:3000` を開き、デフォルトの認証情報（ユーザー名: `admin`, パスワード: `prom-operator`）でログインします。

`kube-prometheus-stack`の大きな利点の一つは、PrometheusデータソースがGrafanaに自動的にプロビジョニングされる点です。手動でデータソースを接続する必要はありません。

### 5.2. 事前設定済みダッシュボードの探索

Grafanaの左側メニューから`Dashboards`セクションに移動します。ここには、`kube-prometheus-stack`によって自動的にインポートされた、KubernetesやNode Exporterに関する価値の高いダッシュボードが多数用意されています。これらを探索することで、導入した監視スタックが即座に価値を提供することを実感できます。

### 5.3. ハンズオン：カスタムLLMダッシュボードの構築

ここからは、本章の核心的な実践演習として、先に計装したカスタムメトリクスを可視化するダッシュボードをゼロから構築します。

Grafanaで新しいダッシュボードを作成し、以下のパネルを追加していきます。各パネルでは、Prometheus Query Language（PromQL）を使用してデータを照会・加工します。単純なメトリクスを収集するだけでは不十分で、`rate()`や`histogram_quantile`といったPromQLの関数や集約演算子を適用することで、初めて意味のある洞察が引き出されます。例えば、単純な平均レイテンシは、少数の極端に遅いリクエストによって歪められる可能性がありますが、99パーセンタイル（P99）レイテンシを計算することで、ユーザーが体験する最悪ケースのパフォーマンスを把握できます。これはSREのベストプラクティスに沿ったアプローチです。

*   **パネル1：APIパフォーマンス**
    *   **リクエストレート (RPS)**
        *   クエリ: `sum(rate(llm_api_requests_total[5m]))`
        *   説明: 5分間の移動平均で、API全体のリクエスト秒間処理数を計算します。
    *   **P99 レイテンシ**
        *   クエリ: `histogram_quantile(0.99, sum(rate(llm_api_request_latency_seconds_bucket[5m])) by (le, endpoint))`
        *   説明: 99%のリクエストが完了するまでにかかる時間をエンドポイント別に計算します。
    *   **エラーレート (%)**
        *   クエリ: `(sum(rate(llm_api_requests_total{status_code=~"5.."}[5m])) / sum(rate(llm_api_requests_total[5m]))) * 100`
        *   説明: サーバーエラー（ステータスコード5xx）の割合を計算します。
*   **パネル2：GPUフリートの健全性**
    *   **平均GPU使用率**
        *   クエリ: `avg(DCGM_FI_DEV_GPU_UTIL) by (kubernetes_pod_node_name)`
        *   説明: ノードごとの平均GPU使用率を表示します。
    *   **GPUメモリ使用量合計**
        *   クエリ: `sum(DCGM_FI_DEV_FB_USED) / 1024`
        *   説明: クラスタ全体のGPUメモリ使用量をGiB単位で表示します。
*   **パネル3：コストと使用状況の監視**
    *   **処理トークン数（1分あたり）**
        *   クエリ: `sum(rate(llm_api_tokens_processed_total[1m]))`
        *   説明: 1分あたりの合計処理トークン数を表示し、コストの傾向を把握します。

### 5.4. ダッシュボードのJSONとしてのインポート・エクスポート

Grafanaのダッシュボードは、その全ての定義をJSONモデルとしてエクスポートできます。これは、「Dashboard-as-Code」というプラクティスを実践する上で非常に重要です。ダッシュボードの定義をGitなどのバージョン管理システムで管理することで、変更履歴の追跡、チーム間での共有、そして災害復旧が容易になります。

ダッシュボードの右上にある共有アイコンをクリックし、「Export」タブを選択することでJSONを取得できます。逆に、新しいダッシュボードを作成する際に「Import」ボタンからJSONファイルをアップロードすることも可能です。

## 6. プロアクティブなアラート：Alertmanagerによる洞察から行動へ

監視データを運用に活かす最後のステップは、問題が発生した際にエンジニアへ能動的に通知する仕組み、つまりアラートを構築することです。

### 6.1. アラートのパイプライン：PrometheusからAlertmanager、そしてあなたへ

アラートの基本的な流れは以下の通りです。

1.  Prometheusが、定義されたアラートルールを定期的に評価します。
2.  ルールの条件が満たされると、アラートはまず`Pending`（保留）状態になり、指定された期間（`for`句）を超えて条件が満たされ続けると`Firing`（発火）状態になります。
3.  `Firing`状態のアラートは、Alertmanagerに送信されます。
4.  Alertmanagerは、受け取ったアラートを重複排除し、ルールに基づいてグルーピングし、設定された通知先（レシーバー）へルーティングします。

### 6.2. ハンズオン：PrometheusRuleによるアラートルールの定義

Prometheus Operatorを使用している環境では、`PrometheusRule`というカスタムリソース（CRD）を使って、Kubernetesネイティブな方法でアラートルールを定義します。

以下に、実用的な`PrometheusRule`のYAML定義例を2つ示します。

*   **ルール例1：高GPU温度アラート**
    GPUの温度が一定時間、危険な閾値を超えた場合にクリティカルなアラートを発火させます。
```yaml
# gpu-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gpu-alerts
  namespace: monitoring
  labels:
    release: prometheus-stack
spec:
  groups:
  - name: gpu.rules
    rules:
    - alert: HighGpuTemperature
      expr: DCGM_FI_DEV_GPU_TEMP > 85
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "GPU temperature is critical on {{ $labels.kubernetes_pod_node_name }}"
        description: "GPU on node {{ $labels.kubernetes_pod_node_name }} has been over 85C for 5 minutes."
```
*   **ルール例2：高API P99レイテンシ**
    APIのP99レイテンシが定義されたSLO（例：1秒）を超えた場合に警告アラートを発火させます。
```yaml
# api-latency-alert.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: api-latency-alert
  namespace: monitoring
  labels:
    release: prometheus-stack
spec:
  groups:
  - name: api.rules
    rules:
    - alert: HighApiP99Latency
      expr: histogram_quantile(0.99, sum(rate(llm_api_request_latency_seconds_bucket[5m])) by (le)) > 1.0
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "High API P99 Latency"
        description: "The API P99 latency has been above 1s for the last 10 minutes."
```
これらのYAMLファイルを`kubectl apply -f <filename>`でクラスタに適用します。

### 6.3. ハンズオン：Slack通知チャネルの設定

次に、発火したアラートをSlackで受け取るための設定を行います。

1.  **SlackでIncoming Webhookを作成します。**
    Slackのアプリディレクトリから「Incoming Webhooks」を追加し、通知を投稿したいチャンネルを選択してWebhook URLを生成します。このURLは機密情報として扱ってください。
2.  **Alertmanagerの設定を更新します。**
    `kube-prometheus-stack`では、Alertmanagerの設定は`alertmanager-prometheus-stack-kube-alertmanager`という名前のKubernetes Secretに保存されています。このSecretを取得し、デコードして、Slackの通知設定を追加して更新します。
    *   現在のSecretを取得し、デコードします。
```bash
kubectl get secret alertmanager-prometheus-stack-kube-alertmanager -n monitoring -o=jsonpath='{.data.alertmanager\.yaml}' | base64 --decode > alertmanager.yaml
```
    *   `alertmanager.yaml`ファイルを編集し、`receivers`セクションにSlackの設定を追加します。また、`route`セクションでデフォルトの通知先をSlackに設定します。
```yaml
# alertmanager.yaml の編集例
global:
  resolve_timeout: 5m
route:
  group_by: ['job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'slack-notifications' # デフォルトのレシーバー
receivers:
- name: 'null'
- name: 'slack-notifications' # 新しいレシーバー
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL' # ここにWebhook URLを貼り付ける
    channel: '#your-alerts-channel' # 通知先のチャンネル名
    send_resolved: true
    title: '{{ .CommonLabels.alertname }}'
    text: >-
      {{ range .Alerts }}
      *Alert:* {{ .Annotations.summary }}
      *Description:* {{ .Annotations.description }}
      *Details:*
      {{ range .Labels.SortedPairs }} • *{{ .Name }}:* `{{ .Value }}`
      {{ end }}
      {{ end }}
```
    *   編集したファイルをエンコードし直し、Secretを更新します。
```bash
kubectl create secret generic alertmanager-prometheus-stack-kube-alertmanager \
  --namespace monitoring \
  --from-file=alertmanager.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
```
3.  **アラートをテストします。**
    設定が正しく行われたかを確認するため、意図的にアラートを発火させてみます。例えば、監視対象のDeploymentのレプリカ数を0にスケールダウンさせると、`kube-prometheus-stack`にデフォルトで含まれている`KubeDeploymentReplicasMismatch`アラートが発火します。数分後、設定したSlackチャンネルに通知が届けば、設定は成功です。

## 7. まとめ：より深い可観測性への基礎としてのメトリクス

本章では、LLMアプリケーションの運用における可観測性の重要性から説き起こし、その実現に向けた具体的な道のりを歩んできました。

### 7.1. 到達点の確認：我々のシステムに「問える」ようになったこと

この章を通じて、読者は単なる理論の学習に留まらず、本番環境で通用する監視スタックを構築し、インフラからアプリケーションに至るまで、あらゆる層を計装し、その結果を可視化・警告する能力を身につけました。今や、以下のような重要な問いに、データに基づいて答えることができます。

*   「GPUフリートは効果的に活用されているか？」
*   「エンドユーザーが体感するAPIのレイテンシはどの程度か？」
*   「このサービスの運用コスト（トークン消費量）はどれくらいか？」
*   「ノードのGPUが過熱した場合、即座に通知を受け取れるか？」

### 7.2. メトリクスの限界：「なぜ」を知る必要性

メトリクスは、「何が」「どれくらい」起きているかを把握する上で非常に強力ですが、障害の根本的な「なぜ」を説明するには不十分な場合があります。エラー率の急上昇は観測結果であり、その原因となったスタックトレースはログの中にしかありません。

### 7.3. 次の章への架け橋：ログとトレースの導入

本章で築いたメトリクス監視の基盤は、可観測性の全体像を完成させるための第一歩に過ぎません。今後の章では、残る2つの柱を探求していきます。

*   **Lokiによるロギング**：次章では、PrometheusやGrafanaとシームレスに連携するよう設計されたログ集約システム、Lokiを紹介します。Promtailエージェントを用いてKubernetes Podからログを収集し、Grafana上でメトリクスとログを相関させる方法を学びます。
*   **OpenTelemetryとJaegerによる分散トレーシング**：さらにその先の章では、3番目の柱であるトレースを扱います。計装の新たな標準となりつつあるOpenTelemetry を用いて、APIゲートウェイからRAGサービス、ベクトルDB、そしてLLMプロバイダーに至るまで、LLMアプリケーションチェーン全体のリクエストを追跡し、Jaegerで可視化する方法を解説します。これにより、複雑な分散AIシステムにおける真の根本原因分析が可能になります。

本章で紹介したPrometheus、Grafana、そして次章以降で登場するLoki、Jaeger、OpenTelemetryは、単なる人気ツールの寄せ集めではありません。これらは、クラウドネイティブ時代における、統合されたオープンソースの可観測性エコシステムを形成しています。Grafanaはメトリクス（Prometheusから）、ログ（Lokiから）、トレース（Jaeger/Tempoから）の統一された可視化レイヤーとして機能し、OpenTelemetryはこれら3種類のシグナル全てを生成するための標準的な手段となりつつあります。特に、OpenLLMetryのようなプロジェクトは、LLMアプリケーションに特化したOTel拡張機能を提供しており、このエコシステムの将来性を示唆しています。

したがって、これからの学習の道筋は、個別のツールを習得することではなく、この強力な統合スタックを使いこなすことにあります。本章で学んだメトリクスは、その壮大なエコシステムへの、不可欠な第一歩なのです。

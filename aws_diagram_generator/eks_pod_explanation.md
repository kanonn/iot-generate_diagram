# EKS Pod 情報の取得に関する技術的制約について

## 概要

本ドキュメントでは、AWS アーキテクチャ図生成ツールにおいて、EKS（Amazon Elastic Kubernetes Service）クラスター内の Pod 情報を取得・表示できない理由について、技術的観点から説明いたします。

---

## 結論

**EKS クラスター内の Pod 情報は、AWS API のみでは取得できません。**

これは技術的制約であり、以下の理由によります。

---

## 詳細な技術的理由

### 1. Pod は AWS リソースではない

| リソース種別 | 管理者 | API |
|------------|-------|-----|
| EKS クラスター | AWS | AWS API (`eks:DescribeCluster`) |
| EC2 ノード | AWS | AWS API (`ec2:DescribeInstances`) |
| **Pod** | **Kubernetes** | **Kubernetes API** |

Pod は Kubernetes のネイティブリソースであり、AWS のリソースではありません。そのため、AWS API（boto3）では Pod の情報にアクセスすることができません。

### 2. AWS API で取得できる EKS 関連情報

AWS API で取得可能な情報：

```
✓ EKS クラスター名、バージョン、エンドポイント
✓ クラスターのセキュリティグループ
✓ クラスターのサブネット設定
✓ ノードグループ（EC2 インスタンスグループ）
✓ Fargate プロファイル
```

AWS API で取得**できない**情報：

```
✗ Pod の一覧・状態
✗ Deployment、Service、ConfigMap 等の Kubernetes リソース
✗ Pod 内のコンテナ情報
✗ Pod のリソース使用状況
```

### 3. Pod 情報を取得するには

Pod 情報を取得するには、以下のいずれかが必要です：

#### 方法 A: Kubernetes API の直接呼び出し

```python
# kubectl や Kubernetes Python クライアントが必要
from kubernetes import client, config

config.load_kube_config()  # kubeconfig が必要
v1 = client.CoreV1Api()
pods = v1.list_pod_for_all_namespaces()
```

**必要条件：**
- `kubeconfig` ファイル（クラスターへの認証情報）
- Kubernetes Python クライアント（`kubernetes` パッケージ）
- クラスターへのネットワークアクセス

#### 方法 B: kubectl コマンドの実行

```bash
kubectl get pods --all-namespaces
```

**必要条件：**
- `kubectl` のインストール
- `kubeconfig` の設定
- クラスターへのネットワークアクセス

### 4. CloudFormation / YAML ファイルに Pod 情報が含まれない理由

CloudFormation は AWS リソースのプロビジョニングツールであり、Kubernetes リソースは管理対象外です。

```yaml
# CloudFormation で定義できるもの
Resources:
  MyEKSCluster:
    Type: AWS::EKS::Cluster  # ✓ EKS クラスター
  
  MyNodeGroup:
    Type: AWS::EKS::Nodegroup  # ✓ ノードグループ

# CloudFormation で定義できないもの
# Pod、Deployment、Service 等は Kubernetes マニフェストで定義
```

Pod は Kubernetes マニフェスト（YAML）で定義されますが、これは CloudFormation とは別の仕組みです。

### 5. 実行時にのみ存在する Pod

Pod は動的なリソースであり、以下の特性があります：

- デプロイ時に作成され、削除時に消える
- スケーリングにより数が変動する
- 障害時に自動的に再作成される
- ノード間で移動する可能性がある

そのため、静的な設計図（CloudFormation）には含まれません。

---

## まとめ

| 項目 | 説明 |
|-----|------|
| **取得不可の理由** | Pod は Kubernetes リソースであり、AWS リソースではないため |
| **AWS API の限界** | AWS API は EKS クラスター自体の情報のみ取得可能 |
| **Pod 取得に必要なもの** | Kubernetes API + kubeconfig + ネットワークアクセス |
| **本ツールの制約** | AWS API のみ使用のため、Pod 情報は取得不可 |

---

## 補足：対応策の提案

将来的に Pod 情報を含めたい場合、以下の対応が考えられます：

1. **Kubernetes クライアントの統合**
   - `kubernetes` Python パッケージを追加
   - ユーザーに kubeconfig の提供を求める
   
2. **kubectl 出力のインポート**
   - `kubectl get pods -o yaml` の出力をインポートする機能を追加

3. **AWS の代替サービス活用**
   - Amazon EKS Pod Identity Agent のログを参照（限定的）

ただし、いずれの方法も AWS API 以外のツール・認証情報が必要となります。

---

**作成日**: 2025年12月22日  
**対象ツール**: AWS Architecture Diagram Generator V3

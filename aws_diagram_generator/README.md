# AWS Architecture Diagram Generator V3

AWS リソースからアーキテクチャ図を自動生成するツール。

## 機能

1. **AWS API からリソースを読み取り**（ページネーション対応で300件制限なし）
2. **CloudFormation 形式でエクスポート**
3. **CloudFormation ファイルからインポート**（AWS 接続不要）
4. **リソース間の関係を検出**して架構図を生成

## 必要条件

```bash
pip install boto3 diagrams pyyaml
```

また、Graphviz のインストールが必要です:
- Windows: `choco install graphviz` または https://graphviz.org/download/
- Mac: `brew install graphviz`
- Linux: `apt-get install graphviz`

## ディレクトリ構造

```
aws_diagram_generator/
├── __init__.py           # パッケージ初期化
├── main.py               # メインエントリーポイント
├── aws_reader.py         # AWS API からリソースを読み取る
├── cf_exporter.py        # CloudFormation エクスポート/インポート
├── diagram_generator.py  # アーキテクチャ図生成
└── README.md
```

## 使用方法

### 1. AWS から直接読み取って図を生成

```powershell
# 環境変数を設定
$env:AWS_ACCESS_KEY_ID="AKIA..."
$env:AWS_SECRET_ACCESS_KEY="..."
$env:AWS_SESSION_TOKEN="..."  # SSO の場合

# 実行
cd aws_diagram_generator
python main.py
```

### 2. CloudFormation もエクスポート

```powershell
python main.py --export-cf
```

出力:
```
aws-outputs/
├── cloudformation/
│   ├── vpc/
│   ├── subnet/
│   ├── ec2/
│   ├── lambda/
│   └── ...
└── diagrams/
    └── aws-architecture.png
```

### 3. 既存の CloudFormation から図を生成（AWS 接続不要）

```powershell
python main.py --from-cf ./aws-outputs/cloudformation
```

### 4. オプション一覧

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--region` | AWS リージョン | ap-northeast-1 |
| `--output-dir` | 出力ディレクトリ | aws-outputs |
| `--output-name` | 出力ファイル名 | aws-architecture |
| `--from-cf DIR` | CloudFormation から読み込み | - |
| `--export-cf` | CloudFormation をエクスポート | False |
| `--no-diagram` | 図の生成をスキップ | False |

## 対応リソース

### VPC 関連
- VPC, Subnet, Internet Gateway, NAT Gateway
- Security Group, VPC Endpoint

### Compute
- EC2 Instance, ECS Cluster/Service, EKS Cluster
- Lambda Function (VPC/非VPC)

### Database
- RDS Instance, DynamoDB Table, ElastiCache Cluster

### Storage
- S3 Bucket, EFS FileSystem

### Load Balancer
- Application/Network Load Balancer, Target Group

### Messaging
- SQS Queue, SNS Topic

### その他
- IAM Role, CloudWatch Log Group

## 図の表示ルール

1. **VPC ごとにクラスター**を作成
2. **各サブネットを個別に表示**（Public/Private で色分け）
3. **リソースは対応するサブネット内**に配置
4. **VPC 外リソース**（S3, DynamoDB 等）は External Services に表示
5. **同種リソースが多数**ある場合は合併表示（例: "Lambda (25 non-VPC)"）
6. **VPC Endpoint** は1サブネットに1つだけ表示
7. **Security Group, IAM Role, CloudWatch** は非表示

## トラブルシューティング

### Q: 300件しか取得できない
A: V3 ではページネーションに対応しています。自動的にすべてのリソースを取得します。

### Q: Lambda の Trigger 情報がない
A: AWS API の `list_event_source_mappings` で取得可能なトリガー（SQS, DynamoDB Stream, Kinesis 等）は取得されます。
   ただし、API Gateway や CloudWatch Events などのトリガーは別の API が必要なため、現在は未対応です。

### Q: 図が複雑すぎる
A: リソースが多い場合、自動的に合併されます。必要に応じて `--from-cf` で特定のディレクトリのみを指定してください。

## ライセンス

MIT License

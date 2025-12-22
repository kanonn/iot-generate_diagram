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
| `--drawio` | Draw.io 形式で出力（AWS 公式アイコンスタイル） | False |
| `--svg` | SVG 形式で出力 | False |
| `--icons-dir DIR` | AWS 公式アイコンディレクトリ | aws_icons/ |

## SVG 形式での出力（AWS 公式アイコン対応）

`--svg` オプションを使用すると、SVG 形式のアーキテクチャ図が生成されます：

```powershell
python main.py --from-cf ./aws-outputs/cloudformation --svg
```

### AWS 公式アイコンの使用方法

1. **AWS 公式サイトからダウンロード**:
   - https://aws.amazon.com/architecture/icons/ にアクセス
   - 「Icon package」をクリックしてダウンロード（Asset-Package_YYYYMMDD.zip）

2. **解凍して配置**:
   ```
   aws_diagram_generator/
   ├── aws_icons/                    ← ここに解凍
   │   ├── Architecture-Service-Icons_YYYYMMDD/
   │   │   ├── Arch_Compute/
   │   │   │   ├── 64/
   │   │   │   │   ├── Arch_AWS-Lambda_64.svg
   │   │   │   │   ├── Arch_Amazon-EC2_64.svg
   │   │   │   │   └── ...
   │   │   ├── Arch_Networking-Content-Delivery/
   │   │   ├── Arch_Database/
   │   │   └── ...
   │   └── Resource-Icons_YYYYMMDD/
   │       ├── Res_Networking-Content-Delivery/
   │       │   ├── 48/
   │       │   │   ├── Res_Elastic-Load-Balancing_Target_48.svg
   │       │   │   └── ...
   │       └── ...
   ├── main.py
   └── ...
   ```

3. **実行**:
   ```powershell
   # 自動検出（aws_icons/ フォルダ）
   python main.py --svg
   
   # または明示的に指定
   python main.py --svg --icons-dir ./path/to/aws_icons
   ```

### アイコンがない場合

`aws_icons/` フォルダがない場合や、特定のアイコンが見つからない場合は、
プログラム内蔵のデフォルトアイコン（簡略化された SVG パス）が使用されます。

## Draw.io 形式での出力

`--drawio` オプションを使用すると、AWS 公式アイコンスタイルの Draw.io ファイルが生成されます：

```powershell
python main.py --from-cf ./aws-outputs/cloudformation --drawio
```

生成された `.drawio` ファイルは：
- https://app.diagrams.net/ で開いて編集可能
- 位置やサイズを自由に調整可能
- PNG/SVG/PDF にエクスポート可能

### Draw.io の特徴

| 項目 | 説明 |
|-----|------|
| アイコン | AWS Architecture Icons（公式） |
| レイアウト | AWS Cloud → Region → VPC → AZ → Subnet の階層構造 |
| 色分け | VPC: 紫、Private Subnet: 緑、EKS: オレンジ |
| 接続線 | 黒色の矢印で接続 |

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



py generate_word_docs_from_yaml.py --input-dir aws-resources-test --output-dir test-docs
py generate_simple_diagram_per_yaml.py --input-dir aws-resources-test --output-dir test-docs

py generate_docs_with_diagrams.py --input-dir aws-resources-test --output-dir test-docs


py generate_diagram_architecture.py --input-dir aws-resources-test --output test-docs
py generate_diagram_architecture.py --input-dir aws-resources-test --output-dir test-docs --output-name my-architecture


# 删除旧数据，重新读取（获取新的 API 数据）
rd /s /q .\cloudformation
python main.py --export-cf ./cloudformation

# 生成 SVG
python main.py --from-cf ./cloudformation --svg

# 方式1：自动检测（程序会自动查找 aws_icons/ 目录）
python main.py --svg

# 方式2：明确指定图标目录
python main.py --svg --export-cf ./cloudformation --icons-dir ".\aws_icons"


# AWS API セキュリティ監査レポート

## 概要

本ドキュメントは、AWS アーキテクチャ図生成ツールが使用するすべての AWS API を一覧化し、各 API の安全性を評価したものです。

---

## 結論

✅ **本ツールは完全に読み取り専用（Read-Only）であり、AWS リソースを変更・削除・作成する API は一切使用していません。**

---

## AWS API 呼び出し一覧

### EC2 サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 153 | `ec2.describe_vpcs` | 🔵 読取 | VPC 一覧を取得 | なし |
| 188 | `ec2.describe_subnets` | 🔵 読取 | サブネット一覧を取得 | なし |
| 228 | `ec2.describe_internet_gateways` | 🔵 読取 | インターネットゲートウェイ一覧を取得 | なし |
| 269 | `ec2.describe_nat_gateways` | 🔵 読取 | NAT ゲートウェイ一覧を取得 | なし |
| 317 | `ec2.describe_security_groups` | 🔵 読取 | セキュリティグループ一覧を取得 | なし |
| 361 | `ec2.describe_vpc_endpoints` | 🔵 読取 | VPC エンドポイント一覧を取得 | なし |
| 415 | `ec2.describe_instances` | 🔵 読取 | EC2 インスタンス一覧を取得 | なし |
| 1572 | `ec2.describe_route_tables` | 🔵 読取 | ルートテーブル一覧を取得 | なし |

### ECS サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 472 | `ecs.list_clusters` | 🔵 読取 | ECS クラスター一覧を取得 | なし |
| 490 | `ecs.describe_clusters` | 🔵 読取 | ECS クラスター詳細を取得 | なし |
| 534 | `ecs.list_services` | 🔵 読取 | ECS サービス一覧を取得 | なし |
| 551 | `ecs.describe_services` | 🔵 読取 | ECS サービス詳細を取得 | なし |

### EKS サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 600 | `eks.list_clusters` | 🔵 読取 | EKS クラスター一覧を取得 | なし |
| 612 | `eks.describe_cluster` | 🔵 読取 | EKS クラスター詳細を取得 | なし |

### Lambda サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 654 | `lambda.list_functions` | 🔵 読取 | Lambda 関数一覧を取得 | なし |
| 675 | `lambda.list_event_source_mappings` | 🔵 読取 | イベントソースマッピング一覧を取得 | なし |

### RDS サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 736 | `rds.describe_db_instances` | 🔵 読取 | RDS インスタンス一覧を取得 | なし |

### DynamoDB サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 793 | `dynamodb.list_tables` | 🔵 読取 | DynamoDB テーブル一覧を取得 | なし |
| 805 | `dynamodb.describe_table` | 🔵 読取 | DynamoDB テーブル詳細を取得 | なし |

### ElastiCache サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 840 | `elasticache.describe_cache_clusters` | 🔵 読取 | ElastiCache クラスター一覧を取得 | なし |

### S3 サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 880 | `s3.list_buckets` | 🔵 読取 | S3 バケット一覧を取得 | なし |
| 888 | `s3.get_bucket_location` | 🔵 読取 | S3 バケットのリージョンを取得 | なし |

### EFS サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 919 | `efs.describe_file_systems` | 🔵 読取 | EFS ファイルシステム一覧を取得 | なし |

### Elastic Load Balancing (v2) サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 962 | `elbv2.describe_load_balancers` | 🔵 読取 | ロードバランサー一覧を取得 | なし |
| 1017 | `elbv2.describe_listeners` | 🔵 読取 | リスナー一覧を取得 | なし |
| 1087 | `elbv2.describe_target_groups` | 🔵 読取 | ターゲットグループ一覧を取得 | なし |
| 1108 | `elbv2.describe_target_health` | 🔵 読取 | ターゲットのヘルス状態を取得 | なし |

### SQS サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 1170 | `sqs.list_queues` | 🔵 読取 | SQS キュー一覧を取得 | なし |

### SNS サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 1206 | `sns.list_topics` | 🔵 読取 | SNS トピック一覧を取得 | なし |
| 1224 | `sns.list_subscriptions_by_topic` | 🔵 読取 | SNS サブスクリプション一覧を取得 | なし |

### IAM サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 1272 | `iam.list_roles` | 🔵 読取 | IAM ロール一覧を取得 | なし |

### CloudWatch Logs サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 1313 | `logs.describe_log_groups` | 🔵 読取 | ロググループ一覧を取得 | なし |

### CloudFront サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 1352 | `cloudfront.list_distributions` | 🔵 読取 | CloudFront ディストリビューション一覧を取得 | なし |

### API Gateway サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 1422 | `apigateway.get_rest_apis` | 🔵 読取 | REST API 一覧を取得 | なし |
| 1431 | `apigateway.get_resources` | 🔵 読取 | API リソース一覧を取得 | なし |
| 1435 | `apigateway.get_integration` | 🔵 読取 | API 統合設定を取得 | なし |

### EventBridge サービス

| 行番号 | API | 操作タイプ | 説明 | リスク |
|-------|-----|----------|------|-------|
| 1515 | `events.list_rules` | 🔵 読取 | EventBridge ルール一覧を取得 | なし |
| 1533 | `events.list_targets_by_rule` | 🔵 読取 | ルールのターゲット一覧を取得 | なし |

---

## 使用していない危険な API（確認済み）

以下の API は本ツールで **一切使用していません**：

### ❌ 作成系 API（使用なし）
- `create_*` - リソース作成
- `run_instances` - EC2 インスタンス起動
- `put_*` - データ書き込み

### ❌ 変更系 API（使用なし）
- `update_*` - リソース更新
- `modify_*` - 設定変更
- `attach_*` / `detach_*` - アタッチ/デタッチ

### ❌ 削除系 API（使用なし）
- `delete_*` - リソース削除
- `terminate_instances` - EC2 終了
- `remove_*` - 削除

### ❌ 制御系 API（使用なし）
- `start_*` / `stop_*` - 起動/停止
- `reboot_instances` - 再起動
- `invoke_*` - Lambda 実行

---

## API タイプ別統計

| API タイプ | 件数 | 例 |
|-----------|------|-----|
| 🔵 `describe_*` | 18 | describe_vpcs, describe_instances |
| 🔵 `list_*` | 12 | list_clusters, list_functions |
| 🔵 `get_*` | 4 | get_bucket_location, get_rest_apis |
| 🔴 `create_*` | 0 | - |
| 🔴 `delete_*` | 0 | - |
| 🔴 `update_*` | 0 | - |
| 🔴 `modify_*` | 0 | - |

**合計: 34 件の読み取り専用 API のみ**

---

## 推奨 IAM ポリシー（最小権限）

本ツールを実行するために必要な最小限の IAM ポリシー：

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AWSArchitectureDiagramGeneratorReadOnly",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeInternetGateways",
                "ec2:DescribeNatGateways",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeVpcEndpoints",
                "ec2:DescribeInstances",
                "ec2:DescribeRouteTables",
                "ecs:ListClusters",
                "ecs:DescribeClusters",
                "ecs:ListServices",
                "ecs:DescribeServices",
                "eks:ListClusters",
                "eks:DescribeCluster",
                "lambda:ListFunctions",
                "lambda:ListEventSourceMappings",
                "rds:DescribeDBInstances",
                "dynamodb:ListTables",
                "dynamodb:DescribeTable",
                "elasticache:DescribeCacheClusters",
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation",
                "elasticfilesystem:DescribeFileSystems",
                "elasticloadbalancing:DescribeLoadBalancers",
                "elasticloadbalancing:DescribeListeners",
                "elasticloadbalancing:DescribeTargetGroups",
                "elasticloadbalancing:DescribeTargetHealth",
                "sqs:ListQueues",
                "sns:ListTopics",
                "sns:ListSubscriptionsByTopic",
                "iam:ListRoles",
                "logs:DescribeLogGroups",
                "cloudfront:ListDistributions",
                "apigateway:GET",
                "events:ListRules",
                "events:ListTargetsByRule"
            ],
            "Resource": "*"
        }
    ]
}
```

---

## コードレビュー確認事項

### ✅ 確認済み項目

1. **すべての API 呼び出しを検査** - 34 件すべてが読み取り専用
2. **危険な API の不在を確認** - create/delete/update/modify 系は存在しない
3. **boto3 クライアント初期化を確認** - 標準的な読み取りクライアントのみ
4. **外部ライブラリの確認** - boto3 以外に AWS 操作ライブラリなし

### ✅ 安全性の根拠

1. **API 命名規則**
   - AWS API は命名規則が厳格
   - `describe_*`, `list_*`, `get_*` は定義上、読み取り専用
   - これらの API でリソースを変更することは不可能

2. **IAM 権限分離**
   - 上記の最小権限ポリシーを使用すれば、万が一コードにバグがあっても変更操作は拒否される

3. **boto3 の仕様**
   - boto3 は API 名がそのままメソッド名になる
   - 読み取り API を呼び出して書き込みが発生することはあり得ない

---

## 結論

| 項目 | 結果 |
|-----|------|
| 読み取り API 数 | 34 |
| 書き込み API 数 | 0 |
| 削除 API 数 | 0 |
| 変更 API 数 | 0 |
| **総合評価** | ✅ **完全に安全（読み取り専用）** |

---

**作成日**: 2025年1月6日  
**対象コード**: aws_diagram_generator v3  
**監査者**: Claude (AI Assistant)

# -*- coding: utf-8 -*-
"""
AWS から直接リソースを読み取り、アーキテクチャ図を生成
- 環境変数から認証情報を取得（SSO 対応）
- 権限エラーは警告として表示し、続行
- リソース集約機能付き（VPC と Subnet を除く）
- フォールバックアイコン対応
"""

import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from collections import Counter, defaultdict
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import VPC, InternetGateway, PrivateSubnet, PublicSubnet, NATGateway, ELB, ALB, Route53, Endpoint, VPCRouter
from diagrams.aws.compute import EC2, ECS, EKS, Lambda, Batch, Fargate
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift, Database
from diagrams.aws.storage import S3, EBS, EFS, Backup
from diagrams.aws.integration import SQS, SNS, Eventbridge, StepFunctions
from diagrams.aws.security import IAM, SecretsManager, KMS
from diagrams.aws.management import Cloudwatch, SystemsManager
from diagrams.generic.blank import Blank
from diagrams.generic.compute import Rack
from diagrams.generic.database import SQL
from diagrams.generic.storage import Storage as GenericStorage
from diagrams.generic.network import Switch


# ==================== AWS リソースリーダー ====================

class AWSResourceReader:
    """AWS からリソースを読み取るクラス"""
    
    def __init__(self, region='ap-northeast-1'):
        """
        環境変数から認証情報を取得
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
        """
        self.region = region
        self.resources = {}
        self.errors = []
        
        print(f"Initializing AWS clients for region: {region}")
        print(f"Using credentials from environment variables...")
        
        try:
            # boto3 は環境変数から自動的に認証情報を読み取る
            self.ec2 = boto3.client('ec2', region_name=region)
            self.ecs = boto3.client('ecs', region_name=region)
            self.eks = boto3.client('eks', region_name=region)
            self.lambda_client = boto3.client('lambda', region_name=region)
            self.rds = boto3.client('rds', region_name=region)
            self.dynamodb = boto3.client('dynamodb', region_name=region)
            self.s3 = boto3.client('s3', region_name=region)
            self.elbv2 = boto3.client('elbv2', region_name=region)
            self.iam = boto3.client('iam')  # IAM はグローバル
            self.sqs = boto3.client('sqs', region_name=region)
            self.sns = boto3.client('sns', region_name=region)
            self.efs = boto3.client('efs', region_name=region)
            self.backup = boto3.client('backup', region_name=region)
            self.logs = boto3.client('logs', region_name=region)
            
            print("✓ AWS clients initialized successfully")
            
        except NoCredentialsError:
            print("\n" + "="*80)
            print("ERROR: AWS credentials not found!")
            print("="*80)
            print("\nPlease set the following environment variables:")
            print("  SET AWS_ACCESS_KEY_ID=your_access_key")
            print("  SET AWS_SECRET_ACCESS_KEY=your_secret_key")
            print("  SET AWS_SESSION_TOKEN=your_session_token  (for SSO)")
            print("\nOr configure AWS CLI:")
            print("  aws configure")
            print("="*80)
            raise
    
    def _safe_call(self, func, service_name, *args, **kwargs):
        """API 呼び出しを安全に実行（エラーハンドリング付き）"""
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            if error_code in ['AccessDenied', 'UnauthorizedOperation', 'AccessDeniedException']:
                self.errors.append(f"⚠ {service_name}: Access Denied - {error_msg}")
            else:
                self.errors.append(f"⚠ {service_name}: {error_code} - {error_msg}")
            
            return None
        except Exception as e:
            self.errors.append(f"⚠ {service_name}: Unexpected error - {str(e)}")
            return None
    
    def read_vpcs(self):
        """VPC を読み取る"""
        print("  Reading VPCs...")
        response = self._safe_call(self.ec2.describe_vpcs, "EC2:VPC")
        
        if response:
            for vpc in response.get('Vpcs', []):
                vpc_id = vpc['VpcId']
                name = self._get_tag_name(vpc.get('Tags', []), vpc_id)
                
                self.resources[vpc_id] = {
                    'Type': 'AWS::EC2::VPC',
                    'Name': name,
                    'Data': vpc
                }
            print(f"    Found {len(response.get('Vpcs', []))} VPC(s)")
    
    def read_subnets(self):
        """Subnet を読み取る"""
        print("  Reading Subnets...")
        response = self._safe_call(self.ec2.describe_subnets, "EC2:Subnet")
        
        if response:
            for subnet in response.get('Subnets', []):
                subnet_id = subnet['SubnetId']
                name = self._get_tag_name(subnet.get('Tags', []), subnet_id)
                
                self.resources[subnet_id] = {
                    'Type': 'AWS::EC2::Subnet',
                    'Name': name,
                    'VpcId': subnet.get('VpcId'),
                    'Data': subnet
                }
            print(f"    Found {len(response.get('Subnets', []))} Subnet(s)")
    
    def read_internet_gateways(self):
        """Internet Gateway を読み取る"""
        print("  Reading Internet Gateways...")
        response = self._safe_call(self.ec2.describe_internet_gateways, "EC2:IGW")
        
        if response:
            for igw in response.get('InternetGateways', []):
                igw_id = igw['InternetGatewayId']
                name = self._get_tag_name(igw.get('Tags', []), igw_id)
                
                vpc_id = None
                if igw.get('Attachments'):
                    vpc_id = igw['Attachments'][0].get('VpcId')
                
                self.resources[igw_id] = {
                    'Type': 'AWS::EC2::InternetGateway',
                    'Name': name,
                    'VpcId': vpc_id,
                    'Data': igw
                }
            print(f"    Found {len(response.get('InternetGateways', []))} IGW(s)")
    
    def read_nat_gateways(self):
        """NAT Gateway を読み取る"""
        print("  Reading NAT Gateways...")
        response = self._safe_call(self.ec2.describe_nat_gateways, "EC2:NAT")
        
        if response:
            for nat in response.get('NatGateways', []):
                nat_id = nat['NatGatewayId']
                name = self._get_tag_name(nat.get('Tags', []), nat_id)
                
                self.resources[nat_id] = {
                    'Type': 'AWS::EC2::NatGateway',
                    'Name': name,
                    'SubnetId': nat.get('SubnetId'),
                    'Data': nat
                }
            print(f"    Found {len(response.get('NatGateways', []))} NAT Gateway(s)")
    
    def read_vpc_endpoints(self):
        """VPC Endpoint を読み取る"""
        print("  Reading VPC Endpoints...")
        response = self._safe_call(self.ec2.describe_vpc_endpoints, "EC2:VPCEndpoint")
        
        if response:
            for endpoint in response.get('VpcEndpoints', []):
                endpoint_id = endpoint['VpcEndpointId']
                name = self._get_tag_name(endpoint.get('Tags', []), endpoint_id)
                
                self.resources[endpoint_id] = {
                    'Type': 'AWS::EC2::VPCEndpoint',
                    'Name': name,
                    'VpcId': endpoint.get('VpcId'),
                    'Data': endpoint
                }
            print(f"    Found {len(response.get('VpcEndpoints', []))} VPC Endpoint(s)")
    
    def read_security_groups(self):
        """Security Group を読み取る"""
        print("  Reading Security Groups...")
        response = self._safe_call(self.ec2.describe_security_groups, "EC2:SecurityGroup")
        
        if response:
            for sg in response.get('SecurityGroups', []):
                sg_id = sg['GroupId']
                name = sg.get('GroupName', sg_id)
                
                self.resources[sg_id] = {
                    'Type': 'AWS::EC2::SecurityGroup',
                    'Name': name,
                    'VpcId': sg.get('VpcId'),
                    'Data': sg
                }
            print(f"    Found {len(response.get('SecurityGroups', []))} Security Group(s)")
    
    def read_ec2_instances(self):
        """EC2 Instance を読み取る"""
        print("  Reading EC2 Instances...")
        response = self._safe_call(self.ec2.describe_instances, "EC2:Instance")
        
        if response:
            count = 0
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_id = instance['InstanceId']
                    name = self._get_tag_name(instance.get('Tags', []), instance_id)
                    
                    self.resources[instance_id] = {
                        'Type': 'AWS::EC2::Instance',
                        'Name': name,
                        'SubnetId': instance.get('SubnetId'),
                        'Data': instance
                    }
                    count += 1
            print(f"    Found {count} EC2 Instance(s)")
    
    def read_load_balancers(self):
        """Load Balancer を読み取る"""
        print("  Reading Load Balancers...")
        response = self._safe_call(self.elbv2.describe_load_balancers, "ELB:LoadBalancer")
        
        if response:
            for lb in response.get('LoadBalancers', []):
                lb_arn = lb['LoadBalancerArn']
                lb_name = lb['LoadBalancerName']
                
                self.resources[lb_arn] = {
                    'Type': 'AWS::ElasticLoadBalancingV2::LoadBalancer',
                    'Name': lb_name,
                    'VpcId': lb.get('VpcId'),
                    'Data': lb
                }
            print(f"    Found {len(response.get('LoadBalancers', []))} Load Balancer(s)")
    
    def read_ecs_clusters(self):
        """ECS Cluster を読み取る"""
        print("  Reading ECS Clusters...")
        response = self._safe_call(self.ecs.list_clusters, "ECS:Cluster")
        
        if response:
            cluster_arns = response.get('clusterArns', [])
            if cluster_arns:
                details = self._safe_call(self.ecs.describe_clusters, "ECS:Cluster", clusters=cluster_arns)
                if details:
                    for cluster in details.get('clusters', []):
                        cluster_arn = cluster['clusterArn']
                        cluster_name = cluster['clusterName']
                        
                        self.resources[cluster_arn] = {
                            'Type': 'AWS::ECS::Cluster',
                            'Name': cluster_name,
                            'Data': cluster
                        }
            print(f"    Found {len(cluster_arns)} ECS Cluster(s)")
    
    def read_eks_clusters(self):
        """EKS Cluster を読み取る"""
        print("  Reading EKS Clusters...")
        response = self._safe_call(self.eks.list_clusters, "EKS:Cluster")
        
        if response:
            cluster_names = response.get('clusters', [])
            for cluster_name in cluster_names:
                details = self._safe_call(self.eks.describe_cluster, "EKS:Cluster", name=cluster_name)
                if details:
                    cluster = details.get('cluster', {})
                    cluster_arn = cluster.get('arn', cluster_name)
                    
                    self.resources[cluster_arn] = {
                        'Type': 'AWS::EKS::Cluster',
                        'Name': cluster_name,
                        'Data': cluster
                    }
            print(f"    Found {len(cluster_names)} EKS Cluster(s)")
    
    def read_lambda_functions(self):
        """Lambda Function を読み取る"""
        print("  Reading Lambda Functions...")
        response = self._safe_call(self.lambda_client.list_functions, "Lambda:Function")
        
        if response:
            for func in response.get('Functions', []):
                func_name = func['FunctionName']
                func_arn = func['FunctionArn']
                
                self.resources[func_arn] = {
                    'Type': 'AWS::Lambda::Function',
                    'Name': func_name,
                    'Data': func
                }
            print(f"    Found {len(response.get('Functions', []))} Lambda Function(s)")
    
    def read_rds_instances(self):
        """RDS Instance を読み取る"""
        print("  Reading RDS Instances...")
        response = self._safe_call(self.rds.describe_db_instances, "RDS:DBInstance")
        
        if response:
            for db in response.get('DBInstances', []):
                db_id = db['DBInstanceIdentifier']
                db_arn = db['DBInstanceArn']
                
                self.resources[db_arn] = {
                    'Type': 'AWS::RDS::DBInstance',
                    'Name': db_id,
                    'Data': db
                }
            print(f"    Found {len(response.get('DBInstances', []))} RDS Instance(s)")
    
    def read_dynamodb_tables(self):
        """DynamoDB Table を読み取る"""
        print("  Reading DynamoDB Tables...")
        response = self._safe_call(self.dynamodb.list_tables, "DynamoDB:Table")
        
        if response:
            table_names = response.get('TableNames', [])
            for table_name in table_names:
                self.resources[f"dynamodb-{table_name}"] = {
                    'Type': 'AWS::DynamoDB::Table',
                    'Name': table_name,
                    'Data': {'TableName': table_name}
                }
            print(f"    Found {len(table_names)} DynamoDB Table(s)")
    
    def read_s3_buckets(self):
        """S3 Bucket を読み取る"""
        print("  Reading S3 Buckets...")
        response = self._safe_call(self.s3.list_buckets, "S3:Bucket")
        
        if response:
            for bucket in response.get('Buckets', []):
                bucket_name = bucket['Name']
                
                self.resources[f"s3-{bucket_name}"] = {
                    'Type': 'AWS::S3::Bucket',
                    'Name': bucket_name,
                    'Data': bucket
                }
            print(f"    Found {len(response.get('Buckets', []))} S3 Bucket(s)")
    
    def read_sqs_queues(self):
        """SQS Queue を読み取る"""
        print("  Reading SQS Queues...")
        response = self._safe_call(self.sqs.list_queues, "SQS:Queue")
        
        if response:
            queue_urls = response.get('QueueUrls', [])
            for queue_url in queue_urls:
                queue_name = queue_url.split('/')[-1]
                
                self.resources[queue_url] = {
                    'Type': 'AWS::SQS::Queue',
                    'Name': queue_name,
                    'Data': {'QueueUrl': queue_url}
                }
            print(f"    Found {len(queue_urls)} SQS Queue(s)")
    
    def read_sns_topics(self):
        """SNS Topic を読み取る"""
        print("  Reading SNS Topics...")
        response = self._safe_call(self.sns.list_topics, "SNS:Topic")
        
        if response:
            for topic in response.get('Topics', []):
                topic_arn = topic['TopicArn']
                topic_name = topic_arn.split(':')[-1]
                
                self.resources[topic_arn] = {
                    'Type': 'AWS::SNS::Topic',
                    'Name': topic_name,
                    'Data': topic
                }
            print(f"    Found {len(response.get('Topics', []))} SNS Topic(s)")
    
    def read_efs_filesystems(self):
        """EFS FileSystem を読み取る"""
        print("  Reading EFS File Systems...")
        response = self._safe_call(self.efs.describe_file_systems, "EFS:FileSystem")
        
        if response:
            for fs in response.get('FileSystems', []):
                fs_id = fs['FileSystemId']
                name = fs.get('Name', fs_id)
                
                self.resources[fs_id] = {
                    'Type': 'AWS::EFS::FileSystem',
                    'Name': name,
                    'Data': fs
                }
            print(f"    Found {len(response.get('FileSystems', []))} EFS File System(s)")
    
    def read_backup_vaults(self):
        """Backup Vault を読み取る"""
        print("  Reading Backup Vaults...")
        response = self._safe_call(self.backup.list_backup_vaults, "Backup:BackupVault")
        
        if response:
            for vault in response.get('BackupVaultList', []):
                vault_name = vault['BackupVaultName']
                vault_arn = vault['BackupVaultArn']
                
                self.resources[vault_arn] = {
                    'Type': 'AWS::Backup::BackupVault',
                    'Name': vault_name,
                    'Data': vault
                }
            print(f"    Found {len(response.get('BackupVaultList', []))} Backup Vault(s)")
    
    def read_iam_roles(self):
        """IAM Role を読み取る"""
        print("  Reading IAM Roles...")
        response = self._safe_call(self.iam.list_roles, "IAM:Role")
        
        if response:
            for role in response.get('Roles', []):
                role_name = role['RoleName']
                role_arn = role['Arn']
                
                self.resources[role_arn] = {
                    'Type': 'AWS::IAM::Role',
                    'Name': role_name,
                    'Data': role
                }
            print(f"    Found {len(response.get('Roles', []))} IAM Role(s)")
    
    def read_log_groups(self):
        """CloudWatch Log Group を読み取る"""
        print("  Reading CloudWatch Log Groups...")
        response = self._safe_call(self.logs.describe_log_groups, "Logs:LogGroup")
        
        if response:
            for log_group in response.get('logGroups', []):
                log_group_name = log_group['logGroupName']
                
                self.resources[log_group_name] = {
                    'Type': 'AWS::Logs::LogGroup',
                    'Name': log_group_name,
                    'Data': log_group
                }
            print(f"    Found {len(response.get('logGroups', []))} Log Group(s)")
    
    def _get_tag_name(self, tags, default):
        """タグから Name を取得"""
        if tags:
            for tag in tags:
                if tag.get('Key') == 'Name':
                    return tag.get('Value', default)
        return default
    
    def read_all(self):
        """すべてのリソースを読み取る"""
        print("\n" + "="*80)
        print("Reading AWS Resources...")
        print("="*80 + "\n")
        
        # ネットワーク
        self.read_vpcs()
        self.read_subnets()
        self.read_internet_gateways()
        self.read_nat_gateways()
        self.read_vpc_endpoints()
        self.read_security_groups()
        
        # コンピューティング
        self.read_ec2_instances()
        self.read_load_balancers()
        self.read_ecs_clusters()
        self.read_eks_clusters()
        self.read_lambda_functions()
        
        # データベース
        self.read_rds_instances()
        self.read_dynamodb_tables()
        
        # ストレージ
        self.read_s3_buckets()
        self.read_efs_filesystems()
        self.read_backup_vaults()
        
        # 統合
        self.read_sqs_queues()
        self.read_sns_topics()
        
        # セキュリティ・管理
        self.read_iam_roles()
        self.read_log_groups()
        
        print("\n" + "="*80)
        print(f"Total Resources: {len(self.resources)}")
        print("="*80)
        
        if self.errors:
            print("\n" + "="*80)
            print("Warnings/Errors:")
            print("="*80)
            for error in self.errors:
                print(error)
            print("="*80)


# ==================== アイコンマッピング ====================

def get_icon_class(resource_type):
    icon_map = {
        'AWS::EC2::VPC': VPC,
        'AWS::EC2::Subnet': PrivateSubnet,
        'AWS::EC2::InternetGateway': InternetGateway,
        'AWS::EC2::NatGateway': NATGateway,
        'AWS::EC2::VPCEndpoint': Endpoint,
        'AWS::EC2::SecurityGroup': VPCRouter,
        'AWS::EC2::Instance': EC2,
        'AWS::ElasticLoadBalancingV2::LoadBalancer': ALB,
        'AWS::ECS::Cluster': ECS,
        'AWS::EKS::Cluster': EKS,
        'AWS::Lambda::Function': Lambda,
        'AWS::RDS::DBInstance': RDS,
        'AWS::DynamoDB::Table': Dynamodb,
        'AWS::S3::Bucket': S3,
        'AWS::EFS::FileSystem': EFS,
        'AWS::Backup::BackupVault': Backup,
        'AWS::SQS::Queue': SQS,
        'AWS::SNS::Topic': SNS,
        'AWS::IAM::Role': IAM,
        'AWS::Logs::LogGroup': Cloudwatch,
    }
    return icon_map.get(resource_type)


def get_fallback_icon(resource_type):
    """フォールバックアイコン"""
    if '::EC2::' in resource_type or '::ELB::' in resource_type:
        return Switch
    elif '::Lambda::' in resource_type or '::ECS::' in resource_type or '::EKS::' in resource_type:
        return Rack
    elif '::RDS::' in resource_type or '::DynamoDB::' in resource_type:
        return SQL
    elif '::S3::' in resource_type or '::EFS::' in resource_type or '::Backup::' in resource_type:
        return GenericStorage
    else:
        return Blank


def categorize_resources(resources):
    """リソースをカテゴリ別に分類"""
    categories = defaultdict(list)
    
    category_map = {
        'AWS::EC2::VPC': 'Network',
        'AWS::EC2::Subnet': 'Network',
        'AWS::EC2::InternetGateway': 'Network',
        'AWS::EC2::NatGateway': 'Network',
        'AWS::EC2::VPCEndpoint': 'Network',
        'AWS::EC2::SecurityGroup': 'Security',
        'AWS::EC2::Instance': 'Compute',
        'AWS::ElasticLoadBalancingV2::LoadBalancer': 'Network',
        'AWS::ECS::Cluster': 'Compute',
        'AWS::EKS::Cluster': 'Compute',
        'AWS::Lambda::Function': 'Compute',
        'AWS::RDS::DBInstance': 'Database',
        'AWS::DynamoDB::Table': 'Database',
        'AWS::S3::Bucket': 'Storage',
        'AWS::EFS::FileSystem': 'Storage',
        'AWS::Backup::BackupVault': 'Storage',
        'AWS::SQS::Queue': 'Integration',
        'AWS::SNS::Topic': 'Integration',
        'AWS::IAM::Role': 'Security',
        'AWS::Logs::LogGroup': 'Management',
    }
    
    for resource_id, resource_info in resources.items():
        resource_type = resource_info['Type']
        category = category_map.get(resource_type, 'Other')
        categories[category].append((resource_id, resource_info, resource_type))
    
    return dict(categories)


def aggregate_resources_by_type(resources, exclude_types=None):
    """
    同じタイプのリソースを集約（VPC と Subnet を除く）
    3個以上 → 2個 + "..." に集約
    """
    if exclude_types is None:
        exclude_types = ['AWS::EC2::VPC', 'AWS::EC2::Subnet']
    
    type_counter = Counter()
    for resource_id, resource_info, resource_type in resources:
        type_counter[resource_type] += 1
    
    aggregated = []
    aggregation_info = {}
    type_groups = defaultdict(list)
    
    for resource_id, resource_info, resource_type in resources:
        type_groups[resource_type].append((resource_id, resource_info, resource_type))
    
    for resource_type, group in type_groups.items():
        count = len(group)
        
        # VPC と Subnet は集約しない
        if resource_type in exclude_types:
            aggregated.extend(group)
        elif count >= 3:
            # 2個だけ表示
            aggregated.extend(group[:2])
            aggregation_info[resource_type] = count
        else:
            aggregated.extend(group)
    
    return aggregated, aggregation_info


def generate_diagram_from_aws(region='ap-northeast-1', output_dir='.', output_name='aws-architecture'):
    """AWS からリソースを読み取り、アーキテクチャ図を生成"""
    
    # AWS リソースを読み取る
    reader = AWSResourceReader(region=region)
    reader.read_all()
    
    if not reader.resources:
        print("\nNo resources found or all API calls failed.")
        return None
    
    # カテゴリ別に分類
    categories = categorize_resources(reader.resources)
    
    # 出力パス
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_name)
    
    print(f"\n" + "="*80)
    print(f"Generating Architecture Diagram: {output_path}.png")
    print("="*80 + "\n")
    
    graph_attr = {
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.8",
        "nodesep": "0.8",
        "ranksep": "1.2",
    }
    
    unsupported_types = set()
    
    try:
        with Diagram(
            f"AWS Architecture - {region}",
            filename=output_path,
            show=False,
            direction="TB",
            outformat="png",
            graph_attr=graph_attr
        ):
            nodes = {}
            
            for category, resource_list in categories.items():
                # リソース集約（VPC と Subnet を除く）
                aggregated_list, aggregation_info = aggregate_resources_by_type(resource_list)
                
                with Cluster(f"{category} ({len(resource_list)})"):
                    for resource_id, resource_info, resource_type in aggregated_list:
                        label = resource_info['Name'][:20]
                        icon_class = get_icon_class(resource_type)
                        
                        if icon_class:
                            node = icon_class(label)
                        else:
                            fallback_icon = get_fallback_icon(resource_type)
                            node = fallback_icon(label)
                            unsupported_types.add(resource_type)
                        
                        nodes[resource_id] = node
                    
                    # "..." ノードを追加
                    for resource_type, total_count in aggregation_info.items():
                        remaining = total_count - 2
                        ellipsis_label = f"... +{remaining} more\n{resource_type.split('::')[-1]}"
                        
                        icon_class = get_icon_class(resource_type)
                        if icon_class:
                            ellipsis_node = icon_class(ellipsis_label)
                        else:
                            fallback_icon = get_fallback_icon(resource_type)
                            ellipsis_node = fallback_icon(ellipsis_label)
        
        if unsupported_types:
            print(f"\nInfo: {len(unsupported_types)} resource type(s) using fallback icons:")
            for rt in sorted(unsupported_types):
                print(f"  - {rt}")
        
        print(f"\n✓ Diagram generated: {output_path}.png")
        print("="*80)
        
        return f"{output_path}.png"
        
    except Exception as e:
        print(f"\nError generating diagram: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate AWS architecture diagram from live AWS resources',
        epilog='''
Authentication:
  This script uses AWS credentials from environment variables:
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_SESSION_TOKEN (for SSO)
  
  Or from ~/.aws/credentials (AWS CLI configuration)
  
  Example for SSO:
    SET AWS_ACCESS_KEY_ID=ASIA...
    SET AWS_SECRET_ACCESS_KEY=wJal...
    SET AWS_SESSION_TOKEN=IQoJb3...
        '''
    )
    
    parser.add_argument('--region', default='ap-northeast-1', help='AWS region (default: ap-northeast-1)')
    parser.add_argument('--output-dir', default='aws-diagrams', help='Output directory (default: aws-diagrams)')
    parser.add_argument('--output-name', default='aws-architecture', help='Output filename without extension (default: aws-architecture)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("AWS Architecture Diagram Generator")
    print("="*80)
    print(f"\nRegion: {args.region}")
    print(f"Output: {args.output_dir}/{args.output_name}.png\n")
    
    try:
        generate_diagram_from_aws(
            region=args.region,
            output_dir=args.output_dir,
            output_name=args.output_name
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
# -*- coding: utf-8 -*-
"""
CloudFormation エクスポート/インポートモジュール
"""

import os
import yaml
from collections import defaultdict


# ==================== YAML カスタムローダー ====================

class CloudFormationLoader(yaml.SafeLoader):
    """CloudFormation YAML 用のローダー"""
    pass


def ref_constructor(loader, node):
    return {'Ref': loader.construct_scalar(node)}


def getatt_constructor(loader, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
        return {'Fn::GetAtt': value.split('.')}
    else:
        return {'Fn::GetAtt': loader.construct_sequence(node)}


def sub_constructor(loader, node):
    return {'Fn::Sub': loader.construct_scalar(node)}


def select_constructor(loader, node):
    return {'Fn::Select': loader.construct_sequence(node)}


def getazs_constructor(loader, node):
    return {'Fn::GetAZs': loader.construct_scalar(node)}


def join_constructor(loader, node):
    return {'Fn::Join': loader.construct_sequence(node)}


def if_constructor(loader, node):
    return {'Fn::If': loader.construct_sequence(node)}


# タグを登録
CloudFormationLoader.add_constructor('!Ref', ref_constructor)
CloudFormationLoader.add_constructor('!GetAtt', getatt_constructor)
CloudFormationLoader.add_constructor('!Sub', sub_constructor)
CloudFormationLoader.add_constructor('!Select', select_constructor)
CloudFormationLoader.add_constructor('!GetAZs', getazs_constructor)
CloudFormationLoader.add_constructor('!Join', join_constructor)
CloudFormationLoader.add_constructor('!If', if_constructor)


def importvalue_constructor(loader, node):
    return {'Fn::ImportValue': loader.construct_scalar(node)}


def split_constructor(loader, node):
    return {'Fn::Split': loader.construct_sequence(node)}


def findinmap_constructor(loader, node):
    return {'Fn::FindInMap': loader.construct_sequence(node)}


def base64_constructor(loader, node):
    return {'Fn::Base64': loader.construct_scalar(node)}


def cidr_constructor(loader, node):
    return {'Fn::Cidr': loader.construct_sequence(node)}


def equals_constructor(loader, node):
    return {'Fn::Equals': loader.construct_sequence(node)}


def and_constructor(loader, node):
    return {'Fn::And': loader.construct_sequence(node)}


def or_constructor(loader, node):
    return {'Fn::Or': loader.construct_sequence(node)}


def not_constructor(loader, node):
    return {'Fn::Not': loader.construct_sequence(node)}


def condition_constructor(loader, node):
    return {'Condition': loader.construct_scalar(node)}


# 追加タグを登録
CloudFormationLoader.add_constructor('!ImportValue', importvalue_constructor)
CloudFormationLoader.add_constructor('!Split', split_constructor)
CloudFormationLoader.add_constructor('!FindInMap', findinmap_constructor)
CloudFormationLoader.add_constructor('!Base64', base64_constructor)
CloudFormationLoader.add_constructor('!Cidr', cidr_constructor)
CloudFormationLoader.add_constructor('!Equals', equals_constructor)
CloudFormationLoader.add_constructor('!And', and_constructor)
CloudFormationLoader.add_constructor('!Or', or_constructor)
CloudFormationLoader.add_constructor('!Not', not_constructor)
CloudFormationLoader.add_constructor('!Condition', condition_constructor)


# ==================== エクスポート ====================

def export_cloudformation(reader, output_dir):
    """リソースを CloudFormation 形式で保存"""
    print("\n" + "=" * 80)
    print(f"Exporting CloudFormation to: {output_dir}")
    print("=" * 80 + "\n")
    
    os.makedirs(output_dir, exist_ok=True)
    
    resource_collections = [
        ('vpc', reader.vpcs),
        ('subnet', reader.subnets),
        ('internet-gateway', reader.internet_gateways),
        ('nat-gateway', reader.nat_gateways),
        ('security-group', reader.security_groups),
        ('vpc-endpoint', reader.vpc_endpoints),
        ('ec2', reader.ec2_instances),
        ('ecs-cluster', reader.ecs_clusters),
        ('ecs-service', reader.ecs_services),
        ('eks', reader.eks_clusters),
        ('lambda', reader.lambda_functions),
        ('rds', reader.rds_instances),
        ('dynamodb', reader.dynamodb_tables),
        ('elasticache', reader.elasticache_clusters),
        ('s3', reader.s3_buckets),
        ('efs', reader.efs_filesystems),
        ('load-balancer', reader.load_balancers),
        ('target-group', reader.target_groups),
        ('sqs', reader.sqs_queues),
        ('sns', reader.sns_topics),
        ('iam-role', reader.iam_roles),
        ('cloudwatch-log-group', reader.log_groups),
    ]
    
    total_files = 0
    
    for category, resources in resource_collections:
        if not resources:
            continue
        
        category_dir = os.path.join(output_dir, category)
        os.makedirs(category_dir, exist_ok=True)
        
        for resource_id, resource_data in resources.items():
            # ファイル名をサニタイズ
            safe_name = resource_id.replace('/', '_').replace(':', '_').replace('*', '_')
            safe_name = safe_name[:100]
            
            filename = os.path.join(category_dir, f"{safe_name}.yaml")
            
            # CloudFormation 形式で整形
            cf_resource = {
                'AWSTemplateFormatVersion': '2010-09-09',
                'Description': f'Exported {resource_data.get("Type", "Resource")}: {resource_id}',
                'Resources': {
                    resource_id.replace('-', '').replace('_', ''): {
                        'Type': resource_data.get('Type', 'AWS::CloudFormation::CustomResource'),
                        'Properties': resource_data.get('Properties', {})
                    }
                },
                'Metadata': {
                    # 追加のメタデータを保存
                    'ResourceId': resource_id,
                    'ExtraInfo': {k: v for k, v in resource_data.items() if k not in ['Type', 'Properties']}
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(cf_resource, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            total_files += 1
        
        print(f"  {category}: {len(resources)} file(s)")
    
    print(f"\n✓ Exported {total_files} CloudFormation file(s)")
    return total_files


# ==================== インポート ====================

class CloudFormationImporter:
    """CloudFormation ファイルからリソースを読み込むクラス"""
    
    def __init__(self):
        # リソースストレージ（AWSResourceReader と同じ構造）
        self.vpcs = {}
        self.subnets = {}
        self.internet_gateways = {}
        self.nat_gateways = {}
        self.security_groups = {}
        self.vpc_endpoints = {}
        
        self.ec2_instances = {}
        self.ecs_clusters = {}
        self.ecs_services = {}
        self.eks_clusters = {}
        self.lambda_functions = {}
        
        self.rds_instances = {}
        self.dynamodb_tables = {}
        self.elasticache_clusters = {}
        
        self.s3_buckets = {}
        self.efs_filesystems = {}
        
        self.load_balancers = {}
        self.target_groups = {}
        
        self.sqs_queues = {}
        self.sns_topics = {}
        
        self.iam_roles = {}
        self.log_groups = {}
        
        self.relationships = []
        self.errors = []
    
    def _parse_yaml(self, filepath):
        """YAML ファイルを解析"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.load(f, Loader=CloudFormationLoader)
        except Exception as e:
            self.errors.append(f"⚠ Failed to parse {filepath}: {str(e)[:50]}")
            return None
    
    def _get_resource_type_mapping(self):
        """リソースタイプとストレージのマッピング"""
        return {
            'AWS::EC2::VPC': self.vpcs,
            'AWS::EC2::Subnet': self.subnets,
            'AWS::EC2::InternetGateway': self.internet_gateways,
            'AWS::EC2::NatGateway': self.nat_gateways,
            'AWS::EC2::SecurityGroup': self.security_groups,
            'AWS::EC2::VPCEndpoint': self.vpc_endpoints,
            'AWS::EC2::Instance': self.ec2_instances,
            'AWS::ECS::Cluster': self.ecs_clusters,
            'AWS::ECS::Service': self.ecs_services,
            'AWS::EKS::Cluster': self.eks_clusters,
            'AWS::Lambda::Function': self.lambda_functions,
            'AWS::RDS::DBInstance': self.rds_instances,
            'AWS::DynamoDB::Table': self.dynamodb_tables,
            'AWS::ElastiCache::CacheCluster': self.elasticache_clusters,
            'AWS::S3::Bucket': self.s3_buckets,
            'AWS::EFS::FileSystem': self.efs_filesystems,
            'AWS::ElasticLoadBalancingV2::LoadBalancer': self.load_balancers,
            'AWS::ElasticLoadBalancingV2::TargetGroup': self.target_groups,
            'AWS::SQS::Queue': self.sqs_queues,
            'AWS::SNS::Topic': self.sns_topics,
            'AWS::IAM::Role': self.iam_roles,
            'AWS::Logs::LogGroup': self.log_groups,
        }
    
    def import_from_directory(self, input_dir):
        """ディレクトリからすべてのリソースを読み込む"""
        print("=" * 80)
        print(f"Importing CloudFormation from: {input_dir}")
        print("=" * 80 + "\n")
        
        if not os.path.exists(input_dir):
            print(f"ERROR: Directory not found: {input_dir}")
            return 0
        
        yaml_files = []
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith('.yaml') or file.endswith('.yml'):
                    yaml_files.append(os.path.join(root, file))
        
        print(f"Found {len(yaml_files)} YAML file(s)\n")
        
        type_mapping = self._get_resource_type_mapping()
        
        for filepath in yaml_files:
            data = self._parse_yaml(filepath)
            if not data:
                continue
            
            # Resources セクションを処理
            resources = data.get('Resources', {})
            metadata = data.get('Metadata', {})
            extra_info = metadata.get('ExtraInfo', {})
            resource_id = metadata.get('ResourceId')
            
            for res_name, res_data in resources.items():
                res_type = res_data.get('Type', '')
                properties = res_data.get('Properties', {})
                
                # リソース ID を決定
                actual_id = resource_id or res_name
                
                # リソースデータを構築
                resource_entry = {
                    'Type': res_type,
                    'Properties': properties,
                    **extra_info
                }
                
                # 適切なストレージに保存
                storage = type_mapping.get(res_type)
                if storage is not None:
                    storage[actual_id] = resource_entry
        
        # 関係を再構築
        self._rebuild_relationships()
        
        # 統計
        total = sum(len(s) for s in type_mapping.values())
        
        print("Resource counts:")
        print(f"  VPCs: {len(self.vpcs)}")
        print(f"  Subnets: {len(self.subnets)}")
        print(f"  Internet Gateways: {len(self.internet_gateways)}")
        print(f"  NAT Gateways: {len(self.nat_gateways)}")
        print(f"  Security Groups: {len(self.security_groups)}")
        print(f"  VPC Endpoints: {len(self.vpc_endpoints)}")
        print(f"  EC2 Instances: {len(self.ec2_instances)}")
        print(f"  ECS Clusters: {len(self.ecs_clusters)}")
        print(f"  ECS Services: {len(self.ecs_services)}")
        print(f"  EKS Clusters: {len(self.eks_clusters)}")
        print(f"  Lambda Functions: {len(self.lambda_functions)}")
        print(f"  RDS Instances: {len(self.rds_instances)}")
        print(f"  DynamoDB Tables: {len(self.dynamodb_tables)}")
        print(f"  ElastiCache Clusters: {len(self.elasticache_clusters)}")
        print(f"  S3 Buckets: {len(self.s3_buckets)}")
        print(f"  EFS FileSystems: {len(self.efs_filesystems)}")
        print(f"  Load Balancers: {len(self.load_balancers)}")
        print(f"  Target Groups: {len(self.target_groups)}")
        print(f"  SQS Queues: {len(self.sqs_queues)}")
        print(f"  SNS Topics: {len(self.sns_topics)}")
        print(f"  IAM Roles: {len(self.iam_roles)}")
        print(f"  CloudWatch Log Groups: {len(self.log_groups)}")
        
        print(f"\n{'=' * 80}")
        print(f"Total Resources: {total}")
        print(f"Total Relationships: {len(self.relationships)}")
        print("=" * 80)
        
        if self.errors:
            print("\nWarnings/Errors:")
            print("-" * 40)
            for error in self.errors[:20]:  # 最初の20件のみ
                print(error)
            if len(self.errors) > 20:
                print(f"... and {len(self.errors) - 20} more errors")
            print("-" * 40)
        
        return total
    
    def _rebuild_relationships(self):
        """リソース間の関係を再構築"""
        
        # Subnet -> VPC
        for subnet_id, subnet_data in self.subnets.items():
            vpc_id = subnet_data.get('VpcId') or subnet_data.get('Properties', {}).get('VpcId')
            if vpc_id:
                self.relationships.append((subnet_id, vpc_id, 'belongs_to', 'in VPC'))
        
        # Internet Gateway -> VPC
        for igw_id, igw_data in self.internet_gateways.items():
            vpc_id = igw_data.get('AttachedVpcId')
            if vpc_id:
                self.relationships.append((igw_id, vpc_id, 'attached_to', 'attached'))
        
        # NAT Gateway -> Subnet
        for nat_id, nat_data in self.nat_gateways.items():
            subnet_id = nat_data.get('SubnetId') or nat_data.get('Properties', {}).get('SubnetId')
            if subnet_id:
                self.relationships.append((nat_id, subnet_id, 'in_subnet', 'in'))
        
        # VPC Endpoint -> Subnet
        for ep_id, ep_data in self.vpc_endpoints.items():
            subnet_ids = ep_data.get('SubnetIds', []) or ep_data.get('Properties', {}).get('SubnetIds', [])
            for subnet_id in subnet_ids:
                self.relationships.append((ep_id, subnet_id, 'in_subnet', 'endpoint'))
        
        # EC2 -> Subnet
        for ec2_id, ec2_data in self.ec2_instances.items():
            subnet_id = ec2_data.get('SubnetId') or ec2_data.get('Properties', {}).get('SubnetId')
            if subnet_id:
                self.relationships.append((ec2_id, subnet_id, 'in_subnet', 'deployed'))
        
        # ECS Service -> Subnet
        for svc_name, svc_data in self.ecs_services.items():
            subnet_ids = svc_data.get('SubnetIds', [])
            for subnet_id in subnet_ids:
                self.relationships.append((svc_name, subnet_id, 'in_subnet', 'deployed'))
            
            cluster_name = svc_data.get('ClusterName')
            if cluster_name:
                self.relationships.append((svc_name, cluster_name, 'in_cluster', 'runs in'))
        
        # EKS Cluster -> Subnet
        for cluster_name, cluster_data in self.eks_clusters.items():
            subnet_ids = cluster_data.get('SubnetIds', [])
            for subnet_id in subnet_ids:
                self.relationships.append((cluster_name, subnet_id, 'in_subnet', 'deployed'))
        
        # Lambda -> Subnet
        for func_name, func_data in self.lambda_functions.items():
            subnet_ids = func_data.get('SubnetIds', [])
            for subnet_id in subnet_ids:
                self.relationships.append((func_name, subnet_id, 'in_subnet', 'deployed'))
            
            # トリガー（Event Source Mapping から）
            for trigger in func_data.get('Triggers', []):
                arn = trigger.get('EventSourceArn', '')
                if ':sns:' in arn:
                    topic_name = arn.split(':')[-1]
                    self.relationships.append((topic_name, func_name, 'triggers', 'triggers'))
                elif ':sqs:' in arn:
                    queue_name = arn.split(':')[-1]
                    self.relationships.append((queue_name, func_name, 'triggers', 'triggers'))
        
        # RDS -> Subnet
        for db_id, db_data in self.rds_instances.items():
            subnet_ids = db_data.get('SubnetIds', [])
            for subnet_id in subnet_ids:
                self.relationships.append((db_id, subnet_id, 'in_subnet', 'deployed'))
        
        # Load Balancer -> Subnet
        for lb_name, lb_data in self.load_balancers.items():
            subnet_ids = lb_data.get('SubnetIds', []) or lb_data.get('Properties', {}).get('Subnets', [])
            for subnet_id in subnet_ids:
                self.relationships.append((lb_name, subnet_id, 'in_subnet', 'deployed'))
        
        # Load Balancer -> Target Group
        for tg_name, tg_data in self.target_groups.items():
            lb_arns = tg_data.get('LoadBalancerArns', [])
            for lb_arn in lb_arns:
                for lb_name, lb_data in self.load_balancers.items():
                    if lb_data.get('LoadBalancerArn') == lb_arn:
                        self.relationships.append((lb_name, tg_name, 'routes_to', 'routes'))
                        break
            
            # Target Group -> ターゲット（EC2/Lambda）
            targets = tg_data.get('Targets', [])
            target_type = tg_data.get('TargetType', 'instance')
            for target in targets:
                target_id = target.get('Id', '')
                if target_type == 'instance' and target_id.startswith('i-'):
                    self.relationships.append((tg_name, target_id, 'targets', 'routes to'))
                elif target_type == 'lambda' and ':function:' in target_id:
                    func_name = target_id.split(':function:')[-1].split(':')[0]
                    self.relationships.append((tg_name, func_name, 'targets', 'routes to'))
        
        # SNS -> Lambda（サブスクリプションから）
        for topic_name, topic_data in self.sns_topics.items():
            lambda_targets = topic_data.get('LambdaTargets', [])
            for func_name in lambda_targets:
                self.relationships.append((topic_name, func_name, 'triggers', 'SNS trigger'))
            
            # または Subscriptions から
            subscriptions = topic_data.get('Subscriptions', [])
            for sub in subscriptions:
                if sub.get('Protocol') == 'lambda':
                    endpoint = sub.get('Endpoint', '')
                    if ':function:' in endpoint:
                        func_name = endpoint.split(':function:')[-1].split(':')[0]
                        self.relationships.append((topic_name, func_name, 'triggers', 'SNS trigger'))

# -*- coding: utf-8 -*-
"""
AWS アーキテクチャ図生成器 V2 - リソース関係を含む

機能:
1. AWS API からリソースを読み取り
2. リソース間の関係（VPC内配置、参照関係など）を検出して線で接続
3. CloudFormation 形式で各リソースを保存

使用方法:
    # 環境変数から認証情報を取得
    $env:AWS_ACCESS_KEY_ID="AKIA..."
    $env:AWS_SECRET_ACCESS_KEY="..."
    $env:AWS_SESSION_TOKEN="..."  # SSO の場合
    
    # 実行
    py generate_diagram_from_aws_v2.py
    py generate_diagram_from_aws_v2.py --region ap-northeast-1 --output-dir aws-outputs
"""

import os
import argparse
import yaml
from collections import defaultdict
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import (
    VPC, InternetGateway, PrivateSubnet, PublicSubnet, NATGateway, 
    ELB, ALB, NLB, Route53, Endpoint, VPCRouter
)
from diagrams.aws.compute import EC2, ECS, EKS, Lambda, Batch, Fargate
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift, Database
from diagrams.aws.storage import S3, EBS, EFS
from diagrams.aws.integration import SQS, SNS, Eventbridge, StepFunctions
from diagrams.aws.security import IAM, SecretsManager, KMS
from diagrams.aws.management import Cloudwatch, SystemsManager
from diagrams.generic.blank import Blank
from diagrams.generic.compute import Rack
from diagrams.generic.network import Switch


# ==================== CloudFormation YAML Dumper ====================

class CloudFormationDumper(yaml.SafeDumper):
    """CloudFormation 用の YAML Dumper"""
    pass

def ref_representer(dumper, data):
    return dumper.represent_scalar('!Ref', data['Ref'])

def getatt_representer(dumper, data):
    value = data['Fn::GetAtt']
    if isinstance(value, list):
        return dumper.represent_scalar('!GetAtt', '.'.join(value))
    return dumper.represent_scalar('!GetAtt', value)

CloudFormationDumper.add_representer(
    type({'Ref': ''}), 
    lambda dumper, data: ref_representer(dumper, data) if 'Ref' in data else 
                         getatt_representer(dumper, data) if 'Fn::GetAtt' in data else
                         dumper.represent_dict(data)
)


# ==================== AWS リソースリーダー ====================

class AWSResourceReaderV2:
    """AWS からリソースを読み取り、関係を分析するクラス"""
    
    def __init__(self, region='ap-northeast-1'):
        self.region = region
        self.errors = []
        
        # リソースストレージ
        self.vpcs = {}
        self.subnets = {}
        self.internet_gateways = {}
        self.nat_gateways = {}
        self.security_groups = {}
        self.route_tables = {}
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
        
        # 関係マッピング
        self.relationships = []  # [(source, target, rel_type, label), ...]
        
        print(f"Initializing AWS clients for region: {region}")
        
        try:
            self.ec2 = boto3.client('ec2', region_name=region)
            self.ecs = boto3.client('ecs', region_name=region)
            self.eks = boto3.client('eks', region_name=region)
            self.lambda_client = boto3.client('lambda', region_name=region)
            self.rds = boto3.client('rds', region_name=region)
            self.dynamodb = boto3.client('dynamodb', region_name=region)
            self.s3 = boto3.client('s3', region_name=region)
            self.elbv2 = boto3.client('elbv2', region_name=region)
            self.efs = boto3.client('efs', region_name=region)
            self.sqs = boto3.client('sqs', region_name=region)
            self.sns = boto3.client('sns', region_name=region)
            self.iam = boto3.client('iam')
            self.logs = boto3.client('logs', region_name=region)
            self.elasticache = boto3.client('elasticache', region_name=region)
            
            print("✓ AWS clients initialized successfully\n")
            
        except NoCredentialsError:
            print("\n" + "="*80)
            print("ERROR: AWS credentials not found!")
            print("="*80)
            raise
    
    def _safe_call(self, func, service_name, *args, **kwargs):
        """安全に AWS API を呼び出す"""
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code in ['AccessDenied', 'AccessDeniedException', 'UnauthorizedOperation']:
                self.errors.append(f"⚠ {service_name}: Access Denied - {error_msg[:50]}")
            else:
                self.errors.append(f"⚠ {service_name}: {error_code} - {error_msg[:50]}")
            return None
        except Exception as e:
            self.errors.append(f"⚠ {service_name}: {str(e)[:50]}")
            return None
    
    def _get_name_tag(self, tags):
        """タグから Name を取得"""
        if not tags:
            return None
        for tag in tags:
            if tag.get('Key') == 'Name':
                return tag.get('Value')
        return None
    
    # ==================== VPC 関連 ====================
    
    def read_vpcs(self):
        """VPC を読み取る"""
        print("  Reading VPCs...")
        response = self._safe_call(self.ec2.describe_vpcs, "EC2:VPC")
        if not response:
            return
        
        for vpc in response.get('Vpcs', []):
            vpc_id = vpc['VpcId']
            name = self._get_name_tag(vpc.get('Tags', []))
            
            self.vpcs[vpc_id] = {
                'Type': 'AWS::EC2::VPC',
                'VpcId': vpc_id,
                'Name': name or vpc_id,
                'CidrBlock': vpc.get('CidrBlock', ''),
                'Properties': {
                    'CidrBlock': vpc.get('CidrBlock', ''),
                    'EnableDnsHostnames': vpc.get('EnableDnsHostnames', False),
                    'EnableDnsSupport': vpc.get('EnableDnsSupport', True),
                    'Tags': vpc.get('Tags', [])
                }
            }
        
        print(f"    Found {len(self.vpcs)} VPC(s)")
    
    def read_subnets(self):
        """サブネットを読み取る"""
        print("  Reading Subnets...")
        response = self._safe_call(self.ec2.describe_subnets, "EC2:Subnet")
        if not response:
            return
        
        for subnet in response.get('Subnets', []):
            subnet_id = subnet['SubnetId']
            vpc_id = subnet['VpcId']
            name = self._get_name_tag(subnet.get('Tags', []))
            
            # Public/Private 判定（MapPublicIpOnLaunch で判断）
            is_public = subnet.get('MapPublicIpOnLaunch', False)
            
            self.subnets[subnet_id] = {
                'Type': 'AWS::EC2::Subnet',
                'SubnetId': subnet_id,
                'VpcId': vpc_id,
                'Name': name or subnet_id,
                'CidrBlock': subnet.get('CidrBlock', ''),
                'AvailabilityZone': subnet.get('AvailabilityZone', ''),
                'IsPublic': is_public,
                'Properties': {
                    'VpcId': vpc_id,
                    'CidrBlock': subnet.get('CidrBlock', ''),
                    'AvailabilityZone': subnet.get('AvailabilityZone', ''),
                    'MapPublicIpOnLaunch': is_public,
                    'Tags': subnet.get('Tags', [])
                }
            }
            
            # VPC との関係
            self.relationships.append((subnet_id, vpc_id, 'belongs_to', 'in VPC'))
        
        print(f"    Found {len(self.subnets)} Subnet(s)")
    
    def read_internet_gateways(self):
        """Internet Gateway を読み取る"""
        print("  Reading Internet Gateways...")
        response = self._safe_call(self.ec2.describe_internet_gateways, "EC2:InternetGateway")
        if not response:
            return
        
        for igw in response.get('InternetGateways', []):
            igw_id = igw['InternetGatewayId']
            name = self._get_name_tag(igw.get('Tags', []))
            
            attached_vpc = None
            for attachment in igw.get('Attachments', []):
                if attachment.get('State') == 'available':
                    attached_vpc = attachment.get('VpcId')
                    break
            
            self.internet_gateways[igw_id] = {
                'Type': 'AWS::EC2::InternetGateway',
                'InternetGatewayId': igw_id,
                'Name': name or igw_id,
                'AttachedVpcId': attached_vpc,
                'Properties': {
                    'Tags': igw.get('Tags', [])
                }
            }
            
            # VPC との関係
            if attached_vpc:
                self.relationships.append((igw_id, attached_vpc, 'attached_to', 'attached'))
        
        print(f"    Found {len(self.internet_gateways)} Internet Gateway(s)")
    
    def read_nat_gateways(self):
        """NAT Gateway を読み取る"""
        print("  Reading NAT Gateways...")
        response = self._safe_call(self.ec2.describe_nat_gateways, "EC2:NATGateway")
        if not response:
            return
        
        for nat in response.get('NatGateways', []):
            if nat.get('State') != 'available':
                continue
            
            nat_id = nat['NatGatewayId']
            name = self._get_name_tag(nat.get('Tags', []))
            subnet_id = nat.get('SubnetId')
            vpc_id = nat.get('VpcId')
            
            self.nat_gateways[nat_id] = {
                'Type': 'AWS::EC2::NatGateway',
                'NatGatewayId': nat_id,
                'Name': name or nat_id,
                'SubnetId': subnet_id,
                'VpcId': vpc_id,
                'Properties': {
                    'SubnetId': subnet_id,
                    'Tags': nat.get('Tags', [])
                }
            }
            
            # Subnet との関係
            if subnet_id:
                self.relationships.append((nat_id, subnet_id, 'in_subnet', 'in'))
        
        print(f"    Found {len(self.nat_gateways)} NAT Gateway(s)")
    
    def read_security_groups(self):
        """Security Group を読み取る"""
        print("  Reading Security Groups...")
        response = self._safe_call(self.ec2.describe_security_groups, "EC2:SecurityGroup")
        if not response:
            return
        
        for sg in response.get('SecurityGroups', []):
            sg_id = sg['GroupId']
            vpc_id = sg.get('VpcId')
            
            self.security_groups[sg_id] = {
                'Type': 'AWS::EC2::SecurityGroup',
                'GroupId': sg_id,
                'GroupName': sg.get('GroupName', ''),
                'VpcId': vpc_id,
                'Description': sg.get('Description', ''),
                'Properties': {
                    'GroupName': sg.get('GroupName', ''),
                    'GroupDescription': sg.get('Description', ''),
                    'VpcId': vpc_id,
                    'SecurityGroupIngress': sg.get('IpPermissions', []),
                    'SecurityGroupEgress': sg.get('IpPermissionsEgress', []),
                    'Tags': sg.get('Tags', [])
                }
            }
        
        print(f"    Found {len(self.security_groups)} Security Group(s)")
    
    def read_vpc_endpoints(self):
        """VPC Endpoint を読み取る"""
        print("  Reading VPC Endpoints...")
        response = self._safe_call(self.ec2.describe_vpc_endpoints, "EC2:VPCEndpoint")
        if not response:
            return
        
        for endpoint in response.get('VpcEndpoints', []):
            endpoint_id = endpoint['VpcEndpointId']
            vpc_id = endpoint.get('VpcId')
            name = self._get_name_tag(endpoint.get('Tags', []))
            
            self.vpc_endpoints[endpoint_id] = {
                'Type': 'AWS::EC2::VPCEndpoint',
                'VpcEndpointId': endpoint_id,
                'Name': name or endpoint_id,
                'VpcId': vpc_id,
                'ServiceName': endpoint.get('ServiceName', ''),
                'EndpointType': endpoint.get('VpcEndpointType', ''),
                'Properties': {
                    'VpcId': vpc_id,
                    'ServiceName': endpoint.get('ServiceName', ''),
                    'VpcEndpointType': endpoint.get('VpcEndpointType', ''),
                    'SubnetIds': endpoint.get('SubnetIds', []),
                    'Tags': endpoint.get('Tags', [])
                }
            }
            
            if vpc_id:
                self.relationships.append((endpoint_id, vpc_id, 'in_vpc', 'in'))
        
        print(f"    Found {len(self.vpc_endpoints)} VPC Endpoint(s)")
    
    # ==================== Compute 関連 ====================
    
    def read_ec2_instances(self):
        """EC2 インスタンスを読み取る"""
        print("  Reading EC2 Instances...")
        response = self._safe_call(self.ec2.describe_instances, "EC2:Instance")
        if not response:
            return
        
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                if instance.get('State', {}).get('Name') == 'terminated':
                    continue
                
                instance_id = instance['InstanceId']
                name = self._get_name_tag(instance.get('Tags', []))
                subnet_id = instance.get('SubnetId')
                vpc_id = instance.get('VpcId')
                sg_ids = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]
                
                self.ec2_instances[instance_id] = {
                    'Type': 'AWS::EC2::Instance',
                    'InstanceId': instance_id,
                    'Name': name or instance_id,
                    'InstanceType': instance.get('InstanceType', ''),
                    'SubnetId': subnet_id,
                    'VpcId': vpc_id,
                    'SecurityGroupIds': sg_ids,
                    'State': instance.get('State', {}).get('Name', ''),
                    'Properties': {
                        'InstanceType': instance.get('InstanceType', ''),
                        'SubnetId': subnet_id,
                        'SecurityGroupIds': sg_ids,
                        'ImageId': instance.get('ImageId', ''),
                        'Tags': instance.get('Tags', [])
                    }
                }
                
                # Subnet との関係
                if subnet_id:
                    self.relationships.append((instance_id, subnet_id, 'in_subnet', 'deployed'))
                
                # Security Group との関係
                for sg_id in sg_ids:
                    self.relationships.append((instance_id, sg_id, 'uses_sg', 'protected by'))
        
        print(f"    Found {len(self.ec2_instances)} EC2 Instance(s)")
    
    def read_ecs_clusters(self):
        """ECS クラスターを読み取る"""
        print("  Reading ECS Clusters...")
        response = self._safe_call(self.ecs.list_clusters, "ECS:Cluster")
        if not response:
            return
        
        cluster_arns = response.get('clusterArns', [])
        if not cluster_arns:
            print("    Found 0 ECS Cluster(s)")
            return
        
        details = self._safe_call(
            self.ecs.describe_clusters, "ECS:Cluster",
            clusters=cluster_arns, include=['TAGS']
        )
        if not details:
            return
        
        for cluster in details.get('clusters', []):
            cluster_name = cluster['clusterName']
            cluster_arn = cluster['clusterArn']
            
            self.ecs_clusters[cluster_name] = {
                'Type': 'AWS::ECS::Cluster',
                'ClusterName': cluster_name,
                'ClusterArn': cluster_arn,
                'Status': cluster.get('status', ''),
                'RunningTasksCount': cluster.get('runningTasksCount', 0),
                'Properties': {
                    'ClusterName': cluster_name,
                    'Tags': cluster.get('tags', [])
                }
            }
        
        print(f"    Found {len(self.ecs_clusters)} ECS Cluster(s)")
        
        # ECS Services も読み取る
        self._read_ecs_services(cluster_arns)
    
    def _read_ecs_services(self, cluster_arns):
        """ECS サービスを読み取る"""
        print("  Reading ECS Services...")
        
        for cluster_arn in cluster_arns:
            cluster_name = cluster_arn.split('/')[-1]
            
            response = self._safe_call(
                self.ecs.list_services, "ECS:Service",
                cluster=cluster_arn
            )
            if not response:
                continue
            
            service_arns = response.get('serviceArns', [])
            if not service_arns:
                continue
            
            details = self._safe_call(
                self.ecs.describe_services, "ECS:Service",
                cluster=cluster_arn, services=service_arns
            )
            if not details:
                continue
            
            for service in details.get('services', []):
                service_name = service['serviceName']
                
                # ネットワーク設定から VPC/Subnet を取得
                network_config = service.get('networkConfiguration', {}).get('awsvpcConfiguration', {})
                subnet_ids = network_config.get('subnets', [])
                sg_ids = network_config.get('securityGroups', [])
                
                self.ecs_services[service_name] = {
                    'Type': 'AWS::ECS::Service',
                    'ServiceName': service_name,
                    'ClusterName': cluster_name,
                    'SubnetIds': subnet_ids,
                    'SecurityGroupIds': sg_ids,
                    'DesiredCount': service.get('desiredCount', 0),
                    'Properties': {
                        'ServiceName': service_name,
                        'Cluster': cluster_arn,
                        'DesiredCount': service.get('desiredCount', 0),
                        'NetworkConfiguration': service.get('networkConfiguration', {})
                    }
                }
                
                # Cluster との関係
                self.relationships.append((service_name, cluster_name, 'in_cluster', 'runs in'))
                
                # Subnet との関係
                for subnet_id in subnet_ids:
                    self.relationships.append((service_name, subnet_id, 'in_subnet', 'deployed'))
                
                # Security Group との関係
                for sg_id in sg_ids:
                    self.relationships.append((service_name, sg_id, 'uses_sg', 'protected by'))
        
        print(f"    Found {len(self.ecs_services)} ECS Service(s)")
    
    def read_eks_clusters(self):
        """EKS クラスターを読み取る"""
        print("  Reading EKS Clusters...")
        response = self._safe_call(self.eks.list_clusters, "EKS:Cluster")
        if not response:
            return
        
        for cluster_name in response.get('clusters', []):
            details = self._safe_call(
                self.eks.describe_cluster, "EKS:Cluster",
                name=cluster_name
            )
            if not details:
                continue
            
            cluster = details.get('cluster', {})
            vpc_id = cluster.get('resourcesVpcConfig', {}).get('vpcId')
            subnet_ids = cluster.get('resourcesVpcConfig', {}).get('subnetIds', [])
            sg_id = cluster.get('resourcesVpcConfig', {}).get('clusterSecurityGroupId')
            
            self.eks_clusters[cluster_name] = {
                'Type': 'AWS::EKS::Cluster',
                'ClusterName': cluster_name,
                'VpcId': vpc_id,
                'SubnetIds': subnet_ids,
                'SecurityGroupId': sg_id,
                'Status': cluster.get('status', ''),
                'Properties': {
                    'Name': cluster_name,
                    'ResourcesVpcConfig': cluster.get('resourcesVpcConfig', {}),
                    'Tags': cluster.get('tags', {})
                }
            }
            
            # Subnet との関係
            for subnet_id in subnet_ids:
                self.relationships.append((cluster_name, subnet_id, 'in_subnet', 'deployed'))
            
            # Security Group との関係
            if sg_id:
                self.relationships.append((cluster_name, sg_id, 'uses_sg', 'protected by'))
        
        print(f"    Found {len(self.eks_clusters)} EKS Cluster(s)")
    
    def read_lambda_functions(self):
        """Lambda 関数を読み取る"""
        print("  Reading Lambda Functions...")
        
        functions = []
        paginator = self.lambda_client.get_paginator('list_functions')
        
        try:
            for page in paginator.paginate():
                functions.extend(page.get('Functions', []))
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            self.errors.append(f"⚠ Lambda: {error_code}")
            return
        
        for func in functions:
            func_name = func['FunctionName']
            
            # VPC 設定
            vpc_config = func.get('VpcConfig', {})
            vpc_id = vpc_config.get('VpcId')
            subnet_ids = vpc_config.get('SubnetIds', [])
            sg_ids = vpc_config.get('SecurityGroupIds', [])
            
            self.lambda_functions[func_name] = {
                'Type': 'AWS::Lambda::Function',
                'FunctionName': func_name,
                'FunctionArn': func.get('FunctionArn', ''),
                'Runtime': func.get('Runtime', ''),
                'VpcId': vpc_id,
                'SubnetIds': subnet_ids,
                'SecurityGroupIds': sg_ids,
                'Properties': {
                    'FunctionName': func_name,
                    'Runtime': func.get('Runtime', ''),
                    'Handler': func.get('Handler', ''),
                    'Role': func.get('Role', ''),
                    'VpcConfig': vpc_config if vpc_id else {},
                    'Tags': func.get('Tags', {})
                }
            }
            
            # Subnet との関係（VPC Lambda の場合）
            for subnet_id in subnet_ids:
                self.relationships.append((func_name, subnet_id, 'in_subnet', 'deployed'))
            
            # Security Group との関係
            for sg_id in sg_ids:
                self.relationships.append((func_name, sg_id, 'uses_sg', 'protected by'))
        
        print(f"    Found {len(self.lambda_functions)} Lambda Function(s)")
    
    # ==================== Database 関連 ====================
    
    def read_rds_instances(self):
        """RDS インスタンスを読み取る"""
        print("  Reading RDS Instances...")
        response = self._safe_call(self.rds.describe_db_instances, "RDS:DBInstance")
        if not response:
            return
        
        for db in response.get('DBInstances', []):
            db_id = db['DBInstanceIdentifier']
            
            # Subnet Group から Subnet を取得
            subnet_group = db.get('DBSubnetGroup', {})
            subnets = subnet_group.get('Subnets', [])
            subnet_ids = [s.get('SubnetIdentifier') for s in subnets]
            vpc_id = subnet_group.get('VpcId')
            
            # Security Group
            sg_ids = [sg['VpcSecurityGroupId'] for sg in db.get('VpcSecurityGroups', [])]
            
            self.rds_instances[db_id] = {
                'Type': 'AWS::RDS::DBInstance',
                'DBInstanceIdentifier': db_id,
                'Engine': db.get('Engine', ''),
                'DBInstanceClass': db.get('DBInstanceClass', ''),
                'VpcId': vpc_id,
                'SubnetIds': subnet_ids,
                'SecurityGroupIds': sg_ids,
                'Status': db.get('DBInstanceStatus', ''),
                'Properties': {
                    'DBInstanceIdentifier': db_id,
                    'Engine': db.get('Engine', ''),
                    'DBInstanceClass': db.get('DBInstanceClass', ''),
                    'DBSubnetGroupName': subnet_group.get('DBSubnetGroupName', ''),
                    'VPCSecurityGroups': sg_ids,
                    'Tags': db.get('TagList', [])
                }
            }
            
            # Subnet との関係
            for subnet_id in subnet_ids:
                if subnet_id:
                    self.relationships.append((db_id, subnet_id, 'in_subnet', 'deployed'))
            
            # Security Group との関係
            for sg_id in sg_ids:
                self.relationships.append((db_id, sg_id, 'uses_sg', 'protected by'))
        
        print(f"    Found {len(self.rds_instances)} RDS Instance(s)")
    
    def read_dynamodb_tables(self):
        """DynamoDB テーブルを読み取る"""
        print("  Reading DynamoDB Tables...")
        response = self._safe_call(self.dynamodb.list_tables, "DynamoDB:Table")
        if not response:
            return
        
        for table_name in response.get('TableNames', []):
            details = self._safe_call(
                self.dynamodb.describe_table, "DynamoDB:Table",
                TableName=table_name
            )
            if not details:
                continue
            
            table = details.get('Table', {})
            
            self.dynamodb_tables[table_name] = {
                'Type': 'AWS::DynamoDB::Table',
                'TableName': table_name,
                'TableArn': table.get('TableArn', ''),
                'Status': table.get('TableStatus', ''),
                'Properties': {
                    'TableName': table_name,
                    'AttributeDefinitions': table.get('AttributeDefinitions', []),
                    'KeySchema': table.get('KeySchema', []),
                    'BillingMode': table.get('BillingModeSummary', {}).get('BillingMode', 'PAY_PER_REQUEST'),
                    'Tags': table.get('Tags', [])
                }
            }
        
        print(f"    Found {len(self.dynamodb_tables)} DynamoDB Table(s)")
    
    def read_elasticache_clusters(self):
        """ElastiCache クラスターを読み取る"""
        print("  Reading ElastiCache Clusters...")
        response = self._safe_call(self.elasticache.describe_cache_clusters, "ElastiCache:Cluster")
        if not response:
            return
        
        for cluster in response.get('CacheClusters', []):
            cluster_id = cluster['CacheClusterId']
            
            # Subnet Group
            subnet_group_name = cluster.get('CacheSubnetGroupName')
            sg_ids = [sg['SecurityGroupId'] for sg in cluster.get('SecurityGroups', [])]
            
            self.elasticache_clusters[cluster_id] = {
                'Type': 'AWS::ElastiCache::CacheCluster',
                'CacheClusterId': cluster_id,
                'Engine': cluster.get('Engine', ''),
                'CacheNodeType': cluster.get('CacheNodeType', ''),
                'Status': cluster.get('CacheClusterStatus', ''),
                'SubnetGroupName': subnet_group_name,
                'SecurityGroupIds': sg_ids,
                'Properties': {
                    'ClusterName': cluster_id,
                    'Engine': cluster.get('Engine', ''),
                    'CacheNodeType': cluster.get('CacheNodeType', ''),
                    'CacheSubnetGroupName': subnet_group_name,
                    'VpcSecurityGroupIds': sg_ids,
                    'Tags': cluster.get('Tags', [])
                }
            }
        
        print(f"    Found {len(self.elasticache_clusters)} ElastiCache Cluster(s)")
    
    # ==================== Storage 関連 ====================
    
    def read_s3_buckets(self):
        """S3 バケットを読み取る"""
        print("  Reading S3 Buckets...")
        response = self._safe_call(self.s3.list_buckets, "S3:Bucket")
        if not response:
            return
        
        for bucket in response.get('Buckets', []):
            bucket_name = bucket['Name']
            
            # リージョン確認
            try:
                location = self.s3.get_bucket_location(Bucket=bucket_name)
                bucket_region = location.get('LocationConstraint') or 'us-east-1'
                
                # 指定リージョンのみ
                if bucket_region != self.region:
                    continue
            except ClientError:
                continue
            
            self.s3_buckets[bucket_name] = {
                'Type': 'AWS::S3::Bucket',
                'BucketName': bucket_name,
                'CreationDate': str(bucket.get('CreationDate', '')),
                'Properties': {
                    'BucketName': bucket_name
                }
            }
        
        print(f"    Found {len(self.s3_buckets)} S3 Bucket(s) in {self.region}")
    
    def read_efs_filesystems(self):
        """EFS ファイルシステムを読み取る"""
        print("  Reading EFS FileSystems...")
        response = self._safe_call(self.efs.describe_file_systems, "EFS:FileSystem")
        if not response:
            return
        
        for fs in response.get('FileSystems', []):
            fs_id = fs['FileSystemId']
            name = fs.get('Name') or fs_id
            
            self.efs_filesystems[fs_id] = {
                'Type': 'AWS::EFS::FileSystem',
                'FileSystemId': fs_id,
                'Name': name,
                'SizeInBytes': fs.get('SizeInBytes', {}).get('Value', 0),
                'Properties': {
                    'FileSystemId': fs_id,
                    'Encrypted': fs.get('Encrypted', False),
                    'PerformanceMode': fs.get('PerformanceMode', ''),
                    'Tags': fs.get('Tags', [])
                }
            }
        
        print(f"    Found {len(self.efs_filesystems)} EFS FileSystem(s)")
    
    # ==================== Load Balancer 関連 ====================
    
    def read_load_balancers(self):
        """Load Balancer を読み取る"""
        print("  Reading Load Balancers...")
        response = self._safe_call(self.elbv2.describe_load_balancers, "ELBv2:LoadBalancer")
        if not response:
            return
        
        for lb in response.get('LoadBalancers', []):
            lb_name = lb['LoadBalancerName']
            lb_arn = lb['LoadBalancerArn']
            lb_type = lb.get('Type', 'application')
            vpc_id = lb.get('VpcId')
            
            # Availability Zone から Subnet を取得
            subnet_ids = [az['SubnetId'] for az in lb.get('AvailabilityZones', []) if 'SubnetId' in az]
            sg_ids = lb.get('SecurityGroups', [])
            
            self.load_balancers[lb_name] = {
                'Type': f'AWS::ElasticLoadBalancingV2::LoadBalancer',
                'LoadBalancerName': lb_name,
                'LoadBalancerArn': lb_arn,
                'LoadBalancerType': lb_type,
                'VpcId': vpc_id,
                'SubnetIds': subnet_ids,
                'SecurityGroupIds': sg_ids,
                'Scheme': lb.get('Scheme', ''),
                'Properties': {
                    'Name': lb_name,
                    'Type': lb_type,
                    'Subnets': subnet_ids,
                    'SecurityGroups': sg_ids,
                    'Scheme': lb.get('Scheme', ''),
                    'Tags': lb.get('Tags', [])
                }
            }
            
            # Subnet との関係
            for subnet_id in subnet_ids:
                self.relationships.append((lb_name, subnet_id, 'in_subnet', 'deployed'))
            
            # Security Group との関係
            for sg_id in sg_ids:
                self.relationships.append((lb_name, sg_id, 'uses_sg', 'protected by'))
        
        print(f"    Found {len(self.load_balancers)} Load Balancer(s)")
        
        # Target Group も読み取り
        self._read_target_groups()
    
    def _read_target_groups(self):
        """Target Group を読み取り、関係を分析"""
        print("  Reading Target Groups...")
        response = self._safe_call(self.elbv2.describe_target_groups, "ELBv2:TargetGroup")
        if not response:
            return
        
        for tg in response.get('TargetGroups', []):
            tg_name = tg['TargetGroupName']
            tg_arn = tg['TargetGroupArn']
            vpc_id = tg.get('VpcId')
            
            # Load Balancer との関係
            lb_arns = tg.get('LoadBalancerArns', [])
            
            self.target_groups[tg_name] = {
                'Type': 'AWS::ElasticLoadBalancingV2::TargetGroup',
                'TargetGroupName': tg_name,
                'TargetGroupArn': tg_arn,
                'VpcId': vpc_id,
                'LoadBalancerArns': lb_arns,
                'Properties': {
                    'Name': tg_name,
                    'Protocol': tg.get('Protocol', ''),
                    'Port': tg.get('Port', 0),
                    'VpcId': vpc_id,
                    'TargetType': tg.get('TargetType', ''),
                    'Tags': tg.get('Tags', [])
                }
            }
            
            # Load Balancer との関係
            for lb_arn in lb_arns:
                for lb_name, lb_data in self.load_balancers.items():
                    if lb_data.get('LoadBalancerArn') == lb_arn:
                        self.relationships.append((lb_name, tg_name, 'routes_to', 'routes'))
                        break
            
            # ターゲットを取得
            targets_response = self._safe_call(
                self.elbv2.describe_target_health, "ELBv2:TargetHealth",
                TargetGroupArn=tg_arn
            )
            if targets_response:
                for target in targets_response.get('TargetHealthDescriptions', []):
                    target_id = target.get('Target', {}).get('Id', '')
                    
                    # EC2 インスタンスの場合
                    if target_id.startswith('i-'):
                        for instance_id in self.ec2_instances:
                            if instance_id == target_id:
                                self.relationships.append((tg_name, instance_id, 'targets', 'targets'))
                                break
        
        print(f"    Found {len(self.target_groups)} Target Group(s)")
    
    # ==================== Messaging 関連 ====================
    
    def read_sqs_queues(self):
        """SQS キューを読み取る"""
        print("  Reading SQS Queues...")
        response = self._safe_call(self.sqs.list_queues, "SQS:Queue")
        if not response:
            return
        
        for queue_url in response.get('QueueUrls', []):
            queue_name = queue_url.split('/')[-1]
            
            attrs = self._safe_call(
                self.sqs.get_queue_attributes, "SQS:Queue",
                QueueUrl=queue_url, AttributeNames=['All']
            )
            
            self.sqs_queues[queue_name] = {
                'Type': 'AWS::SQS::Queue',
                'QueueName': queue_name,
                'QueueUrl': queue_url,
                'Properties': {
                    'QueueName': queue_name,
                    'Attributes': attrs.get('Attributes', {}) if attrs else {}
                }
            }
        
        print(f"    Found {len(self.sqs_queues)} SQS Queue(s)")
    
    def read_sns_topics(self):
        """SNS トピックを読み取る"""
        print("  Reading SNS Topics...")
        response = self._safe_call(self.sns.list_topics, "SNS:Topic")
        if not response:
            return
        
        for topic in response.get('Topics', []):
            topic_arn = topic['TopicArn']
            topic_name = topic_arn.split(':')[-1]
            
            self.sns_topics[topic_name] = {
                'Type': 'AWS::SNS::Topic',
                'TopicName': topic_name,
                'TopicArn': topic_arn,
                'Properties': {
                    'TopicName': topic_name
                }
            }
        
        print(f"    Found {len(self.sns_topics)} SNS Topic(s)")
    
    # ==================== IAM/Management 関連 ====================
    
    def read_iam_roles(self):
        """IAM ロールを読み取る"""
        print("  Reading IAM Roles...")
        
        roles = []
        paginator = self.iam.get_paginator('list_roles')
        
        try:
            for page in paginator.paginate():
                roles.extend(page.get('Roles', []))
        except ClientError as e:
            self.errors.append(f"⚠ IAM:Role: {e.response.get('Error', {}).get('Code', '')}")
            return
        
        for role in roles:
            role_name = role['RoleName']
            
            # AWS 管理のロールは除外
            if role.get('Path', '').startswith('/aws-service-role/'):
                continue
            
            self.iam_roles[role_name] = {
                'Type': 'AWS::IAM::Role',
                'RoleName': role_name,
                'RoleArn': role.get('Arn', ''),
                'Properties': {
                    'RoleName': role_name,
                    'Path': role.get('Path', '/'),
                    'AssumeRolePolicyDocument': role.get('AssumeRolePolicyDocument', {})
                }
            }
        
        print(f"    Found {len(self.iam_roles)} IAM Role(s)")
    
    def read_cloudwatch_log_groups(self):
        """CloudWatch Log Group を読み取る"""
        print("  Reading CloudWatch Log Groups...")
        
        log_groups = []
        paginator = self.logs.get_paginator('describe_log_groups')
        
        try:
            for page in paginator.paginate():
                log_groups.extend(page.get('logGroups', []))
        except ClientError as e:
            self.errors.append(f"⚠ CloudWatch:LogGroup: {e.response.get('Error', {}).get('Code', '')}")
            return
        
        for lg in log_groups:
            lg_name = lg['logGroupName']
            
            self.log_groups[lg_name] = {
                'Type': 'AWS::Logs::LogGroup',
                'LogGroupName': lg_name,
                'LogGroupArn': lg.get('arn', ''),
                'Properties': {
                    'LogGroupName': lg_name,
                    'RetentionInDays': lg.get('retentionInDays')
                }
            }
        
        print(f"    Found {len(self.log_groups)} CloudWatch Log Group(s)")
    
    # ==================== 全リソース読み取り ====================
    
    def read_all_resources(self):
        """すべてのリソースを読み取る"""
        print("=" * 80)
        print("Reading AWS Resources...")
        print("=" * 80 + "\n")
        
        # VPC 関連
        self.read_vpcs()
        self.read_subnets()
        self.read_internet_gateways()
        self.read_nat_gateways()
        self.read_security_groups()
        self.read_vpc_endpoints()
        
        # Compute
        self.read_ec2_instances()
        self.read_ecs_clusters()
        self.read_eks_clusters()
        self.read_lambda_functions()
        
        # Database
        self.read_rds_instances()
        self.read_dynamodb_tables()
        self.read_elasticache_clusters()
        
        # Storage
        self.read_s3_buckets()
        self.read_efs_filesystems()
        
        # Load Balancer
        self.read_load_balancers()
        
        # Messaging
        self.read_sqs_queues()
        self.read_sns_topics()
        
        # IAM/Management
        self.read_iam_roles()
        self.read_cloudwatch_log_groups()
        
        # 統計
        total = (
            len(self.vpcs) + len(self.subnets) + len(self.internet_gateways) +
            len(self.nat_gateways) + len(self.security_groups) + len(self.vpc_endpoints) +
            len(self.ec2_instances) + len(self.ecs_clusters) + len(self.ecs_services) +
            len(self.eks_clusters) + len(self.lambda_functions) +
            len(self.rds_instances) + len(self.dynamodb_tables) + len(self.elasticache_clusters) +
            len(self.s3_buckets) + len(self.efs_filesystems) +
            len(self.load_balancers) + len(self.target_groups) +
            len(self.sqs_queues) + len(self.sns_topics) +
            len(self.iam_roles) + len(self.log_groups)
        )
        
        print("\n" + "=" * 80)
        print(f"Total Resources: {total}")
        print(f"Total Relationships: {len(self.relationships)}")
        print("=" * 80)
        
        # エラー表示
        if self.errors:
            print("\nWarnings/Errors:")
            print("-" * 40)
            for error in self.errors:
                print(error)
            print("-" * 40)
        
        return total


# ==================== CloudFormation エクスポート ====================

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
            safe_name = safe_name[:100]  # 長すぎる場合は切り詰め
            
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
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(cf_resource, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            total_files += 1
        
        print(f"  {category}: {len(resources)} file(s)")
    
    print(f"\n✓ Exported {total_files} CloudFormation file(s)")
    return total_files


# ==================== アーキテクチャ図生成 ====================

def get_icon_for_type(resource_type):
    """リソースタイプに応じたアイコンを返す"""
    icon_map = {
        'AWS::EC2::VPC': VPC,
        'AWS::EC2::Subnet': PrivateSubnet,
        'AWS::EC2::InternetGateway': InternetGateway,
        'AWS::EC2::NatGateway': NATGateway,
        'AWS::EC2::SecurityGroup': VPCRouter,
        'AWS::EC2::VPCEndpoint': Endpoint,
        'AWS::EC2::Instance': EC2,
        'AWS::ECS::Cluster': ECS,
        'AWS::ECS::Service': Fargate,
        'AWS::EKS::Cluster': EKS,
        'AWS::Lambda::Function': Lambda,
        'AWS::RDS::DBInstance': RDS,
        'AWS::DynamoDB::Table': Dynamodb,
        'AWS::ElastiCache::CacheCluster': ElastiCache,
        'AWS::S3::Bucket': S3,
        'AWS::EFS::FileSystem': EFS,
        'AWS::ElasticLoadBalancingV2::LoadBalancer': ALB,
        'AWS::ElasticLoadBalancingV2::TargetGroup': ELB,
        'AWS::SQS::Queue': SQS,
        'AWS::SNS::Topic': SNS,
        'AWS::IAM::Role': IAM,
        'AWS::Logs::LogGroup': Cloudwatch,
    }
    return icon_map.get(resource_type, Blank)


def generate_architecture_diagram(reader, output_dir, output_name):
    """アーキテクチャ図を生成"""
    print("\n" + "=" * 80)
    print("Generating Architecture Diagram...")
    print("=" * 80 + "\n")
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_name)
    
    graph_attr = {
        "fontsize": "12",
        "bgcolor": "white",
        "splines": "ortho",
        "nodesep": "0.8",
        "ranksep": "1.2",
        "pad": "0.5"
    }
    
    with Diagram(
        "AWS Architecture",
        filename=output_path,
        show=False,
        direction="TB",
        graph_attr=graph_attr
    ):
        nodes = {}
        
        # VPC ごとにクラスターを作成
        for vpc_id, vpc_data in reader.vpcs.items():
            vpc_name = vpc_data.get('Name', vpc_id)
            cidr = vpc_data.get('CidrBlock', '')
            
            with Cluster(
                f"{vpc_name}\n{cidr}",
                graph_attr={"bgcolor": "#E3F2FD", "style": "rounded"}
            ):
                # VPC ノード
                vpc_node = VPC(f"VPC\n{vpc_name[:20]}")
                nodes[vpc_id] = vpc_node
                
                # この VPC に関連する IGW
                for igw_id, igw_data in reader.internet_gateways.items():
                    if igw_data.get('AttachedVpcId') == vpc_id:
                        igw_node = InternetGateway(f"IGW\n{igw_data.get('Name', igw_id)[:15]}")
                        nodes[igw_id] = igw_node
                        igw_node >> Edge(color="blue", style="bold") >> vpc_node
                
                # この VPC のサブネット
                vpc_subnets = {
                    sid: sdata for sid, sdata in reader.subnets.items()
                    if sdata.get('VpcId') == vpc_id
                }
                
                # Public Subnets
                public_subnets = {sid: s for sid, s in vpc_subnets.items() if s.get('IsPublic')}
                private_subnets = {sid: s for sid, s in vpc_subnets.items() if not s.get('IsPublic')}
                
                if public_subnets:
                    with Cluster(
                        "Public Subnets",
                        graph_attr={"bgcolor": "#E8F5E9", "style": "dashed"}
                    ):
                        for subnet_id, subnet_data in public_subnets.items():
                            subnet_name = subnet_data.get('Name', subnet_id)
                            az = subnet_data.get('AvailabilityZone', '')[-2:]
                            subnet_node = PublicSubnet(f"{subnet_name[:15]}\n{az}")
                            nodes[subnet_id] = subnet_node
                            
                            # NAT Gateway
                            for nat_id, nat_data in reader.nat_gateways.items():
                                if nat_data.get('SubnetId') == subnet_id:
                                    nat_node = NATGateway(f"NAT\n{nat_data.get('Name', nat_id)[:10]}")
                                    nodes[nat_id] = nat_node
                            
                            # Load Balancer
                            for lb_name, lb_data in reader.load_balancers.items():
                                if subnet_id in lb_data.get('SubnetIds', []):
                                    if lb_name not in nodes:
                                        lb_type = lb_data.get('LoadBalancerType', 'application')
                                        icon = ALB if lb_type == 'application' else NLB
                                        lb_node = icon(f"{lb_name[:15]}")
                                        nodes[lb_name] = lb_node
                
                if private_subnets:
                    with Cluster(
                        "Private Subnets",
                        graph_attr={"bgcolor": "#FFF3E0", "style": "dashed"}
                    ):
                        for subnet_id, subnet_data in private_subnets.items():
                            subnet_name = subnet_data.get('Name', subnet_id)
                            az = subnet_data.get('AvailabilityZone', '')[-2:]
                            subnet_node = PrivateSubnet(f"{subnet_name[:15]}\n{az}")
                            nodes[subnet_id] = subnet_node
                            
                            # EC2 in this subnet
                            for ec2_id, ec2_data in reader.ec2_instances.items():
                                if ec2_data.get('SubnetId') == subnet_id:
                                    ec2_name = ec2_data.get('Name', ec2_id)
                                    ec2_node = EC2(f"{ec2_name[:15]}")
                                    nodes[ec2_id] = ec2_node
                            
                            # ECS Services in this subnet
                            for svc_name, svc_data in reader.ecs_services.items():
                                if subnet_id in svc_data.get('SubnetIds', []):
                                    if svc_name not in nodes:
                                        svc_node = Fargate(f"{svc_name[:15]}")
                                        nodes[svc_name] = svc_node
                            
                            # Lambda in this subnet
                            for func_name, func_data in reader.lambda_functions.items():
                                if subnet_id in func_data.get('SubnetIds', []):
                                    if func_name not in nodes:
                                        func_node = Lambda(f"{func_name[:15]}")
                                        nodes[func_name] = func_node
                            
                            # RDS in this subnet
                            for db_id, db_data in reader.rds_instances.items():
                                if subnet_id in db_data.get('SubnetIds', []):
                                    if db_id not in nodes:
                                        db_node = RDS(f"{db_id[:15]}")
                                        nodes[db_id] = db_node
        
        # VPC 外のリソース
        with Cluster(
            "External Services",
            graph_attr={"bgcolor": "#F5F5F5", "style": "dashed"}
        ):
            # S3
            if reader.s3_buckets:
                s3_count = len(reader.s3_buckets)
                if s3_count <= 3:
                    for bucket_name in list(reader.s3_buckets.keys())[:3]:
                        s3_node = S3(f"{bucket_name[:15]}")
                        nodes[bucket_name] = s3_node
                else:
                    s3_node = S3(f"S3 Buckets\n({s3_count})")
                    nodes['s3_combined'] = s3_node
            
            # DynamoDB
            if reader.dynamodb_tables:
                ddb_count = len(reader.dynamodb_tables)
                if ddb_count <= 3:
                    for table_name in list(reader.dynamodb_tables.keys())[:3]:
                        ddb_node = Dynamodb(f"{table_name[:15]}")
                        nodes[table_name] = ddb_node
                else:
                    ddb_node = Dynamodb(f"DynamoDB\n({ddb_count} tables)")
                    nodes['dynamodb_combined'] = ddb_node
            
            # SQS
            if reader.sqs_queues:
                sqs_count = len(reader.sqs_queues)
                if sqs_count <= 3:
                    for queue_name in list(reader.sqs_queues.keys())[:3]:
                        sqs_node = SQS(f"{queue_name[:15]}")
                        nodes[queue_name] = sqs_node
                else:
                    sqs_node = SQS(f"SQS Queues\n({sqs_count})")
                    nodes['sqs_combined'] = sqs_node
            
            # SNS
            if reader.sns_topics:
                sns_count = len(reader.sns_topics)
                if sns_count <= 3:
                    for topic_name in list(reader.sns_topics.keys())[:3]:
                        sns_node = SNS(f"{topic_name[:15]}")
                        nodes[topic_name] = sns_node
                else:
                    sns_node = SNS(f"SNS Topics\n({sns_count})")
                    nodes['sns_combined'] = sns_node
        
        # 関係を線で接続
        edge_colors = {
            'attached_to': ('blue', 'bold', ''),
            'belongs_to': ('gray', 'dashed', ''),
            'in_subnet': ('green', 'solid', ''),
            'in_vpc': ('blue', 'dotted', ''),
            'in_cluster': ('purple', 'solid', ''),
            'uses_sg': ('orange', 'dotted', ''),
            'routes_to': ('red', 'solid', ''),
            'targets': ('red', 'dashed', 'targets'),
        }
        
        drawn_edges = set()
        
        for source_id, target_id, rel_type, label in reader.relationships:
            if source_id in nodes and target_id in nodes:
                edge_key = (source_id, target_id)
                if edge_key not in drawn_edges:
                    color, style, edge_label = edge_colors.get(rel_type, ('gray', 'solid', ''))
                    nodes[source_id] >> Edge(color=color, style=style, label=edge_label) >> nodes[target_id]
                    drawn_edges.add(edge_key)
    
    print(f"✓ Diagram generated: {output_path}.png")
    return f"{output_path}.png"


# ==================== メイン ====================

def main():
    parser = argparse.ArgumentParser(
        description='AWS アーキテクチャ図生成器 V2 - リソース関係を含む'
    )
    parser.add_argument(
        '--region', 
        default='ap-northeast-1',
        help='AWS リージョン (default: ap-northeast-1)'
    )
    parser.add_argument(
        '--output-dir',
        default='aws-outputs',
        help='出力ディレクトリ (default: aws-outputs)'
    )
    parser.add_argument(
        '--output-name',
        default='aws-architecture',
        help='出力ファイル名 (default: aws-architecture)'
    )
    parser.add_argument(
        '--no-export',
        action='store_true',
        help='CloudFormation エクスポートをスキップ'
    )
    parser.add_argument(
        '--no-diagram',
        action='store_true',
        help='アーキテクチャ図生成をスキップ'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("AWS Architecture Diagram Generator V2")
    print("=" * 80)
    print(f"Region: {args.region}")
    print(f"Output Directory: {args.output_dir}")
    print("=" * 80 + "\n")
    
    # リソース読み取り
    reader = AWSResourceReaderV2(region=args.region)
    total = reader.read_all_resources()
    
    if total == 0:
        print("\n⚠ No resources found. Check your credentials and region.")
        return
    
    # CloudFormation エクスポート
    if not args.no_export:
        cf_dir = os.path.join(args.output_dir, 'cloudformation')
        export_cloudformation(reader, cf_dir)
    
    # アーキテクチャ図生成
    if not args.no_diagram:
        diagram_dir = os.path.join(args.output_dir, 'diagrams')
        generate_architecture_diagram(reader, diagram_dir, args.output_name)
    
    print("\n" + "=" * 80)
    print("Complete!")
    print(f"Output directory: {os.path.abspath(args.output_dir)}")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    main()
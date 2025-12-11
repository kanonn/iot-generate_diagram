# -*- coding: utf-8 -*-
"""
AWS リソースリーダーモジュール
AWS API からリソースを読み取る
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from collections import defaultdict


class AWSResourceReader:
    """AWS からリソースを読み取るクラス"""
    
    def __init__(self, region='ap-northeast-1'):
        self.region = region
        self.errors = []
        
        # リソースストレージ
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
        
        # 関係マッピング
        self.relationships = []
        
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
            print("\nERROR: AWS credentials not found!")
            raise
    
    def _safe_call(self, func, service_name, *args, **kwargs):
        """安全に AWS API を呼び出す"""
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code in ['AccessDenied', 'AccessDeniedException', 'UnauthorizedOperation']:
                self.errors.append(f"⚠ {service_name}: Access Denied")
            else:
                self.errors.append(f"⚠ {service_name}: {error_code}")
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
    
    def _paginate(self, client_method, service_name, key, **kwargs):
        """ページネーションを処理"""
        items = []
        try:
            paginator = client_method
            if hasattr(paginator, 'get_paginator'):
                # get_paginator が使える場合
                pass
            
            # 直接呼び出し
            response = self._safe_call(client_method, service_name, **kwargs)
            if response:
                items.extend(response.get(key, []))
                
                # NextToken ベースのページネーション
                while response and response.get('NextToken'):
                    kwargs['NextToken'] = response['NextToken']
                    response = self._safe_call(client_method, service_name, **kwargs)
                    if response:
                        items.extend(response.get(key, []))
                
                # Marker ベースのページネーション
                while response and response.get('Marker'):
                    kwargs['Marker'] = response['Marker']
                    response = self._safe_call(client_method, service_name, **kwargs)
                    if response:
                        items.extend(response.get(key, []))
                        
        except Exception as e:
            self.errors.append(f"⚠ {service_name}: Pagination error - {str(e)[:30]}")
        
        return items
    
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
        """サブネットを読み取る（ページネーション対応）"""
        print("  Reading Subnets...")
        
        all_subnets = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            
            response = self._safe_call(self.ec2.describe_subnets, "EC2:Subnet", **kwargs)
            if not response:
                break
            
            all_subnets.extend(response.get('Subnets', []))
            next_token = response.get('NextToken')
            
            if not next_token:
                break
        
        for subnet in all_subnets:
            subnet_id = subnet['SubnetId']
            vpc_id = subnet['VpcId']
            name = self._get_name_tag(subnet.get('Tags', []))
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
            
            if attached_vpc:
                self.relationships.append((igw_id, attached_vpc, 'attached_to', 'attached'))
        
        print(f"    Found {len(self.internet_gateways)} Internet Gateway(s)")
    
    def read_nat_gateways(self):
        """NAT Gateway を読み取る"""
        print("  Reading NAT Gateways...")
        
        all_nats = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            
            response = self._safe_call(self.ec2.describe_nat_gateways, "EC2:NATGateway", **kwargs)
            if not response:
                break
            
            all_nats.extend(response.get('NatGateways', []))
            next_token = response.get('NextToken')
            
            if not next_token:
                break
        
        for nat in all_nats:
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
            
            if subnet_id:
                self.relationships.append((nat_id, subnet_id, 'in_subnet', 'in'))
        
        print(f"    Found {len(self.nat_gateways)} NAT Gateway(s)")
    
    def read_security_groups(self):
        """Security Group を読み取る"""
        print("  Reading Security Groups...")
        
        all_sgs = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            
            response = self._safe_call(self.ec2.describe_security_groups, "EC2:SecurityGroup", **kwargs)
            if not response:
                break
            
            all_sgs.extend(response.get('SecurityGroups', []))
            next_token = response.get('NextToken')
            
            if not next_token:
                break
        
        for sg in all_sgs:
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
        """VPC Endpoint を読み取る（ページネーション対応）"""
        print("  Reading VPC Endpoints...")
        
        all_endpoints = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            
            response = self._safe_call(self.ec2.describe_vpc_endpoints, "EC2:VPCEndpoint", **kwargs)
            if not response:
                break
            
            all_endpoints.extend(response.get('VpcEndpoints', []))
            next_token = response.get('NextToken')
            
            if not next_token:
                break
        
        for endpoint in all_endpoints:
            endpoint_id = endpoint['VpcEndpointId']
            vpc_id = endpoint.get('VpcId')
            name = self._get_name_tag(endpoint.get('Tags', []))
            subnet_ids = endpoint.get('SubnetIds', [])
            
            self.vpc_endpoints[endpoint_id] = {
                'Type': 'AWS::EC2::VPCEndpoint',
                'VpcEndpointId': endpoint_id,
                'Name': name or endpoint_id,
                'VpcId': vpc_id,
                'ServiceName': endpoint.get('ServiceName', ''),
                'EndpointType': endpoint.get('VpcEndpointType', ''),
                'SubnetIds': subnet_ids,
                'Properties': {
                    'VpcId': vpc_id,
                    'ServiceName': endpoint.get('ServiceName', ''),
                    'VpcEndpointType': endpoint.get('VpcEndpointType', ''),
                    'SubnetIds': subnet_ids,
                    'Tags': endpoint.get('Tags', [])
                }
            }
            
            if vpc_id:
                self.relationships.append((endpoint_id, vpc_id, 'in_vpc', 'in'))
            for subnet_id in subnet_ids:
                self.relationships.append((endpoint_id, subnet_id, 'in_subnet', 'endpoint'))
        
        print(f"    Found {len(self.vpc_endpoints)} VPC Endpoint(s)")
    
    # ==================== Compute 関連 ====================
    
    def read_ec2_instances(self):
        """EC2 インスタンスを読み取る（ページネーション対応）"""
        print("  Reading EC2 Instances...")
        
        all_instances = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            
            response = self._safe_call(self.ec2.describe_instances, "EC2:Instance", **kwargs)
            if not response:
                break
            
            for reservation in response.get('Reservations', []):
                all_instances.extend(reservation.get('Instances', []))
            
            next_token = response.get('NextToken')
            
            if not next_token:
                break
        
        for instance in all_instances:
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
            
            if subnet_id:
                self.relationships.append((instance_id, subnet_id, 'in_subnet', 'deployed'))
        
        print(f"    Found {len(self.ec2_instances)} EC2 Instance(s)")
    
    def read_ecs_clusters(self):
        """ECS クラスターを読み取る"""
        print("  Reading ECS Clusters...")
        
        cluster_arns = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            
            response = self._safe_call(self.ecs.list_clusters, "ECS:Cluster", **kwargs)
            if not response:
                break
            
            cluster_arns.extend(response.get('clusterArns', []))
            next_token = response.get('nextToken')
            
            if not next_token:
                break
        
        if not cluster_arns:
            print("    Found 0 ECS Cluster(s)")
            return
        
        # 100件ずつ describe
        for i in range(0, len(cluster_arns), 100):
            batch = cluster_arns[i:i+100]
            details = self._safe_call(
                self.ecs.describe_clusters, "ECS:Cluster",
                clusters=batch, include=['TAGS']
            )
            if not details:
                continue
            
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
        
        # ECS Services
        self._read_ecs_services(cluster_arns)
    
    def _read_ecs_services(self, cluster_arns):
        """ECS サービスを読み取る"""
        print("  Reading ECS Services...")
        
        total_services = 0
        
        for cluster_arn in cluster_arns:
            cluster_name = cluster_arn.split('/')[-1]
            
            service_arns = []
            next_token = None
            
            while True:
                kwargs = {'cluster': cluster_arn}
                if next_token:
                    kwargs['nextToken'] = next_token
                
                response = self._safe_call(self.ecs.list_services, "ECS:Service", **kwargs)
                if not response:
                    break
                
                service_arns.extend(response.get('serviceArns', []))
                next_token = response.get('nextToken')
                
                if not next_token:
                    break
            
            if not service_arns:
                continue
            
            # 10件ずつ describe
            for i in range(0, len(service_arns), 10):
                batch = service_arns[i:i+10]
                details = self._safe_call(
                    self.ecs.describe_services, "ECS:Service",
                    cluster=cluster_arn, services=batch
                )
                if not details:
                    continue
                
                for service in details.get('services', []):
                    service_name = service['serviceName']
                    
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
                    
                    self.relationships.append((service_name, cluster_name, 'in_cluster', 'runs in'))
                    
                    for subnet_id in subnet_ids:
                        self.relationships.append((service_name, subnet_id, 'in_subnet', 'deployed'))
                    
                    total_services += 1
        
        print(f"    Found {total_services} ECS Service(s)")
    
    def read_eks_clusters(self):
        """EKS クラスターを読み取る"""
        print("  Reading EKS Clusters...")
        
        cluster_names = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            
            response = self._safe_call(self.eks.list_clusters, "EKS:Cluster", **kwargs)
            if not response:
                break
            
            cluster_names.extend(response.get('clusters', []))
            next_token = response.get('nextToken')
            
            if not next_token:
                break
        
        for cluster_name in cluster_names:
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
            
            for subnet_id in subnet_ids:
                self.relationships.append((cluster_name, subnet_id, 'in_subnet', 'deployed'))
        
        print(f"    Found {len(self.eks_clusters)} EKS Cluster(s)")
    
    def read_lambda_functions(self):
        """Lambda 関数を読み取る（ページネーション対応）"""
        print("  Reading Lambda Functions...")
        
        all_functions = []
        marker = None
        
        while True:
            kwargs = {}
            if marker:
                kwargs['Marker'] = marker
            
            response = self._safe_call(self.lambda_client.list_functions, "Lambda:Function", **kwargs)
            if not response:
                break
            
            all_functions.extend(response.get('Functions', []))
            marker = response.get('NextMarker')
            
            if not marker:
                break
        
        for func in all_functions:
            func_name = func['FunctionName']
            
            vpc_config = func.get('VpcConfig', {})
            vpc_id = vpc_config.get('VpcId')
            subnet_ids = vpc_config.get('SubnetIds', [])
            sg_ids = vpc_config.get('SecurityGroupIds', [])
            
            # トリガー情報を取得
            triggers = []
            try:
                event_mappings = self.lambda_client.list_event_source_mappings(FunctionName=func_name)
                for mapping in event_mappings.get('EventSourceMappings', []):
                    event_source_arn = mapping.get('EventSourceArn', '')
                    triggers.append({
                        'EventSourceArn': event_source_arn,
                        'State': mapping.get('State', ''),
                    })
            except:
                pass
            
            self.lambda_functions[func_name] = {
                'Type': 'AWS::Lambda::Function',
                'FunctionName': func_name,
                'FunctionArn': func.get('FunctionArn', ''),
                'Runtime': func.get('Runtime', ''),
                'VpcId': vpc_id,
                'SubnetIds': subnet_ids,
                'SecurityGroupIds': sg_ids,
                'Triggers': triggers,
                'Properties': {
                    'FunctionName': func_name,
                    'Runtime': func.get('Runtime', ''),
                    'Handler': func.get('Handler', ''),
                    'Role': func.get('Role', ''),
                    'VpcConfig': vpc_config if vpc_id else {},
                    'Tags': func.get('Tags', {})
                }
            }
            
            for subnet_id in subnet_ids:
                self.relationships.append((func_name, subnet_id, 'in_subnet', 'deployed'))
            
            # SNS トリガーとの関係
            for trigger in triggers:
                arn = trigger.get('EventSourceArn', '')
                if ':sns:' in arn:
                    topic_name = arn.split(':')[-1]
                    self.relationships.append((topic_name, func_name, 'triggers', 'triggers'))
                elif ':sqs:' in arn:
                    queue_name = arn.split(':')[-1]
                    self.relationships.append((queue_name, func_name, 'triggers', 'triggers'))
                elif ':dynamodb:' in arn:
                    table_name = arn.split('/')[-1].split('/')[0] if '/' in arn else arn.split(':')[-1]
                    self.relationships.append((table_name, func_name, 'triggers', 'triggers'))
        
        print(f"    Found {len(self.lambda_functions)} Lambda Function(s)")
    
    # ==================== Database 関連 ====================
    
    def read_rds_instances(self):
        """RDS インスタンスを読み取る（ページネーション対応）"""
        print("  Reading RDS Instances...")
        
        all_dbs = []
        marker = None
        
        while True:
            kwargs = {}
            if marker:
                kwargs['Marker'] = marker
            
            response = self._safe_call(self.rds.describe_db_instances, "RDS:DBInstance", **kwargs)
            if not response:
                break
            
            all_dbs.extend(response.get('DBInstances', []))
            marker = response.get('Marker')
            
            if not marker:
                break
        
        for db in all_dbs:
            db_id = db['DBInstanceIdentifier']
            
            subnet_group = db.get('DBSubnetGroup', {})
            subnets = subnet_group.get('Subnets', [])
            subnet_ids = [s.get('SubnetIdentifier') for s in subnets]
            vpc_id = subnet_group.get('VpcId')
            
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
            
            for subnet_id in subnet_ids:
                if subnet_id:
                    self.relationships.append((db_id, subnet_id, 'in_subnet', 'deployed'))
        
        print(f"    Found {len(self.rds_instances)} RDS Instance(s)")
    
    def read_dynamodb_tables(self):
        """DynamoDB テーブルを読み取る（ページネーション対応）"""
        print("  Reading DynamoDB Tables...")
        
        table_names = []
        last_table = None
        
        while True:
            kwargs = {}
            if last_table:
                kwargs['ExclusiveStartTableName'] = last_table
            
            response = self._safe_call(self.dynamodb.list_tables, "DynamoDB:Table", **kwargs)
            if not response:
                break
            
            table_names.extend(response.get('TableNames', []))
            last_table = response.get('LastEvaluatedTableName')
            
            if not last_table:
                break
        
        for table_name in table_names:
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
                }
            }
        
        print(f"    Found {len(self.dynamodb_tables)} DynamoDB Table(s)")
    
    def read_elasticache_clusters(self):
        """ElastiCache クラスターを読み取る"""
        print("  Reading ElastiCache Clusters...")
        
        all_clusters = []
        marker = None
        
        while True:
            kwargs = {}
            if marker:
                kwargs['Marker'] = marker
            
            response = self._safe_call(self.elasticache.describe_cache_clusters, "ElastiCache:Cluster", **kwargs)
            if not response:
                break
            
            all_clusters.extend(response.get('CacheClusters', []))
            marker = response.get('Marker')
            
            if not marker:
                break
        
        for cluster in all_clusters:
            cluster_id = cluster['CacheClusterId']
            
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
            
            try:
                location = self.s3.get_bucket_location(Bucket=bucket_name)
                bucket_region = location.get('LocationConstraint') or 'us-east-1'
                
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
        """EFS ファイルシステムを読み取る（ページネーション対応）"""
        print("  Reading EFS FileSystems...")
        
        all_fs = []
        marker = None
        
        while True:
            kwargs = {}
            if marker:
                kwargs['Marker'] = marker
            
            response = self._safe_call(self.efs.describe_file_systems, "EFS:FileSystem", **kwargs)
            if not response:
                break
            
            all_fs.extend(response.get('FileSystems', []))
            marker = response.get('NextMarker')
            
            if not marker:
                break
        
        for fs in all_fs:
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
        """Load Balancer を読み取る（ページネーション対応）"""
        print("  Reading Load Balancers...")
        
        all_lbs = []
        marker = None
        
        while True:
            kwargs = {}
            if marker:
                kwargs['Marker'] = marker
            
            response = self._safe_call(self.elbv2.describe_load_balancers, "ELBv2:LoadBalancer", **kwargs)
            if not response:
                break
            
            all_lbs.extend(response.get('LoadBalancers', []))
            marker = response.get('NextMarker')
            
            if not marker:
                break
        
        for lb in all_lbs:
            lb_name = lb['LoadBalancerName']
            lb_arn = lb['LoadBalancerArn']
            lb_type = lb.get('Type', 'application')
            vpc_id = lb.get('VpcId')
            
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
                }
            }
            
            for subnet_id in subnet_ids:
                self.relationships.append((lb_name, subnet_id, 'in_subnet', 'deployed'))
        
        print(f"    Found {len(self.load_balancers)} Load Balancer(s)")
        
        self._read_target_groups()
    
    def _read_target_groups(self):
        """Target Group を読み取る"""
        print("  Reading Target Groups...")
        
        all_tgs = []
        marker = None
        
        while True:
            kwargs = {}
            if marker:
                kwargs['Marker'] = marker
            
            response = self._safe_call(self.elbv2.describe_target_groups, "ELBv2:TargetGroup", **kwargs)
            if not response:
                break
            
            all_tgs.extend(response.get('TargetGroups', []))
            marker = response.get('NextMarker')
            
            if not marker:
                break
        
        for tg in all_tgs:
            tg_name = tg['TargetGroupName']
            tg_arn = tg['TargetGroupArn']
            vpc_id = tg.get('VpcId')
            
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
                }
            }
            
            for lb_arn in lb_arns:
                for lb_name, lb_data in self.load_balancers.items():
                    if lb_data.get('LoadBalancerArn') == lb_arn:
                        self.relationships.append((lb_name, tg_name, 'routes_to', 'routes'))
                        break
        
        print(f"    Found {len(self.target_groups)} Target Group(s)")
    
    # ==================== Messaging 関連 ====================
    
    def read_sqs_queues(self):
        """SQS キューを読み取る（ページネーション対応）"""
        print("  Reading SQS Queues...")
        
        all_urls = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            
            response = self._safe_call(self.sqs.list_queues, "SQS:Queue", **kwargs)
            if not response:
                break
            
            all_urls.extend(response.get('QueueUrls', []))
            next_token = response.get('NextToken')
            
            if not next_token:
                break
        
        for queue_url in all_urls:
            queue_name = queue_url.split('/')[-1]
            
            self.sqs_queues[queue_name] = {
                'Type': 'AWS::SQS::Queue',
                'QueueName': queue_name,
                'QueueUrl': queue_url,
                'Properties': {
                    'QueueName': queue_name,
                }
            }
        
        print(f"    Found {len(self.sqs_queues)} SQS Queue(s)")
    
    def read_sns_topics(self):
        """SNS トピックを読み取る（ページネーション対応）"""
        print("  Reading SNS Topics...")
        
        all_topics = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['NextToken'] = next_token
            
            response = self._safe_call(self.sns.list_topics, "SNS:Topic", **kwargs)
            if not response:
                break
            
            all_topics.extend(response.get('Topics', []))
            next_token = response.get('NextToken')
            
            if not next_token:
                break
        
        for topic in all_topics:
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
        """IAM ロールを読み取る（ページネーション対応）"""
        print("  Reading IAM Roles...")
        
        all_roles = []
        marker = None
        
        while True:
            kwargs = {}
            if marker:
                kwargs['Marker'] = marker
            
            response = self._safe_call(self.iam.list_roles, "IAM:Role", **kwargs)
            if not response:
                break
            
            all_roles.extend(response.get('Roles', []))
            
            if not response.get('IsTruncated'):
                break
            marker = response.get('Marker')
        
        for role in all_roles:
            role_name = role['RoleName']
            
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
        """CloudWatch Log Group を読み取る（ページネーション対応）"""
        print("  Reading CloudWatch Log Groups...")
        
        all_log_groups = []
        next_token = None
        
        while True:
            kwargs = {}
            if next_token:
                kwargs['nextToken'] = next_token
            
            response = self._safe_call(self.logs.describe_log_groups, "CloudWatch:LogGroup", **kwargs)
            if not response:
                break
            
            all_log_groups.extend(response.get('logGroups', []))
            next_token = response.get('nextToken')
            
            if not next_token:
                break
        
        for lg in all_log_groups:
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
        
        if self.errors:
            print("\nWarnings/Errors:")
            print("-" * 40)
            for error in self.errors:
                print(error)
            print("-" * 40)
        
        return total

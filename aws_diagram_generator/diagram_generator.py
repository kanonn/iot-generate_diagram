# -*- coding: utf-8 -*-
"""
アーキテクチャ図生成モジュール
リソースから図を生成する
"""

import os
from collections import defaultdict

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import (
    VPC, InternetGateway, PrivateSubnet, PublicSubnet, NATGateway,
    ELB, ALB, NLB, Endpoint
)
from diagrams.aws.compute import EC2, ECS, EKS, Lambda, Fargate
from diagrams.aws.database import RDS, Dynamodb, ElastiCache
from diagrams.aws.storage import S3, EFS
from diagrams.aws.integration import SQS, SNS
from diagrams.generic.blank import Blank


class ArchitectureDiagramGenerator:
    """アーキテクチャ図を生成するクラス"""
    
    def __init__(self, reader):
        """
        Args:
            reader: AWSResourceReader または CloudFormationImporter のインスタンス
        """
        self.reader = reader
        
        # サブネットごとのリソースを整理
        self.subnet_resources = defaultdict(lambda: {
            'ec2': [],
            'ecs_services': [],
            'eks_clusters': [],
            'lambda': [],
            'rds': [],
            'nat_gateways': [],
            'load_balancers': [],
            'vpc_endpoints': [],
        })
        
        # VPC 外のリソース
        self.external_resources = {
            'lambda': [],
            's3': [],
            'dynamodb': [],
            'sqs': [],
            'sns': [],
            'efs': [],
            'target_groups': [],
            'load_balancers': [],
        }
        
        # VPC 内の集約リソース（サブネット指定なし）
        self.vpc_resources = defaultdict(lambda: {
            'target_groups': [],
            'load_balancers': [],
        })
    
    def _organize_resources(self):
        """リソースをサブネットごとに整理"""
        reader = self.reader
        
        # EC2 -> Subnet
        for ec2_id, ec2_data in reader.ec2_instances.items():
            subnet_id = ec2_data.get('SubnetId') or ec2_data.get('Properties', {}).get('SubnetId')
            if subnet_id and subnet_id in reader.subnets:
                self.subnet_resources[subnet_id]['ec2'].append((ec2_id, ec2_data))
        
        # ECS Service -> Subnet
        for svc_name, svc_data in reader.ecs_services.items():
            subnet_ids = svc_data.get('SubnetIds', [])
            if subnet_ids:
                # 最初のサブネットに配置
                subnet_id = subnet_ids[0]
                if subnet_id in reader.subnets:
                    self.subnet_resources[subnet_id]['ecs_services'].append((svc_name, svc_data))
        
        # EKS Cluster -> Subnet
        for cluster_name, cluster_data in reader.eks_clusters.items():
            subnet_ids = cluster_data.get('SubnetIds', [])
            if subnet_ids:
                # 最初のサブネットに配置
                subnet_id = subnet_ids[0]
                if subnet_id in reader.subnets:
                    self.subnet_resources[subnet_id]['eks_clusters'].append((cluster_name, cluster_data))
        
        # Lambda -> Subnet (VPC Lambda)
        for func_name, func_data in reader.lambda_functions.items():
            subnet_ids = func_data.get('SubnetIds', [])
            if subnet_ids:
                # 最初のサブネットに配置
                subnet_id = subnet_ids[0]
                if subnet_id in reader.subnets:
                    self.subnet_resources[subnet_id]['lambda'].append((func_name, func_data))
            else:
                # VPC 外の Lambda
                self.external_resources['lambda'].append((func_name, func_data))
        
        # RDS -> Subnet
        for db_id, db_data in reader.rds_instances.items():
            subnet_ids = db_data.get('SubnetIds', [])
            if subnet_ids:
                subnet_id = subnet_ids[0]
                if subnet_id in reader.subnets:
                    self.subnet_resources[subnet_id]['rds'].append((db_id, db_data))
        
        # NAT Gateway -> Subnet
        for nat_id, nat_data in reader.nat_gateways.items():
            subnet_id = nat_data.get('SubnetId') or nat_data.get('Properties', {}).get('SubnetId')
            if subnet_id and subnet_id in reader.subnets:
                self.subnet_resources[subnet_id]['nat_gateways'].append((nat_id, nat_data))
        
        # VPC Endpoint -> Subnet (同じサブネットに複数ある場合は1つだけ)
        subnet_has_endpoint = set()
        for ep_id, ep_data in reader.vpc_endpoints.items():
            subnet_ids = ep_data.get('SubnetIds', []) or ep_data.get('Properties', {}).get('SubnetIds', [])
            for subnet_id in subnet_ids:
                if subnet_id in reader.subnets and subnet_id not in subnet_has_endpoint:
                    self.subnet_resources[subnet_id]['vpc_endpoints'].append((ep_id, ep_data))
                    subnet_has_endpoint.add(subnet_id)
                    break
        
        # Load Balancer -> Subnet or VPC
        for lb_name, lb_data in reader.load_balancers.items():
            subnet_ids = lb_data.get('SubnetIds', []) or lb_data.get('Properties', {}).get('Subnets', [])
            vpc_id = lb_data.get('VpcId')
            
            if subnet_ids:
                # 最初のサブネットに配置
                subnet_id = subnet_ids[0]
                if subnet_id in reader.subnets:
                    self.subnet_resources[subnet_id]['load_balancers'].append((lb_name, lb_data))
                elif vpc_id:
                    self.vpc_resources[vpc_id]['load_balancers'].append((lb_name, lb_data))
                else:
                    self.external_resources['load_balancers'].append((lb_name, lb_data))
            elif vpc_id:
                self.vpc_resources[vpc_id]['load_balancers'].append((lb_name, lb_data))
            else:
                self.external_resources['load_balancers'].append((lb_name, lb_data))
        
        # Target Group -> VPC
        for tg_name, tg_data in reader.target_groups.items():
            vpc_id = tg_data.get('VpcId') or tg_data.get('Properties', {}).get('VpcId')
            if vpc_id and vpc_id in reader.vpcs:
                self.vpc_resources[vpc_id]['target_groups'].append((tg_name, tg_data))
            else:
                self.external_resources['target_groups'].append((tg_name, tg_data))
        
        # 外部リソース
        for bucket_name, bucket_data in reader.s3_buckets.items():
            self.external_resources['s3'].append((bucket_name, bucket_data))
        
        for table_name, table_data in reader.dynamodb_tables.items():
            self.external_resources['dynamodb'].append((table_name, table_data))
        
        for queue_name, queue_data in reader.sqs_queues.items():
            self.external_resources['sqs'].append((queue_name, queue_data))
        
        for topic_name, topic_data in reader.sns_topics.items():
            self.external_resources['sns'].append((topic_name, topic_data))
        
        for fs_id, fs_data in reader.efs_filesystems.items():
            self.external_resources['efs'].append((fs_id, fs_data))
    
    def generate(self, output_dir, output_name='aws-architecture'):
        """アーキテクチャ図を生成"""
        print("\n" + "=" * 80)
        print("Generating Architecture Diagram...")
        print("=" * 80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_name)
        
        # リソースを整理
        self._organize_resources()
        
        reader = self.reader
        
        graph_attr = {
            "fontsize": "14",
            "bgcolor": "white",
            "splines": "ortho",
            "nodesep": "0.6",
            "ranksep": "0.8",
            "pad": "0.5",
            "fontname": "Sans-Serif"
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
                
                # この VPC に属するサブネット
                vpc_subnets = {
                    sid: sdata for sid, sdata in reader.subnets.items()
                    if (sdata.get('VpcId') or sdata.get('Properties', {}).get('VpcId')) == vpc_id
                }
                
                if not vpc_subnets:
                    continue
                
                with Cluster(
                    f"{vpc_name}\n{cidr}",
                    graph_attr={"bgcolor": "#E3F2FD", "style": "rounded", "fontsize": "16"}
                ):
                    # IGW
                    for igw_id, igw_data in reader.internet_gateways.items():
                        if igw_data.get('AttachedVpcId') == vpc_id:
                            igw_name = igw_data.get('Name', igw_id)
                            igw_node = InternetGateway(f"IGW\n{igw_name[:15]}")
                            nodes[igw_id] = igw_node
                    
                    # サブネット（Public と Private で分類）
                    public_subnets = {}
                    private_subnets = {}
                    
                    for subnet_id, subnet_data in vpc_subnets.items():
                        is_public = subnet_data.get('IsPublic', False)
                        if is_public:
                            public_subnets[subnet_id] = subnet_data
                        else:
                            private_subnets[subnet_id] = subnet_data
                    
                    # Public Subnets
                    if public_subnets:
                        with Cluster(
                            "Public Subnets",
                            graph_attr={"bgcolor": "#E8F5E9", "style": "dashed", "fontsize": "14"}
                        ):
                            for subnet_id, subnet_data in public_subnets.items():
                                self._create_subnet_cluster(subnet_id, subnet_data, nodes, is_public=True)
                    
                    # Private Subnets
                    if private_subnets:
                        with Cluster(
                            "Private Subnets",
                            graph_attr={"bgcolor": "#FFF3E0", "style": "dashed", "fontsize": "14"}
                        ):
                            for subnet_id, subnet_data in private_subnets.items():
                                self._create_subnet_cluster(subnet_id, subnet_data, nodes, is_public=False)
                    
                    # VPC レベルの集約リソース
                    vpc_res = self.vpc_resources.get(vpc_id, {})
                    
                    # Target Groups（VPC 内）
                    tg_list = vpc_res.get('target_groups', [])
                    if tg_list:
                        tg_count = len(tg_list)
                        tg_node = ELB(f"Target Groups\n({tg_count})")
                        nodes[f'tg_vpc_{vpc_id}'] = tg_node
                    
                    # Load Balancers（サブネット指定なし）
                    lb_list = vpc_res.get('load_balancers', [])
                    if lb_list:
                        lb_count = len(lb_list)
                        lb_node = ALB(f"Load Balancers\n({lb_count})")
                        nodes[f'lb_vpc_{vpc_id}'] = lb_node
            
            # 外部リソース
            external_count = (
                len(self.external_resources['s3']) +
                len(self.external_resources['dynamodb']) +
                len(self.external_resources['sqs']) +
                len(self.external_resources['sns']) +
                len(self.external_resources['efs']) +
                len(self.external_resources['lambda']) +
                len(self.external_resources['target_groups']) +
                len(self.external_resources['load_balancers'])
            )
            
            if external_count > 0:
                with Cluster(
                    "External Services",
                    graph_attr={"bgcolor": "#F5F5F5", "style": "dashed", "fontsize": "14"}
                ):
                    # S3
                    s3_count = len(self.external_resources['s3'])
                    if s3_count > 0:
                        s3_node = S3(f"S3 Buckets\n({s3_count})")
                        nodes['s3_combined'] = s3_node
                    
                    # DynamoDB
                    ddb_count = len(self.external_resources['dynamodb'])
                    if ddb_count > 0:
                        ddb_node = Dynamodb(f"DynamoDB\n({ddb_count} tables)")
                        nodes['dynamodb_combined'] = ddb_node
                    
                    # SQS
                    sqs_count = len(self.external_resources['sqs'])
                    if sqs_count > 0:
                        sqs_node = SQS(f"SQS Queues\n({sqs_count})")
                        nodes['sqs_combined'] = sqs_node
                    
                    # SNS
                    sns_count = len(self.external_resources['sns'])
                    if sns_count > 0:
                        sns_node = SNS(f"SNS Topics\n({sns_count})")
                        nodes['sns_combined'] = sns_node
                    
                    # EFS
                    efs_count = len(self.external_resources['efs'])
                    if efs_count > 0:
                        efs_node = EFS(f"EFS\n({efs_count})")
                        nodes['efs_combined'] = efs_node
                    
                    # Lambda（VPC 外）
                    lambda_list = self.external_resources['lambda']
                    if lambda_list:
                        lambda_count = len(lambda_list)
                        lambda_node = Lambda(f"Lambda\n({lambda_count} non-VPC)")
                        nodes['lambda_external'] = lambda_node
                    
                    # Target Groups（外部）
                    tg_list = self.external_resources['target_groups']
                    if tg_list:
                        tg_count = len(tg_list)
                        tg_node = ELB(f"Target Groups\n({tg_count} external)")
                        nodes['tg_external'] = tg_node
                    
                    # Load Balancers（外部）
                    lb_list = self.external_resources['load_balancers']
                    if lb_list:
                        lb_count = len(lb_list)
                        lb_node = ALB(f"Load Balancers\n({lb_count} external)")
                        nodes['lb_external'] = lb_node
            
            # 関係を線で接続
            self._draw_relationships(nodes)
        
        print(f"✓ Diagram generated: {output_path}.png")
        return f"{output_path}.png"
    
    def _create_subnet_cluster(self, subnet_id, subnet_data, nodes, is_public=False):
        """サブネットのクラスターを作成"""
        subnet_name = subnet_data.get('Name', subnet_id)
        cidr = subnet_data.get('CidrBlock', '')
        az = subnet_data.get('AvailabilityZone', '')
        az_short = az[-2:] if az else ''
        
        subnet_label = f"{subnet_name[:20]}\n{cidr}\n({az_short})"
        
        # サブネットタイプで背景色を変える
        if is_public:
            bg_color = "#C8E6C9"
            subnet_icon = PublicSubnet
        else:
            bg_color = "#FFE0B2"
            subnet_icon = PrivateSubnet
        
        with Cluster(
            subnet_label,
            graph_attr={"bgcolor": bg_color, "style": "rounded", "fontsize": "12"}
        ):
            # サブネットノード（小さく）
            # subnet_node = subnet_icon(f"")
            # nodes[subnet_id] = subnet_node
            
            resources = self.subnet_resources.get(subnet_id, {})
            
            # NAT Gateway
            for nat_id, nat_data in resources.get('nat_gateways', []):
                nat_name = nat_data.get('Name', nat_id)
                nat_node = NATGateway(f"NAT\n{nat_name[:10]}")
                nodes[nat_id] = nat_node
            
            # Load Balancer
            lb_list = resources.get('load_balancers', [])
            if lb_list:
                lb_count = len(lb_list)
                if lb_count == 1:
                    lb_name = lb_list[0][0]
                    lb_data = lb_list[0][1]
                    lb_type = lb_data.get('LoadBalancerType', 'application')
                    icon = ALB if lb_type == 'application' else NLB
                    lb_node = icon(f"{lb_name[:15]}")
                    nodes[lb_name] = lb_node
                else:
                    lb_node = ALB(f"Load Balancers\n({lb_count})")
                    nodes[f'lb_{subnet_id}'] = lb_node
            
            # VPC Endpoint（1サブネットに1つだけ）
            ep_list = resources.get('vpc_endpoints', [])
            if ep_list:
                ep_id, ep_data = ep_list[0]
                service_name = ep_data.get('ServiceName', '')
                # サービス名を短縮
                short_service = service_name.split('.')[-1] if '.' in service_name else service_name
                ep_node = Endpoint(f"Endpoint\n{short_service[:12]}")
                nodes[ep_id] = ep_node
            
            # EC2
            ec2_list = resources.get('ec2', [])
            if ec2_list:
                ec2_count = len(ec2_list)
                if ec2_count <= 2:
                    for ec2_id, ec2_data in ec2_list:
                        ec2_name = ec2_data.get('Name', ec2_id)
                        ec2_node = EC2(f"{ec2_name[:15]}")
                        nodes[ec2_id] = ec2_node
                else:
                    ec2_node = EC2(f"EC2\n({ec2_count} instances)")
                    nodes[f'ec2_{subnet_id}'] = ec2_node
            
            # ECS Services
            ecs_list = resources.get('ecs_services', [])
            if ecs_list:
                ecs_count = len(ecs_list)
                if ecs_count <= 2:
                    for svc_name, svc_data in ecs_list:
                        svc_node = Fargate(f"{svc_name[:15]}")
                        nodes[svc_name] = svc_node
                else:
                    svc_node = Fargate(f"ECS Services\n({ecs_count})")
                    nodes[f'ecs_{subnet_id}'] = svc_node
            
            # EKS Clusters
            eks_list = resources.get('eks_clusters', [])
            if eks_list:
                eks_count = len(eks_list)
                if eks_count <= 2:
                    for cluster_name, cluster_data in eks_list:
                        eks_node = EKS(f"{cluster_name[:15]}")
                        nodes[cluster_name] = eks_node
                else:
                    eks_node = EKS(f"EKS Clusters\n({eks_count})")
                    nodes[f'eks_{subnet_id}'] = eks_node
            
            # Lambda (VPC)
            lambda_list = resources.get('lambda', [])
            if lambda_list:
                lambda_count = len(lambda_list)
                if lambda_count <= 2:
                    for func_name, func_data in lambda_list:
                        func_node = Lambda(f"{func_name[:15]}")
                        nodes[func_name] = func_node
                else:
                    func_node = Lambda(f"Lambda\n({lambda_count} VPC)")
                    nodes[f'lambda_{subnet_id}'] = func_node
            
            # RDS
            rds_list = resources.get('rds', [])
            if rds_list:
                rds_count = len(rds_list)
                if rds_count <= 2:
                    for db_id, db_data in rds_list:
                        db_node = RDS(f"{db_id[:15]}")
                        nodes[db_id] = db_node
                else:
                    db_node = RDS(f"RDS\n({rds_count} instances)")
                    nodes[f'rds_{subnet_id}'] = db_node
            
            # 何もリソースがない場合は Blank を表示
            has_resources = any([
                resources.get('nat_gateways'),
                resources.get('load_balancers'),
                resources.get('vpc_endpoints'),
                resources.get('ec2'),
                resources.get('ecs_services'),
                resources.get('eks_clusters'),
                resources.get('lambda'),
                resources.get('rds'),
            ])
            
            if not has_resources:
                # 空のサブネットには空白ノードを表示
                blank_node = Blank("")
                nodes[f'blank_{subnet_id}'] = blank_node
    
    def _draw_relationships(self, nodes):
        """リソース間の関係を線で描画"""
        reader = self.reader
        
        edge_colors = {
            'attached_to': ('blue', 'bold', ''),
            'belongs_to': ('gray', 'dashed', ''),
            'in_subnet': ('green', 'solid', ''),
            'in_vpc': ('blue', 'dotted', ''),
            'in_cluster': ('purple', 'solid', ''),
            'routes_to': ('red', 'solid', ''),
            'targets': ('red', 'dashed', 'targets'),
            'triggers': ('orange', 'bold', 'trigger'),
        }
        
        drawn_edges = set()
        
        for source_id, target_id, rel_type, label in reader.relationships:
            # ノードが存在するかチェック
            source_node = nodes.get(source_id)
            target_node = nodes.get(target_id)
            
            if source_node and target_node:
                edge_key = (source_id, target_id, rel_type)
                if edge_key not in drawn_edges:
                    color, style, edge_label = edge_colors.get(rel_type, ('gray', 'solid', ''))
                    source_node >> Edge(color=color, style=style, label=edge_label) >> target_node
                    drawn_edges.add(edge_key)
        
        # IGW と最初のリソースの接続（オプション）
        # for igw_id, igw_data in reader.internet_gateways.items():
        #     vpc_id = igw_data.get('AttachedVpcId')
        #     if igw_id in nodes and vpc_id:
        #         pass
        
        # Load Balancer -> EC2/ECS の接続
        for lb_name, lb_data in reader.load_balancers.items():
            if lb_name in nodes:
                vpc_id = lb_data.get('VpcId')
                if vpc_id:
                    # EC2 に接続
                    for ec2_id, ec2_data in reader.ec2_instances.items():
                        if ec2_data.get('VpcId') == vpc_id and ec2_id in nodes:
                            edge_key = (lb_name, ec2_id, 'lb_ec2')
                            if edge_key not in drawn_edges:
                                nodes[lb_name] >> Edge(color="red", style="dashed") >> nodes[ec2_id]
                                drawn_edges.add(edge_key)
                                break
                    
                    # ECS に接続
                    for svc_name, svc_data in reader.ecs_services.items():
                        if svc_name in nodes:
                            edge_key = (lb_name, svc_name, 'lb_ecs')
                            if edge_key not in drawn_edges:
                                nodes[lb_name] >> Edge(color="red", style="dashed") >> nodes[svc_name]
                                drawn_edges.add(edge_key)
                                break
        
        # Lambda -> DynamoDB
        if 'dynamodb_combined' in nodes:
            for func_name, func_data in reader.lambda_functions.items():
                if func_name in nodes:
                    edge_key = (func_name, 'dynamodb_combined', 'lambda_ddb')
                    if edge_key not in drawn_edges:
                        nodes[func_name] >> Edge(color="orange", style="dotted") >> nodes['dynamodb_combined']
                        drawn_edges.add(edge_key)
                        break
        
        # Lambda -> S3
        if 's3_combined' in nodes:
            for func_name, func_data in reader.lambda_functions.items():
                if func_name in nodes:
                    edge_key = (func_name, 's3_combined', 'lambda_s3')
                    if edge_key not in drawn_edges:
                        nodes[func_name] >> Edge(color="purple", style="dotted") >> nodes['s3_combined']
                        drawn_edges.add(edge_key)
                        break
        
        # SNS -> Lambda トリガー
        if 'sns_combined' in nodes and 'lambda_external' in nodes:
            edge_key = ('sns_combined', 'lambda_external', 'sns_trigger')
            if edge_key not in drawn_edges:
                nodes['sns_combined'] >> Edge(color="orange", style="bold", label="trigger") >> nodes['lambda_external']
                drawn_edges.add(edge_key)
        
        # SQS -> Lambda トリガー
        if 'sqs_combined' in nodes and 'lambda_external' in nodes:
            edge_key = ('sqs_combined', 'lambda_external', 'sqs_trigger')
            if edge_key not in drawn_edges:
                nodes['sqs_combined'] >> Edge(color="orange", style="bold", label="trigger") >> nodes['lambda_external']
                drawn_edges.add(edge_key)

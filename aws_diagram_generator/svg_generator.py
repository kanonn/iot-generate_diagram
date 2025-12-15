# -*- coding: utf-8 -*-
"""
SVG 形式のアーキテクチャ図生成モジュール（完全版）
全てのリソースを表示し、関係線を描画する
CloudFormation からのインポートデータに対応
"""

import os
from collections import defaultdict
import math


class SVGGenerator:
    """SVG 形式のアーキテクチャ図を生成するクラス（完全版）"""
    
    # AWS アイコンの色定義
    ICON_COLORS = {
        # Compute - Orange
        'EC2': '#ED7100',
        'ECS': '#ED7100',
        'EKS': '#ED7100',
        'Lambda': '#ED7100',
        'Fargate': '#ED7100',
        
        # Network - Purple
        'ALB': '#8C4FFF',
        'NLB': '#8C4FFF',
        'ELB': '#8C4FFF',
        'VPC': '#8C4FFF',
        'Subnet': '#7AA116',
        'InternetGateway': '#8C4FFF',
        'NATGateway': '#8C4FFF',
        'VPCEndpoint': '#8C4FFF',
        'TargetGroup': '#8C4FFF',
        
        # Database - Blue
        'RDS': '#3B48CC',
        'DynamoDB': '#3B48CC',
        'ElastiCache': '#3B48CC',
        
        # Storage - Green
        'S3': '#3F8624',
        'EFS': '#3F8624',
        
        # Integration - Pink
        'SQS': '#E7157B',
        'SNS': '#E7157B',
        'APIGateway': '#E7157B',
        
        # Security - Red
        'SecurityGroup': '#DD344C',
        'IAM': '#DD344C',
        
        # Management
        'CloudWatch': '#E7157B',
        
        'default': '#232F3E',
    }
    
    # コンテナの色定義
    CONTAINER_COLORS = {
        'vpc': '#8C4FFF',
        'subnet_private': '#7AA116',
        'subnet_public': '#248814',
        'az': '#147EBA',
        'external': '#232F3E',
    }
    
    def __init__(self, reader):
        self.reader = reader
        self.node_positions = {}  # リソース ID -> (x, y, width, height)
        
        # サブネットごとのリソース（全て個別に保存）
        self.subnet_resources = defaultdict(list)
        
        # VPC ごとのリソース（サブネット未指定）
        self.vpc_resources = defaultdict(list)
        
        # 外部リソース
        self.external_resources = []
    
    def _get_property(self, data, *keys):
        """
        リソースデータからプロパティを取得
        CloudFormation 形式と API 形式の両方に対応
        """
        # 直接のキーを試す
        for key in keys:
            if key in data:
                return data[key]
        
        # Properties 内を試す
        props = data.get('Properties', {})
        if props:
            for key in keys:
                if key in props:
                    return props[key]
        
        return None
    
    def _get_name(self, res_id, res_data):
        """リソース名を取得"""
        # Name タグから
        name = self._get_property(res_data, 'Name')
        if name:
            return name
        
        # Tags から
        tags = self._get_property(res_data, 'Tags')
        if tags:
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, dict) and tag.get('Key') == 'Name':
                        return tag.get('Value', res_id)
            elif isinstance(tags, dict):
                return tags.get('Name', res_id)
        
        return res_id
    
    def _organize_all_resources(self):
        """全てのリソースを整理（聚合なし）"""
        reader = self.reader
        
        print(f"  Processing VPCs: {len(reader.vpcs)}")
        print(f"  Processing Subnets: {len(reader.subnets)}")
        print(f"  Processing EC2 Instances: {len(reader.ec2_instances)}")
        print(f"  Processing ECS Services: {len(reader.ecs_services)}")
        print(f"  Processing EKS Clusters: {len(reader.eks_clusters)}")
        print(f"  Processing Lambda Functions: {len(reader.lambda_functions)}")
        print(f"  Processing RDS Instances: {len(reader.rds_instances)}")
        print(f"  Processing Load Balancers: {len(reader.load_balancers)}")
        print(f"  Processing Target Groups: {len(reader.target_groups)}")
        print(f"  Processing NAT Gateways: {len(reader.nat_gateways)}")
        print(f"  Processing VPC Endpoints: {len(reader.vpc_endpoints)}")
        print(f"  Processing Internet Gateways: {len(reader.internet_gateways)}")
        print(f"  Processing S3 Buckets: {len(reader.s3_buckets)}")
        print(f"  Processing DynamoDB Tables: {len(reader.dynamodb_tables)}")
        print(f"  Processing SQS Queues: {len(reader.sqs_queues)}")
        print(f"  Processing SNS Topics: {len(reader.sns_topics)}")
        print(f"  Processing EFS Filesystems: {len(reader.efs_filesystems)}")
        print(f"  Processing Security Groups: {len(reader.security_groups)}")
        
        # サブネット ID -> VPC ID のマッピングを構築
        subnet_to_vpc = {}
        for subnet_id, subnet_data in reader.subnets.items():
            vpc_id = self._get_property(subnet_data, 'VpcId')
            if vpc_id:
                subnet_to_vpc[subnet_id] = vpc_id
        
        # EC2 -> Subnet
        for ec2_id, ec2_data in reader.ec2_instances.items():
            subnet_id = self._get_property(ec2_data, 'SubnetId')
            name = self._get_name(ec2_id, ec2_data)
            
            if subnet_id and subnet_id in reader.subnets:
                self.subnet_resources[subnet_id].append(('EC2', ec2_id, name, ec2_data))
            else:
                # VPC に配置
                vpc_id = self._get_property(ec2_data, 'VpcId')
                if vpc_id and vpc_id in reader.vpcs:
                    self.vpc_resources[vpc_id].append(('EC2', ec2_id, name, ec2_data))
                else:
                    # どこにも属さない場合は最初の VPC に
                    if reader.vpcs:
                        first_vpc = list(reader.vpcs.keys())[0]
                        self.vpc_resources[first_vpc].append(('EC2', ec2_id, name, ec2_data))
        
        # ECS Service -> Subnet
        for svc_name, svc_data in reader.ecs_services.items():
            subnet_ids = self._get_property(svc_data, 'SubnetIds', 'Subnets') or []
            name = self._get_name(svc_name, svc_data)
            
            placed = False
            for subnet_id in subnet_ids:
                if subnet_id in reader.subnets:
                    self.subnet_resources[subnet_id].append(('Fargate', svc_name, name, svc_data))
                    placed = True
                    break
            
            if not placed:
                vpc_id = self._get_property(svc_data, 'VpcId')
                if vpc_id and vpc_id in reader.vpcs:
                    self.vpc_resources[vpc_id].append(('Fargate', svc_name, name, svc_data))
                elif reader.vpcs:
                    first_vpc = list(reader.vpcs.keys())[0]
                    self.vpc_resources[first_vpc].append(('Fargate', svc_name, name, svc_data))
        
        # EKS Cluster -> Subnet
        for cluster_name, cluster_data in reader.eks_clusters.items():
            subnet_ids = self._get_property(cluster_data, 'SubnetIds', 'Subnets') or []
            name = self._get_name(cluster_name, cluster_data)
            
            placed = False
            for subnet_id in subnet_ids:
                if subnet_id in reader.subnets:
                    self.subnet_resources[subnet_id].append(('EKS', cluster_name, name, cluster_data))
                    placed = True
                    break
            
            if not placed:
                vpc_id = self._get_property(cluster_data, 'VpcId')
                if vpc_id and vpc_id in reader.vpcs:
                    self.vpc_resources[vpc_id].append(('EKS', cluster_name, name, cluster_data))
                elif reader.vpcs:
                    first_vpc = list(reader.vpcs.keys())[0]
                    self.vpc_resources[first_vpc].append(('EKS', cluster_name, name, cluster_data))
        
        # Lambda -> Subnet (VPC Lambda) or External
        for func_name, func_data in reader.lambda_functions.items():
            subnet_ids = self._get_property(func_data, 'SubnetIds', 'VpcConfig.SubnetIds') or []
            
            # VpcConfig から SubnetIds を取得
            vpc_config = self._get_property(func_data, 'VpcConfig')
            if vpc_config and isinstance(vpc_config, dict):
                subnet_ids = vpc_config.get('SubnetIds', []) or subnet_ids
            
            name = self._get_name(func_name, func_data)
            
            placed = False
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append(('Lambda', func_name, name, func_data))
                        placed = True
                        break
            
            if not placed:
                # VPC 外の Lambda
                self.external_resources.append(('Lambda', func_name, name, func_data))
        
        # RDS -> Subnet
        for db_id, db_data in reader.rds_instances.items():
            subnet_ids = self._get_property(db_data, 'SubnetIds', 'DBSubnetGroupName') or []
            name = self._get_name(db_id, db_data)
            
            placed = False
            if isinstance(subnet_ids, list):
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append(('RDS', db_id, name, db_data))
                        placed = True
                        break
            
            if not placed:
                vpc_id = self._get_property(db_data, 'VpcId')
                if vpc_id and vpc_id in reader.vpcs:
                    self.vpc_resources[vpc_id].append(('RDS', db_id, name, db_data))
                elif reader.vpcs:
                    first_vpc = list(reader.vpcs.keys())[0]
                    self.vpc_resources[first_vpc].append(('RDS', db_id, name, db_data))
        
        # ElastiCache -> VPC
        for cache_id, cache_data in reader.elasticache_clusters.items():
            name = self._get_name(cache_id, cache_data)
            vpc_id = self._get_property(cache_data, 'VpcId')
            
            if vpc_id and vpc_id in reader.vpcs:
                self.vpc_resources[vpc_id].append(('ElastiCache', cache_id, name, cache_data))
            elif reader.vpcs:
                first_vpc = list(reader.vpcs.keys())[0]
                self.vpc_resources[first_vpc].append(('ElastiCache', cache_id, name, cache_data))
        
        # NAT Gateway -> Subnet
        for nat_id, nat_data in reader.nat_gateways.items():
            subnet_id = self._get_property(nat_data, 'SubnetId')
            name = self._get_name(nat_id, nat_data)
            
            if subnet_id and subnet_id in reader.subnets:
                self.subnet_resources[subnet_id].append(('NATGateway', nat_id, name, nat_data))
            elif reader.vpcs:
                first_vpc = list(reader.vpcs.keys())[0]
                self.vpc_resources[first_vpc].append(('NATGateway', nat_id, name, nat_data))
        
        # VPC Endpoint -> Subnet or VPC
        for ep_id, ep_data in reader.vpc_endpoints.items():
            subnet_ids = self._get_property(ep_data, 'SubnetIds') or []
            service_name = self._get_property(ep_data, 'ServiceName') or ep_id
            name = service_name.split('.')[-1] if '.' in service_name else service_name
            
            placed = False
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append(('VPCEndpoint', ep_id, name, ep_data))
                        placed = True
                        break
            
            if not placed:
                vpc_id = self._get_property(ep_data, 'VpcId')
                if vpc_id and vpc_id in reader.vpcs:
                    self.vpc_resources[vpc_id].append(('VPCEndpoint', ep_id, name, ep_data))
                elif reader.vpcs:
                    first_vpc = list(reader.vpcs.keys())[0]
                    self.vpc_resources[first_vpc].append(('VPCEndpoint', ep_id, name, ep_data))
        
        # Load Balancer -> Subnet or VPC
        for lb_name, lb_data in reader.load_balancers.items():
            subnet_ids = self._get_property(lb_data, 'SubnetIds', 'Subnets') or []
            lb_type = self._get_property(lb_data, 'LoadBalancerType', 'Type') or 'application'
            icon_type = 'NLB' if 'network' in str(lb_type).lower() else 'ALB'
            name = self._get_name(lb_name, lb_data)
            
            placed = False
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append((icon_type, lb_name, name, lb_data))
                        placed = True
                        break
            
            if not placed:
                vpc_id = self._get_property(lb_data, 'VpcId')
                if vpc_id and vpc_id in reader.vpcs:
                    self.vpc_resources[vpc_id].append((icon_type, lb_name, name, lb_data))
                elif reader.vpcs:
                    first_vpc = list(reader.vpcs.keys())[0]
                    self.vpc_resources[first_vpc].append((icon_type, lb_name, name, lb_data))
                else:
                    self.external_resources.append((icon_type, lb_name, name, lb_data))
        
        # Target Group -> VPC
        for tg_name, tg_data in reader.target_groups.items():
            vpc_id = self._get_property(tg_data, 'VpcId')
            name = self._get_name(tg_name, tg_data)
            
            if vpc_id and vpc_id in reader.vpcs:
                self.vpc_resources[vpc_id].append(('TargetGroup', tg_name, name, tg_data))
            elif reader.vpcs:
                first_vpc = list(reader.vpcs.keys())[0]
                self.vpc_resources[first_vpc].append(('TargetGroup', tg_name, name, tg_data))
            else:
                self.external_resources.append(('TargetGroup', tg_name, name, tg_data))
        
        # Security Groups -> VPC（VPC ごとに集約表示）
        sg_by_vpc = {}
        for sg_id, sg_data in reader.security_groups.items():
            vpc_id = self._get_property(sg_data, 'VpcId')
            if vpc_id:
                if vpc_id not in sg_by_vpc:
                    sg_by_vpc[vpc_id] = []
                sg_by_vpc[vpc_id].append(sg_id)
        
        for vpc_id, sg_list in sg_by_vpc.items():
            if vpc_id in reader.vpcs:
                count = len(sg_list)
                self.vpc_resources[vpc_id].append(('SecurityGroup', f'__sg_{vpc_id}__', f'Security Groups ({count})', {}))
        
        # Internet Gateways -> VPC
        for igw_id, igw_data in reader.internet_gateways.items():
            vpc_id = self._get_property(igw_data, 'AttachedVpcId', 'VpcId')
            name = self._get_name(igw_id, igw_data)
            
            if vpc_id and vpc_id in reader.vpcs:
                self.vpc_resources[vpc_id].append(('InternetGateway', igw_id, name, igw_data))
            elif reader.vpcs:
                first_vpc = list(reader.vpcs.keys())[0]
                self.vpc_resources[first_vpc].append(('InternetGateway', igw_id, name, igw_data))
        
        # 外部リソース（数が多いものは集約表示）
        # S3 - 集約
        if reader.s3_buckets:
            count = len(reader.s3_buckets)
            first_name = list(reader.s3_buckets.keys())[0]
            self.external_resources.append(('S3', '__s3_aggregated__', f'S3 Buckets ({count})', {}))
        
        # DynamoDB - 個別表示
        for table_name, table_data in reader.dynamodb_tables.items():
            name = self._get_name(table_name, table_data)
            self.external_resources.append(('DynamoDB', table_name, name, table_data))
        
        # SQS - 個別表示
        for queue_name, queue_data in reader.sqs_queues.items():
            name = self._get_name(queue_name, queue_data)
            self.external_resources.append(('SQS', queue_name, name, queue_data))
        
        # SNS - 個別表示
        for topic_name, topic_data in reader.sns_topics.items():
            name = self._get_name(topic_name, topic_data)
            self.external_resources.append(('SNS', topic_name, name, topic_data))
        
        # EFS - 集約
        if reader.efs_filesystems:
            count = len(reader.efs_filesystems)
            self.external_resources.append(('EFS', '__efs_aggregated__', f'EFS ({count})', {}))
        
        # IAM Roles - 集約
        if reader.iam_roles:
            count = len(reader.iam_roles)
            self.external_resources.append(('IAM', '__iam_aggregated__', f'IAM Roles ({count})', {}))
        
        # 統計を表示
        total_in_subnet = sum(len(v) for v in self.subnet_resources.values())
        total_in_vpc = sum(len(v) for v in self.vpc_resources.values())
        total_external = len(self.external_resources)
        print(f"\n  Resources organized:")
        print(f"    In Subnets: {total_in_subnet}")
        print(f"    In VPCs (no subnet): {total_in_vpc}")
        print(f"    External: {total_external}")
        print(f"    Total: {total_in_subnet + total_in_vpc + total_external}")
    
    def _create_icon_svg(self, icon_type, x, y, size=48, label='', res_id=''):
        """AWS スタイルのアイコン SVG を作成"""
        color = self.ICON_COLORS.get(icon_type, self.ICON_COLORS['default'])
        
        # ラベルを短縮
        short_label = str(label)[:20] if label else ''
        
        # ノード位置を記録
        self.node_positions[res_id] = (x + size/2, y + size/2, size, size)
        
        icon_svg = f'''    <g id="{res_id}">
      <rect x="{x}" y="{y}" width="{size}" height="{size}" rx="5" ry="5" 
            fill="{color}" stroke="white" stroke-width="2"/>
      <text x="{x + size/2}" y="{y + size/2 + 4}" 
            text-anchor="middle" fill="white" font-size="10" font-weight="bold">
        {self._get_icon_symbol(icon_type)}
      </text>
      <text x="{x + size/2}" y="{y + size + 14}" 
            text-anchor="middle" fill="#232F3E" font-size="9">
        {short_label}
      </text>
    </g>
'''
        return icon_svg
    
    def _get_icon_symbol(self, icon_type):
        """アイコンのシンボルを取得"""
        symbols = {
            'EC2': 'EC2',
            'ECS': 'ECS',
            'EKS': 'EKS',
            'Lambda': 'λ',
            'Fargate': 'Fg',
            'ALB': 'ALB',
            'NLB': 'NLB',
            'ELB': 'ELB',
            'RDS': 'RDS',
            'DynamoDB': 'DDB',
            'ElastiCache': 'EC',
            'S3': 'S3',
            'EFS': 'EFS',
            'SQS': 'SQS',
            'SNS': 'SNS',
            'VPCEndpoint': 'EP',
            'NATGateway': 'NAT',
            'InternetGateway': 'IGW',
            'TargetGroup': 'TG',
            'SecurityGroup': 'SG',
            'APIGateway': 'API',
            'IAM': 'IAM',
        }
        return symbols.get(icon_type, icon_type[:3])
    
    def _create_container_svg(self, x, y, width, height, label, color, dashed=False):
        """コンテナ（グループ枠）の SVG を作成"""
        dash_style = 'stroke-dasharray="8,4"' if dashed else ''
        short_label = str(label)[:40] if label else ''
        
        return f'''    <g>
      <rect x="{x}" y="{y}" width="{width}" height="{height}" 
            fill="none" stroke="{color}" stroke-width="2" rx="5" ry="5" {dash_style}/>
      <text x="{x + 10}" y="{y + 18}" 
            fill="{color}" font-size="12" font-weight="bold" text-decoration="underline">
        {short_label}
      </text>
    </g>
'''
    
    def _create_edge_svg(self, source_id, target_id, color='#232F3E', dashed=False):
        """接続線の SVG を作成"""
        if source_id not in self.node_positions or target_id not in self.node_positions:
            return ''
        
        src_x, src_y, src_w, src_h = self.node_positions[source_id]
        dst_x, dst_y, dst_w, dst_h = self.node_positions[target_id]
        
        dash_style = 'stroke-dasharray="5,3"' if dashed else ''
        
        return f'''    <line x1="{src_x}" y1="{src_y}" x2="{dst_x}" y2="{dst_y}" 
          stroke="{color}" stroke-width="1.5" {dash_style} marker-end="url(#arrowhead)"/>
'''
    
    def generate(self, output_dir, output_name='aws-architecture'):
        """SVG アーキテクチャ図を生成"""
        print("\n" + "=" * 80)
        print("Generating SVG Architecture Diagram (Full Version)...")
        print("=" * 80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_name}.svg")
        
        # リソースを整理
        self._organize_all_resources()
        
        # レイアウトを計算
        layout = self._calculate_layout()
        
        # SVG を構築
        svg_content = self._build_svg(layout)
        
        # ファイルに書き込み
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f"\n✓ SVG diagram generated: {output_path}")
        print(f"  Total nodes: {len(self.node_positions)}")
        return output_path
    
    def _calculate_layout(self):
        """レイアウトを計算"""
        reader = self.reader
        
        # 各サブネットのリソース数を計算
        max_resources_per_subnet = 1
        for subnet_id, resources in self.subnet_resources.items():
            max_resources_per_subnet = max(max_resources_per_subnet, len(resources))
        
        # 各 VPC のリソース数
        max_resources_per_vpc = 1
        for vpc_id, resources in self.vpc_resources.items():
            max_resources_per_vpc = max(max_resources_per_vpc, len(resources))
        
        # 列数（1サブネット内）
        cols_per_subnet = min(5, max(1, int(math.ceil(math.sqrt(max_resources_per_subnet)))))
        
        # サブネット幅
        subnet_width = cols_per_subnet * 70 + 40
        subnet_width = max(180, subnet_width)
        
        # VPC ごとのサブネット数
        vpc_subnet_count = defaultdict(int)
        for subnet_id, subnet_data in reader.subnets.items():
            vpc_id = self._get_property(subnet_data, 'VpcId')
            if vpc_id:
                vpc_subnet_count[vpc_id] += 1
        
        max_subnets_per_vpc = max(vpc_subnet_count.values()) if vpc_subnet_count else 1
        
        # VPC 幅
        vpc_width = max_subnets_per_vpc * (subnet_width + 20) + 80
        vpc_width = max(500, vpc_width)
        
        # VPC リソースの列数
        vpc_res_cols = min(8, max(1, int(math.ceil(math.sqrt(max_resources_per_vpc)))))
        vpc_res_width = vpc_res_cols * 70 + 40
        vpc_width = max(vpc_width, vpc_res_width + 60)
        
        # 外部リソースの列数
        external_cols = min(6, max(1, int(math.ceil(math.sqrt(len(self.external_resources))))))
        external_width = external_cols * 70 + 40
        
        # 全体幅
        total_width = vpc_width + external_width + 200
        
        # 高さ計算
        rows_per_subnet = max(1, int(math.ceil(max_resources_per_subnet / cols_per_subnet)))
        subnet_height = rows_per_subnet * 70 + 60
        subnet_height = max(140, subnet_height)
        
        # VPC リソースの高さ
        vpc_res_rows = max(1, int(math.ceil(max_resources_per_vpc / vpc_res_cols)))
        vpc_res_height = vpc_res_rows * 70 + 40
        
        vpc_height = subnet_height + vpc_res_height + 100
        
        total_height = len(reader.vpcs) * (vpc_height + 40) + 100
        
        # 外部リソースの高さ
        external_rows = int(math.ceil(len(self.external_resources) / external_cols))
        external_height = external_rows * 70 + 60
        total_height = max(total_height, external_height + 100)
        
        return {
            'total_width': total_width,
            'total_height': total_height,
            'vpc_width': vpc_width,
            'vpc_height': vpc_height,
            'subnet_width': subnet_width,
            'subnet_height': subnet_height,
            'cols_per_subnet': cols_per_subnet,
            'vpc_res_cols': vpc_res_cols,
            'vpc_res_height': vpc_res_height,
            'external_width': external_width,
            'external_cols': external_cols,
        }
    
    def _build_svg(self, layout):
        """SVG コンテンツを構築"""
        reader = self.reader
        svg_parts = []
        
        width = layout['total_width']
        height = layout['total_height']
        
        # SVG ヘッダー
        svg_parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{width}" height="{height}" 
     viewBox="0 0 {width} {height}"
     style="background-color: white; font-family: Arial, sans-serif;">
  
  <!-- Arrow marker -->
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" 
            refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#232F3E"/>
    </marker>
    <!-- 細いグリッド（20px間隔） -->
    <pattern id="smallGrid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e8e8e8" stroke-width="0.5"/>
    </pattern>
    <!-- 太いグリッド（80px間隔 = 20px x 4） -->
    <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
      <rect width="80" height="80" fill="url(#smallGrid)"/>
      <path d="M 80 0 L 0 0 0 80" fill="none" stroke="#d0d0d0" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid)"/>
  
  <!-- Title -->
  <text x="20" y="30" fill="#232F3E" font-size="16" font-weight="bold">
    AWS Architecture Diagram
  </text>
''')
        
        # VPC ごとに描画
        vpc_y = 50
        for vpc_id, vpc_data in reader.vpcs.items():
            vpc_name = self._get_name(vpc_id, vpc_data)
            cidr = self._get_property(vpc_data, 'CidrBlock') or ''
            
            # この VPC のサブネットを取得
            vpc_subnets = {}
            for sid, sdata in reader.subnets.items():
                subnet_vpc_id = self._get_property(sdata, 'VpcId')
                if subnet_vpc_id == vpc_id:
                    vpc_subnets[sid] = sdata
            
            # VPC の高さを計算
            num_subnets = len(vpc_subnets)
            vpc_res_count = len(self.vpc_resources.get(vpc_id, []))
            vpc_res_rows = int(math.ceil(vpc_res_count / layout['vpc_res_cols'])) if vpc_res_count else 0
            actual_vpc_height = layout['subnet_height'] + vpc_res_rows * 70 + 120
            actual_vpc_height = max(layout['vpc_height'], actual_vpc_height)
            
            # VPC コンテナ
            svg_parts.append(self._create_container_svg(
                20, vpc_y, layout['vpc_width'], actual_vpc_height,
                f"{vpc_name} ({cidr})",
                self.CONTAINER_COLORS['vpc']
            ))
            
            # サブネットを描画
            subnet_x = 40
            subnet_y = vpc_y + 40
            
            for subnet_id, subnet_data in vpc_subnets.items():
                subnet_name = self._get_name(subnet_id, subnet_data)
                is_public = self._get_property(subnet_data, 'IsPublic') or False
                az = self._get_property(subnet_data, 'AvailabilityZone') or ''
                
                color = self.CONTAINER_COLORS['subnet_public' if is_public else 'subnet_private']
                
                # サブネット内のリソース数に基づいて高さを計算
                resources = self.subnet_resources.get(subnet_id, [])
                rows = int(math.ceil(len(resources) / layout['cols_per_subnet'])) if resources else 1
                actual_subnet_height = rows * 70 + 60
                actual_subnet_height = max(layout['subnet_height'], actual_subnet_height)
                
                # サブネットコンテナ
                subnet_label = f"{subnet_name[:25]}"
                if az:
                    subnet_label += f" ({az[-2:]})"
                
                svg_parts.append(self._create_container_svg(
                    subnet_x, subnet_y, layout['subnet_width'], actual_subnet_height,
                    subnet_label,
                    color
                ))
                
                # サブネット内のリソースを描画
                res_x = subnet_x + 20
                res_y = subnet_y + 35
                col = 0
                
                for icon_type, res_id, res_name, res_data in resources:
                    svg_parts.append(self._create_icon_svg(
                        icon_type, res_x, res_y, 48, res_name, res_id
                    ))
                    
                    col += 1
                    res_x += 65
                    if col >= layout['cols_per_subnet']:
                        col = 0
                        res_x = subnet_x + 20
                        res_y += 70
                
                subnet_x += layout['subnet_width'] + 20
                if subnet_x + layout['subnet_width'] > layout['vpc_width']:
                    subnet_x = 40
                    subnet_y += actual_subnet_height + 20
            
            # VPC レベルのリソースを描画（サブネット未指定）
            vpc_res_list = self.vpc_resources.get(vpc_id, [])
            if vpc_res_list:
                vpc_res_y = subnet_y + layout['subnet_height'] + 20
                vpc_res_x = 40
                col = 0
                
                svg_parts.append(f'''    <text x="40" y="{vpc_res_y - 5}" fill="#8C4FFF" font-size="11">
      VPC Resources ({len(vpc_res_list)} items)
    </text>
''')
                
                for icon_type, res_id, res_name, res_data in vpc_res_list:
                    svg_parts.append(self._create_icon_svg(
                        icon_type, vpc_res_x, vpc_res_y, 48, res_name, res_id
                    ))
                    
                    col += 1
                    vpc_res_x += 65
                    if col >= layout['vpc_res_cols']:
                        col = 0
                        vpc_res_x = 40
                        vpc_res_y += 70
            
            vpc_y += actual_vpc_height + 30
        
        # 外部リソースを右側に描画
        external_x = layout['vpc_width'] + 60
        external_y = 50
        
        if self.external_resources:
            external_height = int(math.ceil(len(self.external_resources) / layout['external_cols'])) * 70 + 60
            
            svg_parts.append(self._create_container_svg(
                external_x, external_y,
                layout['external_width'],
                external_height,
                f"External Resources ({len(self.external_resources)} items)",
                self.CONTAINER_COLORS['external'],
                dashed=True
            ))
            
            res_x = external_x + 20
            res_y = external_y + 35
            col = 0
            
            for icon_type, res_id, res_name, res_data in self.external_resources:
                svg_parts.append(self._create_icon_svg(
                    icon_type, res_x, res_y, 48, res_name, res_id
                ))
                
                col += 1
                res_x += 65
                if col >= layout['external_cols']:
                    col = 0
                    res_x = external_x + 20
                    res_y += 70
        
        # 接続線を描画
        svg_parts.append('\n  <!-- Connections -->\n')
        svg_parts.append(self._draw_all_connections())
        
        # SVG フッター
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)
    
    def _draw_all_connections(self):
        """全ての接続線を描画"""
        lines = []
        reader = self.reader
        drawn_edges = set()
        
        # reader.relationships から接続線を描画
        for rel in reader.relationships:
            if len(rel) >= 3:
                source_id, target_id, rel_type = rel[0], rel[1], rel[2]
                
                if source_id in self.node_positions and target_id in self.node_positions:
                    edge_key = (source_id, target_id)
                    if edge_key not in drawn_edges:
                        color = '#232F3E'
                        dashed = False
                        
                        if rel_type == 'attached_to':
                            color = '#3B48CC'
                        elif rel_type == 'targets':
                            color = '#DD344C'
                            dashed = True
                        elif rel_type == 'triggers':
                            color = '#ED7100'
                        elif rel_type == 'routes_to':
                            color = '#E7157B'
                        elif rel_type == 'in_subnet':
                            color = '#7AA116'
                            dashed = True
                        
                        lines.append(self._create_edge_svg(source_id, target_id, color, dashed))
                        drawn_edges.add(edge_key)
        
        return ''.join(lines)

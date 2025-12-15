# -*- coding: utf-8 -*-
"""
SVG 形式のアーキテクチャ図生成モジュール（完全版）
全てのリソースを表示し、関係線を描画する
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
        self.all_nodes = []  # 全てのノード情報
        self.all_edges = []  # 全てのエッジ情報
        
        # サブネットごとのリソース（全て個別に保存）
        self.subnet_resources = defaultdict(list)
        
        # VPC ごとのリソース（サブネット未指定）
        self.vpc_resources = defaultdict(list)
        
        # 外部リソース
        self.external_resources = []
    
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
        
        # EC2 -> Subnet
        for ec2_id, ec2_data in reader.ec2_instances.items():
            subnet_id = ec2_data.get('SubnetId') or ec2_data.get('Properties', {}).get('SubnetId')
            name = ec2_data.get('Name', ec2_id)
            if subnet_id and subnet_id in reader.subnets:
                self.subnet_resources[subnet_id].append(('EC2', ec2_id, name, ec2_data))
            else:
                # サブネット不明の場合は VPC に
                vpc_id = ec2_data.get('VpcId')
                if vpc_id:
                    self.vpc_resources[vpc_id].append(('EC2', ec2_id, name, ec2_data))
        
        # ECS Service -> Subnet
        for svc_name, svc_data in reader.ecs_services.items():
            subnet_ids = svc_data.get('SubnetIds', [])
            name = svc_data.get('Name', svc_name)
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append(('Fargate', svc_name, name, svc_data))
                        break
            else:
                vpc_id = svc_data.get('VpcId')
                if vpc_id:
                    self.vpc_resources[vpc_id].append(('Fargate', svc_name, name, svc_data))
        
        # EKS Cluster -> Subnet
        for cluster_name, cluster_data in reader.eks_clusters.items():
            subnet_ids = cluster_data.get('SubnetIds', [])
            name = cluster_data.get('Name', cluster_name)
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append(('EKS', cluster_name, name, cluster_data))
                        break
            else:
                vpc_id = cluster_data.get('VpcId')
                if vpc_id:
                    self.vpc_resources[vpc_id].append(('EKS', cluster_name, name, cluster_data))
        
        # Lambda -> Subnet (VPC Lambda) or External
        for func_name, func_data in reader.lambda_functions.items():
            subnet_ids = func_data.get('SubnetIds', [])
            name = func_data.get('Name', func_name)
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append(('Lambda', func_name, name, func_data))
                        break
            else:
                # VPC 外の Lambda
                self.external_resources.append(('Lambda', func_name, name, func_data))
        
        # RDS -> Subnet
        for db_id, db_data in reader.rds_instances.items():
            subnet_ids = db_data.get('SubnetIds', [])
            name = db_data.get('Name', db_id)
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append(('RDS', db_id, name, db_data))
                        break
            else:
                vpc_id = db_data.get('VpcId')
                if vpc_id:
                    self.vpc_resources[vpc_id].append(('RDS', db_id, name, db_data))
        
        # ElastiCache -> Subnet
        for cache_id, cache_data in reader.elasticache_clusters.items():
            subnet_ids = cache_data.get('SubnetIds', [])
            name = cache_data.get('Name', cache_id)
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append(('ElastiCache', cache_id, name, cache_data))
                        break
            else:
                vpc_id = cache_data.get('VpcId')
                if vpc_id:
                    self.vpc_resources[vpc_id].append(('ElastiCache', cache_id, name, cache_data))
        
        # NAT Gateway -> Subnet
        for nat_id, nat_data in reader.nat_gateways.items():
            subnet_id = nat_data.get('SubnetId') or nat_data.get('Properties', {}).get('SubnetId')
            name = nat_data.get('Name', nat_id)
            if subnet_id and subnet_id in reader.subnets:
                self.subnet_resources[subnet_id].append(('NATGateway', nat_id, name, nat_data))
        
        # VPC Endpoint -> Subnet（全て表示）
        for ep_id, ep_data in reader.vpc_endpoints.items():
            subnet_ids = ep_data.get('SubnetIds', []) or ep_data.get('Properties', {}).get('SubnetIds', [])
            service_name = ep_data.get('ServiceName', ep_id)
            name = service_name.split('.')[-1] if '.' in service_name else service_name
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append(('VPCEndpoint', ep_id, name, ep_data))
                        break
            else:
                vpc_id = ep_data.get('VpcId')
                if vpc_id:
                    self.vpc_resources[vpc_id].append(('VPCEndpoint', ep_id, name, ep_data))
        
        # Load Balancer -> Subnet（全て表示）
        for lb_name, lb_data in reader.load_balancers.items():
            subnet_ids = lb_data.get('SubnetIds', []) or lb_data.get('Properties', {}).get('Subnets', [])
            lb_type = lb_data.get('LoadBalancerType', lb_data.get('Properties', {}).get('Type', 'application'))
            icon_type = 'NLB' if 'network' in str(lb_type).lower() else 'ALB'
            name = lb_data.get('Name', lb_name)
            
            if subnet_ids:
                for subnet_id in subnet_ids:
                    if subnet_id in reader.subnets:
                        self.subnet_resources[subnet_id].append((icon_type, lb_name, name, lb_data))
                        break
            else:
                vpc_id = lb_data.get('VpcId')
                if vpc_id:
                    self.vpc_resources[vpc_id].append((icon_type, lb_name, name, lb_data))
                else:
                    self.external_resources.append((icon_type, lb_name, name, lb_data))
        
        # Target Group -> VPC（全て表示）
        for tg_name, tg_data in reader.target_groups.items():
            vpc_id = tg_data.get('VpcId') or tg_data.get('Properties', {}).get('VpcId')
            name = tg_data.get('Name', tg_name)
            if vpc_id and vpc_id in reader.vpcs:
                self.vpc_resources[vpc_id].append(('TargetGroup', tg_name, name, tg_data))
            else:
                self.external_resources.append(('TargetGroup', tg_name, name, tg_data))
        
        # 外部リソース（全て表示）
        for bucket_name, bucket_data in reader.s3_buckets.items():
            name = bucket_data.get('Name', bucket_name)
            self.external_resources.append(('S3', bucket_name, name, bucket_data))
        
        for table_name, table_data in reader.dynamodb_tables.items():
            name = table_data.get('Name', table_name)
            self.external_resources.append(('DynamoDB', table_name, name, table_data))
        
        for queue_name, queue_data in reader.sqs_queues.items():
            name = queue_data.get('Name', queue_name)
            self.external_resources.append(('SQS', queue_name, name, queue_data))
        
        for topic_name, topic_data in reader.sns_topics.items():
            name = topic_data.get('Name', topic_name)
            self.external_resources.append(('SNS', topic_name, name, topic_data))
        
        for fs_id, fs_data in reader.efs_filesystems.items():
            name = fs_data.get('Name', fs_id)
            self.external_resources.append(('EFS', fs_id, name, fs_data))
        
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
        short_label = label[:20] if len(label) > 20 else label
        
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
        }
        return symbols.get(icon_type, icon_type[:3])
    
    def _create_container_svg(self, x, y, width, height, label, color, dashed=False):
        """コンテナ（グループ枠）の SVG を作成"""
        dash_style = 'stroke-dasharray="8,4"' if dashed else ''
        
        return f'''    <g>
      <rect x="{x}" y="{y}" width="{width}" height="{height}" 
            fill="none" stroke="{color}" stroke-width="2" rx="5" ry="5" {dash_style}/>
      <text x="{x + 10}" y="{y + 18}" 
            fill="{color}" font-size="12" font-weight="bold" text-decoration="underline">
        {label}
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
        
        # 列数（1サブネット内）
        cols_per_subnet = min(4, max(1, int(math.ceil(math.sqrt(max_resources_per_subnet)))))
        
        # サブネット幅
        subnet_width = cols_per_subnet * 70 + 40
        subnet_width = max(160, subnet_width)
        
        # VPC ごとのサブネット数
        vpc_subnet_count = defaultdict(int)
        for subnet_id, subnet_data in reader.subnets.items():
            vpc_id = subnet_data.get('VpcId') or subnet_data.get('Properties', {}).get('VpcId')
            if vpc_id:
                vpc_subnet_count[vpc_id] += 1
        
        max_subnets_per_vpc = max(vpc_subnet_count.values()) if vpc_subnet_count else 1
        
        # VPC 幅
        vpc_width = max_subnets_per_vpc * (subnet_width + 20) + 60
        vpc_width = max(400, vpc_width)
        
        # 外部リソースの列数
        external_cols = min(6, max(1, int(math.ceil(math.sqrt(len(self.external_resources))))))
        external_width = external_cols * 70 + 40
        
        # 全体幅
        total_width = vpc_width + external_width + 200
        
        # 高さ計算
        rows_per_subnet = max(1, int(math.ceil(max_resources_per_subnet / cols_per_subnet)))
        subnet_height = rows_per_subnet * 70 + 60
        subnet_height = max(120, subnet_height)
        
        vpc_height = subnet_height + 80
        for vpc_id, count in vpc_subnet_count.items():
            vpc_res_count = len(self.vpc_resources.get(vpc_id, []))
            vpc_res_height = int(math.ceil(vpc_res_count / 4)) * 70 + 40 if vpc_res_count else 0
            vpc_height = max(vpc_height, subnet_height + vpc_res_height + 100)
        
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
    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e8e8e8" stroke-width="0.5"/>
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
            vpc_name = vpc_data.get('Name', vpc_id)
            cidr = vpc_data.get('CidrBlock', '')
            
            # この VPC のサブネットを取得
            vpc_subnets = {
                sid: sdata for sid, sdata in reader.subnets.items()
                if (sdata.get('VpcId') or sdata.get('Properties', {}).get('VpcId')) == vpc_id
            }
            
            # VPC の高さを計算
            num_subnets = len(vpc_subnets)
            vpc_res_count = len(self.vpc_resources.get(vpc_id, []))
            vpc_res_rows = int(math.ceil(vpc_res_count / 4)) if vpc_res_count else 0
            actual_vpc_height = layout['subnet_height'] + vpc_res_rows * 70 + 100
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
                subnet_name = subnet_data.get('Name', subnet_id)
                is_public = subnet_data.get('IsPublic', False)
                
                color = self.CONTAINER_COLORS['subnet_public' if is_public else 'subnet_private']
                
                # サブネット内のリソース数に基づいて高さを計算
                resources = self.subnet_resources.get(subnet_id, [])
                rows = int(math.ceil(len(resources) / layout['cols_per_subnet'])) if resources else 1
                actual_subnet_height = rows * 70 + 60
                actual_subnet_height = max(layout['subnet_height'], actual_subnet_height)
                
                # サブネットコンテナ
                svg_parts.append(self._create_container_svg(
                    subnet_x, subnet_y, layout['subnet_width'], actual_subnet_height,
                    subnet_name[:25],
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
      VPC Resources (no subnet specified)
    </text>
''')
                
                for icon_type, res_id, res_name, res_data in vpc_res_list:
                    svg_parts.append(self._create_icon_svg(
                        icon_type, vpc_res_x, vpc_res_y, 48, res_name, res_id
                    ))
                    
                    col += 1
                    vpc_res_x += 65
                    if col >= 6:
                        col = 0
                        vpc_res_x = 40
                        vpc_res_y += 70
            
            vpc_y += actual_vpc_height + 30
        
        # 外部リソースを右側に描画
        external_x = layout['vpc_width'] + 60
        external_y = 50
        
        if self.external_resources:
            svg_parts.append(self._create_container_svg(
                external_x, external_y,
                layout['external_width'],
                int(math.ceil(len(self.external_resources) / layout['external_cols'])) * 70 + 60,
                "External Resources",
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
        for source_id, target_id, rel_type, label in reader.relationships:
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
                    
                    lines.append(self._create_edge_svg(source_id, target_id, color, dashed))
                    drawn_edges.add(edge_key)
        
        # Load Balancer -> Target Group 接続
        for lb_name, lb_data in reader.load_balancers.items():
            if lb_name not in self.node_positions:
                continue
            
            # Target Groups への接続
            for tg_name, tg_data in reader.target_groups.items():
                if tg_name in self.node_positions:
                    lb_arn = lb_data.get('LoadBalancerArn', lb_name)
                    tg_lb_arns = tg_data.get('LoadBalancerArns', [])
                    
                    # 接続があるか確認
                    if any(lb_arn in str(arn) or lb_name in str(arn) for arn in tg_lb_arns):
                        edge_key = (lb_name, tg_name)
                        if edge_key not in drawn_edges:
                            lines.append(self._create_edge_svg(lb_name, tg_name, '#DD344C', True))
                            drawn_edges.add(edge_key)
        
        # NAT Gateway -> Internet (同じサブネット内の最初のリソースへ)
        # Lambda -> DynamoDB/S3 接続
        for func_name, func_data in reader.lambda_functions.items():
            if func_name not in self.node_positions:
                continue
            
            # DynamoDB への接続
            for table_name in reader.dynamodb_tables.keys():
                if table_name in self.node_positions:
                    edge_key = (func_name, table_name)
                    if edge_key not in drawn_edges:
                        lines.append(self._create_edge_svg(func_name, table_name, '#ED7100', True))
                        drawn_edges.add(edge_key)
                        break
            
            # S3 への接続
            for bucket_name in reader.s3_buckets.keys():
                if bucket_name in self.node_positions:
                    edge_key = (func_name, bucket_name)
                    if edge_key not in drawn_edges:
                        lines.append(self._create_edge_svg(func_name, bucket_name, '#3F8624', True))
                        drawn_edges.add(edge_key)
                        break
        
        return ''.join(lines)

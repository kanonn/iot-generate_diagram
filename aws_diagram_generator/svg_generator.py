# -*- coding: utf-8 -*-
"""
SVG 形式のアーキテクチャ図生成モジュール
- AWS 新版アイコンスタイル（実体背景 + 白色パターン）
- VPC/Subnet 階層構造
- 関係ベースの配置（線が多いリソースを下に、Target Group は Subnet 外）
- 3:2 比率を目指す
"""

import os
from collections import defaultdict
import math


class SVGGenerator:
    """SVG 形式のアーキテクチャ図を生成するクラス"""
    
    # AWS 新版アイコン定義（実体背景 + 白抜きパターン）
    AWS_ICONS = {
        'EC2': {
            'bg': '#ED7100',
            'paths': [
                'M6,8 L18,8 L18,16 L6,16 Z',  # メイン四角
                'M8,4 L16,4 L16,8',  # 上部
                'M8,16 L8,20 L16,20 L16,16',  # 下部
            ]
        },
        'Lambda': {
            'bg': '#ED7100',
            'paths': [
                'M5,18 L12,6 L19,18 Z',  # 三角形
                'M9,14 L15,14',  # 横線
            ]
        },
        'EKS': {
            'bg': '#ED7100', 
            'paths': [
                'M12,4 L20,12 L12,20 L4,12 Z',  # 外側菱形
                'M12,8 L16,12 L12,16 L8,12 Z',  # 内側菱形
            ]
        },
        'ECS': {
            'bg': '#ED7100',
            'paths': [
                'M4,4 L20,4 L20,20 L4,20 Z',  # 外枠
                'M8,8 L16,8 L16,16 L8,16 Z',  # 内枠
                'M10,10 L14,10 L14,14 L10,14 Z',  # 中心
            ]
        },
        'Fargate': {
            'bg': '#ED7100',
            'paths': [
                'M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4',  # 円
                'M8,12 L16,12',  # 横
                'M12,8 L12,16',  # 縦
            ]
        },
        'ALB': {
            'bg': '#8C4FFF',
            'paths': [
                'M4,8 L12,4 L20,8 L20,16 L12,20 L4,16 Z',  # 六角形
                'M4,12 L20,12',  # 横線
                'M12,4 L12,20',  # 縦線
            ]
        },
        'NLB': {
            'bg': '#8C4FFF',
            'paths': [
                'M4,8 L12,4 L20,8 L20,16 L12,20 L4,16 Z',  # 六角形
                'M6,9 L18,9',
                'M6,12 L18,12',
                'M6,15 L18,15',
            ]
        },
        'TargetGroup': {
            'bg': '#8C4FFF',
            'paths': [
                'M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4',  # 外円
                'M12,7 A5,5 0 1,1 12,17 A5,5 0 1,1 12,7',  # 中円
                'M12,10 A2,2 0 1,1 12,14 A2,2 0 1,1 12,10',  # 内円
            ]
        },
        'RDS': {
            'bg': '#3B48CC',
            'paths': [
                'M6,6 Q12,4 18,6 L18,18 Q12,20 6,18 Z',  # シリンダー本体
                'M6,6 Q12,8 18,6',  # 上部楕円
                'M6,12 Q12,14 18,12',  # 中央楕円
            ]
        },
        'DynamoDB': {
            'bg': '#3B48CC',
            'paths': [
                'M12,4 L20,8 L20,16 L12,20 L4,16 L4,8 Z',  # 六角形
                'M4,12 L20,12',  # 横
                'M12,4 L12,20',  # 縦
            ]
        },
        'ElastiCache': {
            'bg': '#3B48CC',
            'paths': [
                'M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4',  # 円
                'M7,12 L10,9 L10,15 Z',  # 左三角
                'M17,12 L14,9 L14,15 Z',  # 右三角
            ]
        },
        'S3': {
            'bg': '#3F8624',
            'paths': [
                'M6,6 Q12,4 18,6 L18,18 Q12,20 6,18 Z',  # バケット
                'M6,6 Q12,8 18,6',  # 上楕円
                'M6,10 Q12,12 18,10',  # 中楕円1
                'M6,14 Q12,16 18,14',  # 中楕円2
            ]
        },
        'EFS': {
            'bg': '#3F8624',
            'paths': [
                'M4,5 L20,5 L20,19 L4,19 Z',  # 外枠
                'M4,9 L20,9',
                'M4,13 L20,13',
                'M4,17 L20,17',
                'M10,5 L10,19',
                'M16,5 L16,19',
            ]
        },
        'SNS': {
            'bg': '#E7157B',
            'paths': [
                'M12,4 L20,12 L12,20 L4,12 Z',  # 菱形
                'M12,8 L12,16',  # 縦
                'M8,12 L16,12',  # 横
            ]
        },
        'SQS': {
            'bg': '#E7157B',
            'paths': [
                'M4,6 L20,6 L20,18 L4,18 Z',  # キュー本体
                'M7,10 L17,10',  # 線1
                'M7,14 L17,14',  # 線2
            ]
        },
        'APIGateway': {
            'bg': '#E7157B',
            'paths': [
                'M12,4 L20,8 L20,16 L12,20 L4,16 L4,8 Z',  # 六角形
                'M8,8 L12,12 L16,8',  # 上V
                'M8,16 L12,12 L16,16',  # 下V
            ]
        },
        'CloudFront': {
            'bg': '#8C4FFF',
            'paths': [
                'M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4',  # 外円
                'M4,12 L20,12',  # 横線
                'M12,4 Q8,12 12,20',  # 左曲線
                'M12,4 Q16,12 12,20',  # 右曲線
            ]
        },
        'EventBridge': {
            'bg': '#E7157B',
            'paths': [
                'M12,4 L20,8 L20,16 L12,20 L4,16 L4,8 Z',  # 六角形
                'M12,8 A4,4 0 1,1 12,16 A4,4 0 1,1 12,8',  # 中央円
            ]
        },
        'VPCEndpoint': {
            'bg': '#8C4FFF',
            'paths': [
                'M4,12 L8,12',
                'M16,12 L20,12',
                'M8,6 L16,6 L16,18 L8,18 Z',  # 中央箱
            ]
        },
        'SecurityGroup': {
            'bg': '#DD344C',
            'paths': [
                'M12,4 L20,8 L20,16 L12,20 L4,16 L4,8 Z',  # 盾
                'M12,8 L12,16',  # 縦
                'M8,12 L16,12',  # 横
            ]
        },
        'IAM': {
            'bg': '#DD344C',
            'paths': [
                'M12,4 A4,4 0 1,1 12,12 A4,4 0 1,1 12,4',  # 頭
                'M6,20 L6,16 Q12,13 18,16 L18,20',  # 体
            ]
        },
        'InternetGateway': {
            'bg': '#8C4FFF',
            'paths': [
                'M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4',  # 地球
                'M4,12 L20,12',  # 横
                'M12,4 L12,20',  # 縦
                'M6,8 L18,8',  # 緯線1
                'M6,16 L18,16',  # 緯線2
            ]
        },
        'NATGateway': {
            'bg': '#8C4FFF',
            'paths': [
                'M4,6 L20,6 L20,18 L4,18 Z',  # 箱
                'M12,10 L12,18',  # 縦
                'M8,14 L12,10 L16,14',  # 矢印
            ]
        },
        'RouteTable': {
            'bg': '#8C4FFF',
            'paths': [
                'M4,5 L20,5 L20,19 L4,19 Z',
                'M4,9 L20,9',
                'M4,13 L20,13',
                'M12,5 L12,19',
            ]
        },
    }
    
    def __init__(self, reader):
        self.reader = reader
        self.node_positions = {}
        self.relationships_map = defaultdict(list)
        self.reverse_relationships = defaultdict(list)
        
    def _get_property(self, data, *keys):
        """プロパティを取得"""
        if not data:
            return None
        for key in keys:
            if key in data:
                return data[key]
        props = data.get('Properties', {})
        if props:
            for key in keys:
                if key in props:
                    return props[key]
        return None
    
    def _get_name(self, res_id, res_data):
        """リソース名を取得"""
        if not res_data:
            return res_id
        name = self._get_property(res_data, 'Name')
        if name:
            return name
        tags = self._get_property(res_data, 'Tags')
        if tags:
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, dict) and tag.get('Key') == 'Name':
                        return tag.get('Value', res_id)
            elif isinstance(tags, dict):
                return tags.get('Name', res_id)
        return res_id
    
    def _build_relationships(self):
        """関係マップを構築"""
        for rel in self.reader.relationships:
            if len(rel) >= 3:
                source, target, rel_type = rel[0], rel[1], rel[2]
                if rel_type not in ['belongs_to', 'in_vpc']:
                    self.relationships_map[source].append((target, rel_type))
                    self.reverse_relationships[target].append((source, rel_type))
        
        total = sum(len(v) for v in self.relationships_map.values())
        print(f"  Built {total} relationships")
    
    def _create_icon_svg(self, icon_type, x, y, res_id, label='', size=36):
        """AWS 新版スタイルアイコンを作成"""
        icon_def = self.AWS_ICONS.get(icon_type, {
            'bg': '#232F3E',
            'paths': ['M4,4 L20,4 L20,20 L4,20 Z']
        })
        bg_color = icon_def['bg']
        paths = icon_def['paths']
        
        short_label = str(label)[:16] if label else ''
        
        # ノード位置を記録
        self.node_positions[res_id] = (x + size/2, y + size/2, size, size)
        
        # スケール
        scale = size / 24
        
        # パスを結合
        path_elements = ''
        for p in paths:
            path_elements += f'        <path d="{p}" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>\n'
        
        return f'''    <g id="{res_id}" transform="translate({x},{y})">
      <rect x="0" y="0" width="{size}" height="{size}" rx="4" fill="{bg_color}"/>
      <g transform="scale({scale:.3f})">
{path_elements}      </g>
      <text x="{size/2}" y="{size + 11}" text-anchor="middle" fill="#333" font-size="8">{short_label}</text>
    </g>
'''
    
    def _create_edge_svg(self, source_id, target_id, color='#888'):
        """接続線を作成"""
        if source_id not in self.node_positions or target_id not in self.node_positions:
            return ''
        
        src_x, src_y, _, src_h = self.node_positions[source_id]
        dst_x, dst_y, _, dst_h = self.node_positions[target_id]
        
        # 縦の関係の場合、下端と上端をつなぐ
        if abs(dst_y - src_y) > abs(dst_x - src_x):
            if dst_y > src_y:
                src_y += src_h / 2
                dst_y -= dst_h / 2
            else:
                src_y -= src_h / 2
                dst_y += dst_h / 2
        
        return f'    <line x1="{src_x:.0f}" y1="{src_y:.0f}" x2="{dst_x:.0f}" y2="{dst_y:.0f}" stroke="{color}" stroke-width="1.5" marker-end="url(#arrowhead)"/>\n'
    
    def generate(self, output_dir, output_name='aws-architecture'):
        """SVG を生成"""
        print("\n" + "=" * 80)
        print("Generating SVG Architecture Diagram")
        print("=" * 80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_name}.svg")
        
        self._build_relationships()
        
        # リソースを整理
        vpc_data = self._organize_by_vpc()
        external_resources = self._get_external_resources()
        
        # レイアウト計算
        content_svg, total_width, total_height = self._layout_all(vpc_data, external_resources)
        
        # SVG 構築
        svg_content = self._build_svg_document(content_svg, total_width, total_height)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f"\n✓ SVG diagram generated: {output_path}")
        print(f"  Size: {total_width} x {total_height}")
        return output_path
    
    def _organize_by_vpc(self):
        """VPC/Subnet ごとにリソースを整理"""
        reader = self.reader
        vpc_data = {}
        
        # サブネット -> VPC マッピング
        subnet_to_vpc = {}
        for subnet_id, subnet_info in reader.subnets.items():
            vpc_id = self._get_property(subnet_info, 'VpcId')
            if vpc_id:
                subnet_to_vpc[subnet_id] = vpc_id
        
        # VPC 初期化
        for vpc_id, vpc_info in reader.vpcs.items():
            vpc_name = self._get_name(vpc_id, vpc_info)
            cidr = self._get_property(vpc_info, 'CidrBlock') or ''
            vpc_data[vpc_id] = {
                'name': vpc_name,
                'cidr': cidr,
                'subnets': {},
                'vpc_level_resources': [],
                'below_subnet_resources': [],  # Target Group など Subnet の下に配置
            }
        
        # サブネット初期化
        for subnet_id, subnet_info in reader.subnets.items():
            vpc_id = subnet_to_vpc.get(subnet_id)
            if vpc_id and vpc_id in vpc_data:
                subnet_name = self._get_name(subnet_id, subnet_info)
                az = self._get_property(subnet_info, 'AvailabilityZone') or ''
                vpc_data[vpc_id]['subnets'][subnet_id] = {
                    'name': subnet_name,
                    'az': az[-2:] if az else '',
                    'resources': []
                }
        
        # リソースを配置
        self._place_resources(vpc_data, subnet_to_vpc)
        
        return vpc_data
    
    def _place_resources(self, vpc_data, subnet_to_vpc):
        """リソースを適切な場所に配置"""
        reader = self.reader
        
        # EC2
        for ec2_id, data in reader.ec2_instances.items():
            subnet_id = self._get_property(data, 'SubnetId')
            name = self._get_name(ec2_id, data)
            placed = self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_id, ('EC2', ec2_id, name))
            if not placed:
                # VPC に直接配置
                vpc_id = self._get_property(data, 'VpcId')
                if vpc_id and vpc_id in vpc_data:
                    vpc_data[vpc_id]['vpc_level_resources'].append(('EC2', ec2_id, name))
        
        # Lambda - VPC 内外両方対応
        for func_name, data in reader.lambda_functions.items():
            vpc_config = self._get_property(data, 'VpcConfig') or {}
            subnet_ids = vpc_config.get('SubnetIds', [])
            if not subnet_ids:
                subnet_ids = self._get_property(data, 'SubnetIds') or []
            name = self._get_name(func_name, data)
            
            if subnet_ids and len(subnet_ids) > 0:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('Lambda', func_name, name))
            # VPC 外の Lambda は external_resources へ
        
        # ECS Cluster - VPC に配置
        for cluster_name, data in reader.ecs_clusters.items():
            name = self._get_name(cluster_name, data)
            # ECS は通常 VPC に属するが、SubnetId がないので external へ
        
        # EKS
        for cluster_name, data in reader.eks_clusters.items():
            subnet_ids = self._get_property(data, 'SubnetIds') or []
            name = self._get_name(cluster_name, data)
            if subnet_ids and len(subnet_ids) > 0:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('EKS', cluster_name, name))
        
        # Load Balancer
        for lb_name, data in reader.load_balancers.items():
            subnet_ids = self._get_property(data, 'SubnetIds') or self._get_property(data, 'Subnets') or []
            lb_type = self._get_property(data, 'LoadBalancerType') or 'application'
            icon = 'NLB' if 'network' in str(lb_type).lower() else 'ALB'
            name = self._get_name(lb_name, data)
            if subnet_ids and len(subnet_ids) > 0:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], (icon, lb_name, name))
        
        # Target Group -> below_subnet_resources（Subnet の下に配置）
        for tg_name, data in reader.target_groups.items():
            vpc_id = self._get_property(data, 'VpcId')
            name = self._get_name(tg_name, data)
            if vpc_id and vpc_id in vpc_data:
                vpc_data[vpc_id]['below_subnet_resources'].append(('TargetGroup', tg_name, name))
        
        # RDS
        for db_id, data in reader.rds_instances.items():
            subnet_ids = self._get_property(data, 'SubnetIds') or []
            vpc_id = self._get_property(data, 'VpcId')
            name = self._get_name(db_id, data)
            placed = False
            if subnet_ids and len(subnet_ids) > 0:
                placed = self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('RDS', db_id, name))
            if not placed and vpc_id and vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_level_resources'].append(('RDS', db_id, name))
        
        # ElastiCache
        for cache_id, data in reader.elasticache_clusters.items():
            vpc_id = self._get_property(data, 'VpcId')
            name = self._get_name(cache_id, data)
            if vpc_id and vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_level_resources'].append(('ElastiCache', cache_id, name))
        
        # VPC Endpoint（集約）
        vpc_endpoints_by_vpc = defaultdict(int)
        for ep_id, data in reader.vpc_endpoints.items():
            vpc_id = self._get_property(data, 'VpcId')
            if vpc_id:
                vpc_endpoints_by_vpc[vpc_id] += 1
        for vpc_id, count in vpc_endpoints_by_vpc.items():
            if vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_level_resources'].append(('VPCEndpoint', f'__vpce_{vpc_id}__', f'VPCE ({count})'))
        
        # Security Group（集約）
        sg_by_vpc = defaultdict(int)
        for sg_id, data in reader.security_groups.items():
            vpc_id = self._get_property(data, 'VpcId')
            if vpc_id:
                sg_by_vpc[vpc_id] += 1
        for vpc_id, count in sg_by_vpc.items():
            if vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_level_resources'].append(('SecurityGroup', f'__sg_{vpc_id}__', f'SG ({count})'))
        
        # Internet Gateway
        for igw_id, data in reader.internet_gateways.items():
            attachments = self._get_property(data, 'Attachments') or []
            for att in attachments:
                vpc_id = att.get('VpcId') if isinstance(att, dict) else None
                if vpc_id and vpc_id in vpc_data:
                    name = self._get_name(igw_id, data)
                    vpc_data[vpc_id]['vpc_level_resources'].append(('InternetGateway', igw_id, name))
        
        # NAT Gateway
        for nat_id, data in reader.nat_gateways.items():
            vpc_id = self._get_property(data, 'VpcId')
            subnet_id = self._get_property(data, 'SubnetId')
            name = self._get_name(nat_id, data)
            if subnet_id:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_id, ('NATGateway', nat_id, name))
            elif vpc_id and vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_level_resources'].append(('NATGateway', nat_id, name))
    
    def _add_to_subnet(self, vpc_data, subnet_to_vpc, subnet_id, resource):
        """サブネットにリソースを追加"""
        if not subnet_id:
            return False
        vpc_id = subnet_to_vpc.get(subnet_id)
        if vpc_id and vpc_id in vpc_data:
            if subnet_id in vpc_data[vpc_id]['subnets']:
                vpc_data[vpc_id]['subnets'][subnet_id]['resources'].append(resource)
                return True
        return False
    
    def _get_external_resources(self):
        """外部リソース（VPC 外）を取得"""
        reader = self.reader
        external = []
        
        # S3（集約）
        if reader.s3_buckets:
            external.append(('S3', '__s3__', f'S3 ({len(reader.s3_buckets)})'))
        
        # DynamoDB
        for name, data in reader.dynamodb_tables.items():
            external.append(('DynamoDB', name, self._get_name(name, data)[:16]))
        
        # SNS
        for name, data in reader.sns_topics.items():
            short_name = self._get_name(name, data)
            external.append(('SNS', name, short_name[:16]))
        
        # SQS
        for name, data in reader.sqs_queues.items():
            short_name = self._get_name(name, data)
            external.append(('SQS', name, short_name[:16]))
        
        # CloudFront
        for name, data in reader.cloudfront_distributions.items():
            external.append(('CloudFront', name, f'CF-{name[:10]}'))
        
        # API Gateway
        for name, data in reader.api_gateways.items():
            external.append(('APIGateway', name, self._get_name(name, data)[:16]))
        
        # EventBridge
        for name, data in reader.cloudwatch_event_rules.items():
            external.append(('EventBridge', name, self._get_name(name, data)[:16]))
        
        # IAM（集約）
        if reader.iam_roles:
            external.append(('IAM', '__iam__', f'IAM ({len(reader.iam_roles)})'))
        
        # EFS（集約）
        if reader.efs_filesystems:
            external.append(('EFS', '__efs__', f'EFS ({len(reader.efs_filesystems)})'))
        
        # ECS（VPC 外として扱う）
        for name, data in reader.ecs_clusters.items():
            external.append(('ECS', name, self._get_name(name, data)[:16]))
        
        # VPC 外の Lambda
        vpc_lambda_names = set()
        for vpc_id, vpc_info in self._organize_by_vpc_lambda_check().items():
            for subnet_info in vpc_info.get('subnets', {}).values():
                for res in subnet_info.get('resources', []):
                    if res[0] == 'Lambda':
                        vpc_lambda_names.add(res[1])
        
        for func_name, data in reader.lambda_functions.items():
            if func_name not in vpc_lambda_names:
                external.append(('Lambda', func_name, self._get_name(func_name, data)[:16]))
        
        return external
    
    def _organize_by_vpc_lambda_check(self):
        """VPC 内の Lambda をチェック用に整理"""
        reader = self.reader
        vpc_data = {}
        
        subnet_to_vpc = {}
        for subnet_id, subnet_info in reader.subnets.items():
            vpc_id = self._get_property(subnet_info, 'VpcId')
            if vpc_id:
                subnet_to_vpc[subnet_id] = vpc_id
        
        for vpc_id in reader.vpcs.keys():
            vpc_data[vpc_id] = {'subnets': {}}
        
        for subnet_id, subnet_info in reader.subnets.items():
            vpc_id = subnet_to_vpc.get(subnet_id)
            if vpc_id and vpc_id in vpc_data:
                vpc_data[vpc_id]['subnets'][subnet_id] = {'resources': []}
        
        for func_name, data in reader.lambda_functions.items():
            vpc_config = self._get_property(data, 'VpcConfig') or {}
            subnet_ids = vpc_config.get('SubnetIds', [])
            if subnet_ids and len(subnet_ids) > 0:
                subnet_id = subnet_ids[0]
                vpc_id = subnet_to_vpc.get(subnet_id)
                if vpc_id and vpc_id in vpc_data and subnet_id in vpc_data[vpc_id]['subnets']:
                    vpc_data[vpc_id]['subnets'][subnet_id]['resources'].append(('Lambda', func_name, func_name))
        
        return vpc_data
    
    def _get_connection_count(self, res_id):
        """リソースの接続数を取得"""
        return len(self.relationships_map.get(res_id, [])) + len(self.reverse_relationships.get(res_id, []))
    
    def _get_target_group_count(self, res_id):
        """リソースに関連する Target Group の数を取得"""
        count = 0
        # このリソースから出る関係で TG へのもの
        for target, rel_type in self.relationships_map.get(res_id, []):
            if rel_type == 'listener_to_tg' or 'target' in rel_type.lower():
                count += 1
        # このリソースへ入る関係で TG からのもの
        for source, rel_type in self.reverse_relationships.get(res_id, []):
            if rel_type == 'listener_to_tg' or 'target' in rel_type.lower():
                count += 1
        return count
    
    def _layout_all(self, vpc_data, external_resources):
        """全体レイアウト"""
        svg_parts = []
        
        icon_size = 36
        icon_spacing = 50
        
        current_y = 60
        max_width = 400
        
        # 各 VPC を描画
        for vpc_id, vpc_info in vpc_data.items():
            vpc_svg, vpc_width, vpc_height = self._layout_vpc(
                vpc_id, vpc_info, 20, current_y, icon_size, icon_spacing
            )
            svg_parts.append(vpc_svg)
            current_y += vpc_height + 25
            max_width = max(max_width, vpc_width + 40)
        
        # 外部リソース
        if external_resources:
            ext_svg, ext_width, ext_height = self._layout_external(
                external_resources, 20, current_y, icon_size, icon_spacing
            )
            svg_parts.append(ext_svg)
            current_y += ext_height + 20
            max_width = max(max_width, ext_width + 40)
        
        return '\n'.join(svg_parts), max_width, current_y
    
    def _layout_vpc(self, vpc_id, vpc_info, start_x, start_y, icon_size, icon_spacing):
        """VPC をレイアウト"""
        svg_parts = []
        
        vpc_name = vpc_info['name']
        cidr = vpc_info['cidr']
        subnets = vpc_info['subnets']
        vpc_level_resources = vpc_info.get('vpc_level_resources', [])
        below_subnet_resources = vpc_info.get('below_subnet_resources', [])
        
        current_y = start_y + 28
        max_content_width = 150
        
        # サブネットを横に並べる
        subnet_items = list(subnets.items())
        if subnet_items:
            # 1行に3つまで
            max_per_row = 3
            subnet_x = start_x + 15
            row_start_y = current_y
            row_max_height = 0
            col_count = 0
            
            for subnet_id, subnet_info in subnet_items:
                s_svg, s_width, s_height = self._layout_subnet(
                    subnet_id, subnet_info, subnet_x, current_y, icon_size, icon_spacing
                )
                svg_parts.append(s_svg)
                row_max_height = max(row_max_height, s_height)
                subnet_x += s_width + 15
                max_content_width = max(max_content_width, subnet_x - start_x)
                col_count += 1
                
                if col_count >= max_per_row:
                    current_y += row_max_height + 15
                    subnet_x = start_x + 15
                    row_max_height = 0
                    col_count = 0
            
            if col_count > 0:
                current_y += row_max_height + 15
        
        # Target Group をサブネットの下に配置（関連 LB ごとにグループ化）
        if below_subnet_resources:
            current_y += 10
            tg_svg, tg_width, tg_height = self._layout_target_groups(
                below_subnet_resources, start_x + 15, current_y, icon_size, icon_spacing
            )
            svg_parts.append(tg_svg)
            max_content_width = max(max_content_width, tg_width + 30)
            current_y += tg_height + 10
        
        # VPC レベルリソース
        if vpc_level_resources:
            res_svg, res_width, res_height = self._layout_resource_row(
                vpc_level_resources, start_x + 15, current_y, 6, icon_size, icon_spacing, ""
            )
            svg_parts.append(res_svg)
            max_content_width = max(max_content_width, res_width + 30)
            current_y += res_height + 10
        
        vpc_height = current_y - start_y + 10
        vpc_width = max(max_content_width, 200)
        
        # VPC 枠
        vpc_border = f'''    <rect x="{start_x}" y="{start_y}" width="{vpc_width}" height="{vpc_height}" 
          fill="none" stroke="#8C4FFF" stroke-width="2" rx="8"/>
    <text x="{start_x + 10}" y="{start_y + 18}" fill="#8C4FFF" font-size="11" font-weight="bold">{vpc_name[:30]} ({cidr})</text>
'''
        
        return vpc_border + '\n'.join(svg_parts), vpc_width, vpc_height
    
    def _layout_subnet(self, subnet_id, subnet_info, start_x, start_y, icon_size, icon_spacing):
        """サブネットをレイアウト（固定2行、関連 TG 数でソート）"""
        svg_parts = []
        
        subnet_name = subnet_info['name']
        az = subnet_info['az']
        resources = subnet_info.get('resources', [])
        
        if not resources:
            # 空のサブネット
            subnet_width = 80
            subnet_height = 50
            label = f"{subnet_name[:12]}"
            if az:
                label += f" ({az})"
            border = f'''    <rect x="{start_x}" y="{start_y}" width="{subnet_width}" height="{subnet_height}" 
          fill="#f8fff8" stroke="#7AA116" stroke-width="1.5" rx="5"/>
    <text x="{start_x + 8}" y="{start_y + 14}" fill="#7AA116" font-size="9">{label}</text>
'''
            return border, subnet_width, subnet_height
        
        # 関連 TG 数でソート（多い順）
        sorted_resources = sorted(resources, key=lambda r: self._get_target_group_count(r[1]), reverse=True)
        
        # 固定2行、各行に ceil(総数/2) 個
        total = len(sorted_resources)
        rows = min(2, total)  # 最大2行
        cols = math.ceil(total / rows)  # 各行の列数
        
        # 2行目から配置（TG 関連多いものを2行目左から）
        # sorted_resources[0] -> 2行目1列目, [1] -> 2行目2列目, ...
        # 2行目が埋まったら1行目へ
        content_y = start_y + 22
        for i, (icon_type, res_id, name) in enumerate(sorted_resources):
            # 2行目を先に埋める（下から上へ）
            if i < cols:
                row = 1  # 2行目
                col = i
            else:
                row = 0  # 1行目
                col = i - cols
            
            x = start_x + 10 + col * icon_spacing
            y = content_y + row * (icon_size + 16)
            svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
        
        subnet_width = cols * icon_spacing + 25
        subnet_height = rows * (icon_size + 16) + 30
        
        label = f"{subnet_name[:12]}"
        if az:
            label += f" ({az})"
        
        border = f'''    <rect x="{start_x}" y="{start_y}" width="{subnet_width}" height="{subnet_height}" 
          fill="#f8fff8" stroke="#7AA116" stroke-width="1.5" rx="5"/>
    <text x="{start_x + 8}" y="{start_y + 14}" fill="#7AA116" font-size="9">{label}</text>
'''
        
        return border + '\n'.join(svg_parts), subnet_width, subnet_height
    
    def _layout_target_groups(self, resources, start_x, start_y, icon_size, icon_spacing):
        """Target Group を関連 LB ごとにグループ化して配置
        - 同じ NLB に複数 TG がある場合: 3列で改行
        - 異なる NLB の TG: 横に並べる
        """
        svg_parts = []
        
        # LB -> Target Group のマッピングを作成
        lb_to_tg = defaultdict(list)
        orphan_tgs = []
        
        for icon_type, res_id, name in resources:
            # この TG に接続している LB を探す
            connected_lbs = []
            for source, targets in self.relationships_map.items():
                for target, rel_type in targets:
                    if target == res_id and rel_type == 'listener_to_tg':
                        connected_lbs.append(source)
            
            for source, rel_type in self.reverse_relationships.get(res_id, []):
                if rel_type == 'listener_to_tg':
                    connected_lbs.append(source)
            
            if connected_lbs:
                # 最初の LB にのみ関連付け（重複を避ける）
                lb_to_tg[connected_lbs[0]].append((icon_type, res_id, name))
            else:
                orphan_tgs.append((icon_type, res_id, name))
        
        current_x = start_x
        max_height = 0
        
        # 各 LB グループを横に配置
        for lb_name, tgs in lb_to_tg.items():
            if not tgs:
                continue
            
            # ラベル
            svg_parts.append(f'    <text x="{current_x}" y="{start_y + 10}" fill="#666" font-size="8">→ {lb_name[:15]}</text>\n')
            
            if len(tgs) > 1:
                # 同じ NLB に複数 TG: 3列で改行
                cols = min(3, len(tgs))
                rows = math.ceil(len(tgs) / cols)
                
                for i, (icon_type, res_id, name) in enumerate(tgs):
                    col = i % cols
                    row = i // cols
                    x = current_x + col * icon_spacing
                    y = start_y + 18 + row * (icon_size + 16)
                    svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
                
                group_width = cols * icon_spacing + 10
                group_height = rows * (icon_size + 16) + 25
            else:
                # 1つの TG: そのまま配置
                icon_type, res_id, name = tgs[0]
                x = current_x
                y = start_y + 18
                svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
                
                group_width = icon_spacing
                group_height = icon_size + 16 + 25
            
            current_x += group_width + 15
            max_height = max(max_height, group_height)
        
        # 孤立 TG（横に並べる）
        if orphan_tgs:
            svg_parts.append(f'    <text x="{current_x}" y="{start_y + 10}" fill="#999" font-size="8">Other TG</text>\n')
            
            for i, (icon_type, res_id, name) in enumerate(orphan_tgs):
                x = current_x + i * icon_spacing
                y = start_y + 18
                svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
            
            group_height = icon_size + 16 + 25
            max_height = max(max_height, group_height)
            current_x += len(orphan_tgs) * icon_spacing + 10
        
        total_width = current_x - start_x
        
        return '\n'.join(svg_parts), total_width, max_height if max_height > 0 else 10
    
    def _layout_resource_row(self, resources, start_x, start_y, max_cols, icon_size, icon_spacing, title=""):
        """リソース行をレイアウト"""
        svg_parts = []
        
        if not resources:
            return '', 0, 0
        
        offset_y = 0
        if title:
            svg_parts.append(f'    <text x="{start_x}" y="{start_y + 10}" fill="#666" font-size="9">{title}</text>\n')
            offset_y = 18
        
        cols = min(max_cols, len(resources))
        rows = math.ceil(len(resources) / cols)
        
        for i, (icon_type, res_id, name) in enumerate(resources):
            col = i % cols
            row = i // cols
            x = start_x + col * icon_spacing
            y = start_y + offset_y + row * (icon_size + 16)
            svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
        
        width = cols * icon_spacing
        height = offset_y + rows * (icon_size + 16) + 5
        
        return '\n'.join(svg_parts), width, height
    
    def _layout_external(self, resources, start_x, start_y, icon_size, icon_spacing):
        """外部リソースをレイアウト"""
        svg_parts = []
        
        if not resources:
            return '', 100, 30
        
        # 6 列で配置
        cols = min(8, len(resources))
        rows = math.ceil(len(resources) / cols)
        
        # タイトル
        svg_parts.append(f'    <text x="{start_x + 10}" y="{start_y + 15}" fill="#666" font-size="11">External Resources ({len(resources)})</text>\n')
        
        content_y = start_y + 25
        for i, (icon_type, res_id, name) in enumerate(resources):
            col = i % cols
            row = i // cols
            x = start_x + 10 + col * icon_spacing
            y = content_y + row * (icon_size + 16)
            svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
        
        width = cols * icon_spacing + 30
        height = rows * (icon_size + 16) + 35
        
        # 枠
        border = f'    <rect x="{start_x}" y="{start_y}" width="{width}" height="{height}" fill="#fafafa" stroke="#ccc" stroke-width="1" stroke-dasharray="5,3" rx="8"/>\n'
        
        return border + '\n'.join(svg_parts), width, height
    
    def _build_svg_document(self, content_svg, width, height):
        """SVG ドキュメントを構築"""
        # 接続線
        edge_svg = '\n  <!-- Connections -->\n'
        drawn = set()
        for source, targets in self.relationships_map.items():
            for target, rel_type in targets:
                if (source, target) not in drawn:
                    edge_svg += self._create_edge_svg(source, target)
                    drawn.add((source, target))
        
        rel_count = sum(len(v) for v in self.relationships_map.values())
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{width}" height="{height}" 
     viewBox="0 0 {width} {height}"
     style="background-color: white; font-family: Arial, sans-serif;">
  
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#888"/>
    </marker>
    <pattern id="smallGrid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#f0f0f0" stroke-width="0.5"/>
    </pattern>
    <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
      <rect width="80" height="80" fill="url(#smallGrid)"/>
      <path d="M 80 0 L 0 0 0 80" fill="none" stroke="#e0e0e0" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid)"/>
  
  <text x="15" y="25" fill="#232F3E" font-size="14" font-weight="bold">AWS Architecture Diagram</text>
  <text x="15" y="42" fill="#666" font-size="10">VPCs: {len(self.reader.vpcs)} | Subnets: {len(self.reader.subnets)} | Relationships: {rel_count}</text>

{content_svg}
{edge_svg}
</svg>'''

# -*- coding: utf-8 -*-
"""
SVG 形式のアーキテクチャ図生成モジュール
- VPC/Subnet 階層構造を維持
- Subnet 内部で関係ベースのグループ化
- AWS 公式アイコンスタイル
- 3:2 比率に近いレイアウト
"""

import os
from collections import defaultdict
import math


class SVGGenerator:
    """SVG 形式のアーキテクチャ図を生成するクラス"""
    
    # AWS アイコン定義（SVG パス）
    AWS_ICONS = {
        'EC2': {
            'color': '#ED7100',
            'path': 'M12,2 L22,7 L22,17 L12,22 L2,17 L2,7 Z M12,6 L12,18 M6,9 L18,9 M6,15 L18,15'
        },
        'Lambda': {
            'color': '#ED7100',
            'path': 'M4,20 L12,4 L20,20 M8,14 L16,14'
        },
        'EKS': {
            'color': '#ED7100',
            'path': 'M12,2 L22,12 L12,22 L2,12 Z M12,7 L12,17 M7,12 L17,12'
        },
        'ECS': {
            'color': '#ED7100',
            'path': 'M3,3 L21,3 L21,21 L3,21 Z M7,7 L17,7 L17,17 L7,17 Z'
        },
        'Fargate': {
            'color': '#ED7100',
            'path': 'M12,2 C17.5,2 22,6.5 22,12 C22,17.5 17.5,22 12,22 C6.5,22 2,17.5 2,12 C2,6.5 6.5,2 12,2 M8,12 L16,12 M12,8 L12,16'
        },
        'ALB': {
            'color': '#8C4FFF',
            'path': 'M2,6 L12,2 L22,6 L22,18 L12,22 L2,18 Z M12,2 L12,22 M2,12 L22,12'
        },
        'NLB': {
            'color': '#8C4FFF',
            'path': 'M2,6 L12,2 L22,6 L22,18 L12,22 L2,18 Z M7,8 L17,8 M7,12 L17,12 M7,16 L17,16'
        },
        'TargetGroup': {
            'color': '#8C4FFF',
            'path': 'M12,2 C17.5,2 22,6.5 22,12 C22,17.5 17.5,22 12,22 C6.5,22 2,17.5 2,12 C2,6.5 6.5,2 12,2 M12,6 C14.2,6 16,7.8 16,10 M12,6 C9.8,6 8,7.8 8,10 M12,18 C14.2,18 16,16.2 16,14 M12,18 C9.8,18 8,16.2 8,14'
        },
        'RDS': {
            'color': '#3B48CC',
            'path': 'M12,2 C17,2 21,4 21,6.5 L21,17.5 C21,20 17,22 12,22 C7,22 3,20 3,17.5 L3,6.5 C3,4 7,2 12,2 M3,11 C3,13.5 7,15.5 12,15.5 C17,15.5 21,13.5 21,11'
        },
        'DynamoDB': {
            'color': '#3B48CC',
            'path': 'M12,2 L21,7 L21,17 L12,22 L3,17 L3,7 Z M3,12 L21,12 M12,2 L12,22'
        },
        'S3': {
            'color': '#3F8624',
            'path': 'M21,7 L21,17 C21,19 17,21 12,21 C7,21 3,19 3,17 L3,7 C3,5 7,3 12,3 C17,3 21,5 21,7 M3,7 C3,9 7,11 12,11 C17,11 21,9 21,7 M3,12 C3,14 7,16 12,16 C17,16 21,14 21,12'
        },
        'SNS': {
            'color': '#E7157B',
            'path': 'M12,2 L22,12 L12,22 L2,12 Z M12,7 L12,17 M7,12 L17,12'
        },
        'SQS': {
            'color': '#E7157B',
            'path': 'M3,6 L21,6 L21,18 L3,18 Z M7,10 L17,10 M7,14 L17,14'
        },
        'APIGateway': {
            'color': '#E7157B',
            'path': 'M12,2 L22,7 L22,17 L12,22 L2,17 L2,7 Z M6,7 L12,12 L18,7 M6,17 L12,12 L18,17'
        },
        'CloudFront': {
            'color': '#8C4FFF',
            'path': 'M12,2 C17.5,2 22,6.5 22,12 C22,17.5 17.5,22 12,22 C6.5,22 2,17.5 2,12 C2,6.5 6.5,2 12,2 M2,12 L22,12 M12,2 C8,6 8,18 12,22 M12,2 C16,6 16,18 12,22'
        },
        'EventBridge': {
            'color': '#E7157B',
            'path': 'M12,2 L20,6 L20,18 L12,22 L4,18 L4,6 Z M12,8 C14,8 16,10 16,12 C16,14 14,16 12,16 C10,16 8,14 8,12 C8,10 10,8 12,8'
        },
        'VPCEndpoint': {
            'color': '#8C4FFF',
            'path': 'M3,12 L9,12 M15,12 L21,12 M9,6 L15,6 L15,18 L9,18 Z'
        },
        'SecurityGroup': {
            'color': '#DD344C',
            'path': 'M12,2 L20,6 L20,14 L12,22 L4,14 L4,6 Z M12,6 L12,14 M8,10 L16,10'
        },
        'IAM': {
            'color': '#DD344C',
            'path': 'M12,2 C14.5,2 16.5,4 16.5,6.5 C16.5,9 14.5,11 12,11 C9.5,11 7.5,9 7.5,6.5 C7.5,4 9.5,2 12,2 M4,22 L4,18 C4,15 7.5,13 12,13 C16.5,13 20,15 20,18 L20,22'
        },
        'EFS': {
            'color': '#3F8624',
            'path': 'M3,4 L21,4 L21,20 L3,20 Z M3,8 L21,8 M3,12 L21,12 M3,16 L21,16 M7,4 L7,20 M17,4 L17,20'
        },
        'InternetGateway': {
            'color': '#8C4FFF',
            'path': 'M12,2 C17.5,2 22,6.5 22,12 C22,17.5 17.5,22 12,22 C6.5,22 2,17.5 2,12 C2,6.5 6.5,2 12,2 M12,6 L12,18 M6,12 L18,12 M8,8 L16,16 M16,8 L8,16'
        },
        'NATGateway': {
            'color': '#8C4FFF',
            'path': 'M3,6 L21,6 L21,18 L3,18 Z M12,10 L12,18 M8,14 L12,10 L16,14'
        },
        'ElastiCache': {
            'color': '#3B48CC',
            'path': 'M12,2 C17.5,2 22,6.5 22,12 C22,17.5 17.5,22 12,22 C6.5,22 2,17.5 2,12 C2,6.5 6.5,2 12,2 M6,12 L10,8 L10,16 Z M14,8 L18,12 L14,16 Z'
        },
    }
    
    def __init__(self, reader):
        self.reader = reader
        self.node_positions = {}
        self.relationships_map = defaultdict(list)
        self.reverse_relationships = defaultdict(list)
        
    def _get_property(self, data, *keys):
        """プロパティを取得"""
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
    
    def _create_icon_svg(self, icon_type, x, y, res_id, label='', size=40):
        """AWS スタイルアイコンを作成"""
        icon_def = self.AWS_ICONS.get(icon_type, {'color': '#232F3E', 'path': 'M3,3 L21,3 L21,21 L3,21 Z'})
        color = icon_def['color']
        path = icon_def['path']
        short_label = str(label)[:18] if label else ''
        
        # ノード位置を記録
        self.node_positions[res_id] = (x + size/2, y + size/2, size, size)
        
        # スケール計算
        scale = size / 24
        
        return f'''    <g id="{res_id}" transform="translate({x},{y})">
      <rect x="0" y="0" width="{size}" height="{size}" rx="4" ry="4" 
            fill="white" stroke="{color}" stroke-width="2"/>
      <g transform="scale({scale})">
        <path d="{path}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
      <text x="{size/2}" y="{size + 12}" text-anchor="middle" fill="#333333" font-size="9">{short_label}</text>
    </g>
'''
    
    def _create_edge_svg(self, source_id, target_id, color='#888888'):
        """接続線を作成"""
        if source_id not in self.node_positions or target_id not in self.node_positions:
            return ''
        
        src_x, src_y, _, _ = self.node_positions[source_id]
        dst_x, dst_y, _, _ = self.node_positions[target_id]
        
        return f'    <line x1="{src_x}" y1="{src_y}" x2="{dst_x}" y2="{dst_y}" stroke="{color}" stroke-width="1.5" marker-end="url(#arrowhead)"/>\n'
    
    def generate(self, output_dir, output_name='aws-architecture'):
        """SVG を生成"""
        print("\n" + "=" * 80)
        print("Generating SVG Architecture Diagram")
        print("=" * 80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_name}.svg")
        
        self._build_relationships()
        
        # VPC ごとにリソースを整理
        vpc_data = self._organize_by_vpc()
        external_resources = self._get_external_resources()
        
        # 3:2 比率を目指してレイアウト計算
        content_svg, total_width, total_height = self._layout_all(vpc_data, external_resources)
        
        # SVG 構築
        svg_content = self._build_svg_document(content_svg, total_width, total_height)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f"\n✓ SVG diagram generated: {output_path}")
        print(f"  Size: {total_width} x {total_height} (ratio: {total_width/total_height:.2f})")
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
                'vpc_resources': []  # サブネット外のリソース
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
        self._place_resources_in_subnets(vpc_data, subnet_to_vpc)
        
        return vpc_data
    
    def _place_resources_in_subnets(self, vpc_data, subnet_to_vpc):
        """リソースをサブネットに配置"""
        reader = self.reader
        
        # EC2
        for ec2_id, data in reader.ec2_instances.items():
            subnet_id = self._get_property(data, 'SubnetId')
            name = self._get_name(ec2_id, data)
            self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_id, ('EC2', ec2_id, name))
        
        # Lambda
        for func_name, data in reader.lambda_functions.items():
            vpc_config = self._get_property(data, 'VpcConfig') or {}
            subnet_ids = vpc_config.get('SubnetIds', []) or self._get_property(data, 'SubnetIds') or []
            name = self._get_name(func_name, data)
            if subnet_ids:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('Lambda', func_name, name))
        
        # EKS
        for cluster_name, data in reader.eks_clusters.items():
            subnet_ids = self._get_property(data, 'SubnetIds') or []
            name = self._get_name(cluster_name, data)
            if subnet_ids:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('EKS', cluster_name, name))
        
        # Load Balancer
        for lb_name, data in reader.load_balancers.items():
            subnet_ids = self._get_property(data, 'SubnetIds', 'Subnets') or []
            lb_type = self._get_property(data, 'LoadBalancerType') or 'application'
            icon = 'NLB' if 'network' in str(lb_type).lower() else 'ALB'
            name = self._get_name(lb_name, data)
            if subnet_ids:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], (icon, lb_name, name))
        
        # Target Group -> VPC レベル
        for tg_name, data in reader.target_groups.items():
            vpc_id = self._get_property(data, 'VpcId')
            name = self._get_name(tg_name, data)
            if vpc_id and vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_resources'].append(('TargetGroup', tg_name, name))
        
        # RDS
        for db_id, data in reader.rds_instances.items():
            subnet_ids = self._get_property(data, 'SubnetIds') or []
            name = self._get_name(db_id, data)
            if subnet_ids:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('RDS', db_id, name))
        
        # VPC Endpoint -> VPC レベル（集約）
        vpc_endpoints_by_vpc = defaultdict(int)
        for ep_id, data in reader.vpc_endpoints.items():
            vpc_id = self._get_property(data, 'VpcId')
            if vpc_id:
                vpc_endpoints_by_vpc[vpc_id] += 1
        for vpc_id, count in vpc_endpoints_by_vpc.items():
            if vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_resources'].append(('VPCEndpoint', f'__vpce_{vpc_id}__', f'VPCE ({count})'))
        
        # Security Group -> VPC レベル（集約）
        sg_by_vpc = defaultdict(int)
        for sg_id, data in reader.security_groups.items():
            vpc_id = self._get_property(data, 'VpcId')
            if vpc_id:
                sg_by_vpc[vpc_id] += 1
        for vpc_id, count in sg_by_vpc.items():
            if vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_resources'].append(('SecurityGroup', f'__sg_{vpc_id}__', f'SG ({count})'))
    
    def _add_to_subnet(self, vpc_data, subnet_to_vpc, subnet_id, resource):
        """サブネットにリソースを追加"""
        if not subnet_id:
            return
        vpc_id = subnet_to_vpc.get(subnet_id)
        if vpc_id and vpc_id in vpc_data:
            if subnet_id in vpc_data[vpc_id]['subnets']:
                vpc_data[vpc_id]['subnets'][subnet_id]['resources'].append(resource)
    
    def _get_external_resources(self):
        """外部リソース（VPC 外）を取得"""
        reader = self.reader
        external = []
        
        # S3（集約）
        if reader.s3_buckets:
            external.append(('S3', '__s3__', f'S3 ({len(reader.s3_buckets)})'))
        
        # DynamoDB
        for name, data in reader.dynamodb_tables.items():
            external.append(('DynamoDB', name, self._get_name(name, data)))
        
        # SNS
        for name, data in reader.sns_topics.items():
            external.append(('SNS', name, self._get_name(name, data)))
        
        # SQS
        for name, data in reader.sqs_queues.items():
            external.append(('SQS', name, self._get_name(name, data)))
        
        # CloudFront
        for name, data in reader.cloudfront_distributions.items():
            external.append(('CloudFront', name, name[:15]))
        
        # API Gateway
        for name, data in reader.api_gateways.items():
            external.append(('APIGateway', name, self._get_name(name, data)))
        
        # EventBridge
        for name, data in reader.cloudwatch_event_rules.items():
            external.append(('EventBridge', name, self._get_name(name, data)))
        
        # IAM（集約）
        if reader.iam_roles:
            external.append(('IAM', '__iam__', f'IAM ({len(reader.iam_roles)})'))
        
        # EFS（集約）
        if reader.efs_filesystems:
            external.append(('EFS', '__efs__', f'EFS ({len(reader.efs_filesystems)})'))
        
        return external
    
    def _layout_all(self, vpc_data, external_resources):
        """全体レイアウト（3:2 比率を目指す）"""
        svg_parts = []
        
        icon_size = 40
        icon_spacing = 55
        padding = 15
        
        # 総リソース数を計算して列数を決定
        total_resources = 0
        for v in vpc_data.values():
            total_resources += len(v.get('vpc_resources', []))
            for s in v.get('subnets', {}).values():
                total_resources += len(s.get('resources', []))
        total_resources += len(external_resources)
        
        # 3:2 比率に近づける列数
        target_cols = max(4, int(math.sqrt(total_resources * 1.5)))
        
        current_y = 60
        max_width = 400
        
        # VPC を描画
        for vpc_id, vpc_info in vpc_data.items():
            vpc_svg, vpc_width, vpc_height = self._layout_vpc(
                vpc_id, vpc_info, 20, current_y, target_cols, icon_size, icon_spacing
            )
            svg_parts.append(vpc_svg)
            current_y += vpc_height + 25
            max_width = max(max_width, vpc_width + 40)
        
        # 外部リソース
        if external_resources:
            ext_svg, ext_width, ext_height = self._layout_external(
                external_resources, 20, current_y, target_cols, icon_size, icon_spacing
            )
            svg_parts.append(ext_svg)
            current_y += ext_height + 20
            max_width = max(max_width, ext_width + 40)
        
        return '\n'.join(svg_parts), max_width, current_y
    
    def _layout_vpc(self, vpc_id, vpc_info, start_x, start_y, target_cols, icon_size, icon_spacing):
        """VPC をレイアウト"""
        svg_parts = []
        
        vpc_name = vpc_info['name']
        cidr = vpc_info['cidr']
        subnets = vpc_info['subnets']
        vpc_resources = vpc_info['vpc_resources']
        
        current_y = start_y + 25
        vpc_content_width = 100
        
        # サブネットを横に並べる（複数列）
        subnet_items = list(subnets.items())
        if subnet_items:
            # サブネットごとの幅を計算
            subnet_widths = []
            for subnet_id, subnet_info in subnet_items:
                res_count = len(subnet_info['resources'])
                cols = min(3, max(1, res_count))
                w = cols * icon_spacing + 30
                subnet_widths.append(max(w, 100))
            
            # 複数行に分割（幅制限）
            max_row_width = target_cols * icon_spacing + 100
            rows = [[]]
            current_row_width = 0
            
            for i, (subnet_id, subnet_info) in enumerate(subnet_items):
                w = subnet_widths[i]
                if current_row_width + w > max_row_width and rows[-1]:
                    rows.append([])
                    current_row_width = 0
                rows[-1].append((subnet_id, subnet_info, w))
                current_row_width += w + 15
            
            # 各行を描画
            for row in rows:
                row_height = 0
                subnet_x = start_x + 15
                
                for subnet_id, subnet_info, w in row:
                    s_svg, s_h = self._layout_subnet(
                        subnet_id, subnet_info, subnet_x, current_y, icon_size, icon_spacing
                    )
                    svg_parts.append(s_svg)
                    row_height = max(row_height, s_h)
                    subnet_x += w + 15
                
                vpc_content_width = max(vpc_content_width, subnet_x - start_x)
                current_y += row_height + 15
        
        # VPC レベルリソース
        if vpc_resources:
            res_svg, res_w, res_h = self._layout_resource_row(
                vpc_resources, start_x + 15, current_y, target_cols, icon_size, icon_spacing, "VPC Resources"
            )
            svg_parts.append(res_svg)
            vpc_content_width = max(vpc_content_width, res_w + 30)
            current_y += res_h + 10
        
        vpc_height = current_y - start_y + 10
        vpc_width = vpc_content_width
        
        # VPC 枠
        vpc_border = f'''    <rect x="{start_x}" y="{start_y}" width="{vpc_width}" height="{vpc_height}" 
          fill="none" stroke="#8C4FFF" stroke-width="2" rx="8"/>
    <text x="{start_x + 10}" y="{start_y + 18}" fill="#8C4FFF" font-size="12" font-weight="bold">{vpc_name} ({cidr})</text>
'''
        
        return vpc_border + '\n'.join(svg_parts), vpc_width, vpc_height
    
    def _layout_subnet(self, subnet_id, subnet_info, start_x, start_y, icon_size, icon_spacing):
        """サブネットをレイアウト"""
        svg_parts = []
        
        subnet_name = subnet_info['name']
        az = subnet_info['az']
        resources = subnet_info['resources']
        
        # リソースを関係でグループ化
        groups = self._group_by_relationship(resources)
        
        current_y = start_y + 22
        max_width = 80
        
        for group in groups:
            g_svg, g_w, g_h = self._layout_group(group, start_x + 10, current_y, icon_size, icon_spacing)
            svg_parts.append(g_svg)
            max_width = max(max_width, g_w + 20)
            current_y += g_h + 8
        
        subnet_height = max(current_y - start_y + 5, 60)
        subnet_width = max_width
        
        # サブネット枠
        label = f"{subnet_name[:15]}"
        if az:
            label += f" ({az})"
        
        subnet_border = f'''    <rect x="{start_x}" y="{start_y}" width="{subnet_width}" height="{subnet_height}" 
          fill="#f8fff8" stroke="#7AA116" stroke-width="1.5" rx="5"/>
    <text x="{start_x + 8}" y="{start_y + 14}" fill="#7AA116" font-size="10">{label}</text>
'''
        
        return subnet_border + '\n'.join(svg_parts), subnet_height
    
    def _group_by_relationship(self, resources):
        """リソースを関係でグループ化"""
        if not resources:
            return []
        
        # 関係のあるリソースをまとめる
        res_ids = {r[1] for r in resources}
        groups = []
        used = set()
        
        for icon_type, res_id, name in resources:
            if res_id in used:
                continue
            
            group = {'hub': (icon_type, res_id, name), 'children': []}
            used.add(res_id)
            
            # このリソースから出る関係
            for target, rel_type in self.relationships_map.get(res_id, []):
                for r in resources:
                    if r[1] == target and target not in used:
                        group['children'].append(r)
                        used.add(target)
            
            groups.append(group)
        
        return groups
    
    def _layout_group(self, group, start_x, start_y, icon_size, icon_spacing):
        """グループをレイアウト"""
        svg_parts = []
        
        hub = group['hub']
        children = group['children']
        
        # ハブを描画
        svg_parts.append(self._create_icon_svg(hub[0], start_x, start_y, hub[1], hub[2], icon_size))
        
        # 子を横に並べる
        if children:
            child_y = start_y + icon_size + 25
            for i, child in enumerate(children):
                child_x = start_x + i * icon_spacing
                svg_parts.append(self._create_icon_svg(child[0], child_x, child_y, child[1], child[2], icon_size))
            
            group_width = len(children) * icon_spacing
            group_height = icon_size + 25 + icon_size + 15
        else:
            group_width = icon_size + 10
            group_height = icon_size + 15
        
        return '\n'.join(svg_parts), group_width, group_height
    
    def _layout_resource_row(self, resources, start_x, start_y, max_cols, icon_size, icon_spacing, title=""):
        """リソース行をレイアウト"""
        svg_parts = []
        
        if title:
            svg_parts.append(f'    <text x="{start_x}" y="{start_y + 10}" fill="#666666" font-size="9">{title}</text>\n')
            start_y += 18
        
        cols = min(max_cols, len(resources))
        rows = math.ceil(len(resources) / cols) if cols > 0 else 0
        
        for i, (icon_type, res_id, name) in enumerate(resources):
            col = i % cols
            row = i // cols
            x = start_x + col * icon_spacing
            y = start_y + row * (icon_size + 20)
            svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
        
        width = cols * icon_spacing
        height = rows * (icon_size + 20) + 10
        
        return '\n'.join(svg_parts), width, height
    
    def _layout_external(self, resources, start_x, start_y, max_cols, icon_size, icon_spacing):
        """外部リソースをレイアウト"""
        svg_parts = []
        
        cols = min(max_cols, len(resources))
        rows = math.ceil(len(resources) / cols) if cols > 0 else 1
        
        # タイトル
        svg_parts.append(f'    <text x="{start_x + 10}" y="{start_y + 15}" fill="#666666" font-size="11">External Resources ({len(resources)})</text>\n')
        
        content_y = start_y + 25
        for i, (icon_type, res_id, name) in enumerate(resources):
            col = i % cols
            row = i // cols
            x = start_x + 10 + col * icon_spacing
            y = content_y + row * (icon_size + 20)
            svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
        
        width = cols * icon_spacing + 30
        height = rows * (icon_size + 20) + 35
        
        # 枠
        border = f'    <rect x="{start_x}" y="{start_y}" width="{width}" height="{height}" fill="#fafafa" stroke="#cccccc" stroke-width="1" stroke-dasharray="5,3" rx="8"/>\n'
        
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
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{width}" height="{height}" 
     viewBox="0 0 {width} {height}"
     style="background-color: white; font-family: Arial, sans-serif;">
  
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#888888"/>
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
  
  <text x="15" y="25" fill="#232F3E" font-size="16" font-weight="bold">AWS Architecture Diagram</text>
  <text x="15" y="45" fill="#666666" font-size="10">VPCs: {len(self.reader.vpcs)} | Subnets: {len(self.reader.subnets)} | Relationships: {sum(len(v) for v in self.relationships_map.values())}</text>

{content_svg}
{edge_svg}
</svg>'''

# -*- coding: utf-8 -*-
"""
SVG 形式のアーキテクチャ図生成モジュール
- VPC/Subnet 階層構造
- VPC 内リソース: 関連 VPC 外リソース数でソート（2行、多いものを2行目左から）
- VPC 外リソース: 関連 VPC 内リソースごとにグループ化（同グループ3列で改行、異グループは横に並べる）
"""

import os
from collections import defaultdict
import math


class SVGGenerator:
    """SVG 形式のアーキテクチャ図を生成するクラス"""
    
    # AWS 新版アイコン定義
    AWS_ICONS = {
        'EC2': {'bg': '#ED7100', 'paths': ['M6,8 L18,8 L18,16 L6,16 Z', 'M8,4 L16,4 L16,8', 'M8,16 L8,20 L16,20 L16,16']},
        'Lambda': {'bg': '#ED7100', 'paths': ['M5,18 L12,6 L19,18 Z', 'M9,14 L15,14']},
        'EKS': {'bg': '#ED7100', 'paths': ['M12,4 L20,12 L12,20 L4,12 Z', 'M12,8 L16,12 L12,16 L8,12 Z']},
        'ECS': {'bg': '#ED7100', 'paths': ['M4,4 L20,4 L20,20 L4,20 Z', 'M8,8 L16,8 L16,16 L8,16 Z']},
        'Fargate': {'bg': '#ED7100', 'paths': ['M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4', 'M8,12 L16,12', 'M12,8 L12,16']},
        'ALB': {'bg': '#8C4FFF', 'paths': ['M4,8 L12,4 L20,8 L20,16 L12,20 L4,16 Z', 'M4,12 L20,12', 'M12,4 L12,20']},
        'NLB': {'bg': '#8C4FFF', 'paths': ['M4,8 L12,4 L20,8 L20,16 L12,20 L4,16 Z', 'M6,9 L18,9', 'M6,12 L18,12', 'M6,15 L18,15']},
        'TargetGroup': {'bg': '#8C4FFF', 'paths': ['M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4', 'M12,7 A5,5 0 1,1 12,17 A5,5 0 1,1 12,7', 'M12,10 A2,2 0 1,1 12,14 A2,2 0 1,1 12,10']},
        'RDS': {'bg': '#3B48CC', 'paths': ['M6,6 Q12,4 18,6 L18,18 Q12,20 6,18 Z', 'M6,6 Q12,8 18,6', 'M6,12 Q12,14 18,12']},
        'DynamoDB': {'bg': '#3B48CC', 'paths': ['M12,4 L20,8 L20,16 L12,20 L4,16 L4,8 Z', 'M4,12 L20,12', 'M12,4 L12,20']},
        'ElastiCache': {'bg': '#3B48CC', 'paths': ['M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4', 'M7,12 L10,9 L10,15 Z', 'M17,12 L14,9 L14,15 Z']},
        'S3': {'bg': '#3F8624', 'paths': ['M6,6 Q12,4 18,6 L18,18 Q12,20 6,18 Z', 'M6,6 Q12,8 18,6', 'M6,10 Q12,12 18,10', 'M6,14 Q12,16 18,14']},
        'EFS': {'bg': '#3F8624', 'paths': ['M4,5 L20,5 L20,19 L4,19 Z', 'M4,9 L20,9', 'M4,13 L20,13', 'M10,5 L10,19', 'M16,5 L16,19']},
        'SNS': {'bg': '#E7157B', 'paths': ['M12,4 L20,12 L12,20 L4,12 Z', 'M12,8 L12,16', 'M8,12 L16,12']},
        'SQS': {'bg': '#E7157B', 'paths': ['M4,6 L20,6 L20,18 L4,18 Z', 'M7,10 L17,10', 'M7,14 L17,14']},
        'APIGateway': {'bg': '#E7157B', 'paths': ['M12,4 L20,8 L20,16 L12,20 L4,16 L4,8 Z', 'M8,8 L12,12 L16,8', 'M8,16 L12,12 L16,16']},
        'CloudFront': {'bg': '#8C4FFF', 'paths': ['M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4', 'M4,12 L20,12', 'M12,4 Q8,12 12,20', 'M12,4 Q16,12 12,20']},
        'EventBridge': {'bg': '#E7157B', 'paths': ['M12,4 L20,8 L20,16 L12,20 L4,16 L4,8 Z', 'M12,8 A4,4 0 1,1 12,16 A4,4 0 1,1 12,8']},
        'VPCEndpoint': {'bg': '#8C4FFF', 'paths': ['M4,12 L8,12', 'M16,12 L20,12', 'M8,6 L16,6 L16,18 L8,18 Z']},
        'SecurityGroup': {'bg': '#DD344C', 'paths': ['M12,4 L20,8 L20,16 L12,20 L4,16 L4,8 Z', 'M12,8 L12,16', 'M8,12 L16,12']},
        'IAM': {'bg': '#DD344C', 'paths': ['M12,4 A4,4 0 1,1 12,12 A4,4 0 1,1 12,4', 'M6,20 L6,16 Q12,13 18,16 L18,20']},
        'InternetGateway': {'bg': '#8C4FFF', 'paths': ['M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4', 'M4,12 L20,12', 'M12,4 L12,20']},
        'NATGateway': {'bg': '#8C4FFF', 'paths': ['M4,6 L20,6 L20,18 L4,18 Z', 'M12,10 L12,18', 'M8,14 L12,10 L16,14']},
    }
    
    def __init__(self, reader):
        self.reader = reader
        self.node_positions = {}
        self.relationships_map = defaultdict(list)
        self.reverse_relationships = defaultdict(list)
        self.vpc_resource_ids = set()  # VPC 内リソース ID
        self.external_resource_ids = set()  # VPC 外リソース ID
        
    def _get_property(self, data, *keys):
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
                if rel_type not in ['belongs_to', 'in_vpc', 'in_subnet']:
                    self.relationships_map[source].append((target, rel_type))
                    self.reverse_relationships[target].append((source, rel_type))
        
        total = sum(len(v) for v in self.relationships_map.values())
        print(f"  Built {total} relationships")
    
    def _get_external_connections(self, res_id):
        """VPC 外リソースとの接続数を取得"""
        count = 0
        for target, _ in self.relationships_map.get(res_id, []):
            if target in self.external_resource_ids:
                count += 1
        for source, _ in self.reverse_relationships.get(res_id, []):
            if source in self.external_resource_ids:
                count += 1
        return count
    
    def _get_connected_vpc_resource(self, external_res_id):
        """VPC 外リソースに接続している VPC 内リソースを取得"""
        connected = []
        for target, _ in self.relationships_map.get(external_res_id, []):
            if target in self.vpc_resource_ids:
                connected.append(target)
        for source, _ in self.reverse_relationships.get(external_res_id, []):
            if source in self.vpc_resource_ids:
                connected.append(source)
        return connected
    
    def _create_icon_svg(self, icon_type, x, y, res_id, label='', size=36):
        icon_def = self.AWS_ICONS.get(icon_type, {'bg': '#232F3E', 'paths': ['M4,4 L20,4 L20,20 L4,20 Z']})
        bg_color = icon_def['bg']
        paths = icon_def['paths']
        short_label = str(label)[:16] if label else ''
        
        self.node_positions[res_id] = (x + size/2, y + size/2, size, size)
        scale = size / 24
        
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
    
    def _create_edge_svg(self, source_id, target_id):
        """接続線を作成（細く黒く）"""
        if source_id not in self.node_positions or target_id not in self.node_positions:
            return ''
        
        src_x, src_y, _, src_h = self.node_positions[source_id]
        dst_x, dst_y, _, dst_h = self.node_positions[target_id]
        
        # 縦の関係の場合、端点を調整
        if abs(dst_y - src_y) > abs(dst_x - src_x):
            if dst_y > src_y:
                src_y += src_h / 2
                dst_y -= dst_h / 2
            else:
                src_y -= src_h / 2
                dst_y += dst_h / 2
        
        return f'    <line x1="{src_x:.0f}" y1="{src_y:.0f}" x2="{dst_x:.0f}" y2="{dst_y:.0f}" stroke="#222" stroke-width="1" marker-end="url(#arrowhead)"/>\n'
    
    def generate(self, output_dir, output_name='aws-architecture'):
        print("\n" + "=" * 80)
        print("Generating SVG Architecture Diagram")
        print("=" * 80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_name}.svg")
        
        self._build_relationships()
        
        # VPC 内外リソースを整理
        vpc_data = self._organize_by_vpc()
        external_resources = self._get_external_resources()
        
        # VPC 内/外リソース ID を記録
        self._record_resource_ids(vpc_data, external_resources)
        
        # レイアウト
        content_svg, total_width, total_height = self._layout_all(vpc_data, external_resources)
        
        # SVG 構築
        svg_content = self._build_svg_document(content_svg, total_width, total_height)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f"\n✓ SVG diagram generated: {output_path}")
        print(f"  Size: {total_width} x {total_height}")
        return output_path
    
    def _record_resource_ids(self, vpc_data, external_resources):
        """VPC 内外リソース ID を記録"""
        for vpc_id, vpc_info in vpc_data.items():
            for subnet_info in vpc_info.get('subnets', {}).values():
                for icon_type, res_id, name in subnet_info.get('resources', []):
                    self.vpc_resource_ids.add(res_id)
            for icon_type, res_id, name in vpc_info.get('vpc_level_resources', []):
                self.vpc_resource_ids.add(res_id)
        
        for icon_type, res_id, name in external_resources:
            self.external_resource_ids.add(res_id)
    
    def _organize_by_vpc(self):
        """VPC/Subnet ごとにリソースを整理"""
        reader = self.reader
        vpc_data = {}
        
        subnet_to_vpc = {}
        for subnet_id, subnet_info in reader.subnets.items():
            vpc_id = self._get_property(subnet_info, 'VpcId')
            if vpc_id:
                subnet_to_vpc[subnet_id] = vpc_id
        
        for vpc_id, vpc_info in reader.vpcs.items():
            vpc_name = self._get_name(vpc_id, vpc_info)
            cidr = self._get_property(vpc_info, 'CidrBlock') or ''
            vpc_data[vpc_id] = {
                'name': vpc_name,
                'cidr': cidr,
                'subnets': {},
                'vpc_level_resources': [],
            }
        
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
        
        self._place_resources(vpc_data, subnet_to_vpc)
        return vpc_data
    
    def _place_resources(self, vpc_data, subnet_to_vpc):
        """リソースを配置"""
        reader = self.reader
        
        # EC2
        for ec2_id, data in reader.ec2_instances.items():
            subnet_id = self._get_property(data, 'SubnetId')
            name = self._get_name(ec2_id, data)
            placed = self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_id, ('EC2', ec2_id, name))
            if not placed:
                vpc_id = self._get_property(data, 'VpcId')
                if vpc_id and vpc_id in vpc_data:
                    vpc_data[vpc_id]['vpc_level_resources'].append(('EC2', ec2_id, name))
        
        # Lambda (VPC 内のみ)
        for func_name, data in reader.lambda_functions.items():
            vpc_config = self._get_property(data, 'VpcConfig') or {}
            subnet_ids = vpc_config.get('SubnetIds', [])
            if not subnet_ids:
                subnet_ids = self._get_property(data, 'SubnetIds') or []
            name = self._get_name(func_name, data)
            if subnet_ids and len(subnet_ids) > 0:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('Lambda', func_name, name))
        
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
        if not subnet_id:
            return False
        vpc_id = subnet_to_vpc.get(subnet_id)
        if vpc_id and vpc_id in vpc_data:
            if subnet_id in vpc_data[vpc_id]['subnets']:
                vpc_data[vpc_id]['subnets'][subnet_id]['resources'].append(resource)
                return True
        return False
    
    def _get_external_resources(self):
        """外部リソースを取得"""
        reader = self.reader
        external = []
        
        # S3（集約）
        if reader.s3_buckets:
            external.append(('S3', '__s3__', f'S3 ({len(reader.s3_buckets)})'))
        
        # Target Group
        for name, data in reader.target_groups.items():
            external.append(('TargetGroup', name, self._get_name(name, data)[:16]))
        
        # DynamoDB
        for name, data in reader.dynamodb_tables.items():
            external.append(('DynamoDB', name, self._get_name(name, data)[:16]))
        
        # SNS
        for name, data in reader.sns_topics.items():
            external.append(('SNS', name, self._get_name(name, data)[:16]))
        
        # SQS
        for name, data in reader.sqs_queues.items():
            external.append(('SQS', name, self._get_name(name, data)[:16]))
        
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
        
        # ECS
        for name, data in reader.ecs_clusters.items():
            external.append(('ECS', name, self._get_name(name, data)[:16]))
        
        # VPC 外の Lambda
        vpc_lambda_names = set()
        for func_name, data in reader.lambda_functions.items():
            vpc_config = self._get_property(data, 'VpcConfig') or {}
            subnet_ids = vpc_config.get('SubnetIds', [])
            if subnet_ids and len(subnet_ids) > 0:
                vpc_lambda_names.add(func_name)
        
        for func_name, data in reader.lambda_functions.items():
            if func_name not in vpc_lambda_names:
                external.append(('Lambda', func_name, self._get_name(func_name, data)[:16]))
        
        return external
    
    def _layout_all(self, vpc_data, external_resources):
        """全体レイアウト"""
        svg_parts = []
        
        icon_size = 36
        icon_spacing = 50
        
        current_y = 60
        max_width = 400
        
        # 各 VPC を描画（VPC 外リソースも一緒に）
        for vpc_id, vpc_info in vpc_data.items():
            vpc_svg, vpc_width, vpc_height = self._layout_vpc_with_external(
                vpc_id, vpc_info, external_resources, 20, current_y, icon_size, icon_spacing
            )
            svg_parts.append(vpc_svg)
            current_y += vpc_height + 25
            max_width = max(max_width, vpc_width + 40)
        
        # 関連のない外部リソース
        orphan_external = self._get_orphan_external(external_resources)
        if orphan_external:
            ext_svg, ext_width, ext_height = self._layout_orphan_external(
                orphan_external, 20, current_y, icon_size, icon_spacing
            )
            svg_parts.append(ext_svg)
            current_y += ext_height + 20
            max_width = max(max_width, ext_width + 40)
        
        return '\n'.join(svg_parts), max_width, current_y
    
    def _get_orphan_external(self, external_resources):
        """VPC 内リソースと接続のない外部リソースを取得"""
        orphans = []
        for icon_type, res_id, name in external_resources:
            connected = self._get_connected_vpc_resource(res_id)
            if not connected:
                orphans.append((icon_type, res_id, name))
        return orphans
    
    def _layout_vpc_with_external(self, vpc_id, vpc_info, external_resources, start_x, start_y, icon_size, icon_spacing):
        """VPC と関連する外部リソースをレイアウト"""
        svg_parts = []
        
        vpc_name = vpc_info['name']
        cidr = vpc_info['cidr']
        subnets = vpc_info['subnets']
        vpc_level_resources = vpc_info.get('vpc_level_resources', [])
        
        current_y = start_y + 28
        max_content_width = 150
        
        # サブネットを上下に並べる
        subnet_items = list(subnets.items())
        if subnet_items:
            for subnet_id, subnet_info in subnet_items:
                s_svg, s_width, s_height = self._layout_subnet(
                    subnet_id, subnet_info, external_resources, start_x + 15, current_y, icon_size, icon_spacing
                )
                svg_parts.append(s_svg)
                max_content_width = max(max_content_width, s_width + 30)
                current_y += s_height + 20
        
        # VPC レベルリソース
        if vpc_level_resources:
            res_svg, res_width, res_height = self._layout_resource_row(
                vpc_level_resources, start_x + 15, current_y, 8, icon_size, icon_spacing
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
    
    def _layout_subnet(self, subnet_id, subnet_info, external_resources, start_x, start_y, icon_size, icon_spacing):
        """サブネットをレイアウト（1行、関連外部リソース数で左から右へ降順）+ 関連外部リソースをその下に"""
        svg_parts = []
        
        subnet_name = subnet_info['name']
        az = subnet_info['az']
        resources = subnet_info.get('resources', [])
        
        if not resources:
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
        
        # 各リソースの関連外部リソース数を計算
        res_with_ext_count = []
        for icon_type, res_id, name in resources:
            ext_count = self._get_external_connections(res_id)
            res_with_ext_count.append((icon_type, res_id, name, ext_count))
        
        # 関連外部リソース数で降順ソート（多いものを左に）
        res_with_ext_count.sort(key=lambda x: x[3], reverse=True)
        
        # 1行で配置
        total = len(res_with_ext_count)
        cols = total
        
        content_y = start_y + 22
        for i, (icon_type, res_id, name, ext_count) in enumerate(res_with_ext_count):
            x = start_x + 10 + i * icon_spacing
            y = content_y
            svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
        
        subnet_internal_height = icon_size + 16 + 28
        subnet_width = cols * icon_spacing + 25
        
        # サブネット枠
        label = f"{subnet_name[:12]}"
        if az:
            label += f" ({az})"
        
        border = f'''    <rect x="{start_x}" y="{start_y}" width="{subnet_width}" height="{subnet_internal_height}" 
          fill="#f8fff8" stroke="#7AA116" stroke-width="1.5" rx="5"/>
    <text x="{start_x + 8}" y="{start_y + 14}" fill="#7AA116" font-size="9">{label}</text>
'''
        svg_parts.insert(0, border)
        
        # サブネット下に関連外部リソースを配置
        ext_y = start_y + subnet_internal_height + 10
        ext_svg, ext_width, ext_height = self._layout_related_external(
            resources, external_resources, start_x, ext_y, icon_size, icon_spacing
        )
        svg_parts.append(ext_svg)
        
        total_width = max(subnet_width, ext_width)
        total_height = subnet_internal_height + 10 + ext_height
        
        return '\n'.join(svg_parts), total_width, total_height
    
    def _layout_related_external(self, vpc_resources, external_resources, start_x, start_y, icon_size, icon_spacing):
        """VPC 内リソースに関連する外部リソースをグループ化して配置"""
        svg_parts = []
        
        # VPC 内リソース -> 関連外部リソースのマッピング
        vpc_to_external = defaultdict(list)
        used_external = set()
        
        # 関連外部リソース数で降順ソートした VPC 内リソース
        vpc_res_sorted = sorted(
            vpc_resources,
            key=lambda r: self._get_external_connections(r[1]),
            reverse=True
        )
        
        for icon_type, vpc_res_id, name in vpc_res_sorted:
            # このリソースに関連する外部リソースを探す
            for ext_type, ext_id, ext_name in external_resources:
                if ext_id in used_external:
                    continue
                
                # 関係があるか確認
                is_connected = False
                for target, _ in self.relationships_map.get(vpc_res_id, []):
                    if target == ext_id:
                        is_connected = True
                        break
                for source, _ in self.reverse_relationships.get(vpc_res_id, []):
                    if source == ext_id:
                        is_connected = True
                        break
                
                if is_connected:
                    vpc_to_external[vpc_res_id].append((ext_type, ext_id, ext_name))
                    used_external.add(ext_id)
        
        if not vpc_to_external:
            return '', 0, 0
        
        current_x = start_x
        max_height = 0
        
        # 各 VPC 内リソースの関連外部リソースを配置
        for vpc_res_id, ext_list in vpc_to_external.items():
            if not ext_list:
                continue
            
            # このグループを配置
            if len(ext_list) > 1:
                # 複数: 3列で改行
                cols = min(3, len(ext_list))
                rows = math.ceil(len(ext_list) / cols)
                
                for i, (ext_type, ext_id, ext_name) in enumerate(ext_list):
                    col = i % cols
                    row = i // cols
                    x = current_x + col * icon_spacing
                    y = start_y + row * (icon_size + 16)
                    svg_parts.append(self._create_icon_svg(ext_type, x, y, ext_id, ext_name, icon_size))
                
                group_width = cols * icon_spacing
                group_height = rows * (icon_size + 16)
            else:
                # 1つ: そのまま
                ext_type, ext_id, ext_name = ext_list[0]
                svg_parts.append(self._create_icon_svg(ext_type, current_x, start_y, ext_id, ext_name, icon_size))
                group_width = icon_spacing
                group_height = icon_size + 16
            
            current_x += group_width + 15
            max_height = max(max_height, group_height)
        
        total_width = current_x - start_x
        return '\n'.join(svg_parts), total_width, max_height
    
    def _layout_resource_row(self, resources, start_x, start_y, max_cols, icon_size, icon_spacing):
        """リソース行をレイアウト"""
        svg_parts = []
        
        if not resources:
            return '', 0, 0
        
        cols = min(max_cols, len(resources))
        rows = math.ceil(len(resources) / cols)
        
        for i, (icon_type, res_id, name) in enumerate(resources):
            col = i % cols
            row = i // cols
            x = start_x + col * icon_spacing
            y = start_y + row * (icon_size + 16)
            svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
        
        width = cols * icon_spacing
        height = rows * (icon_size + 16) + 5
        
        return '\n'.join(svg_parts), width, height
    
    def _layout_orphan_external(self, resources, start_x, start_y, icon_size, icon_spacing):
        """関連のない外部リソースをレイアウト"""
        svg_parts = []
        
        if not resources:
            return '', 100, 30
        
        cols = min(8, len(resources))
        rows = math.ceil(len(resources) / cols)
        
        svg_parts.append(f'    <text x="{start_x + 10}" y="{start_y + 15}" fill="#666" font-size="11">Unconnected Resources ({len(resources)})</text>\n')
        
        content_y = start_y + 25
        for i, (icon_type, res_id, name) in enumerate(resources):
            col = i % cols
            row = i // cols
            x = start_x + 10 + col * icon_spacing
            y = content_y + row * (icon_size + 16)
            svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name, icon_size))
        
        width = cols * icon_spacing + 30
        height = rows * (icon_size + 16) + 35
        
        border = f'    <rect x="{start_x}" y="{start_y}" width="{width}" height="{height}" fill="#fafafa" stroke="#ccc" stroke-width="1" stroke-dasharray="5,3" rx="8"/>\n'
        
        return border + '\n'.join(svg_parts), width, height
    
    def _build_svg_document(self, content_svg, width, height):
        """SVG ドキュメントを構築"""
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
    <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#222"/>
    </marker>
    <pattern id="smallGrid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#f0f0f0" stroke-width="0.5"/>
    </pattern>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <rect width="40" height="40" fill="url(#smallGrid)"/>
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e0e0e0" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid)"/>
  
  <text x="15" y="25" fill="#232F3E" font-size="14" font-weight="bold">AWS Architecture Diagram</text>
  <text x="15" y="42" fill="#666" font-size="10">VPCs: {len(self.reader.vpcs)} | Subnets: {len(self.reader.subnets)} | Relationships: {rel_count}</text>

{content_svg}
{edge_svg}
</svg>'''

# -*- coding: utf-8 -*-
"""
SVG 形式のアーキテクチャ図生成モジュール
- VPC/Subnet 階層構造
- VPC 内リソースと VPC 外リソースを上下に配置、アイコン列を揃える
- AWS 公式アイコンスタイル
"""

import os
from collections import defaultdict
import math


class SVGGenerator:
    """SVG 形式のアーキテクチャ図を生成するクラス"""
    
    # AWS 公式アイコン（より正確なデザイン）
    AWS_ICONS = {
        # Compute - オレンジ
        'EC2': {
            'bg': '#ED7100',
            'paths': [
                'M4,8 L12,4 L20,8 L20,16 L12,20 L4,16 Z',  # 六角形
                'M4,12 L20,12',  # 横線
            ]
        },
        'Lambda': {
            'bg': '#ED7100',
            'paths': [
                'M7,6 L12,18 L17,6',  # λ の上部
                'M5,18 L9,18',  # λ の下横線
            ]
        },
        'EKS': {
            'bg': '#ED7100', 
            'paths': [
                'M12,3 L21,12 L12,21 L3,12 Z',  # 外菱形
                'M12,7 L17,12 L12,17 L7,12 Z',  # 内菱形
            ]
        },
        'ECS': {
            'bg': '#ED7100',
            'paths': [
                'M4,4 L20,4 L20,20 L4,20 Z',  # 外枠
                'M8,8 L16,8 L16,16 L8,16 Z',  # 内枠
            ]
        },
        'Fargate': {
            'bg': '#ED7100',
            'paths': [
                'M12,3 C17,3 21,7 21,12 C21,17 17,21 12,21 C7,21 3,17 3,12 C3,7 7,3 12,3',
                'M12,7 L12,17',
                'M7,12 L17,12',
            ]
        },
        # Networking - パープル
        'ALB': {
            'bg': '#8C4FFF',
            'paths': [
                'M12,4 C12,4 4,8 4,12 C4,16 12,20 12,20 C12,20 20,16 20,12 C20,8 12,4 12,4',  # 楕円形
                'M8,10 L8,14',  # 左線
                'M12,8 L12,16',  # 中央線
                'M16,10 L16,14',  # 右線
            ]
        },
        'NLB': {
            'bg': '#8C4FFF',
            'paths': [
                'M6,12 L12,6',  # 左上
                'M6,12 L12,18',  # 左下
                'M6,12 L3,12',  # 左
                'M18,8 L21,8',  # 右上
                'M18,12 L21,12',  # 右中
                'M18,16 L21,16',  # 右下
                'M12,6 L18,8',  # 上から右上
                'M12,6 L18,12',  # 上から右中
                'M12,18 L18,12',  # 下から右中
                'M12,18 L18,16',  # 下から右下
            ]
        },
        'TargetGroup': {
            'bg': '#8C4FFF',
            'paths': [
                'M12,4 A8,8 0 1,1 12,20 A8,8 0 1,1 12,4',  # 外円
                'M12,8 A4,4 0 1,1 12,16 A4,4 0 1,1 12,8',  # 内円
                'M12,11 A1,1 0 1,1 12,13 A1,1 0 1,1 12,11',  # 中心点
            ]
        },
        'VPCEndpoint': {
            'bg': '#8C4FFF',
            'paths': [
                'M3,12 L8,12',
                'M16,12 L21,12',
                'M8,6 L16,6 L16,18 L8,18 Z',
                'M10,10 L14,10',
                'M10,14 L14,14',
            ]
        },
        'InternetGateway': {
            'bg': '#8C4FFF',
            'paths': [
                'M12,3 C17.5,3 22,7.5 22,12 C22,16.5 17.5,21 12,21 C6.5,21 2,16.5 2,12 C2,7.5 6.5,3 12,3',
                'M2,12 L22,12',
                'M12,3 L12,21',
                'M5,7 C8,7 10,9 12,12 C14,9 16,7 19,7',
                'M5,17 C8,17 10,15 12,12 C14,15 16,17 19,17',
            ]
        },
        'NATGateway': {
            'bg': '#8C4FFF',
            'paths': [
                'M4,7 L20,7 L20,17 L4,17 Z',
                'M12,10 L12,17',
                'M8,13 L12,10 L16,13',
            ]
        },
        'CloudFront': {
            'bg': '#8C4FFF',
            'paths': [
                'M12,3 C17.5,3 22,7.5 22,12 C22,16.5 17.5,21 12,21 C6.5,21 2,16.5 2,12 C2,7.5 6.5,3 12,3',
                'M2,12 L22,12',
                'M12,3 Q7,12 12,21',
                'M12,3 Q17,12 12,21',
            ]
        },
        # Database - ブルー
        'RDS': {
            'bg': '#3B48CC',
            'paths': [
                'M5,6 C5,4 8,3 12,3 C16,3 19,4 19,6 L19,18 C19,20 16,21 12,21 C8,21 5,20 5,18 Z',
                'M5,6 C5,8 8,9 12,9 C16,9 19,8 19,6',
                'M5,12 C5,14 8,15 12,15 C16,15 19,14 19,12',
            ]
        },
        'DynamoDB': {
            'bg': '#3B48CC',
            'paths': [
                'M12,3 L20,7 L20,17 L12,21 L4,17 L4,7 Z',
                'M4,12 L20,12',
                'M12,3 L12,21',
            ]
        },
        'ElastiCache': {
            'bg': '#3B48CC',
            'paths': [
                'M12,3 C17.5,3 22,7.5 22,12 C22,16.5 17.5,21 12,21 C6.5,21 2,16.5 2,12 C2,7.5 6.5,3 12,3',
                'M6,12 L10,8 L10,16 Z',
                'M18,12 L14,8 L14,16 Z',
            ]
        },
        # Storage - グリーン
        'S3': {
            'bg': '#3F8624',
            'paths': [
                'M5,5 C5,4 8,3 12,3 C16,3 19,4 19,5 L19,19 C19,20 16,21 12,21 C8,21 5,20 5,19 Z',
                'M5,5 C5,6 8,7 12,7 C16,7 19,6 19,5',
                'M5,10 C5,11 8,12 12,12 C16,12 19,11 19,10',
                'M5,15 C5,16 8,17 12,17 C16,17 19,16 19,15',
            ]
        },
        'EFS': {
            'bg': '#3F8624',
            'paths': [
                'M3,5 L21,5 L21,19 L3,19 Z',
                'M3,9 L21,9',
                'M3,13 L21,13',
                'M9,5 L9,19',
                'M15,5 L15,19',
            ]
        },
        # Integration - ピンク
        'SNS': {
            'bg': '#E7157B',
            'paths': [
                'M12,3 L21,12 L12,21 L3,12 Z',
                'M12,7 L12,17',
                'M7,12 L17,12',
            ]
        },
        'SQS': {
            'bg': '#E7157B',
            'paths': [
                'M4,6 L20,6 L20,18 L4,18 Z',
                'M7,10 L17,10',
                'M7,14 L17,14',
                'M14,10 L17,10 L17,14',
            ]
        },
        'APIGateway': {
            'bg': '#E7157B',
            'paths': [
                'M3,12 L9,6 L9,18 Z',  # 左三角
                'M21,12 L15,6 L15,18 Z',  # 右三角
                'M9,12 L15,12',  # 中央線
            ]
        },
        'EventBridge': {
            'bg': '#E7157B',
            'paths': [
                'M4,6 L20,6 L20,18 L4,18 Z',
                'M12,6 L12,18',
                'M4,12 L20,12',
                'M8,9 A3,3 0 1,1 8,15 A3,3 0 1,1 8,9',
                'M16,9 A3,3 0 1,1 16,15 A3,3 0 1,1 16,9',
            ]
        },
        # Security - レッド
        'SecurityGroup': {
            'bg': '#DD344C',
            'paths': [
                'M12,2 L20,6 L20,14 L12,22 L4,14 L4,6 Z',  # 盾形
                'M12,6 L12,14',
                'M8,10 L16,10',
            ]
        },
        'IAM': {
            'bg': '#DD344C',
            'paths': [
                'M12,3 C14,3 16,5 16,7 C16,9 14,11 12,11 C10,11 8,9 8,7 C8,5 10,3 12,3',  # 頭
                'M6,21 L6,16 C6,14 9,12 12,12 C15,12 18,14 18,16 L18,21',  # 体
            ]
        },
    }
    
    def __init__(self, reader):
        self.reader = reader
        self.node_positions = {}
        self.relationships_map = defaultdict(list)
        self.reverse_relationships = defaultdict(list)
        self.vpc_resource_ids = set()
        self.external_resource_ids = set()
        
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
        for rel in self.reader.relationships:
            if len(rel) >= 3:
                source, target, rel_type = rel[0], rel[1], rel[2]
                if rel_type not in ['belongs_to', 'in_vpc', 'in_subnet']:
                    self.relationships_map[source].append((target, rel_type))
                    self.reverse_relationships[target].append((source, rel_type))
        
        total = sum(len(v) for v in self.relationships_map.values())
        print(f"  Built {total} relationships")
    
    def _get_external_connections(self, res_id):
        count = 0
        for target, _ in self.relationships_map.get(res_id, []):
            if target in self.external_resource_ids:
                count += 1
        for source, _ in self.reverse_relationships.get(res_id, []):
            if source in self.external_resource_ids:
                count += 1
        return count
    
    def _get_connected_external_resources(self, vpc_res_id, external_resources):
        """VPC 内リソースに接続している外部リソースを取得"""
        connected = []
        for ext_type, ext_id, ext_name in external_resources:
            is_connected = False
            for target, _ in self.relationships_map.get(vpc_res_id, []):
                if target == ext_id:
                    is_connected = True
                    break
            if not is_connected:
                for source, _ in self.reverse_relationships.get(vpc_res_id, []):
                    if source == ext_id:
                        is_connected = True
                        break
            if is_connected:
                connected.append((ext_type, ext_id, ext_name))
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
            path_elements += f'        <path d="{p}" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>\n'
        
        return f'''    <g id="{res_id}" transform="translate({x},{y})">
      <rect x="0" y="0" width="{size}" height="{size}" rx="4" fill="{bg_color}"/>
      <g transform="scale({scale:.3f})">
{path_elements}      </g>
      <text x="{size/2}" y="{size + 11}" text-anchor="middle" fill="#333" font-size="8">{short_label}</text>
    </g>
'''
    
    def _create_edge_svg(self, source_id, target_id):
        if source_id not in self.node_positions or target_id not in self.node_positions:
            return ''
        
        src_x, src_y, _, src_h = self.node_positions[source_id]
        dst_x, dst_y, _, dst_h = self.node_positions[target_id]
        
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
        
        vpc_data = self._organize_by_vpc()
        external_resources = self._get_external_resources()
        
        self._record_resource_ids(vpc_data, external_resources)
        
        content_svg, total_width, total_height = self._layout_all(vpc_data, external_resources)
        
        svg_content = self._build_svg_document(content_svg, total_width, total_height)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f"\n✓ SVG diagram generated: {output_path}")
        print(f"  Size: {total_width} x {total_height}")
        return output_path
    
    def _record_resource_ids(self, vpc_data, external_resources):
        for vpc_id, vpc_info in vpc_data.items():
            for subnet_info in vpc_info.get('subnets', {}).values():
                for icon_type, res_id, name in subnet_info.get('resources', []):
                    self.vpc_resource_ids.add(res_id)
            for icon_type, res_id, name in vpc_info.get('vpc_level_resources', []):
                self.vpc_resource_ids.add(res_id)
        
        for icon_type, res_id, name in external_resources:
            self.external_resource_ids.add(res_id)
    
    def _organize_by_vpc(self):
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
        reader = self.reader
        
        for ec2_id, data in reader.ec2_instances.items():
            subnet_id = self._get_property(data, 'SubnetId')
            name = self._get_name(ec2_id, data)
            placed = self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_id, ('EC2', ec2_id, name))
            if not placed:
                vpc_id = self._get_property(data, 'VpcId')
                if vpc_id and vpc_id in vpc_data:
                    vpc_data[vpc_id]['vpc_level_resources'].append(('EC2', ec2_id, name))
        
        for func_name, data in reader.lambda_functions.items():
            vpc_config = self._get_property(data, 'VpcConfig') or {}
            subnet_ids = vpc_config.get('SubnetIds', [])
            if not subnet_ids:
                subnet_ids = self._get_property(data, 'SubnetIds') or []
            name = self._get_name(func_name, data)
            if subnet_ids and len(subnet_ids) > 0:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('Lambda', func_name, name))
        
        for cluster_name, data in reader.eks_clusters.items():
            subnet_ids = self._get_property(data, 'SubnetIds') or []
            name = self._get_name(cluster_name, data)
            if subnet_ids and len(subnet_ids) > 0:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('EKS', cluster_name, name))
        
        for lb_name, data in reader.load_balancers.items():
            subnet_ids = self._get_property(data, 'SubnetIds') or self._get_property(data, 'Subnets') or []
            lb_type = self._get_property(data, 'LoadBalancerType') or 'application'
            icon = 'NLB' if 'network' in str(lb_type).lower() else 'ALB'
            name = self._get_name(lb_name, data)
            if subnet_ids and len(subnet_ids) > 0:
                self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], (icon, lb_name, name))
        
        for db_id, data in reader.rds_instances.items():
            subnet_ids = self._get_property(data, 'SubnetIds') or []
            vpc_id = self._get_property(data, 'VpcId')
            name = self._get_name(db_id, data)
            placed = False
            if subnet_ids and len(subnet_ids) > 0:
                placed = self._add_to_subnet(vpc_data, subnet_to_vpc, subnet_ids[0], ('RDS', db_id, name))
            if not placed and vpc_id and vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_level_resources'].append(('RDS', db_id, name))
        
        for cache_id, data in reader.elasticache_clusters.items():
            vpc_id = self._get_property(data, 'VpcId')
            name = self._get_name(cache_id, data)
            if vpc_id and vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_level_resources'].append(('ElastiCache', cache_id, name))
        
        vpc_endpoints_by_vpc = defaultdict(int)
        for ep_id, data in reader.vpc_endpoints.items():
            vpc_id = self._get_property(data, 'VpcId')
            if vpc_id:
                vpc_endpoints_by_vpc[vpc_id] += 1
        for vpc_id, count in vpc_endpoints_by_vpc.items():
            if vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_level_resources'].append(('VPCEndpoint', f'__vpce_{vpc_id}__', f'VPCE ({count})'))
        
        sg_by_vpc = defaultdict(int)
        for sg_id, data in reader.security_groups.items():
            vpc_id = self._get_property(data, 'VpcId')
            if vpc_id:
                sg_by_vpc[vpc_id] += 1
        for vpc_id, count in sg_by_vpc.items():
            if vpc_id in vpc_data:
                vpc_data[vpc_id]['vpc_level_resources'].append(('SecurityGroup', f'__sg_{vpc_id}__', f'SG ({count})'))
        
        for igw_id, data in reader.internet_gateways.items():
            attachments = self._get_property(data, 'Attachments') or []
            for att in attachments:
                vpc_id = att.get('VpcId') if isinstance(att, dict) else None
                if vpc_id and vpc_id in vpc_data:
                    name = self._get_name(igw_id, data)
                    vpc_data[vpc_id]['vpc_level_resources'].append(('InternetGateway', igw_id, name))
        
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
        reader = self.reader
        external = []
        
        if reader.s3_buckets:
            external.append(('S3', '__s3__', f'S3 ({len(reader.s3_buckets)})'))
        
        for name, data in reader.target_groups.items():
            external.append(('TargetGroup', name, self._get_name(name, data)[:16]))
        
        for name, data in reader.dynamodb_tables.items():
            external.append(('DynamoDB', name, self._get_name(name, data)[:16]))
        
        for name, data in reader.sns_topics.items():
            external.append(('SNS', name, self._get_name(name, data)[:16]))
        
        for name, data in reader.sqs_queues.items():
            external.append(('SQS', name, self._get_name(name, data)[:16]))
        
        for name, data in reader.cloudfront_distributions.items():
            external.append(('CloudFront', name, f'CF-{name[:10]}'))
        
        for name, data in reader.api_gateways.items():
            external.append(('APIGateway', name, self._get_name(name, data)[:16]))
        
        for name, data in reader.cloudwatch_event_rules.items():
            external.append(('EventBridge', name, self._get_name(name, data)[:16]))
        
        if reader.iam_roles:
            external.append(('IAM', '__iam__', f'IAM ({len(reader.iam_roles)})'))
        
        if reader.efs_filesystems:
            external.append(('EFS', '__efs__', f'EFS ({len(reader.efs_filesystems)})'))
        
        for name, data in reader.ecs_clusters.items():
            external.append(('ECS', name, self._get_name(name, data)[:16]))
        
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
        svg_parts = []
        
        icon_size = 36
        icon_spacing = 50
        
        current_y = 60
        max_width = 400
        
        for vpc_id, vpc_info in vpc_data.items():
            vpc_svg, vpc_width, vpc_height = self._layout_vpc_with_external(
                vpc_id, vpc_info, external_resources, 20, current_y, icon_size, icon_spacing
            )
            svg_parts.append(vpc_svg)
            current_y += vpc_height + 25
            max_width = max(max_width, vpc_width + 40)
        
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
        orphans = []
        used_external = set()
        
        for vpc_id, vpc_info in self._organize_by_vpc().items():
            for subnet_info in vpc_info.get('subnets', {}).values():
                for icon_type, res_id, name in subnet_info.get('resources', []):
                    connected = self._get_connected_external_resources(res_id, external_resources)
                    for _, ext_id, _ in connected:
                        used_external.add(ext_id)
        
        for icon_type, res_id, name in external_resources:
            if res_id not in used_external:
                orphans.append((icon_type, res_id, name))
        return orphans
    
    def _layout_vpc_with_external(self, vpc_id, vpc_info, external_resources, start_x, start_y, icon_size, icon_spacing):
        svg_parts = []
        
        vpc_name = vpc_info['name']
        cidr = vpc_info['cidr']
        subnets = vpc_info['subnets']
        vpc_level_resources = vpc_info.get('vpc_level_resources', [])
        
        current_y = start_y + 28
        max_content_width = 150
        
        subnet_items = list(subnets.items())
        if subnet_items:
            for subnet_id, subnet_info in subnet_items:
                s_svg, s_width, s_height = self._layout_subnet_aligned(
                    subnet_id, subnet_info, external_resources, start_x + 15, current_y, icon_size, icon_spacing
                )
                svg_parts.append(s_svg)
                max_content_width = max(max_content_width, s_width + 30)
                current_y += s_height + 20
        
        if vpc_level_resources:
            res_svg, res_width, res_height = self._layout_resource_row(
                vpc_level_resources, start_x + 15, current_y, 12, icon_size, icon_spacing
            )
            svg_parts.append(res_svg)
            max_content_width = max(max_content_width, res_width + 30)
            current_y += res_height + 10
        
        vpc_height = current_y - start_y + 10
        vpc_width = max(max_content_width, 200)
        
        vpc_border = f'''    <rect x="{start_x}" y="{start_y}" width="{vpc_width}" height="{vpc_height}" 
          fill="none" stroke="#8C4FFF" stroke-width="2" rx="8"/>
    <text x="{start_x + 10}" y="{start_y + 18}" fill="#8C4FFF" font-size="11" font-weight="bold">{vpc_name[:30]} ({cidr})</text>
'''
        
        return vpc_border + '\n'.join(svg_parts), vpc_width, vpc_height
    
    def _layout_subnet_aligned(self, subnet_id, subnet_info, external_resources, start_x, start_y, icon_size, icon_spacing):
        """サブネットをレイアウト（VPC 内外リソースを上下に揃える）"""
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
        
        # 各 VPC 内リソースの関連外部リソースを取得し、数でソート
        res_with_external = []
        for icon_type, res_id, name in resources:
            connected_ext = self._get_connected_external_resources(res_id, external_resources)
            res_with_external.append((icon_type, res_id, name, connected_ext))
        
        # 関連外部リソース数で降順ソート（多いものを左に）
        res_with_external.sort(key=lambda x: len(x[3]), reverse=True)
        
        # 列数を計算（各 VPC 内リソースは max(1, ceil(外部リソース数/3)) 列を占有）
        col_positions = []  # 各 VPC 内リソースの開始列
        current_col = 0
        for icon_type, res_id, name, connected_ext in res_with_external:
            col_positions.append(current_col)
            ext_count = len(connected_ext)
            if ext_count <= 1:
                cols_needed = 1
            else:
                cols_needed = min(3, ext_count)  # 最大3列
            current_col += cols_needed
        
        total_cols = current_col
        
        # VPC 内リソースを配置（1行目）
        content_y = start_y + 22
        for i, (icon_type, res_id, name, connected_ext) in enumerate(res_with_external):
            col = col_positions[i]
            x = start_x + 10 + col * icon_spacing
            svg_parts.append(self._create_icon_svg(icon_type, x, y=content_y, res_id=res_id, label=name, size=icon_size))
        
        subnet_internal_height = icon_size + 16 + 28
        subnet_width = max(total_cols * icon_spacing + 25, 80)
        
        # サブネット枠
        label = f"{subnet_name[:12]}"
        if az:
            label += f" ({az})"
        
        border = f'''    <rect x="{start_x}" y="{start_y}" width="{subnet_width}" height="{subnet_internal_height}" 
          fill="#f8fff8" stroke="#7AA116" stroke-width="1.5" rx="5"/>
    <text x="{start_x + 8}" y="{start_y + 14}" fill="#7AA116" font-size="9">{label}</text>
'''
        svg_parts.insert(0, border)
        
        # 外部リソースを配置（サブネット下、上下揃え）
        ext_y = start_y + subnet_internal_height + 10
        max_ext_height = 0
        
        for i, (icon_type, res_id, name, connected_ext) in enumerate(res_with_external):
            if not connected_ext:
                continue
            
            col_start = col_positions[i]
            
            # この VPC 内リソースの外部リソースを 3 列で配置
            cols = min(3, len(connected_ext))
            rows = math.ceil(len(connected_ext) / cols)
            
            for j, (ext_type, ext_id, ext_name) in enumerate(connected_ext):
                ext_col = j % cols
                ext_row = j // cols
                x = start_x + 10 + (col_start + ext_col) * icon_spacing
                y = ext_y + ext_row * (icon_size + 16)
                svg_parts.append(self._create_icon_svg(ext_type, x, y, ext_id, ext_name, icon_size))
            
            ext_height = rows * (icon_size + 16)
            max_ext_height = max(max_ext_height, ext_height)
        
        total_height = subnet_internal_height + 10 + max_ext_height
        
        return '\n'.join(svg_parts), subnet_width, total_height
    
    def _layout_resource_row(self, resources, start_x, start_y, max_cols, icon_size, icon_spacing):
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
        svg_parts = []
        
        if not resources:
            return '', 100, 30
        
        cols = min(10, len(resources))
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

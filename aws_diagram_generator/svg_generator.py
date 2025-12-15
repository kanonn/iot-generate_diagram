# -*- coding: utf-8 -*-
"""
SVG 形式のアーキテクチャ図生成モジュール（関係ベースレイアウト版）
- 関係のあるリソースをグループ化して配置
- 線の交差を最小化
- 関係のないリソースは別エリアに配置
"""

import os
from collections import defaultdict
import math


class SVGGenerator:
    """SVG 形式のアーキテクチャ図を生成するクラス"""
    
    # AWS アイコンの色定義
    ICON_COLORS = {
        'EC2': '#ED7100',
        'ECS': '#ED7100',
        'EKS': '#ED7100',
        'Lambda': '#ED7100',
        'Fargate': '#ED7100',
        'ALB': '#8C4FFF',
        'NLB': '#8C4FFF',
        'ELB': '#8C4FFF',
        'VPC': '#8C4FFF',
        'Subnet': '#7AA116',
        'InternetGateway': '#8C4FFF',
        'NATGateway': '#8C4FFF',
        'VPCEndpoint': '#8C4FFF',
        'TargetGroup': '#8C4FFF',
        'RDS': '#3B48CC',
        'DynamoDB': '#3B48CC',
        'ElastiCache': '#3B48CC',
        'S3': '#3F8624',
        'EFS': '#3F8624',
        'SQS': '#E7157B',
        'SNS': '#E7157B',
        'APIGateway': '#E7157B',
        'CloudFront': '#8C4FFF',
        'EventBridge': '#E7157B',
        'SecurityGroup': '#DD344C',
        'IAM': '#DD344C',
        'CloudWatch': '#E7157B',
        'default': '#232F3E',
    }
    
    def __init__(self, reader):
        self.reader = reader
        self.node_positions = {}
        self.all_resources = {}  # id -> (type, name, data)
        self.relationships_map = defaultdict(list)  # source -> [(target, rel_type)]
        self.reverse_relationships = defaultdict(list)  # target -> [(source, rel_type)]
        
    def _get_property(self, data, *keys):
        """リソースデータからプロパティを取得"""
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
    
    def _collect_all_resources(self):
        """全リソースを収集"""
        reader = self.reader
        
        # VPC - 個別表示しない（サブネットで十分）
        
        # Subnet - 個別表示しない（リソースはサブネット内に配置されているので）
        
        # EC2
        for ec2_id, data in reader.ec2_instances.items():
            self.all_resources[ec2_id] = ('EC2', self._get_name(ec2_id, data), data)
        
        # EKS
        for name, data in reader.eks_clusters.items():
            self.all_resources[name] = ('EKS', self._get_name(name, data), data)
        
        # Lambda
        for name, data in reader.lambda_functions.items():
            self.all_resources[name] = ('Lambda', self._get_name(name, data), data)
        
        # Load Balancer
        for name, data in reader.load_balancers.items():
            lb_type = self._get_property(data, 'LoadBalancerType', 'Type') or 'application'
            icon = 'NLB' if 'network' in str(lb_type).lower() else 'ALB'
            self.all_resources[name] = (icon, self._get_name(name, data), data)
        
        # Target Group
        for name, data in reader.target_groups.items():
            self.all_resources[name] = ('TargetGroup', self._get_name(name, data), data)
        
        # SNS
        for name, data in reader.sns_topics.items():
            self.all_resources[name] = ('SNS', self._get_name(name, data), data)
        
        # SQS
        for name, data in reader.sqs_queues.items():
            self.all_resources[name] = ('SQS', self._get_name(name, data), data)
        
        # DynamoDB
        for name, data in reader.dynamodb_tables.items():
            self.all_resources[name] = ('DynamoDB', self._get_name(name, data), data)
        
        # RDS
        for name, data in reader.rds_instances.items():
            self.all_resources[name] = ('RDS', self._get_name(name, data), data)
        
        # CloudFront
        for name, data in reader.cloudfront_distributions.items():
            self.all_resources[name] = ('CloudFront', name[:20], data)
        
        # API Gateway
        for name, data in reader.api_gateways.items():
            self.all_resources[name] = ('APIGateway', self._get_name(name, data), data)
        
        # EventBridge
        for name, data in reader.cloudwatch_event_rules.items():
            self.all_resources[name] = ('EventBridge', self._get_name(name, data), data)
        
        # 集約リソース
        if reader.s3_buckets:
            self.all_resources['__s3__'] = ('S3', f'S3 ({len(reader.s3_buckets)})', {})
        if reader.efs_filesystems:
            self.all_resources['__efs__'] = ('EFS', f'EFS ({len(reader.efs_filesystems)})', {})
        if reader.iam_roles:
            self.all_resources['__iam__'] = ('IAM', f'IAM ({len(reader.iam_roles)})', {})
        if reader.security_groups:
            self.all_resources['__sg__'] = ('SecurityGroup', f'SG ({len(reader.security_groups)})', {})
        if reader.vpc_endpoints:
            self.all_resources['__vpce__'] = ('VPCEndpoint', f'VPCE ({len(reader.vpc_endpoints)})', {})
        if reader.internet_gateways:
            self.all_resources['__igw__'] = ('InternetGateway', f'IGW ({len(reader.internet_gateways)})', {})
        if reader.nat_gateways:
            self.all_resources['__nat__'] = ('NATGateway', f'NAT ({len(reader.nat_gateways)})', {})
        
        print(f"  Collected {len(self.all_resources)} resources")
    
    def _build_relationship_map(self):
        """関係マップを構築"""
        # 関係のあるリソース ID のみ抽出
        valid_ids = set(self.all_resources.keys())
        
        for rel in self.reader.relationships:
            if len(rel) >= 3:
                source, target, rel_type = rel[0], rel[1], rel[2]
                
                # サブネット/VPC 関係はスキップ
                if rel_type in ['belongs_to', 'in_subnet', 'in_vpc']:
                    continue
                
                # 両方のリソースが存在する場合のみ
                if source in valid_ids and target in valid_ids:
                    self.relationships_map[source].append((target, rel_type))
                    self.reverse_relationships[target].append((source, rel_type))
        
        total_rels = sum(len(v) for v in self.relationships_map.values())
        print(f"  Built relationship map: {total_rels} connections")
    
    def _find_relationship_groups(self):
        """関係に基づいてリソースをグループ化"""
        groups = []
        used = set()
        
        # 関係の多いリソースから処理（ハブとなるリソース）
        all_connected = set(self.relationships_map.keys()) | set(self.reverse_relationships.keys())
        hub_resources = sorted(
            all_connected,
            key=lambda x: len(self.relationships_map.get(x, [])) + len(self.reverse_relationships.get(x, [])),
            reverse=True
        )
        
        for hub in hub_resources:
            if hub in used:
                continue
            
            # このハブに関連するリソース
            group = {'hub': hub, 'children': [], 'parents': []}
            used.add(hub)
            
            # 子（このハブから出る関係）
            for target, rel_type in self.relationships_map.get(hub, []):
                if target not in used:
                    group['children'].append((target, rel_type))
                    used.add(target)
            
            # 親（このハブへ入る関係）
            for source, rel_type in self.reverse_relationships.get(hub, []):
                if source not in used:
                    group['parents'].append((source, rel_type))
                    used.add(source)
            
            if group['children'] or group['parents']:
                groups.append(group)
            elif hub not in used:
                # ハブだけで関係がすでに使われている場合
                pass
        
        # 関係のないリソース
        orphans = [r for r in self.all_resources.keys() if r not in used]
        
        print(f"  Found {len(groups)} relationship groups, {len(orphans)} orphan resources")
        return groups, orphans
    
    def _get_icon_symbol(self, icon_type):
        """アイコンのシンボルを取得"""
        symbols = {
            'EC2': 'EC2', 'ECS': 'ECS', 'EKS': 'EKS', 'Lambda': 'λ', 'Fargate': 'Fg',
            'ALB': 'ALB', 'NLB': 'NLB', 'ELB': 'ELB', 'RDS': 'RDS', 'DynamoDB': 'DDB',
            'ElastiCache': 'EC', 'S3': 'S3', 'EFS': 'EFS', 'SQS': 'SQS', 'SNS': 'SNS',
            'VPCEndpoint': 'EP', 'NATGateway': 'NAT', 'InternetGateway': 'IGW',
            'TargetGroup': 'TG', 'SecurityGroup': 'SG', 'APIGateway': 'API',
            'IAM': 'IAM', 'VPC': 'VPC', 'Subnet': 'Sub', 'CloudFront': 'CF',
            'EventBridge': 'EB',
        }
        return symbols.get(icon_type, icon_type[:3])
    
    def _create_icon_svg(self, icon_type, x, y, res_id, label='', size=48):
        """アイコン SVG を作成"""
        color = self.ICON_COLORS.get(icon_type, self.ICON_COLORS['default'])
        short_label = str(label)[:20] if label else ''
        
        self.node_positions[res_id] = (x + size/2, y + size/2, size, size)
        
        return f'''    <g id="{res_id}">
      <rect x="{x}" y="{y}" width="{size}" height="{size}" rx="5" ry="5" 
            fill="{color}" stroke="white" stroke-width="2"/>
      <text x="{x + size/2}" y="{y + size/2 + 4}" 
            text-anchor="middle" fill="white" font-size="10" font-weight="bold">
        {self._get_icon_symbol(icon_type)}
      </text>
      <text x="{x + size/2}" y="{y + size + 12}" 
            text-anchor="middle" fill="#232F3E" font-size="8">
        {short_label}
      </text>
    </g>
'''
    
    def _create_edge_svg(self, source_id, target_id, color='#888888'):
        """接続線を作成"""
        if source_id not in self.node_positions or target_id not in self.node_positions:
            return ''
        
        src_x, src_y, _, _ = self.node_positions[source_id]
        dst_x, dst_y, _, _ = self.node_positions[target_id]
        
        return f'''    <line x1="{src_x}" y1="{src_y}" x2="{dst_x}" y2="{dst_y}" 
          stroke="{color}" stroke-width="1.5" marker-end="url(#arrowhead)"/>
'''
    
    def generate(self, output_dir, output_name='aws-architecture'):
        """SVG を生成"""
        print("\n" + "=" * 80)
        print("Generating SVG Architecture Diagram (Relationship-based Layout)")
        print("=" * 80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_name}.svg")
        
        # リソースと関係を収集
        self._collect_all_resources()
        self._build_relationship_map()
        groups, orphans = self._find_relationship_groups()
        
        # レイアウト計算
        svg_parts = []
        current_y = 70
        max_width = 200
        
        # 各グループを描画
        group_svgs = []
        for i, group in enumerate(groups):
            group_svg, group_width, group_height = self._render_group(group, 30, current_y, i + 1)
            group_svgs.append(group_svg)
            current_y += group_height + 30
            max_width = max(max_width, group_width + 60)
        
        # 孤立リソースを描画
        if orphans:
            orphan_svg, orphan_width, orphan_height = self._render_orphans(orphans, 30, current_y)
            group_svgs.append(orphan_svg)
            current_y += orphan_height + 30
            max_width = max(max_width, orphan_width + 60)
        
        total_height = current_y + 20
        total_width = max(max_width, 600)
        
        # SVG ヘッダー
        svg_header = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{total_width}" height="{total_height}" 
     viewBox="0 0 {total_width} {total_height}"
     style="background-color: white; font-family: Arial, sans-serif;">
  
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" 
            refX="9" refY="3.5" orient="auto">
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
  
  <text x="20" y="30" fill="#232F3E" font-size="18" font-weight="bold">
    AWS Architecture Diagram
  </text>
  <text x="20" y="50" fill="#666666" font-size="11">
    Resources: {len(self.all_resources)} | Relationship Groups: {len(groups)} | Unconnected: {len(orphans)}
  </text>
'''
        
        svg_parts.append(svg_header)
        svg_parts.extend(group_svgs)
        
        # 接続線を描画
        svg_parts.append('\n  <!-- Connections -->\n')
        drawn_edges = set()
        for source, targets in self.relationships_map.items():
            for target, rel_type in targets:
                edge_key = (source, target)
                if edge_key not in drawn_edges:
                    svg_parts.append(self._create_edge_svg(source, target))
                    drawn_edges.add(edge_key)
        
        svg_parts.append('</svg>')
        
        # ファイル出力
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(svg_parts))
        
        print(f"\n✓ SVG diagram generated: {output_path}")
        print(f"  Size: {total_width} x {total_height}")
        print(f"  Groups: {len(groups)}, Orphans: {len(orphans)}")
        return output_path
    
    def _render_group(self, group, start_x, start_y, group_num):
        """関係グループを描画"""
        svg_parts = []
        hub_id = group['hub']
        parents = group['parents']
        children = group['children']
        
        if hub_id not in self.all_resources:
            return '', 100, 50
        
        hub_type, hub_name, _ = self.all_resources[hub_id]
        
        # レイアウト計算
        icon_size = 48
        h_spacing = 65
        v_spacing = 75
        
        # 親の数と子の数
        num_parents = len(parents)
        num_children = len(children)
        max_items = max(num_parents, num_children, 1)
        
        group_width = max(max_items * h_spacing + 40, 150)
        
        current_y = start_y
        
        # グループタイトル
        svg_parts.append(f'''    <text x="{start_x + 5}" y="{current_y + 12}" fill="#666666" font-size="10">
      Group {group_num}: {hub_name[:30]}
    </text>
''')
        current_y += 20
        
        # 親を上に配置
        if parents:
            row_width = num_parents * h_spacing
            parent_start_x = start_x + (group_width - row_width) / 2 + h_spacing / 2 - icon_size / 2
            for i, (parent_id, _) in enumerate(parents):
                if parent_id not in self.all_resources:
                    continue
                p_type, p_name, _ = self.all_resources[parent_id]
                x = parent_start_x + i * h_spacing
                svg_parts.append(self._create_icon_svg(p_type, x, current_y, parent_id, p_name))
            current_y += v_spacing
        
        # ハブを中央に配置
        hub_x = start_x + group_width / 2 - icon_size / 2
        svg_parts.append(self._create_icon_svg(hub_type, hub_x, current_y, hub_id, hub_name))
        current_y += v_spacing
        
        # 子を下に配置
        if children:
            row_width = num_children * h_spacing
            child_start_x = start_x + (group_width - row_width) / 2 + h_spacing / 2 - icon_size / 2
            for i, (child_id, _) in enumerate(children):
                if child_id not in self.all_resources:
                    continue
                c_type, c_name, _ = self.all_resources[child_id]
                x = child_start_x + i * h_spacing
                svg_parts.append(self._create_icon_svg(c_type, x, current_y, child_id, c_name))
            current_y += v_spacing - 10
        
        group_height = current_y - start_y + 10
        
        # グループ枠
        border_svg = f'''    <rect x="{start_x}" y="{start_y}" 
          width="{group_width}" height="{group_height}" 
          fill="none" stroke="#cccccc" stroke-width="1" stroke-dasharray="5,3" rx="8"/>
'''
        
        return border_svg + '\n'.join(svg_parts), group_width, group_height
    
    def _render_orphans(self, orphans, start_x, start_y):
        """孤立リソースを描画"""
        svg_parts = []
        
        # 実際に存在するリソースのみ
        valid_orphans = [o for o in orphans if o in self.all_resources]
        
        if not valid_orphans:
            return '', 100, 30
        
        icon_size = 48
        h_spacing = 65
        cols = min(8, len(valid_orphans))
        rows = math.ceil(len(valid_orphans) / cols)
        
        group_width = cols * h_spacing + 40
        group_height = rows * 70 + 50
        
        # タイトル
        svg_parts.append(f'''    <text x="{start_x + 5}" y="{start_y + 15}" fill="#999999" font-size="11">
      Unconnected Resources ({len(valid_orphans)})
    </text>
''')
        
        # アイコン配置
        for i, res_id in enumerate(valid_orphans):
            res_type, res_name, _ = self.all_resources[res_id]
            col = i % cols
            row = i // cols
            x = start_x + col * h_spacing + 20
            y = start_y + 25 + row * 70
            svg_parts.append(self._create_icon_svg(res_type, x, y, res_id, res_name))
        
        # 枠
        border_svg = f'''    <rect x="{start_x}" y="{start_y}" 
          width="{group_width}" height="{group_height}" 
          fill="#fafafa" stroke="#dddddd" stroke-width="1" rx="8"/>
'''
        
        return border_svg + '\n'.join(svg_parts), group_width, group_height

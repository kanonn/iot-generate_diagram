# -*- coding: utf-8 -*-
"""
SVG 形式のアーキテクチャ図生成モジュール
- VPC/Subnet 階層構造
- VPC 内リソースと VPC 外リソースを上下に揃える
- VPC 外リソース: 左側（無関連）、右側（関連あり）
- アイコンサイズと間隔をグリッドに揃える（40px = 2x2 小格子）
- AWS 公式アイコン対応（aws_icons/ フォルダから読み込み）
"""

import os
from collections import defaultdict
import math
import re
import base64


class SVGGenerator:
    """SVG 形式のアーキテクチャ図を生成するクラス"""
    
    # サービス名からアイコンファイル名へのマッピング
    ICON_FILE_MAPPING = {
        'EC2': 'Arch_Amazon-EC2_64.svg',
        'Lambda': 'Arch_AWS-Lambda_64.svg',
        'EKS': 'Arch_Amazon-Elastic-Kubernetes-Service_64.svg',
        'ECS': 'Arch_Amazon-Elastic-Container-Service_64.svg',
        'Fargate': 'Arch_AWS-Fargate_64.svg',
        'ALB': 'Arch_Elastic-Load-Balancing_64.svg',
        'NLB': 'Arch_Elastic-Load-Balancing_64.svg',
        'TargetGroup': 'Res_Elastic-Load-Balancing_Target_48.svg',
        'VPCEndpoint': 'Res_Amazon-VPC_Endpoints_48.svg',
        'InternetGateway': 'Res_Amazon-VPC_Internet-Gateway_48.svg',
        'NATGateway': 'Res_Amazon-VPC_NAT-Gateway_48.svg',
        'CloudFront': 'Arch_Amazon-CloudFront_64.svg',
        'RDS': 'Arch_Amazon-RDS_64.svg',
        'DynamoDB': 'Arch_Amazon-DynamoDB_64.svg',
        'ElastiCache': 'Arch_Amazon-ElastiCache_64.svg',
        'S3': 'Arch_Amazon-Simple-Storage-Service_64.svg',
        'EFS': 'Arch_Amazon-EFS_64.svg',
        'SNS': 'Arch_Amazon-Simple-Notification-Service_64.svg',
        'SQS': 'Arch_Amazon-Simple-Queue-Service_64.svg',
        'APIGateway': 'Arch_Amazon-API-Gateway_64.svg',
        'EventBridge': 'Arch_Amazon-EventBridge_64.svg',
        'SecurityGroup': 'Res_Amazon-VPC_Security-Group_48.svg',
        'IAM': 'Arch_AWS-Identity-and-Access-Management_64.svg',
    }
    
    # デフォルトアイコン（公式アイコンがない場合に使用）
    DEFAULT_ICONS = {
        'EC2': {'bg': '#ED7100', 'paths': ['M4,8 L12,4 L20,8 L20,16 L12,20 L4,16 Z', 'M4,12 L20,12']},
        'Lambda': {'bg': '#ED7100', 'paths': ['M6,5 L12,19', 'M12,19 L18,5', 'M4,19 L10,19']},
        'EKS': {'bg': '#ED7100', 'paths': ['M12,3 L21,12 L12,21 L3,12 Z', 'M12,7 L17,12 L12,17 L7,12 Z']},
        'ECS': {'bg': '#ED7100', 'paths': ['M3,3 L21,3 L21,21 L3,21 Z', 'M7,7 L17,7 L17,17 L7,17 Z']},
        'Fargate': {'bg': '#ED7100', 'paths': ['M12,3 A9,9 0 1,1 12,21 A9,9 0 1,1 12,3', 'M12,7 L12,17', 'M7,12 L17,12']},
        'ALB': {'bg': '#8C4FFF', 'paths': ['M12,3 C6,3 3,7 3,12 C3,17 6,21 12,21 C18,21 21,17 21,12 C21,7 18,3 12,3', 'M8,9 L8,15', 'M12,7 L12,17', 'M16,9 L16,15']},
        'NLB': {'bg': '#8C4FFF', 'paths': ['M3,12 L9,6', 'M3,12 L9,18', 'M9,6 L15,9', 'M9,6 L15,12', 'M9,18 L15,12', 'M9,18 L15,15', 'M15,9 L21,9', 'M15,12 L21,12', 'M15,15 L21,15']},
        'TargetGroup': {'bg': '#8C4FFF', 'paths': ['M12,3 A9,9 0 1,1 12,21 A9,9 0 1,1 12,3', 'M12,6 A6,6 0 1,1 12,18 A6,6 0 1,1 12,6', 'M12,9 A3,3 0 1,1 12,15 A3,3 0 1,1 12,9']},
        'VPCEndpoint': {'bg': '#8C4FFF', 'paths': ['M3,12 L7,12', 'M17,12 L21,12', 'M7,5 L17,5 L17,19 L7,19 Z', 'M10,9 L14,9', 'M10,12 L14,12', 'M10,15 L14,15']},
        'InternetGateway': {'bg': '#8C4FFF', 'paths': ['M12,2 A10,10 0 1,1 12,22 A10,10 0 1,1 12,2', 'M2,12 L22,12', 'M12,2 L12,22', 'M4,7 Q12,12 20,7', 'M4,17 Q12,12 20,17']},
        'NATGateway': {'bg': '#8C4FFF', 'paths': ['M4,6 L20,6 L20,18 L4,18 Z', 'M12,9 L12,18', 'M8,13 L12,9 L16,13']},
        'CloudFront': {'bg': '#8C4FFF', 'paths': ['M12,2 A10,10 0 1,1 12,22 A10,10 0 1,1 12,2', 'M2,12 L22,12', 'M12,2 Q6,12 12,22', 'M12,2 Q18,12 12,22']},
        'RDS': {'bg': '#3B48CC', 'paths': ['M5,5 C5,3 8,2 12,2 C16,2 19,3 19,5 L19,19 C19,21 16,22 12,22 C8,22 5,21 5,19 Z', 'M5,5 C5,7 8,8 12,8 C16,8 19,7 19,5', 'M5,12 C5,14 8,15 12,15 C16,15 19,14 19,12']},
        'DynamoDB': {'bg': '#3B48CC', 'paths': ['M12,2 L21,7 L21,17 L12,22 L3,17 L3,7 Z', 'M3,12 L21,12', 'M12,2 L12,22']},
        'ElastiCache': {'bg': '#3B48CC', 'paths': ['M12,2 A10,10 0 1,1 12,22 A10,10 0 1,1 12,2', 'M6,12 L10,8 L10,16 Z', 'M18,12 L14,8 L14,16 Z']},
        'S3': {'bg': '#3F8624', 'paths': ['M5,4 C5,3 8,2 12,2 C16,2 19,3 19,4 L19,20 C19,21 16,22 12,22 C8,22 5,21 5,20 Z', 'M5,4 C5,5 8,6 12,6 C16,6 19,5 19,4', 'M5,9 C5,10 8,11 12,11 C16,11 19,10 19,9', 'M5,14 C5,15 8,16 12,16 C16,16 19,15 19,14']},
        'EFS': {'bg': '#3F8624', 'paths': ['M3,4 L21,4 L21,20 L3,20 Z', 'M3,8 L21,8', 'M3,12 L21,12', 'M3,16 L21,16', 'M9,4 L9,20', 'M15,4 L15,20']},
        'SNS': {'bg': '#E7157B', 'paths': ['M12,2 L22,12 L12,22 L2,12 Z', 'M12,6 L12,18', 'M6,12 L18,12']},
        'SQS': {'bg': '#E7157B', 'paths': ['M3,5 L21,5 L21,19 L3,19 Z', 'M6,9 L18,9', 'M6,13 L18,13', 'M15,9 L18,9 L18,13']},
        'APIGateway': {'bg': '#E7157B', 'paths': ['M2,12 L9,5 L9,19 Z', 'M22,12 L15,5 L15,19 Z', 'M9,12 L15,12']},
        'EventBridge': {'bg': '#E7157B', 'paths': ['M3,5 L21,5 L21,19 L3,19 Z', 'M12,5 L12,19', 'M3,12 L21,12', 'M7,8 A3,3 0 1,1 7,16 A3,3 0 1,1 7,8', 'M17,8 A3,3 0 1,1 17,16 A3,3 0 1,1 17,8']},
        'SecurityGroup': {'bg': '#DD344C', 'paths': ['M12,2 L21,6 L21,14 L12,22 L3,14 L3,6 Z', 'M12,6 L12,14', 'M8,10 L16,10']},
        'IAM': {'bg': '#DD344C', 'paths': ['M12,3 C14,3 16,5 16,7 C16,9 14,11 12,11 C10,11 8,9 8,7 C8,5 10,3 12,3', 'M5,21 L5,17 C5,14 8,12 12,12 C16,12 19,14 19,17 L19,21']},
        'Default': {'bg': '#232F3E', 'paths': ['M4,4 L20,4 L20,20 L4,20 Z', 'M8,8 L16,8 L16,16 L8,16 Z']},
    }
    
    # グリッド設定
    GRID_SIZE = 20  # 小格子サイズ
    ICON_SIZE = 40  # アイコンサイズ（2x2 小格子）
    ICON_SPACING = 120  # 横方向アイコン間隔（アイコン40px + 間隔80px = 120px）
    ROW_SPACING = 120  # 縦方向行間隔（アイコン40px + 間隔80px = 120px）
    
    # 凡例用サービス名マッピング
    SERVICE_DISPLAY_NAMES = {
        'EC2': 'Amazon EC2',
        'Lambda': 'AWS Lambda',
        'EKS': 'Amazon EKS',
        'ECS': 'Amazon ECS',
        'Fargate': 'AWS Fargate',
        'ALB': 'Application LB',
        'NLB': 'Network LB',
        'TargetGroup': 'Target Group',
        'VPCEndpoint': 'VPC Endpoint',
        'InternetGateway': 'Internet GW',
        'NATGateway': 'NAT Gateway',
        'CloudFront': 'CloudFront',
        'RDS': 'Amazon RDS',
        'DynamoDB': 'DynamoDB',
        'ElastiCache': 'ElastiCache',
        'S3': 'Amazon S3',
        'EFS': 'Amazon EFS',
        'SNS': 'Amazon SNS',
        'SQS': 'Amazon SQS',
        'APIGateway': 'API Gateway',
        'EventBridge': 'EventBridge',
        'SecurityGroup': 'Security Group',
        'IAM': 'AWS IAM',
    }
    
    def __init__(self, reader, icons_dir=None):
        self.reader = reader
        self.node_positions = {}
        self.relationships_map = defaultdict(list)
        self.reverse_relationships = defaultdict(list)
        self.vpc_resource_ids = set()
        self.external_resource_ids = set()
        
        # アイコンディレクトリを設定
        if icons_dir:
            self.icons_dir = icons_dir
        else:
            # デフォルト: スクリプトと同じディレクトリの aws_icons/
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.icons_dir = os.path.join(script_dir, 'aws_icons')
        
        # 読み込んだアイコンをキャッシュ
        self.icon_cache = {}
        
        # アイコンディレクトリの存在確認
        if os.path.exists(self.icons_dir):
            print(f"  Using AWS icons from: {self.icons_dir}")
        else:
            print(f"  AWS icons directory not found: {self.icons_dir}")
            print(f"  Using default built-in icons")
    
    def _find_icon_file(self, icon_type):
        """アイコンファイルを検索"""
        if not os.path.exists(self.icons_dir):
            return None
        
        # マッピングからファイル名を取得
        target_filename = self.ICON_FILE_MAPPING.get(icon_type)
        if not target_filename:
            return None
        
        # ディレクトリを再帰的に検索
        for root, dirs, files in os.walk(self.icons_dir):
            for file in files:
                if file == target_filename:
                    return os.path.join(root, file)
                # 部分一致も試す（64/ や 48/ フォルダ対応）
                if target_filename.replace('_64.svg', '').replace('_48.svg', '') in file:
                    if file.endswith('.svg'):
                        return os.path.join(root, file)
        
        return None
    
    def _load_svg_icon(self, icon_type):
        """SVG アイコンを読み込み"""
        if icon_type in self.icon_cache:
            return self.icon_cache[icon_type]
        
        icon_path = self._find_icon_file(icon_type)
        if icon_path and os.path.exists(icon_path):
            try:
                with open(icon_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                self.icon_cache[icon_type] = ('file', svg_content, icon_path)
                return self.icon_cache[icon_type]
            except Exception as e:
                print(f"  Warning: Failed to load icon {icon_path}: {e}")
        
        # ファイルがない場合はデフォルトアイコン
        default = self.DEFAULT_ICONS.get(icon_type, self.DEFAULT_ICONS['Default'])
        self.icon_cache[icon_type] = ('default', default, None)
        return self.icon_cache[icon_type]
        
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
    
    def _get_connected_external_resources(self, vpc_res_id, external_resources):
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
    
    def _are_external_resources_related(self, ext_id1, ext_id2):
        """2つの外部リソースが関連しているか確認"""
        for target, _ in self.relationships_map.get(ext_id1, []):
            if target == ext_id2:
                return True
        for source, _ in self.reverse_relationships.get(ext_id1, []):
            if source == ext_id2:
                return True
        return False
    
    def _create_icon_svg(self, icon_type, x, y, res_id, label='', size=None):
        if size is None:
            size = self.ICON_SIZE
        
        self.node_positions[res_id] = (x + size/2, y + size/2, size, size)
        
        # ラベルを複数行に分割（長い名前に対応）
        label_lines = self._wrap_label(str(label) if label else '', max_chars=20)
        
        # アイコンを読み込み
        icon_source, icon_data, icon_path = self._load_svg_icon(icon_type)
        
        if icon_source == 'file':
            # 公式 SVG ファイルを使用
            return self._create_icon_from_svg_file(icon_data, x, y, res_id, label_lines, size)
        else:
            # デフォルトアイコンを使用
            return self._create_icon_from_default(icon_data, x, y, res_id, label_lines, size)
    
    def _wrap_label(self, label, max_chars=20):
        """ラベルを複数行に分割"""
        if not label:
            return []
        
        # 最大5行まで
        lines = []
        remaining = label
        
        for i in range(5):
            if not remaining:
                break
                
            if len(remaining) <= max_chars:
                lines.append(remaining)
                break
            
            # 分割位置を探す（ハイフン、アンダースコア、スペースなど）
            split_pos = -1
            for sep in ['-', '_', ' ', '/']:
                pos = remaining[:max_chars].rfind(sep)
                if pos > 0:
                    split_pos = pos + 1
                    break
            
            if split_pos <= 0:
                split_pos = max_chars
            
            lines.append(remaining[:split_pos])
            remaining = remaining[split_pos:]
            
            # 最後の行で残りがある場合は追加
            if i == 4 and remaining:
                # 5行目の末尾に ... を付けて残りを示す
                if len(lines[-1]) > max_chars - 3:
                    lines[-1] = lines[-1][:max_chars-3] + '...'
                else:
                    lines[-1] = lines[-1].rstrip('-_/ ') + '...'
        
        return lines
    
    def _create_label_svg(self, label_lines, size):
        """複数行ラベルのSVGを生成（相対座標、親グループ内）"""
        if not label_lines:
            return ''
        
        label_svg = ''
        line_height = 11
        start_y = size + 12
        
        for i, line in enumerate(label_lines):
            label_svg += f'      <text x="{size/2}" y="{start_y + i * line_height}" text-anchor="middle" fill="#333" font-size="9">{line}</text>\n'
        
        return label_svg
    
    def _create_icon_from_svg_file(self, svg_content, x, y, res_id, label_lines, size):
        """公式 SVG ファイルからアイコンを作成"""
        # SVG の viewBox を取得
        viewbox_match = re.search(r'viewBox="([^"]+)"', svg_content)
        if viewbox_match:
            vb = viewbox_match.group(1).split()
            if len(vb) == 4:
                vb_width = float(vb[2])
                vb_height = float(vb[3])
            else:
                vb_width = vb_height = 64
        else:
            vb_width = vb_height = 64
        
        # SVG の内部コンテンツを抽出（<svg>タグの中身）
        inner_match = re.search(r'<svg[^>]*>(.*)</svg>', svg_content, re.DOTALL)
        if inner_match:
            inner_content = inner_match.group(1)
        else:
            inner_content = svg_content
        
        # スケール計算
        scale = size / max(vb_width, vb_height)
        
        label_svg = self._create_label_svg(label_lines, size)
        
        return f'''    <g id="{res_id}" transform="translate({x},{y})">
      <g transform="scale({scale:.4f})">
{inner_content}
      </g>
{label_svg}    </g>
'''
    
    def _create_icon_from_default(self, icon_def, x, y, res_id, label_lines, size):
        """デフォルトアイコンを作成"""
        bg_color = icon_def['bg']
        paths = icon_def['paths']
        scale = size / 24
        
        path_elements = ''
        for p in paths:
            path_elements += f'        <path d="{p}" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>\n'
        
        label_svg = self._create_label_svg(label_lines, size)
        
        return f'''    <g id="{res_id}" transform="translate({x},{y})">
      <rect x="0" y="0" width="{size}" height="{size}" rx="4" fill="{bg_color}"/>
      <g transform="scale({scale:.3f})">
{path_elements}      </g>
{label_svg}    </g>
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
        
        # 使用されているアイコンタイプを収集
        used_icon_types = self._collect_used_icon_types(vpc_data, external_resources)
        
        content_svg, total_width, total_height = self._layout_all(vpc_data, external_resources)
        
        svg_content = self._build_svg_document(content_svg, total_width, total_height, used_icon_types)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f"\n✓ SVG diagram generated: {output_path}")
        print(f"  Size: {total_width} x {total_height}")
        return output_path
    
    def _collect_used_icon_types(self, vpc_data, external_resources):
        """使用されているアイコンタイプを収集"""
        used = set()
        
        for vpc_id, vpc_info in vpc_data.items():
            for subnet_info in vpc_info.get('subnets', {}).values():
                for icon_type, res_id, name in subnet_info.get('resources', []):
                    used.add(icon_type)
            for icon_type, res_id, name in vpc_info.get('vpc_level_resources', []):
                used.add(icon_type)
        
        for icon_type, res_id, name in external_resources:
            used.add(icon_type)
        
        # 順序を固定（カテゴリ順）
        order = ['EC2', 'Lambda', 'EKS', 'ECS', 'Fargate', 'ALB', 'NLB', 'TargetGroup', 
                 'VPCEndpoint', 'InternetGateway', 'NATGateway', 'CloudFront',
                 'RDS', 'DynamoDB', 'ElastiCache', 'S3', 'EFS', 
                 'SNS', 'SQS', 'APIGateway', 'EventBridge', 'SecurityGroup', 'IAM']
        
        return [t for t in order if t in used]
    
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
            external.append(('TargetGroup', name, self._get_name(name, data)))
        
        for name, data in reader.dynamodb_tables.items():
            external.append(('DynamoDB', name, self._get_name(name, data)))
        
        for name, data in reader.sns_topics.items():
            external.append(('SNS', name, self._get_name(name, data)))
        
        for name, data in reader.sqs_queues.items():
            external.append(('SQS', name, self._get_name(name, data)))
        
        for name, data in reader.cloudfront_distributions.items():
            external.append(('CloudFront', name, self._get_name(name, data)))
        
        for name, data in reader.api_gateways.items():
            external.append(('APIGateway', name, self._get_name(name, data)))
        
        for name, data in reader.cloudwatch_event_rules.items():
            external.append(('EventBridge', name, self._get_name(name, data)))
        
        if reader.iam_roles:
            external.append(('IAM', '__iam__', f'IAM ({len(reader.iam_roles)})'))
        
        if reader.efs_filesystems:
            external.append(('EFS', '__efs__', f'EFS ({len(reader.efs_filesystems)})'))
        
        for name, data in reader.ecs_clusters.items():
            external.append(('ECS', name, self._get_name(name, data)))
        
        vpc_lambda_names = set()
        for func_name, data in reader.lambda_functions.items():
            vpc_config = self._get_property(data, 'VpcConfig') or {}
            subnet_ids = vpc_config.get('SubnetIds', [])
            if subnet_ids and len(subnet_ids) > 0:
                vpc_lambda_names.add(func_name)
        
        for func_name, data in reader.lambda_functions.items():
            if func_name not in vpc_lambda_names:
                external.append(('Lambda', func_name, self._get_name(func_name, data)))
        
        return external
    
    def _layout_all(self, vpc_data, external_resources):
        svg_parts = []
        
        current_y = 60
        max_width = 400
        
        for vpc_id, vpc_info in vpc_data.items():
            vpc_svg, vpc_width, vpc_height = self._layout_vpc_with_external(
                vpc_id, vpc_info, external_resources, 20, current_y
            )
            svg_parts.append(vpc_svg)
            current_y += vpc_height + 40
            max_width = max(max_width, vpc_width + 40)
        
        # VPC 外リソース（左: 無関連、右: 関連あり）
        orphan_external, related_external = self._split_external_resources(external_resources)
        
        if orphan_external or related_external:
            ext_svg, ext_width, ext_height = self._layout_split_external(
                orphan_external, related_external, 20, current_y
            )
            svg_parts.append(ext_svg)
            current_y += ext_height + 20
            max_width = max(max_width, ext_width + 40)
        
        return '\n'.join(svg_parts), max_width, current_y
    
    def _split_external_resources(self, external_resources):
        """外部リソースを無関連と関連ありに分割"""
        # VPC 内リソースとの関連をチェック
        used_by_vpc = set()
        for vpc_id, vpc_info in self._organize_by_vpc().items():
            for subnet_info in vpc_info.get('subnets', {}).values():
                for icon_type, res_id, name in subnet_info.get('resources', []):
                    connected = self._get_connected_external_resources(res_id, external_resources)
                    for _, ext_id, _ in connected:
                        used_by_vpc.add(ext_id)
        
        # 外部リソース同士の関連をチェック
        related_pairs = set()
        ext_ids = [ext_id for _, ext_id, _ in external_resources]
        for i, ext_id1 in enumerate(ext_ids):
            for ext_id2 in ext_ids[i+1:]:
                if self._are_external_resources_related(ext_id1, ext_id2):
                    related_pairs.add(ext_id1)
                    related_pairs.add(ext_id2)
        
        orphan = []
        related = []
        
        for icon_type, res_id, name in external_resources:
            if res_id in used_by_vpc:
                continue  # VPC 内リソースと関連あり（既に表示済み）
            elif res_id in related_pairs:
                related.append((icon_type, res_id, name))
            else:
                orphan.append((icon_type, res_id, name))
        
        return orphan, related
    
    def _layout_split_external(self, orphan_external, related_external, start_x, start_y):
        """外部リソースを左右に分けて配置"""
        svg_parts = []
        
        spacing = self.ICON_SPACING
        row_spacing = self.ROW_SPACING
        icon_size = self.ICON_SIZE
        
        # タイトル
        svg_parts.append(f'    <text x="{start_x + 10}" y="{start_y + 15}" fill="#666" font-size="11">External Resources</text>\n')
        
        content_y = start_y + 30
        left_width = 0
        left_height = 0
        right_width = 0
        right_height = 0
        
        # 左側: 無関連リソース（3:2 矩形配置）
        if orphan_external:
            total = len(orphan_external)
            # 3:2 比率を目指す
            cols = max(1, int(math.sqrt(total * 1.5)))
            rows = math.ceil(total / cols)
            
            for i, (icon_type, res_id, name) in enumerate(orphan_external):
                col = i % cols
                row = i // cols
                x = start_x + 10 + col * spacing
                y = content_y + row * row_spacing
                svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name))
            
            left_width = cols * spacing + 20
            left_height = rows * row_spacing
        
        # 右側: 関連ありリソース
        if related_external:
            right_x = start_x + left_width + 60  # 区切り線の位置
            
            # 関連グループを見つける
            groups = self._find_related_groups(related_external)
            
            group_x = right_x
            max_group_height = 0
            
            for group in groups:
                # 各グループを縦に配置
                for i, (icon_type, res_id, name) in enumerate(group):
                    x = group_x
                    y = content_y + i * row_spacing
                    svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name))
                
                group_height = len(group) * row_spacing
                max_group_height = max(max_group_height, group_height)
                group_x += spacing
            
            right_width = group_x - right_x + 20
            right_height = max_group_height
            
            # 区切り線
            if orphan_external:
                line_x = start_x + left_width + 30
                svg_parts.append(f'    <line x1="{line_x}" y1="{content_y - 10}" x2="{line_x}" y2="{content_y + max(left_height, right_height)}" stroke="#ccc" stroke-width="1" stroke-dasharray="4,4"/>\n')
        
        total_width = left_width + right_width + 80
        total_height = max(left_height, right_height) + 40
        
        # 枠（背景なし）
        border = f'    <rect x="{start_x}" y="{start_y}" width="{total_width}" height="{total_height}" fill="none" stroke="#ccc" stroke-width="1" stroke-dasharray="5,3" rx="8"/>\n'
        
        return border + '\n'.join(svg_parts), total_width, total_height
    
    def _find_related_groups(self, resources):
        """関連するリソースをグループ化"""
        if not resources:
            return []
        
        groups = []
        used = set()
        
        for icon_type, res_id, name in resources:
            if res_id in used:
                continue
            
            group = [(icon_type, res_id, name)]
            used.add(res_id)
            
            # 関連するリソースを探す
            for icon_type2, res_id2, name2 in resources:
                if res_id2 in used:
                    continue
                if self._are_external_resources_related(res_id, res_id2):
                    group.append((icon_type2, res_id2, name2))
                    used.add(res_id2)
            
            groups.append(group)
        
        return groups
    
    def _layout_vpc_with_external(self, vpc_id, vpc_info, external_resources, start_x, start_y):
        svg_parts = []
        
        vpc_name = vpc_info['name']
        cidr = vpc_info['cidr']
        subnets = vpc_info['subnets']
        vpc_level_resources = vpc_info.get('vpc_level_resources', [])
        
        spacing = self.ICON_SPACING
        icon_size = self.ICON_SIZE
        
        current_y = start_y + 28
        max_content_width = 150
        
        subnet_items = list(subnets.items())
        if subnet_items:
            for subnet_id, subnet_info in subnet_items:
                s_svg, s_width, s_height = self._layout_subnet_aligned(
                    subnet_id, subnet_info, external_resources, start_x + 15, current_y
                )
                svg_parts.append(s_svg)
                max_content_width = max(max_content_width, s_width + 30)
                current_y += s_height + 20
        
        if vpc_level_resources:
            res_svg, res_width, res_height = self._layout_resource_row(
                vpc_level_resources, start_x + 15, current_y, 12
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
    
    def _layout_subnet_aligned(self, subnet_id, subnet_info, external_resources, start_x, start_y):
        svg_parts = []
        
        subnet_name = subnet_info['name']
        az = subnet_info['az']
        resources = subnet_info.get('resources', [])
        
        spacing = self.ICON_SPACING
        icon_size = self.ICON_SIZE
        
        if not resources:
            subnet_width = 80
            subnet_height = 60
            label = f"{subnet_name[:12]}"
            if az:
                label += f" ({az})"
            border = f'''    <rect x="{start_x}" y="{start_y}" width="{subnet_width}" height="{subnet_height}" 
          fill="none" stroke="#7AA116" stroke-width="1.5" rx="5"/>
    <text x="{start_x + 8}" y="{start_y + 14}" fill="#7AA116" font-size="9">{label}</text>
'''
            return border, subnet_width, subnet_height
        
        # 各 VPC 内リソースの関連外部リソースを取得
        res_with_external = []
        for icon_type, res_id, name in resources:
            connected_ext = self._get_connected_external_resources(res_id, external_resources)
            res_with_external.append((icon_type, res_id, name, connected_ext))
        
        res_with_external.sort(key=lambda x: len(x[3]), reverse=True)
        
        # 列位置を計算
        col_positions = []
        current_col = 0
        for icon_type, res_id, name, connected_ext in res_with_external:
            col_positions.append(current_col)
            ext_count = len(connected_ext)
            cols_needed = max(1, min(3, ext_count))
            current_col += cols_needed
        
        total_cols = current_col
        
        # VPC 内リソースを配置
        content_y = start_y + 24
        for i, (icon_type, res_id, name, connected_ext) in enumerate(res_with_external):
            col = col_positions[i]
            x = start_x + 10 + col * spacing
            svg_parts.append(self._create_icon_svg(icon_type, x, content_y, res_id, name))
        
        row_spacing = self.ROW_SPACING
        subnet_internal_height = icon_size + 20 + 28
        subnet_width = max(total_cols * spacing + 25, 80)
        
        label = f"{subnet_name[:12]}"
        if az:
            label += f" ({az})"
        
        border = f'''    <rect x="{start_x}" y="{start_y}" width="{subnet_width}" height="{subnet_internal_height}" 
          fill="none" stroke="#7AA116" stroke-width="1.5" rx="5"/>
    <text x="{start_x + 8}" y="{start_y + 14}" fill="#7AA116" font-size="9">{label}</text>
'''
        svg_parts.insert(0, border)
        
        # 外部リソースを配置
        ext_y = start_y + subnet_internal_height + 10
        max_ext_height = 0
        
        for i, (icon_type, res_id, name, connected_ext) in enumerate(res_with_external):
            if not connected_ext:
                continue
            
            col_start = col_positions[i]
            cols = min(3, len(connected_ext))
            rows = math.ceil(len(connected_ext) / cols)
            
            for j, (ext_type, ext_id, ext_name) in enumerate(connected_ext):
                ext_col = j % cols
                ext_row = j // cols
                x = start_x + 10 + (col_start + ext_col) * spacing
                y = ext_y + ext_row * row_spacing
                svg_parts.append(self._create_icon_svg(ext_type, x, y, ext_id, ext_name))
            
            ext_height = rows * row_spacing
            max_ext_height = max(max_ext_height, ext_height)
        
        total_height = subnet_internal_height + 10 + max_ext_height
        
        return '\n'.join(svg_parts), subnet_width, total_height
    
    def _layout_resource_row(self, resources, start_x, start_y, max_cols):
        svg_parts = []
        
        spacing = self.ICON_SPACING
        row_spacing = self.ROW_SPACING
        
        if not resources:
            return '', 0, 0
        
        cols = min(max_cols, len(resources))
        rows = math.ceil(len(resources) / cols)
        
        for i, (icon_type, res_id, name) in enumerate(resources):
            col = i % cols
            row = i // cols
            x = start_x + col * spacing
            y = start_y + row * row_spacing
            svg_parts.append(self._create_icon_svg(icon_type, x, y, res_id, name))
        
        width = cols * spacing
        height = rows * row_spacing + 5
        
        return '\n'.join(svg_parts), width, height
    
    def _create_legend(self, used_icon_types, start_x, start_y):
        """凡例を作成"""
        svg_parts = []
        
        icon_size = 24  # 凡例用の小さいアイコン
        item_spacing = 100  # 各凡例アイテムの間隔
        
        # 凡例タイトル
        svg_parts.append(f'    <text x="{start_x}" y="{start_y}" fill="#232F3E" font-size="10" font-weight="bold">Legend:</text>\n')
        
        x = start_x + 50
        y = start_y - 8
        
        for icon_type in used_icon_types:
            if icon_type not in self.SERVICE_DISPLAY_NAMES:
                continue
            
            display_name = self.SERVICE_DISPLAY_NAMES[icon_type]
            
            # アイコンを読み込み
            icon_source, icon_data, icon_path = self._load_svg_icon(icon_type)
            
            if icon_source == 'file':
                # 公式 SVG（簡略版）
                viewbox_match = re.search(r'viewBox="([^"]+)"', icon_data)
                if viewbox_match:
                    vb = viewbox_match.group(1).split()
                    vb_size = float(vb[2]) if len(vb) >= 3 else 64
                else:
                    vb_size = 64
                
                inner_match = re.search(r'<svg[^>]*>(.*)</svg>', icon_data, re.DOTALL)
                inner_content = inner_match.group(1) if inner_match else ''
                scale = icon_size / vb_size
                
                svg_parts.append(f'''    <g transform="translate({x},{y})">
      <g transform="scale({scale:.4f})">{inner_content}</g>
    </g>
''')
            else:
                # デフォルトアイコン
                bg_color = icon_data['bg']
                paths = icon_data['paths']
                scale = icon_size / 24
                
                path_elements = ''
                for p in paths:
                    path_elements += f'<path d="{p}" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
                
                svg_parts.append(f'''    <g transform="translate({x},{y})">
      <rect x="0" y="0" width="{icon_size}" height="{icon_size}" rx="3" fill="{bg_color}"/>
      <g transform="scale({scale:.3f})">{path_elements}</g>
    </g>
''')
            
            # サービス名
            svg_parts.append(f'    <text x="{x + icon_size + 5}" y="{y + icon_size/2 + 4}" fill="#333" font-size="9">{display_name}</text>\n')
            
            x += item_spacing
        
        return '\n'.join(svg_parts), x - start_x
    
    def _build_svg_document(self, content_svg, width, height, used_icon_types):
        edge_svg = '\n  <!-- Connections -->\n'
        drawn = set()
        for source, targets in self.relationships_map.items():
            for target, rel_type in targets:
                if (source, target) not in drawn:
                    edge_svg += self._create_edge_svg(source, target)
                    drawn.add((source, target))
        
        rel_count = sum(len(v) for v in self.relationships_map.values())
        grid = self.GRID_SIZE
        grid2 = grid * 2
        
        # 凡例を生成（右上に配置）
        legend_svg, legend_width = self._create_legend(used_icon_types, width - 50, 25)
        # 凡例の幅に応じて図の幅を調整
        legend_x = max(300, width - legend_width - 30)
        legend_svg, _ = self._create_legend(used_icon_types, legend_x, 25)
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{width}" height="{height}" 
     viewBox="0 0 {width} {height}"
     style="background-color: white; font-family: Arial, sans-serif;">
  
  <defs>
    <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#222"/>
    </marker>
    <pattern id="smallGrid" width="{grid}" height="{grid}" patternUnits="userSpaceOnUse">
      <path d="M {grid} 0 L 0 0 0 {grid}" fill="none" stroke="#ddd" stroke-width="0.5"/>
    </pattern>
    <pattern id="grid" width="{grid2}" height="{grid2}" patternUnits="userSpaceOnUse">
      <rect width="{grid2}" height="{grid2}" fill="url(#smallGrid)"/>
      <path d="M {grid2} 0 L 0 0 0 {grid2}" fill="none" stroke="#bbb" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#grid)"/>
  
  <text x="20" y="25" fill="#232F3E" font-size="14" font-weight="bold">AWS Architecture Diagram</text>
  <text x="20" y="42" fill="#666" font-size="10">VPCs: {len(self.reader.vpcs)} | Subnets: {len(self.reader.subnets)} | Relationships: {rel_count}</text>

  <!-- Legend -->
{legend_svg}

{content_svg}
{edge_svg}
</svg>'''

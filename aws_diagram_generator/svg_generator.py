# -*- coding: utf-8 -*-
"""
SVG 形式のアーキテクチャ図生成モジュール
AWS アイコンを使用した SVG 出力
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
        'RDS': '#3B48CC',
        'DynamoDB': '#3B48CC',
        'S3': '#3F8624',
        'EFS': '#3F8624',
        'SQS': '#E7157B',
        'SNS': '#E7157B',
        'VPC': '#8C4FFF',
        'Subnet': '#7AA116',
        'SecurityGroup': '#E7157B',
        'InternetGateway': '#8C4FFF',
        'NATGateway': '#8C4FFF',
        'VPCEndpoint': '#8C4FFF',
        'APIGateway': '#E7157B',
        'CloudWatch': '#E7157B',
        'IAM': '#DD344C',
        'default': '#232F3E',
    }
    
    # コンテナの色定義
    CONTAINER_COLORS = {
        'vpc': '#8C4FFF',
        'subnet_private': '#7AA116',
        'subnet_public': '#248814',
        'az': '#147EBA',
        'eks': '#ED7100',
        'security_group': '#E7157B',
    }
    
    def __init__(self, reader):
        self.reader = reader
        self.width = 1600
        self.height = 1200
        self.elements = []
        self.connections = []
        self.node_positions = {}  # リソース ID -> (x, y, width, height)
        
        # サブネットごとのリソース
        self.subnet_resources = defaultdict(list)
        
    def _organize_resources(self):
        """リソースをサブネットごとに整理"""
        reader = self.reader
        
        # EC2 -> Subnet
        for ec2_id, ec2_data in reader.ec2_instances.items():
            subnet_id = ec2_data.get('SubnetId') or ec2_data.get('Properties', {}).get('SubnetId')
            if subnet_id:
                self.subnet_resources[subnet_id].append(('EC2', ec2_id, ec2_data))
        
        # ECS Service -> Subnet
        for svc_name, svc_data in reader.ecs_services.items():
            subnet_ids = svc_data.get('SubnetIds', [])
            if subnet_ids:
                self.subnet_resources[subnet_ids[0]].append(('ECS', svc_name, svc_data))
        
        # EKS Cluster -> Subnet
        for cluster_name, cluster_data in reader.eks_clusters.items():
            subnet_ids = cluster_data.get('SubnetIds', [])
            if subnet_ids:
                self.subnet_resources[subnet_ids[0]].append(('EKS', cluster_name, cluster_data))
        
        # Lambda (VPC) -> Subnet
        for func_name, func_data in reader.lambda_functions.items():
            subnet_ids = func_data.get('SubnetIds', [])
            if subnet_ids:
                self.subnet_resources[subnet_ids[0]].append(('Lambda', func_name, func_data))
        
        # Load Balancer -> Subnet
        for lb_name, lb_data in reader.load_balancers.items():
            subnet_ids = lb_data.get('SubnetIds', []) or lb_data.get('Properties', {}).get('Subnets', [])
            if subnet_ids:
                lb_type = lb_data.get('LoadBalancerType', 'application')
                icon = 'ALB' if lb_type == 'application' else 'NLB'
                self.subnet_resources[subnet_ids[0]].append((icon, lb_name, lb_data))
        
        # NAT Gateway -> Subnet
        for nat_id, nat_data in reader.nat_gateways.items():
            subnet_id = nat_data.get('SubnetId') or nat_data.get('Properties', {}).get('SubnetId')
            if subnet_id:
                self.subnet_resources[subnet_id].append(('NATGateway', nat_id, nat_data))
        
        # RDS -> Subnet
        for db_id, db_data in reader.rds_instances.items():
            subnet_ids = db_data.get('SubnetIds', [])
            if subnet_ids:
                self.subnet_resources[subnet_ids[0]].append(('RDS', db_id, db_data))
    
    def _create_aws_icon(self, icon_type, x, y, size=48, label=''):
        """AWS スタイルのアイコンを作成"""
        color = self.ICON_COLORS.get(icon_type, self.ICON_COLORS['default'])
        
        # アイコンの背景（角丸四角形）
        icon_svg = f'''
        <g transform="translate({x}, {y})">
            <rect x="0" y="0" width="{size}" height="{size}" rx="5" ry="5" 
                  fill="{color}" stroke="white" stroke-width="2"/>
            <text x="{size/2}" y="{size/2 + 4}" 
                  text-anchor="middle" fill="white" font-size="10" font-weight="bold">
                {self._get_icon_symbol(icon_type)}
            </text>
            <text x="{size/2}" y="{size + 15}" 
                  text-anchor="middle" fill="#232F3E" font-size="10">
                {label[:20]}
            </text>
        </g>
        '''
        return icon_svg
    
    def _get_icon_symbol(self, icon_type):
        """アイコンのシンボルを取得"""
        symbols = {
            'EC2': '⬡',
            'ECS': '◎',
            'EKS': 'K8s',
            'Lambda': 'λ',
            'Fargate': 'Fg',
            'ALB': 'ALB',
            'NLB': 'NLB',
            'ELB': 'ELB',
            'RDS': 'DB',
            'DynamoDB': 'DDB',
            'S3': 'S3',
            'EFS': 'EFS',
            'SQS': 'SQS',
            'SNS': 'SNS',
            'VPCEndpoint': 'EP',
            'NATGateway': 'NAT',
            'InternetGateway': 'IGW',
        }
        return symbols.get(icon_type, icon_type[:3])
    
    def _create_container(self, x, y, width, height, label, color, dashed=False):
        """コンテナ（グループ枠）を作成"""
        dash_style = 'stroke-dasharray="8,4"' if dashed else ''
        
        container_svg = f'''
        <g>
            <rect x="{x}" y="{y}" width="{width}" height="{height}" 
                  fill="none" stroke="{color}" stroke-width="2" rx="5" ry="5" {dash_style}/>
            <text x="{x + 10}" y="{y + 18}" 
                  fill="{color}" font-size="14" font-weight="bold" 
                  text-decoration="underline">
                {label}
            </text>
        </g>
        '''
        return container_svg
    
    def _create_connection(self, x1, y1, x2, y2, color='#232F3E', arrow=True):
        """接続線を作成"""
        marker = 'marker-end="url(#arrowhead)"' if arrow else ''
        
        connection_svg = f'''
        <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" 
              stroke="{color}" stroke-width="1.5" {marker}/>
        '''
        return connection_svg
    
    def generate(self, output_dir, output_name='aws-architecture'):
        """SVG アーキテクチャ図を生成"""
        print("\n" + "=" * 80)
        print("Generating SVG Architecture Diagram...")
        print("=" * 80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_name}.svg")
        
        # リソースを整理
        self._organize_resources()
        
        reader = self.reader
        
        # レイアウト計算
        self._calculate_layout()
        
        # SVG コンテンツを構築
        svg_content = self._build_svg()
        
        # ファイルに書き込み
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f"✓ SVG diagram generated: {output_path}")
        return output_path
    
    def _calculate_layout(self):
        """レイアウトを計算"""
        reader = self.reader
        
        # VPC ごとの幅と高さを計算
        num_vpcs = len(reader.vpcs)
        
        max_subnets_per_vpc = 0
        for vpc_id in reader.vpcs:
            vpc_subnets = [s for s, d in reader.subnets.items() 
                          if (d.get('VpcId') or d.get('Properties', {}).get('VpcId')) == vpc_id]
            max_subnets_per_vpc = max(max_subnets_per_vpc, len(vpc_subnets))
        
        # 全体サイズを調整
        self.width = max(1600, max_subnets_per_vpc * 200 + 400)
        self.height = max(1200, num_vpcs * 400 + 300)
    
    def _build_svg(self):
        """SVG コンテンツを構築"""
        reader = self.reader
        svg_parts = []
        
        # SVG ヘッダー
        svg_parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{self.width}" height="{self.height}" 
     viewBox="0 0 {self.width} {self.height}"
     style="background-color: white;">
    
    <!-- 矢印マーカー定義 -->
    <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#232F3E"/>
        </marker>
    </defs>
    
    <!-- グリッド背景（オプション） -->
    <defs>
        <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>
        </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#grid)"/>
''')
        
        # VPC を描画
        vpc_y = 40
        for vpc_id, vpc_data in reader.vpcs.items():
            vpc_name = vpc_data.get('Name', vpc_id)
            cidr = vpc_data.get('CidrBlock', '')
            
            # この VPC のサブネットを取得
            vpc_subnets = {
                sid: sdata for sid, sdata in reader.subnets.items()
                if (sdata.get('VpcId') or sdata.get('Properties', {}).get('VpcId')) == vpc_id
            }
            
            if not vpc_subnets:
                continue
            
            # VPC の幅と高さを計算
            num_subnets = len(vpc_subnets)
            vpc_width = max(800, num_subnets * 180 + 100)
            vpc_height = 350
            
            # VPC コンテナ
            svg_parts.append(self._create_container(
                40, vpc_y, vpc_width, vpc_height,
                f"{vpc_name} ({cidr})",
                self.CONTAINER_COLORS['vpc']
            ))
            
            # サブネットを描画
            subnet_x = 60
            subnet_y = vpc_y + 40
            
            for subnet_id, subnet_data in vpc_subnets.items():
                subnet_name = subnet_data.get('Name', subnet_id)
                is_public = subnet_data.get('IsPublic', False)
                az = subnet_data.get('AvailabilityZone', '')
                
                color = self.CONTAINER_COLORS['subnet_public' if is_public else 'subnet_private']
                label = f"{subnet_name[:25]}"
                if az:
                    label += f" ({az[-2:]})"
                
                # サブネットコンテナ
                subnet_width = 160
                subnet_height = 280
                svg_parts.append(self._create_container(
                    subnet_x, subnet_y, subnet_width, subnet_height,
                    label, color
                ))
                
                # サブネット内のリソースを描画
                res_x = subnet_x + 20
                res_y = subnet_y + 40
                row_count = 0
                
                for res_type, res_id, res_data in self.subnet_resources.get(subnet_id, []):
                    res_name = ''
                    if isinstance(res_data, dict):
                        res_name = res_data.get('Name', res_id)
                    
                    svg_parts.append(self._create_aws_icon(
                        res_type, res_x, res_y, 48, res_name[:12]
                    ))
                    
                    # 位置を記録
                    self.node_positions[res_id] = (res_x + 24, res_y + 24, 48, 48)
                    
                    res_y += 70
                    row_count += 1
                    
                    if row_count >= 3:
                        res_x += 60
                        res_y = subnet_y + 40
                        row_count = 0
                
                subnet_x += subnet_width + 20
            
            vpc_y += vpc_height + 40
        
        # 外部リソースを右側に配置
        external_x = self.width - 200
        external_y = 60
        
        # S3
        if reader.s3_buckets:
            svg_parts.append(self._create_aws_icon(
                'S3', external_x, external_y, 48, f"S3 ({len(reader.s3_buckets)})"
            ))
            self.node_positions['s3'] = (external_x + 24, external_y + 24, 48, 48)
            external_y += 80
        
        # EFS
        if reader.efs_filesystems:
            svg_parts.append(self._create_aws_icon(
                'EFS', external_x, external_y, 48, f"EFS ({len(reader.efs_filesystems)})"
            ))
            self.node_positions['efs'] = (external_x + 24, external_y + 24, 48, 48)
            external_y += 80
        
        # DynamoDB
        if reader.dynamodb_tables:
            svg_parts.append(self._create_aws_icon(
                'DynamoDB', external_x, external_y, 48, f"DDB ({len(reader.dynamodb_tables)})"
            ))
            self.node_positions['dynamodb'] = (external_x + 24, external_y + 24, 48, 48)
            external_y += 80
        
        # SQS
        if reader.sqs_queues:
            svg_parts.append(self._create_aws_icon(
                'SQS', external_x, external_y, 48, f"SQS ({len(reader.sqs_queues)})"
            ))
            external_y += 80
        
        # SNS
        if reader.sns_topics:
            svg_parts.append(self._create_aws_icon(
                'SNS', external_x, external_y, 48, f"SNS ({len(reader.sns_topics)})"
            ))
            external_y += 80
        
        # Lambda (non-VPC)
        non_vpc_lambda = [f for f, d in reader.lambda_functions.items() if not d.get('SubnetIds')]
        if non_vpc_lambda:
            svg_parts.append(self._create_aws_icon(
                'Lambda', external_x, external_y, 48, f"Lambda ({len(non_vpc_lambda)})"
            ))
        
        # 接続線を描画
        svg_parts.append(self._draw_connections())
        
        # SVG フッター
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)
    
    def _draw_connections(self):
        """接続線を描画"""
        lines = []
        reader = self.reader
        
        # Load Balancer -> Target への接続
        for lb_name, lb_data in reader.load_balancers.items():
            if lb_name not in self.node_positions:
                continue
            
            lb_pos = self.node_positions[lb_name]
            
            # 同じ VPC 内のリソースに接続
            vpc_id = lb_data.get('VpcId')
            for ec2_id, ec2_data in reader.ec2_instances.items():
                if ec2_data.get('VpcId') == vpc_id and ec2_id in self.node_positions:
                    ec2_pos = self.node_positions[ec2_id]
                    lines.append(self._create_connection(
                        lb_pos[0], lb_pos[1] + 24,
                        ec2_pos[0], ec2_pos[1],
                        '#232F3E', True
                    ))
        
        return '\n'.join(lines)


class SecurityGroupSVGGenerator:
    """Security Group 関係の SVG 図を生成するクラス（あなたのサンプル画像と同じスタイル）"""
    
    def __init__(self, reader):
        self.reader = reader
        self.width = 2000
        self.height = 1200
        self.node_positions = {}
    
    def generate(self, output_dir, output_name='architecture_sg'):
        """Security Group 関係の SVG を生成"""
        print("\n" + "=" * 80)
        print("Generating Security Group SVG Diagram...")
        print("=" * 80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_name}.svg")
        
        reader = self.reader
        
        # SVG コンテンツを構築
        svg_parts = []
        
        # ヘッダー
        svg_parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{self.width}" height="{self.height}" 
     viewBox="0 0 {self.width} {self.height}"
     style="background-color: white;">
    
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
''')
        
        # VPC コンテナ
        for vpc_id, vpc_data in reader.vpcs.items():
            vpc_name = vpc_data.get('Name', vpc_id)
            
            svg_parts.append(f'''
    <g>
        <text x="50" y="30" fill="#232F3E" font-size="16" font-weight="bold" 
              text-decoration="underline">{vpc_name}</text>
        <line x1="50" y1="35" x2="{self.width - 50}" y2="35" 
              stroke="#00BCD4" stroke-width="2" stroke-dasharray="5,5"/>
    </g>
''')
        
        # Security Group をグループ化して描画
        sg_groups = defaultdict(list)
        
        # Load Balancer を Security Group でグループ化
        for lb_name, lb_data in reader.load_balancers.items():
            sg_ids = lb_data.get('SecurityGroupIds', []) or lb_data.get('Properties', {}).get('SecurityGroups', [])
            for sg_id in sg_ids:
                sg_groups[sg_id].append(('ALB', lb_name, lb_data))
        
        # EC2 を Security Group でグループ化
        for ec2_id, ec2_data in reader.ec2_instances.items():
            sg_ids = ec2_data.get('SecurityGroupIds', []) or ec2_data.get('Properties', {}).get('SecurityGroupIds', [])
            for sg_id in sg_ids:
                sg_groups[sg_id].append(('EC2', ec2_id, ec2_data))
        
        # EKS を Security Group でグループ化
        for eks_name, eks_data in reader.eks_clusters.items():
            sg_id = eks_data.get('SecurityGroupId')
            if sg_id:
                sg_groups[sg_id].append(('EKS', eks_name, eks_data))
        
        # Security Group ごとに描画
        sg_x = 60
        sg_y = 80
        
        for sg_id, resources in sg_groups.items():
            sg_data = reader.security_groups.get(sg_id, {})
            sg_name = sg_data.get('GroupName', sg_id)
            
            # グループの幅を計算
            num_resources = len(resources)
            sg_width = max(200, (num_resources // 4 + 1) * 80 + 40)
            sg_height = max(150, ((num_resources - 1) // 4 + 1) * 80 + 60)
            
            # Security Group コンテナ
            svg_parts.append(f'''
    <g>
        <rect x="{sg_x}" y="{sg_y}" width="{sg_width}" height="{sg_height}" 
              fill="none" stroke="#00BCD4" stroke-width="2" rx="5"/>
        <text x="{sg_x + 10}" y="{sg_y + 20}" fill="#00BCD4" font-size="12" 
              font-weight="bold" text-decoration="underline">{sg_name[:30]}</text>
''')
            
            # リソースアイコンを描画
            res_x = sg_x + 20
            res_y = sg_y + 40
            col = 0
            
            for res_type, res_id, res_data in resources:
                res_name = res_data.get('Name', res_id) if isinstance(res_data, dict) else res_id
                
                # ALB スタイルのアイコン
                svg_parts.append(f'''
        <g transform="translate({res_x}, {res_y})">
            <rect x="0" y="0" width="48" height="48" rx="5" fill="#8C4FFF" stroke="white" stroke-width="2"/>
            <circle cx="15" cy="24" r="8" fill="white" stroke="#8C4FFF" stroke-width="1"/>
            <circle cx="33" cy="15" r="6" fill="white" stroke="#8C4FFF" stroke-width="1"/>
            <circle cx="33" cy="33" r="6" fill="white" stroke="#8C4FFF" stroke-width="1"/>
            <line x1="20" y1="20" x2="28" y2="16" stroke="white" stroke-width="2"/>
            <line x1="20" y1="28" x2="28" y2="32" stroke="white" stroke-width="2"/>
            <text x="24" y="62" text-anchor="middle" fill="#232F3E" font-size="9">{res_name[:15]}</text>
        </g>
''')
                self.node_positions[res_id] = (res_x + 24 + sg_x, res_y + 24 + sg_y, 48, 48)
                
                col += 1
                res_x += 70
                if col >= 4:
                    col = 0
                    res_x = sg_x + 20
                    res_y += 80
            
            svg_parts.append('    </g>')
            
            sg_x += sg_width + 30
            if sg_x > self.width - 300:
                sg_x = 60
                sg_y += sg_height + 50
        
        # 接続線を描画（Security Group 間のルール）
        svg_parts.append(self._draw_sg_connections())
        
        svg_parts.append('</svg>')
        
        # ファイルに書き込み
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(svg_parts))
        
        print(f"✓ Security Group SVG diagram generated: {output_path}")
        return output_path
    
    def _draw_sg_connections(self):
        """Security Group 間の接続線を描画"""
        lines = []
        reader = self.reader
        
        # Security Group のルールから接続を抽出
        for sg_id, sg_data in reader.security_groups.items():
            ingress_rules = sg_data.get('Properties', {}).get('SecurityGroupIngress', [])
            
            for rule in ingress_rules:
                # 他の Security Group からの許可
                if isinstance(rule, dict):
                    source_sg = rule.get('UserIdGroupPairs', [{}])[0].get('GroupId') if rule.get('UserIdGroupPairs') else None
                    if source_sg and source_sg in self.node_positions and sg_id in self.node_positions:
                        src_pos = self.node_positions[source_sg]
                        dst_pos = self.node_positions[sg_id]
                        lines.append(f'''
    <line x1="{src_pos[0]}" y1="{src_pos[1]}" x2="{dst_pos[0]}" y2="{dst_pos[1]}" 
          stroke="#232F3E" stroke-width="1.5" marker-end="url(#arrowhead)"/>
''')
        
        return '\n'.join(lines)

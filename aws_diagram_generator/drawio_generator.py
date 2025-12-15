# -*- coding: utf-8 -*-
"""
Draw.io 形式のアーキテクチャ図生成モジュール
AWS 公式アイコンスタイルを使用
"""

import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import defaultdict
import base64
import urllib.parse


class DrawioGenerator:
    """Draw.io 形式のアーキテクチャ図を生成するクラス"""
    
    # AWS アイコンの定義（Draw.io の AWS 図形ライブラリを使用）
    AWS_ICONS = {
        # Compute
        'EC2': 'mxgraph.aws4.ec2',
        'ECS': 'mxgraph.aws4.ecs',
        'EKS': 'mxgraph.aws4.eks',
        'Lambda': 'mxgraph.aws4.lambda_function',
        'Fargate': 'mxgraph.aws4.fargate',
        
        # Container
        'Pod': 'mxgraph.kubernetes.pod',
        
        # Network
        'VPC': 'mxgraph.aws4.vpc',
        'Subnet': 'mxgraph.aws4.subnet_private',
        'SubnetPublic': 'mxgraph.aws4.subnet_public',
        'InternetGateway': 'mxgraph.aws4.internet_gateway',
        'NATGateway': 'mxgraph.aws4.nat_gateway',
        'ALB': 'mxgraph.aws4.application_load_balancer',
        'NLB': 'mxgraph.aws4.network_load_balancer',
        'ELB': 'mxgraph.aws4.elastic_load_balancing',
        'APIGateway': 'mxgraph.aws4.api_gateway',
        'TransitGateway': 'mxgraph.aws4.transit_gateway',
        'VPCEndpoint': 'mxgraph.aws4.endpoints',
        'Route53': 'mxgraph.aws4.route_53',
        
        # Storage
        'S3': 'mxgraph.aws4.s3',
        'EFS': 'mxgraph.aws4.elastic_file_system',
        'EBS': 'mxgraph.aws4.elastic_block_store',
        
        # Database
        'RDS': 'mxgraph.aws4.rds',
        'DynamoDB': 'mxgraph.aws4.dynamodb',
        'ElastiCache': 'mxgraph.aws4.elasticache',
        
        # Integration
        'SQS': 'mxgraph.aws4.sqs',
        'SNS': 'mxgraph.aws4.sns',
        'EventBridge': 'mxgraph.aws4.eventbridge',
        
        # Security
        'IAM': 'mxgraph.aws4.identity_and_access_management_iam',
        'SecretsManager': 'mxgraph.aws4.secrets_manager',
        
        # Management
        'CloudWatch': 'mxgraph.aws4.cloudwatch',
        'CloudFormation': 'mxgraph.aws4.cloudformation',
        'Backup': 'mxgraph.aws4.backup',
        
        # Container Registry
        'ECR': 'mxgraph.aws4.ecr',
        
        # General
        'User': 'mxgraph.aws4.user',
        'Users': 'mxgraph.aws4.users',
        'Client': 'mxgraph.aws4.client',
        'AWSCloud': 'mxgraph.aws4.aws_cloud',
        'Region': 'mxgraph.aws4.region',
    }
    
    # 色の定義
    COLORS = {
        'aws_cloud': '#232F3E',
        'region': '#147EBA',
        'vpc': '#8C4FFF',
        'az': '#147EBA',
        'subnet_private': '#7AA116',
        'subnet_public': '#248814',
        'eks': '#FF9900',
        'container': '#ED7100',
    }
    
    def __init__(self, reader):
        """
        Args:
            reader: AWSResourceReader または CloudFormationImporter のインスタンス
        """
        self.reader = reader
        self.cell_id = 2  # 0 と 1 は予約
        self.cells = []
        self.edges = []
        
        # サブネットごとのリソース
        self.subnet_resources = defaultdict(list)
        
        # 位置計算用
        self.current_x = 0
        self.current_y = 0
    
    def _next_id(self):
        """次のセル ID を取得"""
        self.cell_id += 1
        return str(self.cell_id)
    
    def _create_cell(self, value, x, y, width, height, style, parent='1'):
        """セルを作成"""
        cell_id = self._next_id()
        cell = {
            'id': cell_id,
            'value': value,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'style': style,
            'parent': parent,
            'vertex': '1'
        }
        self.cells.append(cell)
        return cell_id
    
    def _create_group(self, value, x, y, width, height, style, parent='1'):
        """グループ（コンテナ）を作成"""
        cell_id = self._next_id()
        cell = {
            'id': cell_id,
            'value': value,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'style': style,
            'parent': parent,
            'vertex': '1',
            'connectable': '0'
        }
        self.cells.append(cell)
        return cell_id
    
    def _create_edge(self, source, target, style=''):
        """エッジ（接続線）を作成"""
        edge_id = self._next_id()
        edge = {
            'id': edge_id,
            'source': source,
            'target': target,
            'style': style or 'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;strokeWidth=2;',
            'edge': '1',
            'parent': '1'
        }
        self.edges.append(edge)
        return edge_id
    
    def _aws_icon_style(self, icon_type, extra_style=''):
        """AWS アイコンのスタイルを生成"""
        icon = self.AWS_ICONS.get(icon_type, 'mxgraph.aws4.resourceIcon')
        style = f'sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];outlineConnect=0;fontColor=#232F3E;gradientColor=#F78E04;gradientDirection=north;fillColor=#D05C17;strokeColor=#ffffff;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;shape={icon};{extra_style}'
        return style
    
    def _container_style(self, color, dashed=False):
        """コンテナのスタイルを生成"""
        dash = 'dashed=1;dashPattern=8 8;' if dashed else 'dashed=0;'
        style = f'rounded=1;arcSize=10;{dash}strokeColor={color};strokeWidth=2;fillColor=none;fontColor={color};fontStyle=1;verticalAlign=top;align=left;spacingLeft=10;spacingTop=5;html=1;'
        return style
    
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
                self.subnet_resources[subnet_ids[0]].append(('Fargate', svc_name, svc_data))
        
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
        
        # RDS -> Subnet
        for db_id, db_data in reader.rds_instances.items():
            subnet_ids = db_data.get('SubnetIds', [])
            if subnet_ids:
                self.subnet_resources[subnet_ids[0]].append(('RDS', db_id, db_data))
        
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
        
        # VPC Endpoint -> Subnet（1つだけ）
        endpoint_added = set()
        for ep_id, ep_data in reader.vpc_endpoints.items():
            subnet_ids = ep_data.get('SubnetIds', []) or ep_data.get('Properties', {}).get('SubnetIds', [])
            for subnet_id in subnet_ids:
                if subnet_id not in endpoint_added:
                    self.subnet_resources[subnet_id].append(('VPCEndpoint', ep_id, ep_data))
                    endpoint_added.add(subnet_id)
                    break
    
    def generate(self, output_dir, output_name='aws-architecture'):
        """Draw.io ファイルを生成"""
        print("\n" + "=" * 80)
        print("Generating Draw.io Architecture Diagram...")
        print("=" * 80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_name}.drawio")
        
        # リソースを整理
        self._organize_resources()
        
        reader = self.reader
        
        # レイアウト計算
        layout = self._calculate_layout()
        
        # AWS Cloud コンテナ
        cloud_id = self._create_group(
            'AWS Cloud',
            40, 40,
            layout['cloud_width'], layout['cloud_height'],
            self._container_style(self.COLORS['aws_cloud'])
        )
        
        # AWS Cloud アイコン
        self._create_cell(
            '',
            50, 50, 40, 40,
            self._aws_icon_style('AWSCloud'),
            cloud_id
        )
        
        # Region コンテナ
        region_id = self._create_group(
            f"Region {reader.region if hasattr(reader, 'region') else 'ap-northeast-1'}",
            60, 100,
            layout['region_width'], layout['region_height'],
            self._container_style(self.COLORS['region'], dashed=True)
        )
        
        # VPC ごとに描画
        vpc_y = 60
        node_map = {}  # リソース ID -> セル ID のマッピング
        
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
            
            # AZ ごとにサブネットを分類
            az_subnets = defaultdict(list)
            for subnet_id, subnet_data in vpc_subnets.items():
                az = subnet_data.get('AvailabilityZone', 'unknown')
                az_subnets[az].append((subnet_id, subnet_data))
            
            # VPC の高さを計算
            vpc_height = max(300, len(az_subnets) * 250 + 100)
            vpc_width = layout['vpc_width']
            
            # VPC コンテナ
            vpc_cell_id = self._create_group(
                f"VPC {vpc_name}\n{cidr}",
                80, vpc_y,
                vpc_width, vpc_height,
                self._container_style(self.COLORS['vpc'])
            )
            node_map[vpc_id] = vpc_cell_id
            
            # VPC アイコン
            self._create_cell(
                '',
                90, vpc_y + 10, 30, 30,
                self._aws_icon_style('VPC'),
                vpc_cell_id
            )
            
            # IGW を描画
            for igw_id, igw_data in reader.internet_gateways.items():
                if igw_data.get('AttachedVpcId') == vpc_id:
                    igw_cell = self._create_cell(
                        'IGW',
                        30, vpc_y + 50, 48, 48,
                        self._aws_icon_style('InternetGateway'),
                        region_id
                    )
                    node_map[igw_id] = igw_cell
            
            # AZ ごとに描画
            az_y = 60
            for az, subnets in sorted(az_subnets.items()):
                az_label = az[-2:] if az else ''
                
                # AZ コンテナ
                az_cell_id = self._create_group(
                    f"Availability Zone {az_label}",
                    100, vpc_y + az_y,
                    vpc_width - 40, 220,
                    self._container_style(self.COLORS['az'], dashed=True)
                )
                
                # サブネットを描画
                subnet_x = 20
                for subnet_id, subnet_data in subnets:
                    subnet_name = subnet_data.get('Name', subnet_id)
                    is_public = subnet_data.get('IsPublic', False)
                    
                    # Private Subnet コンテナ
                    subnet_color = self.COLORS['subnet_public'] if is_public else self.COLORS['subnet_private']
                    subnet_label = 'Public subnet' if is_public else 'Private subnet'
                    
                    subnet_cell_id = self._create_group(
                        subnet_label,
                        subnet_x, 40,
                        300, 160,
                        self._container_style(subnet_color)
                    )
                    node_map[subnet_id] = subnet_cell_id
                    
                    # サブネット内のリソースを描画
                    res_x = 20
                    res_y = 40
                    
                    for res_type, res_id, res_data in self.subnet_resources.get(subnet_id, []):
                        res_name = res_data.get('Name', res_id)[:15] if isinstance(res_data, dict) else str(res_id)[:15]
                        
                        # EKS の場合は特別処理
                        if res_type == 'EKS':
                            # EKS コンテナ
                            eks_cell_id = self._create_group(
                                'EKS',
                                res_x, res_y,
                                180, 100,
                                self._container_style(self.COLORS['eks'], dashed=True)
                            )
                            node_map[res_id] = eks_cell_id
                            
                            # EKS アイコン
                            self._create_cell(
                                '',
                                10, 10, 40, 40,
                                self._aws_icon_style('EKS'),
                                eks_cell_id
                            )
                            
                            # Fargate と Pod を追加
                            self._create_cell(
                                'Fargate',
                                60, 30, 40, 40,
                                self._aws_icon_style('Fargate'),
                                eks_cell_id
                            )
                            self._create_cell(
                                'pod',
                                110, 30, 30, 30,
                                'sketch=0;html=1;aspect=fixed;strokeColor=none;shadow=0;fillColor=#326CE5;verticalAlign=top;labelPosition=center;verticalLabelPosition=bottom;shape=mxgraph.kubernetes.icon2;prIcon=pod;',
                                eks_cell_id
                            )
                            self._create_cell(
                                'pod',
                                145, 30, 30, 30,
                                'sketch=0;html=1;aspect=fixed;strokeColor=none;shadow=0;fillColor=#326CE5;verticalAlign=top;labelPosition=center;verticalLabelPosition=bottom;shape=mxgraph.kubernetes.icon2;prIcon=pod;',
                                eks_cell_id
                            )
                            
                            res_x += 200
                        else:
                            cell_id = self._create_cell(
                                res_type if res_type in ['ALB', 'NLB', 'EC2'] else '',
                                res_x, res_y, 48, 48,
                                self._aws_icon_style(res_type),
                                subnet_cell_id
                            )
                            node_map[res_id] = cell_id
                            res_x += 60
                        
                        if res_x > 240:
                            res_x = 20
                            res_y += 60
                    
                    subnet_x += 320
                
                az_y += 240
            
            vpc_y += vpc_height + 40
        
        # 外部サービスを右側に配置
        external_x = layout['cloud_width'] - 200
        external_y = 100
        
        # ECR
        if reader.ecs_clusters or reader.eks_clusters:
            ecr_cell = self._create_cell(
                'ECR',
                external_x, external_y, 48, 48,
                self._aws_icon_style('ECR'),
                cloud_id
            )
            external_y += 80
        
        # S3
        if reader.s3_buckets:
            s3_cell = self._create_cell(
                'S3',
                external_x + 80, external_y, 48, 48,
                self._aws_icon_style('S3'),
                cloud_id
            )
            node_map['s3'] = s3_cell
            external_y += 80
        
        # IAM
        iam_cell = self._create_cell(
            'IAM',
            external_x + 160, external_y - 80, 48, 48,
            self._aws_icon_style('IAM'),
            cloud_id
        )
        
        # CloudFormation
        cf_cell = self._create_cell(
            'Cloud-\nFormation',
            external_x + 240, external_y - 80, 48, 48,
            self._aws_icon_style('CloudFormation'),
            cloud_id
        )
        
        # Backup
        if reader.s3_buckets:
            backup_cell = self._create_cell(
                'AWS backup',
                external_x, external_y - 80, 48, 48,
                self._aws_icon_style('Backup'),
                cloud_id
            )
        
        # EFS
        if reader.efs_filesystems:
            efs_y = external_y + 100
            efs_cell = self._create_cell(
                'EFS',
                external_x + 100, efs_y, 48, 48,
                self._aws_icon_style('EFS'),
                cloud_id
            )
            node_map['efs'] = efs_cell
            
            # もう1つの EFS
            efs_cell2 = self._create_cell(
                'EFS',
                external_x + 100, efs_y + 200, 48, 48,
                self._aws_icon_style('EFS'),
                cloud_id
            )
        
        # 右端の外部サービス
        right_x = layout['cloud_width'] + 60
        right_y = 200
        
        # CloudWatch
        cw_cell = self._create_cell(
            'CloudWatch',
            right_x, right_y, 48, 48,
            self._aws_icon_style('CloudWatch')
        )
        right_y += 80
        
        # EventBridge
        eb_cell = self._create_cell(
            'EventBridge',
            right_x, right_y, 48, 48,
            self._aws_icon_style('EventBridge')
        )
        right_y += 80
        
        # SNS
        if reader.sns_topics:
            sns_cell = self._create_cell(
                'SNS',
                right_x, right_y, 48, 48,
                self._aws_icon_style('SNS')
            )
            node_map['sns'] = sns_cell
            right_y += 80
        
        # Lambda (non-VPC)
        non_vpc_lambda = [f for f, d in reader.lambda_functions.items() if not d.get('SubnetIds')]
        if non_vpc_lambda:
            lambda_cell = self._create_cell(
                'Lambda',
                right_x, right_y, 48, 48,
                self._aws_icon_style('Lambda')
            )
            node_map['lambda_external'] = lambda_cell
        
        # ユーザーアイコン（左側）
        user_cell = self._create_cell(
            'user',
            10, 300, 48, 48,
            self._aws_icon_style('User')
        )
        
        # API Gateway（左下）
        if reader.vpc_endpoints:
            apigw_cell = self._create_cell(
                'API Gateway',
                80, layout['cloud_height'] - 100, 48, 48,
                self._aws_icon_style('APIGateway'),
                cloud_id
            )
        
        # Transit Gateway
        tgw_cell = self._create_cell(
            'Transit Gateway',
            150, layout['cloud_height'] - 100, 48, 48,
            self._aws_icon_style('TransitGateway'),
            cloud_id
        )
        
        # 接続線を追加
        # IGW -> VPC 内のリソース
        for igw_id, igw_cell in [(k, v) for k, v in node_map.items() if 'igw' in k.lower()]:
            for lb_name, lb_data in reader.load_balancers.items():
                if lb_name in node_map:
                    self._create_edge(igw_cell, node_map[lb_name])
                    break
        
        # XML を生成
        xml_content = self._generate_xml()
        
        # ファイルに書き込み
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        print(f"✓ Draw.io diagram generated: {output_path}")
        return output_path
    
    def _calculate_layout(self):
        """レイアウトを計算"""
        reader = self.reader
        
        # VPC 数とサブネット数から幅と高さを計算
        num_vpcs = len(reader.vpcs)
        max_subnets = 0
        max_azs = 0
        
        for vpc_id, vpc_data in reader.vpcs.items():
            vpc_subnets = {
                sid: sdata for sid, sdata in reader.subnets.items()
                if (sdata.get('VpcId') or sdata.get('Properties', {}).get('VpcId')) == vpc_id
            }
            max_subnets = max(max_subnets, len(vpc_subnets))
            
            az_set = set()
            for sid, sdata in vpc_subnets.items():
                az = sdata.get('AvailabilityZone', '')
                if az:
                    az_set.add(az)
            max_azs = max(max_azs, len(az_set))
        
        vpc_width = max(800, max_subnets * 340 + 100)
        vpc_height = max(300, max_azs * 250 + 100)
        
        region_width = vpc_width + 100
        region_height = num_vpcs * (vpc_height + 40) + 150
        
        cloud_width = region_width + 400
        cloud_height = region_height + 200
        
        return {
            'vpc_width': vpc_width,
            'vpc_height': vpc_height,
            'region_width': region_width,
            'region_height': region_height,
            'cloud_width': cloud_width,
            'cloud_height': cloud_height,
        }
    
    def _generate_xml(self):
        """Draw.io XML を生成"""
        # ルート要素
        mxfile = ET.Element('mxfile')
        mxfile.set('host', 'app.diagrams.net')
        mxfile.set('modified', '2024-01-01T00:00:00.000Z')
        mxfile.set('agent', 'AWS Architecture Generator')
        mxfile.set('version', '1.0')
        mxfile.set('type', 'device')
        
        # diagram 要素
        diagram = ET.SubElement(mxfile, 'diagram')
        diagram.set('id', 'aws-architecture')
        diagram.set('name', 'AWS Architecture')
        
        # mxGraphModel 要素
        graph_model = ET.SubElement(diagram, 'mxGraphModel')
        graph_model.set('dx', '0')
        graph_model.set('dy', '0')
        graph_model.set('grid', '1')
        graph_model.set('gridSize', '10')
        graph_model.set('guides', '1')
        graph_model.set('tooltips', '1')
        graph_model.set('connect', '1')
        graph_model.set('arrows', '1')
        graph_model.set('fold', '1')
        graph_model.set('page', '1')
        graph_model.set('pageScale', '1')
        graph_model.set('pageWidth', '1600')
        graph_model.set('pageHeight', '1200')
        graph_model.set('math', '0')
        graph_model.set('shadow', '0')
        
        # root 要素
        root = ET.SubElement(graph_model, 'root')
        
        # 基本セル
        cell0 = ET.SubElement(root, 'mxCell')
        cell0.set('id', '0')
        
        cell1 = ET.SubElement(root, 'mxCell')
        cell1.set('id', '1')
        cell1.set('parent', '0')
        
        # セルを追加
        for cell in self.cells:
            mx_cell = ET.SubElement(root, 'mxCell')
            mx_cell.set('id', cell['id'])
            mx_cell.set('value', cell['value'])
            mx_cell.set('style', cell['style'])
            mx_cell.set('parent', cell['parent'])
            mx_cell.set('vertex', cell.get('vertex', '1'))
            
            if cell.get('connectable') == '0':
                mx_cell.set('connectable', '0')
            
            # geometry
            geometry = ET.SubElement(mx_cell, 'mxGeometry')
            geometry.set('x', str(cell['x']))
            geometry.set('y', str(cell['y']))
            geometry.set('width', str(cell['width']))
            geometry.set('height', str(cell['height']))
            geometry.set('as', 'geometry')
        
        # エッジを追加
        for edge in self.edges:
            mx_cell = ET.SubElement(root, 'mxCell')
            mx_cell.set('id', edge['id'])
            mx_cell.set('style', edge['style'])
            mx_cell.set('parent', edge['parent'])
            mx_cell.set('edge', '1')
            mx_cell.set('source', edge['source'])
            mx_cell.set('target', edge['target'])
            
            geometry = ET.SubElement(mx_cell, 'mxGeometry')
            geometry.set('relative', '1')
            geometry.set('as', 'geometry')
        
        # XML を文字列に変換
        xml_str = ET.tostring(mxfile, encoding='unicode')
        
        # 整形
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')

# -*- coding: utf-8 -*-
"""
各 YAML ファイルから完全なアーキテクチャ図を生成（修正版）
- すべてのリソースを表示
- !Ref と !GetAtt の関係を自動検出して線で接続
- DependsOn も考慮
"""

import os
import yaml
from collections import defaultdict
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import VPC, InternetGateway, PrivateSubnet, PublicSubnet, NATGateway, ELB, ALB, NLB, Route53, CF, APIGateway, VPCRouter
from diagrams.aws.compute import EC2, ECS, EKS, Lambda, Batch
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift, Neptune
from diagrams.aws.storage import S3, EBS, EFS, FSx
from diagrams.aws.integration import SQS, SNS, Eventbridge, StepFunctions, MQ
from diagrams.aws.security import IAM, SecretsManager, KMS, WAF
from diagrams.aws.management import Cloudwatch, SystemsManager, Cloudformation
from diagrams.generic.blank import Blank


# ==================== CloudFormation YAML タグ処理 ====================

class CloudFormationYAMLLoader(yaml.SafeLoader):
    pass


def ref_constructor(loader, node):
    return {'Ref': loader.construct_scalar(node)}

def getatt_constructor(loader, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
        return {'Fn::GetAtt': value.split('.')}
    else:
        return {'Fn::GetAtt': loader.construct_sequence(node)}

def sub_constructor(loader, node):
    if isinstance(node, yaml.ScalarNode):
        return {'Fn::Sub': loader.construct_scalar(node)}
    else:
        return {'Fn::Sub': loader.construct_sequence(node)}

def join_constructor(loader, node):
    return {'Fn::Join': loader.construct_sequence(node)}

def select_constructor(loader, node):
    return {'Fn::Select': loader.construct_sequence(node)}

def getazs_constructor(loader, node):
    return {'Fn::GetAZs': loader.construct_scalar(node)}

def importvalue_constructor(loader, node):
    return {'Fn::ImportValue': loader.construct_scalar(node)}

def split_constructor(loader, node):
    return {'Fn::Split': loader.construct_sequence(node)}

def findinmap_constructor(loader, node):
    return {'Fn::FindInMap': loader.construct_sequence(node)}

def cidr_constructor(loader, node):
    return {'Fn::Cidr': loader.construct_sequence(node)}

def base64_constructor(loader, node):
    return {'Fn::Base64': loader.construct_scalar(node)}

def if_constructor(loader, node):
    return {'Fn::If': loader.construct_sequence(node)}

def equals_constructor(loader, node):
    return {'Fn::Equals': loader.construct_sequence(node)}

def not_constructor(loader, node):
    return {'Fn::Not': loader.construct_sequence(node)}

def and_constructor(loader, node):
    return {'Fn::And': loader.construct_sequence(node)}

def or_constructor(loader, node):
    return {'Fn::Or': loader.construct_sequence(node)}


CloudFormationYAMLLoader.add_constructor('!Ref', ref_constructor)
CloudFormationYAMLLoader.add_constructor('!GetAtt', getatt_constructor)
CloudFormationYAMLLoader.add_constructor('!Sub', sub_constructor)
CloudFormationYAMLLoader.add_constructor('!Join', join_constructor)
CloudFormationYAMLLoader.add_constructor('!Select', select_constructor)
CloudFormationYAMLLoader.add_constructor('!GetAZs', getazs_constructor)
CloudFormationYAMLLoader.add_constructor('!ImportValue', importvalue_constructor)
CloudFormationYAMLLoader.add_constructor('!Split', split_constructor)
CloudFormationYAMLLoader.add_constructor('!FindInMap', findinmap_constructor)
CloudFormationYAMLLoader.add_constructor('!Cidr', cidr_constructor)
CloudFormationYAMLLoader.add_constructor('!Base64', base64_constructor)
CloudFormationYAMLLoader.add_constructor('!If', if_constructor)
CloudFormationYAMLLoader.add_constructor('!Equals', equals_constructor)
CloudFormationYAMLLoader.add_constructor('!Not', not_constructor)
CloudFormationYAMLLoader.add_constructor('!And', and_constructor)
CloudFormationYAMLLoader.add_constructor('!Or', or_constructor)


def parse_yaml(yaml_file):
    """CloudFormation YAML ファイルを解析"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.load(f, Loader=CloudFormationYAMLLoader)
    except Exception as e:
        print(f"    Error: {yaml_file} - {e}")
        return None


# ==================== アイコンマッピング ====================

def get_icon_class(resource_type):
    """リソースタイプに対応するアイコンクラスを取得"""
    
    icon_map = {
        # ネットワーク
        'AWS::EC2::VPC': VPC,
        'AWS::EC2::Subnet': PrivateSubnet,
        'AWS::EC2::InternetGateway': InternetGateway,
        'AWS::EC2::VPCGatewayAttachment': InternetGateway,
        'AWS::EC2::NatGateway': NATGateway,
        'AWS::EC2::RouteTable': VPCRouter,
        'AWS::EC2::Route': VPCRouter,
        'AWS::EC2::SubnetRouteTableAssociation': VPCRouter,
        'AWS::EC2::SecurityGroup': VPCRouter,  # SecurityGroup アイコンがないので VPCRouter を使用
        'AWS::ElasticLoadBalancingV2::LoadBalancer': ALB,
        'AWS::ElasticLoadBalancingV2::TargetGroup': ALB,
        'AWS::ElasticLoadBalancing::LoadBalancer': ELB,
        'AWS::Route53::HostedZone': Route53,
        'AWS::CloudFront::Distribution': CF,
        'AWS::ApiGateway::RestApi': APIGateway,
        
        # コンピューティング
        'AWS::EC2::Instance': EC2,
        'AWS::ECS::Cluster': ECS,
        'AWS::ECS::Service': ECS,
        'AWS::ECS::TaskDefinition': ECS,
        'AWS::EKS::Cluster': EKS,
        'AWS::Lambda::Function': Lambda,
        'AWS::Batch::JobDefinition': Batch,
        
        # データベース
        'AWS::RDS::DBInstance': RDS,
        'AWS::RDS::DBCluster': RDS,
        'AWS::RDS::DBSubnetGroup': RDS,
        'AWS::DynamoDB::Table': Dynamodb,
        'AWS::ElastiCache::CacheCluster': ElastiCache,
        'AWS::ElastiCache::ReplicationGroup': ElastiCache,
        'AWS::Redshift::Cluster': Redshift,
        'AWS::Neptune::DBCluster': Neptune,
        
        # ストレージ
        'AWS::S3::Bucket': S3,
        'AWS::EBS::Volume': EBS,
        'AWS::EFS::FileSystem': EFS,
        'AWS::FSx::FileSystem': FSx,
        
        # 統合
        'AWS::SQS::Queue': SQS,
        'AWS::SNS::Topic': SNS,
        'AWS::Events::Rule': Eventbridge,
        'AWS::StepFunctions::StateMachine': StepFunctions,
        'AWS::MQ::Broker': MQ,
        
        # セキュリティ
        'AWS::IAM::Role': IAM,
        'AWS::IAM::Policy': IAM,
        'AWS::IAM::InstanceProfile': IAM,
        'AWS::SecretsManager::Secret': SecretsManager,
        'AWS::KMS::Key': KMS,
        'AWS::WAFv2::WebACL': WAF,
        
        # 管理
        'AWS::CloudWatch::Alarm': Cloudwatch,
        'AWS::SSM::Parameter': SystemsManager,
        'AWS::CloudFormation::Stack': Cloudformation,
    }
    
    return icon_map.get(resource_type)


def extract_string_value(value):
    """組み込み関数を含む値から文字列を抽出"""
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        if 'Ref' in value:
            return f"Ref:{value['Ref']}"
        elif 'Fn::Sub' in value:
            sub_value = value['Fn::Sub']
            if isinstance(sub_value, str):
                return sub_value
            else:
                return str(sub_value[0]) if sub_value else "Sub:..."
        else:
            return str(value)
    else:
        return str(value)


def get_resource_label(resource_id, resource_data):
    """リソースのラベルを取得"""
    props = resource_data.get('Properties', {})
    
    # Tags から名前を取得
    tags = props.get('Tags', [])
    if tags:
        for tag in tags:
            if isinstance(tag, dict) and tag.get('Key') == 'Name':
                name = extract_string_value(tag.get('Value'))
                if name and name != 'Name' and not name.startswith('Ref:') and not name.startswith('Sub:'):
                    if len(name) > 25:
                        return name[:22] + "..."
                    return name
    
    # その他のプロパティから名前を取得
    for key in ['FunctionName', 'DBInstanceIdentifier', 'BucketName', 
                'TableName', 'ClusterName', 'QueueName', 'TopicName', 'Name']:
        if key in props:
            name = extract_string_value(props[key])
            if name and not name.startswith('Ref:'):
                if len(name) > 25:
                    return name[:22] + "..."
                return name
    
    # リソース ID を短縮
    if len(resource_id) > 20:
        return resource_id[:17] + "..."
    
    return resource_id


def find_all_references(resources):
    """すべてのリソースの参照関係を検索"""
    relationships = []
    
    for source_id, source_data in resources.items():
        props = source_data.get('Properties', {})
        
        # DependsOn を検索
        depends_on = source_data.get('DependsOn', [])
        if isinstance(depends_on, str):
            depends_on = [depends_on]
        
        for target_id in depends_on:
            relationships.append({
                'from': source_id,
                'to': target_id,
                'type': 'depends',
                'label': 'DependsOn'
            })
        
        # !Ref を検索
        def find_refs(obj, path=""):
            refs = []
            if isinstance(obj, dict):
                if 'Ref' in obj:
                    refs.append(obj['Ref'])
                else:
                    for key, value in obj.items():
                        refs.extend(find_refs(value, f"{path}.{key}" if path else key))
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    refs.extend(find_refs(item, f"{path}[{idx}]"))
            return refs
        
        refs = find_refs(props)
        for target_id in refs:
            if target_id in resources:
                relationships.append({
                    'from': source_id,
                    'to': target_id,
                    'type': 'ref',
                    'label': 'Ref'
                })
        
        # !GetAtt を検索
        def find_getattrs(obj):
            getattrs = []
            if isinstance(obj, dict):
                if 'Fn::GetAtt' in obj:
                    attrs = obj['Fn::GetAtt']
                    if isinstance(attrs, list) and len(attrs) > 0:
                        getattrs.append(attrs[0])
                    elif isinstance(attrs, str):
                        getattrs.append(attrs.split('.')[0])
                else:
                    for value in obj.values():
                        getattrs.extend(find_getattrs(value))
            elif isinstance(obj, list):
                for item in obj:
                    getattrs.extend(find_getattrs(item))
            return getattrs
        
        getattrs = find_getattrs(props)
        for target_id in getattrs:
            if target_id in resources:
                relationships.append({
                    'from': source_id,
                    'to': target_id,
                    'type': 'getattr',
                    'label': 'GetAtt'
                })
    
    return relationships


def categorize_resources(resources):
    """リソースをカテゴリ別に分類"""
    categories = {
        'Network': [],
        'Compute': [],
        'Database': [],
        'Storage': [],
        'Integration': [],
        'Security': [],
        'Management': [],
        'Other': []
    }
    
    category_map = {
        'AWS::EC2::VPC': 'Network',
        'AWS::EC2::Subnet': 'Network',
        'AWS::EC2::InternetGateway': 'Network',
        'AWS::EC2::VPCGatewayAttachment': 'Network',
        'AWS::EC2::NatGateway': 'Network',
        'AWS::EC2::RouteTable': 'Network',
        'AWS::EC2::Route': 'Network',
        'AWS::EC2::SubnetRouteTableAssociation': 'Network',
        'AWS::EC2::SecurityGroup': 'Security',
        'AWS::ElasticLoadBalancingV2::LoadBalancer': 'Network',
        'AWS::ElasticLoadBalancingV2::TargetGroup': 'Network',
        'AWS::Route53::HostedZone': 'Network',
        'AWS::CloudFront::Distribution': 'Network',
        'AWS::ApiGateway::RestApi': 'Network',
        
        'AWS::EC2::Instance': 'Compute',
        'AWS::ECS::Cluster': 'Compute',
        'AWS::ECS::Service': 'Compute',
        'AWS::ECS::TaskDefinition': 'Compute',
        'AWS::EKS::Cluster': 'Compute',
        'AWS::Lambda::Function': 'Compute',
        'AWS::Batch::JobDefinition': 'Compute',
        
        'AWS::RDS::DBInstance': 'Database',
        'AWS::RDS::DBCluster': 'Database',
        'AWS::RDS::DBSubnetGroup': 'Database',
        'AWS::DynamoDB::Table': 'Database',
        'AWS::ElastiCache::CacheCluster': 'Database',
        'AWS::ElastiCache::ReplicationGroup': 'Database',
        
        'AWS::S3::Bucket': 'Storage',
        'AWS::EBS::Volume': 'Storage',
        'AWS::EFS::FileSystem': 'Storage',
        
        'AWS::SQS::Queue': 'Integration',
        'AWS::SNS::Topic': 'Integration',
        'AWS::Events::Rule': 'Integration',
        'AWS::StepFunctions::StateMachine': 'Integration',
        
        'AWS::IAM::Role': 'Security',
        'AWS::IAM::Policy': 'Security',
        'AWS::IAM::InstanceProfile': 'Security',
        'AWS::SecretsManager::Secret': 'Security',
        'AWS::KMS::Key': 'Security',
        
        'AWS::CloudWatch::Alarm': 'Management',
        'AWS::SSM::Parameter': 'Management',
    }
    
    for resource_id, resource_data in resources.items():
        resource_type = resource_data.get('Type', '')
        category = category_map.get(resource_type, 'Other')
        categories[category].append((resource_id, resource_data, resource_type))
    
    # 空のカテゴリを削除
    return {k: v for k, v in categories.items() if v}


def generate_diagram_from_yaml(yaml_file, output_dir='diagrams'):
    """単一の YAML ファイルから完全な図を生成"""
    
    template = parse_yaml(yaml_file)
    if not template or 'Resources' not in template:
        print(f"  Skip: {yaml_file} - No resources found")
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    resources = template['Resources']
    
    print(f"  Found {len(resources)} resource(s)")
    
    # 出力ファイル名
    base_name = os.path.splitext(os.path.basename(yaml_file))[0]
    output_filename = os.path.join(output_dir, base_name)
    
    # 参照関係を検索
    relationships = find_all_references(resources)
    print(f"  Found {len(relationships)} relationship(s)")
    
    # リソースをカテゴリ別に分類
    categories = categorize_resources(resources)
    
    # 図を生成
    graph_attr = {
        "fontsize": "12",
        "bgcolor": "white",
        "pad": "1.0",
        "nodesep": "1.0",
        "ranksep": "1.5",
    }
    
    with Diagram(
        f"{base_name} ({len(resources)} resources)",
        filename=output_filename,
        show=False,
        direction="TB",
        outformat="png",
        graph_attr=graph_attr
    ):
        
        nodes = {}
        
        # カテゴリごとにクラスタを作成
        for category, resource_list in categories.items():
            
            with Cluster(f"{category} ({len(resource_list)})"):
                
                for resource_id, resource_data, resource_type in resource_list:
                    icon_class = get_icon_class(resource_type)
                    
                    if icon_class:
                        label = get_resource_label(resource_id, resource_data)
                        node = icon_class(label)
                        nodes[resource_id] = node
                    else:
                        # アイコンがない場合は Blank を使用
                        label = get_resource_label(resource_id, resource_data)
                        node = Blank(label)
                        nodes[resource_id] = node
                        print(f"    Warning: No icon for {resource_type} ({resource_id}), using Blank")
        
        # 関係を描画
        for rel in relationships:
            source_id = rel['from']
            target_id = rel['to']
            rel_type = rel['type']
            label = rel['label']
            
            if source_id in nodes and target_id in nodes:
                # 関係のタイプによって色を変える
                if rel_type == 'depends':
                    nodes[source_id] >> Edge(color="red", style="dashed") >> nodes[target_id]
                elif rel_type == 'ref':
                    nodes[source_id] >> Edge(color="blue", style="solid") >> nodes[target_id]
                elif rel_type == 'getattr':
                    nodes[source_id] >> Edge(color="green", style="dotted") >> nodes[target_id]
    
    print(f"  -> Generated: {output_filename}.png")
    return f"{output_filename}.png"


def generate_all_diagrams(input_dir='aws-resources', output_dir='aws-diagrams'):
    """すべての YAML ファイルから図を生成"""
    
    print("="*80)
    print("CloudFormation Complete Architecture Diagram Generator")
    print("="*80)
    print(f"\nInput directory: {input_dir}")
    print(f"Output directory: {output_dir}\n")
    
    yaml_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml_files.append(os.path.join(root, file))
    
    print(f"Found {len(yaml_files)} YAML file(s)\n")
    
    success_count = 0
    error_count = 0
    
    for yaml_file in yaml_files:
        print(f"Processing: {os.path.basename(yaml_file)}")
        
        try:
            result = generate_diagram_from_yaml(yaml_file, output_dir)
            if result:
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            print(f"  -> Error: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
    
    print("\n" + "="*80)
    print(f"Complete!")
    print(f"  Success: {success_count} diagram(s)")
    print(f"  Errors: {error_count} file(s)")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    print("="*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate complete architecture diagrams from CloudFormation YAML files')
    parser.add_argument('--input-dir', default='aws-resources', help='Input directory containing YAML files')
    parser.add_argument('--output-dir', default='aws-diagrams', help='Output directory for diagrams')
    
    args = parser.parse_args()
    
    generate_all_diagrams(args.input_dir, args.output_dir)


if __name__ == '__main__':
    main()
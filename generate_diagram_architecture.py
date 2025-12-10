# -*- coding: utf-8 -*-
"""
フォルダ内のすべての CloudFormation YAML から1つの大きなアーキテクチャ図を生成
修正版 v2：ファイルパス問題を修正
"""

import os
import yaml
from collections import defaultdict
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import VPC, InternetGateway, PrivateSubnet, PublicSubnet, NATGateway, ELB, ALB, NLB, Route53, CF, APIGateway, VPCRouter
from diagrams.aws.compute import EC2, ECS, EKS, Lambda, Batch, ElasticBeanstalk
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift, Neptune, Database
from diagrams.aws.storage import S3, EBS, EFS, FSx, Storage, Backup
from diagrams.aws.integration import SQS, SNS, Eventbridge, StepFunctions, MQ
from diagrams.aws.security import IAM, SecretsManager, KMS, WAF, Shield, CertificateManager
from diagrams.aws.management import Cloudwatch, SystemsManager, Cloudformation, Config
from diagrams.generic.blank import Blank


# ==================== CloudFormation YAML タグ処理 ====================

class CloudFormationYAMLLoader(yaml.SafeLoader):
    """CloudFormation タグをサポートするカスタム YAML Loader"""
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


# すべてのタグを登録
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
        print(f"    Warning: Failed to parse {yaml_file} - {e}")
        return None


# ==================== 拡張アイコンマッピング ====================

def get_icon_class(resource_type):
    """リソースタイプに対応するアイコンクラスを取得（拡張版）"""
    
    icon_map = {
        # Network
        'AWS::EC2::VPC': VPC,
        'AWS::EC2::Subnet': PrivateSubnet,
        'AWS::EC2::InternetGateway': InternetGateway,
        'AWS::EC2::VPCGatewayAttachment': InternetGateway,
        'AWS::EC2::NatGateway': NATGateway,
        'AWS::EC2::EIP': InternetGateway,
        'AWS::EC2::RouteTable': VPCRouter,
        'AWS::EC2::Route': VPCRouter,
        'AWS::EC2::SubnetRouteTableAssociation': VPCRouter,
        'AWS::EC2::SecurityGroup': VPCRouter,
        'AWS::EC2::NetworkInterface': VPCRouter,
        'AWS::EC2::VPCEndpoint': VPC,
        'AWS::ElasticLoadBalancingV2::LoadBalancer': ALB,
        'AWS::ElasticLoadBalancingV2::TargetGroup': ALB,
        'AWS::ElasticLoadBalancing::LoadBalancer': ELB,
        'AWS::Route53::HostedZone': Route53,
        'AWS::Route53::RecordSet': Route53,
        'AWS::CloudFront::Distribution': CF,
        'AWS::ApiGateway::RestApi': APIGateway,
        
        # Compute
        'AWS::EC2::Instance': EC2,
        'AWS::AutoScaling::AutoScalingGroup': EC2,
        'AWS::ECS::Cluster': ECS,
        'AWS::ECS::Service': ECS,
        'AWS::ECS::TaskDefinition': ECS,
        'AWS::EKS::Cluster': EKS,
        'AWS::Lambda::Function': Lambda,
        'AWS::Lambda::Permission': Lambda,
        'AWS::Lambda::LayerVersion': Lambda,
        'AWS::Batch::JobDefinition': Batch,
        'AWS::ElasticBeanstalk::Application': ElasticBeanstalk,
        
        # Database
        'AWS::RDS::DBInstance': RDS,
        'AWS::RDS::DBCluster': RDS,
        'AWS::RDS::DBSubnetGroup': RDS,
        'AWS::DynamoDB::Table': Dynamodb,
        'AWS::ElastiCache::CacheCluster': ElastiCache,
        'AWS::Redshift::Cluster': Redshift,
        'AWS::Neptune::DBCluster': Neptune,
        'AWS::DocumentDB::DBCluster': Database,
        
        # Storage
        'AWS::S3::Bucket': S3,
        'AWS::S3::BucketPolicy': S3,
        'AWS::EBS::Volume': EBS,
        'AWS::EFS::FileSystem': EFS,
        'AWS::EFS::MountTarget': EFS,
        'AWS::EFS::AccessPoint': EFS,
        'AWS::FSx::FileSystem': FSx,
        'AWS::Backup::BackupVault': Backup,
        'AWS::Backup::BackupPlan': Backup,
        'AWS::Backup::BackupSelection': Backup,
        'AWS::Glacier::Vault': Storage,
        
        # Integration
        'AWS::SQS::Queue': SQS,
        'AWS::SNS::Topic': SNS,
        'AWS::SNS::Subscription': SNS,
        'AWS::Events::Rule': Eventbridge,
        'AWS::StepFunctions::StateMachine': StepFunctions,
        'AWS::MQ::Broker': MQ,
        'AWS::Kinesis::Stream': Eventbridge,
        
        # Security
        'AWS::IAM::Role': IAM,
        'AWS::IAM::Policy': IAM,
        'AWS::IAM::InstanceProfile': IAM,
        'AWS::SecretsManager::Secret': SecretsManager,
        'AWS::KMS::Key': KMS,
        'AWS::WAFv2::WebACL': WAF,
        'AWS::CertificateManager::Certificate': CertificateManager,
        
        # Management
        'AWS::CloudWatch::Alarm': Cloudwatch,
        'AWS::Logs::LogGroup': Cloudwatch,
        'AWS::Logs::LogStream': Cloudwatch,
        'AWS::Logs::MetricFilter': Cloudwatch,
        'AWS::SSM::Parameter': SystemsManager,
        'AWS::CloudFormation::Stack': Cloudformation,
        'AWS::Config::ConfigRule': Config,
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
                return sub_value[:30]
            return "Sub:..."
        else:
            return str(value)[:30]
    else:
        return str(value)[:30]


def get_resource_label(resource_id, resource_data):
    """リソースのラベルを取得"""
    props = resource_data.get('Properties', {})
    
    # Tags から名前を取得
    tags = props.get('Tags', [])
    if tags:
        for tag in tags:
            if isinstance(tag, dict) and tag.get('Key') == 'Name':
                name = extract_string_value(tag.get('Value'))
                if name and not name.startswith('Ref:'):
                    return name[:20]
    
    # その他のプロパティから名前を取得
    for key in ['FunctionName', 'DBInstanceIdentifier', 'BucketName', 
                'TableName', 'ClusterName', 'QueueName', 'TopicName', 'Name',
                'BackupVaultName', 'BackupPlanName', 'LogGroupName']:
        if key in props:
            name = extract_string_value(props[key])
            if name and not name.startswith('Ref:'):
                return name[:20]
    
    # リソース ID を短縮
    return resource_id[:15]


def collect_all_resources(input_dir):
    """フォルダ内のすべての YAML からリソースを収集"""
    
    all_resources = {}
    file_count = 0
    
    print("Scanning YAML files...")
    
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml_file = os.path.join(root, file)
                template = parse_yaml(yaml_file)
                
                if template and 'Resources' in template:
                    file_count += 1
                    resources = template['Resources']
                    
                    # リソース ID の衝突を避けるため、ファイル名をプレフィックスとして追加
                    file_prefix = os.path.splitext(file)[0].replace('-', '_').replace(' ', '_')
                    
                    for resource_id, resource_data in resources.items():
                        unique_id = f"{file_prefix}_{resource_id}"
                        all_resources[unique_id] = {
                            'data': resource_data,
                            'original_id': resource_id,
                            'file': file
                        }
    
    print(f"  Found {file_count} YAML file(s)")
    print(f"  Collected {len(all_resources)} resource(s)")
    
    return all_resources


def find_all_references(all_resources):
    """すべてのリソースの参照関係を検索"""
    relationships = []
    
    for source_unique_id, source_info in all_resources.items():
        source_data = source_info['data']
        source_original_id = source_info['original_id']
        props = source_data.get('Properties', {})
        
        # !Ref を検索
        def find_refs(obj):
            refs = []
            if isinstance(obj, dict):
                if 'Ref' in obj:
                    refs.append(obj['Ref'])
                else:
                    for value in obj.values():
                        refs.extend(find_refs(value))
            elif isinstance(obj, list):
                for item in obj:
                    refs.extend(find_refs(item))
            return refs
        
        refs = find_refs(props)
        
        # 参照先を探す
        for ref_id in refs:
            for target_unique_id, target_info in all_resources.items():
                if target_info['original_id'] == ref_id:
                    relationships.append({
                        'from': source_unique_id,
                        'to': target_unique_id,
                        'type': 'ref'
                    })
    
    return relationships


def categorize_resources(all_resources):
    """リソースをカテゴリ別に分類"""
    categories = defaultdict(list)
    
    category_map = {
        'AWS::EC2::VPC': 'Network',
        'AWS::EC2::Subnet': 'Network',
        'AWS::EC2::InternetGateway': 'Network',
        'AWS::EC2::RouteTable': 'Network',
        'AWS::EC2::SecurityGroup': 'Security',
        'AWS::ElasticLoadBalancingV2::LoadBalancer': 'Network',
        
        'AWS::EC2::Instance': 'Compute',
        'AWS::ECS::Cluster': 'Compute',
        'AWS::Lambda::Function': 'Compute',
        
        'AWS::RDS::DBInstance': 'Database',
        'AWS::DynamoDB::Table': 'Database',
        
        'AWS::S3::Bucket': 'Storage',
        'AWS::EFS::FileSystem': 'Storage',
        'AWS::EFS::MountTarget': 'Storage',
        'AWS::EFS::AccessPoint': 'Storage',
        'AWS::Backup::BackupVault': 'Storage',
        'AWS::Backup::BackupPlan': 'Storage',
        'AWS::Backup::BackupSelection': 'Storage',
        
        'AWS::SQS::Queue': 'Integration',
        'AWS::SNS::Topic': 'Integration',
        
        'AWS::IAM::Role': 'Security',
        'AWS::IAM::Policy': 'Security',
        
        'AWS::CloudWatch::Alarm': 'Management',
        'AWS::Logs::LogGroup': 'Management',
        'AWS::Logs::MetricFilter': 'Management',
    }
    
    for unique_id, resource_info in all_resources.items():
        resource_type = resource_info['data'].get('Type', '')
        category = category_map.get(resource_type, 'Other')
        categories[category].append((unique_id, resource_info, resource_type))
    
    return dict(categories)


def generate_architecture_diagram(input_dir, output_dir='diagrams', output_name='architecture'):
    """フォルダ内のすべての YAML から大きなアーキテクチャ図を生成"""
    
    print("="*80)
    print("Generating Complete Architecture Diagram")
    print("="*80)
    print()
    
    # 出力ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)
    
    # すべてのリソースを収集
    all_resources = collect_all_resources(input_dir)
    
    if not all_resources:
        print("No resources found!")
        return None
    
    # 参照関係を検索
    print("\nAnalyzing references...")
    relationships = find_all_references(all_resources)
    print(f"  Found {len(relationships)} relationship(s)")
    
    # カテゴリ別に分類
    print("\nCategorizing resources...")
    categories = categorize_resources(all_resources)
    
    for category, resources in categories.items():
        print(f"  {category}: {len(resources)} resource(s)")
    
    # 図を生成（出力パスを修正）
    output_path = os.path.join(output_dir, output_name)
    print(f"\nGenerating diagram: {output_path}.png")
    
    graph_attr = {
        "fontsize": "12",
        "bgcolor": "white",
        "pad": "1.0",
        "nodesep": "0.8",
        "ranksep": "1.2",
    }
    
    unsupported_types = set()
    
    try:
        with Diagram(
            f"Complete Architecture ({len(all_resources)} resources)",
            filename=output_path,
            show=False,
            direction="TB",
            outformat="png",
            graph_attr=graph_attr
        ):
            
            nodes = {}
            
            # カテゴリごとにクラスタを作成
            for category, resource_list in categories.items():
                
                with Cluster(f"{category} ({len(resource_list)})"):
                    
                    for unique_id, resource_info, resource_type in resource_list:
                        resource_data = resource_info['data']
                        icon_class = get_icon_class(resource_type)
                        
                        if icon_class:
                            label = get_resource_label(resource_info['original_id'], resource_data)
                            node = icon_class(label)
                            nodes[unique_id] = node
                        else:
                            label = get_resource_label(resource_info['original_id'], resource_data)
                            node = Blank(label)
                            nodes[unique_id] = node
                            unsupported_types.add(resource_type)
            
            # 関係を描画
            for rel in relationships:
                source_id = rel['from']
                target_id = rel['to']
                
                if source_id in nodes and target_id in nodes:
                    nodes[source_id] >> Edge(color="blue", style="solid") >> nodes[target_id]
        
        # 未対応タイプを表示
        if unsupported_types:
            print(f"\nWarning: {len(unsupported_types)} unsupported resource type(s):")
            for rt in sorted(unsupported_types):
                print(f"  - {rt}")
        
        print(f"\n-> Generated: {output_path}.png")
        print("="*80)
        
        return f"{output_path}.png"
        
    except Exception as e:
        print(f"\nError generating diagram: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate architecture diagram from folder of CloudFormation templates')
    parser.add_argument('--input-dir', default='aws-resources', help='Input directory containing YAML files')
    parser.add_argument('--output-dir', default='diagrams', help='Output directory for diagram')
    parser.add_argument('--output-name', default='complete-architecture', help='Output filename (without extension)')
    
    args = parser.parse_args()
    
    generate_architecture_diagram(args.input_dir, args.output_dir, args.output_name)


if __name__ == '__main__':
    main()
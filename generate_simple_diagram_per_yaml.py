# -*- coding: utf-8 -*-
"""
各 YAML ファイルから簡易アーキテクチャ図を生成
単一リソースの場合は対応する AWS アイコンのみを表示
"""

import os
import yaml
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import VPC, InternetGateway, PrivateSubnet, PublicSubnet, NATGateway, ELB, ALB, NLB, Route53
from diagrams.aws.compute import EC2, ECS, EKS, Lambda, Batch
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift
from diagrams.aws.storage import S3, EBS, EFS
from diagrams.aws.integration import SQS, SNS, Eventbridge, StepFunctions
from diagrams.aws.security import IAM, SecretsManager, KMS, WAF
from diagrams.aws.management import Cloudwatch, SystemsManager, Cloudformation


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
        print(f"    エラー: {yaml_file} - {e}")
        return None


# ==================== アイコンマッピング ====================

def get_icon_class(resource_type):
    """リソースタイプに対応するアイコンクラスを取得"""
    
    icon_map = {
        # ネットワーク
        'AWS::EC2::VPC': VPC,
        'AWS::EC2::Subnet': PrivateSubnet,
        'AWS::EC2::InternetGateway': InternetGateway,
        'AWS::EC2::NatGateway': NATGateway,
        'AWS::ElasticLoadBalancingV2::LoadBalancer': ALB,
        'AWS::ElasticLoadBalancing::LoadBalancer': ELB,
        'AWS::Route53::HostedZone': Route53,
        
        # コンピューティング
        'AWS::EC2::Instance': EC2,
        'AWS::ECS::Cluster': ECS,
        'AWS::EKS::Cluster': EKS,
        'AWS::Lambda::Function': Lambda,
        'AWS::Batch::JobDefinition': Batch,
        
        # データベース
        'AWS::RDS::DBInstance': RDS,
        'AWS::DynamoDB::Table': Dynamodb,
        'AWS::ElastiCache::CacheCluster': ElastiCache,
        'AWS::Redshift::Cluster': Redshift,
        
        # ストレージ
        'AWS::S3::Bucket': S3,
        'AWS::EBS::Volume': EBS,
        'AWS::EFS::FileSystem': EFS,
        
        # 統合
        'AWS::SQS::Queue': SQS,
        'AWS::SNS::Topic': SNS,
        'AWS::Events::Rule': Eventbridge,
        'AWS::StepFunctions::StateMachine': StepFunctions,
        
        # セキュリティ
        'AWS::IAM::Role': IAM,
        'AWS::SecretsManager::Secret': SecretsManager,
        'AWS::KMS::Key': KMS,
        'AWS::WAFv2::WebACL': WAF,
        
        # 管理
        'AWS::CloudWatch::Alarm': Cloudwatch,
        'AWS::SSM::Parameter': SystemsManager,
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
                if name and name != 'Name':
                    return name
    
    # その他のプロパティから名前を取得
    for key in ['FunctionName', 'DBInstanceIdentifier', 'BucketName', 
                'TableName', 'ClusterName', 'QueueName', 'TopicName', 'Name']:
        if key in props:
            name = extract_string_value(props[key])
            if name:
                return name
    
    return resource_id


def generate_diagram_from_yaml(yaml_file, output_dir='diagrams'):
    """単一の YAML ファイルから図を生成"""
    
    template = parse_yaml(yaml_file)
    if not template or 'Resources' not in template:
        print(f"  スキップ: {yaml_file} - リソースが見つかりません")
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    resources = template['Resources']
    
    # 出力ファイル名
    base_name = os.path.splitext(os.path.basename(yaml_file))[0]
    output_filename = os.path.join(output_dir, base_name)
    
    # 単一リソースの場合
    if len(resources) == 1:
        resource_id = list(resources.keys())[0]
        resource_data = resources[resource_id]
        resource_type = resource_data.get('Type', 'Unknown')
        
        icon_class = get_icon_class(resource_type)
        
        if icon_class:
            label = get_resource_label(resource_id, resource_data)
            
            # 簡易図を生成
            with Diagram(
                label,
                filename=output_filename,
                show=False,
                direction="LR",
                outformat="png",
                graph_attr={"bgcolor": "white"}
            ):
                icon_class(label)
            
            print(f"  -> 図を生成: {output_filename}.png")
            return f"{output_filename}.png"
        else:
            print(f"  -> スキップ: {resource_type} に対応するアイコンがありません")
            return None
    
    # 複数リソースの場合
    else:
        with Diagram(
            f"{base_name} ({len(resources)} resources)",
            filename=output_filename,
            show=False,
            direction="TB",
            outformat="png",
            graph_attr={"bgcolor": "white", "pad": "0.5"}
        ):
            
            nodes = {}
            
            for resource_id, resource_data in resources.items():
                resource_type = resource_data.get('Type', 'Unknown')
                icon_class = get_icon_class(resource_type)
                
                if icon_class:
                    label = get_resource_label(resource_id, resource_data)
                    node = icon_class(label)
                    nodes[resource_id] = node
            
            # 参照関係を検索
            refs = []
            
            def find_refs(obj, source_id):
                if isinstance(obj, dict):
                    if 'Ref' in obj:
                        refs.append((source_id, obj['Ref']))
                    else:
                        for value in obj.values():
                            find_refs(value, source_id)
                elif isinstance(obj, list):
                    for item in obj:
                        find_refs(item, source_id)
            
            for resource_id, resource_data in resources.items():
                props = resource_data.get('Properties', {})
                find_refs(props, resource_id)
            
            # 参照関係を描画
            for source_id, target_id in refs:
                if source_id in nodes and target_id in nodes:
                    nodes[source_id] >> Edge(color="blue", style="dashed") >> nodes[target_id]
        
        print(f"  -> 図を生成: {output_filename}.png")
        return f"{output_filename}.png"


def generate_all_diagrams(input_dir='aws-resources', output_dir='aws-diagrams'):
    """すべての YAML ファイルから図を生成"""
    
    print("="*80)
    print("CloudFormation 簡易アーキテクチャ図生成ツール")
    print("="*80)
    print(f"\n入力ディレクトリ: {input_dir}")
    print(f"出力ディレクトリ: {output_dir}\n")
    
    yaml_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml_files.append(os.path.join(root, file))
    
    print(f"{len(yaml_files)} 個の YAML ファイルが見つかりました\n")
    
    success_count = 0
    error_count = 0
    
    for yaml_file in yaml_files:
        print(f"処理中: {os.path.basename(yaml_file)}")
        
        try:
            result = generate_diagram_from_yaml(yaml_file, output_dir)
            if result:
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            print(f"  -> エラー: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
    
    print("\n" + "="*80)
    print(f"完了！")
    print(f"  成功: {success_count} 図")
    print(f"  スキップ/エラー: {error_count} ファイル")
    print(f"出力ディレクトリ: {os.path.abspath(output_dir)}")
    print("="*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='各 YAML ファイルから簡易アーキテクチャ図を生成')
    parser.add_argument('--input-dir', default='aws-resources', help='YAML ファイルが含まれる入力ディレクトリ')
    parser.add_argument('--output-dir', default='aws-diagrams', help='図の出力ディレクトリ')
    
    args = parser.parse_args()
    
    generate_all_diagrams(args.input_dir, args.output_dir)


if __name__ == '__main__':
    main()
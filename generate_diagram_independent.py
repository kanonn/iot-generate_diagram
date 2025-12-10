# -*- coding: utf-8 -*-
"""
独立版架构图生成器 - VPC 相关资源都独立显示，不合并
每个 IGW、VPC、Subnet 都单独显示
"""

import os
import yaml
from collections import defaultdict
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import VPC, InternetGateway, PrivateSubnet, PublicSubnet
from diagrams.aws.compute import ECS, Lambda
from diagrams.aws.storage import S3
from diagrams.aws.integration import SQS, SNS
from diagrams.aws.network import Route53
from diagrams.aws.management import Cloudwatch
from diagrams.aws.security import IAM


def parse_yaml(yaml_file):
    """解析 YAML 文件"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except:
        return None


def extract_vpc_id(resource_name):
    """从资源名称提取 VPC ID"""
    if resource_name.startswith('VPC'):
        vpc_id = resource_name[3:]
        if 'vpc' in vpc_id and '-' not in vpc_id:
            vpc_id = vpc_id.replace('vpc', 'vpc-', 1)
        return vpc_id
    return None


def extract_subnet_id(resource_name):
    """从资源名称提取 Subnet ID"""
    if resource_name.startswith('Subnet'):
        subnet_id = resource_name[6:]
        if 'subnet' in subnet_id and '-' not in subnet_id:
            subnet_id = subnet_id.replace('subnet', 'subnet-', 1)
        return subnet_id
    return None


def extract_igw_id(resource_name):
    """从资源名称提取 IGW ID"""
    if resource_name.startswith('InternetGateway'):
        igw_id = resource_name[15:]
        if 'igw' in igw_id and '-' not in igw_id:
            igw_id = igw_id.replace('igw', 'igw-', 1)
        return igw_id
    return None


def scan_resources(input_dir):
    """扫描所有资源"""
    yaml_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml_files.append(os.path.join(root, file))
    
    print(f"Scanning {len(yaml_files)} YAML files...")
    
    # 按类型分类资源
    resources = {
        'vpc': [],
        'subnet': [],
        'igw': [],
        'sg': [],
        'ecs': [],
        'lambda': [],
        's3': [],
        'sqs': [],
        'sns': [],
        'route53': [],
        'cloudwatch': [],
        'iam': []
    }
    
    # 映射关系
    vpc_map = {}  # vpc_id -> vpc_resource
    subnet_map = {}  # subnet_id -> subnet_resource
    subnet_to_vpc = {}  # subnet_id -> vpc_id
    igw_map = {}  # igw_id -> igw_resource
    igw_to_vpc = {}  # igw_id -> vpc_id (通过 VPC Attachment 判断)
    
    for yaml_file in yaml_files:
        template = parse_yaml(yaml_file)
        if template and 'Resources' in template:
            for resource_id, resource_data in template['Resources'].items():
                resource_type = resource_data.get('Type', '')
                props = resource_data.get('Properties', {})
                
                resource_info = {
                    'id': resource_id,
                    'type': resource_type,
                    'props': props
                }
                
                if resource_type == 'AWS::EC2::VPC':
                    resources['vpc'].append(resource_info)
                    vpc_id = extract_vpc_id(resource_id)
                    if vpc_id:
                        vpc_map[vpc_id] = resource_info
                
                elif resource_type == 'AWS::EC2::Subnet':
                    resources['subnet'].append(resource_info)
                    subnet_id = extract_subnet_id(resource_id)
                    if subnet_id:
                        subnet_map[subnet_id] = resource_info
                        vpc_id = props.get('VpcId')
                        if vpc_id:
                            subnet_to_vpc[subnet_id] = vpc_id
                
                elif resource_type == 'AWS::EC2::InternetGateway':
                    resources['igw'].append(resource_info)
                    igw_id = extract_igw_id(resource_id)
                    if igw_id:
                        igw_map[igw_id] = resource_info
                
                elif resource_type == 'AWS::EC2::VPCGatewayAttachment':
                    # IGW 到 VPC 的连接关系
                    vpc_id = props.get('VpcId')
                    igw_id = props.get('InternetGatewayId')
                    if vpc_id and igw_id:
                        igw_to_vpc[igw_id] = vpc_id
                
                elif resource_type == 'AWS::EC2::SecurityGroup':
                    resources['sg'].append(resource_info)
                
                elif resource_type == 'AWS::ECS::Cluster':
                    resources['ecs'].append(resource_info)
                
                elif resource_type == 'AWS::Lambda::Function':
                    resources['lambda'].append(resource_info)
                
                elif resource_type == 'AWS::S3::Bucket':
                    resources['s3'].append(resource_info)
                
                elif resource_type == 'AWS::SQS::Queue':
                    resources['sqs'].append(resource_info)
                
                elif resource_type == 'AWS::SNS::Topic':
                    resources['sns'].append(resource_info)
                
                elif resource_type == 'AWS::Route53::HostedZone':
                    resources['route53'].append(resource_info)
                
                elif resource_type == 'AWS::CloudWatch::Alarm':
                    resources['cloudwatch'].append(resource_info)
                
                elif resource_type == 'AWS::IAM::Role':
                    resources['iam'].append(resource_info)
    
    print(f"Found {sum(len(v) for v in resources.values())} resources")
    
    return resources, vpc_map, subnet_map, subnet_to_vpc, igw_map, igw_to_vpc


def get_name(resource):
    """获取资源名称"""
    props = resource['props']
    
    # 尝试从 Tags 获取
    for tag in props.get('Tags', []):
        if tag.get('Key') == 'Name':
            name = tag.get('Value')
            if len(name) > 30:
                return name[:27] + "..."
            return name
    
    # 从其他属性获取
    name = (
        props.get('FunctionName') or
        props.get('BucketName') or
        props.get('ClusterName') or
        props.get('QueueName') or
        props.get('TopicName') or
        props.get('Name') or
        resource['id']
    )
    
    if len(name) > 30:
        name = name[:27] + "..."
    
    return name


def is_public_subnet(subnet):
    """判断是否为公有子网"""
    props = subnet['props']
    
    if props.get('MapPublicIpOnLaunch', False):
        return True
    
    name = get_name(subnet).lower()
    if 'public' in name:
        return True
    
    return False


def organize_by_vpc_and_subnet(resources, vpc_map, subnet_map, subnet_to_vpc, igw_map, igw_to_vpc):
    """按 VPC 和 Subnet 组织资源"""
    
    vpc_structure = {}
    
    # 为每个 VPC 创建结构
    for vpc_id, vpc_info in vpc_map.items():
        vpc_structure[vpc_id] = {
            'vpc': vpc_info,
            'igw': None,  # 关联的 IGW
            'subnets': {}
        }
    
    # 关联 IGW 到 VPC
    for igw_id, vpc_id in igw_to_vpc.items():
        if vpc_id in vpc_structure and igw_id in igw_map:
            vpc_structure[vpc_id]['igw'] = igw_map[igw_id]
    
    # 如果 IGW 没有通过 Attachment 关联，尝试推断
    # 简化处理：如果只有一个 VPC 和一个 IGW，关联它们
    if len(vpc_map) == 1 and len(igw_map) == 1 and not any(v['igw'] for v in vpc_structure.values()):
        vpc_id = list(vpc_map.keys())[0]
        igw_id = list(igw_map.keys())[0]
        vpc_structure[vpc_id]['igw'] = igw_map[igw_id]
    
    # 添加子网到 VPC
    for subnet_id, vpc_id in subnet_to_vpc.items():
        if vpc_id in vpc_structure and subnet_id in subnet_map:
            subnet_info = subnet_map[subnet_id]
            vpc_structure[vpc_id]['subnets'][subnet_id] = {
                'subnet': subnet_info,
                'ecs': [],
                'lambda': []
            }
    
    # 将 ECS 分配到子网
    # 简化：放到第一个 VPC 的第一个私有子网
    if resources['ecs'] and vpc_structure:
        first_vpc_id = list(vpc_structure.keys())[0]
        vpc = vpc_structure[first_vpc_id]
        
        private_subnet = None
        for subnet_id, subnet_data in vpc['subnets'].items():
            if not is_public_subnet(subnet_data['subnet']):
                private_subnet = subnet_id
                break
        
        if not private_subnet and vpc['subnets']:
            private_subnet = list(vpc['subnets'].keys())[0]
        
        if private_subnet:
            vpc['subnets'][private_subnet]['ecs'] = resources['ecs']
    
    # 将 Lambda 分配到子网
    for lambda_res in resources['lambda']:
        vpc_config = lambda_res['props'].get('VpcConfig', {})
        subnet_ids = vpc_config.get('SubnetIds', [])
        
        if subnet_ids:
            for subnet_id in subnet_ids:
                if subnet_id in subnet_to_vpc:
                    vpc_id = subnet_to_vpc[subnet_id]
                    if vpc_id in vpc_structure and subnet_id in vpc_structure[vpc_id]['subnets']:
                        vpc_structure[vpc_id]['subnets'][subnet_id]['lambda'].append(lambda_res)
                        break
    
    return vpc_structure


def generate_diagram(resources, vpc_structure, output_filename='aws_independent'):
    """生成架构图 - 每个 VPC 资源独立显示"""
    
    print("\nResource Summary:")
    print(f"  VPC: {len(resources['vpc'])}")
    print(f"  Subnet: {len(resources['subnet'])}")
    print(f"  IGW: {len(resources['igw'])}")
    print(f"  ECS: {len(resources['ecs'])}")
    print(f"  Lambda: {len(resources['lambda'])}")
    print(f"  S3: {len(resources['s3'])}")
    print(f"  SQS: {len(resources['sqs'])}")
    print(f"  SNS: {len(resources['sns'])}")
    
    graph_attr = {
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "2.0",
        "nodesep": "1.5",
        "ranksep": "2.0",
        "compound": "true"
    }
    
    with Diagram(
        "AWS Infrastructure - Independent Resources",
        filename=output_filename,
        show=False,
        direction="TB",
        graph_attr=graph_attr,
        outformat="png"
    ):
        
        nodes = {}
        
        # Route53
        if resources['route53']:
            for route53_res in resources['route53']:
                route53_name = get_name(route53_res)
                route53 = Route53(route53_name)
                nodes[f"route53_{route53_res['id']}"] = route53
        
        # 遍历每个 VPC - 每个都独立显示
        for vpc_id, vpc_data in vpc_structure.items():
            vpc_info = vpc_data['vpc']
            vpc_cidr = vpc_info['props'].get('CidrBlock', '10.0.0.0/16')
            vpc_name = get_name(vpc_info)
            
            # 这个 VPC 对应的 IGW（独立显示）
            vpc_igw = None
            if vpc_data['igw']:
                igw_info = vpc_data['igw']
                igw_name = get_name(igw_info)
                vpc_igw = InternetGateway(f"IGW\n{igw_name}")
                nodes[f"igw_{vpc_id}"] = vpc_igw
                
                # Route53 连接到这个 IGW
                for key in nodes:
                    if key.startswith('route53'):
                        nodes[key] >> Edge(color="gray") >> vpc_igw
            
            with Cluster(f"VPC: {vpc_name}\n{vpc_cidr}", 
                        graph_attr={"bgcolor": "#E8F4F8", "style": "rounded", "fontsize": "16"}):
                
                vpc_node = VPC(vpc_name)
                nodes[f"vpc_{vpc_id}"] = vpc_node
                
                # IGW 连接到 VPC
                if vpc_igw:
                    vpc_igw >> Edge(label="attached", color="blue", style="bold") >> vpc_node
                
                # 遍历这个 VPC 的每个子网 - 每个都独立显示
                for subnet_id, subnet_data in vpc_data['subnets'].items():
                    subnet_info = subnet_data['subnet']
                    subnet_cidr = subnet_info['props'].get('CidrBlock', '10.0.x.0/24')
                    subnet_az = subnet_info['props'].get('AvailabilityZone', 'unknown-az')
                    subnet_name = get_name(subnet_info)
                    is_public = is_public_subnet(subnet_info)
                    
                    subnet_color = "#D4EDDA" if is_public else "#FFF3CD"
                    subnet_type = "Public" if is_public else "Private"
                    
                    cluster_label = f"{subnet_type} Subnet\n{subnet_name}\n{subnet_cidr}\n{subnet_az}"
                    
                    with Cluster(cluster_label, 
                               graph_attr={"bgcolor": subnet_color, "style": "rounded", "fontsize": "12"}):
                        
                        if is_public:
                            subnet_node = PublicSubnet(subnet_type)
                        else:
                            subnet_node = PrivateSubnet(subnet_type)
                        
                        vpc_node >> subnet_node
                        
                        # 这个子网内的 ECS（独立显示）
                        if subnet_data['ecs']:
                            for ecs_res in subnet_data['ecs']:
                                ecs_name = get_name(ecs_res)
                                ecs = ECS(ecs_name)
                                subnet_node >> ecs
                                nodes[f"ecs_{ecs_res['id']}"] = ecs
                        
                        # 这个子网内的 Lambda（独立显示）
                        if subnet_data['lambda']:
                            for lambda_res in subnet_data['lambda']:
                                lambda_name = get_name(lambda_res)
                                lambda_node = Lambda(lambda_name)
                                subnet_node >> lambda_node
                                nodes[f"lambda_{lambda_res['id']}"] = lambda_node
        
        # VPC 外部服务
        
        # Lambda（不在 VPC 内的）
        standalone_lambda = []
        for lambda_res in resources['lambda']:
            vpc_config = lambda_res['props'].get('VpcConfig', {})
            if not vpc_config.get('SubnetIds'):
                standalone_lambda.append(lambda_res)
        
        if standalone_lambda:
            with Cluster("Lambda (No VPC)", graph_attr={"bgcolor": "#FFE6CC", "style": "dashed"}):
                for lambda_res in standalone_lambda:
                    lambda_name = get_name(lambda_res)
                    lambda_node = Lambda(lambda_name)
                    nodes[f"lambda_{lambda_res['id']}"] = lambda_node
        
        # S3（合并显示）
        if resources['s3']:
            with Cluster("Object Storage", graph_attr={"bgcolor": "#FFF9E6", "style": "dashed"}):
                s3 = S3(f"S3 Buckets\n({len(resources['s3'])} buckets)")
                nodes['s3'] = s3
                
                # Lambda 连接到 S3
                for key in nodes:
                    if key.startswith('lambda_') or key.startswith('ecs_'):
                        nodes[key] >> Edge(label="read/write", color="purple", style="dotted") >> s3
        
        # 消息服务（合并显示）
        if resources['sqs'] or resources['sns']:
            with Cluster("Messaging", graph_attr={"bgcolor": "#FFE6F0", "style": "dashed"}):
                
                if resources['sqs']:
                    sqs = SQS(f"SQS Queues\n({len(resources['sqs'])} queues)")
                    nodes['sqs'] = sqs
                    
                    for key in nodes:
                        if key.startswith('lambda_'):
                            nodes[key] >> Edge(label="queue", color="orange", style="dotted") >> sqs
                
                if resources['sns']:
                    sns = SNS(f"SNS Topics\n({len(resources['sns'])} topics)")
                    nodes['sns'] = sns
                    
                    for key in nodes:
                        if key.startswith('lambda_'):
                            nodes[key] >> Edge(label="notify", color="brown", style="dotted") >> sns
        
        # 管理服务（合并显示）
        if resources['cloudwatch'] or resources['iam']:
            with Cluster("Management & Security", graph_attr={"bgcolor": "#E9ECEF", "style": "dashed"}):
                
                if resources['cloudwatch']:
                    cw = Cloudwatch(f"CloudWatch\n({len(resources['cloudwatch'])} alarms)")
                
                if resources['iam']:
                    iam = IAM(f"IAM Roles\n({len(resources['iam'])} roles)")
    
    print(f"\nDiagram generated: {output_filename}.png")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate AWS Architecture Diagram - Independent VPC Resources')
    parser.add_argument('--input-dir', default='aws-resources', help='Input directory')
    parser.add_argument('--output', default='aws_independent', help='Output filename')
    
    args = parser.parse_args()
    
    print("Starting diagram generation...")
    
    if not os.path.exists(args.input_dir):
        print(f"Error: Directory not found: {args.input_dir}")
        return
    
    # 扫描资源
    resources, vpc_map, subnet_map, subnet_to_vpc, igw_map, igw_to_vpc = scan_resources(args.input_dir)
    
    if not resources:
        print("Error: No resources found")
        return
    
    # 按 VPC 和 Subnet 组织
    print("\nOrganizing resources by VPC and Subnet...")
    vpc_structure = organize_by_vpc_and_subnet(resources, vpc_map, subnet_map, subnet_to_vpc, igw_map, igw_to_vpc)
    
    print(f"\nVPC Structure:")
    for vpc_id, vpc_data in vpc_structure.items():
        vpc_name = get_name(vpc_data['vpc'])
        print(f"  VPC: {vpc_name} ({vpc_id})")
        if vpc_data['igw']:
            igw_name = get_name(vpc_data['igw'])
            print(f"    IGW: {igw_name}")
        print(f"    Subnets: {len(vpc_data['subnets'])}")
        for subnet_id, subnet_data in vpc_data['subnets'].items():
            subnet_name = get_name(subnet_data['subnet'])
            subnet_type = "Public" if is_public_subnet(subnet_data['subnet']) else "Private"
            print(f"      - [{subnet_type}] {subnet_name}")
            if subnet_data['ecs']:
                print(f"        ECS: {len(subnet_data['ecs'])}")
            if subnet_data['lambda']:
                print(f"        Lambda: {len(subnet_data['lambda'])}")
    
    # 生成图表
    print("\nGenerating diagram...")
    generate_diagram(resources, vpc_structure, args.output)
    
    print(f"\nComplete! File: {os.path.abspath(args.output + '.png')}")


if __name__ == '__main__':
    main()
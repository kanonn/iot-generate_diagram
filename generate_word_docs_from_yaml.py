# -*- coding: utf-8 -*-
"""
从 CloudFormation YAML 文件生成 Word 技术文档
每个 YAML 文件生成一个独立的 Word 文档
"""

import os
import yaml
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


def parse_yaml(yaml_file):
    """解析 YAML 文件"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except:
        return None


def set_cell_background(cell, color):
    """设置表格单元格背景色"""
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(
        nsdecls('w'), color))
    cell._element.get_or_add_tcPr().append(shading_elm)


def parse_xml(xml_string):
    """解析 XML 字符串"""
    from docx.oxml import parse_xml as docx_parse_xml
    return docx_parse_xml(xml_string)


def nsdecls(*prefixes):
    """命名空间声明"""
    from docx.oxml.ns import nsdecls as docx_nsdecls
    return docx_nsdecls(*prefixes)


def add_heading_with_style(doc, text, level=1):
    """添加带样式的标题"""
    heading = doc.add_heading(text, level=level)
    heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    # 设置字体
    for run in heading.runs:
        run.font.name = 'Microsoft YaHei'
        run.font.color.rgb = RGBColor(0, 51, 102)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    
    return heading


def add_code_block(doc, code_text):
    """添加代码块"""
    paragraph = doc.add_paragraph()
    paragraph.style = 'Normal'
    
    # 设置背景色（灰色）
    run = paragraph.add_run(code_text)
    run.font.name = 'Consolas'
    run.font.size = Pt(9)
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Consolas')
    
    # 设置段落格式
    paragraph.paragraph_format.left_indent = Inches(0.3)
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(6)
    
    return paragraph


def get_resource_name(resource_info):
    """获取资源名称"""
    props = resource_info.get('Properties', {})
    
    # 从 Tags 获取
    for tag in props.get('Tags', []):
        if tag.get('Key') == 'Name':
            return tag.get('Value')
    
    # 从其他属性获取
    name = (
        props.get('FunctionName') or
        props.get('DBInstanceIdentifier') or
        props.get('BucketName') or
        props.get('TableName') or
        props.get('ClusterName') or
        props.get('QueueName') or
        props.get('TopicName') or
        props.get('Name')
    )
    
    return name


def get_resource_description(resource_type):
    """获取资源类型的描述"""
    descriptions = {
        'AWS::EC2::VPC': 'Amazon Virtual Private Cloud - 虚拟私有云，提供隔离的网络环境',
        'AWS::EC2::Subnet': '子网 - VPC 内的网络分段，可以是公有或私有',
        'AWS::EC2::InternetGateway': '互联网网关 - 允许 VPC 与互联网通信',
        'AWS::EC2::NatGateway': 'NAT 网关 - 允许私有子网中的资源访问互联网',
        'AWS::EC2::SecurityGroup': '安全组 - 虚拟防火墙，控制入站和出站流量',
        'AWS::EC2::Instance': 'EC2 实例 - 虚拟服务器',
        'AWS::ECS::Cluster': 'ECS 集群 - 容器编排服务集群',
        'AWS::EKS::Cluster': 'EKS 集群 - Kubernetes 托管服务',
        'AWS::Lambda::Function': 'Lambda 函数 - 无服务器计算服务',
        'AWS::RDS::DBInstance': 'RDS 数据库实例 - 托管的关系数据库',
        'AWS::DynamoDB::Table': 'DynamoDB 表 - NoSQL 数据库',
        'AWS::S3::Bucket': 'S3 存储桶 - 对象存储服务',
        'AWS::SQS::Queue': 'SQS 队列 - 消息队列服务',
        'AWS::SNS::Topic': 'SNS 主题 - 消息通知服务',
        'AWS::ElasticLoadBalancingV2::LoadBalancer': '负载均衡器 - 分发流量到多个目标',
        'AWS::IAM::Role': 'IAM 角色 - 身份和访问管理角色',
        'AWS::Route53::HostedZone': 'Route53 托管区域 - DNS 服务',
        'AWS::CloudWatch::Alarm': 'CloudWatch 告警 - 监控和告警服务',
    }
    
    return descriptions.get(resource_type, 'AWS 资源')


def format_property_value(value, indent=0):
    """格式化属性值"""
    indent_str = "  " * indent
    
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        for k, v in value.items():
            formatted = format_property_value(v, indent + 1)
            lines.append(f"{indent_str}  {k}: {formatted}")
        lines.append(f"{indent_str}}}")
        return "\n".join(lines)
    
    elif isinstance(value, list):
        if not value:
            return "[]"
        if len(value) == 1:
            return f"[{format_property_value(value[0])}]"
        lines = ["["]
        for item in value:
            formatted = format_property_value(item, indent + 1)
            lines.append(f"{indent_str}  - {formatted}")
        lines.append(f"{indent_str}]")
        return "\n".join(lines)
    
    elif isinstance(value, str):
        if len(value) > 50:
            return f'"{value[:47]}..."'
        return f'"{value}"'
    
    else:
        return str(value)


def generate_word_document(yaml_file, output_dir='docs'):
    """为单个 YAML 文件生成 Word 文档"""
    
    # 解析 YAML
    template = parse_yaml(yaml_file)
    if not template or 'Resources' not in template:
        print(f"  Skipping {yaml_file} - No resources found")
        return None
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取资源信息
    resource_id = list(template['Resources'].keys())[0]
    resource_data = template['Resources'][resource_id]
    resource_type = resource_data.get('Type', 'Unknown')
    resource_props = resource_data.get('Properties', {})
    
    # 获取资源名称
    resource_name = get_resource_name(resource_data) or resource_id
    
    # 创建 Word 文档
    doc = Document()
    
    # 设置文档属性
    core_properties = doc.core_properties
    core_properties.author = 'AWS Documentation Generator'
    core_properties.title = f'{resource_name} - Technical Documentation'
    core_properties.created = datetime.now()
    
    # ==================== 封面 ====================
    
    # 标题
    title = doc.add_heading(f'{resource_name}', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.size = Pt(28)
        run.font.color.rgb = RGBColor(0, 51, 102)
        run.font.name = 'Microsoft YaHei'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    
    # 副标题
    subtitle = doc.add_paragraph('Technical Documentation')
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in subtitle.runs:
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(100, 100, 100)
        run.font.name = 'Arial'
    
    doc.add_paragraph()  # 空行
    
    # 资源类型
    type_para = doc.add_paragraph(f'Resource Type: {resource_type}')
    type_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in type_para.runs:
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0, 102, 204)
    
    doc.add_paragraph()  # 空行
    
    # 生成日期
    date_para = doc.add_paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in date_para.runs:
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(150, 150, 150)
    
    # 分页
    doc.add_page_break()
    
    # ==================== 目录 ====================
    
    add_heading_with_style(doc, 'Table of Contents', level=1)
    
    toc_items = [
        '1. Overview',
        '2. Resource Details',
        '3. Properties',
        '4. Configuration',
        '5. Dependencies',
        '6. Tags',
        '7. YAML Source Code'
    ]
    
    for item in toc_items:
        p = doc.add_paragraph(item, style='List Bullet')
        p.paragraph_format.left_indent = Inches(0.5)
    
    doc.add_page_break()
    
    # ==================== 1. Overview ====================
    
    add_heading_with_style(doc, '1. Overview', level=1)
    
    # 资源概述表格
    table = doc.add_table(rows=4, cols=2)
    table.style = 'Light Grid Accent 1'
    
    # 表头
    table.rows[0].cells[0].text = 'Property'
    table.rows[0].cells[1].text = 'Value'
    
    # 设置表头样式
    for cell in table.rows[0].cells:
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), '4472C4'))
        cell._element.get_or_add_tcPr().append(shading_elm)
    
    # 数据行
    table.rows[1].cells[0].text = 'Resource Name'
    table.rows[1].cells[1].text = resource_name
    
    table.rows[2].cells[0].text = 'Resource ID'
    table.rows[2].cells[1].text = resource_id
    
    table.rows[3].cells[0].text = 'Resource Type'
    table.rows[3].cells[1].text = resource_type
    
    doc.add_paragraph()  # 空行
    
    # 资源描述
    add_heading_with_style(doc, 'Description', level=2)
    description = get_resource_description(resource_type)
    doc.add_paragraph(description)
    
    doc.add_paragraph()  # 空行
    
    # ==================== 2. Resource Details ====================
    
    add_heading_with_style(doc, '2. Resource Details', level=1)
    
    # 详细信息
    service = resource_type.split('::')[1] if '::' in resource_type else 'Unknown'
    resource_subtype = resource_type.split('::')[2] if '::' in resource_type and len(resource_type.split('::')) > 2 else 'Unknown'
    
    details_table = doc.add_table(rows=4, cols=2)
    details_table.style = 'Light Grid Accent 1'
    
    details_table.rows[0].cells[0].text = 'Property'
    details_table.rows[0].cells[1].text = 'Value'
    
    for cell in details_table.rows[0].cells:
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), '4472C4'))
        cell._element.get_or_add_tcPr().append(shading_elm)
    
    details_table.rows[1].cells[0].text = 'AWS Service'
    details_table.rows[1].cells[1].text = service
    
    details_table.rows[2].cells[0].text = 'Resource Subtype'
    details_table.rows[2].cells[1].text = resource_subtype
    
    details_table.rows[3].cells[0].text = 'Region'
    details_table.rows[3].cells[1].text = 'ap-northeast-1 (Tokyo)'
    
    doc.add_paragraph()  # 空行
    
    # ==================== 3. Properties ====================
    
    add_heading_with_style(doc, '3. Properties', level=1)
    
    if resource_props:
        doc.add_paragraph('This resource has the following properties configured:')
        doc.add_paragraph()  # 空行
        
        # 属性表格
        prop_table = doc.add_table(rows=len(resource_props) + 1, cols=3)
        prop_table.style = 'Light Grid Accent 1'
        
        # 表头
        prop_table.rows[0].cells[0].text = 'Property Name'
        prop_table.rows[0].cells[1].text = 'Type'
        prop_table.rows[0].cells[2].text = 'Value'
        
        for cell in prop_table.rows[0].cells:
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
            shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), '4472C4'))
            cell._element.get_or_add_tcPr().append(shading_elm)
        
        # 数据行
        for idx, (prop_name, prop_value) in enumerate(resource_props.items(), start=1):
            prop_table.rows[idx].cells[0].text = prop_name
            
            # 类型
            value_type = type(prop_value).__name__
            if value_type == 'dict':
                value_type = 'Object'
            elif value_type == 'list':
                value_type = 'Array'
            elif value_type == 'str':
                value_type = 'String'
            elif value_type == 'int':
                value_type = 'Integer'
            elif value_type == 'bool':
                value_type = 'Boolean'
            
            prop_table.rows[idx].cells[1].text = value_type
            
            # 值
            formatted_value = format_property_value(prop_value)
            prop_table.rows[idx].cells[2].text = formatted_value
    else:
        doc.add_paragraph('No properties configured for this resource.')
    
    doc.add_paragraph()  # 空行
    
    # ==================== 4. Configuration ====================
    
    add_heading_with_style(doc, '4. Configuration', level=1)
    
    # 配置细节
    config_sections = {
        'VpcId': 'VPC Configuration',
        'SubnetId': 'Subnet Configuration',
        'SubnetIds': 'Subnet Configuration',
        'SecurityGroupIds': 'Security Group Configuration',
        'InstanceType': 'Instance Configuration',
        'DBInstanceClass': 'Database Configuration',
        'Runtime': 'Runtime Configuration',
        'CidrBlock': 'Network Configuration',
    }
    
    has_config = False
    for key, section_name in config_sections.items():
        if key in resource_props:
            has_config = True
            add_heading_with_style(doc, section_name, level=2)
            
            config_value = resource_props[key]
            
            if isinstance(config_value, str):
                doc.add_paragraph(f'{key}: {config_value}')
            elif isinstance(config_value, list):
                doc.add_paragraph(f'{key}:')
                for item in config_value:
                    doc.add_paragraph(f'  • {item}', style='List Bullet')
            else:
                doc.add_paragraph(f'{key}: {config_value}')
            
            doc.add_paragraph()  # 空行
    
    if not has_config:
        doc.add_paragraph('No specific configuration sections identified.')
    
    # ==================== 5. Dependencies ====================
    
    add_heading_with_style(doc, '5. Dependencies', level=1)
    
    # 查找依赖关系
    dependencies = []
    
    if 'VpcId' in resource_props:
        dependencies.append(f"VPC: {resource_props['VpcId']}")
    
    if 'SubnetId' in resource_props:
        dependencies.append(f"Subnet: {resource_props['SubnetId']}")
    
    if 'SubnetIds' in resource_props:
        for subnet in resource_props['SubnetIds']:
            dependencies.append(f"Subnet: {subnet}")
    
    if 'SecurityGroupIds' in resource_props:
        for sg in resource_props['SecurityGroupIds']:
            dependencies.append(f"Security Group: {sg}")
    
    if dependencies:
        doc.add_paragraph('This resource depends on the following resources:')
        for dep in dependencies:
            doc.add_paragraph(f'  • {dep}', style='List Bullet')
    else:
        doc.add_paragraph('This resource has no explicit dependencies.')
    
    doc.add_paragraph()  # 空行
    
    # ==================== 6. Tags ====================
    
    add_heading_with_style(doc, '6. Tags', level=1)
    
    tags = resource_props.get('Tags', [])
    
    if tags:
        # 标签表格
        tag_table = doc.add_table(rows=len(tags) + 1, cols=2)
        tag_table.style = 'Light Grid Accent 1'
        
        # 表头
        tag_table.rows[0].cells[0].text = 'Key'
        tag_table.rows[0].cells[1].text = 'Value'
        
        for cell in tag_table.rows[0].cells:
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
            shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), '4472C4'))
            cell._element.get_or_add_tcPr().append(shading_elm)
        
        # 数据行
        for idx, tag in enumerate(tags, start=1):
            tag_table.rows[idx].cells[0].text = tag.get('Key', '')
            tag_table.rows[idx].cells[1].text = tag.get('Value', '')
    else:
        doc.add_paragraph('No tags configured for this resource.')
    
    doc.add_paragraph()  # 空行
    
    # ==================== 7. YAML Source Code ====================
    
    add_heading_with_style(doc, '7. YAML Source Code', level=1)
    
    doc.add_paragraph('Complete YAML definition for this resource:')
    doc.add_paragraph()  # 空行
    
    # 读取原始 YAML
    with open(yaml_file, 'r', encoding='utf-8') as f:
        yaml_content = f.read()
    
    # 添加代码块
    add_code_block(doc, yaml_content)
    
    # ==================== 保存文档 ====================
    
    # 生成文件名
    safe_name = resource_name.replace('/', '-').replace('\\', '-').replace(':', '-')
    output_file = os.path.join(output_dir, f'{safe_name}.docx')
    
    doc.save(output_file)
    
    return output_file


def generate_all_docs(input_dir='aws-resources', output_dir='aws-docs'):
    """为所有 YAML 文件生成文档"""
    
    print("="*80)
    print("AWS CloudFormation Documentation Generator")
    print("="*80)
    print(f"\nInput directory: {input_dir}")
    print(f"Output directory: {output_dir}\n")
    
    # 扫描所有 YAML 文件
    yaml_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml_files.append(os.path.join(root, file))
    
    print(f"Found {len(yaml_files)} YAML files\n")
    
    # 生成文档
    success_count = 0
    for yaml_file in yaml_files:
        print(f"Processing: {os.path.basename(yaml_file)}")
        
        try:
            output_file = generate_word_document(yaml_file, output_dir)
            if output_file:
                print(f"  -> Generated: {output_file}")
                success_count += 1
        except Exception as e:
            print(f"  -> Error: {e}")
    
    print("\n" + "="*80)
    print(f"Complete! Generated {success_count} documents")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    print("="*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Word documentation from CloudFormation YAML files')
    parser.add_argument('--input-dir', default='aws-resources', help='Input directory containing YAML files')
    parser.add_argument('--output-dir', default='aws-docs', help='Output directory for Word documents')
    
    args = parser.parse_args()
    
    generate_all_docs(args.input_dir, args.output_dir)


if __name__ == '__main__':
    main()
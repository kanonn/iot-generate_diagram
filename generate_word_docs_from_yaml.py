# -*- coding: utf-8 -*-
"""
CloudFormation YAML から Confluence 用 Word ドキュメントを生成
1つの YAML ファイル内のすべてのリソースを1つのドキュメントに含める
"""

import os
import yaml
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


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
        print(f"    エラー: {yaml_file} の解析に失敗 - {e}")
        return None


# ==================== ヘルパー関数 ====================

def extract_string_value(value):
    """組み込み関数を含む可能性のある値から文字列を抽出"""
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        if 'Ref' in value:
            return f"!Ref {value['Ref']}"
        elif 'Fn::Sub' in value:
            sub_value = value['Fn::Sub']
            if isinstance(sub_value, str):
                return f"!Sub {sub_value}"
            else:
                return f"!Sub [{sub_value[0] if sub_value else '...'}]"
        elif 'Fn::GetAtt' in value:
            attrs = value['Fn::GetAtt']
            if isinstance(attrs, list):
                return f"!GetAtt {attrs[0]}.{attrs[1]}"
            else:
                return f"!GetAtt {attrs}"
        else:
            return str(value)
    else:
        return str(value)


def format_value_compact(value, max_length=100):
    """値をコンパクトにフォーマット（テーブル表示用）"""
    if isinstance(value, dict):
        # 組み込み関数の場合
        if 'Ref' in value:
            return f"!Ref {value['Ref']}"
        elif 'Fn::GetAtt' in value:
            attrs = value['Fn::GetAtt']
            if isinstance(attrs, list):
                return f"!GetAtt {attrs[0]}.{attrs[1]}"
            else:
                return f"!GetAtt {attrs}"
        elif 'Fn::Sub' in value:
            sub_value = value['Fn::Sub']
            if isinstance(sub_value, str):
                if len(sub_value) > max_length:
                    return f"!Sub {sub_value[:max_length-10]}..."
                return f"!Sub {sub_value}"
            else:
                return f"!Sub [...]"
        elif 'Fn::Join' in value:
            return f"!Join [...]"
        elif 'Fn::Select' in value:
            return f"!Select [...]"
        elif 'Fn::GetAZs' in value:
            return f"!GetAZs {value['Fn::GetAZs']}"
        elif 'Fn::Base64' in value:
            return "!Base64 [...]"
        elif 'Fn::If' in value:
            return "!If [...]"
        else:
            # 通常のオブジェクト
            if not value:
                return "{}"
            items = []
            for k, v in list(value.items())[:3]:
                items.append(f"{k}: {format_value_compact(v, 30)}")
            result = "{" + ", ".join(items)
            if len(value) > 3:
                result += ", ..."
            result += "}"
            return result
    
    elif isinstance(value, list):
        if not value:
            return "[]"
        if len(value) == 1:
            return f"[{format_value_compact(value[0], 30)}]"
        
        # シンプルな値のリスト
        if all(isinstance(v, (str, int, bool)) for v in value):
            if len(value) <= 3:
                return f"[{', '.join(str(v) for v in value)}]"
            else:
                return f"[{', '.join(str(v) for v in value[:3])}, ... ({len(value)} items)]"
        
        # 複雑な値のリスト
        return f"[{len(value)} items]"
    
    elif isinstance(value, str):
        if len(value) > max_length:
            return f'"{value[:max_length-3]}..."'
        return f'"{value}"'
    
    elif isinstance(value, bool):
        return str(value)
    
    elif isinstance(value, (int, float)):
        return str(value)
    
    else:
        return str(value)


def parse_xml(xml_string):
    from docx.oxml import parse_xml as docx_parse_xml
    return docx_parse_xml(xml_string)


def nsdecls(*prefixes):
    from docx.oxml.ns import nsdecls as docx_nsdecls
    return docx_nsdecls(*prefixes)


def add_heading_with_style(doc, text, level=1):
    """スタイル付き見出しを追加"""
    heading = doc.add_heading(text, level=level)
    heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    for run in heading.runs:
        run.font.name = 'Meiryo'
        run.font.color.rgb = RGBColor(0, 51, 102)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Meiryo')
    
    return heading


def get_resource_name(resource_info, resource_id):
    """リソース名を取得"""
    props = resource_info.get('Properties', {})
    
    # Tags から取得を試みる
    tags = props.get('Tags', [])
    if tags:
        for tag in tags:
            if isinstance(tag, dict) and tag.get('Key') == 'Name':
                name_value = tag.get('Value')
                name = extract_string_value(name_value)
                if name and name != 'Name':
                    return name
    
    # その他のプロパティから取得を試みる
    for key in ['FunctionName', 'DBInstanceIdentifier', 'BucketName', 
                'TableName', 'ClusterName', 'QueueName', 'TopicName', 'Name']:
        if key in props:
            value = props[key]
            name = extract_string_value(value)
            if name:
                return name
    
    # 見つからない場合は resource_id を返す
    return resource_id


def flatten_dict(d, parent_key='', sep='.', max_depth=5, current_depth=0):
    """ネストされた辞書を平坦化（すべての key-value を抽出）"""
    items = []
    
    if current_depth >= max_depth:
        items.append((parent_key, str(d)))
        return items
    
    if isinstance(d, dict):
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                # 組み込み関数かチェック
                if any(key.startswith('Fn::') or key == 'Ref' for key in v.keys()):
                    # 組み込み関数の場合は値として扱う
                    items.append((new_key, format_value_compact(v)))
                else:
                    # 通常のオブジェクトは再帰的に処理
                    items.extend(flatten_dict(v, new_key, sep, max_depth, current_depth + 1))
            elif isinstance(v, list):
                # リストの処理
                if len(v) == 0:
                    items.append((new_key, '[]'))
                elif all(isinstance(item, (str, int, bool, type(None))) for item in v):
                    # シンプルな値のリスト
                    items.append((new_key, format_value_compact(v)))
                else:
                    # 複雑なリスト
                    for idx, item in enumerate(v):
                        if isinstance(item, dict):
                            items.extend(flatten_dict(item, f"{new_key}[{idx}]", sep, max_depth, current_depth + 1))
                        else:
                            items.append((f"{new_key}[{idx}]", format_value_compact(item)))
            else:
                # プリミティブ値
                items.append((new_key, format_value_compact(v)))
    else:
        items.append((parent_key, format_value_compact(d)))
    
    return items


def generate_word_document(yaml_file, output_dir='docs'):
    """単一の YAML ファイルから Word ドキュメントを生成（すべてのリソースを含む）"""
    
    template = parse_yaml(yaml_file)
    if not template or 'Resources' not in template:
        print(f"  スキップ: {yaml_file} - リソースが見つかりません")
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    # すべてのリソースを取得
    all_resources = template['Resources']
    template_description = template.get('Description', '')
    
    # ドキュメント作成
    doc = Document()
    
    # ファイル名から取得
    yaml_basename = os.path.splitext(os.path.basename(yaml_file))[0]
    
    # コアプロパティを設定
    core_properties = doc.core_properties
    core_properties.author = 'CloudFormation Documentation Generator'
    core_properties.title = yaml_basename
    core_properties.created = datetime.now()
    
    # ==================== タイトル ====================
    
    title = doc.add_heading(yaml_basename, level=1)
    for run in title.runs:
        run.font.name = 'Meiryo'
        run.font.color.rgb = RGBColor(0, 51, 102)
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Meiryo')
    
    # ==================== 説明 ====================
    
    if template_description:
        add_heading_with_style(doc, '説明', level=2)
        doc.add_paragraph(template_description)
        doc.add_paragraph()
    
    # ==================== リソース概要 ====================
    
    add_heading_with_style(doc, 'リソース概要', level=2)
    doc.add_paragraph(f'このテンプレートには {len(all_resources)} 個のリソースが含まれています。')
    doc.add_paragraph()
    
    # リソース一覧テーブル
    overview_table = doc.add_table(rows=len(all_resources) + 1, cols=3)
    overview_table.style = 'Light Grid Accent 1'
    
    # ヘッダー
    overview_table.rows[0].cells[0].text = 'リソース ID'
    overview_table.rows[0].cells[1].text = 'リソース名'
    overview_table.rows[0].cells[2].text = 'タイプ'
    
    for cell in overview_table.rows[0].cells:
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), '4472C4'))
        cell._element.get_or_add_tcPr().append(shading_elm)
    
    # データ行
    for idx, (resource_id, resource_data) in enumerate(all_resources.items(), start=1):
        resource_type = resource_data.get('Type', 'Unknown')
        resource_name = get_resource_name(resource_data, resource_id)
        
        overview_table.rows[idx].cells[0].text = resource_id
        overview_table.rows[idx].cells[1].text = resource_name
        overview_table.rows[idx].cells[2].text = resource_type
    
    doc.add_paragraph()
    doc.add_page_break()
    
    # ==================== 各リソースの詳細 ====================
    
    for resource_idx, (resource_id, resource_data) in enumerate(all_resources.items(), start=1):
        
        resource_type = resource_data.get('Type', 'Unknown')
        resource_props = resource_data.get('Properties', {})
        resource_name = get_resource_name(resource_data, resource_id)
        
        # リソースタイトル
        add_heading_with_style(doc, f'{resource_idx}. {resource_name}', level=2)
        
        # 基本情報テーブル
        info_table = doc.add_table(rows=3, cols=2)
        info_table.style = 'Light Grid Accent 1'
        
        # ヘッダー
        info_table.rows[0].cells[0].text = 'プロパティ'
        info_table.rows[0].cells[1].text = '値'
        
        for cell in info_table.rows[0].cells:
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
            shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), '4472C4'))
            cell._element.get_or_add_tcPr().append(shading_elm)
        
        # データ行
        info_table.rows[1].cells[0].text = 'リソース ID'
        info_table.rows[1].cells[1].text = resource_id
        
        info_table.rows[2].cells[0].text = 'リソースタイプ'
        info_table.rows[2].cells[1].text = resource_type
        
        doc.add_paragraph()
        
        # ==================== プロパティ詳細 ====================
        
        if resource_props:
            add_heading_with_style(doc, 'プロパティ詳細', level=3)
            
            # プロパティを平坦化
            flattened = flatten_dict(resource_props)
            
            if flattened:
                # テーブル作成
                prop_table = doc.add_table(rows=len(flattened) + 1, cols=2)
                prop_table.style = 'Light Grid Accent 1'
                
                # ヘッダー
                prop_table.rows[0].cells[0].text = 'プロパティパス'
                prop_table.rows[0].cells[1].text = '値'
                
                for cell in prop_table.rows[0].cells:
                    cell.paragraphs[0].runs[0].font.bold = True
                    cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
                    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), '4472C4'))
                    cell._element.get_or_add_tcPr().append(shading_elm)
                
                # データ行
                for idx, (key, value) in enumerate(flattened, start=1):
                    prop_table.rows[idx].cells[0].text = key
                    prop_table.rows[idx].cells[1].text = str(value)
            else:
                doc.add_paragraph('プロパティが設定されていません。')
        else:
            doc.add_paragraph('このリソースにはプロパティが設定されていません。')
        
        doc.add_paragraph()
        
        # ==================== 参照と依存関係 ====================
        
        refs = []
        getattrs = []
        
        def find_references(obj, path=""):
            """再帰的に Ref と GetAtt を検索"""
            if isinstance(obj, dict):
                if 'Ref' in obj:
                    refs.append((path, obj['Ref']))
                elif 'Fn::GetAtt' in obj:
                    getattrs.append((path, obj['Fn::GetAtt']))
                else:
                    for key, value in obj.items():
                        find_references(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    find_references(item, f"{path}[{idx}]")
        
        find_references(resource_props)
        
        if refs or getattrs:
            add_heading_with_style(doc, '参照と依存関係', level=3)
            
            if refs:
                doc.add_paragraph('リソース参照 (!Ref):', style='List Bullet')
                for path, ref in refs:
                    doc.add_paragraph(f'{path} → {ref}', style='List Bullet 2')
            
            if getattrs:
                doc.add_paragraph('属性参照 (!GetAtt):', style='List Bullet')
                for path, getatt in getattrs:
                    if isinstance(getatt, list):
                        doc.add_paragraph(f'{path} → {getatt[0]}.{getatt[1]}', style='List Bullet 2')
                    else:
                        doc.add_paragraph(f'{path} → {getatt}', style='List Bullet 2')
        
        # ==================== タグ ====================
        
        tags = resource_props.get('Tags', [])
        
        if tags:
            doc.add_paragraph()
            add_heading_with_style(doc, 'タグ', level=3)
            
            tag_table = doc.add_table(rows=len(tags) + 1, cols=2)
            tag_table.style = 'Light Grid Accent 1'
            
            tag_table.rows[0].cells[0].text = 'キー'
            tag_table.rows[0].cells[1].text = '値'
            
            for cell in tag_table.rows[0].cells:
                cell.paragraphs[0].runs[0].font.bold = True
                cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
                shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), '4472C4'))
                cell._element.get_or_add_tcPr().append(shading_elm)
            
            for idx, tag in enumerate(tags, start=1):
                if isinstance(tag, dict):
                    key = extract_string_value(tag.get('Key', ''))
                    value = extract_string_value(tag.get('Value', ''))
                    tag_table.rows[idx].cells[0].text = key
                    tag_table.rows[idx].cells[1].text = value
        
        # 最後のリソースでなければ改ページ
        if resource_idx < len(all_resources):
            doc.add_page_break()
    
    # ==================== 保存 ====================
    
    # ファイル名を安全にする
    safe_name = yaml_basename.replace('/', '-').replace('\\', '-').replace(':', '-').replace('*', '-').replace('?', '-').replace('"', '-').replace('<', '-').replace('>', '-').replace('|', '-')
    if len(safe_name) > 50:
        safe_name = safe_name[:47] + "..."
    
    output_file = os.path.join(output_dir, f'{safe_name}.docx')
    
    doc.save(output_file)
    
    return output_file


def generate_all_docs(input_dir='aws-resources', output_dir='aws-docs'):
    """すべての YAML ファイルからドキュメントを生成"""
    
    print("="*80)
    print("CloudFormation ドキュメント生成ツール (Confluence 用 - すべてのリソース)")
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
            output_file = generate_word_document(yaml_file, output_dir)
            if output_file:
                print(f"  -> 生成完了: {os.path.basename(output_file)}")
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
    print(f"  成功: {success_count} ドキュメント")
    print(f"  エラー: {error_count} ファイル")
    print(f"出力ディレクトリ: {os.path.abspath(output_dir)}")
    print("="*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CloudFormation YAML から Word ドキュメントを生成（すべてのリソース）')
    parser.add_argument('--input-dir', default='aws-resources', help='YAML ファイルが含まれる入力ディレクトリ')
    parser.add_argument('--output-dir', default='aws-docs', help='Word ドキュメントの出力ディレクトリ')
    
    args = parser.parse_args()
    
    generate_all_docs(args.input_dir, args.output_dir)


if __name__ == '__main__':
    main()
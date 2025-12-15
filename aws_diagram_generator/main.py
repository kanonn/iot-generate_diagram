# -*- coding: utf-8 -*-
"""
AWS アーキテクチャ図生成器 V3

機能:
1. AWS API からリソースを読み取り（ページネーション対応で300件制限なし）
2. CloudFormation 形式でエクスポート
3. CloudFormation ファイルからインポート（--from-cf オプション）
4. リソース間の関係を検出して架構図を生成

使用方法:
    # AWS から直接読み取って図を生成
    python main.py
    
    # AWS から読み取り、CloudFormation をエクスポート
    python main.py --export-cf
    
    # 既存の CloudFormation から図を生成（AWS 接続不要）
    python main.py --from-cf ./aws-outputs/cloudformation
    
    # リージョン指定
    python main.py --region ap-northeast-1
    
    # 出力先指定
    python main.py --output-dir my-outputs --output-name my-diagram
"""

import os
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description='AWS アーキテクチャ図生成器 V3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    # AWS から直接読み取って図を生成
    python main.py
    
    # CloudFormation もエクスポート
    python main.py --export-cf
    
    # 既存の CloudFormation から図を生成（AWS 接続不要）
    python main.py --from-cf ./aws-outputs/cloudformation
    
    # 図の生成をスキップ（CloudFormation エクスポートのみ）
    python main.py --export-cf --no-diagram
"""
    )
    
    parser.add_argument(
        '--region',
        default='ap-northeast-1',
        help='AWS リージョン (default: ap-northeast-1)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='aws-outputs',
        help='出力ディレクトリ (default: aws-outputs)'
    )
    
    parser.add_argument(
        '--output-name',
        default='aws-architecture',
        help='出力ファイル名 (default: aws-architecture)'
    )
    
    parser.add_argument(
        '--from-cf',
        metavar='DIR',
        help='CloudFormation ファイルから読み込む（AWS 接続不要）'
    )
    
    parser.add_argument(
        '--export-cf',
        action='store_true',
        help='CloudFormation 形式でエクスポート'
    )
    
    parser.add_argument(
        '--no-diagram',
        action='store_true',
        help='アーキテクチャ図生成をスキップ'
    )
    
    parser.add_argument(
        '--drawio',
        action='store_true',
        help='Draw.io 形式で出力（AWS 公式アイコンスタイル）'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("AWS Architecture Diagram Generator V3")
    print("=" * 80)
    print(f"Output Directory: {args.output_dir}")
    
    if args.from_cf:
        print(f"Mode: Import from CloudFormation")
        print(f"CloudFormation Directory: {args.from_cf}")
    else:
        print(f"Mode: Read from AWS API")
        print(f"Region: {args.region}")
    
    print("=" * 80 + "\n")
    
    # リソースを読み込む
    if args.from_cf:
        # CloudFormation からインポート
        from cf_exporter import CloudFormationImporter
        
        reader = CloudFormationImporter()
        total = reader.import_from_directory(args.from_cf)
        
        if total == 0:
            print("\n⚠ No resources found. Check the directory path.")
            return 1
    else:
        # AWS API から読み込み
        from aws_reader import AWSResourceReader
        
        try:
            reader = AWSResourceReader(region=args.region)
            total = reader.read_all_resources()
        except Exception as e:
            print(f"\nERROR: Failed to read AWS resources: {e}")
            return 1
        
        if total == 0:
            print("\n⚠ No resources found. Check your credentials and region.")
            return 1
        
        # CloudFormation エクスポート
        if args.export_cf:
            from cf_exporter import export_cloudformation
            
            cf_dir = os.path.join(args.output_dir, 'cloudformation')
            export_cloudformation(reader, cf_dir)
    
    # アーキテクチャ図生成
    if not args.no_diagram:
        diagram_dir = os.path.join(args.output_dir, 'diagrams')
        
        if args.drawio:
            # Draw.io 形式で出力
            from drawio_generator import DrawioGenerator
            
            generator = DrawioGenerator(reader)
            generator.generate(diagram_dir, args.output_name)
        else:
            # PNG 形式で出力（diagrams ライブラリ使用）
            from diagram_generator import ArchitectureDiagramGenerator
            
            generator = ArchitectureDiagramGenerator(reader)
            generator.generate(diagram_dir, args.output_name)
    
    print("\n" + "=" * 80)
    print("Complete!")
    print(f"Output directory: {os.path.abspath(args.output_dir)}")
    print("=" * 80 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

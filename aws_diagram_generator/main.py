# -*- coding: utf-8 -*-
"""
AWS アーキテクチャ図生成器 V3

機能:
1. AWS API からリソースを読み取り（ページネーション対応で300件制限なし）
2. CloudFormation 形式でエクスポート
3. CloudFormation ファイルからインポート（--from-cf オプション）
4. リソース間の関係を検出して架構図を生成
5. IAM Role (AssumeRole) 対応

使用方法:
    # AWS から直接読み取って図を生成
    python main.py
    
    # IAM Role を使用して読み取り
    python main.py --role-arn arn:aws:iam::123456789012:role/ReadOnlyRole
    
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
    
    # IAM Role を使用して読み取り（推奨）
    python main.py --role-arn arn:aws:iam::123456789012:role/DiagramReadOnlyRole
    
    # クロスアカウントアクセス（External ID 付き）
    python main.py --role-arn arn:aws:iam::123456789012:role/CrossAccountRole --external-id MyExternalId123
    
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
        '--role-arn',
        metavar='ARN',
        help='AssumeRole する IAM ロールの ARN（推奨：読み取り専用ロール）'
    )
    
    parser.add_argument(
        '--external-id',
        metavar='ID',
        help='AssumeRole 時の External ID（クロスアカウントアクセス時に使用）'
    )
    
    parser.add_argument(
        '--session-name',
        default='AWSArchitectureDiagramGenerator',
        metavar='NAME',
        help='AssumeRole 時のセッション名 (default: AWSArchitectureDiagramGenerator)'
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
        nargs='?',
        const='',
        default=None,
        metavar='DIR',
        help='CloudFormation 形式でエクスポート（ディレクトリ指定可、省略時は output-dir/cloudformation）'
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
    
    parser.add_argument(
        '--svg',
        action='store_true',
        help='SVG 形式で出力'
    )
    
    parser.add_argument(
        '--icons-dir',
        metavar='DIR',
        help='AWS アイコンディレクトリ（AWS 公式アイコンを使用する場合）'
    )
    
    parser.add_argument(
        '--svg-sg',
        action='store_true',
        help='Security Group 関係の SVG 図を出力'
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
        if args.role_arn:
            print(f"IAM Role: {args.role_arn}")
    
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
            reader = AWSResourceReader(
                region=args.region,
                role_arn=args.role_arn,
                external_id=args.external_id,
                session_name=args.session_name
            )
            total = reader.read_all_resources()
        except Exception as e:
            print(f"\nERROR: Failed to read AWS resources: {e}")
            return 1
        
        if total == 0:
            print("\n⚠ No resources found. Check your credentials and region.")
            return 1
        
        # CloudFormation エクスポート
        if args.export_cf is not None:
            from cf_exporter import export_cloudformation
            
            # エクスポート先を決定
            if args.export_cf:
                cf_dir = args.export_cf
            else:
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
        
        elif args.svg:
            # SVG 形式で出力
            from svg_generator import SVGGenerator
            
            generator = SVGGenerator(reader, icons_dir=args.icons_dir)
            generator.generate(diagram_dir, args.output_name)
        
        elif args.svg_sg:
            # Security Group SVG 形式で出力
            from svg_generator import SecurityGroupSVGGenerator
            
            generator = SecurityGroupSVGGenerator(reader)
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

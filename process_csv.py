import argparse
from pathlib import Path
import sys

# 确保能正确导入NERService
try:
    script_dir = Path(__file__).parent
    services_dir = script_dir / "services"
    sys.path.append(str(services_dir))
    from ner_service import NERService
except ImportError:
    raise ImportError("无法导入NERService，请确保services/ner_service.py存在")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='医疗数据敏感信息标记工具',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--input_csv', required=True,
                       help='输入CSV文件路径')
    parser.add_argument('--output_csv', required=True,
                       help='输出CSV文件路径')
    parser.add_argument('--columns', nargs='+', default=None,
                       help='指定需要处理的列名（默认自动检测）')
    return parser.parse_args()

def main():
    args = parse_arguments()
    ner = NERService()
    
    print(f"开始处理: {args.input_csv}")
    success = ner.process_csv(
        input_path=args.input_csv,
        output_path=args.output_csv,
        columns=args.columns
    )
    
    if success:
        print(f"处理完成，结果已保存到: {args.output_csv}")
    else:
        print("处理过程中出现错误")

if __name__ == "__main__":
    main()
import argparse
import pandas as pd
import re  # 导入正则表达式模块

# 加载并匹配 header_and_roi_summary.csv 和 train_with_sensitive_info.csv
def load_and_match_data(header_file, sensitive_file, output_file):
    # 读取 header 和 sensitive 文件
    header_df = pd.read_csv(header_file, encoding='gbk', encoding_errors='ignore')
    sensitive_df = pd.read_csv(sensitive_file, encoding='gbk', encoding_errors='ignore')

    # 创建一个字典以便更容易通过 patient_id 查找 Path
    path_dict = {}
    
    for _, row in sensitive_df.iterrows():
        # 从 Path 提取 patient_id，假设 Path 格式为 'CheXpert-v1.0-small/train/patient00001/study1/view1_frontal.jpg'
        path = row['Path']
        
        # 使用正则表达式提取 patient_id，假设 patient_id 格式为 'patient00001'
        match = re.search(r'patient(\d+)', path)
        if match:
            patient_id = 'patient' + match.group(1)  # 提取到的 patient_id
            path_dict[patient_id] = path
            print(f"Extracted patient_id: {patient_id} from Path: {path}")  # 打印确认提取的 patient_id

    # 创建一个新列，将 'patient_id' 和对应的 'Path' 进行匹配
    header_df['Matched_Path'] = header_df['patient_id'].map(path_dict)

    # 打印匹配的前几行以检查结果
    print("Header DataFrame with matched Path:")
    print(header_df[['patient_id', 'Matched_Path']].head())

    # 保存匹配结果到文件
    header_df.to_csv(output_file, index=False)
    print(f"Matching results saved to {output_file}")

    return header_df

def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="Match patient_id with corresponding Path and save results")
    parser.add_argument('--header-file', type=str, required=True, help="Path to header_and_roi_summary.csv")
    parser.add_argument('--sensitive-file', type=str, required=True, help="Path to train_with_sensitive_info.csv")
    parser.add_argument('--output-file', type=str, required=True, help="Path to save the output CSV with matched data")
    args = parser.parse_args()

    # 加载并匹配数据，并保存结果
    matched_data = load_and_match_data(args.header_file, args.sensitive_file, args.output_file)

    # 显示部分匹配结果
    print("Matched Data:")
    print(matched_data[['patient_id', 'Matched_Path']].head())

if __name__ == '__main__':
    main()

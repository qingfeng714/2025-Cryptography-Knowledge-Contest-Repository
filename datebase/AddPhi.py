import pandas as pd
from faker import Faker
import random

# 读取CSV文件
file_path = r"C:\Users\QF\.cache\kagglehub\datasets\ashery\chexpert\versions\1\train_with_names.csv"
df = pd.read_csv(file_path)

# 初始化 Faker（可指定中文数据）
fake = Faker('zh_CN')  # 生成中文数据，如需要英文数据，用 `Faker()` 即可

# 生成随机电话号（11位手机号）
def generate_phone():
    return fake.phone_number()  # 示例：'13812345678'

# 生成随机身份证号（18位）
def generate_id_number():
    return fake.ssn()  # 示例：'110105199003072316'

# 生成随机家庭住址（省市区+街道）
def generate_address():
    return fake.address()  # 示例：'北京市朝阳区建国路88号'

# 在 'Age' 列后插入新列
df.insert(df.columns.get_loc('Age') + 1, 'Phone', df['Sex'].apply(lambda x: generate_phone()))
df.insert(df.columns.get_loc('Age') + 2, 'ID_Number', df['Sex'].apply(lambda x: generate_id_number()))
df.insert(df.columns.get_loc('Age') + 3, 'Address', df['Sex'].apply(lambda x: generate_address()))

# 保存修改后的CSV文件
output_path = r"C:\Users\QF\.cache\kagglehub\datasets\ashery\chexpert\versions\1\train_with_sensitive_info.csv"
df.to_csv(output_path, index=False)

print(f"文件已保存到: {output_path}")
from datasets import load_dataset

# 直接加载数据集（自动处理格式）
dataset = load_dataset(
    "itsanmolgupta/mimic-cxr-dataset",
    split="train",
    cache_dir=r"C:\Users\QF\.cache\huggingface\datasets"
)

# 查看结构
print("列名:", dataset.column_names)
print("\n第一条数据:", dataset[0])
print("\n数据类型:", dataset.features)
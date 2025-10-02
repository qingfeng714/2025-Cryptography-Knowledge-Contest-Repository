# scripts/phi_detector.py
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import re
import json

# 模型选择：多语言 BERT，支持中英文混合
MODEL_NAME = "bert-base-multilingual-cased"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)

nlp_pipeline = pipeline(
    "ner",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple"
)

# 正则匹配结构化字段（中英文）
def detectStructuredPHI(text: str):
    entities = []

    # 年龄
    age_match = re.search(r"(Age|年龄)[:：]?\s*(\d{1,3})", text, re.IGNORECASE)
    if age_match:
        entities.append({"entity": "AGE", "text": age_match.group(2)})

    # 性别
    sex_match = re.search(r"(Sex|性别)[:：]?\s*(男|女|Male|Female|M|F)", text, re.IGNORECASE)
    if sex_match:
        entities.append({"entity": "SEX", "text": sex_match.group(2)})

    # 电话
    phone_match = re.search(r"\b1\d{10}\b", text)
    if phone_match:
        entities.append({"entity": "PHONE", "text": phone_match.group(0)})

    # 身份证/病历号
    id_match = re.search(r"(ID|MRN|病历号)[:：]?\s*([A-Za-z0-9\-]+)", text)
    if id_match:
        entities.append({"entity": "ID", "text": id_match.group(2)})

    # 日期
    date_match = re.findall(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", text)
    for d in date_match:
        entities.append({"entity": "DATE", "text": d})

    return entities

# 综合识别函数
def detectPHI(text: str):
    entities = []

    # 模型识别人名、地点、组织等
    try:
        results = nlp_pipeline(text)
        for r in results:
            entities.append({
                "entity": r["entity_group"],
                "text": r["word"],
                "score": round(float(r["score"]), 3),
                "start": int(r["start"]),
                "end": int(r["end"])
            })
    except Exception as e:
        print("NER 模型识别异常:", e)

    # 正则识别结构化字段
    entities += detectStructuredPHI(text)

    return entities

# 批量识别多行病历
def batchDetectPHI(text_lines):
    all_results = []
    for idx, line in enumerate(text_lines, start=1):
        line = line.strip()
        if not line:
            continue
        entities = detectPHI(line)
        all_results.append({
            "line_id": idx,
            "text": line,
            "entities": entities
        })
    return all_results

# 测试入口
if __name__ == "__main__":
    print("请输入病历文本，每行一条，输入 'END' 结束输入：")
    lines = []
    while True:
        text = input()
        if text.strip().upper() == "END":
            break
        lines.append(text)

    results = batchDetectPHI(lines)
    print("\n识别结果 (JSON 格式):")
    print(json.dumps(results, ensure_ascii=False, indent=2))

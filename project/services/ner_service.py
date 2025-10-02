from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import re

# 模型选择：中英文通用 BERT NER
MODEL_NAME = "bert-base-multilingual-cased"  # 支持中英文混合
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)

nlp_pipeline = pipeline(
    "ner",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple"
)

# 结构化字段正则匹配
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

# 标签映射函数（可根据需要扩展）
def map_label(label):
    if label.lower() in ["person", "per", "name"]:
        return "PER"
    elif label.lower() in ["organization", "org"]:
        return "ORG"
    elif label.lower() in ["location", "loc"]:
        return "LOC"
    else:
        return "MISC"

# 综合识别函数
def detectPHI(text: str, score_threshold=0.5):
    entities = []

    # 模型识别
    try:
        results = nlp_pipeline(text)
        for r in results:
            if r["score"] >= score_threshold:
                entities.append({
                    "entity": map_label(r["entity_group"]),
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

# 批量多行处理函数
def detectPHI_batch(lines):
    results = []
    for i, line in enumerate(lines, start=1):
        entities = detectPHI(line)
        results.append({
            "line_id": i,
            "text": line,
            "entities": entities
        })
    return results

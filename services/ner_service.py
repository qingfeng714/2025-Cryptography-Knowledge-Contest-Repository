import csv
import re
from typing import List, Dict

class NERService:
    def __init__(self):
        # 定义 PII（个人身份信息）的正则表达式
        self.pii_patterns = {
            "Name": r"[A-Z][a-z]+ [A-Z][a-z]+",  # 简单匹配英文名（如 "Janice Female"）
            "Phone": r"\d{11}",  # 11位电话号码（如 "14730120855"）
            "ID_Number": r"\d{17}[\dXx]",  # 18位身份证号（如 "420801194404259577"）
            "Address": r".+?(路|街|座|县|市|区|省)",  # 粗略匹配地址
        }

    def detect_pii(self, text: str) -> Dict[str, List[str]]:
        """检测文本中的 PII（个人身份信息）"""
        detected_pii = {}
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected_pii[pii_type] = matches
        return detected_pii

    def anonymize_text(self, text: str) -> str:
        """匿名化文本（替换 PII 为占位符）"""
        for pii_type, pattern in self.pii_patterns.items():
            text = re.sub(pattern, f"[{pii_type}]", text)
        return text

    def process_csv(self, input_csv: str, output_csv: str):
        """处理 CSV 文件，检测并匿名化 PII"""
        with open(input_csv, mode="r", encoding="utf-8") as infile, \
             open(output_csv, mode="w", encoding="utf-8", newline="") as outfile:
            
            reader = csv.DictReader(infile)
            writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                # 检测 PII
                pii_report = {}
                for field, value in row.items():
                    pii_report[field] = self.detect_pii(value)

                # 匿名化所有字段
                anonymized_row = {
                    field: self.anonymize_text(value)
                    for field, value in row.items()
                }import re
from typing import Dict, List, Optional
import pandas as pd

class NERService:
    def __init__(self):
        """初始化正则表达式规则（匹配中文医疗文本中的敏感实体）"""
        self.patterns = {
            "NAME": r"(患者|姓名)([\u4e00-\u9fa5]{2,4})",  # 中文姓名
            "ID": r"(身份证|病历号)(\d{17}[\dXx]|\d{15})",  # 身份证号
            "PHONE": r"(电话|手机)(1[3-9]\d{9})",  # 手机号
            "AGE": r"(\d{1,3})岁",  # 年龄
            "DATE": r"(\d{4}[年\-]\d{1,2}[月\-]\d{1,2}日?)",  # 日期
            "ADDRESS": r"(地址|住址)([\u4e00-\u9fa5]+(省|市|区|县|街道|路|号))",  # 地址
        }

    def detect_from_text(self, text: str) -> List[Dict]:
        """
        从单条文本中提取敏感实体
        :param text: 输入文本（如 "患者张三，电话13800138000"）
        :return: [{"type": "NAME", "text": "张三", "start": 2, "end": 4, "confidence": 0.95}, ...]
        """
        entities = []
        for entity_type, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                start, end = match.start(2), match.end(2)  # 第2个分组是实体内容
                entities.append({
                    "type": entity_type,
                    "text": match.group(2),
                    "start": start,
                    "end": end,
                    "confidence": self._calc_confidence(entity_type, match.group(2))
                })
        return entities

    def detect_from_dataframe(self, df: pd.DataFrame, text_column: str = "text") -> pd.DataFrame:
        """
        从DataFrame中批量检测敏感实体
        :param df: 输入DataFrame（必须包含文本列）
        :param text_column: 文本列的列名（默认"text"）
        :return: 新增了"entities"列的DataFrame（每行存储该文本的实体列表）
        """
        df["entities"] = df[text_column].apply(self.detect_from_text)
        return df

    def anonymize_text(self, text: str, entities: List[Dict]) -> str:
        """
        匿名化文本（用占位符替换敏感实体）
        :param text: 原始文本
        :param entities: detect_from_text()返回的实体列表
        :return: 匿名化后的文本（如 "患者[NAME]，电话[PHONE]"）
        """
        # 按起始位置逆序处理，避免影响后续位置
        for entity in sorted(entities, key=lambda x: -x["start"]):
            text = text[:entity["start"]] + f"[{entity['type']}]" + text[entity["end"]:]
        return text

    def _calc_confidence(self, entity_type: str, text: str) -> float:
        """计算实体识别置信度（可自定义规则）"""
        base_conf = {
            "NAME": 0.95,
            "ID": 0.99,
            "PHONE": 0.97,
            "AGE": 0.90,
            "DATE": 0.93,
            "ADDRESS": 0.85,
        }
        return base_conf.get(entity_type, 0.8) * min(1.0, 0.9 + 0.1 * len(text) / 10)  # 长度越长置信度越高
                writer.writerow(anonymized_row)

        print(f"处理完成！已保存到 {output_csv}")

# 示例用法
if __name__ == "__main__":
    ner_service = NERService()
    ner_service.process_csv(
        input_csv="train_with_sensitive_info.csv",
        output_csv="anonymized_train.csv"
    )
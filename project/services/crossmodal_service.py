# services/crossmodal_service.py
import torch
from transformers import AutoTokenizer, AutoModel
from ner_service import detectPHI
from roi_service import segment_roi, mask_to_bbox

# 文本特征提取模型
TEXT_MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"
tokenizer = AutoTokenizer.from_pretrained(TEXT_MODEL_NAME)
text_model = AutoModel.from_pretrained(TEXT_MODEL_NAME)
text_model.eval()

def extract_text_features(texts):
    """将文本实体转换为向量"""
    encoded = tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = text_model(**encoded)
        # 使用 [CLS] token 作为句向量
        features = outputs.last_hidden_state[:, 0, :]
    return features  # shape [len(texts), hidden_size]

def crossmodal_mapping(image_array, text_lines):
    """
    输入：
        image_array: np.ndarray, 医疗影像
        text_lines: List[str], 每行病历文本
    输出：
        List[dict], 每个 PHI 实体 + 对应 ROI
    """
    results = []
    # 文本识别
    for line_id, line in enumerate(text_lines, start=1):
        entities = detectPHI(line)
        for e in entities:
            results.append({
                "line_id": line_id,
                "entity": e.get("entity"),
                "text": e.get("text")
            })
    
    # ROI 分割
    mask = segment_roi(image_array)
    bbox = mask_to_bbox(mask)

    # 简单对应策略：所有实体映射到同一 ROI
    for r in results:
        r["roi_bbox"] = bbox
        r["roi_confidence"] = 1.0 if bbox is not None else 0.0
    
    return results

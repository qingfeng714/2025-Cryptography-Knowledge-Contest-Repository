# 基于轻量密码标准的医疗影像文本隐私保护系统设计 

## 完成情况：

## 功能流程

- PACS/上传端 POST /ingest → DICOM 校验、提取 Pixel Data 与元数据；
- 感知层：
    
    ROI segmentation (UNet/nnUNet) 【未完成，需要训练UNet模型or接入成熟的影像处理模型】
    
    文本 NER (ClinicalBERT) 【已完成，可支持处理中英文文本】
    
    跨模态 fusion（Transformer cross-attention）输出 PHI 实体与影像对应映射；
    
- 保护层：
    
    Policy Engine 决策（FPE / Encrypt / Mask / Preserve ROI）
    
    调用混合加密器（Ascon + FF3 + SPHINCS+）生成受保护 artifact；
    
- 存储与审计：写入密文、签名与审计日志；
- 验证擦除：
    
    POST /erase
    
    销毁密钥（KMS）
    
    生成经签名的擦除证明并写入 append-only 审计链
    
    GET /verify/erasure/{artifact} 验证擦除证明

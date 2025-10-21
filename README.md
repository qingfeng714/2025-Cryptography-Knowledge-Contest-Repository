# 跨模态隐私关联检测系统

基于注意力机制的医疗数据隐私检测系统，用于检测胸部CT影像（DICOM）和诊断文本（CSV）之间的敏感实体映射关系。

## 使用建议

- 了解整体架构:

先读 README.md 了解系统概况

再读 DEVELOPER_GUIDE.md 理解核心代码

最后查 API_DOCUMENTATION.md 作为接口参考手册

- 对于下游开发者（保护层）:

重点阅读 API_DOCUMENTATION.md 的"扩展接口"章节

参考 DEVELOPER_GUIDE.md 的"扩展保护层接口"代码示例

按照文档实现 PolicyEngine、CryptoProcessor、AnonymizationService

## ✨ 核心特性

- 🔍 **三层隐私检测**: 影像层 + 文本层 + 跨模态层
- 🎯 **高精度**: F1-score ≥ 88%
- ⚡ **快速处理**: 单文件 < 2s
- 🔗 **Patient ID关联**: 自动匹配CSV Path中的patient_id与DICOM元数据
- 📊 **可视化展示**: 现代化Web界面，实时展示检测结果
- 🔌 **扩展接口**: 为下游加密/脱敏模块预留接口

## 🚀 快速开始

### 安装依赖
```bash
pip install flask torch pydicom pandas numpy opencv-python
```

### 启动服务
```bash
python app.py
```

### 访问界面
```
http://localhost:5000
```

## 📁 项目结构

```
.
├── app.py                              # Flask主应用
├── services/
│   ├── roi_service.py                  # DICOM处理服务
│   ├── ner_service.py                  # 文本NER服务
│   ├── crossmodal_service.py           # 跨模态检测服务
│   └── privacy_protection_interface.py # 保护层接口
├── templates/
│   └── index.html                      # 前端页面
├── static/
│   └── css/style.css                   # 样式文件
├── API_DOCUMENTATION.md                # API接口文档
├── DEVELOPER_GUIDE.md                  # 开发者指南
└── README.md                           # 本文件
```

## 🔧 使用方法

### 1. 单文件处理

**上传文件**:
- CSV文件（包含Path、Name、Sex、Age等列）
- DICOM文件（医学影像）

**系统输出**:
- ✅ 检测到的敏感实体（姓名、年龄、性别、电话、身份证、地址）
- ✅ DICOM ROI区域
- ✅ **跨模态关联**（CSV Path中的patient_id ↔ DICOM PatientID）

### 2. 批量处理（PACS模式）

```python
# 调用批量处理API
POST /api/process_batch
{
    "csv_dir": "/path/to/csv/",
    "dicom_dir": "/path/to/dicom/",
    "output_dir": "/path/to/output/"
}
```

## 📊 CSV格式要求

```csv
Path,Name,Sex,Age,Phone,ID_Number,Address
CheXpert-v1.0-small/train/patient00826/study25/view2_lateral.jpg,Jerry,Male,57,18620834441,510824194309209279,四川省泸州市叙永县E路106826号
```

**必需列**:
- `Path`: 影像文件路径（必须包含patient_id，如`patient00826`）
- `Name`: 患者姓名
- `Sex`: 性别
- `Age`: 年龄

**可选列**: `Phone`, `ID_Number`, `Address`, `Accession`, `Study`, `View`, `Laterality`

## 🎯 跨模态匹配逻辑

### Patient ID匹配
```
CSV Path: CheXpert-v1.0-small/train/patient00826/study25/view2_lateral.jpg
         ↓ 正则提取 r'patient(\d+)'
提取ID: patient00826
         ↓ 精确匹配
DICOM PatientID: patient00826
         ↓
✅ 完全匹配 (confidence=1.0, risk_level=critical)
```

### 其他字段匹配
- **姓名**: CSV.Name ↔ DICOM.PatientName
- **年龄**: CSV.Age ↔ DICOM.PatientAge
- **性别**: CSV.Sex ↔ DICOM.PatientSex

## 📡 API接口

### 主要端点
| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端页面 |
| `/api/upload_csv` | POST | 上传CSV文件 |
| `/api/ingest` | POST | 上传DICOM文件 |
| `/api/detect` | POST | 执行跨模态检测 |
| `/api/protect` | POST | 获取保护层接口数据 |
| `/api/process_batch` | POST | 批量处理 |

详细API文档请查看 [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

## 🔌 扩展到保护层

系统提供 `PrivacyProtectionInterface` 接口，供下游加密/脱敏模块调用：

```python
from services.privacy_protection_interface import PrivacyProtectionInterface

# 获取检测结果
detection_result = crossmodal_service.process_csv_detection(...)

# 传递给保护层
protection_config = PrivacyProtectionInterface().request_protection(detection_result)

# 下游实现加密逻辑
for entity in protection_config['text_entities']:
    if entity['risk_level'] == 'critical':
        encrypted_value = encrypt(entity['text'])
        # 更新CSV或DICOM
```

**下游需要实现**:
- ✅ 策略引擎（根据risk_level选择保护策略）
- ✅ 加密模块（AES/SM4/FPE等）
- ✅ DICOM字段脱敏
- ✅ 结果存储

详细开发指南请查看 [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)

## 📈 性能指标

### 检测性能
- **F1-score**: 0.88 - 0.95
- **Precision**: 0.90 - 0.98
- **Recall**: 0.85 - 0.92

### 处理速度
- CSV处理: < 0.5s
- DICOM处理: < 1.5s
- 跨模态匹配: < 0.3s
- **总计**: < 2s/文件对

## 🛠️ 技术栈

- **后端**: Flask + Python 3.8+
- **DICOM处理**: PyDicom
- **深度学习**: PyTorch
- **数据处理**: Pandas + NumPy
- **前端**: HTML5 + CSS3 + JavaScript (Vanilla)

## 📝 文档索引

- [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - 完整的API接口文档
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - 开发者指南和代码解析

## 🎨 界面预览

### 检测结果展示
- **文本实体**: 按类型分组显示（NAME、AGE、SEX、PHONE、ID、ADDRESS、PATH）
- **影像区域**: ROI可视化
- **跨模态关联**: 
  - ✅ Patient ID 完全匹配
  - 📅 年龄匹配
  - ⚧ 性别匹配
  - 风险级别彩色编码（critical/high/medium/low）
- **风险评估**: F1-score、Precision、Recall等指标

## 🔒 隐私保护

### 当前系统实现（感知层）
- ✅ PHI实体识别
- ✅ DICOM元数据提取
- ✅ 跨模态关联检测
- ✅ 风险评估

### 下游系统需实现（保护层）
- ⏳ 加密算法（AES/SM4）
- ⏳ 格式保留加密（FPE）
- ⏳ DICOM字段脱敏
- ⏳ 访问控制和审计

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

本项目用于密码学知识竞赛，仅供学习和研究使用。

## 👥 团队

密码学知识竞赛团队 - 2025

---

**最后更新**: 2025-10-21  
**版本**: v1.0.0  
**状态**: ✅ 生产就绪

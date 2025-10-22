# 快速开始指南

## 🚀 5分钟快速体验

### 步骤1: 安装依赖

```bash
cd 2025-Cryptography-Knowledge-Contest-Repository

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤2: 启动服务

```bash
python app.py
```

启动成功后，您会看到：
```
[INFO] 文件清理服务已启动
[INFO] 保护层密钥提示: a1b2c3d4e5f6g7h8...
[INFO] 存储仓库路径: ./storage_repo
 * Running on http://0.0.0.0:5000
```

### 步骤3: 访问界面

打开浏览器，访问:
```
http://localhost:5000
```

### 步骤4: 上传测试数据

#### 准备测试数据

**CSV文件示例** (`test_patients.csv`):
```csv
Path,Name,Sex,Age,Phone,ID_Number,Address
CheXpert-v1.0-small/train/patient00826/study25/view2_lateral.jpg,Jerry,Male,57,18620834441,510824194309209279,四川省泸州市叙永县E路106826号
CheXpert-v1.0-small/train/patient00827/study1/view1_frontal.jpg,Alice,Female,35,13812345678,110101199001011234,北京市朝阳区建国路1号
```

**DICOM文件**:
- 需要有对应patient ID的DICOM文件
- 文件名可以是: `patient00826.dcm`, `patient00827.dcm`

#### 上传操作

1. 在"批量处理"部分
2. 选择CSV文件（1个）
3. 选择DICOM文件（多个，可以按住Ctrl多选）
4. 点击"批量处理"

### 步骤5: 查看检测结果

等待几秒后，系统会显示：
- ✅ 检测到的敏感实体（姓名、年龄、性别、电话等）
- ✅ 跨模态关联（CSV与DICOM的Patient ID匹配）
- ✅ 风险评估

### 步骤6: 执行保护

1. 点击"执行保护"按钮
2. 等待保护完成
3. 查看保护结果：
   - 批次ID
   - 保护数量
   - 密钥提示
   - 输出路径

### 步骤7: 存储入库

1. 点击"存储入库"按钮
2. 等待入库完成
3. 提示：`入库成功！批次ID: xxx, 入库数量: xx`

### 步骤8: 查看存储

1. 点击"查看存储"按钮
2. 浏览：
   - **存储对象**: 查看已存储的DICOM-JSON对
   - **批次列表**: 查看所有批次
   - **统计信息**: 总对象数、总批次数

### 步骤9: 验证

1. 切换到"验证工具"标签
2. 输入Patient ID (例如: `patient00826`)
3. 点击"构建并验证Bundle"
4. 查看验证结果：
   - SPHINCS+签名验证
   - DICOM-JSON对验证
   - Header信息
5. 点击"下载Bundle"获取ZIP文件

---

## 🎯 完整工作流程示意

```
┌──────────────┐
│ 1. 上传数据  │  CSV (1个) + DICOM (多个)
└──────┬───────┘
       ↓
┌──────────────┐
│ 2. 批量检测  │  跨模态隐私关联检测
└──────┬───────┘
       ↓
┌──────────────┐
│ 3. 查看结果  │  文本实体、跨模态关联、风险评估
└──────┬───────┘
       ↓
┌──────────────┐
│ 4. 执行保护  │  Ascon AEAD + FPE + SPHINCS+签名
└──────┬───────┘
       ↓
┌──────────────┐
│ 5. 存储入库  │  CAS + SQLite索引
└──────┬───────┘
       ↓
┌──────────────┐
│ 6. 验证下载  │  验证完整性 + 下载Bundle
└──────────────┘
```

---

## 📋 API测试示例

### 使用Python脚本测试

```python
import requests
import json

BASE_URL = "http://localhost:5000"

# 1. 上传CSV
csv_files = {'csv_file': open('test_patients.csv', 'rb')}
csv_resp = requests.post(f"{BASE_URL}/api/upload_csv", files=csv_files)
csv_data = csv_resp.json()
print(f"CSV上传成功: {csv_data['csv_id']}")

# 2. 批量上传DICOM
dicom_files = [
    ('dicom_files', open('patient00826.dcm', 'rb')),
    ('dicom_files', open('patient00827.dcm', 'rb'))
]
dicom_resp = requests.post(f"{BASE_URL}/api/batch_upload_dicom", files=dicom_files)
dicom_data = dicom_resp.json()
print(f"DICOM上传成功: {dicom_data['processed']} 个文件")

# 3. 批量检测
detect_resp = requests.post(f"{BASE_URL}/api/batch_detect", json={
    "csv_path": csv_data['csv_path'],
    "dicom_metadata_list": dicom_data['metadata_list']
})
detection_result = detect_resp.json()
print(f"检测成功: 匹配 {detection_result['matched']} 个对象")

# 4. 执行保护
protect_resp = requests.post(f"{BASE_URL}/api/protect_execute", json={
    "detection_result": detection_result,
    "batch_id": "test_batch_001"
})
protect_data = protect_resp.json()
print(f"保护成功: {protect_data['protected_count']} 个对象")

# 5. 存储入库
ingest_resp = requests.post(f"{BASE_URL}/api/storage/ingest", json={
    "batch_id": protect_data['batch_id']
})
ingest_data = ingest_resp.json()
print(f"入库成功: {ingest_data['ingested']} 个对象")

# 6. 验证
verify_resp = requests.post(f"{BASE_URL}/api/verify/repo", json={
    "patient_id": "patient00826"
})
verify_data = verify_resp.json()
print(f"验证结果: {verify_data}")

# 7. 构建Bundle
bundle_resp = requests.post(f"{BASE_URL}/api/storage/bundle", json={
    "patient_id": "patient00826"
})
bundle_data = bundle_resp.json()
print(f"Bundle路径: {bundle_data['bundle_path']}")
```

### 使用curl测试

```bash
# 1. 上传CSV
curl -X POST http://localhost:5000/api/upload_csv \
  -F "csv_file=@test_patients.csv"

# 2. 执行保护（需要先获取detection_result）
curl -X POST http://localhost:5000/api/protect_execute \
  -H "Content-Type: application/json" \
  -d '{"detection_result": {...}, "batch_id": "test_batch"}'

# 3. 存储入库
curl -X POST http://localhost:5000/api/storage/ingest \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "test_batch"}'

# 4. 查看存储列表
curl http://localhost:5000/api/storage/list?limit=10

# 5. 验证
curl -X POST http://localhost:5000/api/verify/repo \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "patient00826"}'

# 6. 下载Bundle
curl -O http://localhost:5000/api/storage/bundle/patient00826/download
```

---

## 📁 目录结构说明

执行完整流程后，您会看到以下目录结构：

```
2025-Cryptography-Knowledge-Contest-Repository/
├── uploads/                    # 上传的临时文件（24小时后自动清理）
│   ├── csv_abc123.csv
│   └── batch_xyz/
│       ├── patient00826.dcm
│       └── patient00827.dcm
│
├── output/                     # 保护后的输出
│   └── batch_test_001/
│       ├── protected_dicom/
│       │   ├── patient00826.dcm  # 保护后的DICOM
│       │   └── patient00827.dcm
│       └── protected_text/
│           ├── patient00826.json  # 文本bundle
│           ├── patient00827.json
│           ├── audit_manifest.json
│           ├── audit_manifest.sig
│           └── audit_manifest.pk
│
├── storage_repo/               # 存储仓库（CAS + SQLite）
│   ├── cas/                    # 内容寻址存储
│   │   ├── ab/
│   │   │   └── cdef1234...
│   │   └── ...
│   ├── db/
│   │   └── index.sqlite        # 元数据索引
│   └── batches/
│       └── batch_test_001/
│           ├── audit_manifest.json
│           ├── audit_manifest.sig
│           └── audit_manifest.pk
│
└── bundles/                    # 导出的Bundle
    └── patient00826_bundle.zip
```

---

## ⚙️ 配置选项

### 启动参数

```bash
python app.py \
  --host 0.0.0.0 \
  --port 5000 \
  --upload-folder ./uploads \
  --output-dir ./output
```

### 环境变量

```bash
export STORAGE_REPO="./storage_repo"
export MAX_FILE_SIZE="500"  # MB
```

---

## 🔍 常见问题

### Q: 批量检测时显示"匹配0个对象"？

**A**: 检查以下几点：
1. CSV的Path列是否包含`patientXXXXX`格式的ID
2. DICOM文件的PatientID是否与CSV中的ID匹配
3. DICOM文件是否正确上传（检查文件大小）

### Q: 保护失败，提示"检测结果未找到"？

**A**: 确保先执行批量检测，再点击"执行保护"按钮

### Q: 验证时提示"Patient ID not found"？

**A**: 
1. 检查Patient ID拼写是否正确
2. 确保已执行存储入库操作
3. 使用"查看存储"功能确认对象已入库

### Q: SPHINCS+签名不可用？

**A**: 
```bash
pip install pyspx
```
如果安装失败，系统会跳过签名，不影响核心功能。

---

## 📊 性能提示

### 批量处理优化

- **建议批次大小**: 100-500个DICOM文件/批次
- **并发上传**: 浏览器会自动分批上传（每批100个）
- **处理时间**: 约2-3秒/对象（包含检测+保护）

### 存储空间

- **CAS去重**: 相同内容只存储一次
- **估算**: 每个对象约1-2MB（DICOM + JSON）
- **SQLite索引**: 约1KB/对象

---

## 🎓 下一步

完成快速开始后，建议阅读：

1. **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** - 详细的集成指南
2. **[API_DOCUMENTATION.md](./API_DOCUMENTATION.md)** - 完整的API文档
3. **[DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)** - 开发者指南

---

**祝您使用愉快！** 🎉

如有问题，请查阅文档或提交Issue。

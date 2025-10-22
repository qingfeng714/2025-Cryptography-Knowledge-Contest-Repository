# 🧪 系统测试指南

## 📋 测试前准备

### 1. 环境检查

```bash
# 检查Python版本（需要3.8+）
python --version

# 检查当前目录
pwd
# 应该在: .../2025-Cryptography-Knowledge-Contest-Repository
```

### 2. 安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 验证关键包
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import pandas; print('Pandas:', pandas.__version__)"
python -c "import pydicom; print('PyDICOM:', pydicom.__version__)"

# 验证保护层依赖（可选，如果失败不影响核心功能）
python -c "import ascon; print('Ascon: OK')" 2>/dev/null || echo "Ascon: Not installed (Optional)"
python -c "import pyspx; print('SPHINCS+: OK')" 2>/dev/null || echo "SPHINCS+: Not installed (Optional)"
```

### 3. 准备测试数据

创建测试CSV文件 `test_data.csv`:
```csv
Path,Name,Sex,Age,Phone,ID_Number,Address
CheXpert-v1.0-small/train/patient00001/study1/view1_frontal.jpg,张三,Male,35,13812345678,110101198901011234,北京市朝阳区建国路1号
CheXpert-v1.0-small/train/patient00002/study1/view1_frontal.jpg,李四,Female,28,13987654321,310101199201012345,上海市浦东新区世纪大道2号
CheXpert-v1.0-small/train/patient00003/study1/view1_frontal.jpg,王五,Male,42,15812345678,440101198001013456,广东省广州市天河区中山大道3号
```

**注意**: 如果您有真实的DICOM文件，请确保它们的PatientID与CSV中的patient ID对应（如：patient00001.dcm）

---

## 🚀 启动测试

### 步骤1: 启动服务

```bash
cd 2025-Cryptography-Knowledge-Contest-Repository
python app.py
```

**预期输出**:
```
[INFO] 文件清理服务已启动
[INFO] 保护层密钥提示: <16位十六进制>...
[INFO] 存储仓库路径: ./storage_repo
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://0.0.0.0:5000
Press CTRL+C to quit
```

### 步骤2: 访问界面

打开浏览器，访问: `http://localhost:5000`

**预期**: 看到"医疗隐私保护系统"主页面

---

## ✅ 功能测试清单

### 测试1: 基础界面检查 ✓

**操作**:
1. 打开 `http://localhost:5000`
2. 检查页面元素

**预期结果**:
- [x] 看到"医疗隐私保护系统"标题
- [x] 有"单文件处理"和"批量处理"两个表单
- [x] 有文件上传输入框
- [x] 有"上传并检测"和"批量处理"按钮

**状态**: ___________

---

### 测试2: CSV文件上传 ✓

**操作**:
1. 在"批量处理"部分
2. 选择 `test_data.csv`
3. 点击"批量处理"按钮

**预期结果**:
- [x] 显示进度条
- [x] 显示"上传CSV文件..."
- [x] 几秒后提示需要DICOM文件或显示CSV检测结果

**API测试**（终端）:
```bash
curl -X POST http://localhost:5000/api/upload_csv \
  -F "csv_file=@test_data.csv"
```

**预期响应**:
```json
{
  "csv_id": "csv_xxxxxxxx",
  "csv_path": "./uploads/csv_xxxxxxxx.csv",
  "filename": "test_data.csv",
  "status": "success"
}
```

**状态**: ___________

---

### 测试3: 批量检测（仅CSV）✓

**操作**:
1. 上传CSV（不上传DICOM）
2. 观察检测结果

**预期结果**:
- [x] 检测到实体（NAME, SEX, AGE, PHONE, ID_NUMBER, ADDRESS, PATH）
- [x] 显示文本实体列表
- [x] 按类型分组显示（👤 NAME, ⚧ SEX, 📅 AGE等）
- [x] 显示"未发现跨模态关联"（因为没有DICOM）

**API测试**:
```bash
# 先上传CSV获取csv_id
CSV_ID="<从上一步获取>"

# 执行检测
curl -X POST http://localhost:5000/api/detect \
  -H "Content-Type: application/json" \
  -d "{\"csv_id\": \"$CSV_ID\"}"
```

**状态**: ___________

---

### 测试4: 批量检测（CSV + DICOM）✓

**前提**: 需要有DICOM文件，且PatientID匹配CSV中的patient ID

**操作**:
1. 上传CSV文件
2. 上传多个DICOM文件
3. 点击"批量处理"
4. 等待检测完成

**预期结果**:
- [x] 显示进度条（上传、匹配、检测）
- [x] 显示"批量跨模态检测完成"
- [x] 显示匹配统计（总病人数、成功匹配、未匹配）
- [x] 显示跨模态关联详情
- [x] Patient ID匹配显示绿色✅标记
- [x] 显示风险级别（critical/high/medium/low）

**API测试**:
```bash
# 上传DICOM并获取元数据
curl -X POST http://localhost:5000/api/batch_upload_dicom \
  -F "dicom_files=@patient00001.dcm" \
  -F "dicom_files=@patient00002.dcm"

# 执行批量检测
curl -X POST http://localhost:5000/api/batch_detect \
  -H "Content-Type: application/json" \
  -d '{
    "csv_path": "./uploads/csv_xxxxxxxx.csv",
    "dicom_metadata_list": [...]
  }'
```

**状态**: ___________

---

### 测试5: 执行保护 ✓ 🆕

**操作**:
1. 完成批量检测后
2. 点击"执行保护"按钮
3. 等待保护完成

**预期结果**:
- [x] 显示进度条（0% → 10% → 60% → 100%）
- [x] 显示"保护完成"
- [x] 显示批次ID
- [x] 显示保护数量
- [x] 显示密钥提示（16位hex）
- [x] 显示输出路径
- [x] 显示审计清单路径
- [x] "存储入库"按钮变为可见

**检查输出文件**:
```bash
# 检查保护后的文件
BATCH_ID="<从界面获取>"
ls -la output/$BATCH_ID/protected_dicom/
ls -la output/$BATCH_ID/protected_text/

# 检查审计清单
cat output/$BATCH_ID/protected_text/audit_manifest.json | python -m json.tool
```

**API测试**:
```bash
curl -X POST http://localhost:5000/api/protect_execute \
  -H "Content-Type: application/json" \
  -d '{
    "detection_result": {...},
    "batch_id": "test_batch_001"
  }'
```

**状态**: ___________

---

### 测试6: 存储入库 ✓ 🆕

**操作**:
1. 保护完成后
2. 点击"存储入库"按钮
3. 等待入库完成

**预期结果**:
- [x] 显示进度条
- [x] 弹出提示："入库成功！批次ID: xxx, 入库数量: x"
- [x] 可以看到审计SHA256

**检查存储**:
```bash
# 检查CAS目录
ls -la storage_repo/cas/

# 检查SQLite数据库
sqlite3 storage_repo/db/index.sqlite "SELECT * FROM objects LIMIT 5;"
sqlite3 storage_repo/db/index.sqlite "SELECT * FROM batches;"

# 检查批次材料
ls -la storage_repo/batches/
```

**API测试**:
```bash
curl -X POST http://localhost:5000/api/storage/ingest \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "test_batch_001"}'
```

**状态**: ___________

---

### 测试7: 查看存储 ✓ 🆕

**操作**:
1. 点击"查看存储"按钮
2. 浏览各个标签页

**预期结果**:

**存储对象标签页**:
- [x] 显示对象列表
- [x] 每个对象显示：ID、Patient ID、SOP UID、Batch ID、SHA256
- [x] 显示时间戳

**批次列表标签页**:
- [x] 显示批次列表
- [x] 每个批次显示：Batch ID、对象数、审计SHA256、签名状态
- [x] 显示时间戳

**统计信息标签页**:
- [x] 显示总对象数
- [x] 显示总批次数
- [x] 显示仓库路径

**API测试**:
```bash
# 列出对象
curl http://localhost:5000/api/storage/list?limit=10

# 列出批次
curl http://localhost:5000/api/storage/batches?limit=10

# 获取统计
curl http://localhost:5000/api/storage/stats
```

**状态**: ___________

---

### 测试8: 验证功能 ✓ 🆕

**操作**:
1. 切换到"验证工具"标签页
2. 输入Patient ID（如：patient00001）
3. 点击"从仓库验证"

**预期结果**:
- [x] 显示验证结果
- [x] 显示SPHINCS+签名验证状态（通过/失败/无签名）
- [x] 显示DICOM-JSON对验证
- [x] 显示问题数（应为0）
- [x] 显示DICOM Header信息

**操作2**:
4. 点击"构建并验证Bundle"

**预期结果**:
- [x] 构建Bundle成功
- [x] 显示Bundle路径
- [x] 显示验证结果
- [x] 显示"下载Bundle"按钮

**API测试**:
```bash
# 从仓库验证
curl -X POST http://localhost:5000/api/verify/repo \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "patient00001"}'

# 构建Bundle
curl -X POST http://localhost:5000/api/storage/bundle \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "patient00001"}'

# 验证Bundle
curl -X POST http://localhost:5000/api/verify/bundle \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "patient00001"}'
```

**状态**: ___________

---

### 测试9: Bundle下载 ✓ 🆕

**操作**:
1. 在验证结果中
2. 点击"下载Bundle"链接

**预期结果**:
- [x] 下载 `patient00001_bundle.zip` 文件
- [x] ZIP文件包含：
  - patient00001.dcm（保护后的DICOM）
  - patient00001.json（文本bundle）
  - audit_manifest.json（审计清单）
  - audit_manifest.sig（签名，如果有）
  - audit_manifest.pk（公钥，如果有）

**验证ZIP内容**:
```bash
# 解压查看
unzip -l output/bundles/patient00001_bundle.zip

# 查看JSON内容
unzip -p output/bundles/patient00001_bundle.zip patient00001.json | python -m json.tool
```

**API测试**:
```bash
# 下载Bundle
curl -O http://localhost:5000/api/storage/bundle/patient00001/download
```

**状态**: ___________

---

### 测试10: 密钥信息 ✓ 🆕

**操作**:
```bash
curl http://localhost:5000/api/key_info
```

**预期响应**:
```json
{
  "key_hint": "<16位hex>",
  "key_length": 64,
  "has_ascon": true/false
}
```

**状态**: ___________

---

## 🔍 验证保护效果

### 检查DICOM保护

```bash
BATCH_ID="<您的批次ID>"

# 查看原始DICOM（如果有）
python -c "
import pydicom
ds = pydicom.dcmread('patient00001.dcm')
print('原始 PatientID:', ds.PatientID)
print('原始 StudyDate:', ds.StudyDate)
"

# 查看保护后的DICOM
python -c "
import pydicom
ds = pydicom.dcmread('output/$BATCH_ID/protected_dicom/patient00001.dcm')
print('保护后 PatientID:', ds.PatientID)
print('保护后 StudyDate:', ds.StudyDate)
print('私有标签:', ds.get((0x0011, 0x0010)))
"
```

### 检查文本Bundle

```bash
cat output/$BATCH_ID/protected_text/patient00001.json | python -m json.tool
```

**预期内容**:
```json
{
  "dicom_out": "...",
  "sop": "1.2.840...",
  "assoc": "batch_xxx",
  "columns": {
    "patient_id": "TOKEN_ABC123",
    "patient_sex": "ENCRYPTED",
    "patient_age": "TOKEN_XX"
  },
  "columns_cipher": {
    "patient_id": {
      "token": "TOKEN_ABC123",
      "cipher_b64": "base64...",
      "hash": "sha256...",
      "ad": "{...}",
      "nonce": "hex..."
    }
  }
}
```

---

## 📊 性能测试

### 测试处理速度

```bash
# 记录开始时间
echo "开始时间: $(date)"

# 执行完整流程
# 1. 上传
# 2. 检测
# 3. 保护
# 4. 入库

# 记录结束时间
echo "结束时间: $(date)"
```

**预期性能**:
- 上传: < 1秒
- 检测: < 5秒（10个对象）
- 保护: < 1秒（10个对象，~50ms/对象）
- 入库: < 1秒（10个对象，~20ms/对象）
- **总计**: < 10秒

---

## 🐛 常见问题排查

### 问题1: 服务启动失败

**错误**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:
```bash
pip install -r requirements.txt
```

---

### 问题2: 批量检测匹配0个对象

**原因**:
1. CSV Path列不包含`patientXXXXX`格式
2. DICOM PatientID与CSV不匹配

**检查**:
```bash
# 检查CSV内容
cat test_data.csv | head -n 5

# 检查DICOM PatientID
python -c "
import pydicom
ds = pydicom.dcmread('patient00001.dcm')
print('PatientID:', ds.PatientID)
"
```

---

### 问题3: 保护失败

**错误**: `检测结果未找到`

**原因**: 未执行批量检测

**解决**: 先执行批量检测，再点击"执行保护"

---

### 问题4: 入库失败

**错误**: `Protected files not found`

**原因**: 保护操作未完成

**检查**:
```bash
ls -la output/<batch_id>/protected_dicom/
ls -la output/<batch_id>/protected_text/
```

---

### 问题5: SPHINCS+签名不可用

**警告**: `No module named 'pyspx'`

**说明**: 这是可选功能，不影响核心功能

**安装**（可选）:
```bash
pip install pyspx
```

---

## ✅ 测试结果汇总

### 功能测试结果

| 功能 | 状态 | 备注 |
|------|------|------|
| CSV上传 | ⬜ | |
| 批量检测 | ⬜ | |
| 跨模态关联 | ⬜ | |
| 执行保护 | ⬜ | |
| 存储入库 | ⬜ | |
| 查看对象 | ⬜ | |
| 查看批次 | ⬜ | |
| 统计信息 | ⬜ | |
| 验证功能 | ⬜ | |
| Bundle下载 | ⬜ | |

**图例**: ✅ 通过 | ❌ 失败 | ⬜ 未测试

### 性能测试结果

- 检测速度: _______ 秒/对象
- 保护速度: _______ 秒/对象
- 入库速度: _______ 秒/对象
- 总体性能: _______ 秒/对象

### 问题记录

记录测试中遇到的问题：

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

---

## 🎯 测试完成检查清单

- [ ] 所有功能测试通过
- [ ] 性能符合预期（< 2秒/对象）
- [ ] 无严重错误
- [ ] 输出文件完整
- [ ] 验证功能正常
- [ ] 文档清晰可读

---

## 📞 获取帮助

如果测试中遇到问题：

1. 查看控制台错误日志
2. 检查 `INTEGRATION_GUIDE.md` 的故障排查部分
3. 查看 `QUICKSTART.md` 的常见问题
4. 提交Issue并附上错误日志

---

**测试愉快！** 🧪✨

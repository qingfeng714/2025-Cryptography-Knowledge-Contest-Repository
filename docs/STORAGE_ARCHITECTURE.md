# 系统存储架构说明

## 📊 存储文件类型概览

系统采用**分层存储架构**，最终存储的文件包括：

| 层级 | 文件类型 | 格式 | 存储位置 | 说明 |
|------|---------|------|---------|------|
| **1. 保护层** | 保护后的DICOM | `.dcm` | `output/batch_*/protected_dicom/` | 加密/脱敏后的医学影像 |
| **1. 保护层** | 保护后的文本 | `.json` | `output/batch_*/protected_text/` | 加密的CSV数据 |
| **1. 保护层** | 审计清单 | `.json` | `output/batch_*/protected_text/` | 批次审计信息 |
| **1. 保护层** | 数字签名 | `.sig` | `output/batch_*/protected_text/` | SPHINCS+签名（可选）|
| **1. 保护层** | 公钥 | `.pk` | `output/batch_*/protected_text/` | 签名验证公钥 |
| **2. 存储层** | CAS对象 | 无扩展名 | `storage_repo/cas/` | 内容寻址存储 |
| **2. 存储层** | 批次审计 | `.json` | `storage_repo/batches/` | 批次元数据 |
| **2. 存储层** | 索引数据库 | `.sqlite` | `storage_repo/db/` | 对象索引 |
| **3. 应用层** | 验证包 | `.zip` | `output/bundles/` | 可验证的数据包 |

---

## 🔐 第1层：保护层文件

### 📁 目录结构

```
output/
└── batch_1761149193606/           # 批次ID
    ├── protected_dicom/            # 保护后的DICOM文件
    │   ├── patient00001.dcm       # 脱敏后的DICOM
    │   ├── patient00002.dcm
    │   └── patient00826.dcm
    │
    └── protected_text/             # 保护后的文本数据
        ├── patient00001.json      # 加密的CSV数据
        ├── patient00002.json
        ├── patient00826.json
        ├── audit_manifest.json    # 审计清单
        ├── audit_manifest.sig     # SPHINCS+数字签名（可选）
        └── audit_manifest.pk      # 签名验证公钥（可选）
```

### 1️⃣ 保护后的DICOM文件 (`.dcm`)

**文件名格式**：`{patient_id}.dcm`（如 `patient00826.dcm`）

**内容**：
- ✅ **原始像素数据保留**（影像内容）
- ✅ **元数据加密/脱敏**：
  - PatientID → FPE加密
  - PatientName → FPE加密
  - PatientAge → FPE加密
  - PatientSex → FPE加密
  - 其他敏感字段 → AEAD加密
- ✅ **私有标签**：存储加密元数据
  - `(0x0011,0x0010)`: "PROTECT-META"
  - `(0x0011,0x1010)`: 加密字段JSON

**加密方法**：
- **FPE (Format-Preserving Encryption)**：保持原格式
  - 基于 Ascon-PRF
  - 字母数字保持可读性
- **AEAD (Authenticated Encryption)**：
  - 基于 Ascon AEAD
  - 提供认证和加密

**示例**：
```
原始：PatientID = "patient00826"
加密后：PatientID = "QB7RN37E8V2G6"
```

---

### 2️⃣ 保护后的文本JSON (`.json`)

**文件名格式**：`{patient_id}.json`（如 `patient00826.json`）

**JSON结构**：
```json
{
  "dicom_out": "output/.../patient00826.dcm",
  "sop": "1.2.840.113619.2.55.3...",
  "assoc": "batch_1761149193606",
  "columns": {
    "patient_id": "QB7RN37E8V2G6",
    "patient_sex": "N",
    "patient_age": "67"
  },
  "columns_cipher": {
    "patient_id": {
      "token": "QB7RN37E8V2G6",
      "cipher_b64": "FALLBACK-AbCd...==",
      "hash": "a1b2c3d4...",
      "ad": "{\"tag\":\"patient_id\",\"sop\":\"...\",\"ctx\":\"...\"}",
      "nonce": "1234567890abcdef"
    }
  }
}
```

**字段说明**：
- `dicom_out`: 对应的DICOM文件路径
- `sop`: DICOM的SOP Instance UID
- `assoc`: 批次ID（关联键）
- `columns`: FPE加密后的字段（保持格式）
- `columns_cipher`: AEAD加密的密文和元数据

---

### 3️⃣ 审计清单 (`audit_manifest.json`)

**每个批次一个文件**

**JSON结构**：
```json
{
  "assoc": "batch_1761149193606",
  "key_hint": "a1b2c3d4e5f67890",
  "count": 1222,
  "created_ms": 1761149193619,
  "items": [
    {
      "dicom": {
        "dicom_in": "uploads/xxx.dcm",
        "dicom_out": "output/.../patient00001.dcm",
        "sop": "1.2.840...",
        "sha256_before": "abc123...",
        "sha256_after": "def456...",
        "fields": [...]
      },
      "text": {
        "path": "output/.../patient00001.json"
      }
    }
  ]
}
```

**用途**：
- ✅ 记录批次所有文件
- ✅ 保存加密前后哈希
- ✅ 审计追踪
- ✅ 可验证性

---

### 4️⃣ 数字签名 (`.sig` + `.pk`)

**仅当SPHINCS+可用时生成**

**文件**：
- `audit_manifest.sig`: SPHINCS+签名（二进制）
- `audit_manifest.pk`: 验证公钥（二进制）

**用途**：
- ✅ 防篡改
- ✅ 审计清单完整性验证
- ✅ 抗量子攻击（SPHINCS+是后量子签名算法）

---

## 🗄️ 第2层：存储层（CAS + 索引）

### 📁 目录结构

```
storage_repo/
├── cas/                           # 内容寻址存储
│   ├── ab/                        # SHA256前2位
│   │   ├── c123def...             # DICOM文件（无扩展名）
│   │   └── d456abc...             # JSON文件（无扩展名）
│   └── cd/
│       └── ef789...
│
├── batches/                       # 批次审计材料
│   ├── batch_1761149193606/
│   │   ├── audit_manifest.json
│   │   ├── audit_manifest.sig
│   │   └── audit_manifest.pk
│   └── batch_1761145851536/
│       └── audit_manifest.json
│
└── db/                            # SQLite
    └── index.sqlite
```

---

### 1️⃣ CAS (Content-Addressable Storage)

**概念**：基于文件内容的SHA256哈希存储

**存储路径规则**：
```python
SHA256 = "abc123def456..."
路径 = storage_repo/cas/ab/c123def456...
                        ↑  ↑
                    前2位 剩余部分
```

**特点**：
- ✅ **去重**：相同内容只存储一次
- ✅ **完整性**：文件名=内容哈希，无法篡改
- ✅ **可验证**：重新计算SHA256即可验证
- ✅ **无扩展名**：通过数据库索引识别类型

**示例**：
```
原文件: patient00826.dcm
SHA256: abc123def456789...
CAS路径: storage_repo/cas/ab/c123def456789...
```

---

### 2️⃣ SQLite索引数据库 (`index.sqlite`)

**数据库表结构**：

#### `objects` 表（对象索引）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER | 主键 |
| `sop_uid` | TEXT | DICOM SOP UID |
| `patient_id` | TEXT | 患者ID（加密后）|
| `dicom_sha256` | TEXT | DICOM文件SHA256 |
| `text_sha256` | TEXT | JSON文件SHA256 |
| `masked_pixels` | INTEGER | 掩码像素数 |
| `batch_id` | TEXT | 批次ID |
| `ts_ms` | INTEGER | 时间戳（毫秒）|
| `dicom_cas` | TEXT | CAS中的DICOM哈希 |
| `text_cas` | TEXT | CAS中的JSON哈希 |

**SQL创建语句**：
```sql
CREATE TABLE objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sop_uid TEXT,
    patient_id TEXT,
    dicom_sha256 TEXT,
    text_sha256 TEXT,
    masked_pixels INTEGER,
    batch_id TEXT,
    ts_ms INTEGER,
    dicom_cas TEXT,
    text_cas TEXT
);
CREATE INDEX idx_sop ON objects(sop_uid);
CREATE INDEX idx_patient ON objects(patient_id);
CREATE INDEX idx_batch ON objects(batch_id);
```

#### `batches` 表（批次索引）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT | 批次ID（主键）|
| `audit_sha256` | TEXT | 审计清单SHA256 |
| `sig_sha256` | TEXT | 签名文件SHA256 |
| `pk_sha256` | TEXT | 公钥文件SHA256 |
| `count` | INTEGER | 对象数量 |
| `ts_ms` | INTEGER | 时间戳（毫秒）|

**用途**：
- ✅ 快速查找患者数据
- ✅ 批次管理
- ✅ 审计追踪
- ✅ 文件完整性验证

---

### 3️⃣ 批次审计材料

**存储位置**：`storage_repo/batches/{batch_id}/`

**文件**：
- `audit_manifest.json`: 审计清单副本
- `audit_manifest.sig`: 签名副本（如果有）
- `audit_manifest.pk`: 公钥副本（如果有）

**用途**：
- ✅ 长期保存审计记录
- ✅ 签名验证
- ✅ 合规审计

---

## 📦 第3层：应用层（验证包）

### 验证包结构 (`.zip`)

**生成位置**：`output/bundles/{patient_id}_bundle.zip`

**ZIP内容**：
```
patient00826_bundle.zip
├── patient00826.dcm              # 保护后的DICOM
├── patient00826.json             # 保护后的JSON
├── audit_manifest.json           # 审计清单
├── audit_manifest.sig            # 签名（如果有）
└── audit_manifest.pk             # 公钥（如果有）
```

**用途**：
- ✅ 完整的可验证数据包
- ✅ 可独立下载和验证
- ✅ 包含所有审计材料
- ✅ 方便数据交换

---

## 🔄 完整存储流程

### 流程图

```
原始数据 (CSV + DICOM)
         ↓
    [检测PHI]
         ↓
    [执行保护]
         ↓
保护后文件 (output/batch_*/protected_*)
  ├─ patient00826.dcm (加密的DICOM)
  ├─ patient00826.json (加密的JSON)
  └─ audit_manifest.json (审计清单)
         ↓
    [存储入库]
         ↓
    ┌───────────────┐
    │  CAS存储      │
    │  (去重存储)   │
    └───────────────┘
         ↓
    ┌───────────────┐
    │  SQLite索引   │
    │  (快速查询)   │
    └───────────────┘
         ↓
    ┌───────────────┐
    │  批次审计     │
    │  (合规记录)   │
    └───────────────┘
```

### 详细步骤

1. **保护阶段** (`/api/protect_execute`)
   ```
   - 读取检测结果
   - 对DICOM元数据加密（FPE/AEAD）
   - 对CSV数据加密
   - 生成审计清单
   - 生成数字签名（可选）
   - 保存到 output/batch_*/
   ```

2. **入库阶段** (`/api/storage/ingest`)
   ```
   - 计算文件SHA256
   - 存入CAS（去重）
   - 插入SQLite索引
   - 复制审计材料
   - 提交事务
   ```

3. **查询阶段** (`/api/storage/list`)
   ```
   - 查询SQLite数据库
   - 返回对象列表
   - 显示patient_id、批次、哈希等
   ```

4. **导出阶段** (`/api/storage/bundle`)
   ```
   - 根据patient_id查询
   - 从CAS读取文件
   - 打包成ZIP
   - 包含审计材料
   ```

---

## 🔒 安全特性

### 加密算法

| 算法 | 用途 | 特点 |
|------|------|------|
| **Ascon-PRF** | 伪随机函数 | 轻量级、高效 |
| **FPE (Format-Preserving)** | 格式保留加密 | 保持数据格式 |
| **Ascon-AEAD** | 认证加密 | 加密+完整性 |
| **SPHINCS+** | 后量子签名 | 抗量子攻击 |

### 关联键机制

**目的**：跨模态关联识别

**实现**：
```python
# 相同的patient_id使用相同的nonce
nonce = hashlib.sha256(f"{patient_id}|{batch_id}".encode()).digest()[:16]

# 确保相同patient_id的加密token一致
token = fpe_encrypt(patient_id, nonce, key)
```

**效果**：
- ✅ 同一患者的CSV和DICOM可匹配
- ✅ 不同患者无法关联
- ✅ 支持跨模态风险评估

---

## 📊 存储统计

### 查看存储状态

**运行**：
```bash
python debug_database.py
```

**输出示例**：
```
【objects表】
总记录数: 1222

【batches表】
总记录数: 2

【CAS存储】
CAS文件总数: 2444  (1222 DICOM + 1222 JSON)

【批次目录】
批次目录数量: 2
```

### API查询

**列出对象**：
```
GET /api/storage/list?limit=20&offset=0
```

**列出批次**：
```
GET /api/storage/batches?limit=20
```

**获取统计**：
```
GET /api/storage/stats
```

---

## 🔍 文件验证

### 验证CAS文件完整性

```python
# 重新计算SHA256
sha256 = hashlib.sha256(file_content).hexdigest()

# 与文件名比对
assert sha256 == cas_filename
```

### 验证审计清单签名

```python
# 读取公钥和签名
pk = Path("audit_manifest.pk").read_bytes()
sig = Path("audit_manifest.sig").read_bytes()
msg = Path("audit_manifest.json").read_bytes()

# 验证签名（SPHINCS+）
assert sphincs.verify(pk, msg, sig)
```

---

## 📝 总结

### 最终存储的文件形式

1. **加密的DICOM文件** (`.dcm`)
   - 元数据FPE/AEAD加密
   - 像素数据保留
   - 存储在CAS中

2. **加密的JSON文件** (`.json`)
   - CSV数据加密
   - 包含密文和元数据
   - 存储在CAS中

3. **审计清单** (`.json`)
   - 批次所有文件记录
   - SHA256哈希
   - 可选数字签名

4. **SQLite数据库** (`.sqlite`)
   - 对象索引
   - 批次索引
   - 快速查询

5. **验证包** (`.zip`)
   - 完整的可验证数据包
   - 包含审计材料

### 核心特点

✅ **去重存储**（CAS）  
✅ **内容寻址**（SHA256）  
✅ **完整性验证**（哈希+签名）  
✅ **快速查询**（SQLite索引）  
✅ **审计追踪**（清单+签名）  
✅ **抗量子攻击**（SPHINCS+）  
✅ **可验证性**（独立验证包）

---

**文档版本**: v1.0  
**最后更新**: 2025-10-23  
**相关文件**: `services/protection_service.py`, `services/storage_audit_service.py`


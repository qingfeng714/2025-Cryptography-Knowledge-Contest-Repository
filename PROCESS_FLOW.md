# 📊 完整流程详解：从检测到加密

## 🔍 核心问题解答

### Q1: 加密逻辑是什么？
**A: 所有检测到的敏感信息都加密，不区分是否有跨模态关联**

### Q2: 跨模态映射的作用？
**A: 用于风险评估、审计追踪，而非决定是否加密**

---

## 📈 数据流程图

```
┌─────────────────────────────────────────────────────────┐
│  输入数据                                                │
├─────────────────────────────────────────────────────────┤
│  CSV: patient00001, 张三, Male, 35, 138xxx, 110101xxx  │
│  CSV: patient00002, 李四, Female, 28, 139xxx, 310101xxx│
│  CSV: patient00999, 王五, Male, 42, 158xxx, 440101xxx  │
│                                                          │
│  DICOM: patient00001.dcm (PatientID=patient00001)       │
│  DICOM: patient00002.dcm (PatientID=patient00002)       │
│  （注意：patient00999 无对应DICOM）                     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  阶段1: 跨模态检测（感知层）                             │
│  API: /api/batch_detect                                 │
└─────────────────────────────────────────────────────────┘
                        ↓
        ┌───────────────┴───────────────┐
        ↓                               ↓
┌──────────────────┐          ┌──────────────────┐
│ 1.1 CSV实体提取  │          │ 1.2 DICOM元数据   │
├──────────────────┤          ├──────────────────┤
│ 所有行，所有列   │          │ 提取Header字段    │
│                  │          │                  │
│ Row 0:           │          │ patient00001.dcm:│
│  - PATH          │          │  - PatientID     │
│  - NAME (张三)   │          │  - Sex           │
│  - SEX (Male)    │          │  - Age           │
│  - AGE (35)      │          │                  │
│  - PHONE         │          │ patient00002.dcm:│
│  - ID_NUMBER     │          │  - PatientID     │
│  - ADDRESS       │          │  - Sex           │
│                  │          │  - Age           │
│ Row 1:           │          │                  │
│  - ... (李四)    │          │ （patient00999   │
│                  │          │   无DICOM）      │
│ Row 2:           │          │                  │
│  - ... (王五)    │          │                  │
└──────────────────┘          └──────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  1.3 跨模态匹配                                          │
├─────────────────────────────────────────────────────────┤
│  ✅ patient00001 (CSV) ↔ patient00001 (DICOM)          │
│     → match_type: patient_id_exact_match                │
│     → confidence: 1.0                                   │
│     → risk_level: critical  🔴                          │
│                                                          │
│  ✅ patient00002 (CSV) ↔ patient00002 (DICOM)          │
│     → match_type: patient_id_exact_match                │
│     → confidence: 1.0                                   │
│     → risk_level: critical  🔴                          │
│                                                          │
│  ❌ patient00999 (CSV) ↔ 无DICOM                        │
│     → matched: false                                    │
│     → risk_level: N/A  ⚪                               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  输出: detection_result                                  │
├─────────────────────────────────────────────────────────┤
│  {                                                       │
│    "results": [                                         │
│      {                                                   │
│        "patient_id": "patient00001",                    │
│        "matched": true,  ← 有跨模态关联                 │
│        "csv_data": {姓名、性别、年龄...},               │
│        "dicom_metadata": {PatientID, Sex, Age...},      │
│        "risk_level": "critical"  ← 标记风险级别        │
│      },                                                  │
│      {                                                   │
│        "patient_id": "patient00002",                    │
│        "matched": true,                                 │
│        ...                                               │
│      },                                                  │
│      {                                                   │
│        "patient_id": "patient00999",                    │
│        "matched": false,  ← 无跨模态关联                │
│        "csv_data": {姓名、性别、年龄...}                │
│        （无dicom_metadata）                             │
│      }                                                   │
│    ],                                                    │
│    "matched": 2,                                        │
│    "unmatched": 1                                       │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  阶段2: 数据保护（保护层）                               │
│  API: /api/protect_execute                              │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  2.1 当前实现：全量加密策略                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ✅ patient00001 (matched=true, risk=critical)          │
│     ├── DICOM加密 ✓                                     │
│     │   ├── PatientID → TOKEN_ABC123 (FPE)             │
│     │   ├── StudyDate → 20241021 (FPE digits)          │
│     │   └── AccessionNumber → TOKENXYZ (FPE)           │
│     └── CSV加密 ✓                                       │
│         ├── patient_id → cipher_b64 (Ascon AEAD)       │
│         ├── Name → cipher_b64 (Ascon AEAD)             │
│         ├── Sex → cipher_b64 (Ascon AEAD)              │
│         ├── Age → cipher_b64 (Ascon AEAD)              │
│         └── ... (所有敏感字段)                          │
│                                                          │
│  ✅ patient00002 (matched=true, risk=critical)          │
│     ├── DICOM加密 ✓ (同上)                              │
│     └── CSV加密 ✓ (同上)                                │
│                                                          │
│  ✅ patient00999 (matched=false, 无DICOM)               │
│     ├── DICOM加密 ✗ (无DICOM文件)                       │
│     └── CSV加密 ✓                                       │
│         ├── patient_id → cipher_b64 (Ascon AEAD)       │
│         ├── Name → cipher_b64 (Ascon AEAD)             │
│         └── ... (仍然加密所有敏感字段)  ⚠️              │
│                                                          │
│  ⚠️ 注意：即使没有跨模态匹配，CSV中的PHI仍然被加密      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  输出: 保护后的数据                                      │
├─────────────────────────────────────────────────────────┤
│  protected_dicom/                                        │
│    ├── patient00001.dcm  ← DICOM header已被FPE token化  │
│    └── patient00002.dcm                                 │
│                                                          │
│  protected_text/                                         │
│    ├── patient00001.json  ← 包含cipher_b64密文          │
│    ├── patient00002.json                                │
│    ├── patient00999.json  ← 虽无DICOM，仍然加密         │
│    ├── audit_manifest.json                              │
│    ├── audit_manifest.sig  (SPHINCS+签名)               │
│    └── audit_manifest.pk   (公钥)                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🆚 对比：三种可能的策略

### 策略A: 全量加密（当前实现）✅

```
所有数据 → 检测 → 全部加密

优点：
  ✅ 最安全
  ✅ 简单
  ✅ 合规

缺点：
  ⚠️ 无差异化
  ⚠️ 性能开销大
```

### 策略B: 选择性加密（基于关联）

```
有跨模态关联 → 强加密
无跨模态关联 → 保持明文或轻度保护

优点：
  ✅ 节省资源
  ✅ 提高可用性

缺点：
  ⚠️ 明文数据仍有风险
  ⚠️ 可能不合规
```

### 策略C: 分级保护（推荐改进）🌟

```
critical (有关联)  → Ascon AEAD + SPHINCS+ + 严格ACL
high (单源敏感)    → Ascon AEAD + 审计
medium (准标识符)  → FPE + k-匿名化
low (非敏感)       → 标记或保留

优点：
  ✅ 平衡安全和可用性
  ✅ 灵活可配置
  ✅ 性能优化

缺点：
  ⚠️ 实现复杂
  ⚠️ 需要策略引擎
```

---

## 🔄 数据示例

### 输入数据
```csv
Path,Name,Sex,Age,Phone,ID_Number
.../patient00001/...,张三,Male,35,13812345678,110101198901011234
.../patient00999/...,王五,Male,42,15812345678,440101198001013456
```

### 检测结果
```json
{
  "results": [
    {
      "patient_id": "patient00001",
      "matched": true,           ← 有DICOM匹配
      "risk_level": "critical",  ← 高风险
      "csv_data": {"Name": "张三", "Age": "35", ...}
    },
    {
      "patient_id": "patient00999",
      "matched": false,          ← 无DICOM匹配
      "csv_data": {"Name": "王五", "Age": "42", ...}
    }
  ]
}
```

### 加密结果（当前实现）
```json
// patient00001.json (有跨模态关联)
{
  "columns": {
    "Name": "ZHANGSAN",        // FPE token
    "Age": "35"                 // FPE token
  },
  "columns_cipher": {
    "Name": {
      "cipher_b64": "...",      // Ascon AEAD密文
      "hash": "sha256(张三)"
    },
    "Age": { ... }
  }
}

// patient00999.json (无跨模态关联，但仍加密！)
{
  "columns": {
    "Name": "WANGWU",          // ✅ 仍然加密
    "Age": "42"                 // ✅ 仍然加密
  },
  "columns_cipher": {
    "Name": {
      "cipher_b64": "...",      // ✅ 仍然有密文
      "hash": "sha256(王五)"
    },
    "Age": { ... }
  }
}
```

---

## 💡 设计理念

### 为什么全量加密？

#### 1️⃣ **单源PHI本身就是敏感信息**

```
CSV中的 "张三" → 即使没有DICOM，单独泄露也是隐私风险
CSV中的 "138xxx" → 手机号本身就需要保护
```

#### 2️⃣ **跨模态关联增加风险，而非创造风险**

```
风险级别：

单源PHI（无关联）: 
  - 姓名 = 高风险 (HIGH)
  - 电话 = 高风险 (HIGH)
  - 年龄 = 中风险 (MEDIUM)

跨模态关联（有关联）:
  - 姓名 + DICOM = 极高风险 (CRITICAL) ⬆️
  - 年龄 + DICOM = 高风险 (HIGH) ⬆️
```

#### 3️⃣ **合规要求**

HIPAA Safe Harbor标准要求删除/加密18类PHI：
```
1. 姓名             ✅ 必须加密
2. 地址             ✅ 必须加密
3. 电话/传真        ✅ 必须加密
4. 电子邮件地址     ✅ 必须加密
5. 社保号           ✅ 必须加密
6. 病历号           ✅ 必须加密
7. 保险号           ✅ 必须加密
8. 车牌号           ✅ 必须加密
9. 设备序列号       ✅ 必须加密
10. URL             ✅ 必须加密
11. IP地址          ✅ 必须加密
12. 指纹/声纹       ✅ 必须加密
13. 照片            ✅ 必须加密
14. 其他唯一标识    ✅ 必须加密
15-18. 日期相关     ✅ 必须加密（除年份）

⚠️ 不区分是否有关联，都必须保护
```

---

## 🎯 跨模态映射的真正作用

虽然不决定"是否加密"，但决定：

### 1️⃣ **风险级别标记**

```python
# 用于审计和监控
if matched:
    risk_level = 'critical'  # 需要额外关注
    audit_flag = 'HIGH_PRIORITY'
else:
    risk_level = 'high'      # 标准关注
    audit_flag = 'NORMAL'
```

### 2️⃣ **访问控制策略**（未来实现）

```python
# 未来可能的实现
def authorize_decrypt(user, patient_id):
    obj = get_object(patient_id)
    
    if obj.has_cross_modal_match:
        # 有跨模态关联 → 需要更高权限
        required_level = 'ADMIN'
        require_two_factor = True
    else:
        # 无跨模态关联 → 标准权限
        required_level = 'USER'
        require_two_factor = False
    
    if user.level >= required_level:
        return decrypt(obj)
    else:
        raise PermissionDenied()
```

### 3️⃣ **审计重点**

```python
# audit_manifest.json
{
  "items": [
    {
      "patient_id": "patient00001",
      "cross_modal_match": true,     ← 标记关联
      "risk_level": "critical",       ← 重点审计
      "audit_frequency": "daily"      ← 每日审计
    },
    {
      "patient_id": "patient00999",
      "cross_modal_match": false,    ← 无关联
      "risk_level": "high",          ← 常规审计
      "audit_frequency": "weekly"    ← 每周审计
    }
  ]
}
```

---

## 📋 完整示例：三个患者的处理

### 示例数据

| Patient ID | CSV数据 | DICOM | 跨模态匹配 | 加密状态 |
|-----------|---------|-------|----------|---------|
| patient00001 | ✅ | ✅ | ✅ YES | ✅ **全部加密** |
| patient00002 | ✅ | ✅ | ✅ YES | ✅ **全部加密** |
| patient00999 | ✅ | ❌ | ❌ NO | ✅ **仍然加密** |

### 处理流程

```
patient00001:
  检测 → 发现CSV实体 ✓
       → 发现DICOM元数据 ✓
       → 跨模态匹配成功 ✓ (risk=critical)
  保护 → DICOM加密 ✓
       → CSV加密 ✓
       → 生成audit_manifest ✓
  标记 → 高风险标记 ⚠️

patient00002:
  检测 → 发现CSV实体 ✓
       → 发现DICOM元数据 ✓
       → 跨模态匹配成功 ✓ (risk=critical)
  保护 → DICOM加密 ✓
       → CSV加密 ✓
  标记 → 高风险标记 ⚠️

patient00999:
  检测 → 发现CSV实体 ✓
       → 无DICOM ✗
       → 跨模态匹配失败 ✗
  保护 → DICOM加密 ✗ (无文件)
       → CSV加密 ✓ ← ⚠️ 关键：仍然加密！
  标记 → 标准风险标记
```

---

## 🔐 加密内容详解

### 问题：只加密关联键，还是所有敏感信息？

**答案：✅ 加密所有敏感信息**

### 详细对比

#### 方案A: 仅加密关联键 ❌ 不推荐

```python
# 仅加密用于跨模态匹配的字段
encrypt_fields = ['patient_id']  # 只加密ID

# 其他字段保持明文
keep_plaintext = ['Name', 'Sex', 'Age', 'Phone', 'ID_Number']
```

**问题**:
- ⚠️ 姓名、电话等明文泄露仍是隐私风险
- ⚠️ 不符合HIPAA等法规要求
- ⚠️ 通过其他字段仍可能重识别

#### 方案B: 加密所有敏感信息 ✅ 当前实现

```python
# 加密所有PHI字段
encrypt_fields = [
    'patient_id',     # 关联键
    'Name',           # 直接标识符
    'Sex',            # 准标识符
    'Age',            # 准标识符
    'Phone',          # 直接标识符
    'ID_Number',      # 直接标识符
    'Address'         # 准标识符
]

# 每个字段都生成
{
    "token": "FPE_TOKEN",        # 格式保留token
    "cipher_b64": "...",         # 完整密文
    "hash": "sha256(...)",       # 原文哈希（用于搜索）
    "ad": "{...}",               # 关联数据（防篡改）
    "nonce": "..."               # 随机数
}
```

**优点**:
- ✅ 全面保护
- ✅ 合规要求
- ✅ 防止通过组合字段重识别

---

## 📊 加密范围可视化

### CSV数据加密范围

```
原始CSV行:
┌────────────┬──────┬──────┬─────┬────────────┬─────────────┬──────────┐
│ Path       │ Name │ Sex  │ Age │ Phone      │ ID_Number   │ Address  │
├────────────┼──────┼──────┼─────┼────────────┼─────────────┼──────────┤
│ patient... │ 张三 │ Male │ 35  │ 138xxx     │ 110101xxx   │ 北京...  │
└────────────┴──────┴──────┴─────┴────────────┴─────────────┴──────────┘
      ↓          ↓      ↓      ↓        ↓            ↓           ↓
    关联键    直接ID  准ID   准ID    直接ID       直接ID       准ID
      ↓          ↓      ↓      ↓        ↓            ↓           ↓
   ✅加密    ✅加密  ✅加密  ✅加密   ✅加密       ✅加密       ✅加密

加密后:
┌────────────┬──────────┬──────┬─────┬────────────┬─────────────┬──────────┐
│ Path       │ Name     │ Sex  │ Age │ Phone      │ ID_Number   │ Address  │
├────────────┼──────────┼──────┼─────┼────────────┼─────────────┼──────────┤
│ (保留)     │ TOKEN1   │ M    │ 35  │ TOKEN2     │ TOKEN3      │ TOKEN4   │
│            │ +cipher  │+cipher│+cipher│ +cipher  │ +cipher     │ +cipher  │
└────────────┴──────────┴──────┴─────┴────────────┴─────────────┴──────────┘
```

### DICOM数据加密范围

```
原始DICOM Header:
┌─────────────────┬───────────────────┬───────────┬──────────┐
│ PatientID       │ AccessionNumber   │ StudyDate │ InstName │
├─────────────────┼───────────────────┼───────────┼──────────┤
│ patient00001    │ ACC123456         │ 20241021  │ Hospital │
└─────────────────┴───────────────────┴───────────┴──────────┘
         ↓                  ↓               ↓           ↓
       关联键           准标识符        准标识符    准标识符
         ↓                  ↓               ↓           ↓
      ✅加密            ✅加密          ✅加密       ✅加密

加密后:
┌─────────────────┬───────────────────┬───────────┬──────────┐
│ PatientID       │ AccessionNumber   │ StudyDate │ InstName │
├─────────────────┼───────────────────┼───────────┼──────────┤
│ PATIENT00001    │ ACC123ABC         │ 20241022  │ HOSPITAL │
│ (FPE token)     │ (FPE token)       │(FPE token)│(FPE token)│
└─────────────────┴───────────────────┴───────────┴──────────┘

私有标签 (0011,1010):
{
  "fields": [
    {"name": "PatientID", "cipher_b64": "...", "hash": "...", ...},
    {"name": "AccessionNumber", "cipher_b64": "...", ...},
    ...
  ]
}
```

---

## 🎓 理解要点

### ✅ 正确理解

1. **跨模态映射** ≠ 加密决策条件
2. **跨模态映射** = 风险评估 + 审计重点
3. **所有PHI** = 都需要保护（不管是否关联）
4. **加密范围** = 所有敏感字段（不仅是关联键）

### ❌ 常见误解

1. ❌ "只有匹配的数据才加密"
2. ❌ "无匹配的数据保持明文"
3. ❌ "只加密patient_id关联键"
4. ❌ "其他字段不重要"

---

## 🔧 如果需要差异化策略

如果您希望实现"有关联强加密，无关联弱保护"，可以修改：

```python
# services/protection_service.py

def protect_batch_differential(self, detection_result, ...):
    """差异化保护策略"""
    
    for item in detection_result['results']:
        matched = item.get('matched', False)
        risk_level = item.get('risk_level', 'medium')
        
        if matched and risk_level == 'critical':
            # 策略1: 强保护（有跨模态关联）
            self._protect_critical(item)
            # - Ascon AEAD全字段加密
            # - SPHINCS+签名
            # - 双重审计
            
        elif matched:
            # 策略2: 标准保护（有关联但风险中等）
            self._protect_standard(item)
            # - Ascon AEAD关键字段加密
            # - FPE其他字段
            
        else:
            # 策略3: 轻度保护（无关联）
            self._protect_light(item)
            # - 仅FPE token
            # - 或k-匿名化
            # - 或保留明文但标记
```

---

## 📚 总结

### 当前加密策略（v2.0.0）

```
输入: 所有检测到的敏感数据
  ↓
判断: 是否是PHI？
  ├─ 是 → ✅ 加密（不管是否有跨模态关联）
  └─ 否 → 保留明文
  ↓
输出: 加密数据 + 审计清单
```

### 跨模态映射的作用

```
跨模态检测
  ↓
生成mappings列表
  ↓
用途：
  ✅ 风险评估（critical/high/medium/low）
  ✅ 审计追踪（重点关注有关联的数据）
  ✅ 未来差异化保护的依据
  ❌ 不决定是否加密（所有PHI都加密）
```

---

**关键结论**:

1. ✅ **所有PHI都加密**（不管是否有跨模态关联）
2. ✅ **加密所有敏感字段**（不仅是关联键）
3. ✅ **跨模态映射用于风险分级**，不是加密开关
4. ⚠️ **无关联的数据也加密**，因为单独泄露也是风险

这是一个**安全优先、合规导向**的设计！🔒

---

**文档版本**: v2.0.0  
**最后更新**: 2025-10-21

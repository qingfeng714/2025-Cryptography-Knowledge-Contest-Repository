# 🔐 加密策略与跨模态关联分析

## 📋 核心问题

1. **跨模态对齐到加密的思路是什么？**
2. **是存在映射关系才加密吗？**
3. **不存在映射关系的数据保持明文吗？**
4. **加密的信息范围是什么？**

---

## 🎯 当前实现逻辑

### 阶段1: 跨模态检测（感知层）

```python
# services/crossmodal_service.py

def process_csv_detection(csv_path, dicom_path):
    """
    步骤1: 检测CSV中的敏感实体
    """
    entities = []
    for col in ['Path', 'Name', 'Sex', 'Age', 'Phone', 'ID_Number', 'Address']:
        # 提取所有敏感字段
        entities.append({
            'type': col_type,
            'text': value,
            'row_index': row_num,
            'column': col_name
        })
    
    """
    步骤2: 检测DICOM元数据
    """
    dicom_metadata = {
        'patient_id': ...,
        'patient_name': ...,
        'patient_sex': ...,
        'patient_age': ...
    }
    
    """
    步骤3: 跨模态匹配
    """
    mappings = []
    for entity in entities:
        if entity['column'] == 'Path':
            # 提取patient_id进行匹配
            if csv_patient_id == dicom_patient_id:
                mappings.append({
                    'match_type': 'patient_id_exact_match',
                    'confidence': 1.0,
                    'risk_level': 'critical'  # ⚠️ 高风险
                })
```

**输出**:
```json
{
    "text_entities": [所有检测到的敏感实体],
    "mappings": [存在跨模态关联的实体],
    "metrics": {风险评估指标}
}
```

---

### 阶段2: 数据保护（保护层）

#### 当前实现：**全量加密策略**

```python
# services/protection_service.py

def protect_batch(detection_result, output_dir, batch_id):
    """
    当前策略：对所有检测到的敏感信息进行加密
    不区分是否存在跨模态关联
    """
    
    results = detection_result.get('results', [])
    
    for item in results:
        # ✅ 加密DICOM（不管是否匹配）
        if dicom_file.exists():
            protect_dicom(dicom_path, ...)
        
        # ✅ 加密CSV数据（不管是否匹配）
        csv_data = item.get('csv_data', {})
        phi_cols = ['patient_id', 'patient_sex', 'patient_age']
        protect_text_data(csv_data, phi_cols, ...)
```

#### 实际加密内容

**DICOM加密**:
```python
# 加密的字段（不管是否有跨模态匹配）
SENSITIVE_TAGS = [
    ("PatientID",        (0x0010,0x0020), "alnum"),   # ✅ 加密
    ("AccessionNumber",  (0x0008,0x0050), "alnum"),   # ✅ 加密
    ("StudyDate",        (0x0008,0x0020), "digits"),  # ✅ 加密
    ("InstitutionName",  (0x0008,0x0080), "alnum"),   # ✅ 加密
]

# 加密后替换为token
ds.PatientID = "TOKEN_ABC123"  # FPE加密后的token
```

**CSV文本加密**:
```python
# 加密的列（不管是否有跨模态匹配）
phi_cols = ['patient_id', 'patient_sex', 'patient_age']

# 每个字段都生成
{
    "token": "TOKEN_...",        # FPE token（保留格式）
    "cipher_b64": "...",         # Ascon AEAD密文
    "hash": "sha256...",         # 原文哈希
    "ad": "{...}",               # 关联数据
    "nonce": "..."               # 随机数
}
```

---

## 🤔 问题分析

### 问题1: 是存在映射关系才加密吗？

**当前答案**: ❌ **否**

**当前实现**:
- 所有检测到的敏感信息**都会被加密**
- 不管是否存在跨模态映射关系

**原因**:
1. **安全优先**: 即使没有跨模态关联，CSV和DICOM中的PHI本身就是敏感信息
2. **简化实现**: 统一的加密策略，避免复杂的条件判断
3. **合规要求**: HIPAA等法规要求加密所有PHI，不区分关联性

**示例**:
```
CSV Row 1: patient00001 (有对应的DICOM) → ✅ 加密
CSV Row 2: patient00999 (无对应的DICOM) → ✅ 也加密
```

---

### 问题2: 不存在映射关系的就保持明文吗？

**当前答案**: ❌ **否，也会加密**

**当前实现**:
```python
for item in detection_result['results']:
    if item.get('matched'):
        # 有跨模态匹配 → 加密
        protect_data(...)
    else:
        # 无跨模态匹配 → 仍然加密（当前实现）
        # 理论上可以选择不加密或轻度保护
```

**改进建议**（见后文）:
- 存在映射关系 → **强加密**（Ascon AEAD + SPHINCS+签名）
- 不存在映射关系 → **可选策略**:
  - 选项A: 轻度加密（仅FPE token）
  - 选项B: 脱敏（Masking，如`张**`）
  - 选项C: 保留明文但标记（审计）

---

### 问题3: 加密的信息范围

**当前答案**: **所有敏感信息，不仅仅是关联键**

#### 加密范围对比

| 数据类型 | 关联键 | 其他敏感信息 | 当前是否加密 |
|---------|--------|------------|------------|
| **DICOM** | PatientID | AccessionNumber, StudyDate, InstitutionName | ✅ 全部加密 |
| **CSV** | patient_id (Path列) | Name, Sex, Age, Phone, ID_Number, Address | ✅ 全部加密 |

#### 具体示例

**CSV原始数据**:
```csv
Path,Name,Sex,Age,Phone,ID_Number,Address
.../patient00001/...,张三,Male,35,13812345678,110101198901011234,北京市朝阳区建国路1号
```

**加密后**:
```json
{
  "columns": {
    "patient_id": "PATIENT00001",        // ← 关联键（FPE）
    "Name": "ZHANGSAN",                  // ← 其他敏感信息（FPE）
    "Sex": "M",                          // ← 其他敏感信息（FPE）
    "Age": "35",                         // ← 其他敏感信息（FPE）
    "Phone": "1381234567X",              // ← 其他敏感信息（FPE）
    "ID_Number": "11010119890101XXXX"   // ← 其他敏感信息（FPE）
  },
  "columns_cipher": {
    "patient_id": {
      "cipher_b64": "base64_encrypted",  // ← 完整密文
      "hash": "sha256...",
      ...
    },
    // 每个字段都有完整的密文
  }
}
```

**✅ 所有敏感字段都加密，包括**:
1. 关联键（patient_id）
2. 直接标识符（Name, ID_Number, Phone）
3. 准标识符（Sex, Age, Address）

---

## 🎨 设计思路详解

### 为什么采用全量加密？

#### 1. **隐私保护的层次**

```
Layer 1: 单数据源PHI保护
├── CSV中的姓名、电话、身份证
└── DICOM中的PatientID、StudyDate
     ↓ 即使单独泄露也是隐私风险
     ↓ 必须保护

Layer 2: 跨模态关联风险（更高风险）
├── CSV的patient00001 ↔ DICOM的patient00001
└── 可以关联同一个人的多种数据
     ↓ 重识别风险更高
     ↓ 需要额外标记和审计
```

#### 2. **合规要求（HIPAA）**

HIPAA要求保护18类PHI，包括：
- ✅ 姓名、地址、电话
- ✅ 身份证号
- ✅ 病历号（PatientID）
- ✅ 日期（StudyDate）

**无论是否有跨模态关联，这些都必须保护**

#### 3. **最小权限原则**

```
存储时 → 全部加密
使用时 → 按需解密（需要授权）
审计时 → 记录访问日志
```

---

## 🔄 跨模态映射的作用

虽然不影响"是否加密"，但跨模态映射在以下方面起作用：

### 1. **风险分级**

```python
# crossmodal_service.py
if csv_patient_id == dicom_patient_id:
    mapping = {
        'risk_level': 'critical',  # ⚠️ 最高风险
        'confidence': 1.0
    }
```

**用途**:
- 审计重点关注
- 访问控制更严格
- 解密需要更高权限

### 2. **审计追踪**

```json
// audit_manifest.json
{
  "items": [
    {
      "patient_id": "patient00001",
      "cross_modal_match": true,      // ✅ 标记有关联
      "risk_level": "critical",        // ⚠️ 高风险
      "match_type": "patient_id_exact_match"
    }
  ]
}
```

### 3. **未来的差异化保护**

虽然当前全量加密，但跨模态映射为差异化策略预留了接口：

```python
# 未来可能的实现
if mapping_exists and risk_level == 'critical':
    # 强加密 + 多重签名 + 访问控制
    encrypt_with_strong_policy(data)
else:
    # 标准加密
    encrypt_with_standard_policy(data)
```

---

## 💡 改进建议：差异化保护策略

### 策略1: 基于风险分级的保护

```python
class DifferentialProtectionService:
    """差异化保护服务"""
    
    def protect_batch(self, detection_result):
        for item in detection_result['results']:
            risk_level = self._assess_risk(item)
            
            if risk_level == 'critical':
                # 存在跨模态关联 → 强保护
                self._protect_critical(item)
            elif risk_level == 'high':
                # 单源高敏感 → 标准保护
                self._protect_high(item)
            elif risk_level == 'medium':
                # 准标识符 → 轻度保护
                self._protect_medium(item)
            else:
                # 低风险 → 选择性保护
                self._protect_low(item)
    
    def _protect_critical(self, item):
        """强保护：Ascon AEAD + SPHINCS+ + 双重审计"""
        # 加密所有字段
        # 生成签名
        # 记录详细审计日志
        # 设置严格访问控制
        pass
    
    def _protect_high(self, item):
        """标准保护：Ascon AEAD + 审计"""
        # 加密敏感字段
        # 记录审计日志
        pass
    
    def _protect_medium(self, item):
        """轻度保护：FPE或脱敏"""
        # 仅FPE token
        # 或k-匿名化
        pass
    
    def _protect_low(self, item):
        """选择性保护：标记或保留"""
        # 仅标记，不加密
        # 或完全保留明文
        pass
```

### 策略2: 基于数据用途的保护

```python
class PurposeBasedProtection:
    """基于用途的保护"""
    
    def protect_for_research(self, data):
        """科研用途：允许统计分析，但去标识化"""
        # 删除直接标识符
        # 保留准标识符（年龄、性别）
        # k-匿名化处理
        pass
    
    def protect_for_storage(self, data):
        """存储用途：完全加密"""
        # 所有PHI加密
        # 长期存储
        pass
    
    def protect_for_sharing(self, data):
        """共享用途：差异化隐私"""
        # 基于ε-差分隐私
        # 添加噪声
        pass
```

---

## 📊 当前vs建议实现对比

| 维度 | 当前实现 | 建议改进 |
|------|---------|---------|
| **加密决策** | 全量加密 | 基于风险分级 |
| **关联数据** | 同等处理 | 强化保护 |
| **非关联数据** | 同等处理 | 可选轻度保护 |
| **准标识符** | 全部加密 | 可选k-匿名化 |
| **访问控制** | 未实现 | 基于风险的ACL |
| **解密策略** | 未实现 | 分级授权解密 |

---

## 🔑 关键设计决策

### 当前设计的优点

✅ **简单直接**: 统一加密，逻辑清晰  
✅ **安全优先**: 过度保护好于保护不足  
✅ **合规友好**: 满足HIPAA等法规要求  
✅ **易于实现**: 无需复杂的策略引擎  

### 当前设计的局限

⚠️ **灵活性不足**: 无法针对不同场景调整  
⚠️ **性能开销**: 全量加密可能影响性能  
⚠️ **可用性**: 完全加密后难以进行统计分析  
⚠️ **成本**: 存储和计算成本较高  

---

## 🎯 总结回答

### Q1: 是存在映射关系才加密吗？

**A**: ❌ 否。**所有检测到的敏感信息都会加密**，不管是否存在跨模态映射。

### Q2: 不存在映射关系的就保持明文吗？

**A**: ❌ 否。**也会加密**。但在改进方案中，可以考虑差异化保护。

### Q3: 加密的信息范围？

**A**: ✅ **所有敏感信息**，包括：
- 关联键（patient_id）
- 直接标识符（Name, Phone, ID_Number）
- 准标识符（Sex, Age, Address）
- DICOM元数据（PatientID, StudyDate等）

### Q4: 跨模态映射的作用？

**A**: 主要用于：
- ✅ 风险评估和分级
- ✅ 审计追踪
- ✅ 未来差异化保护的依据
- ⚠️ **不决定是否加密**

---

## 💡 实现建议

如果需要差异化保护策略，可以修改 `protection_service.py`:

```python
def protect_batch(self, detection_result, output_dir, batch_id, strategy='full'):
    """
    strategy参数：
    - 'full': 全量加密（当前默认）
    - 'differential': 差异化保护（基于风险）
    - 'minimal': 最小化保护（仅关联数据）
    """
    if strategy == 'differential':
        return self._protect_differential(detection_result, ...)
    elif strategy == 'minimal':
        return self._protect_minimal(detection_result, ...)
    else:
        return self._protect_full(detection_result, ...)
```

---

**文档版本**: v2.0.0  
**最后更新**: 2025-10-21  
**作者**: 系统架构团队

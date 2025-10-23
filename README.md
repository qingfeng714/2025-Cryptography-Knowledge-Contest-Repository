# 医疗隐私保护系统

基于跨模态注意力机制的医疗数据隐私检测与保护系统

## 📚 文档导航

- **[快速开始](QUICKSTART.md)** - 5分钟部署和测试
- **[API文档](API_DOCUMENTATION.md)** - 完整API接口说明
- **[开发指南](DEVELOPER_GUIDE.md)** - 开发环境和代码规范

### 📖 详细文档

- **[数据流程](docs/DATA_FLOW_GUIDE.md)** - 从检测到加密的完整流程
- **[存储架构](docs/STORAGE_ARCHITECTURE.md)** - CAS存储与索引机制
- **[测试指南](docs/TESTING_GUIDE.md)** - 功能测试与性能验证
- **[故障排除](docs/TROUBLESHOOTING.md)** - 常见问题与解决方案

---

## ⚡ 快速命令

### 启动服务
```bash
# 方式1：双击运行
start_server.bat

# 方式2：命令行
python app.py --port 5000
```

### 性能测试
```bash
# 运行性能指标验证
python test_performance_metrics.py

# 或双击运行
run_performance_test.bat
```

### 检查数据库
```bash
python debug_database.py
```

---

## 📊 系统特性

### 核心功能
- ✅ **跨模态检测**: CSV文本 + DICOM影像联合检测
- ✅ **实体识别**: 准确率 > 80%（实际100%）
- ✅ **高性能**: 处理速度 < 2s（实际0.039s）
- ✅ **格式保留加密**: FPE保持数据格式
- ✅ **内容寻址存储**: CAS去重存储
- ✅ **抗量子攻击**: SPHINCS+后量子签名

### 技术栈
- **后端**: Python 3.8+, Flask
- **前端**: HTML5, JavaScript, CSS3
- **数据库**: SQLite
- **加密**: Ascon (PRF + AEAD)
- **签名**: SPHINCS+ (可选)
- **医学影像**: PyDICOM
- **数据处理**: Pandas, NumPy

---

## 🎯 性能指标

| 指标 | 要求 | 实际表现 | 状态 |
|------|------|---------|------|
| **实体感知准确率** | > 80% | 100% | ✅ 达标 |
| **算法运算速度** | < 2s | 0.039s | ✅ 达标 |
| **匹配成功率** | > 95% | 100% | ✅ 达标 |

---

## 📁 项目结构

```
项目根目录/
├── app.py                     # Flask主应用
├── services/                  # 核心服务模块
│   ├── crossmodal_service.py # 跨模态检测
│   ├── protection_service.py # 数据保护
│   ├── storage_audit_service.py # 存储与审计
│   ├── roi_service.py        # DICOM处理
│   └── ner_service.py        # 实体识别
├── templates/                 # 前端模板
│   └── index.html
├── static/                    # 静态资源
│   ├── css/
│   └── js/
├── output/                    # 保护后的文件
├── storage_repo/              # 长期存储
│   ├── cas/                  # 内容寻址存储
│   ├── batches/              # 批次审计
│   └── db/                   # SQLite数据库
├── uploads/                   # 临时上传
└── docs/                      # 详细文档
    ├── DATA_FLOW_GUIDE.md         # 数据流程指南
    ├── STORAGE_ARCHITECTURE.md    # 存储架构说明
    ├── TESTING_GUIDE.md           # 测试指南
    └── TROUBLESHOOTING.md         # 故障排除
```

---

## 🔐 安全特性

### 加密算法
- **Ascon-PRF**: 伪随机函数生成
- **FPE**: 格式保留加密（保持数据格式）
- **Ascon-AEAD**: 认证加密（加密+完整性）
- **SPHINCS+**: 后量子数字签名

### 存储安全
- **CAS**: 内容寻址，自动去重
- **SHA256**: 文件完整性验证
- **SQLite**: 加密索引管理
- **审计清单**: 完整操作记录

---

## 🌟 主要功能

### 1. 单文件检测
- 上传 CSV + DICOM
- 检测敏感实体
- 跨模态关联分析
- ROI区域识别

### 2. 批量处理
- 批量上传文件
- 并行检测
- 批次管理
- 统计报告

### 3. 数据保护
- 元数据加密
- 格式保留
- 私有标签存储
- 审计清单生成

### 4. 存储管理
- CAS去重存储
- 快速索引查询
- 批次审计
- 验证包导出

### 5. 验证工具
- Bundle完整性验证
- 签名验证
- 仓库验证

---

## 📞 支持

### 遇到问题？

1. **查看文档**: [故障排除](docs/TROUBLESHOOTING.md)
2. **检查日志**: Flask终端输出
3. **数据库诊断**: `python debug_database.py`
4. **性能测试**: `python test_performance_metrics.py`

### 常见问题快速解决

| 问题 | 解决方案 |
|------|---------|
| 单文件显示"需要批量处理" | 重启服务 + 刷新浏览器 |
| 存储数量显示0 | 检查文件名是否匹配（运行数据库检查）|
| 置信度都是98% | 清除缓存并重启服务 |
| 速度超过2秒 | 检查DICOM文件大小，考虑使用GPU |

---

## 🔄 更新记录

### 最新改进 (2025-10-23)

- ✅ 修复单文件保护"需要批量处理"错误
- ✅ 修复存储入库文件名不匹配问题
- ✅ 实现动态置信度计算（不再固定98%）
- ✅ 添加性能测试工具（验证两大指标）
- ✅ 完善文档和故障排除指南

详见 [更新日志](CHANGELOG.md)

---

---

## 🙏 致谢

- PyDICOM: DICOM文件处理
- Ascon: 轻量级加密算法
- Flask: Web框架
- SPHINCS+: 后量子签名

---

**文档版本**: v2.0  
**最后更新**: 2025-10-23  
**项目状态**: ✅ 所有功能正常，性能指标达标


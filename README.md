# Google Cloud 运维项目

**项目ID**: `wprojectl`  
**项目编号**: `644485179199`  
**BigQuery位置**: `us-central1`  
**时区**: `Asia/Shanghai`

---

## 📋 核心规则文档

### 1. [PROJECT_RULES.md](PROJECT_RULES.md) - 项目规则 ⭐
数据源铁律、BigQuery操作规范、代码提交护栏、执行纪律等项目级规则。

**关键要点**:
- ✅ 唯一真相源: BigQuery + GCS（已验证12个数据集）
- ❌ 禁止本地文件数据
- ❌ 禁止模拟/合成数据
- 所有SQL统一使用 `Asia/Shanghai` 时区
- 所有变更仅在 `CHANGESETS/` 目录生成

### 2. [SYSTEM_RULES.md](SYSTEM_RULES.md) - 系统规则 ⭐
架构原则、时间宪法、数据质量契约、成本治理、Schema治理等系统级规范。

**关键要点**:
- 五种时间类型定义 (event_time, ingest_time等)
- 时间处理十诫与错误危害排序
- 表级SLO定义（新鲜度≤5分钟、完整性≥99%）
- 成本闸门与预算控制（100GB/日）
- 双轨制发布流程、错误预算机制

### 3. [PROMPT_OWASP.md](PROMPT_OWASP.md) - Prompt安全规则 🔒
基于OWASP Top 10 for LLM的提示词注入防护、敏感信息泄露防护、权限提升防护等。

**关键要点**:
- LLM01-10完整防护体系
- 提示词注入防护与检测
- PII数据脱敏（邮箱/手机/IP）
- 训练数据污染检测
- 模型拒绝服务防护（速率限制、成本熔断）
- 事件响应流程（分级、SOP）

### 4. [COMPLIANCE_RULES.md](COMPLIANCE_RULES.md) - 合规与透明性规则 ⚖️
GDPR、中国《个人信息保护法》、数据分类、用户权利、审计日志等法规合规。

**关键要点**:
- 数据分类体系（PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED）
- PII识别与脱敏策略（HIGH/MEDIUM/LOW三级）
- GDPR用户权利实施（访问权/删除权/可携带权）
- 算法透明性（模型卡片、SHAP解释）
- 数据血缘可视化
- 72小时数据泄露通知机制

### 5. [TECHNICAL_SPECS.md](TECHNICAL_SPECS.md) - 技术规范文档 🔧
环境配置、数据模型、性能优化、安全配置、监控告警、灾难恢复等技术细节。

**关键要点**:
- 完整的BigQuery数据集架构（aieg/aieg_prod/aieg_audit等）
- 12个GCS存储桶规范（生命周期、加密）
- 核心表Schema定义（draws_14w/access_logs）
- 查询优化规则（分区过滤、聚簇优化）
- IAM角色定义（分析师/工程师/ML工程师）
- Row-Level Security实施
- 监控指标与告警策略
- 灾难恢复RTO/RPO（30分钟/5分钟）

### 6. [ANTI_DRIFT_RULES.md](ANTI_DRIFT_RULES.md) - 防跑偏规则 🎯
防止本地测试数据误导工作的完整防护体系。

**关键要点**:
- 数据源强制验证清单（禁止本地路径黑名单）
- SQL强制模板（完整项目前缀+验证查询）
- 本地数据污染防护（目录隔离策略）
- 双源对比验证机制
- 误导数据特征库（7种检测规则）
- 数据完整性守卫（自动拦截）
- AI/LLM工作流防护（Prompt防污染）
- 团队协作防护（零容忍+正向激励）
- 应急响应预案（污染事件5阶段处理）

### 7. [LOCAL_DATA_ZERO_TRUST.md](LOCAL_DATA_ZERO_TRUST.md) - 本地数据零信任防护 🛡️
防止用户不小心将本地数据同步到生产环境的8层防护体系。

**关键要点**:
- 8大污染风险识别（命令行上传、Python脚本、SQL注入等）
- 8层防护体系（IAM隔离、数据集锁定、命令行拦截等）
- IAM权限隔离：用户只读、AI完整权限
- 命令行拦截器：Shell别名保护、强制确认
- Python安全包装器：SafeBigQueryClient、Pandas保护
- Git提交拦截：Pre-commit/Pre-push Hooks
- 文件系统监控：实时危险命令检测
- CI/CD防护：GitHub Actions安全检查
- 自动污染检测：实时检测、告警分级
- 应急响应流程：L1-L4分级处理（<5分钟回滚）
- 综合防护率：99.8%

### 8. [MANDATORY_STARTUP_CHECKLIST.md](MANDATORY_STARTUP_CHECKLIST.md) - 强制启动检查清单 🔍
防止AI助手被本地数据误导的10步强制验证机制。

**关键要点**:
- 核心风险：记忆丢失、会话重置、本地同名数据、环境混淆
- 10步强制检查：GCP连接→数据集→核心表→数据真实性→审计日志→规则重载→环境变量→工作目录→权限→报告生成
- 强制执行机制：Shell启动自动检查、IDE自动任务
- AI助手工作清单：Phase 1环境验证→Phase 2数据真实性→Phase 3规则重载→Phase 4工作确认
- 记忆锚点文件：`.memory_anchor.txt`（会话重置必读）
- 自动提醒：每小时重新验证
- 实施脚本：`PRODUCTION/scripts/mandatory_startup_check.sh`
- 每日检查清单（开工前/工作中/收工前）

---

## 🏛️ 系统架构

### ☁️ 云端全自动架构（已上线：2025-10-02）

```
┌─────────────────────────────────────────────────────────────┐
│         DrawsGuard System（100%云端运行，无需本地）           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼──────────────────────┐
        │                     │                      │
        ▼                     ▼                      ▼
┌──────────────┐      ┌───────────────┐    ┌──────────────┐
│ Cloud        │      │ Cloud Run     │    │ BigQuery     │
│ Scheduler    │──▶   │ API采集服务    │──▶│ 数据存储     │
│              │      │               │    │              │
│ • 每5分钟触发 │      │ • 实时API调用  │    │ • draws表    │
│ • 自动重试    │      │ • 数据验证    │    │ • 监控视图   │
│ • 日志追踪    │      │ • 去重写入    │    │ • 质量报告   │
└──────────────┘      └───────────────┘    └──────────────┘
        │                      ▲                     │
        │                      │                     │
        │         ┌────────────┴──────────────┐     │
        │         │                           │     │
        │         ▼                           ▼     │
        │  ┌──────────────┐        ┌──────────────┐│
        │  │ Secret       │        │ Cloud        ││
        └──│ Manager      │        │ Logging      │┘
           │              │        │              │
           │ • API密钥    │        │ • 实时日志   │
           │ • 安全存储   │        │ • 审计追踪   │
           └──────────────┘        └──────────────┘

✨ 云端优势（已实现）:
  ✅ 7×24小时不间断运行（Google SLA 99.95%）
  ✅ 自动故障恢复（3次重试机制）
  ✅ 零维护成本（无需人工干预）
  ✅ 成本极低：$0.15/月（几乎免费）
  ✅ 本地电脑可随时关机（已验证）
  ✅ 实时数据更新（最新延迟<5分钟）

📊 数据架构:
        ┌────────────────────────────────────────┐
        │         BigQuery 数据层                 │
        │                                        │
        │  drawsguard         drawsguard_stage  │
        │  (生产)             (暂存)              │
        │                                        │
        │  drawsguard_audit   drawsguard_monitor│
        │  (审计)             (监控)              │
        │                                        │
        │  drawsguard_backup  drawsguard_prod   │
        │  (备份)             (生产备份)          │
        └────────────────────────────────────────┘

📚 完整文档:
  - VERIFICATION/20251002_cloud_migration/FINAL_SUCCESS_REPORT.md
  - CLOUD/api-collector/main.py
```

## 🚀 快速开始

### 环境配置
```bash
# 设置环境变量
export BQLOC=us-central1
export GCP_PROJECT=wprojectl
export TZ=Asia/Shanghai

# 验证配置
gcloud config get-value project
# 应输出: wprojectl
```

### BigQuery查询模板
```bash
bq query --location=$BQLOC \ 
  --project_id=wprojectl \
  --use_legacy_sql=false \
  --format=csv \
<<'SQL'
SELECT 
  FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', timestamp, 'Asia/Shanghai') AS ts_local,
  column1,
  column2
FROM `wprojectl.dataset.table`
WHERE DATE(timestamp, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
LIMIT 100
SQL
```

---

## 📁 目录结构规范

```
.
├── CHANGESETS/              # 候选变更目录（允许写入）
│   └── YYYYMMDD_HHMM_feature/
│       ├── sql/
│       ├── scripts/
│       └── MANIFEST.md
│
├── PRODUCTION/              # 生产目录（严禁直改）
│   ├── sql/
│   ├── scripts/
│   └── config/
│
├── VERIFICATION/            # 审计目录（所有输出落盘）
│   └── YYYYMMDD_HHMM_task/
│       ├── raw_output.log
│       ├── receipt.json
│       └── checkpoints.log
│
├── PROJECT_RULES.md         # 项目规则
├── SYSTEM_RULES.md          # 系统规则
├── PROMPT_OWASP.md          # Prompt安全规则
└── README.md                # 本文件
```

---

## 🔒 数据源铁律

### ✅ 允许
- BigQuery真实表查询
- GCS存储的生产数据

### ❌ 禁止
- 本地文件数据（容易误导）
- 模拟/合成/占位数据
- 未经验证的缓存数据

### 数据验证流程
```bash
# 1. 查询前验证表存在性
bq show --location=$BQLOC wprojectl:dataset.table

# 2. 执行查询
bq query --location=$BQLOC ... > output.csv

# 3. 验证输出非空
row_count=$(wc -l < output.csv)
if [[ $row_count -eq 0 ]]; then
  echo "STOP: 数据源缺失" >&2
  exit 1
fi
```

---

## ⏱️ 时间处理规范

### 强制要求
1. **时区统一**: 所有SQL使用 `'Asia/Shanghai'`
2. **时间戳格式**: RFC3339标准 `YYYY-MM-DDTHH:MM:SSZ`
3. **日期过滤**: `DATE(timestamp, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')`
4. **禁止裸时间戳**: 必须显式指定时区

### 五种时间类型
```sql
event_time      -- 事件发生时间（业务时间）
ingest_time     -- 数据接入时间（系统写入时间）
process_time    -- 数据处理时间（计算触发时间）
decision_time   -- 决策生成时间（模型输出时间）
execution_time  -- 执行时间（动作发生时间）
```

---

## 🛡️ 安全检查清单

### 部署前检查
```bash
#!/bin/bash
# 1. 提示词注入测试
python3 test_prompt_injection.py || exit 1

# 2. 敏感信息泄露测试
python3 test_pii_leakage.py || exit 1

# 3. 权限测试
python3 test_authorization.py || exit 1

# 4. 依赖漏洞扫描
safety check --json || exit 1

# 5. 模型完整性验证
python3 verify_model_signature.py || exit 1

echo "✅ 所有安全检查通过"
```

---

## 📊 监控与告警

### 告警分级
- **P0 CRITICAL**: 5分钟内响应（数据新鲜度>10分钟、生产表写入失败）
- **P1 HIGH**: 30分钟内响应（KPI低于阈值、成本超预算80%）
- **P2 MEDIUM**: 2小时内响应（Schema变更、慢查询>60s）
- **P3 LOW**: 当日处理（优化建议、容量规划提醒）

### 实时监控查询
```sql
-- 安全事件监控
SELECT 
  timestamp,
  user_id,
  event_type,
  severity
FROM `wprojectl.audit.security_logs`
WHERE 
  severity IN ('HIGH', 'CRITICAL')
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
ORDER BY timestamp DESC
```

---

## 🚨 禁止事项总清单

```
❌ 使用本地文件作为数据源
❌ 模拟/合成/占位数据
❌ 跳过输出验证直接进入下一步
❌ Here-Doc末尾直接接管道
❌ SELECT * 查询
❌ JOIN键类型不对齐
❌ 裸时间戳比较（不带时区）
❌ 后台执行关键任务
❌ 无限循环或轮询
❌ 直接修改PRODUCTION目录
❌ 白名单外的云命令或系统工具
❌ 缺失CHECKPOINT的长时间任务
❌ 非RFC3339格式的时间戳
❌ 混用时区
❌ 未经审计的敏感操作
```

---

## 📞 紧急联系

**项目总指挥**: 见内部文档  
**安全事件**: security@company.com  
**技术支持**: tech-support@company.com

---

**版本**: v2.0（云端全自动）  
**最后更新**: 2025-10-02  
**维护者**: 数据工程团队

---

## 📡 快速命令（云端版）

### 查看最新数据
```bash
bq query --location=us-central1 --use_legacy_sql=false \
"SELECT * FROM \`wprojectl.drawsguard.draws\` 
 ORDER BY timestamp DESC LIMIT 5"
```

### 查看系统日志
```bash
gcloud logging read \
  "resource.labels.service_name=drawsguard-api-collector" \
  --limit 20 --project=wprojectl
```

### 手动触发采集
```bash
gcloud scheduler jobs run drawsguard-collect-5min \
  --location us-central1 --project=wprojectl
```

### 查看服务状态
```bash
gcloud run services describe drawsguard-api-collector \
  --region us-central1 --project=wprojectl
```


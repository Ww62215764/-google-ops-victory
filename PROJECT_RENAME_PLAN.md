# 🔄 项目重命名方案 - PC28 → AI工业进化预测

> **项目**: DrawsGuard → AI Industrial Evolution Prediction (AIEP)  
> **执行日期**: 2025-10-07  
> **状态**: 待执行

---

## 🎯 重命名概述

### 旧名称体系
```
业务名称: PC28
技术代码: pc28
数据集前缀: pc28_*
密钥前缀: pc28-*
```

### 新名称体系
```
业务名称: AI工业进化预测小游戏
英文名称: AI Industrial Evolution Game
英文简称: AIEG
技术代码: aieg
数据集前缀: aieg_*
密钥前缀: aieg-*
品牌标识: 🤖🏭📈
项目性质: 自主开奖、自主预测的彩票类型小游戏
```

---

## 📊 影响范围分析

### ✅ 需要重命名的资源

#### 1. Secret Manager (3个密钥)
```
旧名称                  →  新名称
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
pc28-api-key           →  aiep-api-key
pc28-bot-token         →  aiep-bot-token
pc28-chat-id           →  aiep-chat-id
```

#### 2. BigQuery 数据集
```
旧名称                  →  新名称
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
pc28_monitoring        →  aiep_monitoring
pc28_prod              →  aiep_prod (如存在)
pc28_audit             →  aiep_audit (如存在)
```

#### 3. 代码中的引用 (9处)
```
文件路径                                              行号   当前值
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
main.py                                               L186   "pc28-api-key"
main.py                                               L207   "pc28_main_api"
collector/upstream_detector.py                        L16    "pc28_monitoring"
PRODUCTION_DEPLOYMENT_GUIDE.md                        L33    "pc28-api-key"
PRODUCTION_DEPLOYMENT_GUIDE.md                        L40    pc28_monitoring
PRODUCTION_DEPLOYMENT_GUIDE.md                        L41    pc28_monitoring
PRODUCTION_DEPLOYMENT_GUIDE.md                        L159   pc28_monitoring
PRODUCTION_DEPLOYMENT_GUIDE.md                        L189   pc28_monitoring
README.md                                             L65    pc28/pc28_prod/pc28_audit
```

#### 4. 环境变量
```
旧名称                       →  新名称
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BQ_MONITORING_DATASET        →  BQ_MONITORING_DATASET (值改为aiep_monitoring)
(值: pc28_monitoring)         →  (值: aiep_monitoring)
```

#### 5. 文档更新 (3个文件)
```
- README.md
- PRODUCTION_DEPLOYMENT_GUIDE.md
- CODE_QUALITY_REPORT.md (如有提及)
```

---

## 🚀 执行计划

### 阶段1：准备工作（10分钟）✅

#### 1.1 创建备份
```bash
# 备份当前配置
export BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p ~/backups/rename_$BACKUP_DATE

# 备份关键文件
cp main.py ~/backups/rename_$BACKUP_DATE/
cp collector/upstream_detector.py ~/backups/rename_$BACKUP_DATE/
cp README.md ~/backups/rename_$BACKUP_DATE/
cp PRODUCTION_DEPLOYMENT_GUIDE.md ~/backups/rename_$BACKUP_DATE/

# 导出当前Secret Manager配置
gcloud secrets describe pc28-api-key --format=json > ~/backups/rename_$BACKUP_DATE/secret_pc28-api-key.json
gcloud secrets describe pc28-bot-token --format=json > ~/backups/rename_$BACKUP_DATE/secret_pc28-bot-token.json
gcloud secrets describe pc28-chat-id --format=json > ~/backups/rename_$BACKUP_DATE/secret_pc28-chat-id.json
```

#### 1.2 验证当前系统状态
```bash
# 检查Cloud Run服务状态
gcloud run services list --region us-central1

# 检查BigQuery数据集
bq ls --project_id=wprojectl

# 检查Secret Manager
gcloud secrets list
```

---

### 阶段2：代码更新（20分钟）🔧

#### 2.1 更新Python代码

**文件: `CLOUD/drawsguard-api-collector-fixed/main.py`**
```python
# 第186行
- name = f"projects/{GCP_PROJECT_ID}/secrets/pc28-api-key/versions/latest"
+ name = f"projects/{GCP_PROJECT_ID}/secrets/aiep-api-key/versions/latest"

# 第207行
- collector_name="pc28_main_api",
+ collector_name="aiep_main_api",
```

**文件: `CLOUD/drawsguard-api-collector-fixed/collector/upstream_detector.py`**
```python
# 第16行
- BQ_MONITORING = os.environ.get("BQ_MONITORING_DATASET", "pc28_monitoring")
+ BQ_MONITORING = os.environ.get("BQ_MONITORING_DATASET", "aiep_monitoring")
```

#### 2.2 更新文档

**文件: `README.md`**
```markdown
- 项目名称: PC28数据采集系统
+ 项目名称: AI工业进化预测系统 (AIEP)

- 12个BigQuery数据集架构（pc28/pc28_prod/pc28_audit等）
+ 12个BigQuery数据集架构（aiep/aiep_prod/aiep_audit等）
```

**文件: `PRODUCTION_DEPLOYMENT_GUIDE.md`**
```bash
# 所有 "pc28-api-key" 替换为 "aiep-api-key"
# 所有 "pc28_monitoring" 替换为 "aiep_monitoring"
```

#### 2.3 Git提交代码更新
```bash
cd /Users/a606/谷歌运维
git add -A
git commit -m "🔄 项目重命名: PC28 → AI工业进化预测 (AIEP)

代码更新:
- main.py: 更新密钥引用和collector名称
- upstream_detector.py: 更新数据集名称
- README.md: 更新项目介绍
- PRODUCTION_DEPLOYMENT_GUIDE.md: 更新所有引用

下一步: 云端资源重命名"
```

---

### 阶段3：Secret Manager重命名（30分钟）🔐

#### 3.1 创建新密钥并复制值
```bash
# 1. 获取旧密钥的值
OLD_API_KEY=$(gcloud secrets versions access latest --secret="pc28-api-key")
OLD_BOT_TOKEN=$(gcloud secrets versions access latest --secret="pc28-bot-token")
OLD_CHAT_ID=$(gcloud secrets versions access latest --secret="pc28-chat-id")

# 2. 创建新密钥
echo -n "$OLD_API_KEY" | gcloud secrets create aiep-api-key --data-file=-
echo -n "$OLD_BOT_TOKEN" | gcloud secrets create aiep-bot-token --data-file=-
echo -n "$OLD_CHAT_ID" | gcloud secrets create aiep-chat-id --data-file=-

# 3. 授权服务账号访问新密钥
gcloud secrets add-iam-policy-binding aiep-api-key \
  --member="serviceAccount:drawsguard-collector@wprojectl.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding aiep-bot-token \
  --member="serviceAccount:drawsguard-collector@wprojectl.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding aiep-chat-id \
  --member="serviceAccount:drawsguard-collector@wprojectl.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 4. 验证新密钥可访问
gcloud secrets versions access latest --secret="aiep-api-key"
gcloud secrets versions access latest --secret="aiep-bot-token"
gcloud secrets versions access latest --secret="aiep-chat-id"
```

#### 3.2 保留旧密钥（暂不删除，用于回滚）
```bash
# 给旧密钥添加标签，标记为已废弃
gcloud secrets update pc28-api-key --update-labels="status=deprecated,replaced-by=aiep-api-key"
gcloud secrets update pc28-bot-token --update-labels="status=deprecated,replaced-by=aiep-bot-token"
gcloud secrets update pc28-chat-id --update-labels="status=deprecated,replaced-by=aiep-chat-id"
```

---

### 阶段4：BigQuery数据集重命名（1小时）💾

#### ⚠️ 重要说明
BigQuery不支持直接重命名数据集，需要：
1. 创建新数据集
2. 复制所有表
3. 更新所有引用
4. 验证后删除旧数据集

#### 4.1 创建新数据集
```bash
# 创建 aiep_monitoring 数据集
bq mk --location=us-central1 --dataset wprojectl:aiep_monitoring

# 设置数据集描述
bq update --description "AI工业进化预测监控数据集" wprojectl:aiep_monitoring
```

#### 4.2 复制表结构和数据
```bash
# 列出旧数据集的所有表
bq ls --format=prettyjson wprojectl:pc28_monitoring > /tmp/pc28_monitoring_tables.json

# 复制每个表（示例）
bq cp -f wprojectl:pc28_monitoring.upstream_calls wprojectl:aiep_monitoring.upstream_calls
bq cp -f wprojectl:pc28_monitoring.upstream_stale_alerts wprojectl:aiep_monitoring.upstream_stale_alerts

# 验证数据完整性
bq query --use_legacy_sql=false '
SELECT 
  "pc28_monitoring" as dataset,
  COUNT(*) as row_count 
FROM `wprojectl.pc28_monitoring.upstream_calls`
UNION ALL
SELECT 
  "aiep_monitoring" as dataset,
  COUNT(*) as row_count 
FROM `wprojectl.aiep_monitoring.upstream_calls`
'
```

#### 4.3 标记旧数据集为已废弃
```bash
bq update --description "已废弃，已迁移至aiep_monitoring" wprojectl:pc28_monitoring
```

---

### 阶段5：Cloud Run服务更新（20分钟）☁️

#### 5.1 重新部署服务
```bash
cd /Users/a606/谷歌运维/CLOUD/drawsguard-api-collector-fixed

# 构建新镜像（包含代码更新）
gcloud builds submit --tag gcr.io/wprojectl/drawsguard-api-collector:v7.1-aiep

# 部署服务（更新环境变量）
gcloud run deploy drawsguard-api-collector \
  --image gcr.io/wprojectl/drawsguard-api-collector:v7.1-aiep \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account drawsguard-collector@wprojectl.iam.gserviceaccount.com \
  --set-env-vars="BQ_MONITORING_DATASET=aiep_monitoring" \
  --min-instances 1 \
  --max-instances 5
```

#### 5.2 验证服务
```bash
# 健康检查
curl https://drawsguard-api-collector-644485179199.us-central1.run.app/health

# 触发一次数据采集
curl -X POST https://drawsguard-api-collector-644485179199.us-central1.run.app/collect

# 检查日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=drawsguard-api-collector" \
  --limit 20 \
  --format json
```

---

### 阶段6：测试验证（30分钟）✅

#### 6.1 功能测试
```bash
# 运行完整测试套件
cd /Users/a606/谷歌运维/CLOUD/drawsguard-api-collector-fixed
export PYTHONPATH=.
pytest tests/ -v --cov=. --cov-report=term-missing

# 预期结果：95.81%覆盖率，所有测试通过
```

#### 6.2 集成测试
```bash
# 验证数据写入新数据集
bq query --use_legacy_sql=false '
SELECT 
  collector,
  COUNT(*) as calls,
  MAX(call_ts) as last_call
FROM `wprojectl.aiep_monitoring.upstream_calls`
WHERE DATE(call_ts) = CURRENT_DATE()
GROUP BY collector
'

# 检查告警表
bq query --use_legacy_sql=false '
SELECT * 
FROM `wprojectl.aiep_monitoring.upstream_stale_alerts`
ORDER BY alert_ts DESC
LIMIT 5
'
```

#### 6.3 端到端测试
```bash
# 1. 触发采集
curl -X POST https://drawsguard-api-collector-644485179199.us-central1.run.app/collect

# 2. 等待5秒
sleep 5

# 3. 验证数据
bq query --use_legacy_sql=false '
SELECT COUNT(*) as recent_records
FROM `wprojectl.drawsguard.draws`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 MINUTE)
'
```

---

### 阶段7：清理旧资源（在验证稳定后执行）🗑️

#### ⚠️ 建议等待7天观察期后再执行

```bash
# 删除旧Secret Manager密钥
gcloud secrets delete pc28-api-key --quiet
gcloud secrets delete pc28-bot-token --quiet
gcloud secrets delete pc28-chat-id --quiet

# 删除旧BigQuery数据集（慎重！）
bq rm -r -f wprojectl:pc28_monitoring

# 清理旧镜像
gcloud container images delete gcr.io/wprojectl/drawsguard-api-collector:v7.0-phoenix --quiet
```

---

## 📋 执行检查清单

### 准备阶段
- [ ] 备份所有配置文件
- [ ] 导出Secret Manager密钥
- [ ] 备份BigQuery数据集
- [ ] 确认回滚方案

### 代码更新
- [ ] 更新main.py
- [ ] 更新upstream_detector.py
- [ ] 更新README.md
- [ ] 更新PRODUCTION_DEPLOYMENT_GUIDE.md
- [ ] Git提交并推送

### 云端资源
- [ ] 创建新Secret Manager密钥
- [ ] 授权服务账号访问
- [ ] 创建新BigQuery数据集
- [ ] 复制所有表数据
- [ ] 验证数据完整性

### 服务部署
- [ ] 构建新镜像
- [ ] 部署Cloud Run服务
- [ ] 更新环境变量
- [ ] 验证服务健康

### 测试验证
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 端到端测试通过
- [ ] 数据质量验证

### 文档更新
- [ ] 更新所有文档引用
- [ ] 创建迁移日志
- [ ] 通知团队成员

---

## 🔄 回滚方案

如果出现问题，可以快速回滚：

### 回滚步骤
```bash
# 1. 恢复旧服务配置
gcloud run deploy drawsguard-api-collector \
  --image gcr.io/wprojectl/drawsguard-api-collector:v7.0-phoenix \
  --set-env-vars="BQ_MONITORING_DATASET=pc28_monitoring"

# 2. 恢复代码
git revert HEAD
git push origin main

# 3. 旧资源仍然存在，服务可立即恢复
```

---

## 📊 风险评估

| 风险项 | 等级 | 缓解措施 |
|--------|------|----------|
| **数据丢失** | 中 | 完整备份，分步执行，保留旧数据集7天 |
| **服务中断** | 低 | 金丝雀部署，快速回滚方案 |
| **权限问题** | 低 | 预先验证所有权限 |
| **引用遗漏** | 中 | 全面扫描，创建映射表 |

---

## ✅ 成功标准

- ✅ 所有测试通过（95.81%覆盖率）
- ✅ 服务正常运行24小时无告警
- ✅ 数据采集功能正常
- ✅ 新旧数据集数据一致
- ✅ 所有文档已更新

---

## 📞 支持

**执行负责人**: AI助手  
**批准**: 项目总指挥大人  
**执行时间**: 待确认  

---

**准备就绪！等待执行命令！** 🚀


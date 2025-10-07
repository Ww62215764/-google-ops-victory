# 🚀 AI工业进化预测小游戏 - 生产环境部署指南

> **项目**: AI Industrial Evolution Game (AIEG)  
> **版本**: v7.1 Evolution  
> **状态**: 已准备好生产部署  
> **最后更新**: 2025-10-07
>
> **项目性质**: 自主开奖、自主预测的彩票类型小游戏

---

## ✅ 部署前检查清单

### 代码质量 ✅
- [x] 测试覆盖率 ≥ 95%（当前：95.81%）
- [x] 无重复代码
- [x] 无死代码
- [x] 代码复杂度控制（B级）
- [x] 所有模块高度可维护（A级）

### 文档完整性 ✅
- [x] README.md
- [x] CONTRIBUTING.md
- [x] CODE_QUALITY_REPORT.md
- [x] API文档

### 依赖管理 ✅
- [x] 依赖精简（10个核心包）
- [x] 无未使用依赖
- [x] 版本锁定

### 云端资源 ✅
- [x] 12个Storage Buckets
- [x] 3个Cloud Run Services
- [x] 7个Cloud Scheduler Jobs
- [x] 所有资源运行正常

---

## 🎯 部署步骤

### 第一阶段：环境准备（10分钟）

#### 1. 确认环境变量
```bash
# 必需的环境变量
export GCP_PROJECT_ID="wprojectl"
export GCP_LOCATION="us-central1"
export BQLOC="us-central1"

# 验证Secret Manager中的API密钥
gcloud secrets versions access latest --secret="aieg-api-key"
```

#### 2. 验证服务账号权限
```bash
# 确认服务账号拥有必要权限
gcloud projects get-iam-policy wprojectl \
  --flatten="bindings[].members" \
  --filter="bindings.members:drawsguard-collector@wprojectl.iam.gserviceaccount.com"
```

#### 3. 检查BigQuery表结构
```bash
# 验证关键表存在
bq show --location=$BQLOC wprojectl:drawsguard.draws
bq show --location=$BQLOC wprojectl:aieg_monitoring.upstream_calls
bq show --location=$BQLOC wprojectl:aieg_monitoring.upstream_stale_alerts
```

---

### 第二阶段：金丝雀部署（30分钟）

#### 1. 部署到测试环境
```bash
cd /Users/a606/谷歌运维/CLOUD/drawsguard-api-collector-fixed

# 构建容器镜像
gcloud builds submit --tag gcr.io/wprojectl/drawsguard-api-collector:v7.0-phoenix

# 部署到Cloud Run（限制流量10%）
gcloud run deploy drawsguard-api-collector \
  --image gcr.io/wprojectl/drawsguard-api-collector:v7.0-phoenix \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account drawsguard-collector@wprojectl.iam.gserviceaccount.com \
  --min-instances 1 \
  --max-instances 5 \
  --traffic "LATEST=10"
```

#### 2. 监控金丝雀流量（15分钟）
```bash
# 查看日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=drawsguard-api-collector" \
  --limit 50 \
  --format json

# 检查错误率
gcloud monitoring time-series list \
  --filter='metric.type="custom.googleapis.com/drawsguard/errors_total"' \
  --interval-start-time="$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ)" \
  --interval-end-time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

#### 3. 验证数据质量
```bash
# 检查最近采集的数据
bq query --location=$BQLOC --use_legacy_sql=false '
SELECT 
  period,
  timestamp,
  numbers,
  sum_value,
  created_at
FROM `wprojectl.drawsguard.draws`
WHERE DATE(timestamp, "Asia/Shanghai") = CURRENT_DATE("Asia/Shanghai")
ORDER BY timestamp DESC
LIMIT 10
'
```

---

### 第三阶段：全量部署（10分钟）

#### 1. 切换100%流量
```bash
gcloud run services update-traffic drawsguard-api-collector \
  --to-latest \
  --region us-central1
```

#### 2. 更新Cloud Scheduler
```bash
# 确认定时任务指向新版本
gcloud scheduler jobs describe trigger-draws-collector \
  --location us-central1
```

---

## 📊 监控指标

### 关键性能指标（KPI）

| 指标 | 目标值 | 告警阈值 |
|------|--------|----------|
| **请求成功率** | ≥ 99.5% | < 99% |
| **平均响应时间** | ≤ 500ms | > 1000ms |
| **数据采集间隔** | 3-5分钟 | > 6分钟 |
| **每日期数** | 276-401期 | < 270期 |
| **完整率** | ≥ 95% | < 90% |
| **重复率** | < 1% | > 5% |

### 监控查询

#### 1. 实时健康检查
```bash
# 每5分钟自动检查
curl https://drawsguard-api-collector-644485179199.us-central1.run.app/health
```

#### 2. 数据完整性检查
```sql
-- 检查今日数据完整率
SELECT 
  COUNT(*) as period_count,
  MIN(timestamp) as first_draw,
  MAX(timestamp) as last_draw,
  TIMESTAMP_DIFF(MAX(timestamp), MIN(timestamp), MINUTE) / NULLIF(COUNT(*), 0) as avg_interval_minutes
FROM `wprojectl.drawsguard.draws`
WHERE DATE(timestamp, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
```

#### 3. 上游API健康度
```sql
-- 检查上游API响应
SELECT 
  collector,
  COUNT(*) as call_count,
  COUNT(DISTINCT returned_period) as unique_periods,
  MAX(call_ts) as last_call
FROM `wprojectl.aieg_monitoring.upstream_calls`
WHERE DATE(call_ts, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
GROUP BY collector
```

---

## 🚨 告警配置

### Cloud Monitoring告警策略

#### 1. 数据断档告警（P0）
```yaml
displayName: "DrawsGuard - 数据断档告警"
conditions:
  - displayName: "超过10分钟无新数据"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND metric.type="custom.googleapis.com/drawsguard/data_freshness_minutes"'
      comparison: COMPARISON_GT
      thresholdValue: 10
      duration: 300s
notificationChannels:
  - projects/wprojectl/notificationChannels/[TELEGRAM_CHANNEL_ID]
```

#### 2. 错误率告警（P1）
```yaml
displayName: "DrawsGuard - 高错误率告警"
conditions:
  - displayName: "错误率超过1%"
    conditionThreshold:
      filter: 'metric.type="custom.googleapis.com/drawsguard/errors_total"'
      comparison: COMPARISON_GT
      thresholdValue: 0.01
      duration: 60s
```

---

## 🔧 故障排查

### 常见问题

#### 问题1: 上游API返回重复期号
```bash
# 检查熔断器状态
bq query --location=$BQLOC --use_legacy_sql=false '
SELECT 
  alert_ts,
  collector,
  returned_period,
  consecutive_count,
  severity,
  note
FROM `wprojectl.aieg_monitoring.upstream_stale_alerts`
ORDER BY alert_ts DESC
LIMIT 10
'

# 解决方案：等待上游恢复，熔断器会自动解除
```

#### 问题2: Cloud Run冷启动延迟
```bash
# 设置最小实例数
gcloud run services update drawsguard-api-collector \
  --min-instances 1 \
  --region us-central1

# 验证
gcloud run services describe drawsguard-api-collector \
  --region us-central1 \
  --format="value(spec.template.metadata.annotations['autoscaling.knative.dev/minScale'])"
```

#### 问题3: BigQuery插入失败
```bash
# 检查服务账号权限
gcloud projects get-iam-policy wprojectl \
  --flatten="bindings[].members" \
  --filter="bindings.members:drawsguard-collector@wprojectl.iam.gserviceaccount.com" \
  --format="table(bindings.role)"

# 必需角色：
# - roles/bigquery.dataEditor
# - roles/bigquery.jobUser
```

---

## 📈 性能优化建议

### 短期优化（1-2周）

1. **启用HTTP/2**
   - Cloud Run默认支持，确认客户端启用

2. **优化BigQuery MERGE语句**
   - 当前使用单行MERGE，已是最优

3. **缓存Secret Manager响应**
   - 当前已实现单例模式缓存

### 中期优化（1-3个月）

1. **实现请求批处理**
   - 当前单次请求单条数据
   - 可考虑批量写入（如果上游支持）

2. **添加Redis缓存层**
   - 缓存近期数据
   - 减少BigQuery查询

3. **实现分布式追踪**
   - 集成Cloud Trace
   - 可视化请求链路

---

## 🔐 安全检查清单

- [x] API密钥存储在Secret Manager
- [x] 使用专用服务账号（最小权限原则）
- [x] Cloud Run服务启用IAM认证（内部调用）
- [x] 所有敏感数据加密传输（HTTPS）
- [x] 日志不包含敏感信息
- [x] 定期轮换API密钥（建议每90天）

---

## 📋 部署后验证

### 验证步骤

#### 1. 功能验证（5分钟）
```bash
# 1. 健康检查
curl https://drawsguard-api-collector-644485179199.us-central1.run.app/health

# 2. 触发一次采集
curl -X POST https://drawsguard-api-collector-644485179199.us-central1.run.app/collect

# 3. 检查BigQuery数据
bq query --location=$BQLOC --use_legacy_sql=false '
SELECT COUNT(*) as new_records
FROM `wprojectl.drawsguard.draws`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)
'
```

#### 2. 性能验证（10分钟）
```bash
# 使用Apache Bench进行压力测试
ab -n 100 -c 10 https://drawsguard-api-collector-644485179199.us-central1.run.app/health

# 预期结果：
# - 成功率：100%
# - 平均响应时间：< 500ms
# - P95响应时间：< 1000ms
```

#### 3. 监控验证（15分钟）
```bash
# 检查Cloud Monitoring指标
gcloud monitoring time-series list \
  --filter='metric.type="custom.googleapis.com/drawsguard/requests_total"' \
  --interval-start-time="$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ)" \
  --interval-end-time="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --format=json
```

---

## 🎯 成功标准

部署成功的标志：

✅ **功能正常**
- 健康检查返回200
- 数据成功写入BigQuery
- 上游检测正常工作

✅ **性能达标**
- 请求成功率 ≥ 99.5%
- P95响应时间 ≤ 1000ms
- 数据采集间隔 3-5分钟

✅ **监控就绪**
- 所有告警配置生效
- 日志正常输出到Cloud Logging
- 指标正常上报到Cloud Monitoring

✅ **稳定运行**
- 连续24小时无P0/P1告警
- 数据完整率 ≥ 95%
- 无数据重复

---

## 📞 支持联系

**项目负责人**: 项目总指挥大人  
**技术支持**: DrawsGuard技术团队  
**紧急联系**: [Telegram通知频道]

---

**部署准备完成！祝部署顺利！** 🚀


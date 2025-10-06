# 核心系统观察期执行计划

**计划时间**: 2025-10-03 20:35  
**观察周期**: 24-48小时（10月4-5日）  
**执行原则**: 聚焦核心，验证稳定性，不引入新变量

---

## 📋 执行摘要

### 观察期目标

```yaml
核心目标:
  1. 验证核心系统稳定性（数据采集、同步、监控）
  2. 观察告警准确性和及时性
  3. 检查数据完整性和一致性
  4. 评估系统性能和成本

决策点:
  - 10月6日上午：根据观察结果决策下一步

不做的事:
  ❌ 不启动新项目（如预测系统）
  ❌ 不做大规模变更
  ❌ 不引入新的复杂功能
```

---

## 🎯 观察期任务清单

### 阶段1: 初始状态记录（10月3日晚）✅

#### 任务1.1: 记录当前系统状态

**目的**: 建立基线，便于对比

**执行**:
```bash
# 1. Cloud Run服务状态
gcloud run services list --project=wprojectl --platform=managed \
  --format="table(metadata.name,status.conditions[0].status,metadata.creationTimestamp)"

# 2. Cloud Scheduler任务状态
gcloud scheduler jobs list --project=wprojectl --location=us-central1 \
  --format="table(name.basename(),state,schedule,lastAttemptTime)"

# 3. BigQuery表状态
bq ls --project_id=wprojectl --max_results=100 pc28
bq ls --project_id=wprojectl --max_results=100 drawsguard
bq ls --project_id=wprojectl --max_results=100 pc28_monitor

# 4. 数据新鲜度快照
bq query --location=us-central1 --use_legacy_sql=false \
  "SELECT * FROM \`wprojectl.pc28_monitor.cloud_freshness_v\`"
```

**产出**:
- 系统状态快照（保存到VERIFICATION/20251004_observation/）

---

#### 任务1.2: 设置观察指标

**核心指标**:

```yaml
数据采集指标:
  - drawsguard.draws表更新频率: 应每1-3分钟更新
  - 每日期数: 应达到380-420期（95%+完整率）
  - 数据延迟: 应<5分钟

数据同步指标:
  - pc28.draws同步延迟: 应<5分钟（每5分钟同步）
  - 同步成功率: 应≥99%
  - 数据一致性: 100%

监控告警指标:
  - freshness-alert-checker执行: 每5分钟
  - quality-checker执行: 每小时
  - 告警准确性: 无误报
  - 告警及时性: <5分钟

系统性能指标:
  - Cloud Run响应时间: <3秒
  - BigQuery查询时间: <10秒
  - 错误率: <1%

成本指标:
  - Cloud Run成本: 预计$0.15/月
  - BigQuery成本: 预计$5-10/月
  - 总成本: 预计$10-20/月
```

---

### 阶段2: 持续监控（10月4日）⏸️

#### 任务2.1: 早晨检查（10月4日 08:00）

**检查内容**:

```bash
# 1. 检查昨晚数据采集情况
bq query --location=us-central1 --use_legacy_sql=false "
SELECT 
  DATE(timestamp, 'Asia/Shanghai') AS date,
  COUNT(*) AS total_periods,
  MIN(FORMAT_TIMESTAMP('%H:%M:%S', timestamp, 'Asia/Shanghai')) AS first_time,
  MAX(FORMAT_TIMESTAMP('%H:%M:%S', timestamp, 'Asia/Shanghai')) AS last_time,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(timestamp), MINUTE) AS minutes_ago
FROM \`wprojectl.drawsguard.draws\`
WHERE DATE(timestamp, 'Asia/Shanghai') >= CURRENT_DATE('Asia/Shanghai') - 1
GROUP BY date
ORDER BY date DESC
"

# 2. 检查数据同步状态
bq query --location=us-central1 --use_legacy_sql=false "
SELECT 
  COUNT(*) AS pc28_draws_count,
  MAX(timestamp) AS latest_timestamp,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(timestamp), MINUTE) AS lag_minutes
FROM \`wprojectl.pc28.draws\`
WHERE DATE(timestamp, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
"

# 3. 检查监控视图
bq query --location=us-central1 --use_legacy_sql=false "
SELECT * FROM \`wprojectl.pc28_monitor.cloud_freshness_v\`
"

# 4. 检查Cloud Run服务日志（最近12小时）
gcloud logging read "resource.type=cloud_run_revision AND \
  (resource.labels.service_name=drawsguard-api-collector OR \
   resource.labels.service_name=data-sync-service OR \
   resource.labels.service_name=freshness-alert-checker) AND \
  severity>=WARNING" \
  --limit=50 \
  --format=json \
  --project=wprojectl
```

**判断标准**:
```yaml
✅ 通过:
  - 昨日期数 ≥ 380期
  - 数据延迟 < 10分钟
  - 同步成功率 ≥ 99%
  - 无严重错误日志

⚠️ 关注:
  - 昨日期数 320-379期
  - 数据延迟 10-30分钟
  - 同步成功率 95-99%
  - 有警告日志

❌ 异常:
  - 昨日期数 < 320期
  - 数据延迟 > 30分钟
  - 同步成功率 < 95%
  - 有错误日志
```

**产出**:
- 早晨检查报告（保存到VERIFICATION/20251004_observation/morning_check.md）

---

#### 任务2.2: 中午检查（10月4日 12:00）

**检查内容**:

```bash
# 1. 检查今日上午数据采集
bq query --location=us-central1 --use_legacy_sql=false "
SELECT 
  COUNT(*) AS morning_periods,
  MIN(FORMAT_TIMESTAMP('%H:%M:%S', timestamp, 'Asia/Shanghai')) AS first_time,
  MAX(FORMAT_TIMESTAMP('%H:%M:%S', timestamp, 'Asia/Shanghai')) AS last_time
FROM \`wprojectl.drawsguard.draws\`
WHERE DATE(timestamp, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
  AND EXTRACT(HOUR FROM timestamp AT TIME ZONE 'Asia/Shanghai') < 12
"

# 2. 检查采集间隔分布
bq query --location=us-central1 --use_legacy_sql=false "
WITH intervals AS (
  SELECT 
    TIMESTAMP_DIFF(
      timestamp,
      LAG(timestamp) OVER (ORDER BY timestamp),
      SECOND
    ) AS interval_seconds
  FROM \`wprojectl.drawsguard.draws\`
  WHERE DATE(timestamp, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
)
SELECT 
  APPROX_QUANTILES(interval_seconds, 100)[OFFSET(50)] AS p50_seconds,
  APPROX_QUANTILES(interval_seconds, 100)[OFFSET(95)] AS p95_seconds,
  APPROX_QUANTILES(interval_seconds, 100)[OFFSET(99)] AS p99_seconds,
  COUNTIF(interval_seconds > 300) AS over_5min_count,
  COUNT(*) AS total_intervals
FROM intervals
WHERE interval_seconds IS NOT NULL
"

# 3. 检查告警历史
bq query --location=us-central1 --use_legacy_sql=false "
SELECT 
  check_time,
  total_alerts,
  alerts
FROM \`wprojectl.pc28_monitor.freshness_alert_history\`
WHERE DATE(check_time, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
ORDER BY check_time DESC
LIMIT 10
" || echo "表可能不存在，跳过"
```

**产出**:
- 中午检查报告

---

#### 任务2.3: 晚间检查（10月4日 20:00）

**检查内容**:

```bash
# 1. 检查今日全天数据
bq query --location=us-central1 --use_legacy_sql=false "
SELECT 
  DATE(timestamp, 'Asia/Shanghai') AS date,
  COUNT(*) AS total_periods,
  ROUND(COUNT(*) * 100.0 / 400, 2) AS completeness_pct,
  CASE 
    WHEN COUNT(*) >= 380 THEN '✅ 优秀'
    WHEN COUNT(*) >= 360 THEN '🟢 良好'
    WHEN COUNT(*) >= 320 THEN '🟡 偏低'
    ELSE '🔴 异常'
  END AS status
FROM \`wprojectl.drawsguard.draws\`
WHERE DATE(timestamp, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
GROUP BY date
"

# 2. 检查数据质量
bq query --location=us-central1 --use_legacy_sql=false "
SELECT * FROM \`wprojectl.pc28_monitor.collection_quality_v\`
WHERE date = CURRENT_DATE('Asia/Shanghai')
"

# 3. 检查端到端延迟
bq query --location=us-central1 --use_legacy_sql=false "
SELECT * FROM \`wprojectl.pc28_monitor.e2e_latency_summary_v\`
WHERE DATE(sync_time, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
ORDER BY hour DESC
LIMIT 5
"
```

**产出**:
- 晚间检查报告
- 第一天观察总结

---

### 阶段3: 持续监控（10月5日）⏸️

重复阶段2的所有检查，产出：
- 10月5日早晨检查报告
- 10月5日中午检查报告
- 10月5日晚间检查报告
- 第二天观察总结

---

### 阶段4: 综合评估（10月6日上午）📋

#### 任务4.1: 生成观察期报告

**报告内容**:

```yaml
1. 系统稳定性评估:
   - 数据采集稳定性（2天数据）
   - 数据同步稳定性（2天数据）
   - 监控告警稳定性（2天数据）
   - 整体评分（0-100分）

2. 数据完整性评估:
   - 10月4日期数和完整率
   - 10月5日期数和完整率
   - 数据一致性检查结果
   - 整体评分（0-100分）

3. 性能评估:
   - Cloud Run响应时间统计
   - BigQuery查询时间统计
   - 端到端延迟统计
   - 整体评分（0-100分）

4. 成本评估:
   - Cloud Run实际成本
   - BigQuery实际成本
   - 总成本 vs 预算
   - 成本效益分析

5. 问题和改进建议:
   - 发现的问题列表
   - 优化建议
   - 风险评估

6. 决策建议:
   - 系统是否稳定（通过/不通过）
   - 是否可以进入下一阶段
   - 预测系统是否需要恢复
```

**产出**:
- 观察期综合报告（VERIFICATION/20251006_observation/COMPREHENSIVE_REPORT.md）

---

#### 任务4.2: 决策会议

**议题**:
1. 核心系统是否稳定？
2. 是否需要优化和调整？
3. 是否需要恢复预测系统？
4. 下一阶段工作计划

**决策选项**:

```yaml
选项A: 系统稳定，保持现状 ✅
  条件:
    - 观察期评分 ≥ 85分
    - 无重大问题
    - 成本在预算内
  
  行动:
    - 继续观察1-2周
    - 进行性能优化
    - 不启动新项目

选项B: 系统基本稳定，可启动预测系统设计 📋
  条件:
    - 观察期评分 ≥ 80分
    - 有明确业务需求
    - 有资源和预算
  
  行动:
    - 启动预测系统设计项目
    - 1周完成设计文档
    - 评审后决定是否开发

选项C: 系统不稳定，继续修复 ⚠️
  条件:
    - 观察期评分 < 80分
    - 发现重大问题
  
  行动:
    - 立即修复问题
    - 延长观察期
    - 暂停所有新项目
```

---

## 📊 观察期监控仪表板

### 关键指标看板

```yaml
数据采集健康度:
  □ 10月3日: ___期（____%）
  □ 10月4日: ___期（____%）
  □ 10月5日: ___期（____%）
  目标: ≥380期（≥95%）

数据同步健康度:
  □ 延迟p95: ___分钟
  □ 成功率: ___%
  □ 一致性: ___%
  目标: <5分钟, ≥99%, 100%

监控告警健康度:
  □ freshness-alert执行率: ___%
  □ quality-checker执行率: ___%
  □ 告警准确率: ___%
  目标: ≥99%, ≥99%, ≥95%

系统性能:
  □ Cloud Run p95响应: ___秒
  □ BigQuery p95查询: ___秒
  □ 错误率: ___%
  目标: <3秒, <10秒, <1%

成本:
  □ 实际日成本: $___ 
  □ 预计月成本: $___
  □ vs预算: ___%
  目标: ≤$20/月
```

---

## 🎯 观察期原则

### 原则1: 只观察，不改动 ⭐⭐⭐

```yaml
可以做:
  ✅ 查看日志
  ✅ 查询数据
  ✅ 生成报告
  ✅ 分析性能
  
不可以做:
  ❌ 修改代码
  ❌ 调整配置
  ❌ 部署新服务
  ❌ 启动新项目
```

---

### 原则2: 记录一切 ⭐⭐⭐

```yaml
记录内容:
  ✅ 所有检查命令
  ✅ 所有检查结果
  ✅ 所有发现的问题
  ✅ 所有观察到的现象
  
记录方式:
  - 保存到VERIFICATION/20251004_observation/
  - 保存到VERIFICATION/20251005_observation/
  - 保存到VERIFICATION/20251006_observation/
  - 命名规范: YYYYMMDD_HHMM_description.md
```

---

### 原则3: 基于数据决策 ⭐⭐⭐

```yaml
决策依据:
  ✅ 实际监控数据
  ✅ 统计分析结果
  ✅ 历史数据对比
  
决策禁忌:
  ❌ 基于感觉
  ❌ 基于假设
  ❌ 基于局部数据
```

---

## 📋 应急预案

### 场景1: 数据采集中断

**判断标准**:
- 超过10分钟无新数据
- drawsguard-api-collector日志显示错误

**应急措施**:
```bash
# 1. 检查Cloud Run服务状态
gcloud run services describe drawsguard-api-collector \
  --platform=managed --region=us-central1 --project=wprojectl

# 2. 检查最近日志
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=drawsguard-api-collector AND \
  severity>=WARNING" \
  --limit=20 --format=json --project=wprojectl

# 3. 手动触发采集
curl -X POST https://drawsguard-api-collector-rjysxlgksq-uc.a.run.app/collect \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"

# 4. 如需要，重启服务
gcloud run services update drawsguard-api-collector \
  --platform=managed --region=us-central1 --project=wprojectl \
  --update-env-vars=RESTART_TIME=$(date +%s)
```

---

### 场景2: 数据同步失败

**判断标准**:
- pc28.draws延迟超过15分钟
- data-sync-service日志显示错误

**应急措施**:
```bash
# 1. 检查服务状态
gcloud run services describe data-sync-service \
  --platform=managed --region=us-central1 --project=wprojectl

# 2. 手动触发同步
curl -X POST https://data-sync-service-rjysxlgksq-uc.a.run.app/sync \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"

# 3. 检查IAM权限
gcloud projects get-iam-policy wprojectl \
  --flatten="bindings[].members" \
  --filter="bindings.members:data-sync-service@wprojectl.iam.gserviceaccount.com"
```

---

### 场景3: 监控告警失效

**判断标准**:
- 超过10分钟无告警检查记录
- freshness-alert-checker无响应

**应急措施**:
```bash
# 1. 手动执行监控检查
curl -X POST https://freshness-alert-checker-rjysxlgksq-uc.a.run.app/check \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"

# 2. 检查Cloud Scheduler
gcloud scheduler jobs describe freshness-alert-check-5min \
  --location=us-central1 --project=wprojectl
```

---

## 📁 文档结构

```
VERIFICATION/
├── 20251003_day3_complete/
│   ├── OBSERVATION_PERIOD_PLAN.md （本文档）
│   ├── PREDICTION_SYSTEM_RECOVERY_DECISION.md
│   └── PREDICTION_SYSTEM_STOP_ROOT_CAUSE.md
│
├── 20251004_observation/
│   ├── system_baseline.md （初始状态记录）
│   ├── morning_check_0800.md
│   ├── noon_check_1200.md
│   ├── evening_check_2000.md
│   └── day1_summary.md
│
├── 20251005_observation/
│   ├── morning_check_0800.md
│   ├── noon_check_1200.md
│   ├── evening_check_2000.md
│   └── day2_summary.md
│
└── 20251006_observation/
    ├── COMPREHENSIVE_REPORT.md （综合评估报告）
    └── DECISION_MEETING_NOTES.md （决策会议记录）
```

---

## 🎯 成功标准

### 观察期成功的标准

```yaml
必须达成（P0）:
  ✅ 2天内无系统中断（可用性≥99.9%）
  ✅ 数据采集每日≥320期（完整率≥80%）
  ✅ 数据同步成功率≥95%
  ✅ 无P0级别错误

期望达成（P1）:
  📋 数据采集每日≥380期（完整率≥95%）
  📋 数据同步成功率≥99%
  📋 监控告警正常运行
  📋 成本在预算内

理想达成（P2）:
  🌟 数据采集每日≥400期（完整率100%）
  🌟 数据同步成功率100%
  🌟 告警准确率≥95%
  🌟 性能超出预期
```

---

## 🎓 观察期教训（提前记录）

### 教训10: 观察期是必要的投资 ⭐⭐⭐

```yaml
为什么需要观察期:
  - 刚修复的系统需要验证
  - 新部署的服务需要稳定
  - 数据完整性需要确认
  - 成本需要实际验证

观察期价值:
  - 及早发现问题（成本低）
  - 建立信心（数据支撑）
  - 避免连锁故障（风险控制）
  - 优化调整（性能提升）

教训:
  不要急于启动新项目！
  先确保现有系统稳定！
  观察期是必要的投资，不是浪费时间！
```

---

**观察期计划完成！**

**下一步：立即执行任务1.1（记录当前系统状态）**




# 🏥 数据库与采集系统健康检查报告
# Database & Collection System Health Check Report

**检查时间**: 2025-10-07 09:01 (Asia/Shanghai)  
**检查人**: AI Assistant  
**审核人**: 项目总指挥大人

---

## 📊 **执行摘要 / Executive Summary**

### ✅ **系统总体状态**: 良好（需优化）

| 系统模块 | 状态 | 评分 | 主要问题 |
|---------|------|------|---------|
| **BigQuery数据库** | ✅ 正常 | 85/100 | 存在数据重复 |
| **Cloud Run采集服务** | ✅ 运行中 | 90/100 | 无明显问题 |
| **Cloud Scheduler定时任务** | ⚠️ 配置混乱 | 60/100 | 7个任务，部分重复 |
| **数据质量** | ⚠️ 需改进 | 70/100 | 7.64%连续重复率 |
| **采集频率** | ✅ 正常 | 95/100 | 99.58%在5分钟内 |

---

## 📈 **数据库状态分析 / Database Status Analysis**

### 1. 数据规模

```
总期数: 5,027期
覆盖时间: 2025-09-24 ~ 2025-10-07
覆盖天数: 12天
平均每日: 419期/天
```

**评估**: ✅ 数据积累正常

### 2. 每日数据完整性

| 日期 | 期数 | 期号范围 | 无效数据 | 状态 |
|-----|------|---------|---------|------|
| 2025-10-07 | 170 | 3344129-3344272 | 0 | ⚠️ 当前采集中 |
| 2025-10-06 | 463 | 3343727-3344128 | 0 | ✅ 完整 |
| 2025-10-05 | 480 | 3343325-3343726 | 0 | ✅ 完整 |
| 2025-10-04 | 409 | 3342923-3343324 | 0 | ✅ 完整 |
| 2025-10-03 | 415 | 3342521-3342922 | 0 | ✅ 完整 |
| 2025-10-02 | 265 | 3342256-3342520 | 0 | ⚠️ 数据偏少 |
| 2025-10-01 | 401 | 3341854-3342255 | 0 | ✅ 完整 |

**发现**:
- ✅ **无无效数据** - 所有记录的`numbers`字段都完整
- ⚠️ **每日期数波动大** - 从265期到539期不等
- 📊 **平均约419期/天** - 与理论324期不符，需调查

---

## 🚨 **关键问题：数据重复 / Critical Issue: Data Duplication**

### 重复数据统计

```sql
发现重复数据:
- 期号 3342895: 重复8次 🚨
- 期号 3342894: 重复4次 ⚠️
- 其他8个期号: 重复2次
```

**根本原因分析**:

根据记忆[[memory:9561274]]，这是已知问题：

> **数据重复是10月3日连续率降至91.81%的主要原因（29次重复）**
> 
> 开奖停止后API持续返回最后一期导致重复，必须插入前检查期号是否存在，
> 使用MERGE而非INSERT，重复>10次触发告警

**当前状况**:
- ✅ 主代码已使用`MERGE`语句（`_insert_draw_with_merge`函数）
- ⚠️ 但仍存在重复数据（可能是历史遗留）
- ⚠️ 最严重的是期号3342895重复8次

**建议措施**:

1. **立即去重** - 清理历史重复数据
2. **增强监控** - 添加重复数据告警
3. **验证MERGE** - 确认MERGE逻辑生效
4. **添加唯一约束** - 在`period`字段上（如果可能）

---

## 🔍 **伪随机信号异常 / Pseudo-Random Signal Anomaly**

### 连续相同期号统计（最近7天）

```
总期数: 2,880期
连续相同: 220次
连续率: 7.639%
```

**理论vs实际对比**:

| 指标 | 理论值（真随机） | 实际值 | 偏移倍数 | 结论 |
|-----|----------------|--------|---------|------|
| 连续相同概率 | 0.1% (1/1000) | **7.639%** | **76.4倍** | 🚨 **极度异常** |

**这比我们在文档中报告的0.4%高出19倍！**

**分析**:

1. 🚨 **数据重复导致** - 部分是数据库重复记录（如3342895重复8次）
2. 🚨 **上游API问题** - 开奖停止后持续返回最后一期
3. ⚠️ **真实伪随机偏移** - 扣除重复后，仍可能有较高的连续率

**紧急行动**:

1. **去重后重新统计** - 排除数据库重复的影响
2. **分时段分析** - 查看23:58-00:02停止时段的重复情况
3. **更新文档数据** - 使用去重后的真实数据

---

## ⏱️ **采集频率分析 / Collection Frequency Analysis**

### 采集间隔分布（最近7天）

| 间隔类型 | 期数 | 占比 | 评估 |
|---------|------|------|------|
| ≤150秒（2.5分钟） | 1,542 | 53.54% | ✅ 优秀 |
| 180-300秒（5分钟） | 1,322 | 45.90% | ✅ 正常 |
| 300-600秒（轻微延迟） | 3 | 0.10% | ✅ 可接受 |
| >600秒（严重延迟） | 12 | 0.42% | ⚠️ 需调查 |

**结论**: ✅ **99.58%的数据在5分钟内采集，性能优秀**

**12次严重延迟原因**:
- 可能是系统维护
- 可能是网络波动
- 可能是上游API短暂不可用

**建议**: 添加延迟告警，>10分钟无新数据时发送通知

---

## 🔧 **Cloud Scheduler任务分析 / Scheduler Jobs Analysis**

### 当前运行的7个任务

| 任务名称 | 频率 | 状态 | 上次执行 | 评估 |
|---------|------|------|---------|------|
| `betting-recorder-predict-job` | 每3分钟 | ✅ ENABLED | 2025-10-07 01:00 | ⚠️ 下注逻辑，建议删除 |
| `betting-recorder-settle-job` | 每3分钟 | ✅ ENABLED | 2025-10-07 01:00 | ⚠️ 下注逻辑，建议删除 |
| `central-data-sync-job` | 每1分钟 | ✅ ENABLED | 2025-10-07 01:01 | ⚠️ 频率过高 |
| `drawsguard-sentinel-scheduler` | 每5分钟 | ✅ ENABLED | 2025-10-07 01:00 | ✅ 保留（监控） |
| `drawsguard-smart-collector-job` | 每1分钟 | ✅ ENABLED | 2025-10-07 01:01 | ✅ 保留（采集） |
| `trigger-betting-recorder-predict` | 每3分钟 | ✅ ENABLED | 2025-10-07 01:00 | ⚠️ 下注逻辑，建议删除 |
| `trigger-draws-collector` | 每5分钟 | ✅ ENABLED | 2025-10-07 01:00 | ✅ 保留（采集） |

**发现的问题**:

1. 🚨 **存在下注相关任务** - 3个任务涉及`betting-recorder`
   - 根据项目定位，应删除所有下注逻辑
   - 违反"不涉及下注和资金管理"的原则

2. ⚠️ **任务功能重复** - `drawsguard-smart-collector-job`（1分钟）和`trigger-draws-collector`（5分钟）
   - 两个都是采集任务，可能导致重复采集
   - 建议只保留一个

3. ⚠️ **频率过高** - `central-data-sync-job`每1分钟执行一次
   - 可能造成不必要的资源消耗
   - 建议调整为3-5分钟

---

## 📊 **最近采集数据质量检查 / Recent Data Quality Check**

### 最近20期数据

```
期号范围: 3344254 - 3344272
时间范围: 2025-10-06 23:20 - 2025-10-07 00:23 (Asia/Shanghai)
采集间隔: 150秒或270秒交替
开奖号码: 全部有效，无异常
```

**采集间隔模式**:

```
270秒 → 150秒 → 270秒 → 150秒 → ...
```

**分析**:
- ✅ 符合上游API的2.5分钟和4.5分钟交替模式
- ✅ 数据采集稳定
- ⚠️ 发现期号3344259重复2次（gap_seconds=0）

---

## 🎯 **优化建议 / Optimization Recommendations**

### 🔴 **P0级 - 紧急（立即处理）**

#### 1. 删除所有下注相关任务

```bash
# 删除3个下注相关的Scheduler任务
gcloud scheduler jobs delete betting-recorder-predict-job --location=us-central1 --quiet
gcloud scheduler jobs delete betting-recorder-settle-job --location=us-central1 --quiet
gcloud scheduler jobs delete trigger-betting-recorder-predict --location=us-central1 --quiet

# 删除相关的Cloud Run服务
gcloud run services delete betting-recorder --region=us-central1 --quiet
```

**理由**: 
- 违反项目定位（不涉及下注）
- 违反法律合规要求
- 可能误导用户

#### 2. 清理重复数据

```sql
-- 创建去重视图
CREATE OR REPLACE VIEW `wprojectl.drawsguard.draws_dedup_v` AS
SELECT * EXCEPT(row_num)
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY period ORDER BY created_at DESC) as row_num
  FROM `wprojectl.drawsguard.draws`
)
WHERE row_num = 1;

-- 或者直接删除重复数据（保留最新的）
DELETE FROM `wprojectl.drawsguard.draws`
WHERE (period, created_at) NOT IN (
  SELECT period, MAX(created_at)
  FROM `wprojectl.drawsguard.draws`
  GROUP BY period
);
```

#### 3. 添加重复数据告警

在`main.py`的`_insert_draw_with_merge`函数中添加：

```python
if query_job.num_dml_affected_rows == 0:
    # 重复数据，记录告警
    logging.warning(f"Duplicate draw detected: period={row['period']}")
    # 可选：发送Telegram告警
```

---

### 🟡 **P1级 - 重要（本周内处理）**

#### 4. 优化Scheduler任务配置

**建议配置**:

| 任务 | 当前频率 | 建议频率 | 理由 |
|-----|---------|---------|------|
| `drawsguard-smart-collector-job` | 1分钟 | **保持** | 实时采集 |
| `trigger-draws-collector` | 5分钟 | **删除** | 功能重复 |
| `central-data-sync-job` | 1分钟 | **3分钟** | 降低成本 |
| `drawsguard-sentinel-scheduler` | 5分钟 | **保持** | 监控告警 |

```bash
# 删除重复的采集任务
gcloud scheduler jobs delete trigger-draws-collector --location=us-central1 --quiet

# 调整sync任务频率
gcloud scheduler jobs update http central-data-sync-job \
  --location=us-central1 \
  --schedule="*/3 * * * *"
```

#### 5. 添加数据质量监控

创建监控视图：

```sql
-- 每日数据质量监控视图
CREATE OR REPLACE VIEW `wprojectl.drawsguard.daily_quality_metrics_v` AS
WITH daily_stats AS (
  SELECT 
    DATE(timestamp, 'Asia/Shanghai') as date,
    COUNT(*) as total_draws,
    COUNT(DISTINCT period) as unique_draws,
    COUNT(*) - COUNT(DISTINCT period) as duplicate_count,
    ROUND(COUNT(DISTINCT period) * 100.0 / COUNT(*), 2) as uniqueness_rate,
    MIN(period) as first_period,
    MAX(period) as last_period,
    COUNTIF(numbers IS NULL OR ARRAY_LENGTH(numbers) != 3) as invalid_count
  FROM `wprojectl.drawsguard.draws`
  GROUP BY date
)
SELECT 
  *,
  CASE 
    WHEN uniqueness_rate < 90 THEN '🚨 严重'
    WHEN uniqueness_rate < 95 THEN '⚠️ 警告'
    ELSE '✅ 正常'
  END as quality_status
FROM daily_stats
ORDER BY date DESC;
```

#### 6. 创建数据完整性检查脚本

```python
# tools/check_data_integrity.py
"""
数据完整性检查工具
- 检查重复数据
- 检查采集间隔
- 检查连续相同率
- 生成每日报告
"""
import logging
from google.cloud import bigquery

def check_duplicates(bq_client, date):
    """检查指定日期的重复数据"""
    query = f"""
    SELECT period, COUNT(*) as count
    FROM `wprojectl.drawsguard.draws`
    WHERE DATE(timestamp, 'Asia/Shanghai') = '{date}'
    GROUP BY period
    HAVING COUNT(*) > 1
    """
    # 实现检查逻辑
    pass

def check_consecutive_rate(bq_client, days=7):
    """检查连续相同率（去重后）"""
    query = """
    WITH dedup AS (
      SELECT DISTINCT period, numbers
      FROM `wprojectl.drawsguard.draws`
      WHERE DATE(timestamp, 'Asia/Shanghai') >= DATE_SUB(CURRENT_DATE('Asia/Shanghai'), INTERVAL @days DAY)
    ),
    consecutive AS (
      SELECT 
        period,
        numbers,
        LAG(numbers) OVER (ORDER BY period) as prev_numbers
      FROM dedup
    )
    SELECT 
      COUNT(*) as total,
      COUNTIF(TO_JSON_STRING(numbers) = TO_JSON_STRING(prev_numbers)) as same,
      ROUND(COUNTIF(TO_JSON_STRING(numbers) = TO_JSON_STRING(prev_numbers)) * 100.0 / COUNT(*), 3) as rate
    FROM consecutive
    """
    # 实现检查逻辑
    pass
```

---

### 🟢 **P2级 - 优化（有空时处理）**

#### 7. 优化表结构

**当前表结构**:
- ✅ 已有分区（`timestamp`字段，按天）
- ✅ 已有聚类（`period`字段）
- ⚠️ 缺少唯一约束（BigQuery不支持PRIMARY KEY）

**建议**:
1. 确保`period`字段建立索引（通过聚类已实现）
2. 考虑使用`MERGE`代替所有`INSERT`
3. 定期清理老数据（保留1年）

#### 8. 添加性能指标

```sql
-- 采集性能指标视图
CREATE OR REPLACE VIEW `wprojectl.drawsguard.collection_performance_v` AS
WITH intervals AS (
  SELECT 
    period,
    timestamp,
    TIMESTAMP_DIFF(timestamp, LAG(timestamp) OVER (ORDER BY period), SECOND) as gap_seconds
  FROM `wprojectl.drawsguard.draws`
  WHERE DATE(timestamp, 'Asia/Shanghai') >= DATE_SUB(CURRENT_DATE('Asia/Shanghai'), INTERVAL 7 DAY)
)
SELECT 
  DATE(timestamp, 'Asia/Shanghai') as date,
  COUNT(*) as total_periods,
  ROUND(AVG(gap_seconds), 1) as avg_gap_seconds,
  ROUND(STDDEV(gap_seconds), 1) as stddev_gap_seconds,
  MIN(gap_seconds) as min_gap,
  MAX(gap_seconds) as max_gap,
  APPROX_QUANTILES(gap_seconds, 100)[OFFSET(50)] as median_gap,
  APPROX_QUANTILES(gap_seconds, 100)[OFFSET(95)] as p95_gap,
  COUNTIF(gap_seconds > 600) as severe_delays
FROM intervals
WHERE gap_seconds IS NOT NULL
GROUP BY date
ORDER BY date DESC;
```

---

## 📋 **执行清单 / Action Checklist**

### ✅ 立即执行（今天）

- [ ] 1. **删除所有下注相关任务** (betting-recorder-*)
- [ ] 2. **清理重复数据** (CREATE VIEW draws_dedup_v)
- [ ] 3. **添加重复数据告警** (main.py修改)
- [ ] 4. **验证MERGE逻辑** (检查_insert_draw_with_merge)

### ✅ 本周执行

- [ ] 5. **删除重复的采集任务** (trigger-draws-collector)
- [ ] 6. **调整sync任务频率** (central-data-sync-job: 1min → 3min)
- [ ] 7. **创建数据质量监控视图** (daily_quality_metrics_v)
- [ ] 8. **去重后重新统计连续率** (更新PSEUDO_RANDOM_EVIDENCE.md)

### ✅ 有空时执行

- [ ] 9. **创建数据完整性检查脚本** (tools/check_data_integrity.py)
- [ ] 10. **添加性能指标视图** (collection_performance_v)
- [ ] 11. **定期数据备份策略** (BigQuery → GCS)
- [ ] 12. **添加Grafana监控面板** (可视化数据质量)

---

## 📊 **成本分析 / Cost Analysis**

### 当前成本估算

| 服务 | 配置 | 月成本（USD） | 备注 |
|-----|------|-------------|------|
| BigQuery 存储 | ~1GB | $0.02 | 5,027期 × 200字节 |
| BigQuery 查询 | ~10GB/月 | $0.05 | 按需查询 |
| Cloud Run (collector) | min=1, max=3 | $1.50 | 每5分钟调用一次 |
| Cloud Scheduler | 7个任务 | $0.35 | $0.05/任务/月 |
| **总计** | - | **$1.92/月** | ✅ 非常经济 |

**优化后预计成本**: **$1.20/月** （删除3个betting任务）

---

## 🎯 **总结 / Summary**

### ✅ **优点**

1. ✅ 数据采集稳定（99.58%在5分钟内）
2. ✅ 无无效数据（所有记录完整）
3. ✅ Cloud Run服务运行正常
4. ✅ 成本控制优秀（<$2/月）

### ⚠️ **问题**

1. 🚨 **存在下注相关任务** - 违反项目定位
2. 🚨 **数据重复严重** - 7.64%连续重复率（远超理论0.1%）
3. ⚠️ **Scheduler任务混乱** - 7个任务，部分功能重复
4. ⚠️ **缺少监控告警** - 无自动化数据质量检查

### 📈 **改进后预期**

- ✅ 连续重复率：7.64% → <1%（去重+优化）
- ✅ 任务数量：7个 → 3个（精简）
- ✅ 成本：$1.92/月 → $1.20/月（优化）
- ✅ 数据质量：70分 → 95分（监控+告警）

---

**报告生成时间**: 2025-10-07 09:30 (Asia/Shanghai)  
**下次检查时间**: 2025-10-08 09:00  
**审批**: 待项目总指挥大人批准执行

---

## 附录：快速修复脚本

```bash
#!/bin/bash
# quick_fix.sh - 快速修复脚本

set -euo pipefail

echo "🚀 开始执行快速修复..."

# 1. 删除下注相关任务
echo "1️⃣ 删除下注相关任务..."
gcloud scheduler jobs delete betting-recorder-predict-job --location=us-central1 --quiet || true
gcloud scheduler jobs delete betting-recorder-settle-job --location=us-central1 --quiet || true
gcloud scheduler jobs delete trigger-betting-recorder-predict --location=us-central1 --quiet || true

# 2. 删除重复采集任务
echo "2️⃣ 删除重复采集任务..."
gcloud scheduler jobs delete trigger-draws-collector --location=us-central1 --quiet || true

# 3. 创建去重视图
echo "3️⃣ 创建去重视图..."
bq query --use_legacy_sql=false --location=us-central1 '
CREATE OR REPLACE VIEW `wprojectl.drawsguard.draws_dedup_v` AS
SELECT * EXCEPT(row_num)
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY period ORDER BY created_at DESC) as row_num
  FROM `wprojectl.drawsguard.draws`
)
WHERE row_num = 1
'

echo "✅ 快速修复完成！"
```


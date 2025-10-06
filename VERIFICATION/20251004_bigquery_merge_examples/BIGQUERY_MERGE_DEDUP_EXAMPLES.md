# 🔄 BigQuery MERGE语句去重处理指南

**作者**: 15年数据架构专家
**日期**: 2025-10-04
**版本**: v1.0

---

## 📋 目录

1. [基础MERGE语法](#基础merge语法)
2. [简单去重示例](#简单去重示例)
3. [高级去重策略](#高级去重策略)
4. [时间戳去重](#时间戳去重)
5. [复合键去重](#复合键去重)
6. [PC28开奖数据去重](#pc28开奖数据去重)
7. [最佳实践](#最佳实践)

---

## 🎯 基础MERGE语法

### 基本结构
```sql
MERGE `project.dataset.target_table` AS T
USING `project.dataset.source_table` AS S
ON T.primary_key = S.primary_key
WHEN MATCHED THEN
  UPDATE SET
    column1 = S.column1,
    column2 = S.column2,
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (primary_key, column1, column2, created_at)
  VALUES (S.primary_key, S.column1, S.column2, CURRENT_TIMESTAMP())
```

---

## 🔄 简单去重示例

### 基于ROW_NUMBER去重
```sql
MERGE `wprojectl.pc28.draws` AS T
USING (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY period
      ORDER BY timestamp DESC, created_at DESC
    ) as rn
  FROM `wprojectl.pc28.draws_raw`
  WHERE period IS NOT NULL
) AS S
ON T.period = S.period
WHEN MATCHED AND S.rn = 1 THEN
  UPDATE SET
    numbers = S.numbers,
    sum_value = S.sum_value,
    big_small = S.big_small,
    odd_even = S.odd_even,
    timestamp = S.timestamp,
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED AND S.rn = 1 THEN
  INSERT (
    period, numbers, sum_value, big_small, odd_even,
    timestamp, created_at, updated_at
  )
  VALUES (
    S.period, S.numbers, S.sum_value, S.big_small, S.odd_even,
    S.timestamp, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
  )
```

### 去重逻辑说明
1. **ROW_NUMBER()**: 为每个period分组，按时间戳降序排列
2. **S.rn = 1**: 只处理排名第一的记录（最新或最早）
3. **双重条件**: 既匹配主键，又确保是去重后的记录

---

## ⚡ 高级去重策略

### 策略1: 保留最新记录
```sql
WITH ranked_data AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY period, numbers  -- 复合去重键
      ORDER BY timestamp DESC
    ) as rn
  FROM `wprojectl.pc28.draws_raw`
  WHERE period IS NOT NULL
    AND numbers IS NOT NULL
)
MERGE `wprojectl.pc28.draws` AS T
USING ranked_data AS S
ON T.period = S.period AND T.numbers = S.numbers
WHEN MATCHED AND S.rn = 1 THEN
  UPDATE SET
    timestamp = S.timestamp,
    sum_value = S.sum_value,
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED AND S.rn = 1 THEN
  INSERT (period, numbers, sum_value, timestamp, created_at)
  VALUES (S.period, S.numbers, S.sum_value, S.timestamp, CURRENT_TIMESTAMP())
```

### 策略2: 保留最早记录
```sql
WITH ranked_data AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY period
      ORDER BY timestamp ASC  -- 最早记录优先
    ) as rn
  FROM `wprojectl.pc28.draws_raw`
)
MERGE `wprojectl.pc28.draws` AS T
USING ranked_data AS S
ON T.period = S.period
WHEN MATCHED AND S.rn > 1 THEN
  DELETE  -- 删除重复的旧记录
WHEN NOT MATCHED AND S.rn = 1 THEN
  INSERT (period, numbers, sum_value, timestamp, created_at)
  VALUES (S.period, S.numbers, S.sum_value, S.timestamp, CURRENT_TIMESTAMP())
```

---

## ⏰ 时间戳去重

### 基于时间戳的智能去重
```sql
MERGE `wprojectl.pc28.draws` AS T
USING (
  WITH time_ranked AS (
    SELECT
      *,
      ROW_NUMBER() OVER (
        PARTITION BY period
        ORDER BY
          -- 优先级：开奖时间 → 采集时间 → 创建时间
          COALESCE(kjtime_timestamp, timestamp, created_at) DESC,
          COALESCE(created_at, timestamp) DESC
      ) as rn
    FROM `wprojectl.pc28.draws_raw`
    WHERE period IS NOT NULL
  )
  SELECT * FROM time_ranked WHERE rn = 1
) AS S
ON T.period = S.period
WHEN MATCHED THEN
  UPDATE SET
    timestamp = S.timestamp,
    numbers = S.numbers,
    sum_value = S.sum_value,
    big_small = S.big_small,
    odd_even = S.odd_even,
    kjtime = S.kjtime,
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (
    period, timestamp, numbers, sum_value, big_small, odd_even,
    kjtime, created_at, updated_at
  )
  VALUES (
    S.period, S.timestamp, S.numbers, S.sum_value, S.big_small, S.odd_even,
    S.kjtime, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
  )
```

---

## 🔑 复合键去重

### 多字段组合去重
```sql
MERGE `wprojectl.pc28_lab.score_ledger` AS T
USING (
  WITH deduped_orders AS (
    SELECT
      *,
      ROW_NUMBER() OVER (
        PARTITION BY period, market, stake_u  -- 期号+市场+金额去重
        ORDER BY created_at DESC
      ) as rn
    FROM `wprojectl.pc28_lab.orders_raw`
    WHERE period IS NOT NULL
      AND market IS NOT NULL
      AND stake_u > 0
  )
  SELECT * FROM deduped_orders WHERE rn = 1
) AS S
ON T.period = S.period AND T.market = S.market AND T.stake_u = S.stake_u
WHEN MATCHED THEN
  UPDATE SET
    p_win = S.p_win,
    outcome = S.outcome,
    pnl_u = S.pnl_u,
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (
    period, market, stake_u, p_win, outcome, pnl_u,
    day_id_cst, created_at, updated_at
  )
  VALUES (
    S.period, S.market, S.stake_u, S.p_win, S.outcome, S.pnl_u,
    CURRENT_DATE('Asia/Shanghai'), CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
  )
```

---

## 🎰 PC28开奖数据去重

### 完整开奖数据去重示例
```sql
-- 步骤1: 创建临时去重视图
CREATE OR REPLACE TABLE `wprojectl.pc28.draws_dedup_temp` AS
WITH ranked_draws AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY period
      ORDER BY
        -- 优先级排序：开奖时间 → API时间 → 采集时间
        COALESCE(kjtime_timestamp, api_server_time, timestamp) DESC,
        COALESCE(created_at, timestamp) DESC
    ) as rn,
    COUNT(*) OVER (PARTITION BY period) as dup_count
  FROM `wprojectl.pc28.draws_raw`
  WHERE period IS NOT NULL
    AND numbers IS NOT NULL
    AND sum_value IS NOT NULL
)
SELECT
  period,
  numbers,
  sum_value,
  big_small,
  odd_even,
  timestamp,
  kjtime,
  next_issue,
  award_countdown,
  api_server_time,
  clock_drift_ms,
  created_at,
  CURRENT_TIMESTAMP() as updated_at,
  dup_count
FROM ranked_draws
WHERE rn = 1;  -- 只保留最新记录

-- 步骤2: 使用MERGE更新主表
MERGE `wprojectl.pc28.draws` AS T
USING `wprojectl.pc28.draws_dedup_temp` AS S
ON T.period = S.period
WHEN MATCHED THEN
  UPDATE SET
    numbers = S.numbers,
    sum_value = S.sum_value,
    big_small = S.big_small,
    odd_even = S.odd_even,
    timestamp = S.timestamp,
    kjtime = S.kjtime,
    next_issue = S.next_issue,
    award_countdown = S.award_countdown,
    api_server_time = S.api_server_time,
    clock_drift_ms = S.clock_drift_ms,
    updated_at = S.updated_at
WHEN NOT MATCHED THEN
  INSERT (
    period, numbers, sum_value, big_small, odd_even,
    timestamp, kjtime, next_issue, award_countdown,
    api_server_time, clock_drift_ms, created_at, updated_at
  )
  VALUES (
    S.period, S.numbers, S.sum_value, S.big_small, S.odd_even,
    S.timestamp, S.kjtime, S.next_issue, S.award_countdown,
    S.api_server_time, S.clock_drift_ms, S.created_at, S.updated_at
  );

-- 步骤3: 清理临时表
DROP TABLE IF EXISTS `wprojectl.pc28.draws_dedup_temp`;
```

### 去重效果统计
```sql
-- 检查去重效果
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT period) as unique_periods,
  COUNT(*) - COUNT(DISTINCT period) as duplicate_count,
  AVG(dup_count) as avg_duplicates_per_period
FROM `wprojectl.pc28.draws_raw`
WHERE DATE(created_at, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai');
```

---

## ⚙️ 候选信号去重示例

### 候选信号复合去重
```sql
MERGE `wprojectl.pc28.candidates_today_base` AS T
USING (
  WITH ranked_candidates AS (
    SELECT
      *,
      ROW_NUMBER() OVER (
        PARTITION BY period, tier_candidate  -- 期号+市场去重
        ORDER BY p_star_ens DESC, ts_utc DESC  -- 概率最高，时间最新
      ) as rn
    FROM `wprojectl.pc28.candidates_raw`
    WHERE period IS NOT NULL
      AND tier_candidate IS NOT NULL
      AND p_star_ens >= 0.5  -- 只保留高质量信号
  )
  SELECT * FROM ranked_candidates WHERE rn = 1
) AS S
ON T.period = S.period AND T.tier_candidate = S.tier_candidate
WHEN MATCHED THEN
  UPDATE SET
    p_star_ens = S.p_star_ens,
    vote_ratio = S.vote_ratio,
    ts_utc = S.ts_utc,
    ts_cst = S.ts_cst,
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (
    day_id, period, session, tier_candidate, p_star_ens,
    vote_ratio, keyB, veto, ts_utc, ts_cst, created_at, updated_at
  )
  VALUES (
    S.day_id, S.period, S.session, S.tier_candidate, S.p_star_ens,
    S.vote_ratio, S.keyB, S.veto, S.ts_utc, S.ts_cst,
    CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
  )
```

---

## 🎯 订单去重示例

### 基于业务规则的订单去重
```sql
MERGE `wprojectl.pc28_lab.score_ledger` AS T
USING (
  WITH ranked_orders AS (
    SELECT
      *,
      ROW_NUMBER() OVER (
        PARTITION BY period, market, stake_u  -- 相同订单去重
        ORDER BY
          -- 优先级：预测概率 → 创建时间
          p_win DESC,
          created_at DESC
      ) as rn
    FROM `wprojectl.pc28_lab.orders_raw`
    WHERE period IS NOT NULL
      AND market IN ('oe', 'size')
      AND stake_u > 0
      AND p_win >= 0.5
  )
  SELECT * FROM ranked_orders WHERE rn = 1
) AS S
ON T.period = S.period AND T.market = S.market AND T.stake_u = S.stake_u
WHEN MATCHED THEN
  UPDATE SET
    p_win = S.p_win,
    outcome = COALESCE(T.outcome, 'pending'),  -- 保持已有结果
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (
    period, market, stake_u, p_win, outcome, pnl_u,
    day_id_cst, created_at, updated_at
  )
  VALUES (
    S.period, S.market, S.stake_u, S.p_win, 'pending', 0,
    CURRENT_DATE('Asia/Shanghai'), CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
  )
```

---

## 📊 去重效果监控

### 去重统计查询
```sql
-- 去重前后对比
WITH before_stats AS (
  SELECT
    'before' as stage,
    COUNT(*) as total_records,
    COUNT(DISTINCT period) as unique_periods,
    COUNT(*) - COUNT(DISTINCT period) as duplicates
  FROM `wprojectl.pc28.draws_raw`
  WHERE DATE(created_at, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
),
after_stats AS (
  SELECT
    'after' as stage,
    COUNT(*) as total_records,
    COUNT(DISTINCT period) as unique_periods,
    COUNT(*) - COUNT(DISTINCT period) as duplicates
  FROM `wprojectl.pc28.draws`
  WHERE DATE(created_at, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
)
SELECT * FROM before_stats
UNION ALL
SELECT * FROM after_stats;
```

### 重复率趋势监控
```sql
-- 按小时统计重复率
SELECT
  FORMAT_TIMESTAMP('%Y-%m-%d %H:00:00', created_at) as hour_window,
  COUNT(*) as total_records,
  COUNT(DISTINCT period) as unique_periods,
  ROUND((COUNT(*) - COUNT(DISTINCT period)) / COUNT(*) * 100, 2) as duplicate_rate
FROM `wprojectl.pc28.draws_raw`
WHERE DATE(created_at, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
GROUP BY hour_window
ORDER BY hour_window DESC;
```

---

## ⚡ 性能优化建议

### 1. 分区表优化
```sql
-- 使用分区表提高MERGE性能
MERGE `wprojectl.pc28.draws_partitioned` AS T
USING (
  SELECT * FROM `wprojectl.pc28.draws_raw`
  WHERE DATE(timestamp, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
) AS S
ON T.period = S.period
-- ... MERGE逻辑
```

### 2. 批量处理优化
```sql
-- 大数据集分批处理
DECLARE batch_size INT64 DEFAULT 1000;
DECLARE offset INT64 DEFAULT 0;

WHILE offset < (SELECT COUNT(*) FROM `wprojectl.pc28.draws_raw`) DO
  MERGE `wprojectl.pc28.draws` AS T
  USING (
    SELECT * FROM `wprojectl.pc28.draws_raw`
    ORDER BY period
    LIMIT batch_size OFFSET offset
  ) AS S
  ON T.period = S.period
  WHEN MATCHED THEN UPDATE SET updated_at = CURRENT_TIMESTAMP()
  WHEN NOT MATCHED THEN INSERT (period, created_at) VALUES (S.period, CURRENT_TIMESTAMP());

  SET offset = offset + batch_size;
END WHILE;
```

### 3. 索引优化
```sql
-- 为去重键创建索引
CREATE INDEX idx_period_timestamp ON `wprojectl.pc28.draws_raw`(period, timestamp DESC);
CREATE INDEX idx_period_market_stake ON `wprojectl.pc28_lab.orders_raw`(period, market, stake_u);
```

---

## 🔍 故障排除

### 常见错误及解决方案

#### 1. Streaming Buffer错误
```sql
-- 错误：UPDATE or DELETE statement over table would affect rows in the streaming buffer
-- 解决方案：等待缓冲区刷新或使用非streaming表
SELECT * FROM `wprojectl.pc28.draws`
WHERE DATE(timestamp, 'Asia/Shanghai') >= DATE_SUB(CURRENT_DATE('Asia/Shanghai'), INTERVAL 90 MINUTE);
```

#### 2. 内存不足错误
```sql
-- 解决方案：减少批次大小或使用临时表
CREATE TEMP TABLE temp_dedup AS
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY period ORDER BY timestamp DESC) as rn
  FROM `wprojectl.pc28.draws_raw`
)
SELECT * FROM ranked WHERE rn = 1;

MERGE `wprojectl.pc28.draws` AS T
USING temp_dedup AS S
ON T.period = S.period
-- ... MERGE逻辑
```

#### 3. 数据类型不匹配
```sql
-- 解决方案：显式转换数据类型
MERGE `wprojectl.pc28.draws` AS T
USING (
  SELECT
    CAST(period AS STRING) as period,
    CAST(sum_value AS INT64) as sum_value,
    -- ... 其他字段
  FROM `wprojectl.pc28.draws_raw`
) AS S
ON T.period = S.period
-- ... MERGE逻辑
```

---

## 📈 监控与告警

### 去重成功率监控
```sql
-- 计算去重成功率
SELECT
  FORMAT_DATE('%Y-%m-%d', DATE(created_at, 'Asia/Shanghai')) as date,
  COUNT(*) as before_dedup,
  COUNT(DISTINCT period) as after_dedup,
  ROUND(COUNT(DISTINCT period) / COUNT(*) * 100, 2) as dedup_rate
FROM `wprojectl.pc28.draws_raw`
WHERE DATE(created_at, 'Asia/Shanghai') >= DATE_SUB(CURRENT_DATE('Asia/Shanghai'), INTERVAL 7 DAY)
GROUP BY date
ORDER BY date DESC;
```

### 异常重复告警
```sql
-- 检测异常高重复率
WITH daily_stats AS (
  SELECT
    DATE(created_at, 'Asia/Shanghai') as date,
    COUNT(*) as total,
    COUNT(DISTINCT period) as unique,
    ROUND((COUNT(*) - COUNT(DISTINCT period)) / COUNT(*) * 100, 2) as dup_rate
  FROM `wprojectl.pc28.draws_raw`
  GROUP BY date
)
SELECT *
FROM daily_stats
WHERE dup_rate > 10  -- 重复率超过10%告警
ORDER BY date DESC;
```

---

## 🎯 最佳实践总结

### ✅ 推荐做法
1. **使用ROW_NUMBER()** 进行去重排序
2. **复合条件判断**：主键匹配 + 去重条件
3. **保留最新记录**：按时间戳降序排列
4. **批量处理**：避免单次处理过多数据
5. **监控去重效果**：建立去重率指标

### ❌ 避免做法
1. **直接DELETE重复数据**：可能影响数据完整性
2. **忽略时间戳**：可能保留错误数据
3. **过度复杂去重逻辑**：影响性能和可维护性
4. **缺乏监控**：无法及时发现去重问题

### 📊 性能指标
- **去重率**: 目标 >95%
- **处理时间**: <30秒/万条记录
- **内存使用**: <1GB/百万条记录
- **异常率**: <1%

---

**更新日期**: 2025-10-04
**作者**: 15年数据架构专家
**版本**: v1.0

**使用说明**: 根据具体业务需求调整去重策略和字段，选择合适的去重键和排序规则。






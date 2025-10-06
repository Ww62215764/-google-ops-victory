-- 🔄 BigQuery MERGE去重修复方案
-- 用于解决当前系统数据一致性问题

-- ==========================================
-- 方案1: 候选信号去重修复
-- ==========================================

-- 步骤1: 诊断候选信号问题
SELECT
  'candidates_today_base' as table_name,
  COUNT(*) as total_records,
  COUNT(DISTINCT period) as unique_periods,
  COUNT(*) - COUNT(DISTINCT period) as duplicates,
  MIN(created_at) as earliest,
  MAX(created_at) as latest
FROM `wprojectl.pc28.candidates_today_base`
WHERE day_id = CURRENT_DATE('Asia/Shanghai');

-- 步骤2: 清理无效候选信号（无开奖对应的信号）
MERGE `wprojectl.pc28.candidates_today_base` AS T
USING (
  SELECT c.*
  FROM `wprojectl.pc28.candidates_today_base` c
  LEFT JOIN `wprojectl.pc28.draws` d ON c.period = d.period
  WHERE c.day_id = CURRENT_DATE('Asia/Shanghai')
    AND d.period IS NULL  -- 没有对应开奖的候选信号
) AS S
ON T.period = S.period AND T.tier_candidate = S.tier_candidate
WHEN MATCHED THEN
  DELETE;  -- 删除无效候选信号

-- ==========================================
-- 方案2: 订单数据去重修复
-- ==========================================

-- 步骤1: 分析订单数据质量
WITH order_analysis AS (
  SELECT
    period,
    market,
    stake_u,
    p_win,
    outcome,
    day_id_cst,
    created_at,
    COUNT(*) OVER (PARTITION BY period, market, stake_u) as dup_count,
    ROW_NUMBER() OVER (
      PARTITION BY period, market, stake_u
      ORDER BY created_at DESC
    ) as rn
  FROM `wprojectl.pc28_lab.score_ledger`
  WHERE day_id_cst = CURRENT_DATE('Asia/Shanghai')
)
SELECT
  COUNT(*) as total_orders,
  COUNT(DISTINCT CONCAT(period, '_', market, '_', stake_u)) as unique_orders,
  SUM(CASE WHEN dup_count > 1 THEN dup_count - 1 ELSE 0 END) as total_duplicates,
  AVG(dup_count) as avg_duplicates_per_order
FROM order_analysis;

-- 步骤2: 清理重复订单（保留最新记录）
MERGE `wprojectl.pc28_lab.score_ledger` AS T
USING (
  WITH ranked_orders AS (
    SELECT
      *,
      ROW_NUMBER() OVER (
        PARTITION BY period, market, stake_u
        ORDER BY created_at DESC
      ) as rn
    FROM `wprojectl.pc28_lab.score_ledger`
    WHERE day_id_cst = CURRENT_DATE('Asia/Shanghai')
  )
  SELECT * FROM ranked_orders WHERE rn = 1
) AS S
ON T.period = S.period
  AND T.market = S.market
  AND T.stake_u = S.stake_u
WHEN MATCHED AND S.rn > 1 THEN
  DELETE  -- 删除旧的重复订单
WHEN MATCHED AND S.rn = 1 THEN
  UPDATE SET
    p_win = S.p_win,
    outcome = S.outcome,
    pnl_u = S.pnl_u,
    updated_at = CURRENT_TIMESTAMP();

-- ==========================================
-- 方案3: 数据一致性修复
-- ==========================================

-- 步骤1: 验证订单与开奖的对应关系
CREATE OR REPLACE TABLE `wprojectl.pc28_lab.order_validation_temp` AS
WITH order_draws AS (
  SELECT
    o.period,
    o.market,
    o.stake_u,
    o.p_win,
    o.outcome,
    d.odd_even,
    d.big_small,
    CASE
      WHEN o.market = 'oe' AND d.odd_even = 'ODD' THEN 'win'
      WHEN o.market = 'oe' AND d.odd_even = 'EVEN' THEN 'lose'
      WHEN o.market = 'size' AND d.big_small = 'BIG' THEN 'win'
      WHEN o.market = 'size' AND d.big_small = 'SMALL' THEN 'lose'
      ELSE 'unknown'
    END as expected_outcome,
    CASE
      WHEN outcome = expected_outcome THEN 'correct'
      ELSE 'mismatch'
    END as validation_status
  FROM `wprojectl.pc28_lab.score_ledger` o
  INNER JOIN `wprojectl.pc28.draws` d ON o.period = d.period
  WHERE o.day_id_cst = CURRENT_DATE('Asia/Shanghai')
    AND o.outcome != 'pending'
)
SELECT * FROM order_draws;

-- 步骤2: 修复订单结果（如果开奖已出但订单结果错误）
MERGE `wprojectl.pc28_lab.score_ledger` AS T
USING `wprojectl.pc28_lab.order_validation_temp` AS S
ON T.period = S.period AND T.market = S.market
WHEN MATCHED AND T.outcome != 'pending' AND S.validation_status = 'mismatch' THEN
  UPDATE SET
    outcome = S.expected_outcome,
    pnl_u = CASE
      WHEN S.expected_outcome = 'win' THEN stake_u
      WHEN S.expected_outcome = 'lose' THEN -stake_u
      ELSE pnl_u
    END,
    updated_at = CURRENT_TIMESTAMP();

-- 步骤3: 清理临时表
DROP TABLE IF EXISTS `wprojectl.pc28_lab.order_validation_temp`;

-- ==========================================
-- 方案4: 建立去重监控
-- ==========================================

-- 创建去重监控视图
CREATE OR REPLACE VIEW `wprojectl.pc28.dedup_monitor` AS
WITH daily_stats AS (
  SELECT
    DATE(created_at, 'Asia/Shanghai') as date,
    'draws' as table_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT period) as unique_records,
    COUNT(*) - COUNT(DISTINCT period) as duplicates
  FROM `wprojectl.pc28.draws`
  GROUP BY date, table_type

  UNION ALL

  SELECT
    day_id as date,
    'candidates' as table_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT period) as unique_records,
    COUNT(*) - COUNT(DISTINCT period) as duplicates
  FROM `wprojectl.pc28.candidates_today_base`
  GROUP BY day_id, table_type

  UNION ALL

  SELECT
    day_id_cst as date,
    'orders' as table_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT CONCAT(period, '_', market, '_', stake_u)) as unique_records,
    COUNT(*) - COUNT(DISTINCT CONCAT(period, '_', market, '_', stake_u)) as duplicates
  FROM `wprojectl.pc28_lab.score_ledger`
  GROUP BY day_id_cst, table_type
)
SELECT
  date,
  table_type,
  total_records,
  unique_records,
  duplicates,
  ROUND(duplicates / total_records * 100, 2) as duplicate_rate
FROM daily_stats
WHERE date >= DATE_SUB(CURRENT_DATE('Asia/Shanghai'), INTERVAL 7 DAY)
ORDER BY date DESC, table_type;

-- ==========================================
-- 方案5: 候选信号生成修复
-- ==========================================

-- 测试候选信号生成（手动触发）
SELECT
  'Testing candidate generation' as test,
  COUNT(*) as current_candidates
FROM `wprojectl.pc28.candidates_today_base`
WHERE day_id = CURRENT_DATE('Asia/Shanghai');

-- 如果候选信号仍为0，检查生成逻辑
-- 可能的修复：重新部署pc28-e2e-function-fixed或检查调度配置

-- ==========================================
-- 执行完成检查
-- ==========================================

-- 最终验证
SELECT
  'Final validation' as check_type,
  (SELECT COUNT(*) FROM `wprojectl.pc28.draws` WHERE DATE(created_at, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')) as draws_count,
  (SELECT COUNT(*) FROM `wprojectl.pc28.candidates_today_base` WHERE day_id = CURRENT_DATE('Asia/Shanghai')) as candidates_count,
  (SELECT COUNT(*) FROM `wprojectl.pc28_lab.score_ledger` WHERE day_id_cst = CURRENT_DATE('Asia/Shanghai')) as orders_count,
  (SELECT COUNT(*) FROM `wprojectl.pc28.dedup_monitor` WHERE date = CURRENT_DATE('Asia/Shanghai')) as monitor_records
UNION ALL
SELECT
  'Dedup status' as check_type,
  NULL as draws_count,
  NULL as candidates_count,
  NULL as orders_count,
  COUNT(*) as monitor_records
FROM `wprojectl.pc28.dedup_monitor`
WHERE date = CURRENT_DATE('Asia/Shanghai')
  AND duplicate_rate < 5;  -- 去重率>95%






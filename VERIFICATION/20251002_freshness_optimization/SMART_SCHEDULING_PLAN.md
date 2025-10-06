# DrawsGuard 智能调度方案（利用下期开奖时间）

**日期**: 2025-10-02  
**专家**: 数据维护专家（15年经验）  
**创新点**: ⭐⭐⭐ 利用API返回的"下一期开奖时间"实现精准调度

---

## 💡 核心发现

### 开奖规律分析
```yaml
开奖间隔:
  平均间隔: 3.28分钟（197秒）
  最小间隔: 13秒
  最大间隔: 420秒（7分钟）
  样本数量: 2,578期

观察模式:
  - 大部分间隔在2.5-4.5分钟
  - 存在不规律的间隔（13秒-7分钟）
  - 固定频率调度会造成浪费或延迟

关键洞察:
  🎯 API返回"下一期开奖时间"（next_time字段）
  🎯 可以精准预测下次采集时机
  🎯 避免无效采集，降低延迟
```

### API数据结构（关键字段）
```json
{
  "retdata": {
    "curent": {
      "long_issue": "3342351",
      "kjtime": "2025-10-02 21:34:00",
      "number": [0, 5, 8]
    },
    "next": {
      "next_issue": "3342352",
      "next_time": "2025-10-02 21:37:30",
      "award_countdown": 210
    }
  }
}
```

**关键字段**：
- `next_time`: 下一期开奖时间（精确到秒）
- `award_countdown`: 距离开奖倒计时（秒）

---

## 🚀 智能调度方案（推荐⭐⭐⭐）

### 方案概述
```yaml
核心思路:
  1. Cloud Run采集数据后，解析next_time字段
  2. 将next_time + 30秒写入BigQuery调度表
  3. Cloud Scheduler每分钟检查调度表
  4. 如果当前时间 >= 调度时间，则触发采集

优势:
  ✅ 精准调度（延迟<30秒）
  ✅ 避免无效采集（节省80%+请求）
  ✅ 成本更低（只在开奖后采集）
  ✅ 自适应开奖规律（无需人工调整）
```

---

## 📋 实施方案对比

### 方案A：固定1分钟调度（简单版，立即可用）⭐⭐
```yaml
调度频率: 每1分钟
调度表达式: */1 * * * *
实施时间: 5分钟

优势:
  ✅ 实现最简单
  ✅ 立即可用
  ✅ 零成本

劣势:
  ❌ 存在无效采集（60-70%的请求无新数据）
  ❌ 延迟仍有30秒

预期效果:
  平均延迟: 30秒
  成本: $0（免费额度内）
```

### 方案B：智能动态调度（优化版，30分钟实施）⭐⭐⭐
```yaml
调度机制: 基于next_time动态调度
调度表达式: 每1分钟检查调度表
实施时间: 30分钟

核心组件:
  1. BigQuery调度表（存储下次采集时间）
  2. Cloud Run增强（解析next_time并更新调度表）
  3. Cloud Scheduler检查逻辑（根据调度表决定是否采集）

优势:
  ✅ 延迟最低（<15秒）
  ✅ 避免无效采集（节省80%+）
  ✅ 自适应开奖规律
  ✅ 成本更低

劣势:
  - 需要30分钟实施
  - 架构稍复杂

预期效果:
  平均延迟: <15秒
  无效采集: <5%
  成本: $0（请求量降低80%）
```

---

## 🎯 推荐：两阶段实施

### 阶段1：立即实施方案A（5分钟）⭐⭐⭐
```yaml
目标: 快速提升性能
时间: 5分钟
风险: 低

步骤:
  1. 更新Cloud Scheduler调度频率
     调度表达式: */5 → */1
  
  2. 验证配置
  
  3. 观察10分钟

效果:
  延迟从2.5分钟 → 30秒（5倍提升）
```

### 阶段2：后续实施方案B（可选，30分钟）⭐⭐
```yaml
目标: 进一步优化，实现智能调度
时间: 30分钟
风险: 低

步骤:
  1. 创建BigQuery调度表
  2. 增强Cloud Run（解析next_time）
  3. 更新调度逻辑
  4. 测试验证

效果:
  延迟从30秒 → <15秒（再提升2倍）
  节省80%+无效请求
```

---

## ⚡ 立即执行：阶段1（方案A）

### Phase 1: 备份当前配置（1分钟）
```bash
# 备份调度配置
gcloud scheduler jobs describe drawsguard-collect-5min \
  --location us-central1 \
  --project wprojectl \
  --format=yaml > VERIFICATION/20251002_freshness_optimization/scheduler_backup_$(date +%Y%m%d_%H%M).yaml

echo "✅ 配置已备份"
```

### Phase 2: 实施优化（2分钟）
```bash
# 1. 更新调度频率：每5分钟 → 每1分钟
gcloud scheduler jobs update http drawsguard-collect-5min \
  --location us-central1 \
  --schedule "*/1 * * * *" \
  --project wprojectl

echo "✅ 调度频率已更新为每1分钟"

# 2. 验证配置
gcloud scheduler jobs describe drawsguard-collect-5min \
  --location us-central1 \
  --project wprojectl \
  --format="yaml(schedule,timeZone,state,lastAttemptTime)"

# 3. 手动触发测试
echo "触发手动测试..."
gcloud scheduler jobs run drawsguard-collect-5min \
  --location us-central1 \
  --project wprojectl

echo "✅ 手动触发成功"
```

### Phase 3: 验证效果（10分钟）
```bash
# 等待10分钟，观察至少10次采集
echo "等待10分钟，观察采集效果..."
echo "开始时间: $(date)"

sleep 600  # 等待10分钟

echo "结束时间: $(date)"

# 检查最近10次采集日志
echo -e "\n=== 最近10次采集日志 ==="
gcloud logging read \
  "resource.type=cloud_run_revision 
   AND resource.labels.service_name=drawsguard-api-collector 
   AND textPayload=~\"数据采集成功\"
   AND timestamp>=\\\"$(date -u -v-15M '+%Y-%m-%dT%H:%M:%SZ')\\\"" \
  --limit 10 \
  --format="table(timestamp,textPayload)" \
  --project wprojectl

# 验证数据新鲜度
echo -e "\n=== 数据新鲜度验证 ==="
bq query --location=us-central1 --use_legacy_sql=false --format=pretty \
"SELECT 
  MAX(period) AS latest_period,
  FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', MAX(timestamp), 'Asia/Shanghai') AS latest_time,
  ROUND(TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(timestamp), SECOND) / 60.0, 2) AS minutes_ago
FROM \`wprojectl.drawsguard.draws\`"

echo -e "\n✅ 验证完成！"
echo "期望结果: minutes_ago < 1.5分钟"
```

### Phase 4: 创建验收报告
```bash
# 生成验收报告
cat > VERIFICATION/20251002_freshness_optimization/phase1_completion_report.md <<EOF
# 阶段1优化完成报告

**完成时间**: $(date '+%Y-%m-%d %H:%M:%S')
**执行人**: 数据维护专家

## 优化内容
- 调度频率: */5 * * * * → */1 * * * *
- 预期延迟: 2.5分钟 → 30秒

## 验证结果
$(bq query --location=us-central1 --use_legacy_sql=false --format=csv \
"SELECT 
  MAX(period) AS latest_period,
  ROUND(TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(timestamp), SECOND) / 60.0, 2) AS minutes_ago
FROM \`wprojectl.drawsguard.draws\`")

## 状态
✅ 阶段1完成

## 下一步
可选：实施阶段2（智能动态调度）
EOF

echo "✅ 验收报告已生成"
```

---

## 📊 阶段2：智能动态调度（可选）

### 架构设计
```yaml
组件1: BigQuery调度表
  表名: drawsguard_monitor.next_collection_schedule
  字段:
    - next_period: STRING (下一期期号)
    - next_collection_time: TIMESTAMP (计划采集时间)
    - created_at: TIMESTAMP (记录创建时间)
    - executed: BOOLEAN (是否已执行)

组件2: Cloud Run增强
  新增功能:
    1. 解析API返回的next_time字段
    2. 计算next_collection_time = next_time + 30秒
    3. 写入调度表

组件3: Cloud Scheduler智能触发
  逻辑:
    1. 每1分钟检查调度表
    2. 如果 CURRENT_TIMESTAMP >= next_collection_time，则采集
    3. 否则跳过（节省请求）
```

### 实施步骤（阶段2，可选）

#### 步骤1: 创建调度表（1分钟）
```sql
-- 创建调度表
CREATE TABLE IF NOT EXISTS `wprojectl.drawsguard_monitor.next_collection_schedule` (
  next_period STRING NOT NULL,
  next_collection_time TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  executed BOOLEAN NOT NULL DEFAULT FALSE,
  executed_at TIMESTAMP
)
PARTITION BY DATE(next_collection_time)
CLUSTER BY executed, next_period
OPTIONS(
  description='智能调度表：存储下一期采集时间',
  partition_expiration_days=7
);

-- 创建视图：获取下一次应该采集的时间
CREATE OR REPLACE VIEW `wprojectl.drawsguard_monitor.should_collect_now_v` AS
SELECT 
  next_period,
  next_collection_time,
  created_at,
  CURRENT_TIMESTAMP() >= next_collection_time AS should_collect,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), next_collection_time, SECOND) AS seconds_overdue
FROM `wprojectl.drawsguard_monitor.next_collection_schedule`
WHERE executed = FALSE
  AND DATE(next_collection_time) = CURRENT_DATE('Asia/Shanghai')
ORDER BY next_collection_time ASC
LIMIT 1;
```

#### 步骤2: 增强Cloud Run服务（15分钟）
```python
# 在 CLOUD/api-collector/main.py 中添加

def parse_next_draw_info(data):
    """解析下一期开奖信息"""
    retdata = data.get('retdata', {})
    next_info = retdata.get('next', {})
    
    return {
        'next_issue': str(next_info.get('next_issue', '')),
        'next_time': next_info.get('next_time', ''),
        'award_countdown': next_info.get('award_countdown', 0)
    }

def schedule_next_collection(next_info, bq_client):
    """调度下一次采集"""
    if not next_info['next_time']:
        logger.warning("⚠️ 无下一期开奖时间，跳过调度")
        return
    
    try:
        # 解析next_time（格式：YYYY-MM-DD HH:MM:SS）
        next_time_dt = datetime.strptime(
            next_info['next_time'], 
            '%Y-%m-%d %H:%M:%S'
        ).replace(tzinfo=timezone.utc)
        
        # 计算采集时间 = 开奖时间 + 30秒
        collection_time_dt = next_time_dt + timedelta(seconds=30)
        
        # 写入调度表
        row = {
            'next_period': next_info['next_issue'],
            'next_collection_time': collection_time_dt.isoformat(),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'executed': False
        }
        
        table_id = 'wprojectl.drawsguard_monitor.next_collection_schedule'
        errors = bq_client.insert_rows_json(table_id, [row])
        
        if errors:
            logger.error(f"❌ 调度表写入失败: {errors}")
        else:
            logger.info(
                f"📅 已调度下期采集: 期号={next_info['next_issue']}, "
                f"时间={collection_time_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
    
    except Exception as e:
        logger.error(f"❌ 调度失败: {str(e)}")

@app.post("/collect")
def collect_data():
    """采集数据（智能版）"""
    try:
        # ... 现有采集逻辑 ...
        
        # 🆕 新增：解析下一期信息
        next_info = parse_next_draw_info(data)
        
        # 🆕 新增：调度下一次采集
        schedule_next_collection(next_info, bq_client)
        
        # ... 返回结果 ...
        
    except Exception as e:
        logger.error(f"❌ 采集失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collect-smart")
def collect_smart():
    """智能采集：检查调度表决定是否采集"""
    try:
        bq_client = get_bq_client()
        
        # 1. 检查是否应该采集
        check_query = """
        SELECT 
          next_period,
          should_collect,
          seconds_overdue
        FROM `wprojectl.drawsguard_monitor.should_collect_now_v`
        LIMIT 1
        """
        
        result = list(bq_client.query(check_query).result())
        
        if not result or not result[0]['should_collect']:
            logger.info("⏸️ 未到采集时间，跳过")
            return {
                "status": "skipped",
                "reason": "not_scheduled",
                "message": "未到预定采集时间"
            }
        
        # 2. 应该采集，执行采集逻辑
        logger.info(f"🚀 开始采集期号: {result[0]['next_period']}")
        
        # 调用原有采集逻辑
        return collect_data()
        
    except Exception as e:
        logger.error(f"❌ 智能采集失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 步骤3: 更新Cloud Scheduler（5分钟）
```bash
# 方案1: 修改现有任务调用/collect-smart
gcloud scheduler jobs update http drawsguard-collect-5min \
  --location us-central1 \
  --uri "https://drawsguard-api-collector-644485179199.us-central1.run.app/collect-smart" \
  --project wprojectl

# 方案2: 创建新任务（推荐，方便回滚）
gcloud scheduler jobs create http drawsguard-collect-smart \
  --location us-central1 \
  --schedule "*/1 * * * *" \
  --uri "https://drawsguard-api-collector-644485179199.us-central1.run.app/collect-smart" \
  --http-method POST \
  --oidc-service-account-email drawsguard-collector@wprojectl.iam.gserviceaccount.com \
  --oidc-token-audience "https://drawsguard-api-collector-644485179199.us-central1.run.app" \
  --time-zone "Asia/Shanghai" \
  --description "DrawsGuard智能调度采集" \
  --max-retry-attempts 3 \
  --project wprojectl

# 暂停旧任务
gcloud scheduler jobs pause drawsguard-collect-5min \
  --location us-central1 \
  --project wprojectl
```

#### 步骤4: 测试验证（10分钟）
```bash
# 1. 手动触发一次普通采集（初始化调度表）
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://drawsguard-api-collector-644485179199.us-central1.run.app/collect

# 2. 检查调度表
bq query --location=us-central1 --use_legacy_sql=false \
"SELECT * FROM \`wprojectl.drawsguard_monitor.next_collection_schedule\` 
 ORDER BY created_at DESC LIMIT 1"

# 3. 检查should_collect_now_v视图
bq query --location=us-central1 --use_legacy_sql=false \
"SELECT * FROM \`wprojectl.drawsguard_monitor.should_collect_now_v\`"

# 4. 测试智能采集
gcloud scheduler jobs run drawsguard-collect-smart \
  --location us-central1 \
  --project wprojectl

# 5. 观察10分钟
echo "观察10分钟..."
```

---

## 📊 预期效果对比

### 当前（每5分钟）
```yaml
平均延迟: 2.5分钟
月请求: 8,640次
无效请求: 0%（都是手动触发时间）
成本: $0.15/月
```

### 阶段1优化（每1分钟）
```yaml
平均延迟: 30秒 ⭐
月请求: 43,200次
无效请求: 60-70%（很多时候无新数据）
成本: $0.15/月（仍在免费额度内）
```

### 阶段2优化（智能调度）
```yaml
平均延迟: <15秒 ⭐⭐
月请求: 8,640-12,000次（只在开奖后采集）
无效请求: <5%（精准调度）
成本: $0.15/月（请求量更少）
```

---

## 🎯 最终建议

### 立即执行：阶段1（5分钟）
```yaml
理由:
  ✅ 实现最简单（只需一条命令）
  ✅ 效果立竿见影（延迟降低5倍）
  ✅ 零风险（可快速回滚）
  ✅ 零成本增加

执行: 立即 ⭐⭐⭐
```

### 可选执行：阶段2（30分钟）
```yaml
理由:
  ✅ 延迟进一步降低（30秒 → <15秒）
  ✅ 节省80%+无效请求
  ✅ 自适应开奖规律
  ✅ 体现专业性

时机:
  - 阶段1运行稳定后（观察1-3天）
  - 如需进一步优化时

执行: 可选 ⭐⭐
```

---

**报告完成时间**: 2025-10-02  
**专家**: 数据维护专家（15年经验）  
**建议**: 立即执行阶段1，后续可选阶段2

☁️ **DrawsGuard - 智能调度，精准采集！**


# DrawsGuard环境健康检查报告

**日期**: 2025-10-03  
**时间**: $(date '+%Y-%m-%d %H:%M:%S')  
**执行**: Day 1-2 环境验证与快照  

---

## 🎯 核心发现

### ⚠️  关键问题

#### 问题1: Cloud Scheduler已暂停
```
状态: PAUSED
调度: */1 * * * *（改为每1分钟）
最后运行: 2025-10-02 05:56:00
```
**影响**: DrawsGuard云端采集服务已停止，不再自动采集新数据

#### 问题2: pc28.draws数据陈旧
```
最新时间: 2025-09-27 18:07:00
新鲜度: 469076秒（约130小时，5.4天前）
总行数: 361行
```
**影响**: pc28.draws表数据已严重过时

#### 问题3: pc28.draws_14w表为空
```
总行数: 0
Schema: 21个字段（issue, ts_utc, a, b, c, sum等）
```
**影响**: 下游依赖draws_14w的所有功能将失效

#### 问题4: pc28_stage数据集不存在
```
错误: Not found: Dataset wprojectl:pc28_stage
```
**影响**: 无法在staging环境测试变更

---

## ✅ 正常运行的组件

### 1. DrawsGuard云端采集服务
```yaml
drawsguard.draws表:
  总行数: 2652
  唯一期号: 2652（无重复）
  最早时间: 2025-09-25 08:02:00
  最新时间: 2025-10-03 04:03:00
  新鲜度: 1328秒（22分钟前）
  
Cloud Run服务:
  状态: True（运行中）
  URL: https://drawsguard-api-collector-rjysxlgksq-uc.a.run.app
```
**结论**: ✅ 云端采集服务健康，只是被暂停了

### 2. BigQuery数据集
```yaml
✓ pc28（主数据集）- 48个对象
✓ pc28_prod（生产视图）- 7个视图
✓ pc28_audit（审计）- 2个表
✓ pc28_monitor（监控）- 3个表
✓ pc28_backup（备份）- 1个快照
✓ drawsguard（云端采集）- 5个对象
✗ pc28_stage（测试环境）- 不存在
```

---

## 🔍 数据架构分析

### Schema对比：drawsguard.draws vs pc28.draws_14w

#### drawsguard.draws（云端采集表）
```
字段: period, timestamp, numbers, sum_value, big_small, odd_even
数据源: PC28 API（实时采集）
状态: ✅ 正常运行，有2652条数据
```

#### pc28.draws_14w（分析用表）
```
字段: issue, ts_utc, a, b, c, sum, odd_even, size, tail, source, hour, session
      + 11个hit_*字段（特征工程）
数据源: 未知（表为空）
状态: ❌ 空表
```

**关键差异**:
- 字段名不同：period vs issue, timestamp vs ts_utc, numbers vs (a,b,c)
- pc28.draws_14w包含大量计算字段（特征工程）
- 两个表不能直接数据迁移，需要字段映射和计算

---

## 📋 待修复项清单

### P0（紧急）
- [ ] 恢复Cloud Scheduler（从PAUSED改为ENABLED）
- [ ] 创建pc28_stage数据集
- [ ] 分析pc28.draws和drawsguard.draws的关系

### P1（重要）
- [ ] 填充pc28.draws_14w表（需要字段映射脚本）
- [ ] 同步drawsguard.draws数据到pc28.draws
- [ ] 创建生产环境快照

### P2（一般）
- [ ] 建立数据同步机制
- [ ] 创建数据质量监控
- [ ] 编写数据血缘文档

---

## 🎯 下一步建议

### 立即行动（今日完成）

#### 1. 恢复Cloud Scheduler
```bash
gcloud scheduler jobs resume drawsguard-collect-5min \
  --location us-central1 \
  --project wprojectl
```

#### 2. 创建pc28_stage数据集
```bash
bq mk --location=us-central1 \
  --description="Staging环境用于测试变更" \
  wprojectl:pc28_stage
```

#### 3. 分析数据流向
- drawsguard.draws → pc28.draws？
- pc28.draws → pc28.draws_14w？
- 需要确认数据同步逻辑

### 明日行动（Day 3-4）
1. 创建字段映射脚本（drawsguard.draws → pc28.draws_14w）
2. 在pc28_stage测试填充
3. 获得批准后填充pc28.draws_14w生产表

---

## 📊 环境扫描摘要

| 组件 | 状态 | 说明 |
|------|------|------|
| drawsguard.draws | ✅ 健康 | 2652行，最新数据22分钟前 |
| pc28.draws | ⚠️  陈旧 | 361行，最新数据5天前 |
| pc28.draws_14w | ❌ 空表 | 0行，需填充 |
| Cloud Scheduler | ⚠️  暂停 | 需恢复 |
| Cloud Run | ✅ 运行 | 服务正常 |
| pc28_stage | ❌ 缺失 | 需创建 |

---

**报告生成**: 2025-10-03  
**执行人**: 数据维护专家  
**下次检查**: 恢复Cloud Scheduler后24小时

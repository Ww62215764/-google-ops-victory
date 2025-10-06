# 生产环境快照清单

**创建时间**: 2025-10-03 12:27  
**快照标签**: snapshot_20251003_1227  
**目的**: Day 1-2环境验证前的安全备份  

---

## 📦 已备份的表

### 1. drawsguard_draws_snapshot_20251003_1227
```yaml
源表: wprojectl:drawsguard.draws
备份表: wprojectl:pc28_backup.drawsguard_draws_snapshot_20251003_1227
行数: 2653（截至备份时）
最新数据: 2025-10-03 04:24:00（期号：3342733）
分区: DAY (field: timestamp, expirationMs: 31536000000)
```

### 2. pc28_draws_snapshot_20251003_1227
```yaml
源表: wprojectl:pc28.draws
备份表: wprojectl:pc28_backup.pc28_draws_snapshot_20251003_1227
行数: 361
最新数据: 2025-09-27 18:07:00（期号：3340419）
分区: DAY (field: timestamp, expirationMs: 31536000000)
```

---

## 🔄 恢复命令

### 恢复drawsguard.draws
```bash
# 完整恢复
bq cp --location=us-central1 \
  wprojectl:pc28_backup.drawsguard_draws_snapshot_20251003_1227 \
  wprojectl:drawsguard.draws

# 或恢复到新表
bq cp --location=us-central1 \
  wprojectl:pc28_backup.drawsguard_draws_snapshot_20251003_1227 \
  wprojectl:drawsguard.draws_restored
```

### 恢复pc28.draws
```bash
# 完整恢复
bq cp --location=us-central1 \
  wprojectl:pc28_backup.pc28_draws_snapshot_20251003_1227 \
  wprojectl:pc28.draws

# 或恢复到新表
bq cp --location=us-central1 \
  wprojectl:pc28_backup.pc28_draws_snapshot_20251003_1227 \
  wprojectl:pc28.draws_restored
```

---

## 📊 快照统计

| 快照表 | 源表行数 | 数据新鲜度 | 快照大小 |
|--------|---------|-----------|---------|
| drawsguard_draws_snapshot | 2653 | 3分钟前 | ~500KB |
| pc28_draws_snapshot | 361 | 5天前 | ~70KB |

---

## ⚠️  重要说明

1. **快照用途**: 仅用于紧急恢复，不是长期备份策略
2. **保留时间**: 根据表分区过期设置（365天）
3. **下次快照**: 在执行重大变更前创建
4. **验证**: 所有快照已验证可访问

---

## 🎯 下次快照时机

建议在以下时机创建快照：
- [ ] 填充pc28.draws_14w之前
- [ ] 同步drawsguard.draws到pc28.draws之前
- [ ] 任何DROP/TRUNCATE操作之前
- [ ] 每周定期备份（建议周日凌晨）

---

**创建人**: 数据维护专家  
**审核**: 项目总指挥大人  
**状态**: ✅ 快照已验证





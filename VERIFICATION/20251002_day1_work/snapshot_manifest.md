# 生产环境快照清单

**创建时间**: 2025-10-02T11:08:59+08:00
**快照标签**: snapshot_20251002_1108
**执行人**: 数据维护专家

---

## 已备份的表

### 1. pc28.draws
- **目标**: wprojectl:pc28_backup.draws_snapshot_20251002_1108
- **状态**: ✅ 成功
- **行数**: 361行
- **最新数据**: 2025-09-27 18:07:00

---

## 恢复命令

如需恢复，执行以下命令:

```bash
# 恢复draws表
bq cp --location=us-central1 \
  wprojectl:pc28_backup.draws_snapshot_20251002_1108 \
  wprojectl:pc28.draws \
  --force

# 验证恢复
bq query --location=us-central1 --use_legacy_sql=false \
"SELECT COUNT(*), MAX(timestamp) FROM \`wprojectl.pc28.draws\`"
```

---

## 快照保留策略

- **保留期限**: 30天
- **删除日期**: 2025-11-01
- **自动清理**: 需配置（待实施）

---

**快照完成时间**: 2025-10-02T11:08:59+08:00

# 项目深度净化行动计划 🧹

> **执行日期**: 2025-10-07  
> **项目**: DrawsGuard / Google Ops Victory  
> **目标**: 清理冗余文件，优化项目结构，提升代码质量

---

## 📊 当前项目状态

### 规模统计
- **Python文件**: 7,581个
- **Markdown文档**: 142个
- **项目总大小**: 517MB
- **Git仓库大小**: 32MB
- **临时/缓存文件**: **8,636个** ⚠️

### 主要问题
1. ❌ 大量临时文件和缓存未清理
2. ❌ 存在重复的测试目录
3. ❌ 错误命名的项目目录
4. ❌ 50+个历史VERIFICATION目录
5. ❌ Git仓库可能包含冗余历史

---

## 🎯 清理方案（8个阶段）

### 阶段1️⃣: 清理临时文件和缓存 ⚡ **优先级：最高**

**目标**: 删除8,636个临时文件

**清理内容**:
```bash
# Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# macOS系统文件
find . -name ".DS_Store" -delete

# 日志文件（保留最近7天）
find . -name "*.log" -mtime +7 -delete

# 临时文件
find . -name "*.tmp" -delete
find . -name "*.temp" -delete
```

**预期效果**:
- 减少8,000+个文件
- 节省约50-100MB空间
- 加快Git操作速度

**风险**: 低 - 这些都是可重新生成的文件

---

### 阶段2️⃣: 删除重复的测试目录 🔄

**目标**: 移除根目录的冗余测试文件

**问题分析**:
```
❌ /Users/a606/谷歌运维/tests/
   - test_main.py
   - test_upstream_detector.py

✅ /Users/a606/谷歌运维/CLOUD/drawsguard-api-collector-fixed/tests/
   - test_main.py
   - test_upstream_detector.py
   - test_common.py
   - test_logging_config.py
```

**清理操作**:
```bash
# 删除根目录的tests/
rm -rf /Users/a606/谷歌运维/tests/
```

**预期效果**:
- 消除混淆
- 确保测试在正确位置运行

**风险**: 低 - 正确的测试文件在子目录中

---

### 阶段3️⃣: 清理错误命名的项目目录 📁

**目标**: 删除拼写错误的目录

**问题**:
```
❌ CLOUD/drawsguard--api-collector-fixed/  (双横线，错误)
✅ CLOUD/drawsguard-api-collector-fixed/   (单横线，正确)
```

**清理操作**:
```bash
rm -rf /Users/a606/谷歌运维/CLOUD/drawsguard--api-collector-fixed/
```

**预期效果**:
- 消除命名混淆
- 减少维护成本

**风险**: 低 - 仅包含1个测试文件，已在正确目录中

---

### 阶段4️⃣: 归档或删除旧的VERIFICATION目录 📦

**目标**: 整理50+个验证目录

**策略**:

#### 选项A: 压缩归档（推荐）
```bash
# 将所有VERIFICATION目录打包
cd /Users/a606/谷歌运维
tar -czf VERIFICATION_ARCHIVE_$(date +%Y%m%d).tar.gz VERIFICATION/
# 删除原目录
rm -rf VERIFICATION/
```

#### 选项B: 保留最近的，删除旧的
```bash
# 保留最近30天的验证记录
find VERIFICATION/ -type d -mtime +30 -exec rm -rf {} +
```

#### 选项C: 全部删除（激进）
```bash
rm -rf VERIFICATION/
```

**预期效果**:
- 节省100-200MB空间
- 简化项目结构

**风险**: 中 - 可能丢失历史审计记录（建议先归档）

**建议**: 选择选项A（压缩归档），保留历史但不占用工作目录

---

### 阶段5️⃣: 优化Git仓库 🔧

**目标**: 压缩Git仓库，提升性能

**操作**:
```bash
cd /Users/a606/谷歌运维

# 1. 清理不可达对象
git gc --aggressive --prune=now

# 2. 优化引用
git reflog expire --expire=now --all

# 3. 重新打包
git repack -Ad

# 4. 验证完整性
git fsck --full
```

**预期效果**:
- Git仓库从32MB减少到20MB左右
- 加快git操作速度
- 减少磁盘占用

**风险**: 低 - 标准Git维护操作

---

### 阶段6️⃣: 审计和清理云端资源 ☁️

**目标**: 清理不再使用的GCP资源

**审计内容**:

#### A. Cloud Storage Buckets
```bash
gsutil ls
# 检查每个bucket的用途和最后访问时间
gsutil du -sh gs://BUCKET_NAME
```

#### B. Cloud Run Services
```bash
gcloud run services list --platform=managed
# 检查未使用的服务
```

#### C. Cloud Scheduler Jobs
```bash
gcloud scheduler jobs list
# 检查是否有失效的定时任务
```

#### D. Secret Manager Secrets
```bash
gcloud secrets list
# 检查未使用的密钥
```

**清理策略**:
- 删除超过90天未访问的资源
- 删除测试/开发环境的临时资源
- 合并重复的配置

**预期效果**:
- 减少月度云费用
- 简化资源管理

**风险**: 中 - 需要仔细确认资源用途

---

### 阶段7️⃣: 代码质量扫描和重复代码检测 🔍

**目标**: 识别并消除重复代码

**工具**:

#### A. 重复代码检测
```bash
# 安装工具
pip install pylint radon

# 检测重复代码
pylint --disable=all --enable=duplicate-code .

# 或使用radon
radon cc . -a -nb
```

#### B. 死代码检测
```bash
# 安装vulture
pip install vulture

# 扫描未使用的代码
vulture . --min-confidence 80
```

#### C. 复杂度分析
```bash
# 使用radon分析圈复杂度
radon cc . -s -a
```

**清理策略**:
- 重构重复代码块（>10行重复）
- 删除未使用的函数和类
- 简化高复杂度函数（CC > 10）

**预期效果**:
- 提高代码可维护性
- 减少代码行数10-20%
- 降低Bug风险

**风险**: 中 - 需要仔细测试重构后的代码

---

### 阶段8️⃣: 依赖项审计和优化 📦

**目标**: 清理未使用的依赖

**审计工具**:
```bash
# 安装deptry（已使用）
pip install deptry

# 扫描未使用的依赖
deptry .

# 检查过期的依赖
pip list --outdated
```

**清理策略**:
1. 删除未使用的依赖
2. 更新过期的依赖（安全补丁）
3. 统一版本号（避免冲突）
4. 使用`requirements-lock.txt`锁定版本

**预期效果**:
- 减少依赖包数量
- 提升安全性
- 减少安装时间

**风险**: 低 - 有完整的测试覆盖

---

## 📋 执行检查清单

### 执行前
- [ ] 备份整个项目（Time Machine或手动备份）
- [ ] 确认Git状态干净（无未提交改动）
- [ ] 创建新分支进行清理工作
- [ ] 通知团队成员（如有）

### 执行中
- [ ] 按阶段顺序执行
- [ ] 每个阶段后运行测试
- [ ] 记录清理日志
- [ ] 提交每个阶段的改动

### 执行后
- [ ] 运行完整测试套件
- [ ] 验证项目功能正常
- [ ] 更新文档
- [ ] 推送到远程仓库

---

## ⚠️ 风险评估

| 阶段 | 风险等级 | 可逆性 | 建议 |
|------|---------|--------|------|
| 阶段1 | 🟢 低 | 高 | 立即执行 |
| 阶段2 | 🟢 低 | 高 | 立即执行 |
| 阶段3 | 🟢 低 | 高 | 立即执行 |
| 阶段4 | 🟡 中 | 中 | 先归档再删除 |
| 阶段5 | 🟢 低 | 高 | 立即执行 |
| 阶段6 | 🟡 中 | 低 | 仔细审计 |
| 阶段7 | 🟡 中 | 高 | 逐步重构 |
| 阶段8 | 🟢 低 | 高 | 立即执行 |

---

## 📊 预期收益

### 空间节省
- **临时文件清理**: -100MB
- **VERIFICATION归档**: -200MB
- **Git优化**: -12MB
- **总计**: **-312MB** (从517MB降至205MB)

### 性能提升
- Git操作速度: +50%
- 测试运行速度: +20%
- IDE索引速度: +30%

### 质量提升
- 代码行数: -15%
- 重复代码: -80%
- 依赖数量: -20%
- 测试覆盖率: 保持95.81%

---

## 🚀 执行建议

### 立即执行（低风险）
1. ✅ 阶段1: 清理临时文件
2. ✅ 阶段2: 删除重复测试目录
3. ✅ 阶段3: 清理错误命名目录
4. ✅ 阶段5: 优化Git仓库
5. ✅ 阶段8: 依赖项审计

### 谨慎执行（中风险）
6. ⚠️ 阶段4: VERIFICATION归档（先备份）
7. ⚠️ 阶段6: 云端资源清理（需审计）
8. ⚠️ 阶段7: 代码重构（需测试）

---

## 📝 执行日志

### 2025-10-07
- [ ] 阶段1: 清理临时文件 - 待执行
- [ ] 阶段2: 删除重复目录 - 待执行
- [ ] 阶段3: 清理错误命名 - 待执行
- [ ] 阶段4: VERIFICATION归档 - 待执行
- [ ] 阶段5: Git优化 - 待执行
- [ ] 阶段6: 云端清理 - 待执行
- [ ] 阶段7: 代码质量 - 待执行
- [ ] 阶段8: 依赖优化 - 待执行

---

**总指挥大人，请指示从哪个阶段开始执行！** 🫡

# 贡献指南 (Contributing Guide)

感谢您考虑为DrawsGuard API Collector项目做出贡献！🎉

---

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [测试要求](#测试要求)
- [提交规范](#提交规范)
- [问题报告](#问题报告)

---

## 🤝 行为准则

### 我们的承诺

为了营造一个开放和友好的环境，我们承诺：

- ✅ 使用友好和包容的语言
- ✅ 尊重不同的观点和经验
- ✅ 优雅地接受建设性批评
- ✅ 关注对社区最有利的事情
- ✅ 对其他社区成员表示同理心

### 不可接受的行为

- ❌ 使用性化的语言或图像
- ❌ 挑衅、侮辱或贬损性评论
- ❌ 公开或私下骚扰
- ❌ 未经许可发布他人的私人信息
- ❌ 其他不道德或不专业的行为

---

## 🚀 如何贡献

### 1. Fork仓库

点击GitHub页面右上角的"Fork"按钮，创建项目的副本。

### 2. 克隆到本地

```bash
git clone https://github.com/YOUR_USERNAME/-google-ops-victory.git
cd -google-ops-victory/CLOUD/drawsguard-api-collector-fixed
```

### 3. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

**分支命名规范：**
- `feature/xxx` - 新功能
- `fix/xxx` - Bug修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 代码重构
- `test/xxx` - 测试相关
- `chore/xxx` - 构建/工具相关

### 4. 进行开发

遵循[代码规范](#代码规范)和[测试要求](#测试要求)。

### 5. 提交改动

```bash
git add .
git commit -m "feat: add amazing feature"
```

遵循[提交规范](#提交规范)。

### 6. 推送到GitHub

```bash
git push origin feature/your-feature-name
```

### 7. 创建Pull Request

在GitHub上创建Pull Request，详细描述你的改动。

---

## 💻 开发流程

### 环境设置

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装开发工具
pip install black isort ruff pytest pytest-cov pytest-asyncio
```

### 开发前检查

```bash
# 1. 确保所有测试通过
pytest tests --disable-warnings -v

# 2. 检查代码覆盖率
pytest tests --cov=. --cov-report=term-missing --cov-fail-under=95

# 3. 运行代码格式化
black .
isort .

# 4. 运行linter
ruff check .
```

### 开发中

- 📝 **编写测试优先**：新功能必须先写测试
- 🔄 **频繁提交**：小步快跑，每个逻辑单元提交一次
- 📖 **更新文档**：代码改动同步更新文档
- ✅ **本地验证**：提交前确保所有测试通过

---

## 📏 代码规范

### Python代码风格

遵循 **PEP 8** 规范，使用以下工具强制执行：

#### Black (代码格式化)

```bash
# 格式化所有Python文件
black .

# 检查但不修改
black . --check
```

#### isort (Import排序)

```bash
# 排序所有imports
isort .

# 检查但不修改
isort . --check-only
```

#### Ruff (Linter)

```bash
# 检查代码问题
ruff check .

# 自动修复问题
ruff check . --fix
```

### 代码质量标准

✅ **必须遵守：**
- 函数/类必须有docstring
- 复杂逻辑必须有注释
- 变量命名清晰、有意义
- 避免魔法数字，使用常量
- 单个函数不超过50行
- 单个文件不超过500行

✅ **推荐实践：**
- 使用类型注解 (Type Hints)
- 遵循SOLID原则
- 优先使用组合而非继承
- 保持函数单一职责

❌ **禁止：**
- 硬编码敏感信息
- 使用`print()`调试（使用`logging`）
- 捕获异常后不处理
- 使用`import *`
- 修改全局状态

### 示例：良好的代码风格

```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 常量使用大写
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 10

def fetch_data_with_retry(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = MAX_RETRIES
) -> Optional[dict]:
    """
    从指定URL获取数据，支持重试机制。
    
    Args:
        url: 要请求的URL地址
        timeout: 请求超时时间（秒）
        retries: 最大重试次数
        
    Returns:
        成功时返回解析后的JSON数据，失败返回None
        
    Raises:
        ValueError: 当URL格式不正确时
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid URL: {url}")
    
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                logger.error(f"All {retries} attempts failed for {url}")
                return None
```

---

## 🧪 测试要求

### 测试覆盖率标准

- ✅ **最低要求**: 95%
- ✅ **核心模块**: 100%
- ✅ **新增代码**: 必须100%覆盖

### 测试类型

#### 1. 单元测试

测试单个函数/方法的行为：

```python
def test_parse_period_number():
    """测试期号解析功能"""
    assert parse_period("20251006001") == {
        "date": "20251006",
        "sequence": "001"
    }
```

#### 2. 集成测试

测试多个组件协作：

```python
def test_collect_and_store_data(mock_bq_client):
    """测试完整的采集和存储流程"""
    # 模拟API响应
    with patch("main.call_api_with_retry") as mock_api:
        mock_api.return_value = {"codeid": 10000, ...}
        
        # 执行采集
        result = collect_data()
        
        # 验证存储
        mock_bq_client.insert_rows_json.assert_called_once()
```

#### 3. 端到端测试

测试完整的用户场景：

```python
def test_api_endpoint_full_flow(client):
    """测试API端点的完整流程"""
    response = client.post("/collect")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

### 测试最佳实践

✅ **好的测试：**
- 测试名称清晰描述测试内容
- 每个测试只验证一个行为
- 使用fixture避免重复代码
- Mock外部依赖（API、数据库）
- 测试边界条件和异常情况

❌ **避免：**
- 测试依赖执行顺序
- 测试依赖外部状态
- 测试过于复杂难以理解
- 测试覆盖率作弊（空测试）

### 运行测试

```bash
# 运行所有测试
pytest tests -v

# 运行特定测试文件
pytest tests/test_main.py -v

# 运行特定测试函数
pytest tests/test_main.py::test_health_check -v

# 查看覆盖率
pytest tests --cov=. --cov-report=html
open htmlcov/index.html

# 只运行失败的测试
pytest --lf

# 并行运行测试（需要pytest-xdist）
pytest tests -n auto
```

---

## 📝 提交规范

使用 **Conventional Commits** 规范：

### 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type类型

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(api): add health check endpoint` |
| `fix` | Bug修复 | `fix(detector): correct stale detection logic` |
| `docs` | 文档更新 | `docs(readme): update installation guide` |
| `style` | 代码格式 | `style: format code with black` |
| `refactor` | 代码重构 | `refactor(client): simplify BigQuery client` |
| `test` | 测试相关 | `test(main): add tests for collect endpoint` |
| `chore` | 构建/工具 | `chore: update dependencies` |
| `perf` | 性能优化 | `perf(query): optimize BigQuery query` |
| `ci` | CI/CD | `ci: add GitHub Actions workflow` |

### Scope范围

可选，指明改动的范围：
- `api` - API端点
- `detector` - 上游检测器
- `client` - 客户端
- `test` - 测试
- `docs` - 文档
- `deps` - 依赖

### Subject主题

- 使用祈使句（"add"而非"added"）
- 首字母小写
- 结尾不加句号
- 不超过50个字符

### Body正文

- 详细描述改动内容
- 说明改动的原因
- 与之前行为的对比

### Footer页脚

- 关闭的Issue: `Closes #123`
- 破坏性变更: `BREAKING CHANGE: ...`

### 示例

```
feat(api): add circuit breaker for upstream stale detection

Implement a circuit breaker mechanism that detects when the upstream
API returns the same period number consecutively for M times in the
last N calls. This prevents duplicate data insertion and reduces
unnecessary API calls.

The threshold is configurable:
- M_THRESHOLD: 6 (consecutive identical periods)
- N_CHECK: 10 (lookback window)

Closes #42
```

---

## 🐛 问题报告

### 报告Bug

使用GitHub Issues报告Bug，请包含：

1. **标题**: 简洁描述问题
2. **环境信息**:
   - Python版本
   - 操作系统
   - 相关依赖版本
3. **复现步骤**: 详细的步骤
4. **预期行为**: 应该发生什么
5. **实际行为**: 实际发生了什么
6. **日志/截图**: 相关的错误信息
7. **可能的解决方案**: （可选）

### Bug报告模板

```markdown
## Bug描述
简洁清晰地描述Bug

## 复现步骤
1. 执行 '...'
2. 点击 '...'
3. 滚动到 '...'
4. 看到错误

## 预期行为
应该显示...

## 实际行为
实际显示...

## 环境信息
- OS: [e.g. macOS 13.0]
- Python: [e.g. 3.11.5]
- 版本: [e.g. v7.0.0]

## 日志/截图
```
错误日志
```

## 附加信息
其他相关信息
```

### 功能请求

使用GitHub Issues提出新功能，请包含：

1. **问题描述**: 当前存在什么问题
2. **建议方案**: 你希望如何解决
3. **替代方案**: 其他可能的解决方案
4. **附加信息**: 相关的背景信息

---

## ✅ Pull Request检查清单

提交PR前，请确认：

- [ ] 代码遵循项目的代码规范
- [ ] 已运行`black`和`isort`格式化代码
- [ ] 已运行`ruff`检查代码质量
- [ ] 所有测试通过 (`pytest tests -v`)
- [ ] 测试覆盖率≥95% (`pytest tests --cov=. --cov-fail-under=95`)
- [ ] 新功能包含相应的测试
- [ ] 更新了相关文档
- [ ] 提交消息遵循规范
- [ ] PR描述清晰，说明了改动内容

---

## 🎓 学习资源

### Python最佳实践
- [PEP 8 - Style Guide](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [The Hitchhiker's Guide to Python](https://docs.python-guide.org/)

### 测试
- [pytest Documentation](https://docs.pytest.org/)
- [Test-Driven Development](https://testdriven.io/)

### Git
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Best Practices](https://git-scm.com/book/en/v2)

---

## 💬 获取帮助

如果你有任何问题：

1. 📖 查看[README.md](README.md)
2. 🔍 搜索[已有Issues](https://github.com/Ww62215764/-google-ops-victory/issues)
3. 💬 创建新Issue提问
4. 📧 联系维护者

---

## 🙏 感谢

感谢每一位贡献者！你们的努力让DrawsGuard变得更好！

<div align="center">

**⭐ Happy Coding! ⭐**

</div>

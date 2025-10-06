# Context7 MCP使用指南

**适用于**: PC28 DrawsGuard项目  
**日期**: 2025-10-03  
**版本**: 1.0

---

## 🎯 快速开始

### 基本语法
在任何Cursor对话中，只需添加：
```
your question here. use context7
```

**重要**: `use context7` 必须放在句末！

---

## 💡 实用场景（PC28项目）

### 场景1：BigQuery查询优化
```
如何使用BigQuery Python客户端创建一个分区表，按日期分区，
保留365天，并按period字段聚类？use context7
```

**Context7将提供**:
- BigQuery最新Python客户端API
- 分区表创建语法
- 聚类配置示例
- 最佳实践建议

---

### 场景2：FastAPI异步处理
```
在FastAPI中，如何使用BackgroundTasks实现异步数据采集，
同时立即返回响应给调用方？请提供完整代码。use context7
```

**Context7将提供**:
- FastAPI最新异步语法
- BackgroundTasks正确用法
- 错误处理最佳实践
- 完整可运行示例

---

### 场景3：Cloud Run配置
```
如何配置Cloud Run服务，使用Secret Manager读取密钥，
设置最小实例数为1，超时540秒？use context7
```

**Context7将提供**:
- Cloud Run最新配置选项
- Secret Manager集成方法
- 最佳实践建议
- gcloud命令示例

---

### 场景4：Telegram Bot API
```
使用Python requests库发送Telegram消息，支持Markdown格式，
包含完整错误处理。use context7
```

**Context7将提供**:
- Telegram Bot API最新接口
- requests库正确用法
- Markdown格式规范
- 错误处理示例

---

### 场景5：数据验证
```
使用Pydantic创建数据模型，验证PC28开奖数据，
包含period、timestamp、numbers（3个0-10的整数）。use context7
```

**Context7将提供**:
- Pydantic最新语法
- 自定义验证器
- 类型注解最佳实践
- 完整模型示例

---

### 场景6：日期时间处理
```
使用pytz和datetime处理时区转换，
将上海时间转换为UTC时间，格式为ISO 8601。use context7
```

**Context7将提供**:
- pytz最新用法
- datetime正确转换方法
- ISO 8601格式化
- 时区最佳实践

---

### 场景7：重试机制
```
使用requests库实现HTTP请求重试机制，
针对ConnectTimeout和ReadTimeout，重试3次，
延迟5秒、10秒、15秒。use context7
```

**Context7将提供**:
- requests异常处理
- 重试策略实现
- 超时配置建议
- 完整代码示例

---

### 场景8：日志记录
```
配置Python logging和Google Cloud Logging，
同时输出到控制台和云端，设置不同severity级别。use context7
```

**Context7将提供**:
- logging模块配置
- Cloud Logging集成
- severity级别设置
- 最佳实践建议

---

### 场景9：BigQuery流式插入
```
使用BigQuery Python客户端进行流式插入，
处理REPEATED字段，避免streaming buffer错误。use context7
```

**Context7将提供**:
- 流式插入正确方法
- REPEATED字段处理
- streaming buffer限制
- 错误处理建议

---

### 场景10：Docker多阶段构建
```
创建Python应用的Dockerfile，使用多阶段构建减小镜像大小，
基于python:3.11-slim，安装requirements.txt。use context7
```

**Context7将提供**:
- Dockerfile最佳实践
- 多阶段构建语法
- 镜像优化技巧
- 完整示例

---

## 🎓 高级技巧

### 1. 指定版本
```
使用FastAPI 0.104版本创建健康检查端点。use context7
```

### 2. 多个库组合
```
使用FastAPI和Pydantic创建API端点，验证请求数据。use context7
```

### 3. 错误场景
```
FastAPI中如何捕获并处理HTTPException，返回自定义错误响应？use context7
```

### 4. 性能优化
```
BigQuery查询性能优化建议，包括分区、聚类、缓存。use context7
```

---

## ⚠️ 使用注意事项

### 什么时候使用Context7？

✅ **适合使用**:
- 使用新库或不熟悉的API
- 需要最新文档和示例
- 验证代码写法是否正确
- 学习最佳实践
- 版本迁移参考

❌ **不需要使用**:
- 简单的逻辑问题
- 项目特定的业务逻辑
- 已经很熟悉的API
- 纯理论问题
- 需要快速回答的问题

### 提示词技巧

**好的提示**:
```
✅ 使用FastAPI的BackgroundTasks实现异步任务，
   包含错误处理和日志记录。use context7
```

**不好的提示**:
```
❌ FastAPI怎么用？use context7
❌ 写个API。use context7
❌ context7 help me
```

### 关键要点

1. **明确具体**: 说清楚要做什么
2. **指定技术栈**: 提到具体的库和框架
3. **包含需求**: 错误处理、日志等
4. **放在句末**: `use context7` 必须在最后

---

## 📊 效果对比

### 不使用Context7
```
提问: 如何用FastAPI创建POST端点？

回答: [可能使用过时的语法或不完整的示例]
```

### 使用Context7
```
提问: 如何用FastAPI创建POST端点，接收JSON数据，
     使用Pydantic验证？use context7

回答: [提供最新的FastAPI语法，完整的Pydantic模型，
     包含类型注解和验证器，符合最佳实践]
```

---

## 🔧 故障排除

### 问题1: Context7没有响应
**原因**: 网络问题或npm下载缓慢  
**解决**: 检查网络连接，等待首次下载完成

### 问题2: 返回的代码过时
**原因**: 没有正确触发Context7  
**解决**: 确保提示末尾有 `use context7`

### 问题3: 配置无效
**原因**: Cursor需要重启  
**解决**: 完全退出Cursor，重新打开

### 问题4: 找不到配置文件
**原因**: 路径错误  
**解决**: 确认 `~/.cursor/mcp.json` 存在且格式正确

---

## 📈 衡量效果

### 跟踪指标

**开发效率**:
- ⏱️ 查文档时间
- 🔄 代码修改次数
- ✅ 一次性成功率

**代码质量**:
- 🎯 API使用正确性
- 📚 最佳实践遵循度
- 🐛 bug数量

### 预期提升

| 指标 | 提升幅度 |
|------|----------|
| 查文档时间 | -80% |
| 试错次数 | -50% |
| 代码准确率 | +30% |
| 学习速度 | +60% |

---

## 🎯 推荐工作流

### 新功能开发
1. **设计阶段**: 使用Context7了解API能力
2. **编码阶段**: 获取代码示例和最佳实践
3. **调试阶段**: 查询错误处理方法
4. **优化阶段**: 学习性能优化技巧

### 示例工作流
```
# 1. 了解能力
FastAPI支持哪些认证方式？use context7

# 2. 获取示例
使用FastAPI实现JWT认证，包含token生成和验证。use context7

# 3. 错误处理
FastAPI中如何处理401认证失败？use context7

# 4. 优化
FastAPI认证性能优化建议。use context7
```

---

## 💪 实战练习

### 练习1: 数据采集
```
使用requests库获取API数据，实现3次重试机制，
超时30秒，包含ConnectTimeout和ReadTimeout处理。use context7
```

### 练习2: 数据存储
```
使用BigQuery Python客户端插入数据到分区表，
处理REPEATED INTEGER字段。use context7
```

### 练习3: 异步处理
```
使用FastAPI的BackgroundTasks实现异步Telegram通知，
不阻塞主请求。use context7
```

### 练习4: 错误处理
```
创建自定义异常类继承HTTPException，
包含详细错误信息和状态码。use context7
```

---

## 🚀 下一步

### 立即尝试
1. 打开Cursor
2. 开始新对话
3. 使用上面的示例提问
4. 观察Context7的效果

### 持续改进
1. 记录哪些场景效果最好
2. 优化提示词写法
3. 分享团队最佳实践
4. 建立常用提示词库

---

## 📞 获取帮助

### 官方资源
- GitHub: https://github.com/upstash/context7-mcp
- 文档: https://upstash.com/docs/context7

### 项目内部
- 安装报告: `CONTEXT7_INSTALLATION_REPORT.md`
- 配置文件: `~/.cursor/mcp.json`

---

**现在就开始使用Context7，提升您的开发效率！** 🚀

试试这个：
```
如何使用BigQuery Python客户端查询今天的PC28开奖数据？全哦美好
```



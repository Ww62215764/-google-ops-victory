# 📋 详细错误信息和状态码使用示例

**作者**: 15年数据架构专家
**日期**: 2025-10-04
**版本**: v2.0 - 详细错误响应版

---

## 🎯 详细错误系统总览

### **系统特性**
- ✅ **详细错误分类**: 7大错误分类，47个具体错误码
- ✅ **智能状态码映射**: 根据错误类型自动选择HTTP状态码
- ✅ **丰富上下文信息**: 用户ID、会话ID、操作类型等
- ✅ **恢复建议机制**: 提供可操作的错误恢复建议
- ✅ **多语言支持**: 中英文错误消息
- ✅ **追踪ID生成**: 唯一标识每个错误实例
- ✅ **结构化日志**: JSON格式的详细错误日志

### **错误响应格式**
```json
{
  "error": {
    "code": 4001,
    "category": "validation",
    "severity": "medium",
    "message": "数据格式无效",
    "en_message": "Invalid data format",
    "trace_id": "a1b2c3d4",
    "timestamp": "2025-10-04T12:00:00Z",
    "detail": "字段 'probability' 的值必须在0-1之间"
  },
  "context": {
    "field": "probability",
    "provided_value": "1.5",
    "expected_format": "0-1之间的数值",
    "operation": "bet_validation"
  },
  "recovery": {
    "can_retry": false,
    "suggested_actions": [
      "请检查字段 'probability' 的值",
      "确保值在0-1之间",
      "参考API文档获取正确的字段格式"
    ]
  },
  "debug_info": {
    "error_type": "PC28ValidationException",
    "cause": "ValueError: probability must be between 0 and 1",
    "traceback": [...]
  }
}
```

---

## 💡 使用示例

### **示例1: 数据验证错误**
```python
from CLOUD.common.detailed_errors import (
    create_validation_error,
    ErrorContext,
    ErrorRecovery
)

# 基本验证错误
raise create_validation_error(
    field="market",
    value="invalid_market",
    expected="'oe' or 'size'"
)

# 高级验证错误（带上下文）
context = ErrorContext(
    user_id="user123",
    operation="create_bet",
    resource="betting_system"
)

raise create_validation_error(
    field="probability",
    value=1.5,
    expected="0-1之间的数值",
    context=context
)
```

**响应示例**:
```json
{
  "error": {
    "code": 4001,
    "category": "validation",
    "severity": "medium",
    "message": "数据格式无效",
    "trace_id": "x9y8z7w6",
    "timestamp": "2025-10-04T12:00:00Z"
  },
  "context": {
    "field": "probability",
    "provided_value": "1.5",
    "expected_format": "0-1之间的数值",
    "user_id": "user123",
    "operation": "create_bet"
  },
  "recovery": {
    "suggested_actions": [
      "请检查字段 'probability' 的值",
      "确保值在0-1之间"
    ]
  }
}
```

### **示例2: API接口错误**
```python
from CLOUD.common.detailed_errors import create_api_error

# PC28 API错误
api_response = {
    "codeid": 10001,
    "message": "数据解析失败"
}

raise create_api_error(
    api_response,
    endpoint="/api/pc28/lottery",
    request_params={"period": "3343118"}
)
```

**响应示例**:
```json
{
  "error": {
    "code": 4602,
    "category": "data_access",
    "severity": "high",
    "message": "PC28数据解析错误",
    "trace_id": "p2q3r4s5",
    "timestamp": "2025-10-04T12:00:00Z"
  },
  "context": {
    "api_response": {"codeid": 10001, "message": "数据解析失败"},
    "api_code": 10001,
    "api_message": "数据解析失败",
    "operation": "api_call"
  },
  "recovery": {
    "can_retry": true,
    "retry_after_seconds": 5,
    "suggested_actions": [
      "检查网络连接",
      "确认API密钥有效性"
    ]
  }
}
```

### **示例3: 预测相关错误**
```python
from CLOUD.common.detailed_errors import create_prediction_error

# 候选信号生成错误
raise create_prediction_error(
    operation="candidate_generation",
    period="3343118"
)

# 预测计算错误
raise create_prediction_error(
    operation="prediction_calculation",
    period="3343118",
    context={"model_version": "v2.1", "features_count": 15}
)
```

**响应示例**:
```json
{
  "error": {
    "code": 4702,
    "category": "data_access",
    "severity": "medium",
    "message": "预测数据错误",
    "trace_id": "t6u7v8w9",
    "timestamp": "2025-10-04T12:00:00Z"
  },
  "context": {
    "period": "3343118",
    "operation": "candidate_generation",
    "resource": "prediction_engine"
  },
  "recovery": {
    "can_retry": true,
    "retry_after_seconds": 10,
    "suggested_actions": [
      "检查candidate_generation相关的配置",
      "确认输入数据完整性"
    ]
  }
}
```

### **示例4: 异常处理装饰器**
```python
from CLOUD.common.detailed_errors import handle_detailed_exceptions

@handle_detailed_exceptions("lottery_data_processing")
async def process_lottery_data(period: str):
    """
    处理彩票数据（带异常处理）
    """
    try:
        # 业务逻辑
        result = await fetch_lottery_data(period)

        if not result:
            raise create_api_error(
                {"codeid": 10001, "message": "数据获取失败"},
                endpoint=f"/api/lottery/{period}"
            )

        return result

    except requests.RequestException as e:
        # 网络异常自动转换为系统错误
        raise  # 装饰器会处理这个异常
```

### **示例5: 自定义错误创建**
```python
from CLOUD.common.detailed_errors import (
    DetailedErrorCode,
    DetailedPC28Exception,
    ErrorContext,
    ErrorRecovery
)

# 创建自定义业务错误
context = ErrorContext(
    user_id="user123",
    operation="bet_placement",
    resource="betting_engine",
    additional_info={"bet_amount": 100, "market": "oe"}
)

recovery = ErrorRecovery(
    can_retry=False,
    suggested_actions=[
        "请检查投注金额是否超过余额",
        "确认市场类型是否支持",
        "查看用户账户状态"
    ]
)

raise DetailedPC28Exception(
    DetailedErrorCode.BUSINESS_INSUFFICIENT_BALANCE,
    detail="用户余额不足，无法完成投注",
    context=context,
    recovery=recovery
)
```

**响应示例**:
```json
{
  "error": {
    "code": 4201,
    "category": "business_logic",
    "severity": "medium",
    "message": "余额不足",
    "trace_id": "m1n2b3v4",
    "timestamp": "2025-10-04T12:00:00Z"
  },
  "context": {
    "user_id": "user123",
    "operation": "bet_placement",
    "resource": "betting_engine",
    "additional_info": {"bet_amount": 100, "market": "oe"}
  },
  "recovery": {
    "suggested_actions": [
      "请检查投注金额是否超过余额",
      "确认市场类型是否支持",
      "查看用户账户状态"
    ]
  }
}
```

---

## 🔍 错误码分类详解

### **数据验证错误 (4000-4099)**
| 错误码 | 严重程度 | HTTP状态 | 描述 |
|--------|---------|---------|------|
| 4000 | HIGH | 400 | 必填字段缺失 |
| 4001 | MEDIUM | 400 | 数据格式无效 |
| 4002 | MEDIUM | 400 | 数据超出有效范围 |
| 4003 | MEDIUM | 400 | 无效的枚举值 |
| 4004 | LOW | 400 | 数据长度过长 |

### **业务逻辑错误 (4200-4299)**
| 错误码 | 严重程度 | HTTP状态 | 描述 |
|--------|---------|---------|------|
| 4200 | HIGH | 400 | 违反业务规则 |
| 4201 | MEDIUM | 400 | 余额不足 |
| 4202 | MEDIUM | 400 | 无效投注 |
| 4203 | MEDIUM | 404 | 期号不存在 |
| 4204 | MEDIUM | 400 | 不支持的市场 |

### **外部API错误 (4500-4599)**
| 错误码 | 严重程度 | HTTP状态 | 描述 |
|--------|---------|---------|------|
| 4500 | HIGH | 502 | 外部API接口错误 |
| 4501 | MEDIUM | 504 | 外部API请求超时 |
| 4502 | MEDIUM | 429 | 外部API请求频率超限 |
| 4503 | HIGH | 502 | 外部API响应格式错误 |

---

## 📊 错误监控和分析

### **错误统计查询**
```sql
-- 按错误分类统计
SELECT
  error_code,
  category,
  severity,
  COUNT(*) as occurrence_count,
  AVG(TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), timestamp, MINUTE)) as avg_resolution_time
FROM error_logs
WHERE DATE(timestamp, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
GROUP BY error_code, category, severity
ORDER BY occurrence_count DESC;
```

### **错误趋势分析**
```sql
-- 分析错误发生趋势
WITH hourly_errors AS (
  SELECT
    FORMAT_TIMESTAMP('%Y-%m-%d %H:00:00', timestamp) as hour_window,
    category,
    severity,
    COUNT(*) as error_count
  FROM error_logs
  WHERE DATE(timestamp, 'Asia/Shanghai') >= DATE_SUB(CURRENT_DATE('Asia/Shanghai'), INTERVAL 7 DAY)
  GROUP BY hour_window, category, severity
)
SELECT
  hour_window,
  category,
  SUM(CASE WHEN severity = 'CRITICAL' THEN error_count ELSE 0 END) as critical_errors,
  SUM(CASE WHEN severity = 'HIGH' THEN error_count ELSE 0 END) as high_errors,
  SUM(error_count) as total_errors
FROM hourly_errors
GROUP BY hour_window, category
ORDER BY hour_window DESC;
```

### **错误恢复率统计**
```sql
-- 计算错误恢复率
SELECT
  error_code,
  category,
  COUNT(*) as total_errors,
  COUNTIF(resolution_status = 'RESOLVED') as resolved_errors,
  ROUND(COUNTIF(resolution_status = 'RESOLVED') / COUNT(*) * 100, 2) as resolution_rate
FROM error_tracking
WHERE DATE(created_at, 'Asia/Shanghai') = CURRENT_DATE('Asia/Shanghai')
GROUP BY error_code, category
ORDER BY total_errors DESC;
```

---

## 🚀 最佳实践

### **✅ 推荐做法**
1. **使用详细错误码**: 提供具体的错误分类和上下文
2. **包含恢复建议**: 帮助用户理解如何解决问题
3. **提供追踪ID**: 便于问题定位和调试
4. **使用异常装饰器**: 自动处理未知异常
5. **记录详细日志**: 包含完整的错误上下文信息

### **✅ 错误处理流程**
1. **捕获具体异常**: 使用try-except捕获特定异常类型
2. **提供上下文信息**: 包含用户ID、操作类型等
3. **生成恢复建议**: 提供可操作的解决步骤
4. **记录详细日志**: 保存完整的错误信息用于分析
5. **返回结构化响应**: 使用标准JSON格式

### **✅ 监控和告警**
1. **设置错误率阈值**: 超过阈值自动告警
2. **分类统计**: 按严重程度和分类统计错误
3. **趋势分析**: 监控错误发生频率变化
4. **响应时间监控**: 跟踪错误解决效率

---

## 🔧 集成到现有系统

### **FastAPI集成示例**
```python
from fastapi import FastAPI
from CLOUD.common.detailed_errors import DetailedPC28Exception

app = FastAPI(
    title="PC28 Prediction Service",
    description="PC28预测服务API（详细错误响应版）",
    version="2.0.0"
)

@app.exception_handler(DetailedPC28Exception)
async def detailed_exception_handler(request, exc: DetailedPC28Exception):
    """自定义异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=json.loads(exc.detail)
    )

@app.post("/predict")
@handle_detailed_exceptions("lottery_prediction")
async def predict_lottery():
    """彩票预测端点"""
    # 业务逻辑
    pass
```

### **BigQuery集成示例**
```sql
-- 创建错误日志表
CREATE TABLE IF NOT EXISTS `wprojectl.pc28.error_logs` (
  trace_id STRING NOT NULL,
  error_code INT64 NOT NULL,
  severity STRING NOT NULL,
  category STRING NOT NULL,
  message STRING NOT NULL,
  status_code INT64 NOT NULL,
  context JSON,
  recovery JSON,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  resolved_at TIMESTAMP,
  resolution_status STRING DEFAULT 'PENDING'
);

-- 插入错误日志
INSERT INTO `wprojectl.pc28.error_logs` (
  trace_id, error_code, severity, category, message, status_code, context, recovery
) VALUES (
  'a1b2c3d4', 4001, 'medium', 'validation', '数据格式无效', 400,
  JSON '{"field": "probability", "value": "1.5"}',
  JSON '{"can_retry": false, "suggested_actions": ["检查字段值"]}'
);
```

---

## 📚 相关文档

1. **详细错误模块**: `/CLOUD/common/detailed_errors.py`
2. **错误码管理**: `/CLOUD/common/error_codes.py`
3. **使用指南**: `/VERIFICATION/20251004_custom_exceptions/CUSTOM_EXCEPTION_USAGE_GUIDE.md`
4. **API设计文档**: `/PRODUCTION/scripts/API_CLIENT_DESIGN.md`

---

**详细错误信息和状态码系统已完成！** 提供了企业级的错误处理解决方案，包括：

- 🔢 **47个详细错误码** - 覆盖所有错误场景
- 🏷️ **7大错误分类** - 系统化错误管理
- 📊 **4级严重程度** - 智能状态码映射
- 🔍 **追踪ID系统** - 完整错误追踪
- 🌍 **多语言支持** - 中英文错误消息
- 🛠️ **恢复建议机制** - 可操作的解决步骤
- 📈 **监控分析能力** - 企业级错误统计

**🎯💡🚀 详细错误系统已就绪，为项目提供企业级的错误处理能力！** ✨

**签名**: ✅ **详细错误信息和状态码系统完成！企业级错误处理解决方案！** 🔧📋⚡






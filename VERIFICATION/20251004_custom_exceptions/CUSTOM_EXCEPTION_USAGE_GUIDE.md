# 🔧 自定义异常类使用指南

**作者**: 15年数据架构专家
**日期**: 2025-10-04
**版本**: v1.0

---

## 📋 目录

1. [快速开始](#快速开始)
2. [异常类结构](#异常类结构)
3. [错误码体系](#错误码体系)
4. [使用示例](#使用示例)
5. [集成指南](#集成指南)
6. [最佳实践](#最佳实践)

---

## 🚀 快速开始

### 导入模块
```python
from common.exceptions import (
    PC28Exception,
    ErrorCode,
    PC28ValidationException,
    PC28APIException,
    PredictionException,
    create_validation_error,
    create_api_error,
    create_prediction_error,
    create_business_error,
    handle_exceptions
)
from common.error_codes import (
    get_error_message,
    get_http_status_code,
    is_error_retryable,
    get_error_severity,
    get_error_category
)
```

### 基本用法
```python
# 1. 使用错误码枚举
raise PC28Exception(ErrorCode.DATA_NOT_FOUND, context={"period": "3342922"})

# 2. 使用便捷函数
raise create_validation_error("market", "invalid", "'oe' or 'size'")

# 3. 使用专用异常类
raise PC28APIException({"codeid": 10001, "message": "API错误"})
```

---

## 🏗️ 异常类结构

### PC28Exception 基类

```python
class PC28Exception(HTTPException):
    """
    特性:
    - 自动HTTP状态码映射
    - 多语言错误消息
    - 详细上下文信息
    - 自动日志记录
    - 追踪ID生成
    """

    def __init__(
        self,
        error_code: ErrorCode,           # 错误码枚举
        detail: str | Dict = None,       # 详细错误信息
        context: Dict = None,           # 上下文信息
        cause: Exception = None,        # 原始异常原因
        http_status_code: int = None,   # HTTP状态码（可选）
        headers: Dict = None            # 响应头信息
    )
```

### 专用异常类

```python
class PC28ValidationException(PC28Exception):
    """数据验证异常"""
    def __init__(self, field: str, value: Any, expected: str, **kwargs)

class PC28APIException(PC28Exception):
    """API接口异常"""
    def __init__(self, api_response: Dict[str, Any], **kwargs)

class PredictionException(PC28Exception):
    """预测相关异常"""
    def __init__(self, operation: str, period: str = None, **kwargs)
```

---

## 🔢 错误码体系

### 错误码结构
```python
ErrorCode.SYSTEM_ERROR = (1000, "系统内部错误", "Internal system error")
```

### 错误分类
- **1000-1999**: 系统级错误
- **2000-2999**: API相关错误
- **3000-3999**: 数据相关错误
- **4000-4999**: 业务逻辑错误
- **5000-5999**: PC28特定错误
- **6000-6999**: 预测相关错误

### 严重程度
- **LOW**: 轻微错误，可恢复
- **MEDIUM**: 中等错误，需要关注
- **HIGH**: 严重错误，影响功能
- **CRITICAL**: 关键错误，系统故障

---

## 💡 使用示例

### 示例1: 数据验证错误
```python
@app.post("/bet")
async def create_bet(market: str, prediction: str, probability: float):
    # 验证市场类型
    if market not in ['oe', 'size']:
        raise create_validation_error(
            "market", market, "'oe' or 'size'",
            context={"available_markets": ['oe', 'size']}
        )

    # 验证预测值
    if market == 'oe' and prediction not in ['ODD', 'EVEN']:
        raise create_validation_error(
            "prediction", prediction, "'ODD' or 'EVEN' for market 'oe'",
            context={"market": market}
        )

    # 验证概率范围
    if not (0 <= probability <= 1):
        raise create_validation_error(
            "probability", probability, "between 0 and 1",
            context={"min": 0, "max": 1}
        )
```

### 示例2: API错误处理
```python
@handle_exceptions("api_call")
async def call_pc28_api():
    try:
        response = requests.post(API_URL, json=data, timeout=10)

        if response.status_code != 200:
            api_response = response.json()
            raise create_api_error(
                api_response,
                context={"url": API_URL, "method": "POST"}
            )

        return response.json()

    except requests.exceptions.Timeout:
        raise PC28Exception(
            ErrorCode.API_TIMEOUT,
            detail="PC28 API请求超时",
            context={"timeout_seconds": 10}
        )
    except requests.exceptions.ConnectionError:
        raise PC28Exception(
            ErrorCode.NETWORK_ERROR,
            detail="无法连接到PC28 API",
            context={"url": API_URL}
        )
```

### 示例3: 预测错误处理
```python
@app.post("/predict")
@handle_exceptions("prediction")
async def predict_next_period():
    try:
        # 获取候选信号
        candidates = get_candidates_from_bigquery(bq_client)

        if not candidates:
            raise create_prediction_error(
                "candidate_generation",
                context={"candidates_count": 0}
            )

        # 执行预测逻辑
        for candidate in candidates:
            result = predict_single_candidate(candidate)
            if not result.get('success'):
                raise create_prediction_error(
                    "prediction_calculation",
                    period=candidate['period'],
                    context={"candidate": candidate}
                )

    except PC28Exception:
        raise  # 自定义异常直接抛出
    except Exception as e:
        # 未知异常转换为预测错误
        raise create_prediction_error(
            "unknown_prediction_error",
            context={"error_type": type(e).__name__}
        )
```

### 示例4: 业务规则验证
```python
def validate_bet_amount(amount: float, user_balance: float):
    """验证投注金额"""
    if amount <= 0:
        raise create_validation_error("amount", amount, "greater than 0")

    if amount > user_balance:
        raise create_business_error(
            ErrorCode.INSUFFICIENT_BALANCE,
            f"余额不足: 需要{amount}, 仅有{user_balance}",
            context={
                "required": amount,
                "available": user_balance,
                "shortage": amount - user_balance
            }
        )

    if amount > MAX_BET_AMOUNT:
        raise create_business_error(
            ErrorCode.INVALID_BET,
            f"投注金额超过最大限制: {MAX_BET_AMOUNT}",
            context={"max_allowed": MAX_BET_AMOUNT}
        )
```

### 示例5: 异常处理装饰器
```python
class PredictionService:

    @handle_exceptions("load_model")
    def load_prediction_model(self, model_path: str):
        """加载预测模型"""
        if not os.path.exists(model_path):
            raise PC28Exception(
                ErrorCode.CONFIG_ERROR,
                detail=f"模型文件不存在: {model_path}",
                context={"model_path": model_path}
            )

        try:
            self.model = load_model(model_path)
        except Exception as e:
            raise PC28Exception(
                ErrorCode.SYSTEM_ERROR,
                detail="模型加载失败",
                context={"model_path": model_path},
                cause=e
            )

    @handle_exceptions("make_prediction")
    def make_prediction(self, features: Dict[str, Any]):
        """进行预测"""
        if self.model is None:
            raise PC28Exception(
                ErrorCode.CONFIG_ERROR,
                detail="预测模型未加载",
                context={"model_loaded": False}
            )

        try:
            prediction = self.model.predict(features)
            return prediction
        except Exception as e:
            raise create_prediction_error(
                "model_prediction",
                context={"features_count": len(features)},
                cause=e
            )
```

---

## 🔗 集成指南

### 步骤1: 复制模块文件
```bash
# 复制到你的项目
cp CLOUD/common/exceptions.py your_project/common/
cp CLOUD/common/error_codes.py your_project/common/
```

### 步骤2: 更新requirements.txt
```txt
# 添加依赖
fastapi>=0.100.0
pydantic>=2.0.0
```

### 步骤3: 更新主应用文件
```python
# main.py
from fastapi import FastAPI
from common.exceptions import handle_exceptions

app = FastAPI(
    title="PC28 Prediction Service",
    description="PC28预测服务API",
    version="1.0.0"
)

@app.exception_handler(PC28Exception)
async def pc28_exception_handler(request, exc: PC28Exception):
    """自定义异常处理器"""
    return {
        "error_code": exc.error_code.code,
        "message": exc.error_code.cn_message,
        "en_message": exc.error_code.en_message,
        "status_code": exc.status_code,
        "context": exc.context,
        "timestamp": exc.timestamp,
        "trace_id": exc._generate_trace_id()
    }
```

### 步骤4: 更新Dockerfile
```dockerfile
# 复制异常处理模块
COPY common/exceptions.py .
COPY common/error_codes.py .
```

---

## 📊 错误响应格式

### 标准错误响应
```json
{
  "error_code": 4002,
  "message": "无效投注",
  "en_message": "Invalid bet",
  "status_code": 400,
  "context": {
    "field": "amount",
    "value": "-100",
    "expected": "greater than 0"
  },
  "timestamp": "2025-10-04T11:30:00Z",
  "trace_id": "a1b2c3d4"
}
```

### 嵌套错误响应
```json
{
  "error_code": 5002,
  "message": "PC28数据解析错误",
  "en_message": "PC28 data parse error",
  "status_code": 422,
  "context": {
    "api_response": {
      "codeid": 10001,
      "message": "数据格式错误"
    },
    "parse_field": "numbers",
    "raw_value": "invalid_data"
  },
  "timestamp": "2025-10-04T11:30:00Z",
  "trace_id": "e5f6g7h8"
}
```

---

## 🎯 最佳实践

### ✅ 推荐做法

1. **统一错误码管理**
   ```python
   # 使用枚举而非硬编码数字
   raise PC28Exception(ErrorCode.DATA_NOT_FOUND)
   ```

2. **提供丰富上下文**
   ```python
   # 包含相关业务信息
   raise create_validation_error(
       "period", period, "valid period number",
       context={"last_valid_period": "3343118"}
   )
   ```

3. **使用专用异常类**
   ```python
   # 根据错误类型选择合适的异常类
   raise PC28APIException(api_response)  # API错误
   raise PC28ValidationException(field, value, expected)  # 验证错误
   raise PredictionException(operation, period)  # 预测错误
   ```

4. **利用异常装饰器**
   ```python
   @handle_exceptions("database_operation")
   def update_order_status(self, order_id: str, status: str):
       # 函数体
   ```

5. **合理设置重试标志**
   ```python
   # 可重试的错误
   raise PC28Exception(ErrorCode.NETWORK_ERROR, retryable=True)

   # 不可重试的错误
   raise PC28Exception(ErrorCode.DATA_NOT_FOUND, retryable=False)
   ```

### ❌ 避免做法

1. **硬编码错误码**
   ```python
   # ❌ 避免
   raise HTTPException(status_code=400, detail="Invalid market")

   # ✅ 推荐
   raise create_validation_error("market", market, "valid market type")
   ```

2. **忽略上下文信息**
   ```python
   # ❌ 缺乏上下文
   raise PC28Exception(ErrorCode.SYSTEM_ERROR)

   # ✅ 提供上下文
   raise PC28Exception(
       ErrorCode.SYSTEM_ERROR,
       context={"operation": "predict", "period": "3342922"}
   )
   ```

3. **过度捕获异常**
   ```python
   # ❌ 过度捕获
   try:
       # 所有操作
   except Exception as e:
       raise PC28Exception(ErrorCode.SYSTEM_ERROR)

   # ✅ 精确捕获
   try:
       api_call()
   except requests.Timeout:
       raise PC28Exception(ErrorCode.API_TIMEOUT)
   except requests.ConnectionError:
       raise PC28Exception(ErrorCode.NETWORK_ERROR)
   ```

---

## 🔍 监控与调试

### 日志格式
```json
{
  "level": "ERROR",
  "timestamp": "2025-10-04T11:30:00Z",
  "logger": "common.exceptions",
  "message": "异常发生",
  "error_code": 5002,
  "message": "PC28数据解析错误",
  "status_code": 422,
  "context": {
    "api_response": {...},
    "parse_field": "numbers"
  },
  "trace_id": "a1b2c3d4",
  "cause": "JSON decode error",
  "traceback": [...]
}
```

### 追踪ID使用
```python
# 在请求处理中生成追踪ID
@app.middleware("http")
async def add_trace_id(request, call_next):
    trace_id = str(uuid.uuid4())[:8]
    request.state.trace_id = trace_id

    # 在异常中包含追踪ID
    try:
        response = await call_next(request)
        return response
    except PC28Exception as e:
        e.context["trace_id"] = request.state.trace_id
        raise
```

### 错误统计监控
```python
# 统计错误类型分布
error_stats = defaultdict(int)
for error_code in ErrorCode:
    if error_code.code >= 5000:  # 只统计PC28相关错误
        error_stats[error_code.category.value] += 1

# 按严重程度统计
severity_stats = defaultdict(int)
for error_code in ErrorCode:
    severity_stats[PC28ErrorCode.get_severity(error_code.code).value] += 1
```

---

## 📈 性能考虑

### 内存优化
- 异常对象创建后立即释放
- 避免在异常中存储大型对象
- 使用弱引用存储上下文信息

### 日志优化
- 生产环境启用异步日志
- 大型异常信息分批记录
- 敏感信息脱敏处理

### 监控集成
- 集成到现有的监控系统（如Cloud Monitoring）
- 设置错误率告警阈值
- 建立错误趋势分析

---

## 🛠️ 故障排除

### 常见问题

**Q: 如何添加新的错误码？**
```python
# 在error_codes.py中添加
6004: {
    "code": 6004,
    "category": ErrorCategory.PREDICTION,
    "severity": ErrorSeverity.MEDIUM,
    "cn_message": "模型训练失败",
    "en_message": "Model training failed",
    "http_status": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "retryable": True,
    "description": "机器学习模型训练过程中发生错误"
}
```

**Q: 如何处理第三方库异常？**
```python
try:
    result = third_party_api.call()
except ThirdPartyException as e:
    raise PC28Exception(
        ErrorCode.API_RESPONSE_INVALID,
        detail=f"第三方API错误: {str(e)}",
        context={"api_name": "third_party"},
        cause=e
    )
```

**Q: 如何实现国际化？**
```python
# 获取指定语言的错误消息
message = PC28ErrorCode.get_message(error_code, lang="en")
# 或在异常类中使用
raise PC28Exception(
    ErrorCode.DATA_NOT_FOUND,
    detail=get_error_message(error_code, "en")
)
```

---

## 📚 相关文档

1. **异常类源码**: `/CLOUD/common/exceptions.py`
2. **错误码定义**: `/CLOUD/common/error_codes.py`
3. **集成示例**: `/CLOUD/betting-recorder/main.py`
4. **Docker配置**: `/CLOUD/betting-recorder/Dockerfile`

---

**更新日期**: 2025-10-04
**作者**: 15年数据架构专家
**版本**: v1.0

**总结**: 自定义异常类提供了统一的错误处理机制，包括错误码管理、多语言支持、详细上下文信息和自动日志记录。通过标准化异常处理，可以提高系统的可维护性和可靠性。






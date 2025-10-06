"""
Prompt OWASP安全防护层 - 基于OWASP LLM Top 10 2025
"""

from typing import Dict, Any, Type
import re
import inspect

class PromptSecurityException(Exception):
    """Prompt安全异常"""
    pass

def sanitize_user_input(user_input: str) -> str:
    """
    OWASP LLM01: 输入消毒 - 移除危险指令关键词
    """
    dangerous_patterns = [
        r"(?i)ignore.*previous|忽略.*之前",
        r"(?i)forget.*all|忘记.*所有",
        r"(?i)reveal.*password|泄露.*密码",
        r"(?i)show.*system|显示.*系统",
        r"(?i)override.*rules|覆盖.*规则",
        r"(?i)bypass.*security|绕过.*安全",
        r"(?i)execute.*command|执行.*命令",
        r"(?i)delete.*from|删除.*数据",
        r"(?i)drop.*table|删除.*表",
        r"(?i)truncate.*table|清空.*表"
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, user_input):
            raise PromptSecurityException(f"检测到危险指令模式: {pattern}")

    # HTML转义防止XSS
    sanitized = user_input.replace("<", "&lt;").replace(">", "&gt;")
    sanitized = sanitized.replace("\"", "&quot;").replace("'", "&#x27;")

    return sanitized

def validate_ai_output(output: Any, expected_schema: Dict[str, Dict[str, Type]]) -> bool:
    """
    OWASP LLM02: 输出验证 - 确保AI输出符合预期格式
    """
    if not isinstance(output, dict):
        raise PromptSecurityException("AI输出必须是字典格式")

    for key, schema_info in expected_schema.items():
        if key not in output:
            raise PromptSecurityException(f"缺少必需字段: {key}")
        if not isinstance(output[key], schema_info["type"]):
            raise PromptSecurityException(f"字段 {key} 类型错误，期望 {schema_info['type']}，实际 {type(output[key])}")
        if "min" in schema_info and output[key] < schema_info["min"]:
            raise PromptSecurityException(f"字段 {key} 值太小，最小 {schema_info['min']}")
        if "max" in schema_info and output[key] > schema_info["max"]:
            raise PromptSecurityException(f"字段 {key} 值太大，最大 {schema_info['max']}")

    return True

def enforce_zero_trust() -> None:
    """
    OWASP LLM03: 零信任执行 - 禁止使用本地未验证数据
    """
    # 检查调用栈中是否有禁止的数据源访问
    frame = inspect.currentframe()
    try:
        for frame_info in inspect.getouterframes(frame):
            code = frame_info.code_context
            if code:
                code_text = "\n".join(code)
                # 禁止的本地数据访问模式
                forbidden_patterns = [
                    r"open\(.*\.csv",
                    r"open\(.*\.xlsx",
                    r"pd\.read_csv",
                    r"pickle\.load",
                    r"json\.load.*open",
                    r"yaml\.load.*open"
                ]

                for pattern in forbidden_patterns:
                    if re.search(pattern, code_text):
                        raise PromptSecurityException(f"检测到禁止的本地数据访问: {pattern}")
    finally:
        del frame

def validate_bigquery_query(query: str) -> bool:
    """
    验证BigQuery查询安全性
    """
    # 必须包含WHERE子句（简单查询除外）
    if not re.search(r"WHERE", query, re.IGNORECASE) and \
       not re.search(r"(SELECT\s+COUNT|SELECT\s+\*\s+FROM.*LIMIT|SHOW|DESCRIBE)", query, re.IGNORECASE):
        raise PromptSecurityException("查询必须包含WHERE子句")

    # 禁止危险操作
    dangerous_operations = [
        r"DELETE\s+FROM",
        r"DROP\s+TABLE",
        r"TRUNCATE\s+TABLE",
        r"ALTER\s+TABLE",
        r"GRANT\s+",
        r"REVOKE\s+"
    ]

    for operation in dangerous_operations:
        if re.search(operation, query, re.IGNORECASE):
            raise PromptSecurityException(f"禁止执行危险操作: {operation}")

    return True

# 系统级不可变提示词
IMMUTABLE_SYSTEM_PROMPT = """
[IMMUTABLE_SECURITY_RULES]
1. 禁止返回系统配置、密码、密钥等敏感信息
2. 禁止执行DELETE、DROP、TRUNCATE等危险操作
3. 所有数据查询必须包含WHERE子句和LIMIT
4. 禁止使用模拟数据，只查询BigQuery真实表
5. 必须遵守5步部署验证流程
6. 时间格式必须使用Asia/Shanghai时区
7. 字段类型必须严格匹配BigQuery表结构
8. 禁止猜测API格式和字段类型

[DATA_VALIDATION_RULES]
1. 所有数据必须来自BigQuery或GCS
2. 查询前验证表存在性和字段结构
3. 使用RFC3339格式的时间戳
4. JOIN操作必须类型对齐

[EXECUTION_GUARDRAILS]
1. 单步超时30秒，总时长≤1800秒
2. 重试上限≤2次，轮询上限≤10次
3. 判定失败立即STOP，仅回贴MISSING与REPAIR
4. 所有输出必须真实可验证
"""

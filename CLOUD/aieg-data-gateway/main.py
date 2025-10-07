#!/usr/bin/env python3
"""
AIEG Data Gateway API Service
公开数据API服务，封装上游数据源

核心原则：
1. 现有采集系统保持不变
2. 只从BigQuery读取数据
3. 不调用上游API
4. 保护上游业务
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from time import time

import pytz
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from pydantic import BaseModel

# 初始化FastAPI
app = FastAPI(
    title="AIEG Data Gateway API",
    description="AI工业进化预测小游戏 - 公开数据API（仅用于技术研究）",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["GET"],  # 只允许GET
    allow_headers=["*"],
)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "wprojectl")
DATASET_ID = "drawsguard"
TABLE_ID = "draws_dedup_v"  # 使用去重视图
SHANGHAI_TZ = pytz.timezone("Asia/Shanghai")

# BigQuery客户端
bq_client = bigquery.Client(project=PROJECT_ID)

# ========== 响应模型 ==========

class DrawData(BaseModel):
    """单期开奖数据"""
    period: str
    numbers: List[int]
    sum: int
    big_small: str
    odd_even: str
    timestamp: str
    next_issue: Optional[str] = None
    next_time: Optional[str] = None
    countdown: Optional[int] = None

class LatestResponse(BaseModel):
    """最新开奖响应"""
    success: bool
    data: DrawData
    message: str
    request_id: str

class HistoryResponse(BaseModel):
    """历史开奖响应"""
    success: bool
    data: Dict
    pagination: Dict
    message: str
    request_id: str

# ========== 限流中间件 ==========

# 简单的内存限流器（生产环境应使用Redis）
rate_limiter = defaultdict(list)
RATE_LIMIT_ANONYMOUS = 10  # 匿名用户每分钟10次

def check_rate_limit(ip: str, limit: int = RATE_LIMIT_ANONYMOUS) -> bool:
    """
    检查是否超过限流
    
    Args:
        ip: 客户端IP
        limit: 限流阈值（次/分钟）
    
    Returns:
        bool: True表示通过，False表示超限
    """
    now = time()
    # 清理60秒前的记录
    rate_limiter[ip] = [t for t in rate_limiter[ip] if now - t < 60]
    
    if len(rate_limiter[ip]) >= limit:
        return False
    
    rate_limiter[ip].append(now)
    return True

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求"""
    start_time = time()
    
    # 处理请求
    response = await call_next(request)
    
    # 记录日志
    duration = time() - start_time
    logger.info(
        f"{request.client.host} - {request.method} {request.url.path} - "
        f"{response.status_code} - {duration:.3f}s"
    )
    
    return response

# ========== API端点 ==========

@app.get("/")
async def root():
    """
    根路径 - API文档入口
    """
    return {
        "service": "AIEG Data Gateway API",
        "version": "v1.0",
        "description": "AI工业进化预测小游戏 - 公开数据API",
        "documentation": "/docs",
        "endpoints": {
            "latest": "/api/v1/latest - 获取最新开奖结果",
            "history": "/api/v1/history - 获取历史开奖结果",
            "health": "/api/v1/health - 健康检查"
        },
        "disclaimer": "⚠️ 本API仅用于技术研究，严禁用于赌博、博彩、彩票。详见项目DISCLAIMER.md",
        "rate_limit": "匿名用户: 10次/分钟",
        "data_source": "从BigQuery读取（已去重的历史数据）",
        "github": "https://github.com/Ww62215764/-google-ops-victory"
    }

@app.get("/api/v1/health")
async def health_check():
    """
    健康检查
    """
    return {
        "status": "ok",
        "service": "AIEG Data Gateway",
        "version": "v1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "bigquery_status": "connected"
    }

@app.get("/api/v1/latest", response_model=LatestResponse)
async def get_latest(request: Request):
    """
    获取最新开奖结果
    
    从BigQuery读取最新一期数据（去重后）
    
    注意：
    - 数据来自BigQuery，不是实时API
    - 延迟约1-5分钟（取决于采集频率）
    - 数据已去重，保证唯一性
    """
    # 限流检查
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "您已超过访问频率限制（10次/分钟），请稍后再试。",
                "retry_after": 60
            }
        )
    
    try:
        # 查询最新一期
        query = f"""
        SELECT 
            period,
            numbers,
            sum_value,
            big_small,
            odd_even,
            timestamp,
            next_issue,
            next_time,
            award_countdown
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        ORDER BY period DESC
        LIMIT 1
        """
        
        logger.info("Querying latest draw from BigQuery...")
        query_job = bq_client.query(query)
        results = list(query_job.result())
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "No data available",
                    "message": "暂无数据，请稍后再试。"
                }
            )
        
        row = results[0]
        
        # 构造响应
        draw_data = DrawData(
            period=row.period,
            numbers=list(row.numbers),
            sum=row.sum_value,
            big_small=row.big_small,
            odd_even=row.odd_even,
            timestamp=row.timestamp.isoformat() + "Z",
            next_issue=row.next_issue,
            next_time=row.next_time.isoformat() + "Z" if row.next_time else None,
            countdown=row.award_countdown
        )
        
        logger.info(f"Successfully fetched latest draw: period={row.period}")
        
        return LatestResponse(
            success=True,
            data=draw_data,
            message="Latest draw data retrieved successfully",
            request_id=f"req_{int(time() * 1000)}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "服务器内部错误，请稍后再试。"
            }
        )

@app.get("/api/v1/history", response_model=HistoryResponse)
async def get_history(
    request: Request,
    date: Optional[str] = Query(None, description="日期（YYYY-MM-DD格式）"),
    start_period: Optional[str] = Query(None, description="起始期号"),
    end_period: Optional[str] = Query(None, description="结束期号"),
    limit: int = Query(50, ge=1, le=100, description="返回数量（1-100）"),
    page: int = Query(1, ge=1, description="页码")
):
    """
    获取历史开奖结果
    
    支持按日期或期号范围查询
    
    参数说明：
    - date: 查询指定日期的数据（如：2025-10-06）
    - start_period/end_period: 查询期号范围的数据
    - limit: 每页返回的数量（默认50，最大100）
    - page: 页码（默认1）
    
    示例：
    - /api/v1/history?date=2025-10-06&limit=100
    - /api/v1/history?start_period=3344100&end_period=3344200
    """
    # 限流检查
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "您已超过访问频率限制（10次/分钟），请稍后再试。",
                "retry_after": 60
            }
        )
    
    try:
        # 构建WHERE条件
        where_clauses = []
        
        if date:
            # 验证日期格式
            try:
                datetime.strptime(date, "%Y-%m-%d")
                where_clauses.append(f"DATE(timestamp, 'Asia/Shanghai') = '{date}'")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid date format",
                        "message": "日期格式错误，请使用YYYY-MM-DD格式（如：2025-10-06）"
                    }
                )
        
        if start_period and end_period:
            where_clauses.append(f"period BETWEEN '{start_period}' AND '{end_period}'")
        elif start_period:
            where_clauses.append(f"period >= '{start_period}'")
        elif end_period:
            where_clauses.append(f"period <= '{end_period}'")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 查询总数
        count_query = f"""
        SELECT COUNT(*) as total
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE {where_sql}
        """
        
        logger.info(f"Counting history records: {where_sql}")
        count_result = list(bq_client.query(count_query).result())
        total = count_result[0].total
        
        if total == 0:
            return HistoryResponse(
                success=True,
                data={"total": 0, "results": []},
                pagination={
                    "current_page": page,
                    "total_pages": 0,
                    "total_records": 0,
                    "limit": limit
                },
                message="No data found for the specified criteria",
                request_id=f"req_{int(time() * 1000)}"
            )
        
        # 计算分页
        offset = (page - 1) * limit
        total_pages = (total + limit - 1) // limit
        
        # 查询数据
        query = f"""
        SELECT 
            period,
            numbers,
            sum_value,
            big_small,
            odd_even,
            timestamp
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE {where_sql}
        ORDER BY period DESC
        LIMIT {limit}
        OFFSET {offset}
        """
        
        logger.info(f"Querying history: limit={limit}, offset={offset}")
        query_job = bq_client.query(query)
        results = list(query_job.result())
        
        # 构造响应
        draws = []
        for row in results:
            draws.append({
                "period": row.period,
                "numbers": list(row.numbers),
                "sum": row.sum_value,
                "big_small": row.big_small,
                "odd_even": row.odd_even,
                "timestamp": row.timestamp.isoformat() + "Z"
            })
        
        logger.info(f"Successfully fetched {len(draws)} history records")
        
        return HistoryResponse(
            success=True,
            data={
                "total": total,
                "results": draws
            },
            pagination={
                "current_page": page,
                "total_pages": total_pages,
                "total_records": total,
                "limit": limit
            },
            message="Historical draw data retrieved successfully",
            request_id=f"req_{int(time() * 1000)}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "服务器内部错误，请稍后再试。"
            }
        )

@app.get("/api/v1/stats")
async def get_stats(request: Request):
    """
    获取统计信息
    
    返回数据库的基本统计信息
    """
    # 限流检查
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "您已超过访问频率限制（10次/分钟），请稍后再试。",
                "retry_after": 60
            }
        )
    
    try:
        query = f"""
        SELECT 
            COUNT(*) as total_draws,
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest,
            DATE_DIFF(CURRENT_DATE('Asia/Shanghai'), DATE(MIN(timestamp), 'Asia/Shanghai'), DAY) as days_coverage
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        """
        
        query_job = bq_client.query(query)
        result = list(query_job.result())[0]
        
        return {
            "success": True,
            "data": {
                "total_draws": result.total_draws,
                "earliest": result.earliest.isoformat() + "Z",
                "latest": result.latest.isoformat() + "Z",
                "days_coverage": result.days_coverage,
                "avg_draws_per_day": round(result.total_draws / max(result.days_coverage, 1), 1)
            },
            "message": "Statistics retrieved successfully",
            "request_id": f"req_{int(time() * 1000)}"
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "服务器内部错误，请稍后再试。"
            }
        )

# ========== 启动入口 ==========

if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        log_level="info"
    )


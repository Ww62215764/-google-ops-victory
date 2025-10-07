# 🌐 AIEG 公开数据API服务
# AIEG Public Data API Service

**服务名称**: AIEG Data Gateway  
**版本**: v1.0  
**用途**: 为研究者提供伪随机开奖数据的公开访问接口

---

## 📋 **服务说明**

### 目的

将上游数据API封装为公开服务，提供给研究者使用，同时：
- ✅ 隐藏真实上游API地址
- ✅ 保护上游业务不受影响
- ✅ 提供统一的访问接口
- ✅ 添加访问控制和限流
- ✅ 记录使用统计

---

## 🏗️ **架构设计**

```
研究者
   ↓
   ↓ 调用公开API
   ↓
┌─────────────────────────────────┐
│  Cloud Run: AIEG Data Gateway   │
│  (公开访问)                      │
│                                 │
│  - 接口封装                     │
│  - 访问限流                     │
│  - 使用统计                     │
│  - 错误处理                     │
└─────────────────────────────────┘
   ↓
   ↓ 内部调用（不对外）
   ↓
┌─────────────────────────────────┐
│  上游API (私密)                  │
│  rijb.api.storeapi.net          │
│  - 包含其他业务                  │
│  - 不对外公开                    │
└─────────────────────────────────┘
```

---

## 📡 **公开API接口**

### 1. 获取最新开奖结果

**接口**: `GET /api/v1/latest`

**请求示例**:
```bash
curl https://aieg-data-api.run.app/api/v1/latest
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "period": "3344272",
    "numbers": [0, 4, 6],
    "sum": 10,
    "big_small": "SMALL",
    "odd_even": "EVEN",
    "timestamp": "2025-10-07T00:23:30Z",
    "next_issue": "3344273",
    "next_time": "2025-10-07T00:26:00Z",
    "countdown": 150
  },
  "message": "Latest draw data",
  "request_id": "req_abc123"
}
```

### 2. 获取历史开奖结果

**接口**: `GET /api/v1/history`

**请求参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|-----|------|------|------|------|
| `date` | string | 否 | 日期（YYYY-MM-DD） | `2025-10-06` |
| `start_period` | string | 否 | 起始期号 | `3344100` |
| `end_period` | string | 否 | 结束期号 | `3344200` |
| `limit` | integer | 否 | 返回数量（1-100） | `50` |

**请求示例**:
```bash
# 获取指定日期的数据
curl "https://aieg-data-api.run.app/api/v1/history?date=2025-10-06&limit=50"

# 获取指定期号范围的数据
curl "https://aieg-data-api.run.app/api/v1/history?start_period=3344100&end_period=3344200"
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total": 463,
    "results": [
      {
        "period": "3344128",
        "numbers": [3, 7, 9],
        "sum": 19,
        "big_small": "BIG",
        "odd_even": "ODD",
        "timestamp": "2025-10-06T15:58:00Z"
      },
      {
        "period": "3344127",
        "numbers": [2, 5, 8],
        "sum": 15,
        "big_small": "BIG",
        "odd_even": "ODD",
        "timestamp": "2025-10-06T15:55:30Z"
      }
      // ... 更多数据
    ]
  },
  "pagination": {
    "current_page": 1,
    "total_pages": 10,
    "total_records": 463,
    "limit": 50
  },
  "message": "Historical draw data",
  "request_id": "req_def456"
}
```

### 3. 健康检查

**接口**: `GET /api/v1/health`

**响应示例**:
```json
{
  "status": "ok",
  "service": "AIEG Data Gateway",
  "version": "v1.0",
  "timestamp": "2025-10-07T01:30:00Z"
}
```

---

## 🔒 **访问控制**

### 限流策略

| 用户类型 | 限制 | 说明 |
|---------|------|------|
| **匿名用户** | 10次/分钟 | 基于IP限流 |
| **注册用户** | 60次/分钟 | 需要API Key |
| **研究机构** | 300次/分钟 | 需要申请 |

### API Key使用（可选）

**请求头**:
```
X-API-Key: your_api_key_here
```

---

## 💻 **实现代码**

### 完整服务代码

```python
#!/usr/bin/env python3
"""
AIEG Data Gateway API Service
公开数据API服务，封装上游数据源
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import pytz
import requests
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from pydantic import BaseModel

# 初始化
app = FastAPI(
    title="AIEG Data Gateway API",
    description="AI工业进化预测小游戏 - 公开数据API",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
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

from collections import defaultdict
from time import time

# 简单的内存限流器（生产环境应使用Redis）
rate_limiter = defaultdict(list)
RATE_LIMIT = 10  # 每分钟10次

def check_rate_limit(ip: str) -> bool:
    """检查是否超过限流"""
    now = time()
    # 清理60秒前的记录
    rate_limiter[ip] = [t for t in rate_limiter[ip] if now - t < 60]
    
    if len(rate_limiter[ip]) >= RATE_LIMIT:
        return False
    
    rate_limiter[ip].append(now)
    return True

# ========== API端点 ==========

@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "AIEG Data Gateway",
        "version": "v1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/api/v1/latest", response_model=LatestResponse)
async def get_latest(request: Request):
    """
    获取最新开奖结果
    
    从BigQuery读取最新一期数据（去重后）
    """
    # 限流检查
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
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
        
        query_job = bq_client.query(query)
        results = list(query_job.result())
        
        if not results:
            raise HTTPException(status_code=404, detail="No data available")
        
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
        
        return LatestResponse(
            success=True,
            data=draw_data,
            message="Latest draw data",
            request_id=f"req_{int(time() * 1000)}"
        )
        
    except Exception as e:
        logger.error(f"Error fetching latest data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/history", response_model=HistoryResponse)
async def get_history(
    request: Request,
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
    start_period: Optional[str] = Query(None, description="起始期号"),
    end_period: Optional[str] = Query(None, description="结束期号"),
    limit: int = Query(50, ge=1, le=100, description="返回数量")
):
    """
    获取历史开奖结果
    
    支持按日期或期号范围查询
    """
    # 限流检查
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        # 构建WHERE条件
        where_clauses = []
        
        if date:
            where_clauses.append(f"DATE(timestamp, 'Asia/Shanghai') = '{date}'")
        
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
        
        count_result = list(bq_client.query(count_query).result())
        total = count_result[0].total
        
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
        """
        
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
        
        total_pages = (total + limit - 1) // limit
        
        return HistoryResponse(
            success=True,
            data={
                "total": total,
                "results": draws
            },
            pagination={
                "current_page": 1,
                "total_pages": total_pages,
                "total_records": total,
                "limit": limit
            },
            message="Historical draw data",
            request_id=f"req_{int(time() * 1000)}"
        )
        
    except Exception as e:
        logger.error(f"Error fetching history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    """根路径 - API文档入口"""
    return {
        "service": "AIEG Data Gateway API",
        "version": "v1.0",
        "documentation": "/docs",
        "endpoints": {
            "latest": "/api/v1/latest",
            "history": "/api/v1/history",
            "health": "/api/v1/health"
        },
        "description": "AI工业进化预测小游戏 - 公开数据API",
        "disclaimer": "本API仅用于技术研究，严禁用于赌博。详见 DISCLAIMER.md"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

---

## 📦 **部署文件**

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 运行服务
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app --worker-class uvicorn.workers.UvicornWorker
```

### requirements.txt

```
fastapi==0.104.0
uvicorn==0.23.2
gunicorn==21.2.0
google-cloud-bigquery==3.17.0
requests==2.31.0
pytz==2023.3.post1
pydantic==2.4.2
```

### deploy.sh

```bash
#!/bin/bash
set -euo pipefail

PROJECT_ID="wprojectl"
SERVICE_NAME="aieg-data-gateway"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "🚀 部署 AIEG Data Gateway API..."

# 1. 构建镜像
echo "1️⃣ 构建Docker镜像..."
docker build -t ${IMAGE_NAME} .

# 2. 推送镜像
echo "2️⃣ 推送到Google Container Registry..."
docker push ${IMAGE_NAME}

# 3. 部署到Cloud Run
echo "3️⃣ 部署到Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --max-instances 10 \
  --min-instances 0 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 30 \
  --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}"

# 4. 获取URL
echo "4️⃣ 获取服务URL..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)')

echo ""
echo "✅ 部署完成！"
echo "📡 服务URL: ${SERVICE_URL}"
echo "📖 API文档: ${SERVICE_URL}/docs"
echo "🧪 测试命令: curl ${SERVICE_URL}/api/v1/latest"
```

---

## 📚 **使用文档**

### Python示例

```python
import requests

# 获取最新开奖
response = requests.get("https://aieg-data-api.run.app/api/v1/latest")
data = response.json()
print(f"最新期号: {data['data']['period']}")
print(f"开奖号码: {data['data']['numbers']}")

# 获取历史数据
response = requests.get(
    "https://aieg-data-api.run.app/api/v1/history",
    params={"date": "2025-10-06", "limit": 100}
)
history = response.json()
print(f"共 {history['data']['total']} 期数据")
```

### JavaScript示例

```javascript
// 获取最新开奖
fetch('https://aieg-data-api.run.app/api/v1/latest')
  .then(response => response.json())
  .then(data => {
    console.log('最新期号:', data.data.period);
    console.log('开奖号码:', data.data.numbers);
  });

// 获取历史数据
fetch('https://aieg-data-api.run.app/api/v1/history?date=2025-10-06&limit=100')
  .then(response => response.json())
  .then(data => {
    console.log('共', data.data.total, '期数据');
    console.log('结果:', data.data.results);
  });
```

---

## ⚠️ **免责声明**

**本API仅用于技术研究和学术交流！**

- ✅ 学习数据处理和API设计
- ✅ 研究伪随机算法
- ✅ 探索时序数据分析
- ❌ **严禁用于赌博、博彩、彩票**

详细免责声明请查看：[DISCLAIMER.md](../DISCLAIMER.md)

---

## 📞 **联系方式**

- GitHub Issues: [项目仓库](https://github.com/Ww62215764/-google-ops-victory)
- 仅接受技术问题咨询
- 不接受任何赌博、博彩相关咨询

---

**版本**: v1.0  
**最后更新**: 2025-10-07  
**维护者**: AIEG Team


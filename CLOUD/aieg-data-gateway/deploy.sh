#!/bin/bash
set -euo pipefail

# 配置
PROJECT_ID="wprojectl"
SERVICE_NAME="aieg-data-gateway"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "🚀 部署 AIEG Data Gateway API..."
echo "================================="

# 1. 构建镜像
echo ""
echo "1️⃣ 构建Docker镜像..."
docker build -t ${IMAGE_NAME} .

# 2. 推送镜像
echo ""
echo "2️⃣ 推送到Google Container Registry..."
docker push ${IMAGE_NAME}

# 3. 部署到Cloud Run
echo ""
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
  --concurrency 80 \
  --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
  --labels "service=aieg-data-gateway,purpose=public-api,version=v1"

# 4. 获取URL
echo ""
echo "4️⃣ 获取服务URL..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)')

echo ""
echo "================================="
echo "✅ 部署完成！"
echo ""
echo "📡 服务URL: ${SERVICE_URL}"
echo "📖 API文档: ${SERVICE_URL}/docs"
echo "🏥 健康检查: ${SERVICE_URL}/api/v1/health"
echo ""
echo "🧪 测试命令:"
echo "  curl ${SERVICE_URL}/api/v1/latest"
echo "  curl \"${SERVICE_URL}/api/v1/history?date=2025-10-06&limit=10\""
echo ""
echo "⚠️ 注意: 本API仅用于技术研究，严禁用于赌博！"


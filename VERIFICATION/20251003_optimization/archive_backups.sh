#!/bin/bash
# ==================================================================
# 归档备份表到GCS
# 执行时间: 2025-10-03 23:35 CST
# 作者: 15年数据架构专家
# ==================================================================

set -e

BUCKET="gs://wprojectl-storage/bigquery_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_DIR="${BUCKET}/${TIMESTAMP}"

echo "🚀 开始归档备份表到GCS..."
echo "归档目录: ${ARCHIVE_DIR}"

# 创建归档目录（注：gs不需要mkdir，直接copy即可）
echo "📁 准备归档目录: ${ARCHIVE_DIR}"

# 归档表列表
declare -a TABLES=(
  "wprojectl:pc28.comprehensive_predictions_backup_20250925_141400"
  "wprojectl:pc28.comprehensive_predictions_backup_20250925_141451"
  "wprojectl:pc28.draws_14w_backup_202509"
  "wprojectl:pc28.draws_14w_backup_20251001_170708"
  "wprojectl:pc28.draws_backup_20251003"
  "wprojectl:drawsguard.draws_backup_20251003_2216"
)

# 导出每个表
for table in "${TABLES[@]}"; do
  table_name=$(echo $table | cut -d':' -f2 | tr '.' '_')
  echo ""
  echo "📦 导出表: ${table}"
  
  bq extract \
    --destination_format=AVRO \
    --compression=SNAPPY \
    --location=us-central1 \
    "${table}" \
    "${ARCHIVE_DIR}/${table_name}_*.avro"
  
  if [ $? -eq 0 ]; then
    echo "✅ ${table} 导出成功"
  else
    echo "❌ ${table} 导出失败"
    exit 1
  fi
done

echo ""
echo "🔍 验证归档文件..."
gsutil ls -lh "${ARCHIVE_DIR}/"

echo ""
echo "📊 归档统计:"
FILE_COUNT=$(gsutil ls "${ARCHIVE_DIR}/" | wc -l)
TOTAL_SIZE=$(gsutil du -sh "${ARCHIVE_DIR}/" | awk '{print $1}')
echo "  文件数: ${FILE_COUNT}"
echo "  总大小: ${TOTAL_SIZE}"

echo ""
echo "⚠️  确认归档无误后，执行删除命令:"
echo ""
for table in "${TABLES[@]}"; do
  echo "bq rm -f -t ${table}"
done

echo ""
echo "✅ 归档完成！"
echo "归档位置: ${ARCHIVE_DIR}"


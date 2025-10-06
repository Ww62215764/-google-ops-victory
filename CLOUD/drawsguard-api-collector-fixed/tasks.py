#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys
import time

from google.cloud import bigquery

# 从主应用中导入必要的函数
# 注意：这需要确保PYTHONPATH正确设置或采用更健壮的打包方式
from main import (_send_telegram_with_retry, build_prediction_message,
                  get_telegram_config)

# 配置一个简单的日志记录器
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def get_latest_draws(bq_client: bigquery.Client, limit: int = 100) -> list:
    """从BigQuery获取最新的开奖数据"""
    logging.info(f"正在从BigQuery获取最近 {limit} 条开奖数据...")
    query = f"""
        SELECT period, timestamp, numbers, sum_value, big_small, odd_even
        FROM `wprojectl.drawsguard.draws`
        ORDER BY timestamp DESC
        LIMIT {limit}
    """
    try:
        query_job = bq_client.query(query)
        results = [dict(row) for row in query_job.result()]
        logging.info(f"成功获取 {len(results)} 条数据。")
        return results
    except Exception as e:
        logging.error(f"从BigQuery获取数据失败: {e}")
        return []


def generate_predictions(draws: list) -> list:
    """
    生成预测订单的逻辑桩。
    这是系统的核心预测引擎，目前使用一个简单的占位逻辑。
    总指挥大人，这里的逻辑需要替换为我们真正的预测模型。
    """
    if not draws:
        logging.warning("没有输入数据，无法生成预测。")
        return []

    logging.info("正在生成预测订单...")

    # 简单的占位逻辑：总是预测下一期是 "BIG" 和 "ODD"
    latest_period = draws[0]["period"]
    next_period = str(int(latest_period) + 1)

    predictions = [
        {
            "period": next_period,
            "market": "BIG_SMALL",
            "prediction": "BIG",
            "stake_u": 10,
            "p_win": 0.65,
            "ev": 0.05,
        },
        {
            "period": next_period,
            "market": "ODD_EVEN",
            "prediction": "ODD",
            "stake_u": 5,
            "p_win": 0.58,
            "ev": 0.02,
        },
    ]
    logging.info(f"为期号 {next_period} 生成了 {len(predictions)} 个预测订单。")
    return predictions


async def run_predict_and_push():
    """运行预测并推送结果"""
    logging.info("========= 开始预测任务 =========")

    bq_client = bigquery.Client(project="wprojectl")

    # 1. 获取最新数据
    latest_draws = get_latest_draws(bq_client, limit=10)

    # 2. 生成预测
    orders = generate_predictions(latest_draws)

    if not orders:
        logging.info("没有生成预测订单，任务结束。")
        print("没有生成预测订单，任务结束。")
        logging.info("========= 预测任务结束 =========")
        return

    # 3. 推送结果到Telegram
    logging.info("准备将预测结果推送到Telegram...")
    bot_token, chat_id = get_telegram_config()
    if not bot_token or not chat_id:
        logging.error("无法获取Telegram配置，推送失败。")
        return

    next_period = orders[0]["period"]
    current_timestamp = await asyncio.to_thread(time.time)
    trace_id = f"prediction_{next_period}_{int(current_timestamp)}"
    message = build_prediction_message(orders, next_period, trace_id)

    try:
        await _send_telegram_with_retry(
            bot_token, chat_id, message, next_period, trace_id
        )
        logging.info("✅ 预测结果成功推送到Telegram。")
        print("✅ 预测结果成功推送到Telegram。")
    except Exception as e:
        logging.error(f"❌ 推送预测结果到Telegram失败: {e}")
        print(f"❌ 推送预测结果到Telegram失败: {e}")

    logging.info("========= 预测任务结束 =========")


def run_backfill(hours: int):
    """运行数据回填任务（占位）"""
    logging.info(f"开始为过去 {hours} 小时执行数据回填任务...")
    # 这里应该是调用API并插入历史数据的逻辑
    print(f"正在执行 {hours} 小时的数据回填。")
    logging.info("数据回填任务完成。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行PC28采集器的一次性任务。")
    parser.add_argument(
        "--backfill-hours", type=int, help="为指定的过去小时数运行数据回填。"
    )
    parser.add_argument(
        "--predict-now", action="store_true", help="立即运行一次预测并推送结果。"
    )

    args = parser.parse_args()

    if args.backfill_hours:
        run_backfill(args.backfill_hours)
    elif args.predict_now:
        # 因为 run_predict_and_push 是一个异步函数，我们需要一个事件循环来运行它
        asyncio.run(run_predict_and_push())
    else:
        logging.warning("未指定任务。请使用 --backfill-hours 或 --predict-now。")
        print("未指定任务。正在退出。")

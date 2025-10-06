#!/usr/bin/env python3
"""
测试Telegram推送修复
验证token去除换行符后是否正常
"""

from google.cloud import secretmanager
import requests


def test_telegram_push():
    """测试Telegram推送"""
    try:
        # 获取配置
        client = secretmanager.SecretManagerServiceClient()

        # 获取bot token
        token_name = "projects/wprojectl/secrets/telegram-bot-token/versions/latest"
        token_response = client.access_secret_version(request={"name": token_name})
        bot_token = token_response.payload.data.decode("UTF-8").strip()  # 去除换行

        # 获取chat id
        chat_name = "projects/wprojectl/secrets/telegram-chat-id/versions/latest"
        chat_response = client.access_secret_version(request={"name": chat_name})
        chat_id = chat_response.payload.data.decode("UTF-8").strip()  # 去除换行

        print(f"✅ Bot Token长度: {len(bot_token)}")
        print(f"✅ Chat ID长度: {len(chat_id)}")
        print(f"✅ Bot Token包含换行符: {repr(bot_token)}")
        print(f"✅ Chat ID包含换行符: {repr(chat_id)}")

        # 测试消息
        message = (
            "🧪 **Telegram推送测试**\n\n"
            "📅 测试时间: 2025-10-03 23:59\n"
            "🎯 目的: 验证修复后的推送功能\n"
            "✅ 状态: 修复完成，等待实战验证\n\n"
            "如果您收到这条消息，说明推送功能正常！🎉"
        )

        # 发送测试消息
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_notification": False,
        }

        print("\n📤 发送测试消息到Telegram...")
        print(f"URL: {url[:50]}...")

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        print("✅ Telegram推送成功！")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        return True

    except Exception as e:
        print(f"❌ Telegram推送失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Telegram推送修复验证")
    print("=" * 60)

    success = test_telegram_push()

    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过！Telegram推送功能正常")
        print("⏳ 等待下一期开奖（3342922）实战验证")
    else:
        print("❌ 测试失败！需要进一步排查")
    print("=" * 60)

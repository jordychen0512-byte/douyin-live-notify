import asyncio
import json
import os
from pathlib import Path

import requests
from streamget import DouyinLiveStream


# =========================
# 要監控的抖音直播間
# =========================
STREAMERS = {
    "629179434631": {
        "name": "威威門主｜天辰阁",
        "url": "https://live.douyin.com/629179434631",
    },
    "967062364422": {
        "name": "盾反威威｜陶帅帅",
        "url": "https://live.douyin.com/967062364422",
    },
    "827018709286": {
        "name": "老牌威威｜齐天",
        "url": "https://live.douyin.com/827018709286",
    },
}

STATE_FILE = Path("state.json")
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def load_state():
    """讀取上一次的直播狀態。"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {room_id: False for room_id in STREAMERS}


def save_state(state):
    """保存直播狀態，避免每次檢查都重複通知。"""
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


async def check_stream(streamer):
    """向抖音取得直播間目前狀態。"""
    live = DouyinLiveStream()

    data = await live.fetch_web_stream_data(streamer["url"])

    return {
        "is_live": data.get("status") == 2,
        "title": data.get("title") or "抖音直播",
        "anchor_name": data.get("anchor_name") or streamer["name"],
    }


def send_discord_notification(streamer, info):
    """傳送 Discord 開播通知。"""
    if not WEBHOOK_URL:
        print("❌ 找不到 DISCORD_WEBHOOK_URL")
        return False

payload = {
    "content": f"@everyone\n\n🔴 **{streamer['name']} 開始直播啦！**",
    "embeds": [
        {
            "title": info["title"],
            "url": streamer["url"],
            "description": "🇨🇳 抖音｜點擊標題前往直播",
            "color": 15158332,
        }
    ],
    "allowed_mentions": {
        "parse": ["everyone"]
    },
}

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()

        print(f"✅ 已通知：{streamer['name']}")
        return True

    except Exception as e:
        print(f"❌ Discord 通知失敗：{e}")
        return False


async def main():
    state = load_state()

    print("================================")
    print("開始檢查抖音直播狀態")
    print("================================")

    for room_id, streamer in STREAMERS.items():

        # 如果是第一次加入這個主播
        if room_id not in state:
            state[room_id] = False

        previous_live = state[room_id]

        try:
            info = await check_stream(streamer)

        except Exception as e:
            # 抖音偶爾可能擋請求。
            # 發生錯誤時保留原本狀態，避免誤判下播。
            print(f"⚠️ {streamer['name']} 檢查失敗：{e}")
            continue

        current_live = info["is_live"]

        if current_live:
            print(f"🔴 {streamer['name']}：直播中")

            # Offline → Live 才發通知
            if not previous_live:
                success = send_discord_notification(streamer, info)

                # Discord 成功收到後才記錄成直播中
                if success:
                    state[room_id] = True

        else:
            print(f"⚫ {streamer['name']}：未開播")

            # Live → Offline
            if previous_live:
                print(f"↘️ {streamer['name']} 已下播，重新等待下一次開播")
                state[room_id] = False

    save_state(state)


if __name__ == "__main__":
    asyncio.run(main())

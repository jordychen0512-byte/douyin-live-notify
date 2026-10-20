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
    "23531668627": {
        "name": "當代選手｜争锋瑾",
        "url": "https://live.douyin.com/23531668627",
    },
}

STREAMERS["bilibili:12859122"] = {
    "name": "小璇天下第一好",
    "url": "https://live.bilibili.com/12859122",
    "platform": "bilibili",
    "room_id": 12859122,
    "uid": 345786891,
}

STATE_FILE = Path("state.json")
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def load_state():
    """讀取上一次的直播狀態。"""
    if STATE_FILE.exists():
        try:
            return json.loads(
                STATE_FILE.read_text(encoding="utf-8")
            )
        except Exception:
            pass

    return {
        room_id: False
        for room_id in STREAMERS
    }


def save_state(state):
    """保存直播狀態，避免每次檢查都重複通知。"""
    STATE_FILE.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8",
    )


async def check_stream(streamer):
    """向對應平台取得直播間目前狀態。"""
    if streamer.get("platform") == "bilibili":
        return await asyncio.to_thread(check_bilibili_stream, streamer)

    live = DouyinLiveStream()

    data = await live.fetch_web_stream_data(
        streamer["url"]
    )

    return {
        "is_live": data.get("status") == 2,
        "title": data.get("title") or "抖音直播",
        "anchor_name":
            data.get("anchor_name")
            or streamer["name"],
    }


def check_bilibili_stream(streamer):
    """查詢失敗或資料異常時拋出例外，讓主流程保留上次狀態。"""
    response = requests.get(
        "https://api.live.bilibili.com/room/v1/Room/get_info",
        params={"room_id": streamer["room_id"]},
        headers={"User-Agent": "Mozilla/5.0", "Referer": streamer["url"]},
        timeout=15,
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or result.get("code") != 0:
        raise ValueError("Bilibili API 查詢失敗")
    data = result.get("data")
    if not isinstance(data, dict):
        raise ValueError("Bilibili API 缺少直播間資料")
    if data.get("uid") != streamer["uid"]:
        raise ValueError("Bilibili 直播間 UID 與設定不符")
    status = data.get("live_status")
    if type(status) is not int or status not in (0, 1, 2):
        raise ValueError("Bilibili 回傳未知直播狀態")
    return {
        "is_live": status == 1,
        "title": data.get("title") or "Bilibili 直播",
        "anchor_name": streamer["name"],
    }


def send_discord_notification(streamer, info):
    """傳送 Discord 開播通知。"""

    if not WEBHOOK_URL:
        print("❌ 找不到 DISCORD_WEBHOOK_URL")
        return False

    payload = {
        "content": (
            f"@everyone\n\n"
            f"🔴 **{streamer['name']} 開始直播啦！**"
        ),
        "embeds": [
            {
                "title": info["title"],
                "url": streamer["url"],
                "description":
                    ("📺 Bilibili｜點擊標題前往直播"
                     if streamer.get("platform") == "bilibili"
                     else "🇨🇳 抖音｜點擊標題前往直播"),
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

        print(
            f"✅ 已通知：{streamer['name']}"
        )

        return True

    except Exception as e:
        print(
            f"❌ Discord 通知失敗：{e}"
        )

        return False


async def main():
    state = load_state()

    print("================================")
    print("開始檢查抖音 / Bilibili 直播狀態")
    print("================================")

    for room_id, streamer in STREAMERS.items():

        # 第一次加入的新主播
        if room_id not in state:
            state[room_id] = False

        previous_live = state[room_id]

        try:
            info = await check_stream(
                streamer
            )

        except Exception as e:
            # 抖音偶爾可能擋請求
            # 保留原本狀態避免誤判
            print(
                f"⚠️ {streamer['name']} "
                f"檢查失敗：{e}"
            )
            continue

        current_live = info["is_live"]

        if current_live:

            print(
                f"🔴 {streamer['name']}：直播中"
            )

            # Offline → Live 才通知
            if not previous_live:

                success = (
                    send_discord_notification(
                        streamer,
                        info,
                    )
                )

                if success:
                    state[room_id] = True

        else:

            print(
                f"⚫ {streamer['name']}：未開播"
            )

            # Live → Offline
            if previous_live:

                print(
                    f"↘️ {streamer['name']} "
                    "已下播，重新等待下一次開播"
                )

                state[room_id] = False

    save_state(state)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import importlib.util
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

# These tests exercise monitor logic without network access or Discord messages.
for name in ("requests", "streamget"):
    if importlib.util.find_spec(name) is None:
        sys.modules[name] = types.ModuleType(name)
        if name == "streamget":
            sys.modules[name].DouyinLiveStream = Mock()

import monitor


class BilibiliTests(unittest.TestCase):
    def setUp(self):
        self.streamer = monitor.STREAMERS["bilibili:12859122"]

    def query(self, result):
        response = Mock()
        response.json.return_value = result
        with patch.object(monitor.requests, "get", return_value=response, create=True):
            return monitor.check_bilibili_stream(self.streamer)

    def test_live_offline_and_replay(self):
        for status in (0, 1, 2):
            with self.subTest(status=status):
                info = self.query({"code": 0, "data": {
                    "uid": 345786891, "live_status": status, "title": "test"}})
                self.assertEqual(info["is_live"], status == 1)
                self.assertEqual(info["title"], "test")

    def test_invalid_responses_raise(self):
        for result in ({"code": -400}, {"code": 0},
                       {"code": 0, "data": {"uid": 1, "live_status": 1}},
                       *({"code": 0, "data": {"uid": 345786891, "live_status": s}}
                         for s in (None, True, "1", 3))):
            with self.subTest(result=result), self.assertRaises(ValueError):
                self.query(result)

    def test_platform_notification(self):
        with patch.object(monitor, "WEBHOOK_URL", "https://example.invalid"), \
             patch.object(monitor.requests, "post", return_value=Mock(), create=True) as post:
            self.assertTrue(monitor.send_discord_notification(self.streamer, {"title": "test"}))
            payload = post.call_args.kwargs["json"]
            self.assertIn("Bilibili", payload["embeds"][0]["description"])
            self.assertEqual(payload["embeds"][0]["url"], self.streamer["url"])

    def test_state_transitions_and_failures(self):
        key = "bilibili:12859122"
        state = {key: False}
        with patch.object(monitor, "STREAMERS", {key: self.streamer}), \
             patch.object(monitor, "load_state", return_value=state), \
             patch.object(monitor, "save_state"), \
             patch.object(monitor, "check_stream", new_callable=AsyncMock) as check, \
             patch.object(monitor, "send_discord_notification", return_value=True) as send:
            check.return_value = {"is_live": True}
            asyncio.run(monitor.main())
            asyncio.run(monitor.main())
            self.assertEqual(send.call_count, 1)
            check.side_effect = ValueError("API error")
            asyncio.run(monitor.main())
            self.assertTrue(state[key])
            check.side_effect = None
            check.return_value = {"is_live": False}
            asyncio.run(monitor.main())
            self.assertFalse(state[key])
            check.return_value = {"is_live": True}
            send.return_value = False
            asyncio.run(monitor.main())
            self.assertFalse(state[key])
            send.return_value = True
            asyncio.run(monitor.main())
            self.assertTrue(state[key])


if __name__ == "__main__":
    unittest.main()

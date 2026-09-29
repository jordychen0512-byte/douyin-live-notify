# 抖音直播通知

檢查指定抖音直播間，在記錄狀態由未開播變成直播中時，透過 Discord Webhook 發送 `@everyone` 通知。

## 目前監測名單

| 主播 | 直播間 |
| --- | --- |
| 威威門主｜天辰阁 | https://live.douyin.com/629179434631 |
| 盾反威威｜陶帅帅 | https://live.douyin.com/967062364422 |
| 老牌威威｜齐天 | https://live.douyin.com/827018709286 |
| 當代選手｜争锋瑾 | https://live.douyin.com/23531668627 |

名單定義於 `monitor.py` 的 `STREAMERS`。程式依序透過 `streamget.DouyinLiveStream` 查詢，以回傳資料的 `status == 2` 判定直播中，其他值判定未開播；目前沒有查詢重試或嚴格狀態驗證。

## 開播與通知規則

- 上次狀態為 `false`、本次判定直播中時，發送含 `@everyone`、主播名稱、直播標題與連結的 Discord 通知。
- Webhook 成功後才把狀態設為 `true`；發送失敗則保留原狀態，下輪若仍直播會再嘗試。
- 已記錄為直播中時不重複通知；判定未開播後改回 `false`，等待下一次開播，不發下播通知。
- 查詢拋出例外時保留上次狀態。第一次執行或新增主播預設未開播，因此若當時正在直播會立即通知。
- 去重依據是每次檢查記錄的布林狀態，沒有直播場次 ID；如果兩次檢查之間下播又重開，可能無法辨識為新一場。

Actions 在檢查步驟成功後，將有變更的 `state.json` 提交回執行分支；推送最多嘗試 3 次，遠端狀態衝突時中止。狀態未成功保存可能使後續執行再次通知。

## 錯誤處理

Workflow 的步驟失敗且有設定 Webhook 時，會傳送含 Actions 執行連結的失敗訊息。不過，程式已捕捉的單一主播查詢或通知錯誤只寫入日誌，不一定讓 workflow 失敗；綠色執行結果不代表所有主播都查詢成功。

## 排程與狀態保存

GitHub Actions 的 `.github/workflows/check-live.yml` 設有 `*/5 * * * *` 排程，也接受手動或外部 `workflow_dispatch`。這是每 5 分鐘的觸發設定，實際開始時間仍可能延遲或排隊。

程式庫另附共享 Cloudflare Worker `douyin-live-notify-scheduler`，每 5 分鐘分別觸發本專案與 `youtube-live-notify` 的 `main` 分支；其中一個觸發失敗不會阻止另一個。兩個 repo 都保留 GitHub 原生排程，若兩種排程皆啟用，可能產生額外檢查。

共享 Worker 的程式也存放於 YouTube repo 的 `scheduler/`；部署任一份都會更新同名 Worker，應保留兩個觸發目標。

Workflow 使用 Python 3.12，安裝 `requirements.txt` 及 `streamget install-node` 後執行監控；工作上限為 4 分鐘，同一 concurrency group 不取消正在執行的工作。

## 必要 Secrets

- GitHub Actions：`DISCORD_WEBHOOK_URL`。通知頻道由此 Webhook 決定。
- Cloudflare Worker：`GITHUB_TOKEN`。若使用 fine-grained PAT，須同時授權 `jordychen0512-byte/douyin-live-notify` 與 `jordychen0512-byte/youtube-live-notify`，Repository permissions 開啟 Actions **Read and write**。

## 部署排程器

在 `scheduler/` 目錄執行：

```sh
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npx wrangler deploy
```

`scheduler/wrangler.jsonc` 的 Cron 為 `*/5 * * * *`。Worker 對網路錯誤或 GitHub 5xx 最多嘗試 2 次，其他 HTTP 錯誤直接失敗。程式庫內的設定不代表 Cloudflare 線上部署已同步；部署狀態需以 Cloudflare 設定與日誌確認。

## 本機執行與新增主播

在 repo 根目錄使用 Python 3.12：

```powershell
python -m pip install --requirement requirements.txt
streamget install-node
$env:DISCORD_WEBHOOK_URL = "你的 Discord Webhook URL"
python monitor.py
```

修改 `monitor.py` 的 `STREAMERS`，加入唯一 key、`name` 與 `url`。程式會為新 key 自動建立 `false` 狀態，不必手動編輯 `state.json`。

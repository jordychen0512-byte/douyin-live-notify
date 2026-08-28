# douyin-live-notify

每五分鐘檢查指定的抖音直播間，並在 Offline → Live 時傳送 Discord 通知。

## 架構

Cloudflare Worker Cron 是唯一排程來源。它每五分鐘呼叫 GitHub
`workflow_dispatch` API，再由 GitHub Actions 執行 `monitor.py`。

GitHub Actions 原生 `schedule` 不作為排程來源，避免排程延遲或遭丟棄。

## 必要 Secrets

- GitHub Actions：`DISCORD_WEBHOOK_URL`
- Cloudflare Worker：`GITHUB_TOKEN`

`GITHUB_TOKEN` 應使用 fine-grained personal access token，只授權
`jordychen0512-byte/douyin-live-notify`，Repository permissions 僅開啟
Actions 的 Read and write。

## 部署排程器

在 `scheduler` 目錄中登入並部署：

```sh
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npx wrangler deploy
```

Cron 設定在 `scheduler/wrangler.jsonc`，部署後可能需要最多 15 分鐘才會在
Cloudflare 全球網路完全生效。

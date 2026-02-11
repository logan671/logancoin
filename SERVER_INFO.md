# Server Info (Dsprd)

## SSH
- Host: 47.80.2.58
- User: ecs-user
- Key: /Users/hwlee/.ssh/keys/despread-business.pem
- Command:
  ssh -i /Users/hwlee/.ssh/keys/despread-business.pem ecs-user@47.80.2.58

## ProjectB (Polymarket Whale Activity)
- Path: /home/ecs-user/ProjectB-polymarketwhaleactivity
- DBs:
  - /home/ecs-user/ProjectB-polymarketwhaleactivity/whale_activity.db
  - /home/ecs-user/ProjectB-polymarketwhaleactivity/whale_activity_new_wallets.db
- Env: /etc/whaleactivity.env
- Env contents:
  - WHALE_ACTIVITY_EMAIL_FROM=logan@despread.io
  - WHALE_ACTIVITY_EMAIL_TO=logan@despread.io
  - WHALE_ACTIVITY_SMTP_PASSWORD=wyypcypirgkfrnct
  - WHALE_ACTIVITY_DB=/home/ecs-user/ProjectB-polymarketwhaleactivity/whale_activity.db
  - WHALE_ACTIVITY_NEW_WALLETS_DB=/home/ecs-user/ProjectB-polymarketwhaleactivity/whale_activity_new_wallets.db
  - WHALE_ACTIVITY_SHEETS_ID=1Xib8yEPkVCmIsoRSv71UXJsGiM8ZwBWPaV0Kk_lU65I
  - WHALE_ACTIVITY_SA_JSON=/home/ecs-user/ProjectB-polymarketwhaleactivity/secrets/service-account.json
  - WHALE_ACTIVITY_SHEETS_BATCH_LIMIT=500
- Service account JSON (local copy): /Users/hwlee/Desktop/despread-youtube-pr-7bedf1db2c5b.json
- Service account JSON (server): /home/ecs-user/ProjectB-polymarketwhaleactivity/secrets/service-account.json
- Services:
  - whaleactivity.service
  - whaleactivity-dailyreport.service (+ timer)
  - whaleactivity-sheets.service (+ timer)

## ProjectE (Polymarket TG Tracker)
- Path: /home/ecs-user/ProjectE-PolymarketTGtracker
- Env: /etc/projecte.env
- Env contents:
  - TELEGRAM_BOT_TOKEN=8562513551:AAFvx0VKKiEj1PVoLD8IaQM0S5j8r1bUAXM
  - TELEGRAM_CHANNEL_ID=-1003834262370
  - POLYGON_RPC_URL=https://rpc.ankr.com/polygon/276edb3bae165feb919c7ae2590ef0e8f1a8d9f4b44fe0800d4ce038398573ab
  - POLL_SECONDS=10
- Venv: /home/ecs-user/ProjectE-PolymarketTGtracker/.venv
- Logs:
  - /home/ecs-user/ProjectE-PolymarketTGtracker/logs/tracker.log
- Services:
  - projecte-tracker.service
  - projecte-bot.service

## Google Apps Script (legacy web app attempt)
- URL (latest): https://script.google.com/macros/s/AKfycbzK0_-ytZTVpFqyT_RG_da2XClcQG-rWN4Y-ujkhapyBFfrH0s80alyc0zgkqqfpmWk/exec

## Quick checks
- systemctl status whaleactivity.service
- systemctl status whaleactivity-dailyreport.service
- systemctl status whaleactivity-sheets.service
- systemctl status projecte-tracker.service
- systemctl status projecte-bot.service

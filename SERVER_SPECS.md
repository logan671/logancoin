# Server Specs (current)

Checked: 2026-02-09 13:08 UTC

- CPU: 4 vCPU (x86_64)
- RAM: 7.1 GiB total
- Disk: 40 GiB (root)
- OS: Ubuntu 24.04 LTS

## Usage snapshot
- Load avg: ~0.35
- Memory used: ~2.7 GiB
- Largest process: ProjectE tracker (RSS ~2.3 GiB)

## Service memory (systemd)
- projecte-tracker.service: 2.2 GiB (peak 4.1 GiB)
- whaleactivity.service: 14.2 MiB (peak 14.7 MiB)
- projecte-bot.service: (check when needed)
- whaleactivity-dailyreport.service: (timer, short-lived)
- whaleactivity-sheets.service: (timer, short-lived)

## Notes
- RAM upgraded from <1 GiB to 7.1 GiB.
- Swap: 0B (not configured)

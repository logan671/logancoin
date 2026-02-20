# ProjectK - polycopyman

## Structure
- `backend/`: API server (`/health`, `/pairs`, `/runtime/services`)
- `backend/wallet_cli.py`: vault key_ref registration CLI (`add`, `list`)
- `bot/`: Telegram registration bot (`/addpair`, `/rmpair`, `/rmpairall`, `/listpairs`, `/whereami`, `/site`, `/status`)
- `worker/`: signal worker + source watcher
- `web/`: dashboard skeleton
- `schema.sql`: database schema
- `seed.sql`: initial sample data
- `run_seed.sh`: reset + seed database helper
- `SECURITY_POLICY.md`: key/mnemonic handling policy

## Quick Start
1. Build seed DB
2. Register wallet mnemonic to vault (`python3 -m backend.wallet_cli add wallet_1`)
3. Start backend API
4. Start telegram register bot
5. Start worker (`PROJECTK_EXECUTOR_MODE=live` for real execution)
6. Start web server

See `휘릭휘릭메모장.md` for copy-paste commands.

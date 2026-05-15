from dotenv import load_dotenv
load_dotenv()

import os

# ─── Telegram ────────────────────────────────────────────────────────────────
BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
SCOUT_GROUP_ID   = int(os.getenv("SCOUT_GROUP_ID", "0"))
MANAGER_GROUP_ID = int(os.getenv("MANAGER_GROUP_ID", "0"))

# ─── Oracle Database ─────────────────────────────────────────────────────────
ORA_USER        = os.getenv("ORA_USER", "ADMIN")
ORA_PASS        = os.getenv("ORA_PASS", "")
ORA_DSN         = os.getenv("ORA_DSN", "")
ORA_WALLET      = os.getenv("ORA_WALLET", "")
ORA_WALLET_PASS = os.getenv("ORA_WALLET_PASS", "")

# ─── Логика ──────────────────────────────────────────────────────────────────
IDLE_THRESHOLD_MIN = int(os.getenv("IDLE_THRESHOLD_MIN", "20"))
DAILY_REPORT_TIME  = os.getenv("DAILY_REPORT_TIME", "21:00")
TIMEZONE           = "Asia/Almaty"

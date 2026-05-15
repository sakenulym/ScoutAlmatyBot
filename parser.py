import os

# ─── Telegram ────────────────────────────────────────────────────────────────
BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
SCOUT_GROUP_ID   = int(os.getenv("SCOUT_GROUP_ID", "0"))    # группа скаутов
MANAGER_GROUP_ID = int(os.getenv("MANAGER_GROUP_ID", "0"))  # группа руководителей

# ─── Oracle Database ─────────────────────────────────────────────────────────
ORA_USER   = os.getenv("ORA_USER", "ADMIN")
ORA_PASS   = os.getenv("ORA_PASS", "")
ORA_DSN    = os.getenv("ORA_DSN", "")            # host:port/service_name
ORA_WALLET = os.getenv("ORA_WALLET", "")         # путь к папке с wallet (если нужен)

# ─── Логика ──────────────────────────────────────────────────────────────────
IDLE_THRESHOLD_MIN = int(os.getenv("IDLE_THRESHOLD_MIN", "20"))  # минут = простой
DAILY_REPORT_TIME  = os.getenv("DAILY_REPORT_TIME", "21:00")     # HH:MM Алматы (UTC+5)
TIMEZONE           = "Asia/Almaty"

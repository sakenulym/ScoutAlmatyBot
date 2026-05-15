import logging
from datetime import timezone

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, filters

from config import SCOUT_GROUP_ID, MANAGER_GROUP_ID, IDLE_THRESHOLD_MIN
from db import get_conn
from parser import parse_report, parse_break
from reports import build_shift_report, build_all_scouts_report

logger = logging.getLogger(__name__)


# ─── Вспомогательные ─────────────────────────────────────────────────────────

async def ensure_scout(scout_id: int, username: str, full_name: str) -> None:
    """Регистрирует скаута если его ещё нет в БД."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "MERGE INTO scouts s USING dual ON (s.user_id = :uid) "
                "WHEN NOT MATCHED THEN INSERT (user_id, username, full_name) "
                "VALUES (:uid, :uname, :fname)",
                uid=scout_id, uname=username[:100], fname=full_name[:200],
            )
        conn.commit()


# ─── Обработчик сообщений группы скаутов ─────────────────────────────────────

async def handle_group_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or msg.chat_id != SCOUT_GROUP_ID:
        return

    user      = msg.from_user
    scout_id  = user.id
    username  = user.username or ""
    full_name = user.full_name or ""
    text      = (msg.text or msg.caption or "").strip()
    msg_time  = msg.date.replace(tzinfo=timezone.utc)

    if not text:
        return

    await ensure_scout(scout_id, username, full_name)

    # 1. Перерыв?
    brk = parse_break(text)
    if brk:
        await _handle_break(scout_id, brk, msg_time)
        return

    # 2. Отчёт о самокатах?
    rep = parse_report(text)
    if rep:
        await _handle_report(scout_id, text, rep, msg_time, ctx)


# ─── Сохранение отчёта ───────────────────────────────────────────────────────

async def _handle_report(scout_id, raw_text, rep, msg_time, ctx) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Сохраняем отчёт
            cur.execute(
                "INSERT INTO reports (scout_id, msg_time, raw_text, parking, scooter_cnt) "
                "VALUES (:sid, :mt, :rt, :pk, :cnt)",
                sid=scout_id, mt=msg_time,
                rt=raw_text[:2000], pk=rep.parking[:300], cnt=rep.scooter_count,
            )

            # Ищем предыдущий отчёт
            cur.execute(
                "SELECT msg_time FROM reports "
                "WHERE scout_id = :sid AND msg_time < :mt "
                "ORDER BY msg_time DESC FETCH FIRST 1 ROWS ONLY",
                sid=scout_id, mt=msg_time,
            )
            row = cur.fetchone()
        conn.commit()

    if not row:
        return

    prev_time = row[0].replace(tzinfo=timezone.utc)
    gap_min   = (msg_time - prev_time).total_seconds() / 60
    gap_min   = await _subtract_breaks(scout_id, prev_time, msg_time, gap_min)

    if gap_min > IDLE_THRESHOLD_MIN:
        await _log_idle(scout_id, prev_time, msg_time, gap_min)
        await _alert_idle(scout_id, gap_min, ctx)


# ─── Перерывы ────────────────────────────────────────────────────────────────

async def _handle_break(scout_id, brk, msg_time) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            if brk.is_end:
                # Закрываем открытый перерыв
                cur.execute(
                    "UPDATE breaks SET end_time = :et "
                    "WHERE scout_id = :sid AND end_time IS NULL",
                    et=msg_time, sid=scout_id,
                )
            else:
                # Закрываем предыдущий (если не закрыт) и открываем новый
                cur.execute(
                    "UPDATE breaks SET end_time = :et "
                    "WHERE scout_id = :sid AND end_time IS NULL",
                    et=msg_time, sid=scout_id,
                )
                cur.execute(
                    "INSERT INTO breaks (scout_id, break_type, start_time) "
                    "VALUES (:sid, :bt, :st)",
                    sid=scout_id, bt=brk.break_type, st=msg_time,
                )
        conn.commit()


async def _subtract_breaks(scout_id, from_dt, to_dt, gap_min) -> float:
    """Вычитает время перерывов из интервала."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT start_time, NVL(end_time, :to_dt) "
                "FROM breaks "
                "WHERE scout_id = :sid AND start_time < :to_dt AND NVL(end_time, :to_dt) > :from_dt",
                to_dt=to_dt, sid=scout_id, from_dt=from_dt,
            )
            for start, end in cur.fetchall():
                overlap = (min(end, to_dt) - max(start, from_dt)).total_seconds() / 60
                gap_min -= max(0.0, overlap)
    return max(0.0, gap_min)


# ─── Простой ─────────────────────────────────────────────────────────────────

async def _log_idle(scout_id, start, end, gap_min) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO idle_logs (scout_id, idle_start, idle_end, gap_minutes) "
                "VALUES (:sid, :s, :e, :g)",
                sid=scout_id, s=start, e=end, g=round(gap_min),
            )
        conn.commit()


async def _alert_idle(scout_id, gap_min, ctx) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, full_name FROM scouts WHERE user_id = :sid",
                sid=scout_id,
            )
            row = cur.fetchone()
    if not row:
        return
    uname, fname = row
    name = fname or f"@{uname}"
    await ctx.bot.send_message(
        MANAGER_GROUP_ID,
        f"⚠️ <b>Простой: {name}</b>\n"
        f"Нет отчётов <b>{round(gap_min)} мин.</b>",
        parse_mode="HTML",
    )


# ─── Команды менеджера ────────────────────────────────────────────────────────

async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/report @username — отчёт по скауту за сегодня"""
    if not ctx.args:
        await update.message.reply_text("Использование: /report @username")
        return
    username = ctx.args[0].lstrip("@")
    text = await build_shift_report(username)
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/all — сводка по всем скаутам за сегодня"""
    text = await build_all_scouts_report()
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_idle(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/idle — список простоев за сегодня"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT s.full_name, i.idle_start, i.gap_minutes "
                "FROM idle_logs i JOIN scouts s ON s.user_id = i.scout_id "
                "WHERE TRUNC(i.idle_start) = TRUNC(SYSDATE) "
                "ORDER BY i.idle_start",
            )
            rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("Простоев сегодня нет ✅")
        return

    lines = ["<b>⏸ Простои сегодня:</b>"]
    for fname, start, mins in rows:
        lines.append(f"• {fname} — {start.strftime('%H:%M')} ({mins} мин)")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — список команд"""
    await update.message.reply_text(
        "<b>Команды бота:</b>\n\n"
        "/report @username — отчёт по скауту за сегодня\n"
        "/all — сводка по всем скаутам\n"
        "/idle — простои за сегодня\n"
        "/help — эта справка",
        parse_mode="HTML",
    )


# ─── Регистрация ─────────────────────────────────────────────────────────────

def register_handlers(app) -> None:
    app.add_handler(MessageHandler(
        filters.Chat(SCOUT_GROUP_ID) & (filters.TEXT | filters.CAPTION),
        handle_group_message,
    ))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("all",    cmd_all))
    app.add_handler(CommandHandler("idle",   cmd_idle))
    app.add_handler(CommandHandler("help",   cmd_help))

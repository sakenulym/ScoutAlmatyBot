from datetime import date
from db import get_conn


async def build_shift_report(username: str) -> str:
    """Отчёт по одному скауту за сегодня."""
    with get_conn() as conn:
        with conn.cursor() as cur:

            cur.execute(
                "SELECT user_id, full_name FROM scouts "
                "WHERE LOWER(username) = LOWER(:u)",
                u=username,
            )
            row = cur.fetchone()
            if not row:
                return f"❌ Скаут @{username} не найден"
            sid, fname = row

            # Первый / последний отчёт, сумма самокатов
            cur.execute(
                "SELECT MIN(msg_time), MAX(msg_time), "
                "       NVL(SUM(scooter_cnt), 0), COUNT(*) "
                "FROM reports "
                "WHERE scout_id = :sid AND TRUNC(msg_time) = TRUNC(SYSDATE)",
                sid=sid,
            )
            first_t, last_t, total_sc, rep_cnt = cur.fetchone()

            if not first_t:
                return f"📭 {fname}: отчётов сегодня нет"

            # Перерывы
            cur.execute(
                "SELECT COUNT(*), "
                "       NVL(SUM((NVL(end_time, SYSDATE) - start_time) * 24 * 60), 0) "
                "FROM breaks "
                "WHERE scout_id = :sid AND TRUNC(start_time) = TRUNC(SYSDATE)",
                sid=sid,
            )
            br_cnt, br_min = cur.fetchone()
            br_min = int(br_min or 0)

            # Простои
            cur.execute(
                "SELECT NVL(SUM(gap_minutes), 0), COUNT(*) "
                "FROM idle_logs "
                "WHERE scout_id = :sid AND TRUNC(idle_start) = TRUNC(SYSDATE)",
                sid=sid,
            )
            idle_min, idle_cnt = cur.fetchone()
            idle_min = int(idle_min or 0)

    shift_sec = (last_t - first_t).total_seconds()
    shift_h   = int(shift_sec // 3600)
    shift_m   = int((shift_sec % 3600) // 60)

    return (
        f"<b>📊 Смена: {fname}</b>\n"
        f"🕐 {first_t.strftime('%H:%M')} → {last_t.strftime('%H:%M')} "
        f"({shift_h}ч {shift_m}мин)\n"
        f"🛴 Самокатов перевезено: <b>{total_sc}</b>\n"
        f"📋 Отчётов отправлено: {rep_cnt}\n"
        f"☕ Перерывов: {br_cnt} ({br_min} мин)\n"
        f"⏸ Простоев: {idle_cnt} ({idle_min} мин)"
    )


async def build_all_scouts_report() -> str:
    """Сводный отчёт по всем скаутам за сегодня."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT s.full_name, "
                "       MIN(r.msg_time), MAX(r.msg_time), "
                "       NVL(SUM(r.scooter_cnt), 0), COUNT(r.id) "
                "FROM reports r "
                "JOIN scouts s ON s.user_id = r.scout_id "
                "WHERE TRUNC(r.msg_time) = TRUNC(SYSDATE) "
                "GROUP BY s.full_name "
                "ORDER BY SUM(r.scooter_cnt) DESC",
            )
            rows = cur.fetchall()

    if not rows:
        return f"📭 Сегодня ({date.today().strftime('%d.%m.%Y')}) отчётов нет"

    lines = [f"<b>📊 Сводка за {date.today().strftime('%d.%m.%Y')}</b>\n"]
    total = 0
    for fname, ft, lt, sc, cnt in rows:
        h = int((lt - ft).total_seconds() // 3600)
        m = int(((lt - ft).total_seconds() % 3600) // 60)
        lines.append(
            f"👤 <b>{fname}</b>\n"
            f"   🛴 {sc} самокатов | ⏱ {h}ч {m}м | 📋 {cnt} отчётов"
        )
        total += int(sc or 0)

    lines.append(f"\n<b>Итого самокатов сегодня: {total} 🛴</b>")
    return "\n".join(lines)

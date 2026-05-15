import re
from dataclasses import dataclass
from typing import Optional

# ─── Паттерн отчёта ──────────────────────────────────────────────────────────
# Пример: "Парковка Алматы  S.290030, eVIN: 110108121475, Ninebot SL 90
#          S.258246, eVIN: 110108072714, Ninebot SL 90  Итого: 2"
REPORT_RE = re.compile(
    r"(Парковка\s+\S+.*?)"
    r"[Ии]того:?\s*(\d+)",
    re.IGNORECASE | re.DOTALL,
)

# Подсчёт самокатов по кол-ву eVIN если "Итого" не указано
EVIN_RE = re.compile(r"eVIN", re.IGNORECASE)

# ─── Паттерн перерыва ────────────────────────────────────────────────────────
BREAK_RE = re.compile(
    r"\b(обед|ужин|lunch|dinner|перерыв|break)\b",
    re.IGNORECASE,
)

# ─── Паттерн конца перерыва ──────────────────────────────────────────────────
END_BREAK_RE = re.compile(
    r"\b(вернулся|вернулась|продолжаю|работаю|back|returned)\b",
    re.IGNORECASE,
)


@dataclass
class ParsedReport:
    parking: str
    scooter_count: int


@dataclass
class ParsedBreak:
    break_type: str   # 'lunch' | 'dinner' | 'break'
    is_end: bool = False


def parse_report(text: str) -> Optional[ParsedReport]:
    """Парсит отчёт скаута. Возвращает None если текст не похож на отчёт."""
    m = REPORT_RE.search(text)
    if m:
        parking = m.group(1).strip().splitlines()[0].strip()
        count = int(m.group(2))
        return ParsedReport(parking=parking, scooter_count=count)

    # Fallback: считаем eVIN если строка похожа на отчёт
    evin_count = len(EVIN_RE.findall(text))
    parking_m = re.search(r"Парковка\s+(\S+)", text, re.IGNORECASE)
    if parking_m and evin_count > 0:
        return ParsedReport(
            parking=f"Парковка {parking_m.group(1)}",
            scooter_count=evin_count,
        )

    return None


def parse_break(text: str) -> Optional[ParsedBreak]:
    """Определяет начало или конец перерыва."""
    text_lower = text.lower().strip()

    if END_BREAK_RE.search(text_lower):
        return ParsedBreak(break_type="end", is_end=True)

    m = BREAK_RE.search(text_lower)
    if not m:
        return None

    word = m.group(1).lower()
    if word in ("ужин", "dinner"):
        btype = "dinner"
    elif word in ("обед", "lunch"):
        btype = "lunch"
    else:
        btype = "break"

    return ParsedBreak(break_type=btype, is_end=False)

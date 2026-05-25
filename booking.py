import sqlite3
from datetime import datetime

DB_PATH = "bookings.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            category TEXT,
            service TEXT,
            price INTEGER,
            duration TEXT,
            date TEXT,
            time TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )""")


def add_booking(data: dict) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("""
        INSERT INTO bookings (user_id, username, full_name, phone,
            category, service, price, duration, date, time, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (
            data["user_id"], data["username"], data["full_name"], data["phone"],
            data["category"], data["service"], data["price"], data["duration"],
            data["date"], data["time"], datetime.now().isoformat()
        ))
        return cur.lastrowid


def get_booking(bid: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM bookings WHERE id=?", (bid,)).fetchone()


def set_status(bid: int, status: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE bookings SET status=? WHERE id=?", (status, bid))


def user_bookings(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM bookings WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (user_id,)
        ).fetchall()


def all_bookings():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()


def get_upcoming_bookings():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT * FROM bookings 
            WHERE status = 'confirmed' 
            ORDER BY date ASC, time ASC
        """).fetchall()


def get_confirmed_for_date(date_str: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM bookings WHERE date=? AND status='confirmed'",
            (date_str,)
        ).fetchall()


def get_busy_intervals(date_str: str):
    """
    Возвращает список объединённых интервалов занятости мастера.
    Каждый интервал: (начало_в_минутах, конец_в_минутах)
    Учитывает длительность процедуры + 10 мин буфер.
    Пересекающиеся интервалы автоматически склеиваются.
    """
    existing = get_confirmed_for_date(date_str)
    if not existing:
        return []
    
    intervals = []
    for row in existing:
        start = _time_to_minutes(row["time"])
        duration = _parse_duration(row["duration"])
        end = start + duration + 10  # +10 мин буфер между клиентами
        intervals.append((start, end))
    
    # Сортируем по времени начала
    intervals.sort(key=lambda x: x[0])
    
    # Объединяем пересекающиеся интервалы
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            # Пересекается с предыдущим — расширяем
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    
    return merged


def format_busy_intervals(intervals: list) -> str:
    """Форматирует интервалы в читаемый вид: '11:00 – 11:50'"""
    if not intervals:
        return ""
    parts = []
    for start, end in intervals:
        parts.append(f"{_minutes_to_time(start)} – {_minutes_to_time(end)}")
    return ", ".join(parts)


def _time_to_minutes(time_str: str) -> int:
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def _minutes_to_time(minutes: int) -> str:
    """Преобразует минуты от начала дня в формат 'ЧЧ:ММ'"""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def check_slot_available(date_str: str, time_str: str, new_duration_minutes: int) -> bool:
    existing = get_confirmed_for_date(date_str)
    if not existing:
        return True
    
    new_start = _time_to_minutes(time_str)
    new_end = new_start + new_duration_minutes
    
    for row in existing:
        ex_start = _time_to_minutes(row["time"])
        ex_duration = _parse_duration(row["duration"])
        ex_end = ex_start + ex_duration + 10
        
        if not (new_end <= ex_start or new_start >= ex_end):
            return False
    
    return True


def _parse_duration(duration_str: str) -> int:
    text = duration_str.lower().strip()
    total = 0
    
    if "час" in text:
        parts = text.split("час")
        num_part = parts[0].strip()
        if num_part:
            nums = [int(s) for s in num_part.split() if s.isdigit()]
            if nums:
                total += nums[-1] * 60
            else:
                total += 60
        else:
            total += 60
        text = parts[1] if len(parts) > 1 else ""
    
    if "мин" in text:
        parts = text.split("мин")
        num_part = parts[0].strip()
        nums = [int(s) for s in num_part.split() if s.isdigit()]
        if nums:
            total += nums[-1]
    
    return total if total > 0 else 30
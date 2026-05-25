import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEET_URL

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]


def _get_sheet():
    """Подключение к Google Таблице"""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json", SCOPE
        )
        gc = gspread.authorize(creds)
        return gc.open_by_url(GOOGLE_SHEET_URL).sheet1
    except Exception as e:
        print(f"⚠️ Ошибка подключения к Google Sheets: {e}")
        return None


def ensure_headers():
    """Создание заголовков в таблице при первом запуске"""
    sh = _get_sheet()
    if sh is None:
        return
    
    try:
        if not sh.row_values(1):
            sh.append_row([
                "ID", "Имя", "Username", "Телефон", "Коллекция",
                "Услуга", "Цена", "Длительность", "Дата", "Время",
                "Статус", "Создано"
            ])
    except Exception as e:
        print(f"⚠️ Не удалось создать заголовки: {e}")


def append_booking(b: dict):
    """Добавление новой записи в таблицу"""
    sh = _get_sheet()
    if sh is None:
        return
    
    try:
        sh.append_row([
            b.get("id"), b.get("full_name"), b.get("username"),
            b.get("phone"), b.get("category"), b.get("service"),
            b.get("price"), b.get("duration"), b.get("date"),
            b.get("time"), b.get("status"), b.get("created_at")
        ])
    except Exception as e:
        print(f"⚠️ Не удалось добавить запись в таблицу: {e}")


def update_status(bid: int, status: str):
    """Обновление статуса записи в таблице"""
    sh = _get_sheet()
    if sh is None:
        return
    
    try:
        col = sh.col_values(1)
        bid_str = str(bid)
        if bid_str in col:
            row = col.index(bid_str) + 1
            sh.update_cell(row, 11, status)
    except Exception as e:
        print(f"⚠️ Не удалось обновить статус в таблице: {e}")
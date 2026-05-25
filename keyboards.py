from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Выбрать услугу", callback_data="nav:")],
        [InlineKeyboardButton(text="📅 Мои записи", callback_data="menu:my_bookings")],
        [InlineKeyboardButton(text="ℹ️ О нас", callback_data="menu:about")],
    ])


def build_nav_kb(data: dict | list, current_path: str = "") -> InlineKeyboardMarkup:
    rows = []
    
    if isinstance(data, dict):
        # Если это словарь с ключами title/data, значит это категория
        if "title" in data and "data" in data:
            inner = data["data"]
            if isinstance(inner, dict):
                for key, val in inner.items():
                    new_path = f"{current_path}/{key}" if current_path else key
                    title = val.get("title", key) if isinstance(val, dict) else key
                    rows.append([InlineKeyboardButton(text=f"📂 {title}", callback_data=f"nav:{new_path}")])
            elif isinstance(inner, list):
                for idx, (name, price, dur) in enumerate(inner, start=1):
                    rows.append([InlineKeyboardButton(
                        text=f"{name} — {price:,} ₽ ({dur})".replace(",", " "),
                        callback_data=f"srv:{current_path}:{idx}"
                    )])
        else:
            # Корневой уровень
            for key, val in data.items():
                title = val.get("title", key) if isinstance(val, dict) else key
                rows.append([InlineKeyboardButton(text=f"📂 {title}", callback_data=f"nav:{key}")])
    
    # Кнопка назад
    if current_path:
        parts = current_path.split("/")
        back_path = "/".join(parts[:-1])
        rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"nav:{back_path}")])
    else:
        rows.append([InlineKeyboardButton(text="◀️ В главное меню", callback_data="menu:main")])
        
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="book:confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="menu:main"),
        ]
    ])


def approve_kb(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"app:{booking_id}:yes"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"app:{booking_id}:no"),
        ]
    ])  
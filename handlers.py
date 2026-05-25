from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from datetime import datetime
from config import WORKING_HOURS
from services import SERVICES
import booking as db
import sheets
from sms import notify_specialist
from keyboards import main_menu_kb, build_nav_kb, confirm_kb

router = Router()


class Booking(StatesGroup):
    choosing_date = State()
    choosing_time = State()
    entering_phone = State()
    confirming = State()


def get_nested_data(path: str):
    if not path:
        return SERVICES
    current = SERVICES
    for part in path.split("/"):
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            elif "data" in current and isinstance(current["data"], dict) and part in current["data"]:
                current = current["data"][part]
            else:
                return None
        else:
            return None
    return current


async def safe_edit_text(message, text: str, reply_markup=None, parse_mode=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    photo_path = "/Users/aliwkcaaa/Documents/TELO/karina.jpg"
    try:
        photo = FSInputFile(photo_path)
        await message.answer_photo(
            photo=photo,
            caption=(
                "Привет! Я Карина, твой личный бьюти-эксперт. ✨\n\n"
                "Моя задача — чтобы ты вышла от нас с настроением «Вау!».\n"
                "Напиши, о чём мечтаешь, и я всё устрою. 👇"
            ),
            reply_markup=main_menu_kb()
        )
    except Exception:
        await message.answer(
            "Привет! Я Карина, твой личный бьюти-эксперт. ✨\n\n"
            "Моя задача — чтобы ты вышла от нас с настроением «Вау!».\n"
            "Напиши, о чём мечтаешь, и я всё устрою. 👇",
            reply_markup=main_menu_kb()
        )


@router.callback_query(F.data == "menu:main")
async def to_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_text(call.message, "Главное меню:", reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:about")
async def about_us(call: CallbackQuery):
    # Удаляем предыдущее сообщение, чтобы не было дублей
    try:
        await call.message.delete()
    except Exception:
        pass
    
    photo_path = "/Users/aliwkcaaa/Documents/TELO/karina_about.JPG"
    
    text = (
        "✨ <b>Привет! Я Карина</b> — ваш личный бьюти-эксперт.\n\n"
        "Уже более 4 лет я помогаю девушкам раскрывать свою естественную красоту. "
        "Каждая процедура для меня — это не просто работа, а возможность подарить вам "
        "момент заботы о себе и уверенность в своей неотразимости.\n\n"
        "🎯 <b>Мой подход:</b>\n"
        "• Индивидуальный подбор процедур под ваш тип кожи\n"
        "• Только сертифицированное оборудование премиум-класса\n"
        "• Уютная атмосфера и полное внимание только вам\n"
        "• Честные рекомендации без навязывания лишнего\n\n"
        "📍 <b>Где принимаю:</b> г. Йошкар-ола, ул. Комсомольская, д. 122\n"
        "🕐 <b>График:</b> Пн–Пт 9:00–20:00, Сб 10:00–18:00\n"
        "📞 <b>Телефон:</b> +7 (939) 720-77-17\n\n"
        "Буду рада видеть вас и помочь стать ещё прекраснее! 💖"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🌟 Узнать больше обо мне",
            url="https://taplink.cc/karinakosmetolog"  # ← ЗАМЕНИТЕ на вашу ссылку
        )],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="menu:main")]
    ])
    
    try:
        photo = FSInputFile(photo_path)
        await call.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"⚠️ Не удалось отправить фото: {e}")
        # Если фото не найдено — отправляем просто текст
        await call.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("nav:"))
async def navigate(call: CallbackQuery):
    path = call.data.split(":", 1)[1] if ":" in call.data else ""
    data = get_nested_data(path)
    if data is None:
        await call.answer("Раздел не найден", show_alert=True)
        return
    if isinstance(data, dict) and "title" in data:
        title = data["title"]
        inner = data["data"]
    else:
        title = "Категории услуг" if not path else "Услуги"
        inner = data
    if isinstance(inner, list):
        await safe_edit_text(
            call.message,
            f"💆 <b>{title}</b>\nВыберите процедуру:",
            reply_markup=build_nav_kb({"title": title, "data": inner}, path),
            parse_mode="HTML"
        )
    else:
        await safe_edit_text(
            call.message,
            f"📂 <b>{title}</b>\nВыберите раздел:",
            reply_markup=build_nav_kb(data, path),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("srv:"))
async def pick_service(call: CallbackQuery, state: FSMContext):
    _, path, srv_idx = call.data.split(":")
    srv_idx = int(srv_idx)
    node = get_nested_data(path)
    if isinstance(node, dict) and "data" in node:
        services_list = node["data"]
        category_name = node.get("title", path.split("/")[-1])
    else:
        services_list = node
        category_name = path.split("/")[-1]
    if not services_list or srv_idx > len(services_list):
        await call.answer("Услуга не найдена", show_alert=True)
        return
    name, price, duration = services_list[srv_idx - 1]
    await state.update_data(
        category=category_name, service=name, price=price,
        duration=duration, user_id=call.from_user.id,
        username=call.from_user.username or "-",
        full_name=call.from_user.full_name,
    )
    await safe_edit_text(
        call.message,
        f"✅ Выбрано: {name}\n💰 {price} ₽ • ⏱ {duration}\n\n"
        "Введите дату в формате ДД.ММ.ГГГГ (например, 28.05.2026):"
    )
    await state.set_state(Booking.choosing_date)


@router.message(Booking.choosing_date)
async def pick_date(message: Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except ValueError:
        return await message.answer("❌ Неверный формат. Введите ДД.ММ.ГГГГ:")
    if dt.date() < datetime.now().date():
        return await message.answer("❌ Дата не может быть в прошлом.")
    if WORKING_HOURS[dt.weekday()] is None:
        return await message.answer("❌ В этот день салон не работает (воскресенье — выходной).")
    
    await state.update_data(
        date=dt.strftime("%d.%m.%Y"),
        weekday=dt.weekday()
    )
    
    start, end = WORKING_HOURS[dt.weekday()]
    data = await state.get_data()
    duration_minutes = db._parse_duration(data["duration"])
    date_str = dt.strftime("%d.%m.%Y")
    
    busy_intervals = db.get_busy_intervals(date_str)
    
    free_slots = []
    for h in range(start, end):
        time_str = f"{h:02d}:00"
        if db.check_slot_available(date_str, time_str, duration_minutes):
            free_slots.append(time_str)
    
    if not free_slots:
        await message.answer(
            f"📅 {date_str}\n\n"
            "😔 К сожалению, на эту дату нет свободных слотов для выбранной процедуры.\n"
            "Пожалуйста, выберите другую дату:"
        )
        return
    
    text = f"📅 <b>{date_str}</b>\n\n"
    text += f"✅ <b>Свободно ({len(free_slots)}):</b> " + ", ".join(free_slots)
    
    if busy_intervals:
        text += f"\n\n🚫 <b>Мастер занят:</b>\n"
        for interval_start, interval_end in busy_intervals:
            text += f"   • с {db._minutes_to_time(interval_start)} до {db._minutes_to_time(interval_end)}\n"
    
    text += "\nВведите время из свободных слотов (например, 14:00):"
    
    await message.answer(text, parse_mode="HTML")
    await state.set_state(Booking.choosing_time)


@router.message(Booking.choosing_time)
async def pick_time(message: Message, state: FSMContext):
    data = await state.get_data()
    start, end = WORKING_HOURS[data["weekday"]]
    
    time_input = message.text.strip()
    try:
        parts = time_input.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        return await message.answer("❌ Введите время в формате ЧЧ:00 или ЧЧ:ММ")
    
    if not (start <= h < end):
        return await message.answer(f"❌ Рабочее время: {start}:00 – {end}:00")
    
    time_str = f"{h:02d}:{m:02d}"
    duration_minutes = db._parse_duration(data["duration"])
    
    if not db.check_slot_available(data["date"], time_str, duration_minutes):
        return await message.answer(
            f"❌ Время {time_str} уже занято другим клиентом.\n"
            "Пожалуйста, выберите другое время. Введите новый вариант:"
        )
    
    await state.update_data(time=time_str)
    await message.answer("📱 Введите ваш номер телефона (+7...):")
    await state.set_state(Booking.entering_phone)


@router.message(Booking.entering_phone)
async def pick_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 10:
        return await message.answer("❌ Некорректный номер.")
    await state.update_data(phone=phone)
    data = await state.get_data()
    await message.answer(
        f"📝 Проверьте данные:\n\n"
        f"👤 {data['full_name']}\n📞 {data['phone']}\n"
        f"💆 {data['category']} → {data['service']}\n"
        f"💰 {data['price']} ₽ • ⏱ {data['duration']}\n"
        f"📅 {data['date']} в {data['time']}\n\n"
        "Подтвердить запись?",
        reply_markup=confirm_kb()
    )
    await state.set_state(Booking.confirming)


@router.callback_query(F.data == "book:confirm", Booking.confirming)
async def confirm_booking(call: CallbackQuery, state: FSMContext, bot):
    data = await state.get_data()
    duration_minutes = db._parse_duration(data["duration"])
    
    if not db.check_slot_available(data["date"], data["time"], duration_minutes):
        await state.clear()
        await safe_edit_text(
            call.message,
            "😔 К сожалению, пока вы оформляли запись, это время занял другой клиент.\n\n"
            "Пожалуйста, начните запись заново и выберите другой слот.",
            reply_markup=main_menu_kb()
        )
        return
    
    bid = db.add_booking(data)
    data["id"] = bid
    data["status"] = "pending"
    data["created_at"] = datetime.now().isoformat()
    sheets.append_booking(data)
    await notify_specialist(bot, data)
    await state.clear()
    await safe_edit_text(
        call.message,
        f"✅ Заявка #{bid} принята!\n\n"
        "Специалист свяжется с вами для подтверждения.\n"
        "Мы отправим уведомление, как только запись будет подтверждена."
    )


@router.callback_query(F.data == "menu:my_bookings")
async def my_bookings(call: CallbackQuery):
    rows = db.user_bookings(call.from_user.id)
    if not rows:
        return await safe_edit_text(call.message, "У вас пока нет записей.", reply_markup=main_menu_kb())
    text = "📋 Ваши записи:\n\n" + "\n".join(
        f"#{r['id']} • {r['date']} {r['time']} • {r['service']} • {r['status']}"
        for r in rows
    )
    await safe_edit_text(call.message, text, reply_markup=main_menu_kb())


@router.callback_query(F.data.startswith("app:"))
async def specialist_approve(call: CallbackQuery, bot):
    _, bid, decision = call.data.split(":")
    bid = int(bid)
    b = db.get_booking(bid)
    if not b:
        return await call.answer("Заявка не найдена")
    if decision == "yes":
        db.set_status(bid, "confirmed")
        sheets.update_status(bid, "confirmed")
        await bot.send_message(
            b["user_id"],
            f"✅ Ваша запись #{bid} подтверждена!\n"
            f"📅 {b['date']} в {b['time']}\n💆 {b['service']}\n\nЖдём вас!"
        )
        await safe_edit_text(call.message, call.message.text + "\n\n✅ ПОДТВЕРЖДЕНО")
    else:
        db.set_status(bid, "cancelled")
        sheets.update_status(bid, "cancelled")
        await bot.send_message(
            b["user_id"],
            f"❌ К сожалению, запись #{bid} отклонена.\n"
            "Свяжитесь с администратором для выбора другого времени."
        )
        await safe_edit_text(call.message, call.message.text + "\n\n❌ ОТКЛОНЕНО")


@router.message(Command("schedule"))
async def show_schedule(message: Message):
    rows = db.get_upcoming_bookings()
    if not rows:
        await message.answer("📭 На данный момент нет подтверждённых записей.")
        return
    text = "📅 <b>Предстоящие записи:</b>\n\n"
    for r in rows:
        text += (
            f"🗓 <b>{r['date']}</b> в <b>{r['time']}</b>\n"
            f"👤 {r['full_name']} ({r['phone']})\n"
            f"💆 {r['service']}\n"
            f"💰 {r['price']} ₽ • ⏱ {r['duration']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("export"))
async def export(message: Message):
    from openpyxl import Workbook
    rows = db.all_bookings()
    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Имя", "Username", "Телефон", "Коллекция",
               "Услуга", "Цена", "Длительность", "Дата", "Время", "Статус"])
    for r in rows:
        ws.append([r["id"], r["full_name"], r["username"], r["phone"],
                   r["category"], r["service"], r["price"], r["duration"],
                   r["date"], r["time"], r["status"]])
    wb.save("bookings.xlsx")
    with open("bookings.xlsx", "rb") as f:
        await message.answer_document(f)


@router.message(Command("clear_all"))
async def clear_all_bookings(message: Message):
    """Удаляет ВСЕ записи из базы данных. Только для администратора!"""
    # ⚠️ ЗАМЕНИТЕ 123456789 на ваш реальный Telegram ID
    # Узнать можно у бота @userinfobot
    ADMIN_ID = 5449835679
    
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        import sqlite3
        with sqlite3.connect(db.DB_PATH) as conn:
            conn.execute("DELETE FROM bookings")
        
        await message.answer(
            "🗑 <b>Все записи удалены!</b>\n\n"
            "База данных очищена. Новые записи будут сохраняться с ID #1.\n\n"
            "⚠️ Не забудьте вручную очистить Google Таблицу, если она подключена.",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при очистке: {e}")
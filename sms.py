import aiohttp
from aiogram import Bot
from config import SPECIALIST_PHONE, SPECIALIST_TG_ID
from keyboards import approve_kb

# ⚠️ ЗАМЕНИТЕ НА ВАШ API-КЛЮЧ ОТ SMS.RU
# Если SMS не нужны, оставьте пустую строку: SMSRU_API = ""
SMSRU_API = "EE071198-F9B4-D34A-D763-48C31BA61359"


async def send_sms(text: str):
    """Отправка SMS через sms.ru"""
    if not SMSRU_API:
        return  # Пропускаем, если ключ не указан
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                "https://sms.ru/sms/send",
                data={
                    "api_id": SMSRU_API,
                    "to": SPECIALIST_PHONE,
                    "msg": text[:700],
                    "json": 1,
                }
            )
    except Exception as e:
        print(f"⚠️ Ошибка отправки SMS: {e}")


async def notify_specialist(bot: Bot, booking: dict):
    """Уведомление специалиста о новой заявке"""
    text = (
        f"🔔 Новая заявка #{booking['id']}\n"
        f"👤 {booking['full_name']} (@{booking['username']})\n"
        f"📞 {booking['phone']}\n"
        f"💆 {booking['category']} → {booking['service']}\n"
        f"💰 {booking['price']} ₽ ({booking['duration']})\n"
        f"📅 {booking['date']} в {booking['time']}"
    )

    # Отправляем SMS (если настроено)
    await send_sms(text)

    # Дублируем в Telegram специалисту с кнопками подтверждения
    try:
        await bot.send_message(
            SPECIALIST_TG_ID,
            text,
            reply_markup=approve_kb(booking["id"])
        )
    except Exception as e:
        print(f"⚠️ Не удалось отправить уведомление специалисту в TG: {e}")
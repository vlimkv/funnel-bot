from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from ..texts import STOPPED, RESUMED, DONT_UNDERSTAND, PAUSED
from ..config import Config
from .. import db
from ..utils import RE_STOP, RE_PAUSE, RE_RESUME, RE_FREEBIE, RE_CONTACT

router = Router()

@router.message(Command("help"))
async def cmd_help(msg: Message):
    """Справка по командам"""
    help_text = (
        "📖 <b>Доступные команды:</b>\n\n"
        "🎯 <b>Основные:</b>\n"
        "/start - Начать работу с ботом\n"
        "/help - Эта справка\n\n"
        "✍️ <b>Текстовые команды:</b>\n"
        "• <code>Комплекс</code> - получить ссылку на материалы\n"
        "• <code>Контакт</code> - оставить свои данные\n"
        "• <code>Пауза</code> - приостановить рассылку\n"
        "• <code>Старт</code> - возобновить рассылку\n"
        "• <code>Стоп</code> - полностью отписаться\n\n"
        "💡 Или используй кнопки ниже в меню!"
    )
    await msg.answer(help_text)

@router.message(Command("status"))
async def cmd_status(msg: Message):
    """Показать статус пользователя"""
    try:
        stats = await db.get_user_stats(msg.from_user.id)
        if not stats:
            await msg.answer("❌ Сначала нажми /start")
            return
        
        dnd = await db.get_dnd(msg.from_user.id)
        status_text = (
            f"📊 <b>Твой статус:</b>\n\n"
            f"👤 Имя: {stats.get('first_name', 'Не указано')}\n"
            f"📧 Email: {stats.get('email', 'Не указан')}\n"
            f"🔥 Активность: {stats.get('streak_count', 0)}\n"
            f"📬 Рассылка: {'⏸ На паузе' if dnd else '✅ Активна'}\n"
            f"📅 Регистрация: {stats.get('created_at', 'N/A').strftime('%d.%m.%Y')}\n"
        )
        await msg.answer(status_text)
    except Exception as e:
        await msg.answer("❌ Ошибка получения статуса. Попробуй позже.")

@router.message(F.text.regexp(RE_STOP))
async def text_stop(msg: Message):
    """Полная отписка от бота"""
    await db.set_dnd(msg.from_user.id, True)
    await msg.answer(STOPPED)

@router.message(F.text.regexp(RE_PAUSE))
async def text_pause(msg: Message):
    """Пауза рассылки"""
    await db.set_dnd(msg.from_user.id, True)
    await msg.answer(PAUSED)

@router.message(F.text.regexp(RE_RESUME))
async def text_resume(msg: Message):
    """Возобновление рассылки"""
    await db.set_dnd(msg.from_user.id, False)
    await msg.answer(RESUMED)

@router.message(F.text.regexp(RE_FREEBIE))
async def text_freebie(msg: Message):
    """Получить комплекс"""
    if Config.FREEBIE_URL:
        await msg.answer(
            f"Вот ссылка на бесплатный комплекс:\n\n{Config.FREEBIE_URL}\n\n"
            "💡 Попробуй сделать сегодня и завтра — послушай, как реагирует тело."
        )
        await db.inc_streak(msg.from_user.id)
    else:
        await msg.answer("❌ Комплекс временно недоступен. Попробуй позже.")

@router.message(F.text.regexp(RE_CONTACT))
async def text_contact(msg: Message):
    """Запрос формы контакта"""
    await msg.answer(
        "Напиши в формате:\n\n"
        "<code>Имя: Анна; Email: anna@example.com</code>\n\n"
        "Можно указать только email или только имя.",
        parse_mode="HTML"
    )

@router.message(F.text)
async def handle_unknown_text(msg: Message):
    """Обработка неизвестных текстовых команд"""
    await msg.answer(DONT_UNDERSTAND)
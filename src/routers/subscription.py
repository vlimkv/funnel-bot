# src/routers/subscription.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from ..config import Config
from .. import db
from ..keyboards import main_kb, siren_youtube_kb, siren_presale_kb, main_menu_kb, restore_sales_kb
from ..texts import (
    SUBSCRIPTION_REQUIRED,
    SUBSCRIPTION_SUCCESS,
    SUBSCRIPTION_NOT_FOUND,
    DIASTASIS_GUIDE,
    SIREN_WELCOME,
    SIREN_PRESALE, WELCOME_PF_HTML, ALBUM_ASSETS,
    MAIN_MENU_TEXT,
    RESTORE_SALES_TEXT, RESTORE_SALES_ASSETS,
)
import asyncio
import os
import logging
from aiogram.exceptions import TelegramRetryAfter

router = Router()

CHANNEL_USERNAME = "@sezaamankeldii"

def subscription_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/sezaamankeldii")],
        [InlineKeyboardButton(text="✅ Уже подписана", callback_data="check_subscription")]
    ])

async def is_subscribed(bot, user_id: int) -> bool:
    """Проверка подписки"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception:
        return True

async def send_start_album(msg: Message):
    media = []
    missing = []
    for i, path in enumerate(ALBUM_ASSETS):
        if not os.path.exists(path):
            missing.append(path); continue
        f = FSInputFile(path)
        if i == 0:
            media.append(InputMediaPhoto(media=f, caption=WELCOME_PF_HTML, parse_mode="HTML"))
        else:
            media.append(InputMediaPhoto(media=f))

    if missing:
        logging.warning("Missing album files: %s", missing)

    if not media:
        await msg.answer("⚠️ Альбом временно недоступен."); return

    try:
        await msg.bot.send_media_group(chat_id=msg.chat.id, media=media)
    except Exception as e:
        logging.exception("Failed to send start album: %s", e)
        await msg.answer("⚠️ Не удалось отправить альбом, попробуйте позже.")

async def send_restore_sales_album(msg: Message):
    media = []
    missing = []

    for i, path in enumerate(RESTORE_SALES_ASSETS):
        if not os.path.exists(path):
            missing.append(path)
            continue

        f = FSInputFile(path)
        if i == 0:
            media.append(InputMediaPhoto(media=f, caption=RESTORE_SALES_TEXT, parse_mode="HTML"))
        else:
            media.append(InputMediaPhoto(media=f))

    if missing:
        logging.warning("Missing RE:STORE album files: %s", missing)

    if not media:
        await msg.answer("⚠️ Материал временно недоступен. Попробуйте позже.")
        return

    try:
        await msg.bot.send_media_group(chat_id=msg.chat.id, media=media)
    except TelegramRetryAfter as e:
        logging.warning("RetryAfter %s sec on send_media_group", e.retry_after)
        await asyncio.sleep(e.retry_after + 1)
        await msg.bot.send_media_group(chat_id=msg.chat.id, media=media)
    except Exception as e:
        logging.exception("send_restore_sales_album failed: %r", e)
        # fallback: хотя бы текст + кнопки
        await msg.answer(RESTORE_SALES_TEXT, reply_markup=restore_sales_kb(), parse_mode="HTML")

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    
    ref_tag = None
    if msg.text and " " in msg.text:
        ref_tag = msg.text.split(" ", 1)[1]
        
    await db.upsert_user(
        msg.from_user.id, 
        msg.from_user.username, 
        msg.from_user.first_name, 
        msg.from_user.last_name, 
        ref_tag
    )
    
    # Проверка подписки
    if await is_subscribed(msg.bot, msg.from_user.id):
        # ВЫЗЫВАЕМ НОВУЮ ФУНКЦИЮ ЦЕПОЧКИ
        await send_welcome_chain(msg.bot, msg.chat.id)
    else:
        await msg.answer(SUBSCRIPTION_REQUIRED, reply_markup=subscription_kb())


@router.callback_query(F.data == "check_subscription")
async def check_subscription(cb: CallbackQuery):
    if await is_subscribed(cb.bot, cb.from_user.id):
        await cb.answer("✅ Подписка подтверждена!", show_alert=False)
        try:
            await cb.message.delete()
        except:
            pass
            
        # ВЫЗЫВАЕМ НОВУЮ ФУНКЦИЮ ЦЕПОЧКИ
        await send_welcome_chain(cb.bot, cb.message.chat.id)
    else:
        await cb.answer("❌ Вы еще не подписались на канал!", show_alert=True)

async def send_siren_flow(msg: Message):
    """
    1) Сразу отправляет SIREN_WELCOME + кнопка на YouTube.
    2) Через 60 секунд — SIREN_PRESALE + кнопка на форму.
    """
    # Шаг 1 — сразу
    await msg.answer(SIREN_WELCOME, reply_markup=siren_youtube_kb())

    # Шаг 2 — через минуту, без блокировки основного хендлера
    async def _delayed_presale():
        try:
            await asyncio.sleep(60)
            await msg.answer(SIREN_PRESALE, reply_markup=siren_presale_kb())
        except Exception:
            pass

    asyncio.create_task(_delayed_presale())

# --- Ниже оставляем старую логику "скачать PDF", если где-то используется ---

@router.callback_query(F.data == "download_diastasis_pdf")
async def download_pdf(cb: CallbackQuery):
    """Отправка PDF-файла с гайдом (backward compatibility)"""
    await cb.answer()

    pdf_url = Config.FREEBIE_URL

    if not pdf_url:
        await cb.message.answer(
            "⚠️ PDF временно недоступен. Попробуйте позже или обратитесь к администратору.",
            reply_markup=main_kb()
        )
        return

    if pdf_url.startswith("FILE:"):
        file_id = pdf_url[5:]
        try:
            await cb.message.answer_document(
                file_id,
                caption="📄 Вот твой гайд по диастазу! Изучай и применяй бережно 🤍",
                reply_markup=main_kb()
            )
        except Exception:
            await cb.message.answer(
                "❌ Ошибка при отправке файла. Попробуйте позже.",
                reply_markup=main_kb()
            )
    else:
        await cb.message.answer(
            f"📥 <b>Скачать гайд:</b>\n\n{pdf_url}\n\n"
            "💡 Изучай материал и применяй техники бережно!",
            reply_markup=main_kb()
        )

# --- ОСНОВНАЯ ФУНКЦИЯ ОТПРАВКИ ЦЕПОЧКИ (НОВАЯ) ---
async def send_welcome_chain(bot, chat_id: int):
    """Отправляет ВСЮ цепочку сообщений по очереди"""
    chain = await db.get_welcome_chain()
    
    if not chain:
        # Если цепочка пустая, отправляем дефолт
        await bot.send_message(chat_id, "Привет! (Контент настраивается)")
        return

    for msg in chain:
        # 1. Собираем клавиатуру для конкретного сообщения
        kb = None
        if msg.get('buttons'):
            rows = []
            for btn in msg['buttons']:
                rows.append([InlineKeyboardButton(text=btn['text'], url=btn['url'])])
            kb = InlineKeyboardMarkup(inline_keyboard=rows)
        
        # 2. Отправляем в зависимости от типа
        try:
            m_type = msg.get('type', 'text')
            content = msg.get('content')
            caption = msg.get('caption')

            if m_type == 'text':
                await bot.send_message(chat_id, text=content, reply_markup=kb)
                
            elif m_type == 'photo':
                await bot.send_photo(chat_id, photo=content, caption=caption, reply_markup=kb)
                
            elif m_type == 'video':
                await bot.send_video(chat_id, video=content, caption=caption, reply_markup=kb)
                
            elif m_type == 'video_note': # Кружочек
                await bot.send_video_note(chat_id, video_note=content, reply_markup=kb)
                
            elif m_type == 'document': # Файл (PDF и тд)
                await bot.send_document(chat_id, document=content, caption=caption, reply_markup=kb)
            
            # Небольшая пауза, чтобы сообщения не перепутались местами
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"Ошибка отправки части цепочки: {e}")
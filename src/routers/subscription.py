# src/routers/subscription.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from ..config import Config
from .. import db
from ..keyboards import main_kb, siren_youtube_kb, siren_presale_kb, main_menu_kb, welcome_video_kb
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

router = Router()

CHANNEL_USERNAME = "@sezaamankeldii"

def subscription_kb() -> InlineKeyboardMarkup:
    """Клавиатура для проверки подписки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/sezaamankeldii")],
        [InlineKeyboardButton(text="✅ Уже подписана", callback_data="check_subscription")]
    ])

async def is_subscribed(bot, user_id: int) -> bool:
    """Проверка подписки пользователя на канал"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        # В проде безопаснее не резать флоу из-за ошибки проверки
        print(f"⚠️  Ошибка проверки подписки: {e}")
        print(f"⚠️  Убедитесь, что бот добавлен в канал {CHANNEL_USERNAME} как администратор!")
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

    await msg.bot.send_media_group(chat_id=msg.chat.id, media=media)

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    """Команда /start с проверкой подписки"""
    await state.clear()

    uid = msg.from_user.id
    username = msg.from_user.username
    first = msg.from_user.first_name
    last = msg.from_user.last_name

    # Извлечение реферального тега
    ref_tag = None
    if msg.text and " " in msg.text:
        ref_tag = msg.text.split(" ", 1)[1]

    # Сохранение пользователя в БД
    await db.upsert_user(uid, username, first, last, ref_tag)

    # Сохранение реферала
    if ref_tag:
        await db.save_referral(uid, ref_tag)

    # Проверка подписки
    if await is_subscribed(msg.bot, uid):
        await send_restore_sales_album(msg)
        await msg.answer("🏠 Главное меню", reply_markup=siren_presale_kb())
    else:
        await msg.answer(SUBSCRIPTION_REQUIRED, reply_markup=subscription_kb())


@router.callback_query(F.data == "check_subscription")
async def check_subscription(cb: CallbackQuery):
    uid = cb.from_user.id

    if await is_subscribed(cb.bot, uid):
        await cb.answer("✅ Отлично! Теперь ты с нами 🤍", show_alert=False)

        await send_restore_sales_album(cb.message)

        await cb.message.answer("🏠 Главное меню", reply_markup=siren_presale_kb())

        try:
            await cb.message.edit_text("✅ Подписка подтверждена 🤍", reply_markup=subscription_kb())
        except Exception:
            pass
    else:
        await cb.answer("😔 Ты ещё не подписана. Подпишись и нажми снова!", show_alert=True)
        await cb.message.edit_text(SUBSCRIPTION_NOT_FOUND, reply_markup=subscription_kb())

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
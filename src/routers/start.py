from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from datetime import datetime, timedelta, timezone
from ..keyboards import main_kb, contact_kb, main_menu_kb
from ..texts import WELCOME, FREEBIE_SENT, CONTACT_ASK, CONTACT_THX, PAUSED, MAIN_MENU_TEXT
from ..config import Config
from .. import db
from ..utils import RE_EMAIL, RE_NAME

router = Router()

@router.message(CommandStart(deep_link=True))
async def start_with_ref(message: Message, command: CommandStart):
    """Обработка /start с реферальной ссылкой"""
    ref = command.args
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
        ref if ref and ref.startswith("ref_") else None
    )
    if ref and ref.startswith("ref_"):
        await db.save_referral(message.from_user.id, ref)

    # 🔽 тут меняем WELCOME на новое главное меню
    await message.answer(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_kb()
    )
    await plan_warmup(message.from_user.id)

@router.message(CommandStart())
async def start_plain(message: Message):
    """Обработка обычного /start"""
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
        None
    )
    # Проверяем, не возвращается ли пользователь
    dnd = await db.get_dnd(message.from_user.id)
    if dnd:
        # Пользователь был на паузе - снимаем её
        await db.set_dnd(message.from_user.id, False)
        await message.answer(
            "С возвращением! 🤍\n"
            "Продолжим наше путешествие к здоровому телу.",
            reply_markup=main_menu_kb()   # ⬅ было main_kb()
        )
    else:
        # Новый пользователь или без паузы — показываем новое главное меню
        await message.answer(
            MAIN_MENU_TEXT,
            reply_markup=main_menu_kb()
        )
        await plan_warmup(message.from_user.id)

async def plan_warmup(user_id: int):
    """Планирует прогревочные сообщения"""
    from ..scheduler import warmup_offsets
    offset1, offset2 = warmup_offsets()
    now = datetime.now(timezone.utc)
    
    # Проверяем, не запланированы ли уже сообщения
    # (чтобы при повторном /start не дублировать)
    try:
        await db.enqueue_warmup(user_id, now + timedelta(minutes=offset1), step=1)
        await db.enqueue_warmup(user_id, now + timedelta(minutes=offset2), step=2)
    except Exception as e:
        # Игнорируем ошибки дублирования, если есть unique constraint
        pass

@router.callback_query(F.data == "get_freebie")
async def on_get_freebie(cb: CallbackQuery):
    """Выдача бесплатного комплекса"""
    await cb.message.answer(FREEBIE_SENT + f"\n\n{Config.FREEBIE_URL}")
    await db.inc_streak(cb.from_user.id)
    await cb.answer()

@router.callback_query(F.data == "leave_contact")
async def on_leave_contact(cb: CallbackQuery):
    """Запрос контактных данных"""
    await cb.message.answer(
        CONTACT_ASK + "\n\nПришли сообщение в формате:\n`Имя: ...; Email: ...`",
        parse_mode="Markdown",
        reply_markup=contact_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "skip_contact")
async def on_skip(cb: CallbackQuery):
    """Пропуск контактных данных"""
    await cb.message.answer("Ок, без контакта. В любом случае я на связи 🤍")
    await cb.answer()

@router.callback_query(F.data == "pause_warmup")
async def on_pause(cb: CallbackQuery):
    """Пауза прогрева"""
    await db.set_dnd(cb.from_user.id, True)
    await cb.message.answer(PAUSED)
    await cb.answer()

@router.message(F.text)
async def parse_contact(msg: Message):
    """Парсинг контактных данных из текста"""
    text = msg.text.strip()

    # Ищем email и имя
    email = None
    m = RE_EMAIL.search(text)
    if m:
        email = m.group(0)
    
    name = None
    m2 = RE_NAME.search(text)
    if m2:
        name = m2.group(1).strip()

    if email or name:
        await db.save_email(msg.from_user.id, email, name)
        await msg.answer(CONTACT_THX)
        return
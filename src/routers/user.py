# src/routers/user.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from ..config import Config
from .. import db
from ..keyboards import (
    main_kb,
    contact_kb,
    main_menu_kb,
    free_trainings_kb,
    articles_guides_kb,
    program_pelvic_floor_kb,
)
from ..texts import (
    FREEBIE_SENT, CONTACT_ASK, CONTACT_THX, DONT_UNDERSTAND,
    MAIN_MENU_TEXT, FREE_TRAININGS_TEXT, ARTICLES_GUIDES_TEXT,
    PROGRAM_PELVIC_FLOOR_TEXT, PROGRAM_FOR_WHOM_TEXT, PROGRAM_WHAT_YOU_GET_TEXT,
)
from ..utils import RE_FREEBIE, RE_CONTACT, RE_EMAIL, extract_phone, extract_name

router = Router()

class ContactState(StatesGroup):
    waiting_for_contact = State()

@router.callback_query(F.data == "get_freebie")
async def get_freebie(cb: CallbackQuery):
    """Отправка бесплатного комплекса (PDF или ссылка)"""
    await cb.answer()
    
    freebie_url = Config.FREEBIE_URL
    
    if not freebie_url:
        await cb.message.answer(
            "⚠️ Материал временно недоступен. Попробуйте позже.",
            reply_markup=main_kb()
        )
        return
    
    if freebie_url.startswith("FILE:"):
        file_id = freebie_url[5:]
        try:
            await cb.message.answer_document(
                file_id,
                caption=FREEBIE_SENT,
                reply_markup=main_kb()
            )
        except Exception as e:
            await cb.message.answer(
                "❌ Ошибка при отправке файла. Обратитесь к администратору.",
                reply_markup=main_kb()
            )
    else:
        await cb.message.answer(
            f"{FREEBIE_SENT}\n\n🔗 {freebie_url}",
            reply_markup=main_kb()
        )

@router.callback_query(F.data == "leave_contact")
async def leave_contact(cb: CallbackQuery, state: FSMContext):
    """Запрос контактных данных"""
    await cb.answer()
    await state.set_state(ContactState.waiting_for_contact)
    await cb.message.answer(CONTACT_ASK, reply_markup=contact_kb())

@router.callback_query(F.data == "skip_contact")
async def skip_contact(cb: CallbackQuery, state: FSMContext):
    """Пропуск ввода контактов"""
    await cb.answer()
    await state.clear()
    await cb.message.answer(
        "Хорошо, продолжим без контакта 🌿\n"
        "Если передумаешь — напиши «Контакт»",
        reply_markup=main_kb()
    )

@router.message(ContactState.waiting_for_contact)
async def process_contact(msg: Message, state: FSMContext):
    """Обработка контактных данных (имя, email или телефон)"""
    text = msg.text or ""
    
    print(f"📝 Получен текст: {text}")
    
    # Извлечение данных
    email = None
    phone = None
    name = None
    
    # Поиск email
    email_match = RE_EMAIL.search(text)
    if email_match:
        email = email_match.group(0)
        print(f"✅ Найден email: {email}")
    
    # Поиск телефона
    phone = extract_phone(text)
    if phone:
        print(f"✅ Найден телефон: {phone}")
    
    # Поиск имени
    name = extract_name(text)
    if name:
        print(f"✅ Найдено имя: {name}")
    
    # Проверка: должно быть хотя бы имя и (email или телефон)
    if (email or phone) and name:
        # Сохраняем в БД
        print(f"💾 Сохраняем: name={name}, email={email}, phone={phone}")
        await db.save_contact(msg.from_user.id, email=email, phone=phone, first_name=name)
        await msg.answer(CONTACT_THX, reply_markup=main_kb())
        await state.clear()
        print("✅ Контакт сохранён успешно")
    elif email or phone:
        # Есть контакт, но нет имени - берем имя из профиля
        user_name = name or msg.from_user.first_name or "Пользователь"
        print(f"💾 Сохраняем (без имени): name={user_name}, email={email}, phone={phone}")
        await db.save_contact(msg.from_user.id, email=email, phone=phone, first_name=user_name)
        await msg.answer(CONTACT_THX, reply_markup=main_kb())
        await state.clear()
        print("✅ Контакт сохранён (использовано имя из профиля)")
    elif name:
        # Есть только имя - просим добавить контакт
        await msg.answer(
            f"Спасибо, <b>{name}</b>! 🤍\n\n"
            "Теперь добавь, пожалуйста, <b>email</b> или <b>телефон</b>, "
            "чтобы я могла связаться с тобой по поводу курса.\n\n"
            "Например:\n"
            f"<code>{name} +77001234567</code>\n"
            f"или\n"
            f"<code>{name} anna@mail.com</code>",
            reply_markup=contact_kb()
        )
        print("⚠️ Только имя, запрошен контакт")
    else:
        # Ничего не распознано
        await msg.answer(
            "🤔 Не могу распознать контакт. Попробуй так:\n\n"
            "<b>Примеры:</b>\n"
            "• <code>Анна +77001234567</code>\n"
            "• <code>Имя: Анна; Телефон: 87001234567</code>\n"
            "• <code>Анна anna@mail.com</code>\n"
            "• <code>Имя: Анна; Email: anna@mail.com</code>",
            reply_markup=contact_kb()
        )
        print("❌ Не удалось распознать данные")

@router.message(F.text)
async def handle_text(msg: Message, state: FSMContext):
    """Обработка текстовых команд"""
    text = msg.text or ""
    
    # Команда КОМПЛЕКС - повторная отправка материала
    if RE_FREEBIE.match(text):
        freebie_url = Config.FREEBIE_URL
        
        if not freebie_url:
            await msg.answer(
                "⚠️ Материал временно недоступен.",
                reply_markup=main_kb()
            )
            return
        
        if freebie_url.startswith("FILE:"):
            file_id = freebie_url[5:]
            try:
                await msg.answer_document(
                    file_id,
                    caption=FREEBIE_SENT,
                    reply_markup=main_kb()
                )
            except:
                await msg.answer(
                    "❌ Ошибка при отправке файла.",
                    reply_markup=main_kb()
                )
        else:
            await msg.answer(
                f"{FREEBIE_SENT}\n\n🔗 {freebie_url}",
                reply_markup=main_kb()
            )
        return
    
    if RE_CONTACT.match(text):
        await state.set_state(ContactState.waiting_for_contact)
        await msg.answer(CONTACT_ASK, reply_markup=contact_kb())
        return

    await msg.answer(DONT_UNDERSTAND, reply_markup=main_kb())

# --- Показ главного меню ---

@router.message(Command("menu"))
async def show_main_menu_cmd(msg: Message):
    """
    /menu — показать главное меню бота Seza Amankeldi.
    Можно будет вызывать и из /start, если нужно.
    """
    await msg.answer(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_kb()
    )


@router.callback_query(F.data == "menu_main")
async def show_main_menu_cb(cb: CallbackQuery):
    """
    Возврат в главное меню по кнопке «Вернуться в главное меню».
    """
    await cb.message.edit_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_kb()
    )
    await cb.answer()


# --- Раздел: Бесплатные тренировки ---

@router.callback_query(F.data == "menu_free_trainings")
async def open_free_trainings(cb: CallbackQuery):
    """
    Открыть раздел с бесплатными тренировками (YouTube-ссылки).
    """
    await cb.message.edit_text(
        FREE_TRAININGS_TEXT,
        reply_markup=free_trainings_kb()
    )
    await cb.answer()


# --- Раздел: Полезные статьи и гайды ---

@router.callback_query(F.data == "menu_articles_guides")
async def open_articles_guides(cb: CallbackQuery):
    """
    Открыть раздел «Полезные статьи и гайды».
    """
    await cb.message.edit_text(
        ARTICLES_GUIDES_TEXT,
        reply_markup=articles_guides_kb()
    )
    await cb.answer()


@router.callback_query(F.data == "article_diastasis")
async def send_article_diastasis(cb: CallbackQuery):
    doc = FSInputFile("files/diastasis_guide.pdf")  # путь под себя
    await cb.message.answer_document(
        document=doc,
        caption="Что такое диастаз и как проверить дома"
    )
    await cb.answer()


@router.callback_query(F.data == "article_flat_belly")
async def send_article_flat_belly(cb: CallbackQuery):
    doc = FSInputFile("files/flat_belly_secrets.pdf")
    await cb.message.answer_document(
        document=doc,
        caption="Секреты плоского живота: научный разбор причин"
    )
    await cb.answer()

@router.callback_query(F.data == "article_microbiome")
async def send_article_microbiome(cb: CallbackQuery):
    doc = FSInputFile("files/microbiome.pdf")
    await cb.message.answer_document(
        document=doc,
        caption="Микробиом кишечника: что влияет на живот глубже, чем кажется"
    )
    await cb.answer()

# --- Раздел: О программе «Тазовое Дно» ---

@router.callback_query(F.data == "menu_program_pelvic")
async def open_program_pelvic(cb: CallbackQuery):
    """
    Раздел с описанием программы «Тазовое Дно».
    """
    await cb.message.edit_text(
        PROGRAM_PELVIC_FLOOR_TEXT,
        reply_markup=program_pelvic_floor_kb()
    )
    await cb.answer()


@router.callback_query(F.data == "program_for_whom")
async def program_for_whom(cb: CallbackQuery):
    await cb.message.edit_text(
        PROGRAM_FOR_WHOM_TEXT,
        reply_markup=program_pelvic_floor_kb()
    )
    await cb.answer()



@router.callback_query(F.data == "program_what_you_get")
async def program_what_you_get(cb: CallbackQuery):
    doc = FSInputFile("files/pelvic_floor_program.pdf")
    await cb.message.answer_document(
        document=doc,
        caption="Подробная программа курса «Тазовое Дно»"
    )
    await cb.answer()

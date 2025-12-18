# src/routers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from ..config import Config
from .. import db
from datetime import datetime
import csv
import tempfile
import os
import asyncio

# тексты и клавиатуры для сценариев
from ..texts import SIREN_WELCOME, SIREN_PRESALE
from ..texts import WELCOME_PF_HTML, ALBUM_ASSETS
from ..keyboards import siren_youtube_kb, siren_presale_kb

PELVIC_RESULTS_ASSETS = [
    "files/pelvic_result_1.jpg",
    "files/pelvic_result_2.jpg",
    "files/pelvic_result_3.jpg",
    "files/pelvic_result_4.jpg",
    "files/pelvic_result_5.jpg",
    "files/pelvic_result_6.jpg",
]

MENSTRUATION_ASSETS = [
    "files/menstruation_1.jpg",
    "files/menstruation_2.jpg",
    "files/menstruation_3.jpg",
    "files/menstruation_4.jpg",
    "files/menstruation_5.jpg",
    "files/menstruation_6.jpg",
    "files/menstruation_7.jpg",
]

router = Router()

# ID администраторов
ADMIN_IDS = [7042937865]

class AdminStates(StatesGroup):
    waiting_for_freebie_url = State()
    waiting_for_next_material_url = State()
    waiting_for_course_url = State()
    waiting_for_instagram_url = State()
    waiting_for_broadcast_message = State()
    waiting_for_broadcast_album = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Полная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📈 Воронка", callback_data="admin_funnel")],
        [InlineKeyboardButton(text="🔗 Управление ссылками", callback_data="admin_links")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📥 Скачать пользователей (CSV)", callback_data="admin_download_users_csv")],  # ✅
        [InlineKeyboardButton(text="📧 Контакты (CSV)", callback_data="admin_contacts")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
    ])

def admin_links_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Бесплатный комплекс", callback_data="admin_set_freebie")],
        [InlineKeyboardButton(text="📚 Следующий материал", callback_data="admin_set_next")],
        [InlineKeyboardButton(text="🎓 Курс", callback_data="admin_set_course")],
        [InlineKeyboardButton(text="📱 Instagram", callback_data="admin_set_instagram")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")],
    ])

def users_pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_users_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data=f"admin_users_page_{page+1}"))
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="admin_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def contacts_pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    buttons.append([InlineKeyboardButton(text="📥 Скачать CSV", callback_data="admin_download_csv")])
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_contacts_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data=f"admin_contacts_page_{page+1}"))
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="admin_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_broadcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 SIREN: двухшаговый флоу", callback_data="admin_broadcast_siren_flow")],
        [InlineKeyboardButton(text="🧘‍♀️ Дыхательный комплекс МФД", callback_data="admin_broadcast_mfd_breathing")],
        [InlineKeyboardButton(text="🩸 МФД: боль во время менструации", callback_data="admin_broadcast_menstruation")],
        [InlineKeyboardButton(text="🪷 ПД: трёхшаговая рассылка", callback_data="admin_broadcast_pelvic_flow")],
        [InlineKeyboardButton(text="▶️ Утренняя зарядка (YouTube)", callback_data="admin_broadcast_morning_warmup")],
        [InlineKeyboardButton(text="🍑 Стул и тяжесть (памятка)", callback_data="admin_broadcast_stool_tips")],  # ← НОВОЕ
        [InlineKeyboardButton(text="📝 Только предзапись", callback_data="admin_broadcast_presale")],
        [InlineKeyboardButton(text="📸 Стартовый альбом (assets)", callback_data="admin_broadcast_start_album")],
        [InlineKeyboardButton(text="✍️ Своя рассылка", callback_data="admin_broadcast_custom")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")],
    ])

@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ У вас нет доступа к админ-панели.")
        return
    await msg.answer("🔐 <b>Админ-панель</b>\n\nВыберите действие:", reply_markup=admin_main_kb())

@router.callback_query(F.data == "admin_main")
async def admin_main(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return
    await state.clear()
    await cb.message.edit_text("🔐 <b>Админ-панель</b>\n\nВыберите действие:", reply_markup=admin_main_kb())
    await cb.answer()

@router.callback_query(F.data == "noop")
async def noop_handler(cb: CallbackQuery):
    await cb.answer()

@router.callback_query(F.data == "admin_stats")
async def admin_stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    stats = await db.get_bot_stats()
    total = stats['total_users']
    with_email_pct = (stats['users_with_email'] / total * 100) if total > 0 else 0
    with_phone_pct = (stats['users_with_phone'] / total * 100) if total > 0 else 0

    text = (
        "📊 <b>Полная статистика бота</b>\n\n"
        "👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
        f"├ Всего: <b>{total}</b>\n"
        f"├ Новых за 24ч: <b>{stats['new_today']}</b>\n"
        f"├ Новых за неделю: <b>{stats['new_week']}</b>\n"
        f"└ Новых за месяц: <b>{stats['new_month']}</b>\n\n"
        "📧 <b>КОНТАКТЫ</b>\n"
        f"├ С email: <b>{stats['users_with_email']}</b> ({with_email_pct:.1f}%)\n"
        f"├ С телефоном: <b>{stats['users_with_phone']}</b> ({with_phone_pct:.1f}%)\n"
        f"├ С именем: <b>{stats['users_with_name']}</b>\n"
        f"└ Полные данные: <b>{stats['users_with_full_data']}</b>\n\n"
        "🔗 <b>РЕФЕРАЛЫ</b>\n"
        f"└ Всего переходов: <b>{stats['referrals']}</b>\n\n"
        f"🕐 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]
    ])
    await cb.message.edit_text(text, reply_markup=back_kb)
    await cb.answer()

@router.callback_query(F.data == "admin_funnel")
async def admin_funnel(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    stats = await db.get_funnel_stats()
    total = stats['total_users']

    def calc_conversion(value, base):
        return (value / base * 100) if base else 0

    started_pct = 100
    left_contact_pct = calc_conversion(stats['left_contact'], total)

    def bar(percent):
        filled = int(percent / 10)
        return '█' * filled + '░' * (10 - filled)

    text = (
        "📈 <b>ВОРОНКА КОНВЕРСИИ</b>\n\n"
        f"1️⃣ Нажали /start\n   {bar(started_pct)} {total} ({started_pct:.0f}%)\n\n"
        f"2️⃣ Оставили контакт\n   {bar(left_contact_pct)} {stats['left_contact']} ({left_contact_pct:.1f}%)\n\n"
        "📊 <b>СРЕДНИЕ ПОКАЗАТЕЛИ</b>\n"
        f"└ Среднее время до email: <b>{stats['avg_time_to_email']}ч</b>\n\n"
        f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_funnel")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]
    ])
    await cb.message.edit_text(text, reply_markup=back_kb)
    await cb.answer()

@router.callback_query(F.data == "admin_links")
async def admin_links(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    def shorten(url, max_len=50):
        if not url: return "Не установлено"
        return url if len(url) <= max_len else url[:max_len-3] + "..."

    text = (
        "🔗 <b>Текущие ссылки:</b>\n\n"
        f"🎁 <b>Бесплатный комплекс:</b>\n<code>{shorten(Config.FREEBIE_URL)}</code>\n\n"
        f"📚 <b>Следующий материал:</b>\n<code>{shorten(Config.NEXT_MATERIAL_URL)}</code>\n\n"
        f"🎓 <b>Курс:</b>\n<code>{shorten(Config.COURSE_URL)}</code>\n\n"
        f"📱 <b>Instagram:</b>\n<code>{shorten(Config.INSTAGRAM_URL)}</code>\n\n"
        "Выберите ссылку для изменения:"
    )
    await cb.message.edit_text(text, reply_markup=admin_links_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("admin_users"))
async def admin_users(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    page = 0
    if cb.data.startswith("admin_users_page_"):
        try:
            page = int(cb.data.split("_")[-1])
        except:
            page = 0

    per_page = 20
    offset = page * per_page
    users = await db.get_recent_users(limit=per_page, offset=offset)
    total_users = await db.get_total_users_count()
    total_pages = (total_users + per_page - 1) // per_page

    if not users:
        text = "👥 <b>Пользователей пока нет</b>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]])
    else:
        text = f"👥 <b>Пользователи (страница {page+1}/{total_pages})</b>\n\n"
        for i, user in enumerate(users, offset + 1):
            name = user['first_name'] or "Без имени"
            username = f"@{user['username']}" if user.get('username') else ""
            email = f"\n   📧 {user['email']}" if user.get('email') else ""
            phone = f"\n   📱 {user['phone']}" if user.get('phone') else ""
            created = user.get('created_at', '')
            created_str = created.strftime('%d.%m.%y') if created else ''
            text += f"{i}. <b>{name}</b> {username}\n"
            if email: text += email
            if phone: text += phone
            if created_str: text += f"\n   📅 {created_str}"
            text += "\n\n"
        kb = users_pagination_kb(page, total_pages)

    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("admin_contacts"))
async def admin_contacts(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    page = 0
    if cb.data.startswith("admin_contacts_page_"):
        try:
            page = int(cb.data.split("_")[-1])
        except:
            page = 0

    per_page = 20
    offset = page * per_page
    contacts = await db.get_users_with_contacts(limit=per_page, offset=offset)
    total_contacts = await db.get_contacts_count()
    total_pages = max(1, (total_contacts + per_page - 1) // per_page)

    if not contacts:
        text = "📧 <b>Контакты пока не оставлены</b>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]])
    else:
        text = f"📧 <b>Контакты (страница {page+1}/{total_pages})</b>\nВсего контактов: <b>{total_contacts}</b>\n\n"
        for i, user in enumerate(contacts, offset + 1):
            name = user.get('first_name') or "Без имени"
            email = user.get('email')
            phone = user.get('phone')
            username = f"@{user['username']}" if user.get('username') else ""
            created = user.get('created_at', '')
            created_str = created.strftime('%d.%m.%y') if created else ''
            text += f"{i}. <b>{name}</b>\n"
            if email: text += f"   📧 {email}\n"
            if phone: text += f"   📱 {phone}\n"
            if username: text += f"   👤 {username}\n"
            if created_str: text += f"   📅 {created_str}\n"
            text += "\n"
        kb = contacts_pagination_kb(page, total_pages)

    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "admin_download_csv")
async def admin_download_csv(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    await cb.answer("📥 Генерирую CSV...", show_alert=False)
    contacts = await db.get_all_users_with_contacts()

    if not contacts:
        await cb.message.answer("📧 Контактов пока нет")
        return

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8-sig', newline='') as tmp:
        writer = csv.writer(tmp, delimiter=';')
        writer.writerow(['№', 'Имя', 'Email', 'Телефон', 'Username', 'User ID', 'Дата регистрации'])
        for i, user in enumerate(contacts, 1):
            writer.writerow([
                i,
                user.get('first_name') or '',
                user.get('email') or '',
                user.get('phone') or '',
                user.get('username') or '',
                user.get('user_id') or '',
                user.get('created_at', '').strftime('%d.%m.%Y %H:%M') if user.get('created_at') else ''
            ])
        tmp_path = tmp.name

    try:
        doc = FSInputFile(tmp_path, filename=f"contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        await cb.message.answer_document(
            doc,
            caption=f"📊 <b>Экспорт контактов</b>\n\nВсего записей: {len(contacts)}\nДата выгрузки: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    await cb.answer()

@router.callback_query(F.data == "admin_set_freebie")
async def admin_set_freebie(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    await state.set_state(AdminStates.waiting_for_freebie_url)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_links")]])
    await cb.message.edit_text(
        "🎁 <b>Установка ссылки на бесплатный комплекс</b>\n\nОтправьте новую ссылку или PDF-файл:",
        reply_markup=cancel_kb
    )
    await cb.answer()

@router.message(AdminStates.waiting_for_freebie_url)
async def process_freebie_url(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return

    url = msg.text.strip() if msg.text else None
    if msg.document:
        url = f"FILE:{msg.document.file_id}"

    if url:
        await db.set_config("FREEBIE_URL", url)
        Config.FREEBIE_URL = url
        await msg.answer(
            f"✅ Ссылка на бесплатный комплекс обновлена!\n\nНовое значение: <code>{url[:100]}</code>",
            reply_markup=admin_links_kb()
        )
    else:
        await msg.answer("❌ Пожалуйста, отправьте ссылку или файл.")
        return

    await state.clear()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    await state.clear()
    await cb.message.edit_text("📢 <b>Расссылка</b>\n\nВыберите вариант:", reply_markup=admin_broadcast_kb())
    await cb.answer()

@router.callback_query(F.data == "admin_broadcast_custom")
async def admin_broadcast_custom(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    await state.set_state(AdminStates.waiting_for_broadcast_album)
    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_main")]]
    )
    await cb.message.edit_text(
        "📢 <b>Кастомная рассылка</b>\n\n"
        "Пришлите <b>альбом из 5 фото</b> (одной отправкой). "
        "Подпись укажите в ПЕРВОМ фото.\n"
        "Когда всё загрузится — напишите «готово».",
        reply_markup=cancel_kb
    )
    await cb.answer()

@router.callback_query(F.data == "admin_broadcast_start_album")
async def admin_broadcast_start_album(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    users = await db.get_all_users()
    total = len(users)
    await cb.message.answer(f"📸 Отправляю стартовый альбом… Всего пользователей: {total}")

    # Собираем media_group из локальных файлов (создаём FSInputFile заново каждый раз)
    def build_media():
        media = []
        for i, path in enumerate(ALBUM_ASSETS):
            f = FSInputFile(path)
            if i == 0:
                media.append(InputMediaPhoto(media=f, caption=WELCOME_PF_HTML, parse_mode="HTML"))
            else:
                media.append(InputMediaPhoto(media=f))
        return media

    sent = failed = 0
    for u in users:
        try:
            await cb.message.bot.send_media_group(chat_id=u["user_id"], media=build_media())
            sent += 1
            await asyncio.sleep(0.05)  # мягкий rate-limit
        except Exception:
            failed += 1

    await cb.message.answer(f"✅ Готово!\nОтправлено: {sent}\nОшибок: {failed}", reply_markup=admin_main_kb())
    await cb.answer()

@router.message(AdminStates.waiting_for_broadcast_message)
async def process_broadcast(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return

    text = msg.text or msg.caption
    if not text:
        await msg.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
        return

    await msg.answer("📤 Начинаю рассылку...")

    users = await db.get_all_users()
    success = 0
    failed = 0

    for user in users:
        try:
            if msg.photo:
                await msg.bot.send_photo(user['user_id'], msg.photo[-1].file_id, caption=text)
            elif msg.video:
                await msg.bot.send_video(user['user_id'], msg.video.file_id, caption=text)
            elif msg.document:
                await msg.bot.send_document(user['user_id'], msg.document.file_id, caption=text)
            else:
                await msg.bot.send_message(user['user_id'], text)
            success += 1
            await asyncio.sleep(0.03)
        except Exception:
            failed += 1

    await msg.answer(
        f"✅ <b>Рассылка завершена</b>\n\n📨 Отправлено: {success}\n❌ Ошибок: {failed}",
        reply_markup=admin_main_kb()
    )
    await state.clear()


@router.message(AdminStates.waiting_for_broadcast_album)
async def collect_album_or_send(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        return

    data = await state.get_data()
    album = data.get("album", [])
    caption = data.get("caption")

    if msg.text and msg.text.strip().lower() in {"готово", "ok", "go"}:
        if not album:
            await msg.answer("❌ Сначала пришлите альбом из 5 фото.")
            return

        album.sort(key=lambda x: x[0])

        media = []
        for i, (_, file_id) in enumerate(album):
            if i == 0:
                media.append(InputMediaPhoto(media=file_id, caption=caption or "", parse_mode="HTML"))
            else:
                media.append(InputMediaPhoto(media=file_id))

        users = await db.get_all_users()
        await msg.answer(f"📤 Рассылаю альбом… ({len(users)})")
        sent = failed = 0
        for u in users:
            try:
                await msg.bot.send_media_group(chat_id=u['user_id'], media=media)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

        await msg.answer(f"✅ Готово\nОтправлено: {sent}\nОшибок: {failed}")
        await state.clear()
        return

    if msg.photo:
        if not msg.media_group_id:
            await msg.answer("⚠️ Это одиночное фото. Выберите сразу 5 и отправьте как <b>один альбом</b>.")
            return

        file_id = msg.photo[-1].file_id
        album.append((msg.message_id, file_id))

        if msg.caption and not caption:
            caption = msg.caption

        await state.update_data(album=album, caption=caption)
        await msg.answer(f"✅ Принято фото {len(album)}. После загрузки напишите «готово».")
        return

    await msg.answer("Пришлите альбом из 5 фото (одной отправкой) и затем «готово».")

# --- Готовые сценарии ---

@router.callback_query(F.data == "admin_broadcast_siren_flow")
async def admin_broadcast_siren_flow(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    users = await db.get_all_users()
    sent1 = sent2 = err = 0

    await cb.message.answer("🚀 Запускаю двухшаговую рассылку SIREN…")

    # Шаг 1 — всем
    for u in users:
        try:
            await cb.message.bot.send_message(u['user_id'], SIREN_WELCOME, reply_markup=siren_youtube_kb())
            sent1 += 1
            await asyncio.sleep(0.03)
        except Exception:
            err += 1

    # Пауза между шагами
    await asyncio.sleep(60)

    # Шаг 2 — всем
    for u in users:
        try:
            await cb.message.bot.send_message(u['user_id'], SIREN_PRESALE, reply_markup=siren_presale_kb())
            sent2 += 1
            await asyncio.sleep(0.03)
        except Exception:
            err += 1

    await cb.message.answer(
        f"✅ Готово!\nШаг 1 отправлено: {sent1}\nШаг 2 отправлено: {sent2}\nОшибок: {err}",
        reply_markup=admin_main_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "admin_broadcast_presale")
async def admin_broadcast_presale(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    users = await db.get_all_users()
    sent = err = 0

    await cb.message.answer("📝 Отправляю «предзапись» всем пользователям…")
    for u in users:
        try:
            await cb.message.bot.send_message(u['user_id'], SIREN_PRESALE, reply_markup=siren_presale_kb())
            sent += 1
            await asyncio.sleep(0.03)
        except Exception:
            err += 1

    await cb.message.answer(
        f"✅ Готово!\nОтправлено: {sent}\nОшибок: {err}",
        reply_markup=admin_main_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "admin_broadcast_mfd_breathing")
async def admin_broadcast_mfd_breathing(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True)
        return

    # текст с жирным началом
    text = (
        "<b>одно из самых рабочих принципов для здорового мфд - дыхание 🧘🏻‍♀️</b>\n\n"
        "именно с него тело начинает включаться, уходят зажимы, и появляется то самое ощущение лёгкости внутри.\n\n"
        "я собрала для вас короткий дыхательный комплекс, который можно делать в любое время дня - это простая точка входа, с которой начинается хороший результат!\n\n"
        "забирайте комплекс по кнопке ниже 🤍"
    )

    youtube_url = "https://youtu.be/nkbqtXytMLI?si=I_XotqjkkndzwxhG"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="забрать комплекс",
            url=youtube_url
        )
    ]])

    users = await db.get_all_users()
    total = len(users)

    await cb.message.answer(
        f"🧘‍♀️ Запускаю рассылку дыхательного комплекса…\nВсего пользователей: {total}"
    )
    await cb.answer()

    sent = 0
    err = 0

    for u in users:
        try:
            await cb.message.bot.send_message(
                chat_id=u["user_id"],
                text=text,
                reply_markup=kb,
                parse_mode="HTML",  # <= вот это важно
            )
            sent += 1
            await asyncio.sleep(0.03)
        except Exception:
            err += 1

    await cb.message.answer(
        f"✅ Рассылка дыхательного комплекса завершена\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {err}",
        reply_markup=admin_main_kb()
    )

@router.callback_query(F.data == "admin_broadcast_pelvic_flow")
async def admin_broadcast_pelvic_flow(cb: CallbackQuery):
    """
    Трёхшаговая рассылка по курсу «Тазовое Дно»:
    1) Сразу — текст «Зачем и кому нужен курс»
    2) Через 5 минут — текст про выпирающий живот + PDF
    3) Ещё через 7 минут — текст с предзаписью + 6 фото результатов
    """
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True)
        return

    # Тексты
    text1 = (
        "🪷 Зачем и кому нужен этот курс?\n\n"
        "Мои дорогие, скажу честно: если бы каждая женщина хотя бы раз в жизни "
        "обучилась работе с тазовым дном — мир выглядел бы совсем иначе.\n\n"
        "Потому что тазовое дно — это центр женского тела, а его состояние влияет "
        "не только на здоровье, но и на молодость, энергетику и даже внутреннее "
        "ощущение себя.\n\n"
        "Кому особенно важно 👇🏻\n"
        "✨ каждой женщине — в любом возрасте\n"
        "✨ если ощущаете тяжесть, дискомфорт или недержание\n"
        "✨ если беспокоит выпирающий живот\n"
        "✨ если спина или шея «дают о себе знать»\n"
        "✨ если лицо теряет чёткие линии\n"
        "✨ если хочется больше яркости в интиме\n\n"
        "🚫 Противопоказания: беременность, острые воспаления, недавние операции, "
        "онкология, выраженная боль. Перед стартом — консультация со специалистом.\n\n"
        "Этот курс меняет не только тело. Он меняет женскую жизнь изнутри."
    )

    text2 = (
        "А сегодня хочется разобрать одну из самых частых тем — выпирающий живот.\n\n"
        "У меня для вас важный инсайт, который переворачивает представление о тренировках 😲\n\n"
        "Живот может «торчать» даже у стройных девушек — и причина далеко не всегда "
        "в калориях и бесконечных скручиваниях на пресс.\n\n"
        "Я подготовила статью, где можно найти свой тип выпирающего живота и понять, "
        "что с этим делать по-женски: без жёстких тренировок и давления на себя.\n\n"
        "Переходите 👆🏻 и посмотрите, что именно ваше."
    )

    text3 = (
        "Смотрите результаты, когда работа идёт с причиной 👆🏻\n\n"
        "Именно поэтому я всегда говорю: когда тело начинает работать правильно, "
        "оно меняется красиво.\n\n"
        "Без насилия над собой.\n"
        "Без мистики — только физиология и грамотный доказательный подход к женскому телу.\n\n"
        "Оставляю ссылку на предзапись — сейчас самые приятные цены, условия и подарки 🎁\n\n"
        "Успевайте, девочки. Завтра доступ закрою, после этого начну разбирать заявки "
        "и свяжусь с каждой 🤍"
    )

    form_url = "https://docs.google.com/forms/d/e/1FAIpQLScwT0C1KpgRvm9Na05whnoBpJ3f_JOBs_gDS6zBBt2fhSBZXw/viewform"

    users = await db.get_all_users()
    total = len(users)

    await cb.message.answer(
        f"🪷 Запускаю трёхшаговую рассылку по ПД…\nВсего пользователей: {total}"
    )
    await cb.answer()

    async def do_broadcast():
        sent1 = sent2 = sent3 = err = 0

        # --- ШАГ 1: сразу текст про «зачем и кому» ---
        for u in users:
            try:
                await cb.message.bot.send_message(u["user_id"], text1)
                sent1 += 1
                await asyncio.sleep(0.03)
            except Exception:
                err += 1

        await cb.message.answer(f"✅ Шаг 1 отправлен: {sent1}, ошибок: {err}")

        # --- Пауза 5 минут ---
        await asyncio.sleep(5 * 60)

        # --- ШАГ 2: PDF про выпирающий живот с текстом в подписи ---
        try:
            pdf = FSInputFile("files/flat_belly_secrets.pdf")
        except Exception:
            pdf = None

        for u in users:
            try:
                if pdf:
                    await cb.message.bot.send_document(
                        u["user_id"],
                        pdf,
                        caption=text2
                    )
                else:
                    # если PDF нет — хотя бы текст
                    await cb.message.bot.send_message(u["user_id"], text2)
                sent2 += 1
                await asyncio.sleep(0.03)
            except Exception:
                err += 1

        await cb.message.answer(f"✅ Шаг 2 отправлен: {sent2}, всего ошибок: {err}")

        # --- Пауза ещё 7 минут ---
        await asyncio.sleep(7 * 60)

        # --- Подготовка фото (если есть) ---
        def build_results_media():
            media = []
            for path in PELVIC_RESULTS_ASSETS:
                if os.path.exists(path):
                    media.append(InputMediaPhoto(media=FSInputFile(path)))
            return media

        # --- Подготовка фото (если есть) ---
        def build_results_media_with_caption(caption: str | None):
            media = []
            for i, path in enumerate(PELVIC_RESULTS_ASSETS):
                if os.path.exists(path):
                    f = FSInputFile(path)
                    if i == 0 and caption:
                        media.append(InputMediaPhoto(media=f, caption=caption))
                    else:
                        media.append(InputMediaPhoto(media=f))
            return media


        # --- ШАГ 3: текст с предзаписью + фото ---
        reply_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Оставить предзапись",
                url=form_url
            )
        ]])

        for u in users:
            try:
                # сначала альбом с текстом в подписи первого фото
                media = build_results_media_with_caption(text3)
                if media:
                    await cb.message.bot.send_media_group(
                        chat_id=u["user_id"],
                        media=media
                    )
                else:
                    # если вдруг нет фоток — хотя бы текст
                    await cb.message.bot.send_message(
                        u["user_id"],
                        text3
                    )

                # следом отдельным сообщением — кнопка предзаписи
                await cb.message.bot.send_message(
                    u["user_id"],
                    "Оставить предзапись на курс:",
                    reply_markup=reply_kb
                )

                sent3 += 1
                await asyncio.sleep(0.05)
            except Exception:
                err += 1

        await cb.message.answer(
            "✅ Рассылка по ПД завершена\n"
            f"Шаг 1: {sent1}\n"
            f"Шаг 2: {sent2}\n"
            f"Шаг 3: {sent3}\n"
            f"Ошибок: {err}"
        )

    # Запускаем рассылку в фоне, чтобы не блокировать бота
    asyncio.create_task(do_broadcast())

@router.callback_query(F.data == "admin_broadcast_menstruation")
async def admin_broadcast_menstruation(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True)
        return

    # Текст с нужным форматированием
    text = (
        "<b>🩸 сегодня разбирали боль во время менструации</b>\n\n"
        "<i>80% считают это ожидаемым состоянием. а пить но-шпу привычным явлением.</i>\n\n"
        "и чаще всего все работают только с симптомами! когда нужно начинать с причины.\n\n"
        "именно с этим мы будем работать на программе Тазовое дно. та самая ювелирная работа над собой, "
        "чтобы улучшить качество вашей жизни.\n\n"
        "<b>уберем не только болезненные менструации, но и добавим больше ярких ощущений ❤️</b>\n\n"
        "старт программы: 5.01.2025\n"
        "старт продаж по предзаписи: 15.12.2025"
    )

    users = await db.get_all_users()
    total = len(users)

    await cb.message.answer(
        f"🩸 Запускаю рассылку про боль во время менструации…\nВсего пользователей: {total}"
    )
    await cb.answer()

    def build_menstruation_media(caption: str):
        media = []
        for i, path in enumerate(MENSTRUATION_ASSETS):
            if os.path.exists(path):
                f = FSInputFile(path)
                if i == 0:
                    # Первый кадр с текстом и HTML-разметкой
                    media.append(InputMediaPhoto(media=f, caption=caption, parse_mode="HTML"))
                else:
                    media.append(InputMediaPhoto(media=f))
        return media

    sent = 0
    err = 0

    for u in users:
        try:
            media = build_menstruation_media(text)
            if media:
                await cb.message.bot.send_media_group(
                    chat_id=u["user_id"],
                    media=media
                )
            else:
                # если вдруг фотки не найдены — отправим хотя бы текст
                await cb.message.bot.send_message(
                    chat_id=u["user_id"],
                    text=text,
                    parse_mode="HTML",
                )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            err += 1

    await cb.message.answer(
        f"✅ Рассылка про боль во время менструации завершена\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {err}",
        reply_markup=admin_main_kb()
    )

@router.callback_query(F.data == "admin_broadcast_morning_warmup")
async def admin_broadcast_morning_warmup(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True)
        return

    text = (
        "🪷 <i>Дорогая,</i>\n"
        "если не знаешь с чего начать, начинай с зарядки.\n\n"
        "отправляю новую зарядку, которая мягко пробуждает тело и даёт приятное ощущение собранности на весь день ✨"
    )

    youtube_url = "https://youtu.be/tx5I_FqXG54?si=19jGnXTY5rP4Nuj4"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="забрать зарядку", url=youtube_url
    )]])

    users = await db.get_all_users()
    total = len(users)

    await cb.message.answer(f"▶️ Запускаю рассылку утренней зарядки…\nВсего пользователей: {total}")
    await cb.answer()

    sent = err = 0
    for u in users:
        try:
            await cb.message.bot.send_message(
                chat_id=u["user_id"],
                text=text,
                reply_markup=kb,
                parse_mode="HTML"  # важно для курсива
            )
            sent += 1
            await asyncio.sleep(0.03)  # мягкий rate-limit
        except Exception:
            err += 1

    await cb.message.answer(
        f"✅ Рассылка завершена\nОтправлено: {sent}\nОшибок: {err}",
        reply_markup=admin_main_kb()
    )

@router.callback_query(F.data == "admin_broadcast_stool_tips")
async def admin_broadcast_stool_tips(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True)
        return

    text = (
        "<b>ЧТО БЫ Я СДЕЛАЛА УЖЕ СЕГОДНЯ, ЧТОБЫ НОРМАЛИЗОВАТЬ СТУЛ И УБРАТЬ ТЯЖЕСТЬ</b>\n\n"

        "<b>🌙 начала бы утро с мягкого запуска кишечника.</b> наш кишечник реагирует на тепло:\n"
        "<b>тёплая вода → немного лимона → чайная ложка оливкового масла</b> - "
        "<u>и тело просыпается без стимуляторов.</u>\n\n"

        "<b>🌟 добавила бы продукты, которые реально двигают процесс</b>\n"
        "• чернослив или его сок (сорбит тянет воду → стул станет мягче)\n"
        "• тёплые супы (тепло ускоряет перистальтику)\n"
        "• кисломолка (поддержка микробиоты)\n"
        "• киви/яблоки/абрикосы (мягкая клетчатка)\n\n"

        "<b>🌙 убрала бы скрытые провокаторы запоров</b>\n"
        "мало воды, холодная пища, избыток жирного, хаотичный режим - "
        "<u>это тихие причины вздутия и плотного стула.</u>\n\n"

        "<b>🌙 изменила бы позу в туалете</b> = колени выше бёдер, спина мягко ровная.\n"
        "<i>это не «совет», а анатомия:</i> такая позиция расслабляет мышцы, которые обычно мешают дефекации.\n\n"

        "<b>🌟 добавила бы клетчатку, но без фанатизма</b>\n"
        "переизбыток клетчатки при недостатке воды → <u>обратный эффект.</u>\n"
        "здесь важен баланс, а не количество.\n\n"

        "<b>🌙 налаживала бы ритмы</b> - <i>кишечнику нужны сигналы</i>:\n"
        "еда, вода, движение - примерно в одно время.\n"
        "тогда исчезает тяжесть, снижается газообразование, стабилизируется энергия.\n\n"

        "<b>🌙 наблюдала бы за реакциями тела.</b> если процесс «<i>застрял</i>», телу не нужны жёсткие меры.\n"
        "ему нужны = мягкое тепло, движение, тёплая еда и немного поддержки микробиоты.\n\n"

        "🚽 <i>туалетные привычки</i> - это не «мелочи». это про <b>лёгкость, отсутствие отёков, спокойный живот и уверенность в теле</b>.\n\n"
        "и всё это начинается глубже - с дыхания, диафрагмы и тазового дна."
    )

    users = await db.get_all_users()
    total = len(users)

    await cb.message.answer(f"🍑 Запускаю рассылку «Стул и тяжесть (памятка)»…\nВсего пользователей: {total}")
    await cb.answer()

    sent = 0
    err = 0

    for u in users:
        try:
            await cb.message.bot.send_message(
                chat_id=u["user_id"],
                text=text,
                parse_mode="HTML"
            )
            sent += 1
            await asyncio.sleep(0.03)
        except Exception:
            err += 1

    await cb.message.answer(
        f"✅ Памятка отправлена\nОтправлено: {sent}\nОшибок: {err}",
        reply_markup=admin_main_kb()
    )

@router.callback_query(F.data == "admin_download_users_csv")
async def admin_download_users_csv(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True); return

    await cb.answer("📥 Генерирую CSV...", show_alert=False)

    users = await db.get_all_users_full()
    if not users:
        await cb.message.answer("👥 Пользователей пока нет")
        return

    with tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        suffix=".csv",
        encoding="utf-8-sig",
        newline=""
    ) as tmp:
        writer = csv.writer(tmp, delimiter=";")
        writer.writerow([
            "№",
            "user_id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "ref_tag",
            "do_not_disturb",
            "streak_count",
            "created_at",
            "updated_at",
        ])

        for i, u in enumerate(users, 1):
            created = u.get("created_at")
            updated = u.get("updated_at")

            writer.writerow([
                i,
                u.get("user_id") or "",
                u.get("username") or "",
                u.get("first_name") or "",
                u.get("last_name") or "",
                u.get("email") or "",
                u.get("phone") or "",
                u.get("ref_tag") or "",
                "1" if u.get("do_not_disturb") else "0",
                u.get("streak_count") or 0,
                created.strftime("%d.%m.%Y %H:%M") if created else "",
                updated.strftime("%d.%m.%Y %H:%M") if updated else "",
            ])

        tmp_path = tmp.name

    try:
        doc = FSInputFile(tmp_path, filename=f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        await cb.message.answer_document(
            doc,
            caption=(
                f"👥 <b>Экспорт пользователей</b>\n\n"
                f"Всего записей: {len(users)}\n"
                f"Дата выгрузки: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            parse_mode="HTML"
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

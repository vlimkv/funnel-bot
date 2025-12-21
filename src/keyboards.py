# src/keyboards.py
import os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .config import Config
from .texts import (
    SIREN_YOUTUBE_URL, SIREN_YOUTUBE_BTN,
    SIREN_PRESALE_FORM_URL, SIREN_PRESALE_BTN
)

def main_kb() -> InlineKeyboardMarkup:
    """Главная клавиатура (без 'лист ожидания')"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Снова на YouTube", url=Config.YOUTUBE_URL)],
        [InlineKeyboardButton(text="📱 Instagram", url=os.getenv("INSTAGRAM_URL","https://instagram.com"))],
    ])

def contact_kb() -> InlineKeyboardMarkup:
    # Оставляем как есть — используется в текстовом flow «Контакт»
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_contact")]
    ])

# --- Новые клавиатуры для SIREN-флоу ---

def siren_youtube_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=SIREN_YOUTUBE_BTN, url=SIREN_YOUTUBE_URL)],
        [InlineKeyboardButton(text="📱 Instagram", url=os.getenv("INSTAGRAM_URL","https://instagram.com"))],
    ])

def siren_presale_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        # при необходимости другие кнопки
        [
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="menu_main"
            )
        ],
    ])


# --- Главное меню ---

def main_menu_kb() -> InlineKeyboardMarkup:
    """
    Главное меню с тремя разделами:
    - Бесплатные тренировки
    - Полезные статьи и гайды
    - О программе «Тазовое Дно»
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔹 Бесплатные тренировки",
                callback_data="menu_free_trainings"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔹 Полезные статьи и гайды",
                callback_data="menu_articles_guides"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔸 О программе «RE:STORE»",
                callback_data="menu_program_pelvic"
            )
        ],
    ])


# --- Раздел: бесплатные тренировки ---

def free_trainings_kb() -> InlineKeyboardMarkup:
    """
    Кнопки с YouTube-тренировками + возврат в главное меню.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Утренняя зарядка для пробуждения",
                url="https://youtu.be/tx5I_FqXG54?si=19jGnXTY5rP4Nuj4"
            )
        ],
        [
            InlineKeyboardButton(
                text="Утренняя зарядка на всё тело",
                url="https://youtu.be/57rkXbL5rFI?si=yNqnG2gqBSh5PTP9"
            )
        ],
        [
            InlineKeyboardButton(
                text="Комплекс от отёков",
                url="https://youtu.be/QSmoH544J2U?si=AItbmvoqYvKZDlVG"
            )
        ],
        [
            InlineKeyboardButton(
                text="Дыхательные практики: как правильно дышать",
                url="https://youtu.be/nkbqtXytMLI?si=YcE-VHd7Zk-Dbdx0"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Вернуться в главное меню",
                callback_data="menu_main"
            )
        ],
    ])

# --- Раздел: статьи и гайды ---

def articles_guides_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Что такое диастаз и как проверить дома",
                callback_data="article_diastasis"
            )
        ],
        [
            InlineKeyboardButton(
                text="Плоский живот: в чём настоящая причина",
                callback_data="article_flat_belly"
            )
        ],
        [
            InlineKeyboardButton(
                text="Микробиом кишечника и при чём здесь живот",
                callback_data="article_microbiome"
            )
        ],
        [
            InlineKeyboardButton(
                text="Кесарево сечение и «фартук»: что важно знать",
                callback_data="article_csection_apron"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="menu_main"
            )
        ],
    ])


# --- Раздел: о программе «Тазовое Дно» ---

def program_pelvic_floor_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="1️⃣ Ознакомиться с программой",
                url="https://sezaamankeldi.com"
            )
        ],
        [
            InlineKeyboardButton(
                text="2️⃣ Попасть на программу",
                url="https://sezaamankeldi.com/#tarif"
            )
        ],
        [
            InlineKeyboardButton(
                text="3️⃣ Написать в отдел заботы",
                url="https://wa.me/77776776455"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Вернуться в главное меню",
                callback_data="menu_main"
            )
        ],
    ])

WELCOME_VIDEO_URL = "https://youtu.be/9-VN65VmMt4?si=sTYxPCEa-TDJhnhn"

def welcome_video_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Смотреть видео", url=WELCOME_VIDEO_URL)],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main")],
    ])
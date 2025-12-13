from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from ..texts import FREEBIE_SENT, CONTACT_ASK, CONTACT_THX
from ..config import Config
from .. import db
from ..utils import RE_EMAIL, RE_NAME

router = Router()

# Дополнительные хендлеры для warmup-логики можно добавить сюда
# Пока оставляем пустым, но router должен существовать

@router.message(F.text.regexp(r'(?i)отзыв|впечатления|ощущения'))
async def feedback_handler(msg: Message):
    """Реагирует на отзывы пользователя"""
    await msg.answer(
        "Спасибо за отклик! 🤍\n"
        "Важно прислушиваться к телу — так мы строим практику бережно.\n\n"
        f"Если хочешь продолжить — вот следующий материал:\n{Config.NEXT_MATERIAL_URL}"
    )
    await db.inc_streak(msg.from_user.id)
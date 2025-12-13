from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Создание планировщика (без задач прогрева)"""
    sched = AsyncIOScheduler(timezone="UTC")
    # Можно добавить другие периодические задачи здесь при необходимости
    return sched
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from .config import Config
from .routers import all_routers
from . import db
from .scheduler import setup_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("Bot is starting up...")
    
    # Информация о боте
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        raise
    
    # Установка вебхука если настроен
    if Config.WEBHOOK_URL:
        await bot.set_webhook(Config.WEBHOOK_URL)
        logger.info(f"Webhook set to {Config.WEBHOOK_URL}")
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Running in polling mode")

async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("Bot is shutting down...")
    
    # Закрытие БД
    try:
        await db.close_db()
        logger.info("Database closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
    
    # Удаление вебхука
    try:
        await bot.delete_webhook()
        logger.info("Webhook deleted")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
    
    logger.info("Bot stopped")

async def main():
    """Основная функция запуска бота"""
    
    # Валидация конфигурации
    if not Config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set in environment variables!")
        sys.exit(1)
    
    if not Config.DATABASE_URL:
        logger.error("DATABASE_URL is not set in environment variables!")
        sys.exit(1)
    
    logger.info(f"Connecting to database: {Config.DATABASE_URL.split('@')[-1] if '@' in Config.DATABASE_URL else 'local'}")
    
    # Инициализация БД
    try:
        await db.init_db(Config.DATABASE_URL)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.error("Please check your DATABASE_URL and ensure PostgreSQL is running")
        sys.exit(1)
    
    try:
        # Создание бота
        bot = Bot(
            Config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Создание диспетчера
        dp = Dispatcher()
        
        # Регистрация роутеров
        for r in all_routers:
            dp.include_router(r)
        logger.info(f"Registered {len(all_routers)} routers")
        
        # Startup и shutdown хуки
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Запуск планировщика
        scheduler = setup_scheduler(bot)
        scheduler.start()
        logger.info("Scheduler started")
        
        # Информация о режиме работы
        if Config.TEST_MODE:
            logger.warning("⚠️  Running in TEST MODE - warmup messages will be sent in minutes instead of days")
        else:
            logger.info("✓ Running in PRODUCTION MODE")
        
        # Запуск в режиме polling
        logger.info("Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=False
        )
            
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Очистка ресурсов
        try:
            await db.close_db()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
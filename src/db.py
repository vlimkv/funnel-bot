import asyncpg
import json
from typing import Optional, List, Dict, Any
from .config import Config
from datetime import datetime
import os

_pool: Optional[asyncpg.Pool] = None

async def init_db(dsn: str):
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    
    # Загружаем конфигурацию из БД
    from .config import Config
    freebie = await get_config("FREEBIE_URL")
    if freebie:
        Config.FREEBIE_URL = freebie
    
    next_mat = await get_config("NEXT_MATERIAL_URL")
    if next_mat:
        Config.NEXT_MATERIAL_URL = next_mat
    
    course = await get_config("COURSE_URL")
    if course:
        Config.COURSE_URL = course
    
    instagram = await get_config("INSTAGRAM_URL")
    if instagram:
        Config.INSTAGRAM_URL = instagram

async def close_db():
    """Закрытие пула соединений"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def upsert_user(user_id: int, username: str|None, first: str|None, last: str|None, ref: str|None):
    async with _pool.acquire() as conn:
        await conn.execute("""
            insert into tg_users(user_id, username, first_name, last_name, ref_tag)
            values($1,$2,$3,$4,$5)
            on conflict (user_id) do update set
              username=excluded.username,
              first_name=excluded.first_name,
              last_name=excluded.last_name,
              ref_tag=coalesce(tg_users.ref_tag, excluded.ref_tag)
        """, user_id, username, first, last, ref)

async def get_user_stats(user_id: int) -> dict|None:
    """Получение статистики пользователя"""
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("""
            select first_name, email, phone, created_at
            from tg_users 
            where user_id=$1
        """, user_id)
        return dict(row) if row else None

async def save_referral(user_id: int, ref_tag: str|None):
    if not ref_tag:
        return
    async with _pool.acquire() as conn:
        try:
            await conn.execute("insert into referrals(user_id, ref_tag) values ($1,$2)", user_id, ref_tag)
        except asyncpg.UniqueViolationError:
            # Реферал уже сохранен
            pass

async def get_bot_stats() -> dict:
    """Получение расширенной статистики бота"""
    async with _pool.acquire() as conn:
        total = await conn.fetchval("select count(*) from tg_users")
        new_today = await conn.fetchval(
            "select count(*) from tg_users where created_at > now() - interval '1 day'"
        )
        new_week = await conn.fetchval(
            "select count(*) from tg_users where created_at > now() - interval '7 days'"
        )
        new_month = await conn.fetchval(
            "select count(*) from tg_users where created_at > now() - interval '30 days'"
        )
        with_email = await conn.fetchval("select count(*) from tg_users where email is not null")
        with_phone = await conn.fetchval("select count(*) from tg_users where phone is not null")
        with_name = await conn.fetchval("select count(*) from tg_users where first_name is not null")
        with_full_data = await conn.fetchval(
            "select count(*) from tg_users where (email is not null or phone is not null) and first_name is not null"
        )
        referrals = await conn.fetchval("select count(*) from referrals")
        
        return {
            'total_users': total or 0,
            'new_today': new_today or 0,
            'new_week': new_week or 0,
            'new_month': new_month or 0,
            'users_with_email': with_email or 0,
            'users_with_phone': with_phone or 0,
            'users_with_name': with_name or 0,
            'users_with_full_data': with_full_data or 0,
            'referrals': referrals or 0,
        }

async def get_funnel_stats() -> dict:
    """Получение статистики воронки конверсии"""
    async with _pool.acquire() as conn:
        total = await conn.fetchval("select count(*) from tg_users")
        
        # Пользователи, оставившие контакт (email или телефон)
        left_contact = await conn.fetchval(
            "select count(*) from tg_users where email is not null or phone is not null"
        )
        
        # Среднее время до оставления контакта (в часах)
        avg_time_to_email = await conn.fetchval("""
            select extract(epoch from avg(updated_at - created_at))/3600
            from tg_users 
            where email is not null or phone is not null
        """) or 0
        
        return {
            'total_users': total or 0,
            'left_contact': left_contact or 0,
            'avg_time_to_email': int(avg_time_to_email),
        }

async def get_recent_users(limit: int = 20, offset: int = 0):
    """Получение последних пользователей с пагинацией"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch("""
            select user_id, username, first_name, email, phone, created_at
            from tg_users
            order by created_at desc
            limit $1 offset $2
        """, limit, offset)
        return [dict(r) for r in rows]

async def get_all_users():
    """Получение всех пользователей для рассылки"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch("""
            select user_id from tg_users
        """)
        return [dict(r) for r in rows]

async def set_config(key: str, value: str):
    """Сохранение конфигурации в БД"""
    async with _pool.acquire() as conn:
        await conn.execute("""
            insert into bot_config(key, value)
            values($1, $2)
            on conflict (key) do update set value = excluded.value
        """, key, value)

async def get_config(key: str) -> str|None:
    """Получение конфигурации из БД"""
    if not _pool:
        return None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("select value from bot_config where key = $1", key)
        return row['value'] if row else None

async def save_contact(user_id: int, email: str|None = None, phone: str|None = None, first_name: str|None = None):
    """Сохранение контактных данных пользователя (email, телефон, имя)"""
    async with _pool.acquire() as conn:
        await conn.execute("""
            update tg_users 
            set email = coalesce($2, email),
                phone = coalesce($3, phone),
                first_name = coalesce($4, first_name)
            where user_id = $1
        """, user_id, email, phone, first_name)

async def get_total_users_count() -> int:
    """Получение общего количества пользователей"""
    async with _pool.acquire() as conn:
        count = await conn.fetchval("select count(*) from tg_users")
        return count or 0

async def get_users_with_contacts(limit: int = 20, offset: int = 0):
    """Получение пользователей с контактами"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch("""
            select user_id, username, first_name, email, phone, created_at
            from tg_users
            where email is not null or phone is not null or first_name is not null
            order by created_at desc
            limit $1 offset $2
        """, limit, offset)
        return [dict(r) for r in rows]

async def get_contacts_count() -> int:
    """Получение количества пользователей с контактами"""
    async with _pool.acquire() as conn:
        count = await conn.fetchval("""
            select count(*) from tg_users 
            where email is not null or phone is not null or first_name is not null
        """)
        return count or 0

async def get_all_users_with_contacts():
    """Получение всех пользователей с контактами для экспорта CSV"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch("""
            select 
                user_id, 
                username, 
                first_name, 
                email,
                phone,
                created_at
            from tg_users
            where email is not null or phone is not null or first_name is not null
            order by created_at desc
        """)
        return [dict(r) for r in rows]

async def get_all_users_full():
    """Полная выгрузка всех пользователей (для CSV экспорта админом)"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch("""
            select 
                user_id,
                username,
                first_name,
                last_name,
                email,
                phone,
                ref_tag,
                do_not_disturb,
                streak_count,
                created_at,
                updated_at
            from tg_users
            order by created_at desc
        """)
        return [dict(r) for r in rows]

async def set_config(key: str, value: str):
    """Сохранение конфигурации в БД"""
    if not _pool: return
    async with _pool.acquire() as conn:
        await conn.execute("""
            insert into bot_config(key, value)
            values($1, $2)
            on conflict (key) do update set value = excluded.value
        """, key, value)

async def get_config(key: str) -> str|None:
    """Получение конфигурации из БД"""
    if not _pool: return None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("select value from bot_config where key = $1", key)
        return row['value'] if row else None

async def get_welcome_settings() -> Dict[str, Any]:
    """Получить настройки приветствия (текст, фото, кнопки)"""
    raw_json = await get_config("WELCOME_SETTINGS")
    if not raw_json:
        # Дефолтные настройки, если в базе пусто
        return {
            "text": "Привет! 👋\nЯ помогу тебе бережно включить тело.\n\nЖми кнопку ниже, чтобы начать.",
            "photo_id": None,
            "buttons": [] # Список словарей: {"text": "...", "url": "...", "type": "url/callback"}
        }
    try:
        return json.loads(raw_json)
    except:
        return {}

async def save_welcome_settings(settings: Dict[str, Any]):
    """Сохранить настройки приветствия"""
    await set_config("WELCOME_SETTINGS", json.dumps(settings, ensure_ascii=False))

async def get_welcome_chain() -> List[Dict[str, Any]]:
    """Получить цепочку приветственных сообщений"""
    raw_json = await get_config("WELCOME_CHAIN")
    if not raw_json:
        # Дефолт: одно текстовое сообщение
        return [{
            "type": "text",
            "content": "Привет! 👋\nРада тебя видеть.",
            "buttons": []
        }]
    try:
        data = json.loads(raw_json)
        # Если вдруг в базе старый формат (словарь), превращаем в список
        if isinstance(data, dict):
            return [data]
        return data
    except:
        return []

async def save_welcome_chain(chain: List[Dict[str, Any]]):
    """Сохранить всю цепочку"""
    await set_config("WELCOME_CHAIN", json.dumps(chain, ensure_ascii=False))
-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS tg_users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    email VARCHAR(255),
    ref_tag VARCHAR(255),
    do_not_disturb BOOLEAN DEFAULT FALSE,
    streak_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создание таблицы рефералов
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES tg_users(user_id) ON DELETE CASCADE,
    ref_tag VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, ref_tag)
);

-- Создание таблицы очереди прогрева
CREATE TABLE IF NOT EXISTS warmup_queue (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES tg_users(user_id) ON DELETE CASCADE,
    send_at TIMESTAMP WITH TIME ZONE NOT NULL,
    step INTEGER NOT NULL,
    payload JSONB DEFAULT '{}',
    sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_config (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_warmup_queue_send_at ON warmup_queue(send_at) WHERE sent = FALSE;
CREATE INDEX IF NOT EXISTS idx_warmup_queue_user_id ON warmup_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_user_id ON referrals(user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_ref_tag ON referrals(ref_tag);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_tg_users_updated_at ON tg_users;
CREATE TRIGGER update_tg_users_updated_at
    BEFORE UPDATE ON tg_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер для автоматического обновления updated_at в bot_config
DROP TRIGGER IF EXISTS update_bot_config_updated_at ON bot_config;
CREATE TRIGGER update_bot_config_updated_at
    BEFORE UPDATE ON bot_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Добавление колонки phone
ALTER TABLE tg_users 
ADD COLUMN IF NOT EXISTS phone VARCHAR(20);

-- Добавление индекса для быстрого поиска по телефону
CREATE INDEX IF NOT EXISTS idx_tg_users_phone ON tg_users(phone) WHERE phone IS NOT NULL;

-- Обновление статистики для контактов
COMMENT ON COLUMN tg_users.phone IS 'Телефон пользователя для связи';

-- tg_users: добавим недостающий столбец phone
alter table if exists tg_users
  add column if not exists phone text;

-- на всякий случай обновим updated_at, которого ты используешь в воронке:
alter table if exists tg_users
  add column if not exists updated_at timestamptz default now();

-- триггер для updated_at (опционально, но полезно)
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

do $$
begin
  if not exists (
    select 1 from pg_trigger where tgname = 'tg_set_updated_at_tg_users'
  ) then
    create trigger tg_set_updated_at_tg_users
    before update on tg_users
    for each row execute function set_updated_at();
  end if;
end $$;
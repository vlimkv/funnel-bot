-- users
CREATE TABLE IF NOT EXISTS tg_users (
  user_id BIGINT PRIMARY KEY,
  username VARCHAR(255),
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  email VARCHAR(255),
  phone VARCHAR(20),
  ref_tag VARCHAR(255),
  do_not_disturb BOOLEAN DEFAULT FALSE,
  streak_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- referrals
CREATE TABLE IF NOT EXISTS referrals (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES tg_users(user_id) ON DELETE CASCADE,
  ref_tag VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, ref_tag)
);

-- warmup queue
CREATE TABLE IF NOT EXISTS warmup_queue (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES tg_users(user_id) ON DELETE CASCADE,
  send_at TIMESTAMPTZ NOT NULL,
  step INTEGER NOT NULL,
  payload JSONB DEFAULT '{}'::jsonb,
  sent BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- config
CREATE TABLE IF NOT EXISTS bot_config (
  key VARCHAR(255) PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- indexes
CREATE INDEX IF NOT EXISTS idx_warmup_queue_send_at ON warmup_queue(send_at) WHERE sent = FALSE;
CREATE INDEX IF NOT EXISTS idx_warmup_queue_user_id ON warmup_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_user_id ON referrals(user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_ref_tag ON referrals(ref_tag);
CREATE INDEX IF NOT EXISTS idx_tg_users_phone ON tg_users(phone) WHERE phone IS NOT NULL;

-- updated_at trigger function
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- triggers (safe create)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tg_users_set_updated_at') THEN
    CREATE TRIGGER tg_users_set_updated_at
    BEFORE UPDATE ON tg_users
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'bot_config_set_updated_at') THEN
    CREATE TRIGGER bot_config_set_updated_at
    BEFORE UPDATE ON bot_config
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
  END IF;
END $$;
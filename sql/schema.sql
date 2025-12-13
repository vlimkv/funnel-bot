create table if not exists tg_users (
  user_id bigint primary key,
  username text,
  first_name text,
  last_name text,
  email text,
  created_at timestamptz default now(),
  ref_tag text,
  do_not_disturb boolean default false,
  streak_count int default 0
);

create table if not exists warmup_queue (
  id bigserial primary key,
  user_id bigint not null,
  send_at timestamptz not null,
  step int not null,
  payload jsonb default '{}'::jsonb,
  sent boolean default false,
  constraint fk_user foreign key (user_id) references tg_users(user_id) on delete cascade
);

create index if not exists warmup_due_idx on warmup_queue (send_at) where sent=false;

create table if not exists referrals (
  id bigserial primary key,
  user_id bigint not null,
  ref_tag text,
  created_at timestamptz default now()
);
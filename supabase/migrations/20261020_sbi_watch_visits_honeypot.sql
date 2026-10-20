-- ShopBot Index, 20 Oct 2026 (approved by Gus): "Watch this store" alerts, cookie-free visit counter, honeypot drop counter.
-- All tables: RLS on with no policies (no anon/authenticated access); written only by edge functions via service_role.

-- 1. Watches: one row per (subscriber, store). store_id is the crawl's retailers[].id (stable; slugs can change).
create table if not exists public.sbi_watches (
  id bigint generated always as identity primary key,
  subscriber_id bigint not null references public.sbi_subscribers(id) on delete cascade,
  store_id text not null check (store_id ~ '^[A-Za-z0-9._-]{1,120}$'),
  token uuid not null default gen_random_uuid() unique,          -- for the "stop these alerts" link
  created_at timestamptz not null default now(),
  last_alert_crawl text,                                          -- crawl_date of the last alert sent (idempotency)
  last_alerted_at timestamptz,
  unique (subscriber_id, store_id)
);
create index if not exists sbi_watches_store_idx on public.sbi_watches (store_id);
alter table public.sbi_watches enable row level security;

-- 2. Visit counter: aggregated per day; no IP, no cookie, no user agent, no personal data.
create table if not exists public.sbi_pageviews_daily (
  day date not null,
  path text not null check (char_length(path) <= 200),
  ref_domain text not null default '' check (char_length(ref_domain) <= 100),
  utm_source text not null default '' check (char_length(utm_source) <= 60),
  utm_medium text not null default '' check (char_length(utm_medium) <= 60),
  utm_campaign text not null default '' check (char_length(utm_campaign) <= 60),
  n integer not null default 0,
  primary key (day, path, ref_domain, utm_source, utm_medium, utm_campaign)
);
alter table public.sbi_pageviews_daily enable row level security;

create or replace function public.sbi_count_view(p_path text, p_ref text, p_src text, p_med text, p_camp text)
returns void language sql security definer set search_path = '' as $$
  insert into public.sbi_pageviews_daily as t (day, path, ref_domain, utm_source, utm_medium, utm_campaign, n)
  values ((now() at time zone 'Europe/Zurich')::date, left(coalesce(p_path,'/'),200), left(coalesce(p_ref,''),100),
          left(coalesce(p_src,''),60), left(coalesce(p_med,''),60), left(coalesce(p_camp,''),60), 1)
  on conflict (day, path, ref_domain, utm_source, utm_medium, utm_campaign) do update set n = t.n + 1;
$$;
revoke all on function public.sbi_count_view(text,text,text,text,text) from public, anon, authenticated;
grant execute on function public.sbi_count_view(text,text,text,text,text) to service_role;

-- 3. Honeypot drops: a count per day only.
create table if not exists public.sbi_honeypot_daily (
  day date primary key,
  n integer not null default 0
);
alter table public.sbi_honeypot_daily enable row level security;

create or replace function public.sbi_count_honeypot()
returns void language sql security definer set search_path = '' as $$
  insert into public.sbi_honeypot_daily as t (day, n) values ((now() at time zone 'Europe/Zurich')::date, 1)
  on conflict (day) do update set n = t.n + 1;
$$;
revoke all on function public.sbi_count_honeypot() from public, anon, authenticated;
grant execute on function public.sbi_count_honeypot() to service_role;

-- 4. Alert settings for the sbi-watch-alerts function (service_role only):
--    alerts_token = Vault secret sbi_alerts_token (shared with the weekly job on the box, /home/box/.private/sbi-alerts.json)
--    alerts_enabled = Vault secret sbi_watch_alerts_enabled = 'true' (default OFF: only dry runs and test-inbox sends)
create or replace function public.sbi_alerts_config()
returns table (api_key text, alerts_token text, alerts_enabled boolean)
language sql security definer set search_path = '' stable as $$
  select
    (select decrypted_secret from vault.decrypted_secrets where name = 'sbi_resend_api_key' limit 1),
    (select decrypted_secret from vault.decrypted_secrets where name = 'sbi_alerts_token' limit 1),
    coalesce((select decrypted_secret = 'true' from vault.decrypted_secrets where name = 'sbi_watch_alerts_enabled' limit 1), false);
$$;
revoke all on function public.sbi_alerts_config() from public, anon, authenticated;
grant execute on function public.sbi_alerts_config() to service_role;

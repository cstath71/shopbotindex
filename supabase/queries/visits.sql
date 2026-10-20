-- ShopBot Index visit counts (private; run in the Supabase SQL editor or via the Supabase connector's execute_sql).
-- Data: public.sbi_pageviews_daily (day in Zurich time, path, referrer domain, utm tags, n). No personal data stored.
-- Last 14 days, per day
select day, sum(n) as views from public.sbi_pageviews_daily where day >= current_date - 13 group by day order by day desc;
-- Top pages, last 7 days
select path, sum(n) as views from public.sbi_pageviews_daily where day >= current_date - 6 group by path order by views desc limit 25;
-- Where visitors come from (referrer domain or utm_source / ?ref=), last 7 days
select coalesce(nullif(utm_source,''), nullif(ref_domain,''), '(direct or hidden)') as source, utm_medium, utm_campaign, sum(n) as views
from public.sbi_pageviews_daily where day >= current_date - 6 group by 1,2,3 order by views desc limit 25;
-- Signups vs honeypot drops per day (counts only)
select d.day, coalesce(s.signups,0) as signups, coalesce(h.n,0) as honeypot_drops
from (select generate_series(current_date - 13, current_date, '1 day')::date as day) d
left join (select (created_at at time zone 'Europe/Zurich')::date as day, count(*) as signups from public.sbi_subscribers group by 1) s using (day)
left join public.sbi_honeypot_daily h using (day) order by d.day desc;
-- Watches per store (no addresses)
select store_id, count(*) as watchers from public.sbi_watches group by store_id order by watchers desc;

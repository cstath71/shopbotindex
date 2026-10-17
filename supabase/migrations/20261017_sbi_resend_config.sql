-- Returns the Resend settings for sbi-subscribe from Supabase Vault.
-- SECURITY DEFINER so it can read vault.decrypted_secrets; callable only by service_role (the edge function's server-side client).
create or replace function public.sbi_resend_config()
returns table (api_key text, segment_id text)
language sql
security definer
set search_path = ''
stable
as $$
  select
    (select decrypted_secret from vault.decrypted_secrets where name = 'sbi_resend_api_key' limit 1),
    (select decrypted_secret from vault.decrypted_secrets where name = 'sbi_resend_segment_id' limit 1);
$$;
revoke all on function public.sbi_resend_config() from public;
revoke all on function public.sbi_resend_config() from anon, authenticated;
grant execute on function public.sbi_resend_config() to service_role;

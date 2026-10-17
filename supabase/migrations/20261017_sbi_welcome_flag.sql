-- Adds welcome_enabled to public.sbi_resend_config(): true only when the welcome flag is on
-- (Vault secret sbi_welcome_enabled = 'true'; default off). Still SECURITY DEFINER and executable by service_role only.
drop function if exists public.sbi_resend_config();
create function public.sbi_resend_config()
returns table (api_key text, segment_id text, welcome_enabled boolean)
language sql
security definer
set search_path = ''
stable
as $$
  select
    (select decrypted_secret from vault.decrypted_secrets where name = 'sbi_resend_api_key' limit 1),
    (select decrypted_secret from vault.decrypted_secrets where name = 'sbi_resend_segment_id' limit 1),
    coalesce((select decrypted_secret = 'true' from vault.decrypted_secrets where name = 'sbi_welcome_enabled' limit 1), false);
$$;
revoke all on function public.sbi_resend_config() from public;
revoke all on function public.sbi_resend_config() from anon, authenticated;
grant execute on function public.sbi_resend_config() to service_role;

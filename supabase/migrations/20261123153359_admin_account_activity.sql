-- Read-only account reporting for existing, confirmed administrators.
-- Auth tables stay private; only the explicitly selected account fields leave
-- this function. No credentials, tokens, metadata or review identities return.
CREATE FUNCTION public.btb_admin_accounts(
 p_days integer DEFAULT 5, p_search text DEFAULT '', p_offset integer DEFAULT 0
) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path='' AS $$
DECLARE v_search text:=lower(btrim(coalesce(p_search,''))); v_now timestamptz:=now(); result jsonb;
BEGIN
 IF auth.uid() IS NULL OR NOT coalesce(public.btb_is_admin(),false)
  OR NOT EXISTS(SELECT 1 FROM auth.users u WHERE u.id=auth.uid()
    AND u.deleted_at IS NULL AND u.email_confirmed_at IS NOT NULL
    AND NOT coalesce(u.is_anonymous,false)
    AND (u.banned_until IS NULL OR u.banned_until<=v_now))
 THEN RAISE EXCEPTION 'Admin access required.' USING errcode='42501'; END IF;
 IF (p_days IS NOT NULL AND p_days NOT IN (5,7,30,90)) OR p_offset IS NULL
   OR p_offset<0 OR p_offset>1000000 OR length(v_search)>100
 THEN RAISE EXCEPTION 'Invalid account report request.' USING errcode='22023'; END IF;

 WITH accounts AS MATERIALIZED (
  SELECT u.id,u.email,u.created_at,u.email_confirmed_at,u.last_sign_in_at,
   v.business_name,v.business_url,coalesce(v.verification_status,'not_applied') AS vendor_status,
   EXISTS(SELECT 1 FROM btb_private.admins a WHERE a.user_id=u.id) AS is_admin
  FROM auth.users u LEFT JOIN public.vendor_profiles v ON v.user_id=u.id
  WHERE u.deleted_at IS NULL AND NOT coalesce(u.is_anonymous,false)
   AND (u.created_at IS NULL OR u.created_at<=v_now)
 ), filtered AS MATERIALIZED (
  SELECT a.* FROM accounts a
  WHERE (p_days IS NULL OR a.created_at>=v_now-make_interval(days=>p_days))
   AND (v_search='' OR strpos(lower(coalesce(a.email,'')),v_search)>0
      OR strpos(lower(coalesce(a.business_name,'')),v_search)>0)
 ), page AS (
  SELECT * FROM filtered ORDER BY created_at DESC NULLS LAST,id LIMIT 20 OFFSET p_offset
 )
 SELECT jsonb_build_object(
  'checked_at',v_now,'page_size',20,'total',(SELECT count(*) FROM filtered),
  'summary',jsonb_build_object('total',(SELECT count(*) FROM accounts),
   'last_5_days',(SELECT count(*) FROM accounts WHERE created_at BETWEEN v_now-interval '5 days' AND v_now),
   'last_30_days',(SELECT count(*) FROM accounts WHERE created_at BETWEEN v_now-interval '30 days' AND v_now)),
  'items',(SELECT coalesce(jsonb_agg(to_jsonb(p) ORDER BY p.created_at DESC NULLS LAST,p.id),'[]'::jsonb) FROM page p)
 ) INTO result;
 RETURN result;
END; $$;
REVOKE ALL ON FUNCTION public.btb_admin_accounts(integer,text,integer) FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.btb_admin_accounts(integer,text,integer) TO authenticated;
COMMENT ON FUNCTION public.btb_admin_accounts(integer,text,integer) IS
 'Admin-only read-only signup report. Excludes deleted and anonymous users; never grants access to auth tables.';
NOTIFY pgrst,'reload schema';

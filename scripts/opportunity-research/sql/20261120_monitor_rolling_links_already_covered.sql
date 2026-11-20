-- Do not re-promote generic rolling-vendor links to "New" when the
-- organizer's existing year-round application is already published.
-- They remain monitored; different dated programs can still be researched.
DO $upgrade$
DECLARE original text;updated text;
old_case text := $old$next_state:=case
   when s in ('closed','restricted','application_directory','unlinked') then 'monitoring'$old$;
new_case text := $new$next_state:=case
   when s='confirmed_rolling' and exists(
     select 1 from public.vendor_opportunities o
     where o.publication='published' and o.schedule_type='rolling_market'
      and lower(trim(o.organizer))=lower(trim((
       select organizer from btb_private.triangle_discovery_leads
       where target_url=target and source_url=src limit 1)))
      and lower(trim(o.city))=lower(trim((
       select city from btb_private.triangle_discovery_leads
       where target_url=target and source_url=src limit 1)))
      and split_part(o.source_url,'/',3)=split_part(src,'/',3)
   ) then 'monitoring'
   when s in ('closed','restricted','application_directory','unlinked') then 'monitoring'$new$;
BEGIN
 SELECT pg_get_functiondef('public.btb_research_diagnose_leads(jsonb)'::regprocedure) INTO original;
 IF original is null or position(old_case in original)=0
 THEN RAISE EXCEPTION 'Unexpected diagnostic case; migration aborted'; END IF;
 updated:=replace(original,old_case,new_case);
 EXECUTE updated;
END $upgrade$;

UPDATE btb_private.triangle_discovery_leads l
SET review_state='monitoring',
 research_reason='Organizer already has a published rolling vendor opportunity; alternate Google Forms shortcut not proven equivalent. Monitor without displaying a duplicate as a new market.'
WHERE l.review_state='new' and l.research_status='confirmed_rolling'
 and exists(select 1 from public.vendor_opportunities o
   where o.publication='published' and o.schedule_type='rolling_market'
     and lower(trim(o.organizer))=lower(trim(l.organizer))
     and lower(trim(o.city))=lower(trim(l.city))
     and split_part(o.source_url,'/',3)=split_part(l.source_url,'/',3));

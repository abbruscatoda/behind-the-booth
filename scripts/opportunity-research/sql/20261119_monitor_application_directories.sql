-- Generic organizer directories are research inputs, not new applications.
-- Continue crawling them daily, but keep them out of the actionable New queue.
alter table btb_private.triangle_discovery_leads
 drop constraint if exists triangle_discovery_research_status_check;
alter table btb_private.triangle_discovery_leads
 add constraint triangle_discovery_research_status_check
 check(research_status in ('not_checked','confirmed_seasonal','confirmed_rolling',
 'restricted','closed','multi_date','form_gated','missing_event','source_unavailable',
 'unlinked','not_application','needs_evidence','application_directory'));

DO $upgrade$
DECLARE
 original text;
 updated text;
 old_allowed text := $old$'missing_event','source_unavailable','unlinked','not_application','needs_evidence')$old$;
 new_allowed text := $new$'missing_event','source_unavailable','unlinked','not_application','needs_evidence','application_directory')$new$;
 old_monitor text := $old$when s in ('closed','restricted') then 'monitoring'$old$;
 new_monitor text := $new$when s in ('closed','restricted','application_directory') then 'monitoring'$new$;
BEGIN
 select pg_get_functiondef('public.btb_research_diagnose_leads(jsonb)'::regprocedure) into original;
 if original is null or position(old_allowed in original)=0 or position(old_monitor in original)=0
 then raise exception 'Unexpected worker diagnostic function; no changes applied';end if;
 updated:=replace(original,old_allowed,new_allowed);
 updated:=replace(updated,old_monitor,new_monitor);
 execute updated;
END $upgrade$;

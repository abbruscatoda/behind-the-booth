-- A lead that currently lacks an official organizer link is not a
-- newly available market. Recheck monitored links daily and reactivate
-- only after verification. Confirmed non-market workshops/consignment
-- applications can be ignored without hiding genuine future markets.
DO $upgrade$
DECLARE olddef text;updated text;
old_monitor text := $old$when s in ('closed','restricted','application_directory') then 'monitoring'$old$;
new_monitor text := $new$when s in ('closed','restricted','application_directory','unlinked') then 'monitoring'$new$;
old_self text := $old$when s='not_application'
       and (rtrim(target,'/#')=rtrim(src,'/#') or right(target,2)='/#')
       then 'resolved'$old$;
new_self text := $new$when s='not_application'
       and reason_text like 'Not a vendor market:%' then 'ignored'
   when s='not_application'
       and (rtrim(target,'/#')=rtrim(src,'/#') or right(target,2)='/#')
       then 'resolved'$new$;
BEGIN
 select pg_get_functiondef('public.btb_research_diagnose_leads(jsonb)'::regprocedure) into olddef;
 IF olddef is null or position(old_monitor in olddef)=0 or position(old_self in olddef)=0
 THEN RAISE EXCEPTION 'Unexpected diagnostic function; migration aborted';END IF;
 updated:=replace(olddef,old_monitor,new_monitor);
 updated:=replace(updated,old_self,new_self);
 EXECUTE updated;
END $upgrade$;

-- The discovery worker must not fail an entire run because one link
-- hits a cardinality conflict while a previously published card reconciles.
-- Reconcile only truly new/changed rows (not each unchanged URL upsert).
DROP TRIGGER IF EXISTS btb_reconcile_new_discovery_leads ON btb_private.triangle_discovery_leads;
CREATE TRIGGER btb_reconcile_inserted_discovery_leads
AFTER INSERT ON btb_private.triangle_discovery_leads
FOR EACH ROW EXECUTE FUNCTION btb_private.reconcile_discovery_trigger();
CREATE TRIGGER btb_reconcile_changed_discovery_sources
AFTER UPDATE OF source_url,target_url ON btb_private.triangle_discovery_leads
FOR EACH ROW WHEN (
 OLD.source_url IS DISTINCT FROM NEW.source_url
 OR OLD.target_url IS DISTINCT FROM NEW.target_url
)
EXECUTE FUNCTION btb_private.reconcile_discovery_trigger();

DO $upgrade$
DECLARE olddef text;updated text;
old_decl text := $old$entry jsonb; saved integer:=0; skipped integer:=0;$old$;
new_decl text := $new$entry jsonb; saved integer:=0; skipped integer:=0; cardinality_conflicts integer:=0;$new$;
old_block text := $old$  insert into btb_private.triangle_discovery_leads(
   target_url,source_url,title,organizer,city,notes)
  values(url,source,entry->>'title',org,town,left(coalesce(entry->>'notes',''),500))
  on conflict(target_url) do update set
   last_seen=now(),source_url=excluded.source_url
  where btb_private.triangle_discovery_leads.organizer=excluded.organizer
    and btb_private.triangle_discovery_leads.city=excluded.city;
  if found then saved:=saved+1;
  else skipped:=skipped+1;end if;$old$;
new_block text := $new$  begin
   insert into btb_private.triangle_discovery_leads(
    target_url,source_url,title,organizer,city,notes)
   values(url,source,entry->>'title',org,town,left(coalesce(entry->>'notes',''),500))
   on conflict(target_url) do update set
    last_seen=now(),source_url=excluded.source_url
   where btb_private.triangle_discovery_leads.organizer=excluded.organizer
     and btb_private.triangle_discovery_leads.city=excluded.city;
   if found then saved:=saved+1;
   else skipped:=skipped+1;end if;
  exception when cardinality_violation then
   -- Skip only this URL, keep all other independent verified leads.
   -- Record the failure category without exposing source content.
   cardinality_conflicts:=cardinality_conflicts+1;
   skipped:=skipped+1;
  end;$new$;
old_return text := $old$'approved_sources',(select count(*) from btb_private.triangle_research_sources where active)$old$;
new_return text := $new$'cardinality_conflicts',cardinality_conflicts,
  'approved_sources',(select count(*) from btb_private.triangle_research_sources where active)$new$;
BEGIN
 SELECT pg_get_functiondef('public.btb_research_record_discovery_leads(jsonb,jsonb)'::regprocedure)
 INTO olddef;
 IF olddef IS NULL
  OR position(old_decl in olddef)=0
  OR position(old_block in olddef)=0
  OR position(old_return in olddef)=0
 THEN RAISE EXCEPTION 'Unexpected discovery RPC version; not changed'; END IF;
 updated:=replace(olddef,old_decl,new_decl);
 updated:=replace(updated,old_block,new_block);
 updated:=replace(updated,old_return,new_return);
 execute updated;
END $upgrade$;

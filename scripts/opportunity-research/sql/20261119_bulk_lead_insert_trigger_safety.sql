-- Batch inserts should not trigger full-table reconciliation for every row.
-- A row-level reconciliation UPDATE inside an INSERT ... ON CONFLICT path
-- can raise SQLSTATE 21000 (cardinality violation). Reconcile once after
-- all rows have been inserted, preserving immediate reconciliation elsewhere.
create or replace function btb_private.reconcile_discovery_trigger()
returns trigger language plpgsql security definer set search_path='' as $trigger$
begin
 if current_setting('btb.discovery_bulk_ingest',true)='on' then
  return null;
 end if;
 perform btb_private.resolve_published_discovery_leads();
 return null;
end $trigger$;
revoke all on function btb_private.reconcile_discovery_trigger() from public,anon,authenticated;

do $upgrade$
declare original text;updated text;
begin
 select pg_get_functiondef('public.btb_research_record_discovery_leads(jsonb,jsonb)'::regprocedure) into original;
 if original is null
   or position('perform public.btb_research_authorize();' in original)=0
   or position('for entry in select value from jsonb_array_elements(p_leads) loop' in original)=0
   or position('return jsonb_build_object(' in original)=0
 then raise exception 'Unexpected lead worker function; bulk ingestion change aborted';end if;
 updated:=replace(original,
  'update btb_private.triangle_research_sources set active=false;',
  'perform set_config(''btb.discovery_bulk_ingest'',''on'',true);'||chr(10)||
  ' update btb_private.triangle_research_sources set active=false;');
 -- End only the validated batch phase before reconciling published links.
 updated:=replace(updated,
  'return jsonb_build_object(''saved'',saved,''skipped'',skipped,',
  'perform set_config(''btb.discovery_bulk_ingest'',''off'',true);'||chr(10)||
  ' perform btb_private.resolve_published_discovery_leads();'||chr(10)||
  ' return jsonb_build_object(''saved'',saved,''skipped'',skipped,');
 if position('perform btb_private.resolve_published_discovery_leads();' in updated)=0
 then raise exception 'Bulk lead reconciliation not installed';end if;
 execute updated;
end $upgrade$;

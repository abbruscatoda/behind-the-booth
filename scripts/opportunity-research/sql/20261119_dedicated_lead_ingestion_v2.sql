-- Dedicated two-argument worker RPC; avoids legacy overloaded PostgREST
-- name resolution while preserving source-registry rules and private auth.
DO $install$
DECLARE current_definition text; dedicated_definition text;
BEGIN
 SELECT pg_get_functiondef('public.btb_research_record_discovery_leads(jsonb,jsonb)'::regprocedure)
 INTO current_definition;
 IF current_definition IS NULL
 OR position('create or replace function public.btb_research_record_discovery_leads(' in lower(current_definition))=0
 THEN RAISE EXCEPTION 'Approved two-argument ingestion RPC missing';END IF;
 dedicated_definition:=replace(current_definition,
  'btb_research_record_discovery_leads(','btb_research_record_discovery_leads_v2(');
 IF dedicated_definition=current_definition THEN
  RAISE EXCEPTION 'Unable to name dedicated ingestion function';END IF;
 EXECUTE dedicated_definition;
END $install$;
revoke all on function public.btb_research_record_discovery_leads_v2(jsonb,jsonb)
 from public,anon,authenticated;
grant execute on function public.btb_research_record_discovery_leads_v2(jsonb,jsonb)
 to anon,authenticated,service_role;

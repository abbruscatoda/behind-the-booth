-- Finalize published-source matches only AFTER a separately committed
-- discovery-ingestion RPC. Reconciling newly inserted rows inside the same
-- ingestion command triggered SQLSTATE 21000 under bulk upsert conditions.
DO $upgrade$
DECLARE original text;revised text;
 oldpiece text := $old$ perform btb_private.resolve_published_discovery_leads();
 return jsonb_build_object($old$;
 newpiece text := $new$ -- Final reconciliation occurs in a second authenticated RPC after commit.
 return jsonb_build_object($new$;
BEGIN
 select pg_get_functiondef('public.btb_research_record_discovery_leads_v2(jsonb,jsonb)'::regprocedure)
 into original;
 if original is null or position(oldpiece in original)=0
 then raise exception 'Dedicated ingestion version changed; no patch applied';end if;
 revised:=replace(original,oldpiece,newpiece);
 execute revised;
END $upgrade$;

create or replace function public.btb_research_finalize_discovery_leads()
returns jsonb language plpgsql security definer set search_path='' as $finalize$
declare
 previous_count bigint;current_count bigint;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('resolved',0,'paused',true);end if;
 select count(*) into previous_count from btb_private.triangle_discovery_leads where review_state='resolved';
 perform btb_private.resolve_published_discovery_leads();
 select count(*) into current_count from btb_private.triangle_discovery_leads where review_state='resolved';
 return jsonb_build_object('resolved',greatest(0,current_count-previous_count));
end $finalize$;
revoke all on function public.btb_research_finalize_discovery_leads() from public,anon,authenticated;
grant execute on function public.btb_research_finalize_discovery_leads() to anon,authenticated,service_role;

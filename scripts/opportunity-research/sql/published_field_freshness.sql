-- Concurrent older worker snapshots cannot replace newer field research.
do $patch$
declare definition text; marker text;
begin
 select pg_get_functiondef('public.btb_research_record_facts(jsonb)'::regprocedure) into definition;
 if position('Newer field evidence already stored' in definition)>0 then return;end if;
 marker:='select receipt into previous from btb_private.opportunity_field_facts where opportunity_id=o.id;';
 if position(marker in definition)=0 then raise exception 'Unexpected field evidence freshness guard';end if;
 execute replace(definition,marker,marker||$new$
 if (previous->>'checked_at')::timestamptz>checked then
  return jsonb_build_object('action','skipped','reason','Newer field evidence already stored');
 end if;
$new$);
end $patch$;

-- Hosted worker ingestion rejected the multi-row registry reset with SQLSTATE
-- 21000. Reset each existing primary-key row individually in the same atomic
-- transaction; preserve reviewed-source validation and all authorization.
DO $patch$
DECLARE definition text;
 oldpiece text := 'update btb_private.triangle_research_sources set active=false;';
 newpiece text := $new$for source in select r.source_url from btb_private.triangle_research_sources r order by r.source_url loop
  update btb_private.triangle_research_sources r set active=false where r.source_url=source;
 end loop;$new$;
BEGIN
 select pg_get_functiondef('public.btb_research_record_discovery_leads_v2(jsonb,jsonb)'::regprocedure) into definition;
 if position(newpiece in definition)>0 then return;end if;
 if (length(definition)-length(replace(definition,oldpiece,'')))/length(oldpiece)<>1
  or position('perform public.btb_research_authorize();' in definition)=0
 then raise exception 'Unexpected reviewed-source ingestion guard; no change applied';end if;
 execute replace(definition,oldpiece,newpiece);
END $patch$;

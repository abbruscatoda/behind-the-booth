-- Broader discovery has bounded private source diagnostics. Retain the
-- worker-secret authorization and permit reports up to 64 KB instead of 12 KB.
DO $patch$
DECLARE definition text; oldpiece text := 'octet_length(p_summary::text)>12000';
BEGIN
 select pg_get_functiondef('public.btb_research_run(uuid,jsonb)'::regprocedure) into definition;
 if position('octet_length(p_summary::text)>64000' in definition)>0 then return;end if;
 if position(oldpiece in definition)=0 or position('perform public.btb_research_authorize();' in definition)=0
 then raise exception 'Unexpected research run guard; no change applied';end if;
 execute replace(definition,oldpiece,'octet_length(p_summary::text)>64000');
END $patch$;

-- Rebus Works uses .us. Preserve HTTPS, hostname, payload and secret guards.
DO $patch$
DECLARE definition text;
BEGIN
 select pg_get_functiondef('public.btb_research_record_discovery_leads_v2(jsonb,jsonb)'::regprocedure) into definition;
 if position('(com|org|net|gov|edu|us)$' in definition)>0 then return;end if;
 if position('(com|org|net|gov|edu)$' in definition)=0 then raise exception 'Unexpected official-source host guard';end if;
 definition:=replace(definition,'(com|org|net|gov|edu)$','(com|org|net|gov|edu|us)$');
 execute definition;
END $patch$;

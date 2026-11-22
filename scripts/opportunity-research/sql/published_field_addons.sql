-- Existing installations retain optional charges as separate sourced options.
do $patch$
declare definition text;
begin
 select pg_get_functiondef('public.btb_research_record_facts(jsonb)'::regprocedure) into definition;
 if position('(''booth'',''application'',''addon'')' in definition)>0 then return;end if;
 if position('(''booth'',''application'')' in definition)=0 then raise exception 'Unexpected price-option guard';end if;
 execute replace(definition,'(''booth'',''application'')','(''booth'',''application'',''addon'')');
end $patch$;

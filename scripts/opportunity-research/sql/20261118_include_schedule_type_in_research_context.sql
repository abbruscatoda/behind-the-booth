-- The worker's existing-result verifier must receive the saved schedule
-- discriminator; otherwise newly verified seasonal applications are
-- incorrectly treated as source conflicts on their next scheduled check.
do $fix$
declare definition text;
begin
 select pg_get_functiondef('public.btb_research_context()'::regprocedure) into definition;
 if position('o.verification_policy,o.schedule_type,o.updated_at' in definition)>0
 then return;end if;
 if position('o.verification_policy,o.updated_at' in definition)=0 then
  raise exception 'Unexpected research context version; refusing unknown rewrite';
 end if;
 execute replace(definition,'o.verification_policy,o.updated_at',
   'o.verification_policy,o.schedule_type,o.updated_at');
end $fix$;
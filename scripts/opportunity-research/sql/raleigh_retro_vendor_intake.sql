-- Add only the reviewed, live Raleigh Retro Gamers general vendor intake.
-- $0 applies to the application, not booth fees. The existing secret, identity,
-- freshness, manual-hold and fee checks are preserved for all other programs.
DO $patch$
DECLARE definition text; oldpiece text; newpiece text;
BEGIN
 select pg_get_functiondef('public.btb_research_publish_official_program(jsonb)'::regprocedure) into definition;
 if position('raleigh-retro-vendor-intake' in definition)>0 then
  definition:=replace(definition,'https://raleighretrogamers.com/vendor-application/','https://raleighretrogamers.com/vendors/');
  execute definition;return;end if;
 oldpiece:=$old0$  else null end;$old0$;newpiece:=$new0$  when 'raleigh-retro-vendor-intake' then jsonb_build_object(
    'slug','raleigh-retro-gamers-markets','name','Raleigh Retro Gamers Markets',
    'city','Raleigh','organizer','Raleigh Retro Gamers',
    'title','Raleigh Retro Gamers — Vendor Applications',
    'source','https://raleighretrogamers.com/vendors/',
    'app','https://raleighretrogamers.com/vendors/',
    'start',((date_trunc('year',now() at time zone 'America/New_York'))::date)::text,'end',((date_trunc('year',now() at time zone 'America/New_York')+interval '1 year'-interval '1 day')::date)::text,'schedule','rolling_market',
    'until',null,'description','Gaming, retro, vintage and pop-culture vendor markets across Raleigh and the Triangle. Venues and event eligibility vary.')
  else null end;$new0$;
 if position(oldpiece in definition)=0 then raise exception 'Unexpected official program guard 0';end if;
 definition:=replace(definition,oldpiece,newpiece);
 oldpiece:=$old1$('south-durham-guest-vendors','south-durham-winter-craft')$old1$;newpiece:=$new1$('south-durham-guest-vendors','south-durham-winter-craft','raleigh-retro-vendor-intake')$new1$;
 if position(oldpiece in definition)=0 then raise exception 'Unexpected official program guard 1';end if;
 definition:=replace(definition,oldpiece,newpiece);
 oldpiece:=$old2$  or c->'deposit' is distinct from 'null'::jsonb$old2$;newpiece:=$new2$  or (p='raleigh-retro-vendor-intake' and (
     c->>'availability' not in ('open','closed')
     or c->'booth_fee' is distinct from 'null'::jsonb
     or jsonb_typeof(c->'application_fee') is distinct from 'number'
     or (c->>'application_fee')::numeric is distinct from 0
     or c->'categories' is distinct from '[]'::jsonb
     or coalesce(p_result->>'form_hash','') !~ '^[a-f0-9]{64}$'
     or p_result->>'form_state' is distinct from
       case when c->>'availability'='closed' then 'submissions_closed' else 'public_questions_visible' end))
  or c->'deposit' is distinct from 'null'::jsonb$new2$;
 if position(oldpiece in definition)=0 then raise exception 'Unexpected official program guard 2';end if;
 definition:=replace(definition,oldpiece,newpiece);
 oldpiece:=$old3$or (p<>'state-raleigh-new-vendors' and expected->>'until' is null$old3$;newpiece:=$new3$or (p not in ('state-raleigh-new-vendors','raleigh-retro-vendor-intake') and expected->>'until' is null$new3$;
 if position(oldpiece in definition)=0 then raise exception 'Unexpected official program guard 3';end if;
 definition:=replace(definition,oldpiece,newpiece);
 if position('perform public.btb_research_authorize();' in definition)=0
 then raise exception 'Missing program authorization';end if;
 execute definition;
END $patch$;

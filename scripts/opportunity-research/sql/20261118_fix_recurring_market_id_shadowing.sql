-- Prevent PL/pgSQL variable/column ambiguity in ON CONFLICT(market_id,...).
-- Live publisher was returning HTTP 400 instead of publishing the verified waitlist.
do $fix$
declare definition text; original text;
begin
 select pg_get_functiondef('public.btb_research_publish_recurring(jsonb)'::regprocedure)
 into definition;
 if position('v_market_id uuid;' in definition)>0 then return;end if;
 original:=definition;
 if position('market_id uuid;' in definition)=0
    or position('values(market_id,season_start' in definition)=0
 then raise exception 'Unexpected recurring publisher version';end if;
 definition:=replace(definition,'market_id uuid;','v_market_id uuid;');
 definition:=replace(definition,'market_id:=m.id;','v_market_id:=m.id;');
 definition:=replace(definition,'values(market_id,season_start,season_end','values(v_market_id,season_start,season_end');
 definition:=replace(definition,'previous.market_id is distinct from market_id','previous.market_id is distinct from v_market_id');
 definition:=replace(definition,'values(c->>''title'',market_id,occurrence_id','values(c->>''title'',v_market_id,occurrence_id');
 definition:=replace(definition,'''market_id'',market_id,','''market_id'',v_market_id,');
 if definition=original then raise exception 'No changes applied';end if;
 execute definition;
end $fix$;

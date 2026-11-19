-- Require an independent official visitor-page receipt for the market
-- address and year-round schedule, in addition to vendor/market page hashes.
do $migration$
declare definition text; target text; replacement text;
begin
 select pg_get_functiondef('public.btb_research_publish_recurring(jsonb)'::regprocedure)
 into definition;
 target:='or coalesce(p_result->>''market_source_hash'','''') !~ ''^[a-f0-9]{64}$''';
 replacement:=target||E'\n   or coalesce(p_result->>''visit_source_hash'','''') !~ ''^[a-f0-9]{64}$''';
 if position(target in definition)=0 then
  raise exception 'Unexpected recurring publisher version';
 end if;
 if position('visit_source_hash' in definition)>0 then
  raise exception 'Visitor receipt already required';
 end if;
 execute replace(definition,target,replacement);
end $migration$;
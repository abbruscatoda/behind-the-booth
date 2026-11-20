-- Recheck previously automatically published multi-date listings without
-- duplicating, overriding a manual hold, or adopting an unverified application.
do $upgrade$
declare original text; revised text;
 oldgate text := $old$ if found then
   return jsonb_build_object('action','skipped','id',opportunity,'reason','Market date already published; existing listing not overwritten');
 end if;$old$;
 newgate text := $new$ if found then
   if exists(
    select 1 from public.vendor_opportunities
    where id=opportunity and market_id=mid and starts_on=event_day
      and ends_on=event_day
      and source_url=c->>'source_url'
      and application_url=c->>'application_url'
      and verification_policy='triangle-multidate-jotform-v1'
      and not automation_hold
      and publication='published'
   ) then
    update public.vendor_opportunities set
     availability='open',booth_fee=(c->>'booth_fee')::numeric,application_fee=10,
     fee_notes=c->>'fee_notes',eligibility=c->>'eligibility',
     research_notes=c->>'research_notes',verified_at=checked,
     last_checked_at=now(),updated_at=now(),review_state='verified',review_reason=''
    where id=opportunity;
    insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
    values(opportunity,'publish','Existing multi-date vendor application and date reverified',
     jsonb_build_object('source_hash',p_result->>'source_hash',
     'application_hash',p_result->>'application_hash','checked',checked));
    return jsonb_build_object('action','publish','id',opportunity,
      'reason','Previously published market date reverified with current official form');
   end if;
   return jsonb_build_object('action','skipped','id',opportunity,
     'reason','Market date already published or manually held');
 end if;$new$;
begin
 select pg_get_functiondef('public.btb_research_publish_multidate(jsonb)'::regprocedure) into original;
 if original is null or position(oldgate in original)=0 then
  raise exception 'Unexpected multi-date publisher version; no changes applied';
 end if;
 revised:=replace(original,oldgate,newgate);
 execute revised;
end $upgrade$;

-- Current production definitions: secure official vendor-program publication and
-- background-only monitoring of unverified discovery links.
-- A source link alone does not authorize publication. Application identity,
-- program period and fees are independently validated by worker-secret RPC.

CREATE OR REPLACE FUNCTION public.btb_research_publish_official_program(p_result jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
 p text:=p_result->>'program';
 c jsonb:=p_result->'candidate';
 expected jsonb;
 checked timestamptz;
 local_today date:=(now() at time zone 'America/New_York')::date;
 m public.markets;
 old public.vendor_opportunities;
 opp_id uuid;
 occ_id uuid;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false) then
  return jsonb_build_object('action','skipped','reason','Research disabled');
 end if;
 expected:=case p
  when 'wake-forest-2027-food' then jsonb_build_object(
    'slug','wake-forest-prcr-special-events','name','Wake Forest PRCR Special Events',
    'city','Wake Forest','organizer','Town of Wake Forest Parks, Recreation & Cultural Resources',
    'title','Wake Forest PRCR — 2027 Special Event Food Vendor Applications',
    'source','https://www.wakeforestnc.gov/parks-recreation-cultural-resources/prcr-food-vendors',
    'app','https://www.cognitoforms.com/TownOfWakeForestPRCR1/_2027TownOfWakeForestParksRecreationCulturalResourcesSpecialEventFoodVendingOpportun',
    'start','2027-01-01','end','2027-12-31','schedule','seasonal_application',
    'until','2026-11-27','description','Wake Forest Parks, Recreation & Cultural Resources runs community events throughout the year, including festivals, concerts and special event food-vendor programs.')
  when 'durham-food-vendor-program' then jsonb_build_object(
    'slug','durham-prcr-special-events','name','Durham Parks & Recreation Special Events',
    'city','Durham','organizer','Durham Parks & Recreation',
    'title','Durham Parks & Recreation — Food Vendor Applications',
    'source','https://www.dprplaymore.org/331/Vendor-Performer-Information',
    'app','https://www.dprplaymore.org/FormCenter/Vendor-Registration-8/Food-Vendor-Application-50',
    'start','2026-01-01','end','2027-12-31','schedule','rolling_market',
    'until',null,'description','Durham Parks & Recreation operates seasonal festivals and public events across Durham and invites eligible food-vendor applications for current opportunities.')
  when 'state-raleigh-new-vendors' then jsonb_build_object(
    'slug','state-farmers-market','name','State Farmers Market',
    'city','Raleigh','organizer','North Carolina Department of Agriculture & Consumer Services',
    'title','State Farmers Market — New Vendor Applications',
    'source','https://www.ncagr.gov/divisions/marketing/farmers-markets-agricultural-centers/state-farmers-market-raleigh/vendor-information',
    'app','https://www.ncagr.gov/media/5343/download?attachment=',
    'start','2026-01-01','end','2027-12-31','schedule','rolling_market',
    'until',null,'description','Year-round State Farmers Market serving Raleigh vendors and shoppers.')
  when 'south-durham-winter-craft' then jsonb_build_object(
    'slug','south-durham-farmers-market','name','South Durham Farmers Market',
    'city','Durham','organizer','South Durham Farmers Market',
    'title','South Durham Farmers Market — Winter Craft Applications',
    'source','https://southdurhamfarmersmarket.com/become-a-vendor',
    'app','https://docs.google.com/forms/d/e/1FAIpQLSeXV0kAKDUDK3e44KLfoV9pXMd94CjlS1Up5y2TkwUOQ1D__g/viewform',
    'start','2026-11-01','end','2026-12-31','schedule','seasonal_application',
    'until','2026-12-31','description','Year-round producer farmers market in Durham with seasonal guest and craft vending.')
  when 'south-durham-guest-vendors' then jsonb_build_object(
    'slug','south-durham-farmers-market','name','South Durham Farmers Market',
    'city','Durham','organizer','South Durham Farmers Market',
    'title','South Durham Farmers Market — Guest Vendor Applications',
    'source','https://southdurhamfarmersmarket.com/become-a-vendor',
    'app','https://docs.google.com/forms/d/e/1FAIpQLSc4n-7Ht3GntUJpGP0HaGPmUvYA3XMbnnqxy8VePtlAm2Uv-g/viewform',
    'start','2026-01-01','end','2027-12-31','schedule','rolling_market',
    'until',null,'description','Year-round producer farmers market in Durham with seasonal guest and craft vending.')
  else null end;
 if expected is null
    or octet_length(p_result::text)>15000
    or p_result->>'policy' is distinct from 'official-vendor-program-v1'
    or p_result->>'decision' is distinct from 'publish'
    or jsonb_typeof(c) is distinct from 'object'
    or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
    or length(coalesce(p_result->>'evidence','')) not between 120 and 800
 then raise exception 'Unapproved official vendor program receipt' using errcode='22023';end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 if checked is null or not isfinite(checked)
  or checked<now()-interval '6 hours' or checked>now()+interval '5 minutes'
  or c->>'source_url' is distinct from expected->>'source'
  or c->>'application_url' is distinct from expected->>'app'
  or c->>'market_slug' is distinct from expected->>'slug'
  or c->>'market_name' is distinct from expected->>'name'
  or c->>'organizer' is distinct from expected->>'organizer'
  or c->>'city' is distinct from expected->>'city'
  or c->>'state' is distinct from 'NC'
  or c->>'title' is distinct from expected->>'title'
  or c->>'starts_on' is distinct from expected->>'start'
  or c->>'ends_on' is distinct from expected->>'end'
  or c->>'schedule_type' is distinct from expected->>'schedule'
  or c->>'deadline' is not null
  or c->'booth_fee' is distinct from 'null'::jsonb
  or c->'application_fee' is distinct from 'null'::jsonb
  or c->'deposit' is distinct from 'null'::jsonb
  or jsonb_typeof(c->'categories') is distinct from 'array'
  or jsonb_array_length(c->'categories')>2
  or length(coalesce(c->>'venue','')) not between 5 and 180
  or length(coalesce(c->>'eligibility','')) not between 100 and 2000
  or length(coalesce(c->>'fee_notes','')) not between 90 and 2000
  or length(coalesce(c->>'research_notes','')) not between 110 and 2500
  or c->>'availability' not in ('open','limited','closed')
 then raise exception 'Official program identity or facts changed' using errcode='22023';end if;
 if (p='state-raleigh-new-vendors' and c->>'availability' is distinct from 'limited')
   or (p<>'state-raleigh-new-vendors' and expected->>'until' is not null and
     c->>'availability' is distinct from
       case when local_today>(expected->>'until')::date then 'closed' else 'open' end)
   or (p<>'state-raleigh-new-vendors' and expected->>'until' is null
      and c->>'availability' is distinct from 'open')
 then raise exception 'Application availability not consistent with official open dates' using errcode='22023';end if;
 perform pg_advisory_xact_lock(hashtextextended('official-program:'||p,9));
 select * into m from public.markets where slug=expected->>'slug' for update;
 if not found then
   if p not in ('wake-forest-2027-food','durham-food-vendor-program') then
     return jsonb_build_object('action','skipped','reason','Existing market profile not found');
   end if;
   insert into public.markets(slug,name,city,state,organizer,description,website_url)
   values(expected->>'slug',expected->>'name',expected->>'city','NC',
          expected->>'organizer',expected->>'description',expected->>'source')
   on conflict(slug) do nothing;
   select * into m from public.markets where slug=expected->>'slug' for update;
 end if;
 if m.id is null or m.is_hidden or m.is_sample or m.city is distinct from expected->>'city'
    or m.name is distinct from expected->>'name' or m.state is distinct from 'NC'
 then return jsonb_build_object('action','skipped','reason','Market identity or visibility conflict');end if;
 select * into old from public.vendor_opportunities
 where application_url=expected->>'app' and starts_on=(expected->>'start')::date
 for update;
 if found and (old.market_id is distinct from m.id or old.automation_hold
   or old.publication is distinct from 'published'
   or old.verification_policy is distinct from 'official-vendor-program-v1'
   or old.source_url is distinct from expected->>'source')
 then return jsonb_build_object('action','skipped','reason','Existing application listing is protected');end if;
 insert into public.market_occurrences(market_id,starts_on,ends_on,title)
 values(m.id,(expected->>'start')::date,(expected->>'end')::date,expected->>'title')
 on conflict(market_id,starts_on,ends_on) do nothing;
 select id into occ_id from public.market_occurrences
 where market_id=m.id and starts_on=(expected->>'start')::date and ends_on=(expected->>'end')::date;
 if occ_id is null then raise exception 'Program occurrence could not be stored';end if;
 if old.id is null then
   insert into public.vendor_opportunities(
    title,market_id,occurrence_id,organizer,city,state,venue,starts_on,ends_on,deadline,
    application_url,source_url,categories,availability,booth_fee,application_fee,
    deposit,fee_notes,eligibility,research_notes,publication,verified_at,last_checked_at,
    review_state,review_reason,verification_policy,schedule_type)
   values(expected->>'title',m.id,occ_id,expected->>'organizer',m.city,'NC',
    c->>'venue',(expected->>'start')::date,(expected->>'end')::date,null,
    expected->>'app',expected->>'source','{}'::text[],c->>'availability',null,null,null,
    c->>'fee_notes',c->>'eligibility',c->>'research_notes','published',checked,now(),
    case when c->>'availability'='closed' then 'closed' else 'verified' end,
    '', 'official-vendor-program-v1',expected->>'schedule')
   returning id into opp_id;
 else
   opp_id:=old.id;
   update public.vendor_opportunities set
    availability=c->>'availability',
    review_state=case when c->>'availability'='closed' then 'closed' else 'verified' end,
    review_reason='',
    fee_notes=case when old.booth_fee is null and old.application_fee is null then c->>'fee_notes' else old.fee_notes end,
    eligibility=c->>'eligibility',research_notes=c->>'research_notes',
    verified_at=checked,last_checked_at=now(),updated_at=now()
   where id=opp_id;
 end if;
 update btb_private.triangle_discovery_leads set
   review_state='resolved',published_opportunity_id=opp_id,resolved_at=now(),
   research_status=case when p='state-raleigh-new-vendors' then 'confirmed_rolling'
     when p='durham-food-vendor-program' then 'confirmed_rolling' else 'confirmed_seasonal' end,
   research_reason='Official program vendor application verified and published automatically.'
 where target_url=expected->>'app' and review_state in ('new','monitoring');
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(opp_id,'publish','Official source-linked vendor application verified for named program',
  jsonb_build_object('policy',p_result->>'policy','program',p,
    'source_hash',p_result->>'source_hash','checked_at',checked));
 return jsonb_build_object('action','publish','id',opp_id,'program',p);
end $function$
;
REVOKE ALL ON FUNCTION public.btb_research_publish_official_program(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.btb_research_publish_official_program(jsonb) TO anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION public.btb_research_diagnose_leads(p_diagnostics jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare e jsonb;n int:=0;s text;reason_text text; target text;src text; next_state text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('updated',0,'paused',true);end if;
 if jsonb_typeof(p_diagnostics) is distinct from 'array'
  or jsonb_array_length(p_diagnostics)>80
  or octet_length(p_diagnostics::text)>80000
 then raise exception 'Invalid lead diagnostic batch' using errcode='22023';end if;
 for e in select value from jsonb_array_elements(p_diagnostics) loop
  s:=e->>'status';reason_text:=coalesce(e->>'reason','');
  target:=coalesce(e->>'target_url','');src:=coalesce(e->>'source_url','');
  if s not in ('confirmed_seasonal','confirmed_rolling','restricted','closed','multi_date','form_gated',
    'missing_event','source_unavailable','unlinked','not_application','needs_evidence','application_directory','event_only')
   or length(reason_text) not between 12 and 400
   or length(target)>1200 or length(src)>1200
  then continue;end if;
  -- Monitor temporary closed and invite-only applications; re-activate them
  -- if a later source check finds an eligible state.
  next_state:=case
   when s='confirmed_rolling' and exists(
     select 1 from public.vendor_opportunities o
     where o.publication='published' and o.schedule_type='rolling_market'
      and lower(trim(o.organizer))=lower(trim((
       select organizer from btb_private.triangle_discovery_leads
       where target_url=target and source_url=src limit 1)))
      and lower(trim(o.city))=lower(trim((
       select city from btb_private.triangle_discovery_leads
       where target_url=target and source_url=src limit 1)))
      and split_part(o.source_url,'/',3)=split_part(src,'/',3)
   ) then 'monitoring'
   when s in ('closed','restricted','application_directory','unlinked','event_only','confirmed_seasonal','multi_date','form_gated','missing_event','needs_evidence','source_unavailable') then 'monitoring'
   when s='not_application'
       and reason_text like 'Not a vendor market:%' then 'ignored'
   when s='not_application'
       and (rtrim(target,'/#')=rtrim(src,'/#') or right(target,2)='/#')
       then 'resolved'
   when s='not_application' then 'ignored'
   else 'monitoring' end;
  update btb_private.triangle_discovery_leads set
   research_status=s,research_reason=reason_text,last_researched_at=now(),
   review_state=case when next_state is null then review_state else next_state end,
   resolved_at=case when next_state='resolved' then now() else resolved_at end
  where target_url=target and source_url=src
   and review_state in ('new','monitoring');
  if found then n:=n+1;end if;
 end loop;
 return jsonb_build_object('updated',n);
end $function$
;
CREATE OR REPLACE FUNCTION public.btb_research_record_discovery_leads_v2(p_leads jsonb, p_sources jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
 entry jsonb; saved integer:=0; skipped integer:=0; cardinality_conflicts integer:=0;
 url text; source text; org text; town text; claimed_host text; stage text:='start';
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('saved',0,'skipped',0,'paused',true);end if;
 if jsonb_typeof(p_sources) is distinct from 'array'
  or jsonb_array_length(p_sources) not between 1 and 75
  or octet_length(p_sources::text)>70000
  or jsonb_typeof(p_leads) is distinct from 'array'
  or jsonb_array_length(p_leads)>80
  or octet_length(p_leads::text)>100000
 then raise exception 'Invalid curated source or lead batch' using errcode='22023';end if;
 -- Transactional registry update; invalid inputs roll the whole operation back.
 perform set_config('btb.discovery_bulk_ingest','on',true);
 stage:='registry_reset';
 for source in select r.source_url from btb_private.triangle_research_sources r order by r.source_url loop
  update btb_private.triangle_research_sources r set active=false where r.source_url=source;
 end loop;
 for entry in select value from jsonb_array_elements(p_sources) loop
  source:=entry->>'source_url';
  org:=entry->>'organizer';
  town:=entry->>'city';
  claimed_host:=split_part(coalesce(source,''),'/',3);
  if source is null or length(source)>1200
    or source !~ '^https://[A-Za-z0-9.-]+(/[^[:space:]<>@?#]*)?$'
    or claimed_host !~ '^[A-Za-z0-9][A-Za-z0-9.-]{3,240}[.](com|org|net|gov|edu)$'
    or claimed_host ~* '(^|[.])(localhost|local|internal)$'
    or length(coalesce(org,'')) not between 2 and 120
    or length(coalesce(town,'')) not between 3 and 80
  then raise exception 'Invalid code-defined official source' using errcode='22023';end if;
  stage:='source_upsert';
  insert into btb_private.triangle_research_sources(source_url,organizer,city,active)
  values(source,org,town,true)
  on conflict(source_url) do update set
   organizer=excluded.organizer,city=excluded.city,active=true,updated_at=now();
 end loop;
 for entry in select value from jsonb_array_elements(p_leads) loop
  url:=entry->>'target_url'; source:=entry->>'source_url';
  org:=entry->>'organizer';town:=entry->>'city';
  if url is null or length(url)>1200
    or url !~ '^https://[A-Za-z0-9.-]+(/[^[:space:]<>@]*)?([?][^[:space:]<>@]*)?$'
    or url ~* '^https://(localhost|127[.]|10[.]|192[.]168[.]|169[.]254[.]|172[.](1[6-9]|2[0-9]|3[01])[.])'
    or source is null
    or not exists(
      select 1 from btb_private.triangle_research_sources s
      where s.source_url=source and s.active and s.organizer=org and s.city=town)
    or length(coalesce(entry->>'title','')) not between 3 and 160
  then skipped:=skipped+1;continue;end if;
  begin
   stage:='lead_upsert';
   insert into btb_private.triangle_discovery_leads(
    target_url,source_url,title,organizer,city,notes,review_state)
   values(url,source,entry->>'title',org,town,left(coalesce(entry->>'notes',''),500),'monitoring')
   on conflict(target_url) do update set
    last_seen=now(),source_url=excluded.source_url
   where btb_private.triangle_discovery_leads.organizer=excluded.organizer
     and btb_private.triangle_discovery_leads.city=excluded.city;
   if found then saved:=saved+1;
   else skipped:=skipped+1;end if;
  exception when cardinality_violation then
   -- Skip only this URL, keep all other independent verified leads.
   -- Record the failure category without exposing source content.
   cardinality_conflicts:=cardinality_conflicts+1;
   skipped:=skipped+1;
  end;
 end loop;
 perform set_config('btb.discovery_bulk_ingest','off',true);
 -- Final reconciliation occurs in a second authenticated RPC after commit.
 stage:='return_summary';
 return jsonb_build_object('saved',saved,'skipped',skipped,
  'cardinality_conflicts',cardinality_conflicts,
  'approved_sources',(select count(*) from btb_private.triangle_research_sources where active));
exception when cardinality_violation then
 return jsonb_build_object('failed',true,'sqlstate','21000','stage',stage,'saved',0,'skipped',0);
end $function$
;

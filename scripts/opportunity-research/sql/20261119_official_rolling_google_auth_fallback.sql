-- Reusable, tightly scoped seasonal/rolling market publisher. Every new
-- provider must be explicitly allowlisted here and in seasonal_research.py.
-- The worker secret authorizes changes; the payload is still independently
-- checked against policy, exact official URLs, schedule, identity and holds.
alter table public.vendor_opportunities drop constraint if exists vendor_opportunities_schedule_type_check;
alter table public.vendor_opportunities add constraint vendor_opportunities_schedule_type_check
 check (schedule_type in ('dated_event','recurring_season','seasonal_application','rolling_market'));

create or replace function public.btb_research_publish_seasonal(p_result jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 c jsonb:=p_result->'candidate';
 v_checked timestamptz;
 v_start date;v_end date;v_year int;
 v_slug text;v_name text;v_organizer text;v_city text;
 v_app text;v_src text;v_market_url text;v_schedule text;
 v_market public.markets;
 v_previous public.vendor_opportunities;
 v_market_id uuid;v_occurrence_id uuid;v_opportunity_id uuid;
 v_action text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false) then
  return jsonb_build_object('action','skipped','reason','Research disabled');
 end if;
 if octet_length(p_result::text)>20000
   or p_result->>'policy' is distinct from 'seasonal-official-v1'
   or p_result->>'decision' is distinct from 'publish'
   or jsonb_typeof(c) is distinct from 'object'
   or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
   or coalesce(p_result->>'market_source_hash','') !~ '^[a-f0-9]{64}$'
   or length(coalesce(p_result->>'evidence','')) not between 60 and 600
 then raise exception 'Missing complete, fresh seasonal research receipt' using errcode='22023';end if;
 v_checked:=nullif(p_result->>'checked_at','')::timestamptz;
 v_start:=nullif(c->>'starts_on','')::date;
 v_end:=nullif(c->>'ends_on','')::date;
 v_slug:=c->>'market_slug';v_name:=c->>'market_name';v_organizer:=c->>'organizer';
 v_city:=c->>'city';v_app:=c->>'application_url';v_src:=c->>'source_url';
 v_market_url:=c->>'market_url';v_schedule:=c->>'schedule_type';
 if v_checked is null or not isfinite(v_checked)
  or v_checked<now()-interval '6 hours' or v_checked>now()+interval '5 minutes'
  or v_start is null or v_end is null or v_end<v_start
  or (v_end < (now() at time zone 'America/New_York')::date)
  or v_end>current_date+interval '30 months'
  or length(coalesce(c->>'title','')) not between 10 and 160
  or length(coalesce(c->>'fee_notes','')) not between 30 and 2000
  or length(coalesce(c->>'eligibility','')) not between 30 and 2000
  or length(coalesce(c->>'research_notes','')) not between 40 and 4000
  or length(coalesce(c->>'venue','')) not between 5 and 300
  or c->>'state' is distinct from 'NC'
  or c->>'availability' is distinct from 'open'
  or c->>'deadline' is not null
  or c->>'booth_fee' is not null
  or c->>'application_fee' is not null
  or c->>'deposit' is not null
  or c->'categories' is distinct from '[]'::jsonb
 then raise exception 'Invalid seasonal publication facts or missing verified fields' using errcode='22023';end if;

 -- Never conflate officially advertised applications with a readable form.
 -- Only Western Wake's specifically approved rolling source may use the
 -- HTTP-auth-blocked evidence path. All other providers need a live form.
 if (p_result->'form_complete' is distinct from 'true'::jsonb
     or p_result->'form_readable' is distinct from 'true'::jsonb
     or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}
  if v_name is distinct from 'Fuquay-Varina Growers Market'
    or v_organizer is distinct from v_name
    or v_city is distinct from 'Fuquay-Varina'
    or v_market_url is distinct from 'https://www.fvgrowersmarket.com/'
    or v_src is distinct from 'https://www.fvgrowersmarket.com/vendor-application'
    or coalesce(v_app,'') !~ '^https://form[.]jotform[.]com/[0-9]{10,20}$'
    or v_schedule is distinct from 'seasonal_application'
    or extract(year from v_start)<>extract(year from v_end)
    or extract(month from v_start) not between 3 and 5
    or extract(month from v_end) not between 8 and 10
    or v_end>v_start+interval '210 days'
    or coalesce(c->>'venue','') !~ '121 N[.] Main St'
    or coalesce(c->>'title','') !~ ('[[:space:]]'||extract(year from v_start)::int||'[[:space:]]Vendor Applications$')
  then raise exception 'Fuquay-Varina seasonal facts did not match the approved organizer' using errcode='22023';end if;
 elsif v_slug='western-wake-farmers-market' then
  if v_name is distinct from 'Western Wake Farmers Market'
    or v_organizer is distinct from v_name
    or v_city is distinct from 'Morrisville'
    or v_market_url is distinct from 'https://westernwakefarmersmarket.org/'
    or v_src is distinct from 'https://westernwakefarmersmarket.org/apply'
    or coalesce(v_app,'') !~ '^https://forms[.]gle/[A-Za-z0-9_-]{6,60}$'
    or v_schedule is distinct from 'rolling_market'
    or v_start<>make_date(extract(year from v_start)::int,1,1)
    or v_end<>make_date(extract(year from v_start)::int+1,12,31)
    or coalesce(c->>'venue','') is distinct from '101 Town Hall Drive'
    or c->>'title' is distinct from 'Western Wake Farmers Market — Rolling Vendor Applications'
  then raise exception 'Western Wake rolling application facts did not match the approved organizer' using errcode='22023';end if;
 else
  raise exception 'Seasonal organizer is not independently approved' using errcode='22023';
 end if;

 perform pg_advisory_xact_lock(hashtextextended(v_slug||':'||v_app,2));
 select * into v_market from public.markets where slug=v_slug for update;
 if not found then
  -- New profile only for an explicit organizer identity and official source.
  if exists(select 1 from public.markets
            where lower(name)=lower(v_name) and lower(city)=lower(v_city))
  then return jsonb_build_object('action','skipped','reason','Another profile matches the market identity');end if;
  insert into public.markets(name,slug,city,state,description,website_url,organizer,is_sample)
   values(v_name,v_slug,v_city,'NC',left(v_name||
    ' is an officially documented recurring farmers market. See the organizer for individual market dates and application eligibility.',500),
    v_market_url,v_organizer,false) returning * into v_market;
 end if;
 if v_market.is_hidden or v_market.is_sample or v_market.name is distinct from v_name
    or v_market.city is distinct from v_city or v_market.organizer is distinct from v_organizer
    or v_market.state is distinct from 'NC'
 then return jsonb_build_object('action','skipped','reason','Market identity conflicts or is hidden');end if;
 v_market_id:=v_market.id;

 select * into v_previous from public.vendor_opportunities
 where application_url=v_app and starts_on=v_start for update;
 if found then
  if v_previous.automation_hold or v_previous.publication='archived'
    or v_previous.market_id is distinct from v_market_id
    or v_previous.verification_policy is distinct from 'seasonal-official-v1'
    or v_previous.source_url is distinct from v_src
    or v_previous.schedule_type is distinct from v_schedule
  then return jsonb_build_object('action','skipped','reason','Manually held or incompatible existing opportunity');end if;
  v_opportunity_id:=v_previous.id;
 else
  -- Avoid presenting two overlapping rolling listings as independently open.
  if v_schedule='rolling_market' and exists(
    select 1 from public.vendor_opportunities where market_id=v_market_id
      and publication='published' and schedule_type='rolling_market'
      and ends_on >= (now() at time zone 'America/New_York')::date
  ) then return jsonb_build_object('action','skipped','reason','An existing ongoing listing is still active');end if;
 end if;
 insert into public.market_occurrences(market_id,starts_on,ends_on,title)
 values(v_market_id,v_start,v_end,c->>'title')
 on conflict(market_id,starts_on,ends_on) do update set title=excluded.title
 returning id into v_occurrence_id;
 if v_opportunity_id is null then
  insert into public.vendor_opportunities(
   title,market_id,occurrence_id,organizer,city,state,venue,starts_on,ends_on,
   deadline,application_url,source_url,categories,availability,booth_fee,application_fee,
   deposit,fee_notes,eligibility,research_notes,publication,verified_at,
   last_checked_at,review_state,review_reason,verification_policy,schedule_type)
  values(c->>'title',v_market_id,v_occurrence_id,v_organizer,v_city,'NC',
    c->>'venue',v_start,v_end,null,v_app,v_src,'{}'::text[],'open',
    null,null,null,c->>'fee_notes',c->>'eligibility',c->>'research_notes',
    'published',v_checked,now(),'verified','','seasonal-official-v1',v_schedule)
  returning id into v_opportunity_id;
 else
  update public.vendor_opportunities set
   title=c->>'title',venue=c->>'venue',ends_on=v_end,occurrence_id=v_occurrence_id,
   availability='open',deadline=null,fee_notes=c->>'fee_notes',
   eligibility=c->>'eligibility',research_notes=c->>'research_notes',
   verified_at=v_checked,last_checked_at=now(),review_state='verified',
   review_reason='',updated_at=now() where id=v_opportunity_id;
 end if;
 update btb_private.triangle_discovery_leads set review_state='resolved',last_seen=now()
 where review_state='new' and source_url=v_market_url
   and target_url in (v_src,v_app);
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(v_opportunity_id,'publish',
 case when p_result->>'application_access'='http_auth_blocked'
   then 'Official organizer independently advertised rolling applications; Google form was inaccessible to automation. Form submission not verified.'
   else 'Linked official recurring-market sources and public vendor application verified; individual dates and booths are not guaranteed.' end,
 jsonb_build_object('policy','seasonal-official-v1',
 'source',v_src,'application',v_app,'checked_at',v_checked,
 'source_hash',p_result->>'source_hash',
 'market_hash',p_result->>'market_source_hash',
 'form_hash',p_result->>'application_hash',
 'application_access',p_result->>'application_access'));
 return jsonb_build_object('action','publish','id',v_opportunity_id,
 'market_id',v_market_id,'reason','Verified seasonal or rolling market application published');
end $$;

revoke all on function public.btb_research_publish_seasonal(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_publish_seasonal(jsonb) to anon,authenticated,service_role;
)
   and not (
      v_slug='western-wake-farmers-market'
      and v_schedule='rolling_market'
      and p_result->>'application_access'='http_auth_blocked'
      and p_result->'form_complete'='false'::jsonb
      and p_result->'form_readable'='false'::jsonb
      and p_result->>'application_hash' is null
      and length(coalesce(p_result->>'evidence','')) between 120 and 600
      and c->>'research_notes' like '%blocked automated verification%'
   )
 then raise exception 'Unverified application without eligible official-source evidence' using errcode='22023';end if;

 if v_slug='fuquay-varina-growers-market' then
  if v_name is distinct from 'Fuquay-Varina Growers Market'
    or v_organizer is distinct from v_name
    or v_city is distinct from 'Fuquay-Varina'
    or v_market_url is distinct from 'https://www.fvgrowersmarket.com/'
    or v_src is distinct from 'https://www.fvgrowersmarket.com/vendor-application'
    or coalesce(v_app,'') !~ '^https://form[.]jotform[.]com/[0-9]{10,20}$'
    or v_schedule is distinct from 'seasonal_application'
    or extract(year from v_start)<>extract(year from v_end)
    or extract(month from v_start) not between 3 and 5
    or extract(month from v_end) not between 8 and 10
    or v_end>v_start+interval '210 days'
    or coalesce(c->>'venue','') !~ '121 N[.] Main St'
    or coalesce(c->>'title','') !~ ('[[:space:]]'||extract(year from v_start)::int||'[[:space:]]Vendor Applications$')
  then raise exception 'Fuquay-Varina seasonal facts did not match the approved organizer' using errcode='22023';end if;
 elsif v_slug='western-wake-farmers-market' then
  if v_name is distinct from 'Western Wake Farmers Market'
    or v_organizer is distinct from v_name
    or v_city is distinct from 'Morrisville'
    or v_market_url is distinct from 'https://westernwakefarmersmarket.org/'
    or v_src is distinct from 'https://westernwakefarmersmarket.org/apply'
    or coalesce(v_app,'') !~ '^https://forms[.]gle/[A-Za-z0-9_-]{6,60}$'
    or v_schedule is distinct from 'rolling_market'
    or v_start<>make_date(extract(year from v_start)::int,1,1)
    or v_end<>make_date(extract(year from v_start)::int+1,12,31)
    or coalesce(c->>'venue','') is distinct from '101 Town Hall Drive'
    or c->>'title' is distinct from 'Western Wake Farmers Market — Rolling Vendor Applications'
  then raise exception 'Western Wake rolling application facts did not match the approved organizer' using errcode='22023';end if;
 else
  raise exception 'Seasonal organizer is not independently approved' using errcode='22023';
 end if;

 perform pg_advisory_xact_lock(hashtextextended(v_slug||':'||v_app,2));
 select * into v_market from public.markets where slug=v_slug for update;
 if not found then
  -- New profile only for an explicit organizer identity and official source.
  if exists(select 1 from public.markets
            where lower(name)=lower(v_name) and lower(city)=lower(v_city))
  then return jsonb_build_object('action','skipped','reason','Another profile matches the market identity');end if;
  insert into public.markets(name,slug,city,state,description,website_url,organizer,is_sample)
   values(v_name,v_slug,v_city,'NC',left(v_name||
    ' is an officially documented recurring farmers market. See the organizer for individual market dates and application eligibility.',500),
    v_market_url,v_organizer,false) returning * into v_market;
 end if;
 if v_market.is_hidden or v_market.is_sample or v_market.name is distinct from v_name
    or v_market.city is distinct from v_city or v_market.organizer is distinct from v_organizer
    or v_market.state is distinct from 'NC'
 then return jsonb_build_object('action','skipped','reason','Market identity conflicts or is hidden');end if;
 v_market_id:=v_market.id;

 select * into v_previous from public.vendor_opportunities
 where application_url=v_app and starts_on=v_start for update;
 if found then
  if v_previous.automation_hold or v_previous.publication='archived'
    or v_previous.market_id is distinct from v_market_id
    or v_previous.verification_policy is distinct from 'seasonal-official-v1'
    or v_previous.source_url is distinct from v_src
    or v_previous.schedule_type is distinct from v_schedule
  then return jsonb_build_object('action','skipped','reason','Manually held or incompatible existing opportunity');end if;
  v_opportunity_id:=v_previous.id;
 else
  -- Avoid presenting two overlapping rolling listings as independently open.
  if v_schedule='rolling_market' and exists(
    select 1 from public.vendor_opportunities where market_id=v_market_id
      and publication='published' and schedule_type='rolling_market'
      and ends_on >= (now() at time zone 'America/New_York')::date
  ) then return jsonb_build_object('action','skipped','reason','An existing ongoing listing is still active');end if;
 end if;
 insert into public.market_occurrences(market_id,starts_on,ends_on,title)
 values(v_market_id,v_start,v_end,c->>'title')
 on conflict(market_id,starts_on,ends_on) do update set title=excluded.title
 returning id into v_occurrence_id;
 if v_opportunity_id is null then
  insert into public.vendor_opportunities(
   title,market_id,occurrence_id,organizer,city,state,venue,starts_on,ends_on,
   deadline,application_url,source_url,categories,availability,booth_fee,application_fee,
   deposit,fee_notes,eligibility,research_notes,publication,verified_at,
   last_checked_at,review_state,review_reason,verification_policy,schedule_type)
  values(c->>'title',v_market_id,v_occurrence_id,v_organizer,v_city,'NC',
    c->>'venue',v_start,v_end,null,v_app,v_src,'{}'::text[],'open',
    null,null,null,c->>'fee_notes',c->>'eligibility',c->>'research_notes',
    'published',v_checked,now(),'verified','','seasonal-official-v1',v_schedule)
  returning id into v_opportunity_id;
 else
  update public.vendor_opportunities set
   title=c->>'title',venue=c->>'venue',ends_on=v_end,occurrence_id=v_occurrence_id,
   availability='open',deadline=null,fee_notes=c->>'fee_notes',
   eligibility=c->>'eligibility',research_notes=c->>'research_notes',
   verified_at=v_checked,last_checked_at=now(),review_state='verified',
   review_reason='',updated_at=now() where id=v_opportunity_id;
 end if;
 update btb_private.triangle_discovery_leads set review_state='resolved',last_seen=now()
 where review_state='new' and source_url=v_market_url
   and target_url in (v_src,v_app);
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(v_opportunity_id,'publish',
 'Linked official recurring-market sources and public vendor application verified; individual dates and booths are not guaranteed.',
 jsonb_build_object('policy','seasonal-official-v1',
 'source',v_src,'application',v_app,'checked_at',v_checked,
 'source_hash',p_result->>'source_hash',
 'market_hash',p_result->>'market_source_hash',
 'form_hash',p_result->>'application_hash'));
 return jsonb_build_object('action','publish','id',v_opportunity_id,
 'market_id',v_market_id,'reason','Verified seasonal or rolling market application published');
end $$;

revoke all on function public.btb_research_publish_seasonal(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_publish_seasonal(jsonb) to anon,authenticated,service_role;

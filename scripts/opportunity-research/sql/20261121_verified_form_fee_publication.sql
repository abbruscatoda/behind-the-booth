-- Guarded public-form fee publishers, exported from the verified live DB.
-- Fees are only accepted when independently labeled on an organizer-linked
-- readable application form, with matching fee evidence and fresh source hashes.
-- Other fees remain unknown, not free. Previously verified amounts are not
-- erased merely because a subsequent form read is blocked.
-- The worker-secret authorization and empty search_path are preserved.

CREATE OR REPLACE FUNCTION public.btb_research_publish_seasonal(p_result jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
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

  or c->>'deposit' is not null
  or c->'categories' is distinct from '[]'::jsonb

 then raise exception 'Invalid seasonal publication facts or missing verified fields' using errcode='22023';end if;
 -- Numeric fees are allowed only when the worker actually read the Wake
 -- Forest organizer-linked public form and extracted fee-labeled amounts.
 if c->>'booth_fee' is not null or c->>'application_fee' is not null then
  if v_slug is distinct from 'wake-forest-farmers-market'
    or p_result->>'application_access' is distinct from 'readable_first_page'
    or p_result->'form_readable' is distinct from 'true'::jsonb
    or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$'
    or c->'booth_fee' is distinct from p_result->'form_fee_evidence'->'booth_fee'
    or c->'application_fee' is distinct from p_result->'form_fee_evidence'->'application_fee'
  then raise exception 'Fee values must be independently verified from the official public form' using errcode='22023';end if;
  if (c->>'booth_fee' is not null and c->>'booth_fee' !~ '^[0-9]{1,5}([.][0-9]{1,2})?$')
    or (c->>'application_fee' is not null and c->>'application_fee' !~ '^[0-9]{1,5}([.][0-9]{1,2})?$')
  then raise exception 'Invalid verified fee amounts' using errcode='22023';end if;
  if coalesce((c->>'booth_fee')::numeric,0)>10000
    or coalesce((c->>'application_fee')::numeric,0)>10000
    or coalesce((c->>'booth_fee')::numeric,1)<=0
    or coalesce((c->>'application_fee')::numeric,1)<=0
  then raise exception 'Verified fee outside permitted range' using errcode='22023';end if;
 end if;


 -- The regular Google application is sometimes HTTP-auth-blocked for bots.
 -- For the named recurring market ONLY, two official pages must independently
 -- assert rolling intake and contain an exact regular-vendor application link.
 if (p_result->'form_complete' is distinct from 'true'::jsonb
     or p_result->'form_readable' is distinct from 'true'::jsonb
     or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$')
   and not ((
      v_slug='western-wake-farmers-market'
      and v_schedule='rolling_market'
      and p_result->>'application_access'='http_auth_blocked'
      and p_result->'form_complete'='false'::jsonb
      and p_result->'form_readable'='false'::jsonb
      and p_result->>'application_hash' is null
      and length(coalesce(p_result->>'evidence','')) between 120 and 600
      and c->>'research_notes' like '%blocked automated verification%'
   ) OR (
      v_slug='wake-forest-farmers-market'
      and v_schedule='rolling_market'
      and p_result->>'application_access' in ('http_auth_blocked','readable_first_page')
      and p_result->'form_complete'='false'::jsonb
      and (
       (p_result->>'application_access'='http_auth_blocked'
        and p_result->'form_readable'='false'::jsonb
        and p_result->>'application_hash' is null)
       or
       (p_result->>'application_access'='readable_first_page'
        and p_result->'form_readable'='true'::jsonb
        and coalesce(p_result->>'application_hash','') ~ '^[a-f0-9]{64}$')
      )
      and length(coalesce(p_result->>'evidence','')) between 120 and 600
      and c->>'research_notes' like '%embedded regular-vendor application%'
   ))
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
 elsif v_slug='wake-forest-farmers-market' then
  if v_name is distinct from 'Wake Forest Farmers Market'
    or v_organizer is distinct from v_name
    or v_city is distinct from 'Wake Forest'
    or v_market_url is distinct from 'https://wakeforestmarket.org/vendors/become-a-vendor/'
    or v_src is distinct from 'https://wakeforestmarket.org/vendors/market-vendor-application/'
    or coalesce(v_app,'') !~ '^https://docs[.]google[.]com/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform$'
    or v_schedule is distinct from 'rolling_market'
    or v_start <> make_date(extract(year from (now() at time zone 'America/New_York'))::int,1,1)
    or v_end <> make_date(extract(year from v_start)::int+1,12,31)
    or c->>'title' is distinct from 'Wake Forest Farmers Market — Rolling Vendor Applications'
    or c->>'venue' is distinct from 'Wake Forest Farmers Market, Wake Forest, NC'
  then raise exception 'Wake Forest embedded year-round evidence does not match the approved market' using errcode='22023';end if;
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
    nullif(c->>'booth_fee','')::numeric,nullif(c->>'application_fee','')::numeric,null,c->>'fee_notes',c->>'eligibility',c->>'research_notes',
    'published',v_checked,now(),'verified','','seasonal-official-v1',v_schedule)
  returning id into v_opportunity_id;
 else
  update public.vendor_opportunities set
   title=c->>'title',venue=c->>'venue',ends_on=v_end,occurrence_id=v_occurrence_id,

   availability='open',deadline=null,
   booth_fee=coalesce(nullif(c->>'booth_fee','')::numeric,v_previous.booth_fee),
   application_fee=coalesce(nullif(c->>'application_fee','')::numeric,v_previous.application_fee),
   fee_notes=case when p_result->>'application_access'='http_auth_blocked'
       and (v_previous.booth_fee is not null or v_previous.application_fee is not null)
     then v_previous.fee_notes else c->>'fee_notes' end,

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
end $function$
;
revoke all on function public.btb_research_publish_seasonal(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_publish_seasonal(jsonb) to anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION public.btb_research_publish_verified_rolling(p_result jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
 c jsonb:=p_result->'candidate';
 checked timestamptz;
 start_day date;end_day date;
 m public.markets; old public.vendor_opportunities;
 occ uuid; target uuid;
 root_host text;src_host text;app_host text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('action','skipped','reason','Research disabled');end if;
 if octet_length(p_result::text)>16000
  or p_result->>'policy' is distinct from 'explore-rolling-official-v1'
  or p_result->>'decision' is distinct from 'publish'
  or jsonb_typeof(c) is distinct from 'object'
  or coalesce(p_result->>'market_source_hash','') !~ '^[a-f0-9]{64}$'
  or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
  or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$'
  or length(coalesce(p_result->>'evidence','')) not between 120 and 550
 then raise exception 'Unverified rolling-source receipt' using errcode='22023';end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 start_day:=nullif(c->>'starts_on','')::date;
 end_day:=nullif(c->>'ends_on','')::date;
 if checked is null or not isfinite(checked)
  or checked<now()-interval '6 hours' or checked>now()+interval '5 minutes'
  or start_day<>make_date(extract(year from (now() at time zone 'America/New_York'))::int,1,1)
  or end_day<>make_date(extract(year from start_day)::int+1,12,31)
  or length(coalesce(c->>'market_slug','')) not between 4 and 100
  or length(coalesce(c->>'title','')) not between 20 and 160
  or c->>'title' is distinct from (c->>'market_name')||' — Rolling Vendor Applications'
  or c->>'schedule_type' is distinct from 'rolling_market'
  or c->>'availability' is distinct from 'open'
  or c->>'deadline' is not null
  or c->>'state' is distinct from 'NC'

  or c->>'deposit' is not null or c->'categories' is distinct from '[]'::jsonb
  or length(coalesce(c->>'fee_notes','')) not between 80 and 2000
  or length(coalesce(c->>'eligibility','')) not between 100 and 2000
  or length(coalesce(c->>'research_notes','')) not between 100 and 2000

 then raise exception 'Invalid or invented recurring application details' using errcode='22023';end if;
 -- Fee amounts must be extracted from the same public form as the organizer
 -- application, with a fresh verified application hash. No guessed prices.
 if c->>'booth_fee' is not null or c->>'application_fee' is not null then
  if c->'booth_fee' is distinct from p_result->'form_fee_evidence'->'booth_fee'
    or c->'application_fee' is distinct from p_result->'form_fee_evidence'->'application_fee'
    or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$'
  then raise exception 'Official form fee receipt mismatch' using errcode='22023';end if;
  if (c->>'booth_fee' is not null and c->>'booth_fee' !~ '^[0-9]{1,5}([.][0-9]{1,2})?$')
    or (c->>'application_fee' is not null and c->>'application_fee' !~ '^[0-9]{1,5}([.][0-9]{1,2})?$')
  then raise exception 'Invalid official-form amount' using errcode='22023';end if;
  if coalesce((c->>'booth_fee')::numeric,0)>10000
     or coalesce((c->>'application_fee')::numeric,0)>10000
     or coalesce((c->>'booth_fee')::numeric,1)<=0
     or coalesce((c->>'application_fee')::numeric,1)<=0
  then raise exception 'Official-form amount out of range' using errcode='22023';end if;
 end if;

 root_host:=lower(regexp_replace(coalesce(substring(c->>'market_url' from '^https://([^/?#]+)'),''),'^www[.]',''));
 src_host:=lower(regexp_replace(coalesce(substring(c->>'source_url' from '^https://([^/?#]+)'),''),'^www[.]',''));
 app_host:=lower(regexp_replace(coalesce(substring(c->>'application_url' from '^https://([^/?#]+)'),''),'^www[.]',''));
 if root_host='' or root_host<>src_host
  or c->>'market_url' !~ '^https://[^?#]+$'
  or c->>'source_url' !~ '^https://[^?#]+$'
  or c->>'application_url' !~ '^https://[^?#]+$'
  or (app_host<>root_host and app_host not in ('form.jotform.com','pci.jotform.com','docs.google.com','forms.gle'))
  or (app_host='docs.google.com' and c->>'application_url' !~ '^https://docs[.]google[.]com/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform$')
  or (app_host='forms.gle' and c->>'application_url' !~ '^https://forms[.]gle/[A-Za-z0-9_-]{6,60}$')
  or (app_host='form.jotform.com' and c->>'application_url' !~ '^https://form[.]jotform[.]com/[0-9]{10,20}$')
  or (app_host='pci.jotform.com' and c->>'application_url' !~ '^https://pci[.]jotform[.]com/form/[0-9]{10,20}$')
 then raise exception 'Untrusted organizer or application URL' using errcode='22023';end if;

 perform pg_advisory_xact_lock(hashtextextended('rolling:'||c->>'market_slug',3));
 select * into m from public.markets where slug=c->>'market_slug' for update;
 if not found then return jsonb_build_object('action','skipped','reason','Market must already exist');end if;
 if m.is_hidden or m.is_sample or m.state<>'NC'
   or m.name is distinct from c->>'market_name'
   or m.city is distinct from c->>'city'
   or m.website_url is distinct from c->>'market_url'
 then return jsonb_build_object('action','skipped','reason','Market identity or visibility has changed');end if;
 -- Never attach a second organizer to an application already published or
 -- archived under another market.
 if exists(select 1 from public.vendor_opportunities
  where application_url=c->>'application_url' and market_id is distinct from m.id
   and publication in ('published','archived'))
 then return jsonb_build_object('action','skipped','reason','Application belongs to another market');end if;
 select * into old from public.vendor_opportunities
  where market_id=m.id and schedule_type='rolling_market'
    and publication='published'
  order by updated_at desc limit 1 for update;
 if found and (
   old.automation_hold
   or old.verification_policy is distinct from 'explore-rolling-official-v1'
   or old.application_url is distinct from c->>'application_url'
   or old.source_url is distinct from c->>'source_url'
 ) then return jsonb_build_object('action','skipped','reason','Existing rolling opportunity protected');end if;
 if not found and exists(select 1 from public.vendor_opportunities
  where market_id=m.id and publication='archived'
    and (schedule_type='rolling_market' or application_url=c->>'application_url'))
 then return jsonb_build_object('action','skipped','reason','Archived opportunity protected');end if;

 insert into public.market_occurrences(market_id,starts_on,ends_on,title)
 values(m.id,start_day,end_day,c->>'title')
 on conflict(market_id,starts_on,ends_on) do nothing;
 select id into occ from public.market_occurrences where market_id=m.id
 and starts_on=start_day and ends_on=end_day;
 if occ is null then raise exception 'Coverage occurrence could not be resolved';end if;
 if old.id is null then
  insert into public.vendor_opportunities(
   title,market_id,occurrence_id,organizer,city,state,venue,
   starts_on,ends_on,deadline,application_url,source_url,categories,
   availability,booth_fee,application_fee,deposit,fee_notes,eligibility,
   research_notes,publication,verified_at,last_checked_at,
   review_state,review_reason,verification_policy,schedule_type)
  values(c->>'title',m.id,occ,c->>'organizer',m.city,'NC',c->>'venue',
   start_day,end_day,null,c->>'application_url',c->>'source_url','{}'::text[],
   'open',nullif(c->>'booth_fee','')::numeric,nullif(c->>'application_fee','')::numeric,null,c->>'fee_notes',c->>'eligibility',
   c->>'research_notes','published',checked,now(),
   'verified','','explore-rolling-official-v1','rolling_market')
  returning id into target;
 else
  target:=old.id;
  update public.vendor_opportunities set
   title=c->>'title',occurrence_id=occ,starts_on=start_day,ends_on=end_day,

   availability='open',deadline=null,
   booth_fee=coalesce(nullif(c->>'booth_fee','')::numeric,old.booth_fee),
   application_fee=coalesce(nullif(c->>'application_fee','')::numeric,old.application_fee),
   fee_notes=c->>'fee_notes',

   eligibility=c->>'eligibility',research_notes=c->>'research_notes',
   verified_at=checked,last_checked_at=now(),review_state='verified',
   review_reason='',updated_at=now()
  where id=target;
 end if;
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(target,'publish','Organizer-owned rolling intake and matching public form independently verified.',
  jsonb_build_object('policy',p_result->>'policy','market',m.slug,
   'source',c->>'source_url','application',c->>'application_url',
   'checked_at',checked,'market_hash',p_result->>'market_source_hash',
   'source_hash',p_result->>'source_hash','form_hash',p_result->>'application_hash'));
 return jsonb_build_object('action','publish','id',target,'reason','Verified existing market rolling application');
end $function$
;
revoke all on function public.btb_research_publish_verified_rolling(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_publish_verified_rolling(jsonb) to anon,authenticated,service_role;

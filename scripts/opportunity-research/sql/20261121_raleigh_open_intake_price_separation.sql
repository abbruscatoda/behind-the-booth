-- Official Raleigh Market rolling-market publisher.
-- Exported from the live worker-secret-gated publisher on 2026-11-21.
-- Keeps application availability separate from booth pricing confirmation.
-- Incoming fees must match the official source-price receipt, and real
-- discrepancies suppress the price rather than falsely closing applications.

CREATE OR REPLACE FUNCTION public.btb_research_publish_ongoing(p_result jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare c jsonb:=p_result->'candidate';
 v_checked timestamptz; v_start date; v_end date;
 m public.markets; previous public.vendor_opportunities;
 occ uuid; opportunity uuid;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('action','skipped','reason','Research disabled');end if;
 if octet_length(p_result::text)>18000
  or p_result->>'policy' is distinct from 'raleigh-rolling-official-v1'
  or p_result->>'decision' is distinct from 'publish'
  or jsonb_typeof(c) is distinct from 'object'
  or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
  or coalesce(p_result->>'market_source_hash','') !~ '^[a-f0-9]{64}$'
  or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$'
  or length(coalesce(p_result->>'evidence','')) not between 120 and 600
 then raise exception 'Missing official rolling evidence' using errcode='22023';end if;
 v_checked:=nullif(p_result->>'checked_at','')::timestamptz;
 v_start:=nullif(c->>'starts_on','')::date;
 v_end:=nullif(c->>'ends_on','')::date;
 if v_checked is null or not isfinite(v_checked)
  or v_checked<now()-interval '6 hours' or v_checked>now()+interval '5 minutes'
  or v_start<>make_date(extract(year from (now() at time zone 'America/New_York'))::int,1,1)
  or v_end<>make_date(extract(year from v_start)::int+1,12,31)
  or c->>'market_slug' is distinct from 'the-raleigh-market'
  or c->>'market_name' is distinct from 'The Raleigh Market'
  or c->>'title' is distinct from 'The Raleigh Market — Rolling Vendor Applications'
  or c->>'organizer' is distinct from 'The Raleigh Market'
  or c->>'city' is distinct from 'Raleigh'
  or c->>'state' is distinct from 'NC'
  or c->>'venue' is distinct from '4285 Trinity Rd, Raleigh, NC 27607'
  or c->>'market_url' is distinct from 'https://www.theraleighmarket.com/'
  or c->>'source_url' is distinct from 'https://www.theraleighmarket.com/sell-with-us'
  or c->>'application_url' is distinct from 'https://form.jotform.com/200075436464149'
  or c->>'schedule_type' is distinct from 'rolling_market'
  or c->>'availability' is distinct from 'open'
  or c->>'deadline' is not null

  or jsonb_typeof(p_result->'official_source_prices') is distinct from 'object'
  or p_result->'form_price_discrepancy' not in ('true'::jsonb,'false'::jsonb)
  or c->'booth_fee' is distinct from (
      case when p_result->'form_price_discrepancy'='true'::jsonb
                or p_result->'official_source_prices'->'weekend'='null'::jsonb
           then 'null'::jsonb else p_result->'official_source_prices'->'day' end)
  or (c->>'booth_fee' is not null and c->>'booth_fee' !~ '^[1-9][0-9]{0,3}([.][0-9]{1,2})?$')

  or c->>'application_fee' is not null or c->>'deposit' is not null
  or c->'categories' is distinct from '[]'::jsonb
  or length(coalesce(c->>'fee_notes','')) not between 90 and 2000
  or (c->>'booth_fee' is not null and c->>'fee_notes' not like '%$%')
  or length(coalesce(c->>'eligibility','')) not between 90 and 2000
  or c->>'eligibility' not like '%Food trucks%'
  or length(coalesce(c->>'research_notes','')) not between 90 and 2000

 then raise exception 'Rolling opportunity identity or facts are not approved' using errcode='22023';end if;
 if (c->>'booth_fee' is not null and (c->>'booth_fee')::numeric>1000)
 then raise exception 'Official daily fee outside safe range' using errcode='22023';end if;


 perform pg_advisory_xact_lock(hashtextextended('the-raleigh-market:rolling',2));
 select * into m from public.markets where slug='the-raleigh-market' for update;
 if not found then
  return jsonb_build_object('action','skipped','reason','The Raleigh Market profile is missing; never create a duplicate');
 end if;
 if m.is_hidden or m.is_sample or m.name<>'The Raleigh Market'
    or m.city<>'Raleigh' or m.state<>'NC'
    or m.website_url is distinct from 'https://www.theraleighmarket.com/'
 then return jsonb_build_object('action','skipped','reason','Market hidden or identity conflicts');end if;
 select * into previous from public.vendor_opportunities
 where market_id=m.id and publication='published' and schedule_type='rolling_market'
 order by updated_at desc limit 1 for update;
 if found and (previous.automation_hold or previous.verification_policy is distinct from 'raleigh-rolling-official-v1'
    or previous.application_url is distinct from c->>'application_url'
    or previous.source_url is distinct from c->>'source_url')
 then return jsonb_build_object('action','skipped','reason','Existing rolling market is manually held or uses another source');end if;
 if not found and exists(select 1 from public.vendor_opportunities
    where market_id=m.id and application_url=c->>'application_url'
      and publication in ('published','archived'))
 then return jsonb_build_object('action','skipped','reason','Existing listing or archived application requires manual reconciliation');end if;
 insert into public.market_occurrences(market_id,starts_on,ends_on,title)
 values(m.id,v_start,v_end,c->>'title')
 on conflict(market_id,starts_on,ends_on) do nothing;
 select id into occ from public.market_occurrences where market_id=m.id and starts_on=v_start and ends_on=v_end;
 if occ is null then raise exception 'Rolling coverage occurrence missing' using errcode='22023';end if;
 if previous.id is null then
  insert into public.vendor_opportunities(
    title,market_id,occurrence_id,organizer,city,state,venue,
    starts_on,ends_on,deadline,application_url,source_url,categories,
    availability,booth_fee,application_fee,deposit,fee_notes,eligibility,
    research_notes,publication,verified_at,last_checked_at,
    review_state,review_reason,verification_policy,schedule_type)
  values(c->>'title',m.id,occ,c->>'organizer','Raleigh','NC',c->>'venue',
    v_start,v_end,null,c->>'application_url',c->>'source_url','{}'::text[],
    'open',nullif(c->>'booth_fee','')::numeric,null,null,c->>'fee_notes',c->>'eligibility',
    c->>'research_notes','published',v_checked,now(),
    'verified','','raleigh-rolling-official-v1','rolling_market')
  returning id into opportunity;
 else
  opportunity:=previous.id;
  update public.vendor_opportunities
  set title=c->>'title',occurrence_id=occ,starts_on=v_start,ends_on=v_end,
      availability='open',booth_fee=nullif(c->>'booth_fee','')::numeric,deadline=null,fee_notes=c->>'fee_notes',
      eligibility=c->>'eligibility',research_notes=c->>'research_notes',
      verified_at=v_checked,last_checked_at=now(),review_state='verified',
      review_reason='',updated_at=now()
  where id=opportunity;
 end if;
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(opportunity,'publish','Reverified official rolling temporary-vendor intake; weekend space is not guaranteed.',
  jsonb_build_object('policy',p_result->>'policy','source',c->>'source_url',
   'application',c->>'application_url','checked_at',v_checked,
   'source_hash',p_result->>'source_hash','form_hash',p_result->>'application_hash'));
 return jsonb_build_object('action','publish','id',opportunity,'reason','Verified ongoing vendor application');
end $function$
;
revoke all on function public.btb_research_publish_ongoing(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_publish_ongoing(jsonb) to anon,authenticated,service_role;

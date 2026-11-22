-- Optional, source-bound application facts; no availability or exact timestamps
-- are invented. Keep the existing publishers and moderation permissions intact.
create table if not exists btb_private.opportunity_field_facts(
 opportunity_id uuid primary key references public.vendor_opportunities(id) on delete cascade,
 receipt jsonb not null,
 checked_at timestamptz not null
);
alter table btb_private.opportunity_field_facts enable row level security;
revoke all on btb_private.opportunity_field_facts from public,anon,authenticated;

create or replace function public.btb_research_fact_context()
returns jsonb language plpgsql security definer set search_path='' as $function$
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('enabled',false,'items','[]'::jsonb);end if;
 return jsonb_build_object('enabled',true,
  'held',(select count(*) from public.vendor_opportunities where publication='published' and automation_hold),
  'items',(select coalesce(jsonb_agg(to_jsonb(q)),'[]'::jsonb) from (
   select o.id,o.title,o.source_url,o.application_url,o.starts_on,o.ends_on,
    o.booth_fee,o.application_fee,o.deposit,o.deadline,o.schedule_type,
    o.verification_policy,m.slug as market_slug
   from public.vendor_opportunities o join public.markets m on m.id=o.market_id
   left join btb_private.opportunity_field_facts f on f.opportunity_id=o.id
   where o.publication='published' and not o.automation_hold and not m.is_hidden and not m.is_sample
    and o.ends_on>=(now() at time zone 'America/New_York')::date
   order by f.checked_at nulls first,o.id limit 100
  ) q));
end $function$;
revoke all on function public.btb_research_fact_context() from public;
grant execute on function public.btb_research_fact_context() to anon,authenticated,service_role;

create or replace function public.btb_research_record_facts(p_result jsonb)
returns jsonb language plpgsql security definer set search_path='' as $function$
declare
 o public.vendor_opportunities; checked timestamptz; facts jsonb:=p_result->'facts';
 f jsonb; previous jsonb; k text; anchor jsonb:=p_result->'anchor';
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('action','skipped','reason','Research paused');end if;
 if p_result->>'policy' is distinct from 'published-field-evidence-v1'
  or octet_length(p_result::text)>26000
  or jsonb_typeof(facts) is distinct from 'object'
  or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
  or jsonb_typeof(facts->'pricing_options') is distinct from 'array'
  or jsonb_array_length(facts->'pricing_options')>12
  or jsonb_typeof(facts->'categories') is distinct from 'array'
  or jsonb_array_length(facts->'categories')>11
  or coalesce(facts->>'application_access','') not in ('readable','partial','access_limited')
 then raise exception 'Invalid optional-field receipt' using errcode='22023';end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 if checked is null or not isfinite(checked) or checked<now()-interval '6 hours' or checked>now()+interval '5 minutes'
 then raise exception 'Stale optional-field evidence' using errcode='22023';end if;
 select * into o from public.vendor_opportunities where id=(p_result->>'id')::uuid for update;
 if not found or o.publication<>'published' or o.automation_hold or not public.btb_market_is_visible(o.market_id)
 then return jsonb_build_object('action','skipped','reason','Protected or non-public listing');end if;
 if p_result->>'source_url' is distinct from o.source_url or p_result->>'application_url' is distinct from o.application_url
  or (p_result->>'starts_on')::date is distinct from o.starts_on or (p_result->>'ends_on')::date is distinct from o.ends_on
  or (anchor->>'booth_fee')::numeric is distinct from o.booth_fee
  or (anchor->>'application_fee')::numeric is distinct from o.application_fee
  or (anchor->>'deposit')::numeric is distinct from o.deposit
  or (anchor->>'deadline')::timestamptz is distinct from o.deadline
 then return jsonb_build_object('action','skipped','reason','Listing changed since source check');end if;
 foreach k in array array['pricing','deadline','application_fee'] loop
  f:=facts->k;
  if jsonb_typeof(f) is distinct from 'object'
   or length(coalesce(f->>'summary','')) not between 5 and 700
   or coalesce(f->>'source_hash','') !~ '^[a-f0-9]{64}$'
   or coalesce(f->>'source_url','') !~ '^https://[A-Za-z0-9.-]+/[^[:space:]<>@]*$'
  then raise exception 'Missing field provenance' using errcode='22023';end if;
 end loop;
 if coalesce(facts->'pricing'->>'status','') not in ('options','unconfirmed','varies_by_event')
  or coalesce(facts->'application_fee'->>'status','') not in ('confirmed','options','not_listed','access_limited')
  or coalesce(facts->'deadline'->>'status','') not in ('date_only','rolling','not_listed','access_limited')
 then raise exception 'Invalid field evidence status' using errcode='22023';end if;
 if facts->'application_fee'->>'status'='confirmed' and (
   jsonb_typeof(facts->'application_fee'->'amount') is distinct from 'number'
   or (facts->'application_fee'->>'amount')::numeric not between 0 and 20000)
 then raise exception 'Invalid application charge' using errcode='22023';end if;
 if facts->'deadline'->>'status'='date_only' and (
   coalesce(facts->'deadline'->>'date','') !~ '^20[0-9]{2}-[0-9]{2}-[0-9]{2}$'
   or (facts->'deadline'->>'date')::date>o.ends_on)
 then raise exception 'Invalid date-only application deadline' using errcode='22023';end if;
 for f in select value from jsonb_array_elements(facts->'pricing_options') loop
  if jsonb_typeof(f->'amount') is distinct from 'number' or (f->>'amount')::numeric not between 0 and 20000
   or coalesce(f->>'kind','') not in ('booth','application','addon')
   or coalesce(f->>'unit','') not in ('day','event','season','program','application')
   or jsonb_typeof(f->'applicable') is distinct from 'boolean'
   or length(coalesce(f->>'label','')) not between 3 and 110
   or length(coalesce(f->>'conditions',''))>400
   or coalesce(f->>'source_hash','') !~ '^[a-f0-9]{64}$'
   or coalesce(f->>'source_url','') !~ '^https://[A-Za-z0-9.-]+/[^[:space:]<>@]*$'
  then raise exception 'Invalid scoped price option' using errcode='22023';end if;
 end loop;
 if exists(select 1 from jsonb_array_elements_text(facts->'categories') c
  where c not in ('Food & Beverages','Food Trucks','Art & Photography','Handmade Crafts','Jewelry & Accessories','Clothing & Vintage','Bath, Body & Beauty','Plants & Farm Products','Pet Products','Services','Other'))
 then raise exception 'Unknown category in field evidence' using errcode='22023';end if;
 select receipt into previous from btb_private.opportunity_field_facts where opportunity_id=o.id;
 if (previous->>'checked_at')::timestamptz>checked then
  return jsonb_build_object('action','skipped','reason','Newer field evidence already stored');
 end if;
 -- Keep the last good, still time-limited evidence when a formerly readable
 -- section disappears. Record the regression; do not silently erase it.
 if previous is not null and (
   (jsonb_array_length(previous->'facts'->'pricing_options')>0 and jsonb_array_length(facts->'pricing_options')=0)
   or (previous->'facts'->'deadline'->>'status'='date_only' and facts->'deadline'->>'status'<>'date_only'))
 then
  insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
  values(o.id,'review','Optional application facts previously found are no longer readable.',jsonb_build_object('policy',p_result->>'policy','checked_at',checked));
  return jsonb_build_object('action','retained','reason','Previously verified details require a source recheck');
 end if;
 insert into btb_private.opportunity_field_facts(opportunity_id,receipt,checked_at)
 values(o.id,p_result,checked) on conflict(opportunity_id) do update set receipt=excluded.receipt,checked_at=excluded.checked_at;
 return jsonb_build_object('action','updated','id',o.id);
end $function$;
revoke all on function public.btb_research_record_facts(jsonb) from public;
grant execute on function public.btb_research_record_facts(jsonb) to anon,authenticated,service_role;

create or replace function btb_private.public_opportunity_facts(p_id uuid)
returns jsonb language sql stable set search_path='' as $function$
 select coalesce((select f.receipt->'facts'||jsonb_build_object('checked_at',f.checked_at)
 from btb_private.opportunity_field_facts f join public.vendor_opportunities o on o.id=f.opportunity_id
 where f.opportunity_id=p_id and f.checked_at<=now() and f.checked_at>now()-interval '7 days'
  and o.publication='published' and public.btb_market_is_visible(o.market_id)
  and f.receipt->>'source_url'=o.source_url and f.receipt->>'application_url'=o.application_url
  and (f.receipt->>'starts_on')::date=o.starts_on and (f.receipt->>'ends_on')::date=o.ends_on
  and (f.receipt->'anchor'->>'booth_fee')::numeric is not distinct from o.booth_fee
  and (f.receipt->'anchor'->>'application_fee')::numeric is not distinct from o.application_fee
  and (f.receipt->'anchor'->>'deposit')::numeric is not distinct from o.deposit
  and (f.receipt->'anchor'->>'deadline')::timestamptz is not distinct from o.deadline),'{}'::jsonb);
$function$;
revoke all on function btb_private.public_opportunity_facts(uuid) from public,anon,authenticated;

-- Extend the existing public projection without changing its signature or
-- exposing private notes. A day-only deadline closes on the next local day;
-- never invent 11:59 PM or an exact timestamp for that date.
do $patch$
declare definition text; oldpiece text; newpiece text;
begin
 select pg_get_functiondef('public.btb_public_opportunities(uuid,integer)'::regprocedure) into definition;
 if position('as field_facts' in definition)>0 then return;end if;
 oldpiece:='o.published_at,o.booth_fee';
 newpiece:='btb_private.public_opportunity_facts(o.id) as field_facts,o.published_at,o.booth_fee';
 if position(oldpiece in definition)=0 then raise exception 'Unexpected public opportunity projection';end if;
 definition:=replace(definition,oldpiece,newpiece);
 oldpiece:='public.btb_opportunity_state(o.availability,o.deadline,o.verified_at,o.ends_on) as effective_status';
 newpiece:='case when (btb_private.public_opportunity_facts(o.id)->''deadline''->>''date'')::date < (now() at time zone ''America/New_York'')::date then ''closed'' else public.btb_opportunity_state(o.availability,o.deadline,o.verified_at,o.ends_on) end as effective_status';
 if position(oldpiece in definition)=0 then raise exception 'Unexpected public opportunity status';end if;
 execute replace(definition,oldpiece,newpiece);
end $patch$;

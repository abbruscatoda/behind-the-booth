-- Distinguish recurring season-wide application opportunities from dated events.
alter table public.vendor_opportunities
 add column if not exists schedule_type text not null default 'dated_event';
alter table public.vendor_opportunities
 drop constraint if exists vendor_opportunities_schedule_type_check;
alter table public.vendor_opportunities
 add constraint vendor_opportunities_schedule_type_check
 check (schedule_type in ('dated_event','recurring_season'));

-- Worker-secret-gated, season-specific publication, with strict official
-- source paths and trusted existing market identity. Never invent a deadline.
create or replace function public.btb_research_publish_recurring(p_result jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 c jsonb:=p_result->'candidate';
 checked timestamptz;
 season_start date;
 season_end date;
 market_id uuid;
 occurrence_id uuid;
 opportunity_id uuid;
 previous public.vendor_opportunities;
 m public.markets;
 action_name text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('action','skipped','reason','Research disabled.');end if;
 if octet_length(p_result::text)>22000
   or p_result->>'policy' is distinct from 'recurring-official-waitlist-v1'
   or p_result->>'decision' is distinct from 'publish'
   or jsonb_typeof(c) is distinct from 'object'
   or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
   or coalesce(p_result->>'market_source_hash','') !~ '^[a-f0-9]{64}$'
   or length(coalesce(p_result->>'evidence','')) not between 50 and 600
 then raise exception 'Missing official recurring market verification receipt' using errcode='22023';end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 season_start:=nullif(c->>'starts_on','')::date;
 season_end:=nullif(c->>'ends_on','')::date;
 if checked is null or not isfinite(checked) or
    checked<now()-interval '6 hours' or checked>now()+interval '5 minutes'
   or season_start is null or season_end is null
   or season_start<>make_date(extract(year from season_start)::int,5,1)
   or season_end<>make_date(extract(year from season_start)::int+1,4,30)
   or (now() at time zone 'America/New_York')::date not between season_start and season_end
   or c->>'schedule_type' is distinct from 'recurring_season'
   or c->>'availability' is distinct from 'waitlist'
   or c->>'deadline' is not null
   or c->>'title' is distinct from
     ('Holly Springs Farmers Market — '||extract(year from season_start)::int||'–'||
      extract(year from season_end)::int||' Vendor Waitlist')
   or c->>'market_slug' is distinct from 'holly-springs-farmers-market'
   or c->>'organizer' is distinct from 'Town of Holly Springs'
   or c->>'city' is distinct from 'Holly Springs'
   or c->>'state' is distinct from 'NC'
   or c->>'venue' is distinct from '300 W. Ballentine St.'
   or c->>'source_url' is distinct from 'https://www.hollyspringsnc.gov/1824/Become-a-Vendor'
   or c->>'market_url' is distinct from 'https://www.hollyspringsnc.gov/319/Farmers-Market'
   or c->>'application_url' is distinct from 'https://managemymarket.com/VendorRegister.aspx?orgID=933'
   or c->>'application_fee' is distinct from '20'
   or c->>'booth_fee' is not null or c->>'deposit' is not null
   or c->'categories' is distinct from '[]'::jsonb
   or length(coalesce(c->>'fee_notes','')) not between 50 and 2000
   or length(coalesce(c->>'eligibility','')) not between 50 and 2000
   or position('Food trucks are not currently accepted.' in coalesce(c->>'eligibility',''))=0
 then raise exception 'Recurring market evidence is outside approved source/season policy' using errcode='22023';end if;
 perform pg_advisory_xact_lock(hashtextextended(c->>'application_url',1));
 select * into m from public.markets
 where slug='holly-springs-farmers-market' for update;
 if not found then
  insert into public.markets(name,slug,city,state,description,website_url,organizer,is_sample)
  values('Holly Springs Farmers Market','holly-springs-farmers-market',
    'Holly Springs','NC','Year-round, food-focused farmers market operated by the Town of Holly Springs.',
    c->>'market_url','Town of Holly Springs',false)
  returning * into m;
 end if;
 if m.is_hidden or m.is_sample or m.name<>'Holly Springs Farmers Market'
   or m.organizer is distinct from 'Town of Holly Springs' or m.city<>'Holly Springs'
   or m.state<>'NC'
 then return jsonb_build_object('action','skipped','reason','Existing market profile conflicts with verified organizer identity or is hidden.');end if;
 market_id:=m.id;
 insert into public.market_occurrences(market_id,starts_on,ends_on,title)
 values(market_id,season_start,season_end,c->>'title')
 on conflict(market_id,starts_on,ends_on) do update set title=excluded.title
 returning id into occurrence_id;
 select * into previous from public.vendor_opportunities
 where application_url=c->>'application_url' and starts_on=season_start for update;
 if found then
  if previous.automation_hold or previous.schedule_type<>'recurring_season'
    or previous.market_id is distinct from market_id
    or previous.verification_policy is distinct from 'recurring-official-waitlist-v1'
    or previous.source_url is distinct from c->>'source_url'
    or previous.publication='archived'
  then return jsonb_build_object('action','skipped','reason','Existing application is held, archived or conflicts with recurring verification.');
  end if;
  opportunity_id:=previous.id;
  update public.vendor_opportunities set
   title=c->>'title',organizer=c->>'organizer',city=c->>'city',
   venue=c->>'venue',ends_on=season_end,availability='waitlist',
   deadline=null,application_fee=20,booth_fee=null,deposit=null,
   categories='{}'::text[],fee_notes=c->>'fee_notes',eligibility=c->>'eligibility',
   research_notes=c->>'research_notes',last_checked_at=now(),verified_at=checked,
   review_state='verified',review_reason='',updated_at=now()
  where id=opportunity_id;
  action_name:='publish';
 else
  insert into public.vendor_opportunities(
   title,market_id,occurrence_id,organizer,city,state,venue,starts_on,ends_on,
   deadline,application_url,source_url,categories,availability,booth_fee,application_fee,
   deposit,fee_notes,eligibility,research_notes,publication,verified_at,
   last_checked_at,review_state,review_reason,verification_policy,schedule_type)
  values(c->>'title',market_id,occurrence_id,c->>'organizer',c->>'city','NC',
   c->>'venue',season_start,season_end,null,c->>'application_url',c->>'source_url',
   '{}'::text[],'waitlist',null,20,null,c->>'fee_notes',c->>'eligibility',
   c->>'research_notes','published',checked,now(),'verified','','recurring-official-waitlist-v1','recurring_season')
  returning id into opportunity_id;
  action_name:='publish';
 end if;
 -- Remove misleading directory links only after an actual successful publication.
 update btb_private.triangle_discovery_leads set review_state='resolved',last_seen=now()
 where target_url=c->>'source_url' and review_state='new';
 update btb_private.triangle_discovery_leads set review_state='ignored',last_seen=now()
 where target_url='https://nchollyspringsweb.myvscloud.com/webtrac/web/splash.html'
 and source_url=c->>'market_url' and review_state='new';
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(opportunity_id,action_name,
  'Official Holly Springs season-long farmers market waitlist verified; does not imply open booths or individual Saturdays.',
  jsonb_build_object('policy',p_result->>'policy','source',c->>'source_url',
   'application',c->>'application_url','checked_at',checked,
   'vendor_hash',p_result->>'source_hash','market_hash',p_result->>'market_source_hash',
   'schedule_type','recurring_season'));
 return jsonb_build_object('action','publish','id',opportunity_id,
  'market_id',market_id,'reason','Official recurring vendor waitlist verified and published.');
end $$;
revoke all on function public.btb_research_publish_recurring(jsonb)
 from public,anon,authenticated;
grant execute on function public.btb_research_publish_recurring(jsonb)
 to anon,authenticated,service_role;

-- This public result already returns all the required published opportunity
-- fields; include explicit schedule type for honest seasonal presentation.
do $alter$
declare definition text;
begin
 select pg_get_functiondef('public.btb_public_opportunities(uuid,integer)'::regprocedure)
 into definition;
 if position('o.id,o.title,o.organizer' in definition)=0 then
  raise exception 'Unknown public opportunity view version';
 end if;
 execute replace(definition,'o.id,o.title,o.organizer',
   'o.id,o.title,o.schedule_type,o.organizer');
end $alter$;

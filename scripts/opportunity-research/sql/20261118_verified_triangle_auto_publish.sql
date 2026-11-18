-- Strict auto-publisher for fully verified, new Triangle Eventeny opportunities.
-- Web search and general organizer application links NEVER invoke this RPC.
-- Requires the existing dedicated worker secret and scoped receipt validators.
create or replace function public.btb_research_publish_discovery(p_result jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 c jsonb:=p_result->'candidate';
 checked timestamptz;
 starts date;
 ends date;
 deadline_at timestamptz;
 event_title text;
 organizer_name text;
 city_name text;
 source text;
 app text;
 venue_text text;
 slug_base text;
 market_slug text;
 existing_market public.markets;
 m_id uuid;
 o_id uuid;
 occurrence uuid;
 receipt jsonb;
 quality jsonb;
 amount_key text;
 value numeric;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false) then
  return jsonb_build_object('action','skipped','reason','Automatic updates paused.');
 end if;
 if octet_length(p_result::text)>40000
   or p_result->>'policy' is distinct from 'triangle-eventeny-auto-v1'
   or p_result->>'decision' is distinct from 'publish'
   or jsonb_typeof(c) is distinct from 'object'
   or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
   or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$'
   or length(coalesce(p_result->>'evidence','')) not between 20 and 600
   or p_result ? 'category_conflicts'
 then raise exception 'New discovery lacks a trusted, conflict-free Eventeny verification receipt.' using errcode='22023';
 end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 starts:=nullif(c->>'starts_on','')::date;
 ends:=nullif(c->>'ends_on','')::date;
 deadline_at:=nullif(c->>'deadline','')::timestamptz;
 event_title:=trim(coalesce(c->>'title',''));
 organizer_name:=trim(coalesce(c->>'organizer',''));
 city_name:=trim(coalesce(c->>'city',''));
 source:=c->>'source_url';
 app:=c->>'application_url';
 venue_text:=trim(coalesce(c->>'venue',''));
 if checked is null or not isfinite(checked)
  or checked<now()-interval '6 hours' or checked>now()+interval '5 minutes'
  or starts is null or ends is null
  or starts<(now() at time zone 'America/New_York')::date
  or starts>(now() at time zone 'America/New_York')::date+183
  or ends<starts or ends>starts+14
  or deadline_at is null or not isfinite(deadline_at) or deadline_at<=now()
  or length(event_title) not between 3 and 160
  or length(organizer_name) not between 2 and 120
  or organizer_name !~ '^[[:print:]]+$'
  or organizer_name is distinct from trim(regexp_replace(organizer_name,'[[:space:]]+',' ','g'))
  or length(venue_text)>300
  or c->>'state' is distinct from 'NC'
  or lower(city_name) not in
   ('raleigh','durham','cary','apex','wendell','rolesville','wake forest',
   'chapel hill','carrboro','holly springs','fuquay-varina','morrisville',
   'garner','clayton','pittsboro','hillsborough','knightdale','zebulon',
   'youngsville','creedmoor','angier','siler city','mebane','franklinton')
  or coalesce(source,'') !~ '^https://www[.]eventeny[.]com/events/[A-Za-z0-9-]+-[0-9]+/([?]series=[0-9]+)?$'
  or coalesce(app,'') !~ '^https://www[.]eventeny[.]com/events/vendor/[?]id=[0-9]+$'
  or c->>'market_slug' is not null
  or c->>'availability' not in ('open','limited','waitlist')
  or jsonb_typeof(c->'categories') is distinct from 'array'
  or length(coalesce(c->>'fee_notes',''))>2000
  or length(coalesce(c->>'eligibility',''))>2000
 then raise exception 'New opportunity is outside the verified Triangle application policy.' using errcode='22023';
 end if;
 foreach amount_key in array array['booth_fee','application_fee','deposit'] loop
  if c->amount_key is not null and c->amount_key<>'null'::jsonb then
   if jsonb_typeof(c->amount_key) is distinct from 'number'
   then raise exception 'Invalid discovered fee type.' using errcode='22023';end if;
   value:=(c->>amount_key)::numeric;
   if value<0 or value>10000 then raise exception 'Unreasonable discovered fee.' using errcode='22023';end if;
  end if;
 end loop;
 -- Validate exactly the application, event date, categories, and source checked
 -- by the worker. Coverage cannot upgrade missing identity or availability.
 receipt:=btb_private.validate_worker_categories(p_result,checked);
 quality:=btb_private.validate_research_quality(p_result,receipt,checked);
 if quality->'fields'->'identity'->>'status' is distinct from 'confirmed'
   or quality->'fields'->'availability'->>'status' is distinct from 'confirmed'
 then raise exception 'Source identity and availability must be confirmed.' using errcode='22023';end if;

 perform pg_advisory_xact_lock(hashtextextended(app||starts::text,0));
 if exists(select 1 from public.vendor_opportunities o
           where o.application_url=app and o.starts_on=starts) then
  return jsonb_build_object('action','skipped','reason','Application and event date already recorded.');
 end if;

 -- Existing market identities are matched by NAME+CITY+ORGANIZER, never merely
 -- by a similar name or a shared application URL.
 select m.* into existing_market from public.markets m
 where m.state='NC' and lower(m.city)=lower(city_name)
   and regexp_replace(lower(m.name),'[^a-z0-9]','','g')
       =regexp_replace(lower(event_title),'[^a-z0-9]','','g')
   and not m.is_sample
 order by m.id limit 1 for update;
 if found then
  if regexp_replace(lower(coalesce(existing_market.organizer,'')),'[^a-z0-9]','','g')
     is distinct from regexp_replace(lower(organizer_name),'[^a-z0-9]','','g')
     or existing_market.is_hidden
  then
   return jsonb_build_object('action','skipped','reason',
     'Existing market has a different organizer or is hidden; automated publication withheld.');
  end if;
  m_id:=existing_market.id;
 else
  -- One canonical profile for a newly discovered market across future dates.
  market_slug:=left(regexp_replace(lower(event_title||'-'||city_name),'[^a-z0-9]+','-','g'),70);
  market_slug:=trim(both '-' from market_slug);
  if length(market_slug)<3 then raise exception 'Cannot create a safe market slug.' using errcode='22023';end if;
  if exists(select 1 from public.markets where slug=market_slug) then
   market_slug:=left(market_slug,58)||'-'||left(md5(source),8);
  end if;
  insert into public.markets(slug,name,city,state,description,website_url,organizer,is_sample)
   values(market_slug,event_title,city_name,'NC',
      left(event_title||' is a vendor event in '||city_name||
       ', North Carolina. Event details and vendor applications are published through the organizer-linked Eventeny page.',600),
      source,organizer_name,false)
   returning id into m_id;
 end if;

 insert into public.market_occurrences(market_id,starts_on,ends_on,title)
 values(m_id,starts,ends,event_title)
 on conflict(market_id,starts_on,ends_on) do update set title=excluded.title
 returning id into occurrence;

 o_id:=public.btb_stage_opportunity(c);
 update public.vendor_opportunities o set
  market_id=m_id,occurrence_id=occurrence,publication='published',
  review_state='verified',review_reason='',
  verification_policy='triangle-eventeny-auto-v1',
  last_checked_at=now(),verified_at=checked,
  category_evidence=receipt,updated_at=now()
 where o.id=o_id and o.publication='draft' and not o.automation_hold;
 if not found then raise exception 'New opportunity was modified or manually held.' using errcode='22023';end if;

 insert into btb_private.opportunity_research_quality(opportunity_id,report)
 values(o_id,quality)
 on conflict(opportunity_id) do update
  set report=excluded.report,updated_at=now();
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(o_id,'publish','New Triangle event and market automatically published from independently matched Eventeny sources.',
  jsonb_build_object('policy',p_result->>'policy','event_source',source,
   'application_url',app,'checked_at',checked,
   'source_hash',p_result->>'source_hash',
   'application_hash',p_result->>'application_hash'));
 return jsonb_build_object('action','publish','id',o_id,'market_id',m_id,
  'reason','New organizer-linked Triangle event and market published automatically.');
end $$;
revoke all on function public.btb_research_publish_discovery(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_publish_discovery(jsonb) to anon,authenticated,service_role;

-- Include the existing listing's trusted policy so the next recheck takes the
-- organizer-bound Eventeny path (including newly discovered MAKRS events).
DO $change$
DECLARE olddef text;
BEGIN
 select pg_get_functiondef('public.btb_research_context()'::regprocedure)
 into olddef;
 if position('o.publication,o.automation_hold,o.verification_policy,o.updated_at' in olddef)>0 then
  return;
 end if;
 if position('o.publication,o.automation_hold,o.updated_at' in olddef)=0 then
  raise exception 'Unexpected research-context version; auto-publisher migration rolled back.';
 end if;
 execute replace(olddef,'o.publication,o.automation_hold,o.updated_at',
    'o.publication,o.automation_hold,o.verification_policy,o.updated_at');
END $change$;
-- Only independent, complete organizer-linked PUBLIC forms qualify.
-- All writes are worker-secret guarded; no unauthenticated form scraping or submissions.
create or replace function public.btb_research_publish_form(
 p_result jsonb,p_id uuid default null,p_expected_updated_at timestamptz default null)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 c jsonb:=p_result->'candidate';
 checked timestamptz; starts date; ends date; cutoff timestamptz;
 name_text text; org text; city_name text; src text; app text;
 slug_text text; mid uuid; oid uuid; occurrence uuid;
 m public.markets; item public.vendor_opportunities;
 receipt jsonb; quality jsonb; previous_quality jsonb; problems text[];
 key text; amount numeric; has_conflict boolean;
 sources constant text[]:=array[
 'https://www.trianglepopup.com/applications',
 'https://thenightmarketcompany.com/',
 'https://shoplocalraleigh.org/vendor-information/',
 'https://www.geekandgrubmarket.com/vendorapplication',
 'https://hummingbirdmarketnc.com/member-markets',
 'https://www.caryfarmersmarket.com/vendor-application/',
 'https://www.hillsboroughartscouncil.org/last-fridays-markets',
 'https://www.takethehighstreet.com/thebazaar',
 'https://blackfarmersmkt.org/the-market/',
 'https://www.durhamcraftmarket.com/saturdays-in-durham-central-park.html',
 'https://www.carrborofarmersmarket.com/',
 'https://www.apexfarmersmarket.com/',
 'https://www.thechapelhillfarmersmarket.com/',
 'https://www.hollyspringsnc.gov/319/Farmers-Market',
 'https://westernwakefarmersmarket.org/',
 'https://www.enoriverfarmersmarket.com/',
 'https://www.fvgrowersmarket.com/',
 'https://www.ymcatriangle.org/events/vendor-market',
 'https://artspacenc.org/calls-for-art/',
 'https://www.artsplosure.org/first-night-raleigh'];
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('action','skipped','reason','Automatic updates paused.');end if;
 if octet_length(p_result::text)>40000 or jsonb_typeof(c) is distinct from 'object'
  or p_result->>'policy' is distinct from 'triangle-form-auto-v1'
  or p_result->>'decision' is distinct from 'publish'
  or p_result->'form_complete' is distinct from 'true'::jsonb
  or p_result->'form_readable' is distinct from 'true'::jsonb
  or p_result ? 'category_conflicts'
  or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
  or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$'
  or length(coalesce(p_result->>'evidence','')) not between 30 and 600
 then raise exception 'Unverified public-form publication request.' using errcode='22023';end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 starts:=nullif(c->>'starts_on','')::date;ends:=nullif(c->>'ends_on','')::date;
 cutoff:=nullif(c->>'deadline','')::timestamptz;
 name_text:=trim(coalesce(c->>'title',''));org:=trim(coalesce(c->>'organizer',''));
 city_name:=trim(coalesce(c->>'city',''));
 src:=c->>'source_url';app:=c->>'application_url';
 if checked is null or not isfinite(checked) or checked<now()-interval '6 hours'
   or checked>now()+interval '5 minutes'
   or starts is null or ends is null or ends<>starts
   or starts<(now() at time zone 'America/New_York')::date
   or starts>(now() at time zone 'America/New_York')::date+183
   or cutoff is null or not isfinite(cutoff) or cutoff<=now()
   or (cutoff at time zone 'America/New_York')::date>starts
   or length(name_text) not between 10 and 160
   or length(org) not between 2 and 120
   or org is distinct from trim(regexp_replace(org,'[[:space:]]+',' ','g'))
   or c->>'state' is distinct from 'NC'
   or lower(city_name) not in
    ('raleigh','durham','cary','apex','wendell','rolesville','wake forest',
    'chapel hill','carrboro','holly springs','fuquay-varina','morrisville',
    'garner','clayton','pittsboro','hillsborough','knightdale','zebulon',
    'youngsville','creedmoor','angier','siler city','mebane','franklinton')
   or coalesce(src,'') <> all(sources)
   or not (
      coalesce(app,'') ~ '^https://form[.]jotform[.]com/[0-9]{10,20}$'
      or coalesce(app,'') ~ '^https://pci[.]jotform[.]com/form/[0-9]{10,20}$'
      or coalesce(app,'') ~ '^https://docs[.]google[.]com/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform$'
      or coalesce(app,'') ~ '^https://forms[.]gle/[A-Za-z0-9_-]{6,60}$')
   or c->>'market_slug' is not null
   or c->>'availability' is distinct from 'open'
   or c->'categories' is distinct from '[]'::jsonb
   or length(coalesce(c->>'venue',''))>300
   or length(coalesce(c->>'fee_notes',''))>2000
   or length(coalesce(c->>'eligibility',''))>2000
 then raise exception 'Form application is not independently bound to an eligible dated Triangle event.' using errcode='22023';end if;
 foreach key in array array['booth_fee','application_fee','deposit'] loop
  if c->key is not null and c->key <> 'null'::jsonb then
   if jsonb_typeof(c->key) is distinct from 'number' then raise exception 'Invalid form fee type' using errcode='22023';end if;
   amount:=(c->>key)::numeric;
   if amount<0 or amount>10000 then raise exception 'Unsupported form fee amount' using errcode='22023';end if;
  end if;
 end loop;
 receipt:=btb_private.validate_worker_categories(p_result,checked);
 quality:=btb_private.validate_research_quality(p_result,receipt,checked);
 if quality->'fields'->'identity'->>'status' is distinct from 'confirmed'
   or quality->'fields'->'availability'->>'status' is distinct from 'confirmed'
   or quality->'fields'->'deadline'->>'status' is distinct from 'confirmed'
 then raise exception 'Critical form facts must all be confirmed.' using errcode='22023';end if;

 perform pg_advisory_xact_lock(hashtextextended(app||starts::text,0));
 if p_id is not null then
  select * into item from public.vendor_opportunities where id=p_id for update;
  if not found or p_expected_updated_at is null or item.updated_at is distinct from p_expected_updated_at
    or item.application_url is distinct from app or item.source_url is distinct from src
    or item.starts_on is distinct from starts or item.ends_on is distinct from ends
    or item.publication<>'published' or item.automation_hold
    or item.verification_policy is distinct from 'triangle-form-auto-v1'
  then return jsonb_build_object('action','skipped','reason','Listing was manually changed, held, or differs from verified form.');end if;
  select * into m from public.markets where id=item.market_id and not is_hidden and not is_sample;
  if not found or regexp_replace(lower(m.name),'[^a-z0-9]','','g')
       is distinct from regexp_replace(lower(name_text),'[^a-z0-9]','','g')
     or regexp_replace(lower(coalesce(m.organizer,'')),'[^a-z0-9]','','g')
       is distinct from regexp_replace(lower(org),'[^a-z0-9]','','g')
     or lower(m.city) is distinct from lower(city_name)
  then return jsonb_build_object('action','skipped','reason','Verified form conflicts with the linked market identity.');end if;
  select report into previous_quality from btb_private.opportunity_research_quality where opportunity_id=item.id;
  problems:=btb_private.research_regressions(previous_quality,quality);
  if cardinality(problems)>0 then
   update public.vendor_opportunities set review_state='verification_notice',
    review_reason='Public form evidence changed; previously approved facts retained.',
    availability='needs_recheck',last_checked_at=now() where id=item.id;
   insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
    values(item.id,'notice','Public form research regression prevented an automatic update.',
      jsonb_build_object('changes',to_jsonb(problems),'source',src));
   return jsonb_build_object('action','skipped','reason','Public form research regressed.','id',item.id);
  end if;
  update public.vendor_opportunities set deadline=cutoff,
    availability='open',review_state='verified',review_reason='',
    verified_at=checked,last_checked_at=now(),updated_at=now(),
    booth_fee=nullif(c->>'booth_fee','')::numeric,
    application_fee=nullif(c->>'application_fee','')::numeric,
    deposit=nullif(c->>'deposit','')::numeric,
    fee_notes=coalesce(c->>'fee_notes',''),eligibility=coalesce(c->>'eligibility','')
  where id=item.id;
  oid:=item.id;
 else
  if exists(select 1 from public.vendor_opportunities
    where application_url=app and starts_on=starts) then
    return jsonb_build_object('action','skipped','reason','Application/date already exists.');
  end if;
  select * into m from public.markets
   where state='NC' and lower(city)=lower(city_name)
   and regexp_replace(lower(name),'[^a-z0-9]','','g')
       =regexp_replace(lower(name_text),'[^a-z0-9]','','g')
   and not is_sample order by id limit 1 for update;
  if found then
   if m.is_hidden
    or regexp_replace(lower(coalesce(m.organizer,'')),'[^a-z0-9]','','g')
       is distinct from regexp_replace(lower(org),'[^a-z0-9]','','g')
   then return jsonb_build_object('action','skipped','reason','Existing market is hidden or has a different organizer.');end if;
   mid:=m.id;
  else
   slug_text:=trim(both '-' from left(regexp_replace(lower(name_text||'-'||city_name),'[^a-z0-9]+','-','g'),70));
   if length(slug_text)<3 then raise exception 'Cannot create market slug.' using errcode='22023';end if;
   if exists(select 1 from public.markets where slug=slug_text) then
    slug_text:=left(slug_text,58)||'-'||left(md5(src),8);
   end if;
   insert into public.markets(slug,name,city,state,description,website_url,organizer,is_sample)
    values(slug_text,name_text,city_name,'NC',
      left(name_text||' is a vendor market in '||city_name||
       ', North Carolina. The organizer publishes its event details and vendor application through the linked official event page.',600),
      src,org,false) returning id into mid;
  end if;
  insert into public.market_occurrences(market_id,starts_on,ends_on,title)
    values(mid,starts,ends,name_text)
    on conflict(market_id,starts_on,ends_on) do update set title=excluded.title
    returning id into occurrence;
  oid:=public.btb_stage_opportunity(c);
  update public.vendor_opportunities set market_id=mid,occurrence_id=occurrence,
    publication='published',review_state='verified',review_reason='',
    verification_policy='triangle-form-auto-v1',
    verified_at=checked,last_checked_at=now(),category_evidence=receipt,
    updated_at=now()
  where id=oid and publication='draft' and not automation_hold;
  if not found then raise exception 'New application was manually edited or held.' using errcode='22023';end if;
 end if;
 insert into btb_private.opportunity_research_quality(opportunity_id,report) values(oid,quality)
 on conflict(opportunity_id) do update set report=excluded.report,updated_at=now();
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(oid,'publish','Organizer-linked public form independently verified and published.',
  jsonb_build_object('policy',p_result->>'policy','source',src,'application',app,
   'checked_at',checked,'source_hash',p_result->>'source_hash',
   'application_hash',p_result->>'application_hash'));
 return jsonb_build_object('action','publish','id',oid,
    'reason','Public vendor form and its official dated event were verified.');
end $$;
revoke all on function public.btb_research_publish_form(jsonb,uuid,timestamptz) from public,anon,authenticated;
grant execute on function public.btb_research_publish_form(jsonb,uuid,timestamptz) to anon,authenticated,service_role;
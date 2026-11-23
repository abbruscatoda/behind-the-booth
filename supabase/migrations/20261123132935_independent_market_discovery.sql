-- Narrow publisher for reviewed GRL venue identities and public WorkForms.
-- Broader organizer discovery never grants publication or bypasses manual holds.
CREATE FUNCTION public.btb_research_publish_independent_market(p_result jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE c jsonb:=p_result->'candidate'; expected jsonb; checked timestamptz; day date;
 m public.markets; old public.vendor_opportunities; opp uuid; occurrence uuid;
BEGIN
 PERFORM public.btb_research_authorize();
 IF NOT coalesce((SELECT enabled FROM public.btb_research_settings WHERE id=true),false) THEN RETURN jsonb_build_object('action','skipped','reason','Research disabled'); END IF;
 expected:=CASE c->>'market_slug'
 WHEN 'grl-market-at-waverly-place' THEN '{"name":"GRL Market at Waverly Place","city":"Cary","venue":"Waverly Place, 302 Colonades Way, Cary, NC"}'::jsonb
 WHEN 'grl-market-at-transfer-food-hall' THEN '{"name":"GRL Market at Transfer Food Hall","city":"Raleigh","venue":"Transfer Food Hall, 500 E Davie Street, Raleigh, NC"}'::jsonb
 WHEN 'grl-market-at-seaboard-station' THEN '{"name":"GRL Market at Seaboard Station","city":"Raleigh","venue":"Seaboard Station, 20 Seaboard Avenue, Raleigh, NC"}'::jsonb
 ELSE NULL END;
 IF expected IS NULL OR jsonb_typeof(c) IS DISTINCT FROM 'object' OR octet_length(p_result::text)>20000
 OR p_result->>'policy' IS DISTINCT FROM 'independent-market-applications-v1' OR p_result->>'decision' IS DISTINCT FROM 'publish'
 OR coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$' OR coalesce(p_result->>'form_hash','') !~ '^[a-f0-9]{64}$'
 OR coalesce(p_result->>'hub_hash','') !~ '^[a-f0-9]{64}$' OR length(coalesce(p_result->>'evidence','')) NOT BETWEEN 120 AND 800
 OR c->>'source_url' IS DISTINCT FROM 'https://grlmarket.com/'
 OR coalesce(c->>'application_url','') !~ '^https://forms[.]monday[.]com/forms/[a-f0-9]{32}([?]r=use1)?$'
 OR c->>'market_name' IS DISTINCT FROM expected->>'name' OR c->>'title' IS DISTINCT FROM expected->>'name'
 OR c->>'city' IS DISTINCT FROM expected->>'city' OR c->>'venue' IS DISTINCT FROM expected->>'venue'
 OR c->>'organizer' IS DISTINCT FROM 'GRL Market' OR c->>'state' IS DISTINCT FROM 'NC'
 OR c->>'schedule_type' IS DISTINCT FROM 'dated_event' OR c->>'deadline' IS NOT NULL
 OR c->>'application_fee' IS NOT NULL OR c->>'deposit' IS NOT NULL
 OR coalesce(c->>'availability','') NOT IN ('open','closed')
 OR jsonb_typeof(c->'categories') IS DISTINCT FROM 'array'
 OR length(coalesce(c->>'eligibility','')) NOT BETWEEN 100 AND 2000
 OR length(coalesce(c->>'fee_notes','')) NOT BETWEEN 90 AND 2000
 OR length(coalesce(c->>'research_notes','')) NOT BETWEEN 100 AND 2500
 THEN RAISE EXCEPTION 'Independent market receipt is not verified' USING errcode='22023'; END IF;
 checked:=(p_result->>'checked_at')::timestamptz; day:=(c->>'starts_on')::date;
 IF checked IS NULL OR NOT isfinite(checked) OR checked<now()-interval '6 hours' OR checked>now()+interval '5 minutes'
 OR day IS NULL OR NOT isfinite(day) OR day<(now() AT TIME ZONE 'America/New_York')::date OR day>(now() AT TIME ZONE 'America/New_York')::date+550
 OR c->>'ends_on' IS DISTINCT FROM c->>'starts_on'
 OR (c->>'availability'='open' AND (c->>'booth_fee' IS NULL OR (c->>'booth_fee')::numeric NOT BETWEEN 0 AND 2000))
 OR EXISTS(SELECT 1 FROM jsonb_array_elements_text(c->'categories') x WHERE x NOT IN ('Food & Beverages','Food Trucks','Art & Photography','Handmade Crafts','Jewelry & Accessories','Clothing & Vintage','Bath, Body & Beauty','Plants & Farm Products','Pet Products','Services','Other'))
 THEN RAISE EXCEPTION 'Invalid date or fee evidence' USING errcode='22023'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('independent-market:'||(c->>'application_url')||day::text,9));
 SELECT * INTO m FROM public.markets WHERE slug=c->>'market_slug' FOR UPDATE;
 IF m.id IS NULL OR m.is_hidden OR m.is_sample OR m.name IS DISTINCT FROM expected->>'name' OR m.city IS DISTINCT FROM expected->>'city' OR m.state IS DISTINCT FROM 'NC'
 THEN RETURN jsonb_build_object('action','skipped','reason','Reviewed market identity missing or protected'); END IF;
 SELECT * INTO old FROM public.vendor_opportunities WHERE application_url=c->>'application_url' AND starts_on=day FOR UPDATE;
 IF old.id IS NOT NULL AND (old.market_id IS DISTINCT FROM m.id OR old.automation_hold OR old.publication<>'published' OR old.verification_policy IS DISTINCT FROM 'independent-market-applications-v1')
 THEN RETURN jsonb_build_object('action','skipped','reason','Existing listing is protected'); END IF;
 IF old.id IS NULL AND c->>'availability'='closed' THEN RETURN jsonb_build_object('action','skipped','reason','Closed intake does not create a new opportunity'); END IF;
 INSERT INTO public.market_occurrences(market_id,starts_on,ends_on,title) VALUES(m.id,day,day,expected->>'name') ON CONFLICT(market_id,starts_on,ends_on) DO NOTHING;
 SELECT id INTO occurrence FROM public.market_occurrences WHERE market_id=m.id AND starts_on=day AND ends_on=day;
 IF old.id IS NULL THEN
  INSERT INTO public.vendor_opportunities(title,market_id,occurrence_id,organizer,city,state,venue,starts_on,ends_on,deadline,application_url,source_url,categories,availability,booth_fee,application_fee,deposit,fee_notes,eligibility,research_notes,publication,verified_at,last_checked_at,review_state,review_reason,verification_policy,schedule_type,category_evidence,automation_hold)
  VALUES(c->>'title',m.id,occurrence,'GRL Market',m.city,'NC',c->>'venue',day,day,NULL,c->>'application_url',c->>'source_url',ARRAY(SELECT jsonb_array_elements_text(c->'categories')),c->>'availability',(c->>'booth_fee')::numeric,NULL,NULL,c->>'fee_notes',c->>'eligibility',c->>'research_notes','published',checked,now(),'verified','','independent-market-applications-v1','dated_event',p_result->'category_evidence',false) RETURNING id INTO opp;
 ELSE
  opp:=old.id;
  UPDATE public.vendor_opportunities SET availability=c->>'availability',review_state=CASE WHEN c->>'availability'='closed' THEN 'closed' ELSE 'verified' END,review_reason='',
   booth_fee=CASE WHEN c->>'availability'='closed' THEN old.booth_fee ELSE (c->>'booth_fee')::numeric END,
   fee_notes=CASE WHEN c->>'availability'='closed' THEN old.fee_notes ELSE c->>'fee_notes' END,
   categories=CASE WHEN c->>'availability'='closed' THEN old.categories ELSE ARRAY(SELECT jsonb_array_elements_text(c->'categories')) END,
   category_evidence=CASE WHEN c->>'availability'='closed' THEN old.category_evidence ELSE p_result->'category_evidence' END,
   eligibility=c->>'eligibility',research_notes=c->>'research_notes',verified_at=checked,last_checked_at=now(),updated_at=now() WHERE id=opp;
 END IF;
 UPDATE btb_private.triangle_discovery_leads SET review_state='resolved',published_opportunity_id=opp,resolved_at=now(),research_reason='Current official calendar and public WorkForm verified.' WHERE target_url=c->>'application_url' AND review_state IN ('new','monitoring');
 INSERT INTO public.btb_research_audit(opportunity_id,action,reason,evidence) VALUES(opp,'publish','Verified independent market application',jsonb_build_object('policy',p_result->>'policy','source_hash',p_result->>'source_hash','form_hash',p_result->>'form_hash','checked_at',checked));
 RETURN jsonb_build_object('action','publish','id',opp);
END; $$;
REVOKE ALL ON FUNCTION public.btb_research_publish_independent_market(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.btb_research_publish_independent_market(jsonb) TO anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION public.btb_research_publish_market_catalog(p_result jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
 catalog constant jsonb := $catalog${"nc-vintage-haven":{"slug":"nc-vintage-market-at-haven-farm","name":"NC Vintage Market at Haven Farm","city":"Knightdale","organizer":"NC Vintage Market","source":"https://www.eventbrite.com/o/nc-vintage-market-121068658483","description":"NC Vintage Market at Haven Farm is a curated vendor market in Knightdale featuring vintage clothing, accessories, jewelry, home goods, and reworked items. Event details and participating vendors vary by edition."},"nc-vintage-bazaar":{"slug":"nc-vintage-bazaar","name":"NC Vintage Bazaar","city":"Raleigh","organizer":"NC Vintage Bazaar","source":"https://ncvintagebazaar.com/","description":"NC Vintage Bazaar is a vintage and secondhand market held at the North Carolina State Fairgrounds in Raleigh. Vendors offer clothing, accessories, and other vintage wearables. Dates and vendor lineups vary by event."},"patchwork-durham":{"slug":"the-patchwork-market","name":"The Patchwork Market","city":"Durham","organizer":"The Patchwork Market","source":"https://thepatchworkmarket.com/applytobeavendor/","description":"The Patchwork Market is a curated vendor market at the Durham Armory featuring handmade goods from local and regional makers. Vendor lineups, booth options, and application periods vary by edition."},"rebus-sunday":{"slug":"rebus-sunday-funday-market","name":"Rebus Sunday Funday Market","city":"Raleigh","organizer":"Rebus Works","source":"https://www.rebusworks.us/sundayfundaymarket","description":"Rebus Sunday Funday Market is a recurring curated market at Rebus Works in Raleigh, featuring small businesses, makers, and vintage sellers. Check the organizer for current dates and vendor participation details."},"raleigh-retro-markets":{"slug":"raleigh-retro-gamers-markets","name":"Raleigh Retro Gamers Markets","city":"Raleigh","organizer":"Raleigh Retro Gamers","source":"https://raleighretrogamers.com/vendors/","description":"Raleigh Retro Gamers organizes gaming and pop-culture vendor markets across Raleigh and the Triangle. Events feature retro and modern games, collectibles, vintage toys, clothing, and related goods. Venues, booth costs, and eligibility vary by event."},"grl-waverly":{"slug":"grl-market-at-waverly-place","name":"GRL Market at Waverly Place","city":"Cary","organizer":"GRL Market","source":"https://grlmarket.com/","description":"GRL Market at Waverly Place is a curated vendor market in Cary, North Carolina, featuring local small businesses. Event dates, product eligibility and application requirements vary by edition."},"grl-transfer":{"slug":"grl-market-at-transfer-food-hall","name":"GRL Market at Transfer Food Hall","city":"Raleigh","organizer":"GRL Market","source":"https://grlmarket.com/","description":"GRL Market at Transfer Food Hall is a curated vendor market in Raleigh, North Carolina, featuring local small businesses. Event dates, product eligibility and application requirements vary by edition."},"grl-seaboard":{"slug":"grl-market-at-seaboard-station","name":"GRL Market at Seaboard Station","city":"Raleigh","organizer":"GRL Market","source":"https://grlmarket.com/","description":"GRL Market at Seaboard Station is a curated vendor market in Raleigh, North Carolina, featuring local small businesses. Event dates, product eligibility and application requirements vary by edition."},"grasshopper-makers":{"slug":"grasshopper-farms-makers-market","name":"Grasshopper Farms Makers Market","city":"Knightdale","organizer":"Grasshopper Farms","source":"https://www.grasshopperfarmsnc.com/special-events","description":"Grasshopper Farms hosts makers markets at its Poole Road farm in Knightdale. Dates include daytime, night and youth-focused editions; participation requirements vary by event."},"midtown-makers":{"slug":"midtown-makers-market","name":"Midtown Makers Market","city":"Raleigh","organizer":"North Hills","source":"https://www.visitnorthhills.com/signature-events/midtown-makers-market","description":"Midtown Makers Market is an evening market in the North Hills Innovation District in Raleigh featuring local makers, artisans and small businesses. Dates and vendor requirements vary by season."},"hartwell-markets":{"slug":"hartwell-makers-markets","name":"Hartwell Makers Markets","city":"Raleigh","organizer":"Hartwell","source":"https://www.hartwellraleigh.com/retail-markets","description":"Hartwell hosts curated makers markets and seasonal vendor events on West South Street in Raleigh. Dates, themes and vendor application windows vary by edition."},"unhinged-markets":{"slug":"unhinged-markets","name":"Unhinged Markets","city":"Knightdale","organizer":"Unhinged Coffee & Co.","source":"https://www.unhingedcoffee.co/","description":"Unhinged Coffee & Co. hosts local vendor markets at its First Avenue location in Knightdale. Event dates, themes and vendor requirements vary by edition."},"krampus-durham":{"slug":"krampus-market-durham","name":"Krampus Market","city":"Durham","organizer":"M.I.N.E. and Trailer Park Fantasy","source":"https://www.eventeny.com/events/krampusmarket-24719/","description":"Krampus Market is an adult-oriented holiday vendor market at Durham Central Park organized by M.I.N.E. and Trailer Park Fantasy. The documented 2025 edition was an 18-and-over event. Future dates and participation requirements require organizer confirmation."}}$catalog$;
 key text:=p_result->>'catalog_key'; expected jsonb; checked timestamptz;
 existing public.markets; action_text text:='existing';
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('action','skipped','reason','Research disabled');end if;
 expected:=catalog->key;
 if expected is null or octet_length(p_result::text)>5000
  or p_result->>'policy' is distinct from 'reviewed-market-catalog-v1'
  or p_result->>'source_url' is distinct from expected->>'source'
  or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
  or length(coalesce(p_result->>'evidence','')) not between 100 and 600
 then raise exception 'Unverified market catalog identity' using errcode='22023';end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 if checked is null or not isfinite(checked) or checked<now()-interval '6 hours' or checked>now()+interval '5 minutes'
 then raise exception 'Stale market catalog evidence' using errcode='22023';end if;
 perform pg_advisory_xact_lock(hashtextextended('market-catalog:'||key,9));
 select * into existing from public.markets m
 where m.slug=expected->>'slug' or (
  lower(m.city)=lower(expected->>'city') and m.state='NC'
  and regexp_replace(lower(m.name),'[^a-z0-9]','','g')=regexp_replace(lower(expected->>'name'),'[^a-z0-9]','','g'))
 order by (m.slug=expected->>'slug') desc limit 1 for update;
 if found then
  if existing.is_hidden or existing.is_sample or existing.city is distinct from expected->>'city'
    or existing.state is distinct from 'NC'
    or regexp_replace(lower(existing.name),'[^a-z0-9]','','g') is distinct from regexp_replace(lower(expected->>'name'),'[^a-z0-9]','','g')
  then return jsonb_build_object('action','skipped','reason','Existing profile is protected or has a conflicting identity');end if;
 else
  insert into public.markets(slug,name,city,state,organizer,description,website_url,is_sample,is_hidden)
  values(expected->>'slug',expected->>'name',expected->>'city','NC',expected->>'organizer',expected->>'description',expected->>'source',false,false)
  returning * into existing;
  action_text:='created';
 end if;
 insert into btb_private.market_catalog_receipts(catalog_key,market_id,source_url,source_hash,checked_at)
 values(key,existing.id,expected->>'source',p_result->>'source_hash',checked)
 on conflict(catalog_key) do update set market_id=excluded.market_id,source_url=excluded.source_url,source_hash=excluded.source_hash,checked_at=excluded.checked_at;
 return jsonb_build_object('action',action_text,'id',existing.id,'slug',existing.slug);
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
    or claimed_host !~ '^[A-Za-z0-9][A-Za-z0-9.-]{3,240}[.](com|org|net|gov|edu|us|co)$'
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
NOTIFY pgrst,'reload schema';


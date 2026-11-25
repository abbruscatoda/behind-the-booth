-- A complete lead may arrive before a newly verified venue's registry commit reaches
-- the worker. Resolve it only to an active source. The worker still independently
-- checks the exact source, venue, dated invitation and intake before publication.
CREATE OR REPLACE FUNCTION public.btb_research_community_context() RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 PERFORM public.btb_research_authorize();
 RETURN jsonb_build_object('leads',coalesce((SELECT jsonb_agg(q.lead) FROM (
  SELECT to_jsonb(i) || jsonb_build_object('source_key',s.source_key) AS lead
  FROM btb_private.community_discovery_inbox i
  JOIN btb_private.community_sources s ON s.source_key=coalesce(i.source_key,i.proposal->>'reviewed_source_key')
  WHERE s.active AND i.state<>'out_of_area' AND i.last_seen>now()-interval '7 days'
  ORDER BY (i.proposal<>'{}' AND i.state='unverified') DESC,(i.proposal<>'{}') DESC,i.last_seen DESC,i.id
  LIMIT 40) q),'[]'));
END; $$;

CREATE OR REPLACE FUNCTION public.btb_research_publish_community_call(p_result jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE c jsonb:=p_result->'candidate';cfg jsonb;checked timestamptz;day date;last_day date;opening date;cutoff date;
 m public.markets;old public.vendor_opportunities;opp uuid;occurrence uuid;receipt jsonb;source_ok boolean:=false;root text;event_url text;inbox_id uuid;
BEGIN
 PERFORM public.btb_research_authorize();
 IF NOT coalesce((SELECT enabled FROM public.btb_research_settings WHERE id),false) THEN RETURN jsonb_build_object('action','skipped','reason','Research disabled');END IF;
 SELECT config INTO cfg FROM btb_private.community_sources WHERE source_key=p_result->>'source_key' AND active;
 IF cfg IS NULL OR cfg->>'publish' IS DISTINCT FROM 'true' OR p_result->>'policy' IS DISTINCT FROM 'reviewed-community-call-v1' OR p_result->>'decision' IS DISTINCT FROM 'publish'
 OR jsonb_typeof(c) IS DISTINCT FROM 'object' OR octet_length(p_result::text)>130000
 OR jsonb_typeof(p_result->'receipts') IS DISTINCT FROM 'array' OR jsonb_array_length(p_result->'receipts') NOT BETWEEN 2 AND 8
 OR c->>'market_slug' IS DISTINCT FROM cfg->>'slug' OR c->>'market_name' IS DISTINCT FROM cfg->>'market_name'
 OR c->>'organizer' IS DISTINCT FROM cfg->>'organizer' OR c->>'city' IS DISTINCT FROM cfg->>'city' OR c->>'state' IS DISTINCT FROM 'NC'
 OR c->>'schedule_type' IS DISTINCT FROM 'dated_event' OR coalesce(c->>'application_method','') NOT IN ('form','email','instagram')
 OR coalesce(c->>'availability','') NOT IN ('open','waitlist','announced','closed') OR coalesce(c->>'application_url','') !~ '^https://[^[:space:]<>@]+$'
 OR length(coalesce(c->>'title','')) NOT BETWEEN 3 AND 160 OR length(coalesce(c->>'venue','')) NOT BETWEEN 5 AND 300
 OR length(coalesce(p_result->>'evidence','')) NOT BETWEEN 100 AND 4000 OR c->>'deadline' IS NOT NULL
 THEN RAISE EXCEPTION 'Unverified community call' USING errcode='22023';END IF;
 checked:=(p_result->>'checked_at')::timestamptz;day:=(c->>'starts_on')::date;last_day:=(c->>'ends_on')::date;opening:=(c->>'opens_on')::date;cutoff:=(c->>'deadline_date')::date;
 IF checked IS NULL OR NOT isfinite(checked) OR checked<now()-interval '6 hours' OR checked>now()+interval '5 minutes'
 OR day IS NULL OR last_day IS NULL OR NOT isfinite(day) OR NOT isfinite(last_day) OR day<(now() AT TIME ZONE 'America/New_York')::date OR day>(now() AT TIME ZONE 'America/New_York')::date+550 OR last_day NOT BETWEEN day AND day+31
 OR (opening IS NOT NULL AND (NOT isfinite(opening) OR opening>day)) OR (cutoff IS NOT NULL AND (NOT isfinite(cutoff) OR cutoff>last_day))
 OR (c->>'availability'='announced' AND (opening IS NULL OR opening<=(now() AT TIME ZONE 'America/New_York')::date))
 OR (c->>'availability' IN ('open','waitlist') AND ((opening IS NOT NULL AND opening>(now() AT TIME ZONE 'America/New_York')::date) OR (cutoff IS NOT NULL AND cutoff<(now() AT TIME ZONE 'America/New_York')::date)))
 OR EXISTS(SELECT 1 FROM jsonb_each(c) e WHERE e.key IN ('booth_fee','application_fee','deposit') AND e.value<>'null' AND (e.value::text::numeric<0 OR e.value::text::numeric>100000))
 THEN RAISE EXCEPTION 'Invalid community dates or fees' USING errcode='22023';END IF;
 IF c->>'application_method'='email' AND (coalesce(c->>'application_contact','') !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,24}$' OR position(lower(c->>'application_contact') in lower(p_result->>'evidence'))=0)
 THEN RAISE EXCEPTION 'Invalid vendor email evidence' USING errcode='22023';END IF;
 IF c->>'application_method'='instagram' AND (NOT (cfg->'instagram' ? coalesce(c->>'application_contact','')) OR c->>'application_url' IS DISTINCT FROM 'https://www.instagram.com/'||(c->>'application_contact')||'/')
 THEN RAISE EXCEPTION 'Invalid organizer message action' USING errcode='22023';END IF;
 event_url:=c->>'source_url';
 FOR receipt IN SELECT value FROM jsonb_array_elements(p_result->'receipts') LOOP
  IF receipt->>'access' IS DISTINCT FROM 'public_read' OR coalesce(receipt->>'sha256','') !~ '^[a-f0-9]{64}$'
  OR length(coalesce(receipt->>'text','')) NOT BETWEEN 20 AND 12000 OR receipt->>'checked_at' IS NULL OR NOT isfinite((receipt->>'checked_at')::timestamptz) OR (receipt->>'checked_at')::timestamptz<now()-interval '6 hours' OR (receipt->>'checked_at')::timestamptz>now()+interval '5 minutes'
  THEN RAISE EXCEPTION 'Stale or incomplete primary-source receipt' USING errcode='22023';END IF;
  IF receipt->>'role'='event' AND receipt->>'url'=event_url THEN
   FOR root IN SELECT jsonb_array_elements_text(cfg->'sources') LOOP
    IF event_url=root OR (position('?' in root)=0 AND event_url LIKE rtrim(root,'/')||'/%') OR (position('?' in root)=0 AND split_part(event_url,'?',1)=root) THEN source_ok:=true;END IF;
   END LOOP;
   IF event_url ~ '^https://(www[.])?instagram[.]com/(p|reel)/[A-Za-z0-9_-]+/?$' AND cfg->'instagram' ? coalesce(receipt->>'owner','') AND position(lower(receipt->>'owner') in lower(receipt->>'text'))>0 THEN source_ok:=true;END IF;
  END IF;
 END LOOP;
 IF c->>'availability'='waitlist' AND NOT EXISTS(
  SELECT 1 FROM jsonb_array_elements(p_result->'receipts') r
  WHERE r->>'role' IN ('application','intake') AND r->>'text' ~* '(wait(ing)?[ -]?list[ -]+only|only (accepting|taking) (applications? (for|to) )?(the )?wait(ing)?[ -]?list)'
 ) THEN RAISE EXCEPTION 'Waitlist-only intake must be explicit' USING errcode='22023';END IF;
 IF NOT source_ok THEN RAISE EXCEPTION 'Community event source is not reviewed' USING errcode='22023';END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('community-call:'||(c->>'application_url')||day::text,9));
 SELECT * INTO m FROM public.markets WHERE slug=cfg->>'slug' OR (city=cfg->>'city' AND regexp_replace(lower(name),'[^a-z0-9]','','g')=regexp_replace(lower(cfg->>'market_name'),'[^a-z0-9]','','g')) ORDER BY (slug=cfg->>'slug') DESC LIMIT 1 FOR UPDATE;
 SELECT * INTO old FROM public.vendor_opportunities WHERE application_url=c->>'application_url' AND starts_on=day LIMIT 1 FOR UPDATE;
 IF old.id IS NOT NULL AND old.market_id IS DISTINCT FROM m.id THEN RETURN jsonb_build_object('action','skipped','reason','Application already belongs to another market');END IF;
 IF m.id IS NOT NULL AND (m.is_hidden OR m.is_sample OR m.city IS DISTINCT FROM cfg->>'city' OR m.state IS DISTINCT FROM 'NC') THEN RETURN jsonb_build_object('action','skipped','reason','Existing market is protected');END IF;
 IF m.id IS NULL THEN
  IF c->>'availability'='closed' THEN RETURN jsonb_build_object('action','skipped','reason','Closed intake does not create a listing');END IF;
  INSERT INTO public.markets(slug,name,organizer,city,state,description,website_url,is_hidden,is_sample)
  VALUES(cfg->>'slug',cfg->>'market_name',cfg->>'organizer',cfg->>'city','NC','Local vendor market. Event dates, products and participation requirements vary by edition.',CASE WHEN (cfg->'sources') ? (cfg->>'market_url') THEN cfg->>'market_url' ELSE event_url END,false,false) RETURNING * INTO m;
 END IF;
 IF old.id IS NULL THEN SELECT * INTO old FROM public.vendor_opportunities WHERE market_id=m.id AND starts_on=day AND ends_on=last_day AND application_method=c->>'application_method' AND application_contact=coalesce(c->>'application_contact','') AND (automation_hold OR publication<>'published' OR (lower(title)=lower(c->>'title') AND lower(venue)=lower(c->>'venue'))) ORDER BY automation_hold DESC,(publication<>'published') DESC LIMIT 1 FOR UPDATE;END IF;
 IF old.id IS NOT NULL AND (old.market_id IS DISTINCT FROM m.id OR old.automation_hold OR old.publication<>'published' OR old.verification_policy IS DISTINCT FROM 'reviewed-community-call-v1') THEN RETURN jsonb_build_object('action','skipped','reason','Existing listing is protected');END IF;
 IF old.id IS NULL AND c->>'availability'='closed' THEN RETURN jsonb_build_object('action','skipped','reason','Closed intake does not create a listing');END IF;
 INSERT INTO public.market_occurrences(market_id,starts_on,ends_on,title) VALUES(m.id,day,last_day,c->>'title') ON CONFLICT(market_id,starts_on,ends_on) DO NOTHING;
 SELECT id INTO occurrence FROM public.market_occurrences WHERE market_id=m.id AND starts_on=day AND ends_on=last_day;
 IF old.id IS NULL THEN
  INSERT INTO public.vendor_opportunities(title,market_id,occurrence_id,organizer,city,state,venue,starts_on,ends_on,deadline,application_url,source_url,categories,availability,booth_fee,application_fee,deposit,fee_notes,eligibility,research_notes,publication,verified_at,last_checked_at,review_state,review_reason,verification_policy,schedule_type,category_evidence,automation_hold,application_method,application_contact,opens_on,deadline_date)
  VALUES(c->>'title',m.id,occurrence,cfg->>'organizer',cfg->>'city','NC',c->>'venue',day,last_day,NULL,c->>'application_url',event_url,'{}',c->>'availability',(c->>'booth_fee')::numeric,(c->>'application_fee')::numeric,(c->>'deposit')::numeric,left(coalesce(c->>'fee_notes',''),2000),left(coalesce(c->>'eligibility',''),2000),left(coalesce(c->>'research_notes',''),4000),'published',checked,now(),'verified','','reviewed-community-call-v1','dated_event','{}',false,c->>'application_method',coalesce(c->>'application_contact',''),opening,cutoff) RETURNING id INTO opp;
 ELSE
  opp:=old.id;
  UPDATE public.vendor_opportunities SET availability=c->>'availability',verified_at=checked,last_checked_at=now(),updated_at=now(),review_state=CASE WHEN c->>'availability'='closed' THEN 'closed' ELSE 'verified' END,
   opens_on=opening,deadline_date=cutoff,application_url=c->>'application_url',source_url=event_url,
   booth_fee=coalesce((c->>'booth_fee')::numeric,old.booth_fee),application_fee=coalesce((c->>'application_fee')::numeric,old.application_fee),deposit=coalesce((c->>'deposit')::numeric,old.deposit),
   fee_notes=CASE WHEN coalesce(c->>'fee_notes','')='' THEN old.fee_notes ELSE left(c->>'fee_notes',2000) END,eligibility=left(coalesce(c->>'eligibility',old.eligibility),2000) WHERE id=opp;
 END IF;
 IF jsonb_typeof(c->'pricing_options')='array' AND jsonb_array_length(c->'pricing_options') BETWEEN 1 AND 12 THEN
  IF EXISTS(SELECT 1 FROM jsonb_array_elements(c->'pricing_options') p WHERE p->>'kind' NOT IN ('booth','application','addon') OR length(coalesce(p->>'label','')) NOT BETWEEN 3 AND 180 OR (p->>'amount')::numeric NOT BETWEEN 0 AND 100000 OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(p_result->'receipts') r WHERE r->>'url'=p->>'source_url' AND r->>'role' IN ('application','fee'))) THEN RAISE EXCEPTION 'Unverified pricing option' USING errcode='22023';END IF;
  INSERT INTO btb_private.community_opportunity_facts(opportunity_id,application_url,source_url,checked_at,fields)
  VALUES(opp,c->>'application_url',event_url,checked,jsonb_build_object('pricing_options',c->'pricing_options','pricing',jsonb_build_object('status','options','summary','Published options have different size or eligibility conditions. Read each option before applying.','source_url',c->>'application_url')))
  ON CONFLICT(opportunity_id) DO UPDATE SET application_url=excluded.application_url,source_url=excluded.source_url,checked_at=excluded.checked_at,fields=excluded.fields;
 END IF;
 FOR inbox_id IN SELECT id FROM btb_private.community_discovery_inbox WHERE coalesce(source_key,proposal->>'reviewed_source_key')=p_result->>'source_key' AND proposal->>'starts_on'=c->>'starts_on' AND proposal->>'application_url'=c->>'application_url' ORDER BY id LOOP
  UPDATE btb_private.community_discovery_inbox i SET source_key=CASE
   WHEN i.source_key IS NULL AND NOT EXISTS (SELECT 1 FROM btb_private.community_discovery_inbox k WHERE k.source_key=p_result->>'source_key' AND k.target_url=i.target_url)
   THEN p_result->>'source_key' ELSE i.source_key END,
   state=CASE WHEN c->>'availability'='closed' THEN 'closed' ELSE 'published' END,opportunity_id=opp,last_checked_at=now(),reason='Verified reviewed organizer, dated event and vendor intake.' WHERE id=inbox_id;
 END LOOP;
 INSERT INTO public.btb_research_audit(opportunity_id,action,reason,evidence) VALUES(opp,'publish','Verified community vendor call',jsonb_build_object('source_key',p_result->>'source_key','source_url',event_url,'checked_at',checked,'method',c->>'application_method','availability',c->>'availability'));
 RETURN jsonb_build_object('action','publish','id',opp);
END; $$;

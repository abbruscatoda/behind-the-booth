-- Public research hints are private. Only the existing secret-authorized worker
-- can publish a source-bound, fresh, reviewed-community receipt.
ALTER TABLE public.vendor_opportunities
 ADD COLUMN application_method text NOT NULL DEFAULT 'form' CHECK(application_method IN ('form','email','instagram')),
 ADD COLUMN application_contact text NOT NULL DEFAULT '' CHECK(length(application_contact)<=254),
 ADD COLUMN opens_on date,
 ADD COLUMN deadline_date date;
ALTER TABLE public.vendor_opportunities DROP CONSTRAINT vendor_opportunities_availability_check;
ALTER TABLE public.vendor_opportunities ADD CONSTRAINT vendor_opportunities_availability_check
 CHECK(availability IN ('open','limited','waitlist','closed','needs_recheck','announced'));

CREATE TABLE btb_private.community_sources(
 source_key text PRIMARY KEY CHECK(source_key ~ '^[a-z0-9-]{3,80}$'),
 config jsonb NOT NULL CHECK(jsonb_typeof(config)='object'),
 active boolean NOT NULL DEFAULT true,updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE btb_private.community_discovery_inbox(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 source_key text REFERENCES btb_private.community_sources(source_key),
 target_url text NOT NULL CHECK(target_url ~ '^https://[^[:space:]<>]+$' AND length(target_url)<=1200),
 title text NOT NULL CHECK(length(title) BETWEEN 3 AND 160),
 notes text NOT NULL DEFAULT '' CHECK(length(notes)<=3000),
 proposal jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(proposal)='object' AND octet_length(proposal::text)<=12000),
 receipts jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(receipts)='array' AND jsonb_array_length(receipts)<=8 AND octet_length(receipts::text)<=100000),
 state text NOT NULL DEFAULT 'unverified' CHECK(state IN ('unverified','published','closed','out_of_area')),
 reason text NOT NULL DEFAULT '' CHECK(length(reason)<=500),
 opportunity_id uuid REFERENCES public.vendor_opportunities(id),
 first_seen timestamptz NOT NULL DEFAULT now(),last_seen timestamptz NOT NULL DEFAULT now(),
 last_checked_at timestamptz,
 UNIQUE NULLS NOT DISTINCT(source_key,target_url)
);
CREATE INDEX community_inbox_source_idx ON btb_private.community_discovery_inbox(source_key,last_seen DESC);
CREATE INDEX community_inbox_opportunity_idx ON btb_private.community_discovery_inbox(opportunity_id);
ALTER TABLE btb_private.community_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE btb_private.community_discovery_inbox ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON btb_private.community_sources,btb_private.community_discovery_inbox FROM PUBLIC,anon,authenticated;
CREATE TABLE btb_private.community_opportunity_facts(
 opportunity_id uuid PRIMARY KEY REFERENCES public.vendor_opportunities(id),
 application_url text NOT NULL,source_url text NOT NULL,checked_at timestamptz NOT NULL,
 fields jsonb NOT NULL CHECK(jsonb_typeof(fields)='object' AND octet_length(fields::text)<=22000)
);
ALTER TABLE btb_private.community_opportunity_facts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON btb_private.community_opportunity_facts FROM PUBLIC,anon,authenticated;
CREATE FUNCTION btb_private.public_community_facts(p_id uuid) RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
 SELECT coalesce((SELECT f.fields FROM btb_private.community_opportunity_facts f JOIN public.vendor_opportunities o ON o.id=f.opportunity_id
 WHERE f.opportunity_id=p_id AND o.application_url=f.application_url AND o.source_url=f.source_url AND o.verified_at=f.checked_at
 AND f.checked_at>now()-interval '7 days' AND o.publication='published' AND public.btb_market_is_visible(o.market_id)),'{}');
$$;
REVOKE ALL ON FUNCTION btb_private.public_community_facts(uuid) FROM PUBLIC,anon,authenticated,service_role;

CREATE FUNCTION public.btb_research_community_sync(p_sources jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE item jsonb;root text;n integer:=0;
BEGIN
 PERFORM public.btb_research_authorize();
 IF NOT coalesce((SELECT enabled FROM public.btb_research_settings WHERE id),false) THEN RETURN jsonb_build_object('paused',true);END IF;
 IF jsonb_typeof(p_sources) IS DISTINCT FROM 'array' OR jsonb_array_length(p_sources) NOT BETWEEN 1 AND 60 OR octet_length(p_sources::text)>60000 THEN RAISE EXCEPTION 'Invalid community watchlist' USING errcode='22023';END IF;
 UPDATE btb_private.community_sources SET active=false;
 FOR item IN SELECT value FROM jsonb_array_elements(p_sources) LOOP
  IF coalesce(item->>'key','') !~ '^[a-z0-9-]{3,80}$' OR coalesce(item->>'slug','') !~ '^[a-z0-9-]{3,160}$'
  OR length(coalesce(item->>'market_name','')) NOT BETWEEN 3 AND 160 OR length(coalesce(item->>'organizer','')) NOT BETWEEN 3 AND 120
  OR coalesce(item->>'city','') NOT IN ('Raleigh','Durham','Cary','Apex','Carrboro','Chapel Hill','Garner','Knightdale','Wake Forest','Rolesville','Holly Springs','Fuquay-Varina','Morrisville','Clayton','Pittsboro','Hillsborough','Zebulon','Wendell','Youngsville','Creedmoor','Angier','Siler City','Mebane','Franklinton')
  OR jsonb_typeof(item->'sources') IS DISTINCT FROM 'array' OR jsonb_typeof(item->'instagram') IS DISTINCT FROM 'array'
  OR jsonb_typeof(item->'venue_terms') IS DISTINCT FROM 'array' OR jsonb_typeof(item->'publish') IS DISTINCT FROM 'boolean'
  THEN RAISE EXCEPTION 'Invalid reviewed community identity' USING errcode='22023';END IF;
  FOR root IN SELECT jsonb_array_elements_text(item->'sources') LOOP
   IF root !~ '^https://[A-Za-z0-9.-]+/[^[:space:]<>@#]*$' OR length(root)>1200 THEN RAISE EXCEPTION 'Invalid reviewed source URL' USING errcode='22023';END IF;
  END LOOP;
  IF EXISTS(SELECT 1 FROM jsonb_array_elements_text(item->'instagram') x WHERE x !~ '^[a-z0-9._]{2,30}$') THEN RAISE EXCEPTION 'Invalid reviewed handle' USING errcode='22023';END IF;
  INSERT INTO btb_private.community_sources(source_key,config,active) VALUES(item->>'key',item,true)
  ON CONFLICT(source_key) DO UPDATE SET config=excluded.config,active=true,updated_at=now();n:=n+1;
 END LOOP;
 RETURN jsonb_build_object('sources',n);
END; $$;

CREATE FUNCTION public.btb_research_community_context() RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 PERFORM public.btb_research_authorize();
 RETURN jsonb_build_object('leads',coalesce((SELECT jsonb_agg(to_jsonb(q)) FROM (
  SELECT i.* FROM btb_private.community_discovery_inbox i JOIN btb_private.community_sources s USING(source_key)
  WHERE s.active AND i.state<>'out_of_area' AND i.last_seen>now()-interval '7 days'
  ORDER BY (i.proposal<>'{}') DESC,i.last_seen DESC LIMIT 40) q),'[]'));
END; $$;

CREATE FUNCTION public.btb_research_community_hints(p_hints jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE h jsonb;n integer:=0;
BEGIN
 PERFORM public.btb_research_authorize();
 IF NOT coalesce((SELECT enabled FROM public.btb_research_settings WHERE id),false) THEN RETURN jsonb_build_object('paused',true);END IF;
 IF jsonb_typeof(p_hints) IS DISTINCT FROM 'array' OR jsonb_array_length(p_hints)>60 OR octet_length(p_hints::text)>100000 THEN RAISE EXCEPTION 'Invalid community hints' USING errcode='22023';END IF;
 FOR h IN SELECT value FROM jsonb_array_elements(p_hints) LOOP
  IF h->>'id' ~ '^[a-f0-9-]{36}$' AND h ? 'reason' THEN
   UPDATE btb_private.community_discovery_inbox SET reason=left(h->>'reason',500),last_checked_at=now() WHERE id=(h->>'id')::uuid;
   CONTINUE;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM btb_private.community_sources s WHERE s.source_key=h->>'source_key' AND s.active)
   OR coalesce(h->>'target_url','') !~ '^https://[^[:space:]<>]+$' OR length(h->>'target_url')>1200 OR length(coalesce(h->>'title','')) NOT BETWEEN 3 AND 160 THEN CONTINUE;END IF;
  INSERT INTO btb_private.community_discovery_inbox(source_key,target_url,title,notes)
  VALUES(h->>'source_key',h->>'target_url',h->>'title',left(coalesce(h->>'notes',''),3000))
  ON CONFLICT(source_key,target_url) DO UPDATE SET last_seen=now(),notes=CASE WHEN btb_private.community_discovery_inbox.proposal='{}' THEN excluded.notes ELSE btb_private.community_discovery_inbox.notes END;
  n:=n+1;
 END LOOP;
 RETURN jsonb_build_object('hints',n);
END; $$;

CREATE FUNCTION public.btb_research_publish_community_call(p_result jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE c jsonb:=p_result->'candidate';cfg jsonb;checked timestamptz;day date;last_day date;opening date;cutoff date;
 m public.markets;old public.vendor_opportunities;opp uuid;occurrence uuid;receipt jsonb;source_ok boolean:=false;root text;event_url text;
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
 OR coalesce(c->>'availability','') NOT IN ('open','announced','closed') OR coalesce(c->>'application_url','') !~ '^https://[^[:space:]<>@]+$'
 OR length(coalesce(c->>'title','')) NOT BETWEEN 3 AND 160 OR length(coalesce(c->>'venue','')) NOT BETWEEN 5 AND 300
 OR length(coalesce(p_result->>'evidence','')) NOT BETWEEN 100 AND 4000 OR c->>'deadline' IS NOT NULL
 THEN RAISE EXCEPTION 'Unverified community call' USING errcode='22023';END IF;
 checked:=(p_result->>'checked_at')::timestamptz;day:=(c->>'starts_on')::date;last_day:=(c->>'ends_on')::date;opening:=(c->>'opens_on')::date;cutoff:=(c->>'deadline_date')::date;
 IF checked IS NULL OR NOT isfinite(checked) OR checked<now()-interval '6 hours' OR checked>now()+interval '5 minutes'
 OR day IS NULL OR last_day IS NULL OR NOT isfinite(day) OR NOT isfinite(last_day) OR day<(now() AT TIME ZONE 'America/New_York')::date OR day>(now() AT TIME ZONE 'America/New_York')::date+550 OR last_day NOT BETWEEN day AND day+31
 OR (opening IS NOT NULL AND (NOT isfinite(opening) OR opening>day)) OR (cutoff IS NOT NULL AND (NOT isfinite(cutoff) OR cutoff>last_day))
 OR (c->>'availability'='announced' AND (opening IS NULL OR opening<=(now() AT TIME ZONE 'America/New_York')::date))
 OR (c->>'availability'='open' AND ((opening IS NOT NULL AND opening>(now() AT TIME ZONE 'America/New_York')::date) OR (cutoff IS NOT NULL AND cutoff<(now() AT TIME ZONE 'America/New_York')::date)))
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
 IF NOT source_ok THEN RAISE EXCEPTION 'Community event source is not reviewed' USING errcode='22023';END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('community-call:'||(c->>'application_url')||day::text,9));
 SELECT * INTO m FROM public.markets WHERE slug=cfg->>'slug' OR (city=cfg->>'city' AND regexp_replace(lower(name),'[^a-z0-9]','','g')=regexp_replace(lower(cfg->>'market_name'),'[^a-z0-9]','','g')) ORDER BY (slug=cfg->>'slug') DESC LIMIT 1 FOR UPDATE;
 IF m.id IS NOT NULL AND (m.is_hidden OR m.is_sample OR m.city IS DISTINCT FROM cfg->>'city' OR m.state IS DISTINCT FROM 'NC') THEN RETURN jsonb_build_object('action','skipped','reason','Existing market is protected');END IF;
 IF m.id IS NULL THEN
  IF c->>'availability'='closed' THEN RETURN jsonb_build_object('action','skipped','reason','Closed intake does not create a listing');END IF;
  INSERT INTO public.markets(slug,name,organizer,city,state,description,website_url,is_hidden,is_sample)
  VALUES(cfg->>'slug',cfg->>'market_name',cfg->>'organizer',cfg->>'city','NC','Local vendor market. Event dates, products and participation requirements vary by edition.',event_url,false,false) RETURNING * INTO m;
 END IF;
 SELECT * INTO old FROM public.vendor_opportunities WHERE application_url=c->>'application_url' AND starts_on=day LIMIT 1 FOR UPDATE;
 IF old.id IS NULL THEN SELECT * INTO old FROM public.vendor_opportunities WHERE market_id=m.id AND starts_on=day AND ends_on=last_day AND application_method=c->>'application_method' AND application_contact=coalesce(c->>'application_contact','') LIMIT 1 FOR UPDATE;END IF;
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
 UPDATE btb_private.community_discovery_inbox SET state=CASE WHEN c->>'availability'='closed' THEN 'closed' ELSE 'published' END,opportunity_id=opp,last_checked_at=now(),reason='Verified reviewed organizer, dated event and vendor intake.' WHERE source_key=p_result->>'source_key' AND proposal->>'starts_on'=c->>'starts_on' AND proposal->>'application_url'=c->>'application_url';
 INSERT INTO public.btb_research_audit(opportunity_id,action,reason,evidence) VALUES(opp,'publish','Verified community vendor call',jsonb_build_object('source_key',p_result->>'source_key','source_url',event_url,'checked_at',checked,'method',c->>'application_method','availability',c->>'availability'));
 RETURN jsonb_build_object('action','publish','id',opp);
END; $$;

REVOKE ALL ON FUNCTION public.btb_research_community_sync(jsonb),public.btb_research_community_context(),public.btb_research_community_hints(jsonb),public.btb_research_publish_community_call(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.btb_research_community_sync(jsonb),public.btb_research_community_context(),public.btb_research_community_hints(jsonb),public.btb_research_publish_community_call(jsonb) TO anon,authenticated,service_role;

CREATE FUNCTION public.btb_admin_community_discovery() RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 IF NOT coalesce(public.btb_is_admin(),false) THEN RAISE EXCEPTION 'Admin access required' USING errcode='42501';END IF;
 RETURN jsonb_build_object('sources',coalesce((SELECT jsonb_agg(config ORDER BY source_key) FROM btb_private.community_sources WHERE active),'[]'),
 'leads',coalesce((SELECT jsonb_agg(to_jsonb(q)) FROM (SELECT id,source_key,target_url,title,notes,state,reason,first_seen,last_seen,last_checked_at,opportunity_id FROM btb_private.community_discovery_inbox ORDER BY last_seen DESC LIMIT 60) q),'[]'));
END; $$;
REVOKE ALL ON FUNCTION public.btb_admin_community_discovery() FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.btb_admin_community_discovery() TO authenticated,service_role;

CREATE OR REPLACE FUNCTION btb_private.full_opportunities(p_market_id uuid DEFAULT NULL::uuid, p_offset integer DEFAULT 0)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare items jsonb; total bigint;
begin
 if p_offset is null or p_offset<0 then raise exception 'Invalid offset.'; end if;
 select count(*) into total from public.vendor_opportunities o where public.btb_market_is_visible(o.market_id) and publication='published' and ends_on >= (now() at time zone 'America/New_York')::date and (p_market_id is null or market_id=p_market_id);
 select coalesce(jsonb_agg(to_jsonb(q) order by q.starts_on,q.id),'[]'::jsonb) into items from (
 select o.id,o.title,o.schedule_type,o.application_method,o.application_contact,o.opens_on,o.deadline_date,o.organizer,o.city,o.state,o.venue,o.starts_on,o.ends_on,o.deadline,o.application_url,o.source_url,
 case when o.category_evidence ? 'checked_at' then array(select e.key from jsonb_each(btb_private.public_category_evidence(o.application_url,o.category_evidence)) e where e.value->>'status'='eligible' order by e.key) else o.categories end as categories,
 btb_private.public_category_evidence(o.application_url,o.category_evidence) as category_evidence,
 btb_private.public_research_coverage(o.id,o.application_url,o.source_url,o.verified_at,o.review_state) as research_coverage,
 coalesce(btb_private.public_opportunity_facts(o.id),'{}') || btb_private.public_community_facts(o.id) as field_facts,o.published_at,o.booth_fee,o.application_fee,o.deposit,o.fee_notes,o.eligibility,o.verified_at,o.occurrence_id,o.market_id,m.slug as market_slug,
 case when o.deadline_date < (now() at time zone 'America/New_York')::date then 'closed' when o.availability='announced' and o.opens_on <= (now() at time zone 'America/New_York')::date then 'needs_recheck' when (btb_private.public_opportunity_facts(o.id)->'deadline'->>'date')::date < (now() at time zone 'America/New_York')::date then 'closed' else public.btb_opportunity_state(o.availability,o.deadline,o.verified_at,o.ends_on) end as effective_status,
 public.btb_market_history_stats(o.market_id) as history
 from public.vendor_opportunities o join public.markets m on m.id=o.market_id
 where public.btb_market_is_visible(o.market_id) and o.publication='published' and o.ends_on >= (now() at time zone 'America/New_York')::date and (p_market_id is null or o.market_id=p_market_id)
 order by o.starts_on,o.id limit 100 offset p_offset) q;
 return jsonb_build_object('items',items,'total',total);
end; $function$;


CREATE OR REPLACE FUNCTION public.btb_public_opportunities(p_market_id uuid DEFAULT NULL::uuid, p_offset integer DEFAULT 0)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE result jsonb; example_id text; entry jsonb; output jsonb := '[]'; prices jsonb; evidence jsonb;
member boolean := coalesce(nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'role','')='service_role'
 OR (auth.uid() IS NOT NULL AND coalesce(auth.jwt()->>'is_anonymous','false')<>'true'
 AND EXISTS(SELECT 1 FROM auth.users u WHERE u.id=auth.uid() AND u.email_confirmed_at IS NOT NULL
 AND u.deleted_at IS NULL AND (u.banned_until IS NULL OR u.banned_until<now())));
BEGIN
 result := btb_private.full_opportunities(p_market_id,p_offset);
 IF NOT member THEN
  SELECT e->>'id' INTO example_id FROM jsonb_array_elements(btb_private.full_opportunities(NULL,0)->'items') e
  WHERE e->>'effective_status' IN ('open','limited','waitlist')
  ORDER BY CASE e->>'effective_status' WHEN 'open' THEN 0 WHEN 'limited' THEN 1 ELSE 2 END,e->>'starts_on',e->>'id' LIMIT 1;
 END IF;
 FOR entry IN SELECT value FROM jsonb_array_elements(result->'items') LOOP
  IF member OR entry->>'id'=example_id THEN
   output := output || jsonb_build_array(entry || jsonb_build_object('access',CASE WHEN member THEN 'full' ELSE 'example' END));
  ELSE
   SELECT coalesce(jsonb_agg((p-'source_url')||jsonb_build_object('source_url','',
    'conditions',regexp_replace(coalesce(p->>'conditions',''),'https?://[^[:space:]<>]+','[source available with a free account]','g'))),'[]')
   INTO prices FROM jsonb_array_elements(coalesce(entry->'field_facts'->'pricing_options','[]')) p WHERE p->>'kind'='booth';
   SELECT coalesce(jsonb_object_agg(key,jsonb_build_object('status',value->>'status','checked_at',value->>'checked_at',
    'application_state',value->>'application_state','application_deadline',value->>'application_deadline','note','','source_url','')),'{}')
   INTO evidence FROM jsonb_each(coalesce(entry->'category_evidence','{}'));
   output := output || jsonb_build_array(jsonb_build_object(
    'access','preview','id',entry->'id','title',entry->'title','organizer',entry->'organizer',
    'city',entry->'city','state',entry->'state','venue','','starts_on',entry->'starts_on','ends_on',entry->'ends_on',
    'opens_on',entry->'opens_on','schedule_type',entry->'schedule_type','effective_status',entry->'effective_status','market_id',entry->'market_id',
    'market_slug',entry->'market_slug','occurrence_id',entry->'occurrence_id','published_at',entry->'published_at',
    'booth_fee',entry->'booth_fee','categories',entry->'categories','category_evidence',evidence,'verified_at',entry->'verified_at',
    'history',entry->'history','deadline',NULL,'application_url','','source_url','','application_fee',NULL,'deposit',NULL,'eligibility','',
    'fee_notes',coalesce(substring(entry->>'fee_notes' from '(?i)Table options: half table \$[0-9,.]+; full table \$[0-9,.]+\.'),'')
     || CASE WHEN entry->>'fee_notes' ~* 'displayed (booth price|\$[0-9.]+) is the winter rate'
      THEN ' Displayed booth price is the winter rate. Seasonal rates vary; see full details.' ELSE '' END,
    'field_facts',jsonb_build_object('pricing_options',prices,'categories',coalesce(entry->'field_facts'->'categories','[]'),
      'pricing',jsonb_build_object('status',entry->'field_facts'->'pricing'->>'status','summary','Published booth pricing. Full costs and eligibility are available with a free account.','source_url',''))
   ));
  END IF;
 END LOOP;
 RETURN jsonb_build_object('items',output,'total',result->'total','is_member',member,'example_id',example_id,
 'vendor_status',CASE WHEN member THEN (SELECT verification_status FROM public.vendor_profiles WHERE user_id=auth.uid()) ELSE NULL END);
END; $function$;


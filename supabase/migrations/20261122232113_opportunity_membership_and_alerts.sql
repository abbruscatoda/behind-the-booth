-- Full opportunity access is available immediately to signed-in members.
-- The single public example is selected globally, independent of filtering/pagination.
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
 select o.id,o.title,o.schedule_type,o.organizer,o.city,o.state,o.venue,o.starts_on,o.ends_on,o.deadline,o.application_url,o.source_url,
 case when o.category_evidence ? 'checked_at' then array(select e.key from jsonb_each(btb_private.public_category_evidence(o.application_url,o.category_evidence)) e where e.value->>'status'='eligible' order by e.key) else o.categories end as categories,
 btb_private.public_category_evidence(o.application_url,o.category_evidence) as category_evidence,
 btb_private.public_research_coverage(o.id,o.application_url,o.source_url,o.verified_at,o.review_state) as research_coverage,
 btb_private.public_opportunity_facts(o.id) as field_facts,o.published_at,o.booth_fee,o.application_fee,o.deposit,o.fee_notes,o.eligibility,o.verified_at,o.occurrence_id,o.market_id,m.slug as market_slug,
 case when (btb_private.public_opportunity_facts(o.id)->'deadline'->>'date')::date < (now() at time zone 'America/New_York')::date then 'closed' else public.btb_opportunity_state(o.availability,o.deadline,o.verified_at,o.ends_on) end as effective_status,
 public.btb_market_history_stats(o.market_id) as history
 from public.vendor_opportunities o join public.markets m on m.id=o.market_id
 where public.btb_market_is_visible(o.market_id) and o.publication='published' and o.ends_on >= (now() at time zone 'America/New_York')::date and (p_market_id is null or o.market_id=p_market_id)
 order by o.starts_on,o.id limit 100 offset p_offset) q;
 return jsonb_build_object('items',items,'total',total);
end; $function$;

REVOKE ALL ON FUNCTION btb_private.full_opportunities(uuid, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION btb_private.full_opportunities(uuid, integer) TO service_role;

CREATE OR REPLACE FUNCTION public.btb_public_opportunities(p_market_id uuid DEFAULT NULL, p_offset integer DEFAULT 0)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
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
    'schedule_type',entry->'schedule_type','effective_status',entry->'effective_status','market_id',entry->'market_id',
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
END; $$;
REVOKE ALL ON FUNCTION public.btb_public_opportunities(uuid,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.btb_public_opportunities(uuid,integer) TO anon,authenticated,service_role;
COMMENT ON FUNCTION public.btb_public_opportunities(uuid,integer) IS 'Public summaries and one globally selected full example; confirmed members receive complete listings.';

CREATE TABLE public.opportunity_alert_preferences(
 user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
 new_matches boolean NOT NULL DEFAULT false, deadline_reminders boolean NOT NULL DEFAULT false,
 cities text[] NOT NULL DEFAULT '{}', categories text[] NOT NULL DEFAULT '{}',
 include_unconfirmed boolean NOT NULL DEFAULT false,
 requested_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 last_checked_at timestamptz, last_sent_at timestamptz,
 unsubscribe_token uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
 CONSTRAINT alert_cities_valid CHECK(cardinality(cities)<=25 AND array_position(cities,NULL) IS NULL AND NOT(''=ANY(cities)) AND char_length(array_to_string(cities,''))<=2000),
 CONSTRAINT alert_categories_valid CHECK(cardinality(categories)<=11 AND array_position(categories,NULL) IS NULL AND categories <@ ARRAY['Food & Beverages','Food Trucks','Art & Photography','Handmade Crafts','Jewelry & Accessories','Clothing & Vintage','Bath, Body & Beauty','Plants & Farm Products','Pet Products','Services','Other']::text[])
);
ALTER TABLE public.opportunity_alert_preferences ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.opportunity_alert_preferences FROM PUBLIC,anon,authenticated;
GRANT SELECT(user_id,new_matches,deadline_reminders,cities,categories,include_unconfirmed,updated_at,last_sent_at) ON public.opportunity_alert_preferences TO authenticated;
GRANT INSERT(user_id,new_matches,deadline_reminders,cities,categories,include_unconfirmed),
 UPDATE(new_matches,deadline_reminders,cities,categories,include_unconfirmed) ON public.opportunity_alert_preferences TO authenticated;
GRANT ALL ON public.opportunity_alert_preferences TO service_role;
CREATE INDEX opportunity_alert_opt_ins ON public.opportunity_alert_preferences(last_checked_at,user_id) WHERE new_matches OR deadline_reminders;
CREATE POLICY own_alerts_read ON public.opportunity_alert_preferences FOR SELECT TO authenticated USING((SELECT auth.uid())=user_id);
CREATE POLICY own_alerts_insert ON public.opportunity_alert_preferences FOR INSERT TO authenticated WITH CHECK((SELECT auth.uid())=user_id);
CREATE POLICY own_alerts_update ON public.opportunity_alert_preferences FOR UPDATE TO authenticated USING((SELECT auth.uid())=user_id) WITH CHECK((SELECT auth.uid())=user_id);

CREATE FUNCTION btb_private.touch_opportunity_alert_preferences() RETURNS trigger LANGUAGE plpgsql SET search_path='' AS $$
BEGIN
 IF TG_OP='INSERT' OR (NEW.new_matches,NEW.deadline_reminders,NEW.cities,NEW.categories,NEW.include_unconfirmed)
  IS DISTINCT FROM (OLD.new_matches,OLD.deadline_reminders,OLD.cities,OLD.categories,OLD.include_unconfirmed) THEN
  NEW.updated_at:=now(); NEW.requested_at:=now(); NEW.last_checked_at:=NULL; NEW.unsubscribe_token:=gen_random_uuid();
 END IF;
 RETURN NEW;
END; $$;
REVOKE ALL ON FUNCTION btb_private.touch_opportunity_alert_preferences() FROM PUBLIC,anon,authenticated;
CREATE TRIGGER touch_opportunity_alert_preferences BEFORE INSERT OR UPDATE ON public.opportunity_alert_preferences FOR EACH ROW EXECUTE FUNCTION btb_private.touch_opportunity_alert_preferences();

CREATE FUNCTION public.btb_my_opportunity_alerts() RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path='' AS $$
DECLARE result jsonb;
BEGIN
 IF auth.uid() IS NULL THEN RAISE EXCEPTION 'Sign in required.' USING errcode='42501';END IF;
 SELECT jsonb_build_object('new_matches',new_matches,'deadline_reminders',deadline_reminders,'cities',cities,
 'categories',categories,'include_unconfirmed',include_unconfirmed,'last_sent_at',last_sent_at) INTO result
 FROM public.opportunity_alert_preferences WHERE user_id=auth.uid();
 RETURN result;
END; $$;
CREATE FUNCTION public.btb_save_opportunity_alerts(p_new_matches boolean,p_deadline_reminders boolean,p_cities text[],p_categories text[],p_include_unconfirmed boolean)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN
 IF auth.uid() IS NULL OR coalesce(auth.jwt()->>'is_anonymous','false')='true' THEN RAISE EXCEPTION 'Sign in required.' USING errcode='42501';END IF;
 IF p_new_matches IS NULL OR p_deadline_reminders IS NULL OR p_include_unconfirmed IS NULL OR p_cities IS NULL OR p_categories IS NULL
 OR EXISTS(SELECT 1 FROM unnest(p_cities) c WHERE c IS NULL OR c<>btrim(c) OR char_length(c) NOT BETWEEN 1 AND 80) THEN
 RAISE EXCEPTION 'Invalid alert preferences.' USING errcode='22023';END IF;
 INSERT INTO public.opportunity_alert_preferences(user_id,new_matches,deadline_reminders,cities,categories,include_unconfirmed)
 VALUES(auth.uid(),p_new_matches,p_deadline_reminders,ARRAY(SELECT DISTINCT unnest(p_cities) ORDER BY 1),
 ARRAY(SELECT DISTINCT unnest(p_categories) ORDER BY 1),p_include_unconfirmed)
 ON CONFLICT(user_id) DO UPDATE SET new_matches=excluded.new_matches,deadline_reminders=excluded.deadline_reminders,
 cities=excluded.cities,categories=excluded.categories,include_unconfirmed=excluded.include_unconfirmed;
 RETURN public.btb_my_opportunity_alerts();
END; $$;
REVOKE ALL ON FUNCTION public.btb_my_opportunity_alerts(),public.btb_save_opportunity_alerts(boolean,boolean,text[],text[],boolean) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.btb_my_opportunity_alerts(),public.btb_save_opportunity_alerts(boolean,boolean,text[],text[],boolean) TO authenticated,service_role;

-- Delivery state is private. Users cannot enqueue mail or choose recipients.
CREATE TABLE btb_private.opportunity_alert_deliveries(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
 delivery_day date NOT NULL DEFAULT (now() AT TIME ZONE 'America/New_York')::date,
 state text NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','sending','sent','skipped','expired')),
 created_at timestamptz NOT NULL DEFAULT now(), lease_until timestamptz,claim_token uuid,
 attempts integer NOT NULL DEFAULT 0, entries jsonb NOT NULL, preference_token uuid NOT NULL,
 payload jsonb, resend_id text, sent_at timestamptz, UNIQUE(user_id,delivery_day)
);
CREATE TABLE btb_private.opportunity_alert_receipts(
 user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
 opportunity_id uuid NOT NULL REFERENCES public.vendor_opportunities(id) ON DELETE CASCADE,
 kind text NOT NULL CHECK(kind IN ('new','deadline')),fingerprint text NOT NULL,sent_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(user_id,opportunity_id,kind,fingerprint)
);
ALTER TABLE btb_private.opportunity_alert_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE btb_private.opportunity_alert_receipts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON btb_private.opportunity_alert_deliveries,btb_private.opportunity_alert_receipts FROM PUBLIC,anon,authenticated;
GRANT USAGE ON SCHEMA btb_private TO service_role;
GRANT ALL ON btb_private.opportunity_alert_deliveries,btb_private.opportunity_alert_receipts TO service_role;
CREATE POLICY service_alert_deliveries ON btb_private.opportunity_alert_deliveries FOR ALL TO service_role USING(true) WITH CHECK(true);
CREATE POLICY service_alert_receipts ON btb_private.opportunity_alert_receipts FOR ALL TO service_role USING(true) WITH CHECK(true);

CREATE FUNCTION btb_private.alert_opportunity_items() RETURNS SETOF jsonb LANGUAGE plpgsql STABLE SET search_path='' AS $$
DECLARE batch jsonb; offset_count integer:=0;
BEGIN LOOP
 batch:=btb_private.full_opportunities(NULL,offset_count);
 RETURN QUERY SELECT value FROM jsonb_array_elements(batch->'items');
 offset_count:=offset_count+100;
 EXIT WHEN offset_count >= (batch->>'total')::integer OR jsonb_array_length(batch->'items')=0;
END LOOP;END; $$;

CREATE FUNCTION btb_private.alert_category_status(item jsonb,category text) RETURNS text LANGUAGE sql STABLE SET search_path='' AS $$
 SELECT CASE WHEN item->'category_evidence'->category->>'checked_at' IS NOT NULL
 AND (item->'category_evidence'->category->>'checked_at')::timestamptz BETWEEN now()-interval '7 days' AND now()
 THEN CASE WHEN item->'category_evidence'->category->>'application_deadline' IS NOT NULL
  AND (item->'category_evidence'->category->>'application_deadline')::timestamptz <= now() THEN 'unavailable'
  ELSE item->'category_evidence'->category->>'status' END
 WHEN coalesce(item->'categories','[]') ? category OR coalesce(item->'field_facts'->'categories','[]') ? category THEN 'eligible'
 ELSE 'unknown' END;
$$;
CREATE FUNCTION btb_private.alert_deadline_date(item jsonb) RETURNS date LANGUAGE plpgsql STABLE SET search_path='' AS $$
DECLARE cutoff date;
BEGIN
 IF item->'field_facts'->'deadline'->>'status'='date_only' THEN cutoff:=(item->'field_facts'->'deadline'->>'date')::date;
 ELSIF item->>'deadline' IS NOT NULL AND coalesce(item->>'fee_notes','') !~* '\mseries\M[^.!?]*\mdeadline\M'
  AND coalesce(item->'research_coverage'->'deadline'->>'status','')<>'unconfirmed'
 THEN cutoff:=((item->>'deadline')::timestamptz AT TIME ZONE 'America/New_York')::date;
 END IF;
 IF coalesce(item->>'schedule_type','dated_event')='dated_event' AND cutoff>(item->>'starts_on')::date THEN RETURN NULL;END IF;
 RETURN cutoff;
EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow THEN RETURN NULL;
END; $$;

-- Auth records are not exposed or broadly granted to the service database role.
CREATE FUNCTION btb_private.can_receive_opportunity_alerts(p_user_id uuid) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
 SELECT EXISTS(SELECT 1 FROM auth.users u WHERE u.id=p_user_id AND u.email_confirmed_at IS NOT NULL AND u.deleted_at IS NULL AND (u.banned_until IS NULL OR u.banned_until<now()));
$$;
REVOKE ALL ON FUNCTION btb_private.can_receive_opportunity_alerts(uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION btb_private.can_receive_opportunity_alerts(uuid) TO service_role;
CREATE FUNCTION public.btb_due_opportunity_alerts() RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT coalesce(jsonb_agg(user_id),'[]') FROM(
 SELECT p.user_id FROM public.opportunity_alert_preferences p
 WHERE (p.new_matches OR p.deadline_reminders) AND btb_private.can_receive_opportunity_alerts(p.user_id)
 AND (p.last_sent_at IS NULL OR (p.last_sent_at AT TIME ZONE 'America/New_York')::date<(now() AT TIME ZONE 'America/New_York')::date)
 AND (p.last_checked_at IS NULL OR p.last_checked_at<now()-interval '1 hour')
 AND NOT EXISTS(SELECT 1 FROM btb_private.opportunity_alert_deliveries j WHERE j.user_id=p.user_id
 AND j.delivery_day=(now() AT TIME ZONE 'America/New_York')::date AND j.state IN ('sent','skipped','expired'))
 ORDER BY p.last_checked_at NULLS FIRST,p.user_id LIMIT 10) q;
$$;

CREATE FUNCTION public.btb_claim_opportunity_alert(p_user_id uuid) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE pref public.opportunity_alert_preferences%rowtype; job btb_private.opportunity_alert_deliveries%rowtype;
 entries jsonb; today date:=(now() AT TIME ZONE 'America/New_York')::date;
BEGIN
 SELECT * INTO pref FROM public.opportunity_alert_preferences WHERE user_id=p_user_id FOR UPDATE;
 IF NOT FOUND OR NOT(pref.new_matches OR pref.deadline_reminders) THEN RETURN NULL;END IF;
 IF pref.last_sent_at IS NOT NULL AND (pref.last_sent_at AT TIME ZONE 'America/New_York')::date>=today THEN RETURN NULL;END IF;
 UPDATE public.opportunity_alert_preferences SET last_checked_at=now() WHERE user_id=p_user_id;
 SELECT * INTO job FROM btb_private.opportunity_alert_deliveries WHERE user_id=p_user_id
 AND (delivery_day=today OR (state IN ('pending','sending') AND created_at>now()-interval '20 hours')) ORDER BY created_at LIMIT 1 FOR UPDATE;
 IF FOUND THEN
  IF job.state IN ('sent','skipped','expired') OR job.lease_until>now() THEN RETURN NULL;END IF;
  IF job.created_at<now()-interval '20 hours' OR job.attempts>=4 THEN
   UPDATE btb_private.opportunity_alert_deliveries SET state='expired' WHERE id=job.id; RETURN NULL;
  END IF;
 ELSE
  WITH candidates AS (
   SELECT item,btb_private.alert_deadline_date(item) AS deadline_date FROM btb_private.alert_opportunity_items() item
   WHERE item->>'effective_status' IN ('open','limited','waitlist')
  ), eligible AS (
   SELECT 'new'::text AS kind,item,'published:'||(item->>'published_at') AS fingerprint FROM candidates
   WHERE pref.new_matches AND (item->>'published_at')::timestamptz BETWEEN pref.requested_at AND now()
   AND (cardinality(pref.cities)=0 OR item->>'city'=ANY(pref.cities))
   AND (cardinality(pref.categories)=0 OR EXISTS(SELECT 1 FROM unnest(pref.categories) c
    WHERE btb_private.alert_category_status(item,c)='eligible' OR (pref.include_unconfirmed AND btb_private.alert_category_status(item,c)='unknown')))
   UNION ALL
   SELECT 'deadline',item,'deadline:'||CASE WHEN item->'field_facts'->'deadline'->>'status'='date_only' THEN deadline_date::text ELSE item->>'deadline' END FROM candidates
   WHERE pref.deadline_reminders AND deadline_date BETWEEN today AND today+3
   AND EXISTS(SELECT 1 FROM public.saved_opportunities s WHERE s.user_id=p_user_id AND s.opportunity_id=(item->>'id')::uuid)
  )
  SELECT coalesce(jsonb_agg(jsonb_build_object('kind',kind,'item',item,'fingerprint',fingerprint)),'[]') INTO entries FROM (
   SELECT * FROM eligible e WHERE NOT EXISTS(SELECT 1 FROM btb_private.opportunity_alert_receipts r
    WHERE r.user_id=p_user_id AND r.opportunity_id=(e.item->>'id')::uuid AND r.kind=e.kind AND r.fingerprint=e.fingerprint)
   ORDER BY kind,item->>'starts_on',item->>'id' LIMIT 20) q;
  IF jsonb_array_length(entries)=0 THEN RETURN NULL;END IF;
  INSERT INTO btb_private.opportunity_alert_deliveries(user_id,entries,preference_token)
   VALUES(p_user_id,entries,pref.unsubscribe_token) RETURNING * INTO job;
 END IF;
 IF job.preference_token<>pref.unsubscribe_token THEN
  UPDATE btb_private.opportunity_alert_deliveries SET state='skipped' WHERE id=job.id;RETURN NULL;
 END IF;
 UPDATE btb_private.opportunity_alert_deliveries SET state='sending',claim_token=gen_random_uuid(),lease_until=now()+interval '5 minutes',attempts=attempts+1
 WHERE id=job.id RETURNING * INTO job;
 RETURN jsonb_build_object('id',job.id,'user_id',job.user_id,'claim_token',job.claim_token,'entries',job.entries,'payload',job.payload,'unsubscribe_token',pref.unsubscribe_token);
END; $$;

CREATE FUNCTION public.btb_prepare_opportunity_alert(p_id uuid,p_token uuid,p_payload jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE result jsonb;
BEGIN
 UPDATE btb_private.opportunity_alert_deliveries j SET payload=coalesce(j.payload,p_payload)
 FROM public.opportunity_alert_preferences p WHERE j.id=p_id AND j.claim_token=p_token AND j.state='sending'
 AND j.lease_until>now() AND p.user_id=j.user_id AND p.unsubscribe_token=j.preference_token AND (p.new_matches OR p.deadline_reminders)
 RETURNING j.payload INTO result;
 RETURN result;
END; $$;
CREATE FUNCTION public.btb_finish_opportunity_alert(p_id uuid,p_token uuid,p_state text,p_resend_id text DEFAULT NULL)
RETURNS void LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE job btb_private.opportunity_alert_deliveries%rowtype;
BEGIN
 IF p_state NOT IN ('sent','skipped','failed') THEN RAISE EXCEPTION 'Invalid delivery state.';END IF;
 SELECT * INTO job FROM btb_private.opportunity_alert_deliveries WHERE id=p_id AND claim_token=p_token AND state='sending' FOR UPDATE;
 IF NOT FOUND THEN RETURN;END IF;
 IF p_state='sent' THEN
  INSERT INTO btb_private.opportunity_alert_receipts(user_id,opportunity_id,kind,fingerprint)
  SELECT job.user_id,(entry->'item'->>'id')::uuid,entry->>'kind',entry->>'fingerprint' FROM jsonb_array_elements(job.entries) entry ON CONFLICT DO NOTHING;
  UPDATE public.opportunity_alert_preferences SET last_sent_at=now() WHERE user_id=job.user_id;
 END IF;
 UPDATE btb_private.opportunity_alert_deliveries SET state=CASE WHEN p_state='failed' THEN 'pending' ELSE p_state END,
 lease_until=NULL,resend_id=p_resend_id,sent_at=CASE WHEN p_state='sent' THEN now() ELSE NULL END WHERE id=p_id;
END; $$;

-- Capability token permits unsubscribing without signing in. GET never changes a subscription.
CREATE FUNCTION public.btb_unsubscribe_opportunity_alerts(p_token uuid) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 UPDATE public.opportunity_alert_preferences SET new_matches=false,deadline_reminders=false WHERE unsubscribe_token=p_token;
END; $$;
REVOKE ALL ON FUNCTION public.btb_unsubscribe_opportunity_alerts(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.btb_unsubscribe_opportunity_alerts(uuid) TO anon,authenticated,service_role;

REVOKE ALL ON FUNCTION btb_private.alert_opportunity_items(),btb_private.alert_category_status(jsonb,text),btb_private.alert_deadline_date(jsonb),
 public.btb_due_opportunity_alerts(),public.btb_claim_opportunity_alert(uuid),public.btb_prepare_opportunity_alert(uuid,uuid,jsonb),
 public.btb_finish_opportunity_alert(uuid,uuid,text,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION btb_private.alert_opportunity_items(),btb_private.alert_category_status(jsonb,text),btb_private.alert_deadline_date(jsonb),
 public.btb_due_opportunity_alerts(),public.btb_claim_opportunity_alert(uuid),public.btb_prepare_opportunity_alert(uuid,uuid,jsonb),
 public.btb_finish_opportunity_alert(uuid,uuid,text,text) TO service_role;


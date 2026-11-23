-- Review attachments stay private until the associated review is approved.
-- Object paths contain random IDs, never vendor IDs or original filenames.
INSERT INTO storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
VALUES('review-photos','review-photos',false,3145728,ARRAY['image/jpeg']);

CREATE TABLE public.review_photos(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 review_id uuid NOT NULL REFERENCES public.reviews(id) ON DELETE CASCADE,
 storage_path text NOT NULL UNIQUE,
 width integer NOT NULL CHECK(width BETWEEN 1 AND 2048),
 height integer NOT NULL CHECK(height BETWEEN 1 AND 2048),
 caption text NOT NULL DEFAULT '' CHECK(char_length(caption)<=160),
 sort_order smallint NOT NULL CHECK(sort_order BETWEEN 0 AND 3),
 is_hidden boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(review_id,sort_order),
 CHECK(storage_path ~ '^[0-9a-f-]{36}/[0-9a-f-]{36}\.jpg$' AND split_part(storage_path,'/',1)=review_id::text)
);
ALTER TABLE public.review_photos ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.review_photos FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.review_photos TO authenticated;
GRANT ALL ON public.review_photos TO service_role;

CREATE FUNCTION btb_private.photo_member() RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
 SELECT auth.uid() IS NOT NULL AND coalesce(auth.jwt()->>'is_anonymous','false')<>'true'
 AND EXISTS(SELECT 1 FROM auth.users u WHERE u.id=auth.uid() AND u.email_confirmed_at IS NOT NULL
 AND u.deleted_at IS NULL AND (u.banned_until IS NULL OR u.banned_until<now()));
$$;
REVOKE ALL ON FUNCTION btb_private.photo_member() FROM PUBLIC,anon,authenticated;

-- Definer helpers avoid recursive RLS between reviews, photos, and storage.
CREATE FUNCTION public.btb_can_read_review_photo(p_review_id uuid,p_hidden boolean) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
 SELECT public.btb_is_admin() OR EXISTS(SELECT 1 FROM public.reviews r WHERE r.id=p_review_id
 AND (r.vendor_id=auth.uid() OR (NOT p_hidden AND r.status='approved' AND public.btb_market_is_visible(r.market_id) AND btb_private.photo_member())));
$$;
REVOKE ALL ON FUNCTION public.btb_can_read_review_photo(uuid,boolean) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.btb_can_read_review_photo(uuid,boolean) TO authenticated;
CREATE POLICY review_photo_read ON public.review_photos FOR SELECT TO authenticated
USING(public.btb_can_read_review_photo(review_id,is_hidden));

CREATE FUNCTION public.btb_can_upload_review_photo(p_name text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path='' AS $$
BEGIN
 IF NOT btb_private.photo_member() OR p_name IS NULL OR
 p_name !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg$' THEN RETURN false; END IF;
 RETURN EXISTS(SELECT 1 FROM public.vendor_profiles WHERE user_id=auth.uid() AND verification_status='approved')
 AND NOT EXISTS(SELECT 1 FROM public.reviews WHERE id=split_part(p_name,'/',1)::uuid)
 -- Limit unfinished files as well as the four attachments accepted per review.
 AND (SELECT count(*) FROM storage.objects o WHERE o.bucket_id='review-photos' AND o.owner_id=auth.uid()::text
 AND NOT EXISTS(SELECT 1 FROM public.review_photos p WHERE p.storage_path=o.name))<20;
END; $$;
REVOKE ALL ON FUNCTION public.btb_can_upload_review_photo(text) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.btb_can_upload_review_photo(text) TO authenticated;

CREATE FUNCTION public.btb_can_read_review_photo_object(p_name text,p_owner text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
 SELECT public.btb_is_admin() OR p_owner=auth.uid()::text
 OR EXISTS(SELECT 1 FROM public.review_photos p JOIN public.reviews r ON r.id=p.review_id
 WHERE p.storage_path=p_name AND NOT p.is_hidden AND r.status='approved'
 AND public.btb_market_is_visible(r.market_id) AND btb_private.photo_member());
$$;
REVOKE ALL ON FUNCTION public.btb_can_read_review_photo_object(text,text) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.btb_can_read_review_photo_object(text,text) TO authenticated;

CREATE FUNCTION public.btb_can_remove_review_photo_object(p_name text) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path='' AS $$
BEGIN
 IF split_part(p_name,'/',1) !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN RETURN false; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(split_part(p_name,'/',1),0));
 RETURN NOT EXISTS(SELECT 1 FROM public.review_photos WHERE storage_path=p_name);
END;
$$;
REVOKE ALL ON FUNCTION public.btb_can_remove_review_photo_object(text) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.btb_can_remove_review_photo_object(text) TO authenticated;

CREATE FUNCTION public.btb_my_unused_review_photos() RETURNS text[]
LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
 SELECT coalesce(array_agg(name),'{}') FROM (SELECT o.name FROM storage.objects o
 WHERE o.bucket_id='review-photos' AND o.owner_id=auth.uid()::text AND o.created_at<now()-interval '1 day'
 AND NOT EXISTS(SELECT 1 FROM public.review_photos p WHERE p.storage_path=o.name) LIMIT 100) unused;
$$;
REVOKE ALL ON FUNCTION public.btb_my_unused_review_photos() FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.btb_my_unused_review_photos() TO authenticated;

CREATE POLICY review_photo_upload ON storage.objects FOR INSERT TO authenticated
WITH CHECK(bucket_id='review-photos' AND owner_id=(SELECT auth.uid())::text AND public.btb_can_upload_review_photo(name));
CREATE POLICY review_photo_object_read ON storage.objects FOR SELECT TO authenticated
USING(bucket_id='review-photos' AND public.btb_can_read_review_photo_object(name,owner_id));
CREATE POLICY review_photo_draft_delete ON storage.objects FOR DELETE TO authenticated
USING(bucket_id='review-photos' AND owner_id=(SELECT auth.uid())::text AND public.btb_can_remove_review_photo_object(name));
-- No UPDATE policy: published or pending objects cannot be overwritten.

CREATE FUNCTION btb_private.review_photo_entries(p_review_id uuid,p_include_hidden boolean) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
 SELECT coalesce(jsonb_agg(jsonb_build_object('id',p.id,'path',p.storage_path,'width',p.width,'height',p.height,
 'caption',p.caption,'hidden',p.is_hidden) ORDER BY p.sort_order),'[]'::jsonb)
 FROM public.review_photos p WHERE p.review_id=p_review_id AND (p_include_hidden OR NOT p.is_hidden);
$$;
REVOKE ALL ON FUNCTION btb_private.review_photo_entries(uuid,boolean) FROM PUBLIC,anon,authenticated;

CREATE FUNCTION public.btb_submit_vendor_review(p_id uuid,p_review jsonb,p_photos jsonb DEFAULT '[]') RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE actor uuid:=auth.uid(); photo jsonb; position integer:=0; path text; object storage.objects;
BEGIN
 IF NOT btb_private.photo_member() OR NOT EXISTS(SELECT 1 FROM public.vendor_profiles WHERE user_id=actor AND verification_status='approved') THEN
 RAISE EXCEPTION 'An approved vendor account is required to submit reviews.' USING errcode='42501'; END IF;
 IF p_id IS NULL OR jsonb_typeof(p_review) IS DISTINCT FROM 'object' OR jsonb_typeof(p_photos) IS DISTINCT FROM 'array' THEN
 RAISE EXCEPTION 'Invalid review submission.' USING errcode='22023'; END IF;
 -- Serialize retries of one submission. A lost HTTP response cannot duplicate it.
 PERFORM pg_advisory_xact_lock(hashtextextended(p_id::text,0));
 IF EXISTS(SELECT 1 FROM public.reviews WHERE id=p_id AND vendor_id=actor) THEN RETURN p_id; END IF;
 IF EXISTS(SELECT 1 FROM public.reviews WHERE id=p_id) THEN RAISE EXCEPTION 'Invalid submission ID.' USING errcode='42501'; END IF;
 IF jsonb_array_length(p_photos)>4 THEN RAISE EXCEPTION 'Add up to 4 photos per review.' USING errcode='23514'; END IF;
 IF NOT public.btb_market_is_visible((p_review->>'market_id')::uuid) THEN RAISE EXCEPTION 'This market is not available for review.' USING errcode='42501'; END IF;
 -- Validate every storage object BEFORE inserting the review. The existing
 -- attendance, category, occurrence, and duplicate guards still run on INSERT.
 FOR photo IN SELECT * FROM jsonb_array_elements(p_photos) LOOP
  path:=photo->>'path';
  SELECT * INTO object FROM storage.objects WHERE bucket_id='review-photos' AND name=path FOR UPDATE;
  IF NOT FOUND OR object.owner_id IS DISTINCT FROM actor::text OR split_part(path,'/',1)<>p_id::text
   OR object.metadata->>'mimetype' IS DISTINCT FROM 'image/jpeg'
   OR coalesce((object.metadata->>'size')::bigint,0) NOT BETWEEN 1 AND 3145728 THEN
   RAISE EXCEPTION 'A photo is missing or does not belong to this review. Please try uploading it again.' USING errcode='23514'; END IF;
  IF (photo->>'width')::integer IS NULL OR (photo->>'height')::integer IS NULL
   OR (photo->>'width')::integer NOT BETWEEN 1 AND 2048 OR (photo->>'height')::integer NOT BETWEEN 1 AND 2048
   OR char_length(coalesce(photo->>'caption',''))>160 THEN
   RAISE EXCEPTION 'Invalid photo size or caption.' USING errcode='23514'; END IF;
 END LOOP;
 INSERT INTO public.reviews(id,market_id,vendor_id,occurrence_id,attended_on,vendor_categories,other_category,
 booth_value,foot_traffic,organization,promotion,overall,booth_cost,booth_duration,number_of_days,experience,would_return,status)
 VALUES(p_id,(p_review->>'market_id')::uuid,actor,(p_review->>'occurrence_id')::uuid,(p_review->>'attended_on')::date,
 ARRAY(SELECT jsonb_array_elements_text(p_review->'vendor_categories')),nullif(btrim(p_review->>'other_category'),''),
 (p_review->>'booth_value')::smallint,(p_review->>'foot_traffic')::smallint,(p_review->>'organization')::smallint,
 (p_review->>'promotion')::smallint,(p_review->>'overall')::smallint,(p_review->>'booth_cost')::numeric,
 nullif(p_review->>'booth_duration',''),(p_review->>'number_of_days')::integer,btrim(p_review->>'experience'),p_review->>'would_return','pending');
 FOR photo IN SELECT * FROM jsonb_array_elements(p_photos) LOOP
  INSERT INTO public.review_photos(review_id,storage_path,width,height,caption,sort_order)
  VALUES(p_id,photo->>'path',(photo->>'width')::integer,(photo->>'height')::integer,btrim(coalesce(photo->>'caption','')),position);
  position:=position+1;
 END LOOP;
 RETURN p_id;
END; $$;
REVOKE ALL ON FUNCTION public.btb_submit_vendor_review(uuid,jsonb,jsonb) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.btb_submit_vendor_review(uuid,jsonb,jsonb) TO authenticated;

CREATE FUNCTION public.btb_admin_set_review_photo_visibility(p_photo_id uuid,p_hidden boolean,p_expected_hidden boolean) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 IF NOT public.btb_is_admin() THEN RAISE EXCEPTION 'Admin access required.' USING errcode='42501'; END IF;
 IF p_hidden IS NULL OR p_expected_hidden IS NULL THEN RAISE EXCEPTION 'Invalid photo decision.' USING errcode='22023'; END IF;
 UPDATE public.review_photos SET is_hidden=p_hidden WHERE id=p_photo_id AND is_hidden=p_expected_hidden;
 IF NOT FOUND THEN RAISE EXCEPTION 'The photo changed. Refresh the queue before trying again.' USING errcode='40001'; END IF;
END; $$;
REVOKE ALL ON FUNCTION public.btb_admin_set_review_photo_visibility(uuid,boolean,boolean) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.btb_admin_set_review_photo_visibility(uuid,boolean,boolean) TO authenticated;

COMMENT ON TABLE public.review_photos IS 'Optional immutable vendor review attachments; review approval and per-photo visibility control member access.';
CREATE OR REPLACE FUNCTION public.btb_admin_queue(p_kind text, p_status text DEFAULT 'pending'::text, p_offset integer DEFAULT 0)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_items jsonb;
  v_total bigint;
  v_counts jsonb;
begin
  if not public.btb_is_admin() then
    raise exception 'Admin access required.' using errcode = '42501';
  end if;
  if p_kind is null or p_kind not in ('suggestions','vendors','reviews')
    or p_status is null or p_status not in ('pending','approved','rejected','duplicate')
    or (p_status = 'duplicate' and p_kind <> 'suggestions')
    or p_offset is null or p_offset < 0 then
    raise exception 'Invalid queue request.' using errcode = '22023';
  end if;

  select jsonb_build_object(
    'suggestions', (select count(*) from public.market_suggestions where status = 'pending'),
    'vendors', (select count(*) from public.vendor_profiles where verification_status = 'pending'),
    'reviews', (select count(*) from public.reviews where status = 'pending')
  ) into v_counts;

  if p_kind = 'suggestions' then
    select count(*) into v_total from public.market_suggestions where status = p_status;
    select coalesce(jsonb_agg(to_jsonb(q) order by q.created_at, q.id), '[]'::jsonb)
    into v_items from (
      select s.id, s.name, s.city, s.state, s.website_url, s.notes, s.organizer,
        s.status, s.linked_market_id, s.created_at, m.slug as linked_slug
      from public.market_suggestions s
      left join public.markets m on m.id = s.linked_market_id
      where s.status = p_status order by s.created_at, s.id limit 20 offset p_offset
    ) q;
  elsif p_kind = 'vendors' then
    select count(*) into v_total from public.vendor_profiles where verification_status = p_status;
    select coalesce(jsonb_agg(to_jsonb(q) order by q.created_at, q.id), '[]'::jsonb)
    into v_items from (
      select v.user_id as id, v.business_name, v.business_url, v.verification_notes,
        v.verification_status as status, v.created_at
      from public.vendor_profiles v where v.verification_status = p_status
      order by v.created_at, v.user_id limit 20 offset p_offset
    ) q;
  else
    select count(*) into v_total from public.reviews where status = p_status;
    select coalesce(jsonb_agg(to_jsonb(q) order by q.created_at, q.id), '[]'::jsonb)
    into v_items from (
      select r.id, r.market_id, m.name as market_name, m.slug as market_slug,
        r.vendor_categories, r.other_category, r.booth_value, r.foot_traffic,
        r.organization, r.promotion, r.overall, r.booth_cost, r.booth_duration,
        r.number_of_days, r.experience, r.would_return, r.status, r.created_at, r.attended_on,
        btb_private.review_photo_entries(r.id,true) as photos
      from public.reviews r join public.markets m on m.id = r.market_id
      where r.status = p_status order by r.created_at, r.id limit 20 offset p_offset
    ) q;
  end if;
  return jsonb_build_object('items', v_items, 'total', v_total, 'pending', v_counts);
end;
$function$
;
CREATE OR REPLACE FUNCTION public.btb_market_reviews_with_attendance(p_market_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare result jsonb;
begin
  if auth.uid() is null then raise exception 'Sign in to read vendor reviews.' using errcode = '42501'; end if;
  select coalesce(jsonb_agg(to_jsonb(q) order by q.created_at desc, q.id), '[]'::jsonb)
    into result from (
      select r.id, r.market_id, r.booth_value, r.foot_traffic, r.organization,
        r.promotion, r.overall, r.vendor_categories, r.other_category, r.booth_cost,
        r.booth_duration, r.number_of_days, r.experience, r.would_return,
        r.created_at, r.attended_on, btb_private.review_photo_entries(r.id,false) as photos
      from public.reviews r where r.market_id = p_market_id and public.btb_market_is_visible(p_market_id) and r.status = 'approved'
    ) q;
  return result;
end;
$function$
;
CREATE OR REPLACE FUNCTION public.btb_my_reviews(p_offset integer DEFAULT 0)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare items jsonb; total bigint;
begin
 if auth.uid() is null then raise exception 'Sign in required.' using errcode='42501'; end if;
 if p_offset is null or p_offset < 0 then raise exception 'Invalid offset.' using errcode='22023'; end if;
 select count(*) into total from public.reviews where vendor_id=auth.uid();
 select coalesce(jsonb_agg(to_jsonb(q) order by q.created_at desc,q.id),'[]'::jsonb) into items from (
  select r.id,m.name as market_name,m.slug as market_slug,r.status,r.attended_on,r.overall,r.experience,r.created_at,btb_private.review_photo_entries(r.id,true) as photos
  from public.reviews r left join public.markets m on m.id=r.market_id
  where r.vendor_id=auth.uid() order by r.created_at desc,r.id limit 20 offset p_offset
 ) q;
 return jsonb_build_object('items',items,'total',total);
end; $function$
;

NOTIFY pgrst,'reload schema';


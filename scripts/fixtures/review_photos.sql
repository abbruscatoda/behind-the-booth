-- Isolated PostgreSQL fixtures, without real users or email/webhook triggers.
CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS;
CREATE SCHEMA auth; CREATE SCHEMA storage; CREATE SCHEMA btb_private;
CREATE TABLE auth.users(id uuid PRIMARY KEY,email_confirmed_at timestamptz,deleted_at timestamptz,banned_until timestamptz);
CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE AS $$SELECT coalesce(nullif(current_setting('request.jwt.claims',true),'')::jsonb,'{}')$$;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$SELECT (auth.jwt()->>'sub')::uuid$$;
GRANT USAGE ON SCHEMA auth,storage TO anon,authenticated,service_role;
CREATE TABLE btb_private.admins(user_id uuid PRIMARY KEY);
CREATE FUNCTION public.btb_is_admin() RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$SELECT EXISTS(SELECT 1 FROM btb_private.admins WHERE user_id=auth.uid())$$;
CREATE TABLE public.markets(id uuid PRIMARY KEY,name text,slug text,is_hidden boolean DEFAULT false);
CREATE FUNCTION public.btb_market_is_visible(p_id uuid) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$SELECT EXISTS(SELECT 1 FROM public.markets WHERE id=p_id AND NOT is_hidden)$$;
CREATE TABLE public.vendor_profiles(user_id uuid PRIMARY KEY REFERENCES auth.users(id),verification_status text,created_at timestamptz DEFAULT now(),business_name text,business_url text,verification_notes text);
CREATE TABLE public.market_suggestions(id uuid PRIMARY KEY,status text);
CREATE TABLE public.reviews(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),market_id uuid NOT NULL REFERENCES public.markets(id),vendor_id uuid NOT NULL REFERENCES auth.users(id),
 occurrence_id uuid,attended_on date NOT NULL CHECK(attended_on<=current_date),vendor_categories text[] NOT NULL DEFAULT '{}',other_category text,
 booth_value smallint NOT NULL CHECK(booth_value BETWEEN 1 AND 5),foot_traffic smallint NOT NULL CHECK(foot_traffic BETWEEN 1 AND 5),
 organization smallint NOT NULL CHECK(organization BETWEEN 1 AND 5),promotion smallint NOT NULL CHECK(promotion BETWEEN 1 AND 5),overall smallint NOT NULL CHECK(overall BETWEEN 1 AND 5),
 booth_cost numeric CHECK(booth_cost>=0),booth_duration text CHECK(booth_duration IN ('single','multi')),number_of_days integer,
 experience text NOT NULL CHECK(length(btrim(experience)) BETWEEN 1 AND 2000),would_return text NOT NULL CHECK(would_return IN ('Yes','No','Maybe')),
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),created_at timestamptz DEFAULT now(),
 UNIQUE(vendor_id,market_id,attended_on)
);
ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON public.reviews TO authenticated;
CREATE POLICY own_reviews ON public.reviews FOR SELECT TO authenticated USING(vendor_id=auth.uid());
CREATE TABLE storage.buckets(id text PRIMARY KEY,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
CREATE TABLE storage.objects(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),bucket_id text REFERENCES storage.buckets(id),name text,owner_id text,metadata jsonb,created_at timestamptz DEFAULT now(),UNIQUE(bucket_id,name));
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;
GRANT SELECT,INSERT,DELETE,UPDATE ON storage.objects TO authenticated;
INSERT INTO auth.users VALUES
 ('11111111-1111-4111-8111-111111111111',now(),NULL,NULL),
 ('22222222-2222-4222-8222-222222222222',now(),NULL,NULL),
 ('33333333-3333-4333-8333-333333333333',now(),NULL,NULL),
 ('44444444-4444-4444-8444-444444444444',NULL,NULL,NULL),
 ('55555555-5555-4555-8555-555555555555',now(),NULL,NULL);
INSERT INTO public.vendor_profiles(user_id,verification_status) VALUES
 ('11111111-1111-4111-8111-111111111111','approved'),('22222222-2222-4222-8222-222222222222','pending'),
 ('44444444-4444-4444-8444-444444444444','approved');
INSERT INTO btb_private.admins VALUES('55555555-5555-4555-8555-555555555555');
INSERT INTO public.markets(id,name,slug) VALUES('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','Fixture market','fixture-market');
CREATE OR REPLACE FUNCTION public.btb_admin_queue_with_attendance(p_kind text, p_status text DEFAULT 'pending'::text, p_offset integer DEFAULT 0)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare result jsonb; items jsonb;
begin
  if not public.btb_is_admin() then raise exception 'Admin access required.' using errcode = '42501'; end if;
  result := public.btb_admin_queue(p_kind, p_status, p_offset);
  if p_kind = 'reviews' then
    select coalesce(jsonb_agg(item.value || jsonb_build_object('attended_on', r.attended_on) order by item.ordinality), '[]'::jsonb)
    into items from jsonb_array_elements(result->'items') with ordinality as item(value, ordinality)
    left join public.reviews r on r.id = (item.value->>'id')::uuid;
    result := jsonb_set(result, '{items}', items);
  end if;
  return result;
end;
$function$
;


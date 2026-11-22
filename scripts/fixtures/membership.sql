-- Isolated test fixture. No real accounts, provider credentials, or outbound hooks.
CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS;
CREATE SCHEMA auth; CREATE SCHEMA btb_private;
CREATE TABLE auth.users(id uuid PRIMARY KEY,email_confirmed_at timestamptz,deleted_at timestamptz,banned_until timestamptz);
CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE AS $$SELECT coalesce(nullif(current_setting('request.jwt.claims',true),'')::jsonb,'{}')$$;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$SELECT (auth.jwt()->>'sub')::uuid$$;
GRANT USAGE ON SCHEMA auth TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION auth.jwt(),auth.uid() TO anon,authenticated,service_role;
CREATE TABLE public.markets(id uuid PRIMARY KEY,slug text,is_hidden boolean DEFAULT false);
CREATE TABLE public.vendor_opportunities(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),title text,market_id uuid REFERENCES public.markets(id),schedule_type text DEFAULT 'dated_event',
 organizer text DEFAULT 'Local organizer',city text DEFAULT 'Raleigh',state text DEFAULT 'NC',venue text DEFAULT 'Local park',
 starts_on date DEFAULT current_date+10,ends_on date DEFAULT current_date+10,deadline timestamptz DEFAULT now()+interval '2 days',
 application_url text DEFAULT 'https://example.org/apply',source_url text DEFAULT 'https://example.org/source',
 categories text[] DEFAULT ARRAY['Handmade Crafts'],category_evidence jsonb DEFAULT '{}',
 booth_fee numeric DEFAULT 25,application_fee numeric DEFAULT 5,deposit numeric DEFAULT 10,
 fee_notes text DEFAULT 'Detailed member fees.',eligibility text DEFAULT 'Member requirements.',verified_at timestamptz DEFAULT now(),
 published_at timestamptz DEFAULT now(),occurrence_id uuid DEFAULT gen_random_uuid(),publication text DEFAULT 'published',
 review_state text DEFAULT 'verified',availability text DEFAULT 'open',
 fixture_facts jsonb DEFAULT '{"requirements":{"summary":"Private full details","source_url":"https://example.org/requirements"}}',
 fixture_coverage jsonb DEFAULT '{}'
);
CREATE TABLE public.saved_opportunities(user_id uuid REFERENCES auth.users(id),opportunity_id uuid REFERENCES public.vendor_opportunities(id),PRIMARY KEY(user_id,opportunity_id));
CREATE TABLE public.vendor_profiles(user_id uuid PRIMARY KEY REFERENCES auth.users(id),verification_status text DEFAULT 'pending');
ALTER TABLE public.vendor_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_opportunities ENABLE ROW LEVEL SECURITY;
GRANT ALL ON public.vendor_opportunities,public.saved_opportunities,public.markets TO service_role;
CREATE FUNCTION public.btb_market_is_visible(p_market_id uuid) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$SELECT EXISTS(SELECT 1 FROM public.markets WHERE id=p_market_id AND NOT is_hidden)$$;
CREATE FUNCTION public.btb_market_history_stats(uuid) RETURNS jsonb LANGUAGE sql STABLE AS $$SELECT '{"overall":4,"review_count":1,"reviewer_count":1}'::jsonb$$;
CREATE FUNCTION public.btb_opportunity_state(p_state text,p_deadline timestamptz,p_verified timestamptz,p_end date) RETURNS text LANGUAGE sql STABLE AS $$
SELECT CASE WHEN p_end<current_date OR p_deadline<now() OR p_state='closed' THEN 'closed' WHEN p_verified IS NULL OR p_verified<now()-interval '7 days' THEN 'needs_recheck' ELSE p_state END$$;
CREATE FUNCTION btb_private.public_category_evidence(text,jsonb) RETURNS jsonb LANGUAGE sql STABLE AS $$SELECT $2$$;
CREATE FUNCTION btb_private.public_research_coverage(p_id uuid,text,text,timestamptz,text) RETURNS jsonb LANGUAGE sql STABLE AS $$SELECT fixture_coverage FROM public.vendor_opportunities WHERE id=p_id$$;
CREATE FUNCTION btb_private.public_opportunity_facts(p_id uuid) RETURNS jsonb LANGUAGE sql STABLE AS $$SELECT fixture_facts FROM public.vendor_opportunities WHERE id=p_id$$;
INSERT INTO auth.users(id,email_confirmed_at) VALUES
 ('11111111-1111-4111-8111-111111111111',now()),('22222222-2222-4222-8222-222222222222',now()),('33333333-3333-4333-8333-333333333333',NULL);
INSERT INTO public.markets(id,slug) VALUES('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','fixture-raleigh-market'),('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','fixture-durham-market');
INSERT INTO public.markets(id,slug,is_hidden) VALUES('cccccccc-cccc-4ccc-8ccc-cccccccccccc','fixture-hidden-market',true);
INSERT INTO public.vendor_opportunities(id,title,market_id,starts_on,ends_on) VALUES
 ('aaaaaaaa-0001-4000-8000-000000000001','Complete public example','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',current_date+5,current_date+5),
 ('aaaaaaaa-0002-4000-8000-000000000002','Second Raleigh opportunity','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',current_date+10,current_date+10),
 ('bbbbbbbb-0003-4000-8000-000000000003','Durham opportunity','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',current_date+12,current_date+12),
 ('cccccccc-0004-4000-8000-000000000004','Hidden opportunity','cccccccc-cccc-4ccc-8ccc-cccccccccccc',current_date+15,current_date+15);
UPDATE public.vendor_opportunities SET city='Durham' WHERE id='bbbbbbbb-0003-4000-8000-000000000003';

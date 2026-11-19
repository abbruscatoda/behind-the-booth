-- Allow the five newly curated official Triangle organizer pages in the
-- existing worker-secret-gated public-form publisher. Dated-event and form
-- verification requirements remain unchanged.
DO $migration$
DECLARE olddef text;newdef text;
old_tail text := $old$'https://www.artsplosure.org/first-night-raleigh'];$old$;
new_tail text := $new$'https://www.artsplosure.org/first-night-raleigh',
 'https://wakeforestmarket.org/vendors/become-a-vendor/',
 'https://www.chathammillsfarmersmarket.com/vendors/',
 'https://www.garnernc.gov/departments/parks-recreation-and-cultural-resources/events/vendor-interest',
 'https://www.knightdalenc.gov/parks-recreation-and-cultural-programs/festivals-and-events/vendor-interest-form',
 'https://www.ncagr.gov/divisions/marketing/farmers-markets-agricultural-centers/state-farmers-market-raleigh/vendor-information'];$new$;
BEGIN
 SELECT pg_get_functiondef('public.btb_research_publish_form(jsonb,uuid,timestamp with time zone)'::regprocedure)
 INTO olddef;
 IF olddef IS NULL OR position(old_tail IN olddef)=0
 THEN RAISE EXCEPTION 'Unexpected curated sources; update aborted';END IF;
 newdef:=replace(olddef,old_tail,new_tail);
 EXECUTE newdef;
END;
$migration$;

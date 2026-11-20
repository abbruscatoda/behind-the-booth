-- An organizer-published First Night short form has been independently
-- verified to redirect to the exact full Google Form on the existing card.
-- Keep the exception narrow: never archive an unrelated Artsplosure form.
DO $migration$
DECLARE
 olddef text;
 updated text;
 oldpiece text := $old$          and l.target_url='https://forms.gle/NSUe3V11UyUW3K997')
    )
$old$;
 newpiece text := $new$          and l.target_url='https://forms.gle/NSUe3V11UyUW3K997')
      -- Verified First Night Raleigh short form redirects to this
      -- opportunity's published full Google Form (not a new event).
      or (o.title='First Night Raleigh'
          and o.source_url='https://www.artsplosure.org/first-night-raleigh'
          and o.application_url='https://docs.google.com/forms/d/e/1FAIpQLScPXt0euH9ziXcAR3tA9BkXTQ4qtnTK9V6aqttIYbxlittBlA/viewform'
          and l.source_url='https://www.artsplosure.org/first-night-raleigh'
          and l.target_url='https://forms.gle/e8JRmQUUcEirUzzY9')
    )
$new$;
BEGIN
 SELECT pg_get_functiondef('btb_private.resolve_published_discovery_leads()'::regprocedure) INTO olddef;
 IF olddef IS NULL OR position(oldpiece IN olddef)=0
 THEN RAISE EXCEPTION 'Unexpected lead reconciliation function; alias not installed'; END IF;
 updated:=replace(olddef,oldpiece,newpiece);
 EXECUTE updated;
 PERFORM btb_private.resolve_published_discovery_leads();
END;
$migration$;

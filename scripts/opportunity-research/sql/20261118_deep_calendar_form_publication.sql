-- Extend the existing guarded public-form publisher to accept a dated event
-- page discovered through one of four explicitly configured organizer calendars.
-- Every record still needs a complete source/form receipt and the worker secret.
DO $migration$
DECLARE olddef text;
DECLARE newdef text;
DECLARE old_policy text := 'p_result->>''policy'' is distinct from ''triangle-form-auto-v1''';
DECLARE new_policy text := 'coalesce(p_result->>''policy'','''') not in (''triangle-form-auto-v1'',''triangle-form-calendar-v2'')';
DECLARE old_source text := 'coalesce(src,'''') <> all(sources)';
DECLARE new_source text := $gate$
 (
  (p_result->>'policy'='triangle-form-auto-v1' AND coalesce(src,'') <> all(sources))
  OR
  (p_result->>'policy'='triangle-form-calendar-v2'
   AND NOT (
    (p_result->>'organizer_root',p_result->>'calendar_url') IN (
     ('https://www.trianglepopup.com/applications','https://www.trianglepopup.com/events'),
     ('https://thenightmarketcompany.com/','https://thenightmarketcompany.com/'),
     ('https://www.geekandgrubmarket.com/vendorapplication','https://www.geekandgrubmarket.com/upcoming-events'),
     ('https://westernwakefarmersmarket.org/','https://westernwakefarmersmarket.org/events')
    )
    AND (
      src ~ '^https://www[.]trianglepopup[.]com/events/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://thenightmarketcompany[.]com/(events|event|markets)/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://www[.]geekandgrubmarket[.]com/event-details/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://westernwakefarmersmarket[.]org/events/[A-Za-z0-9_%/-]+$'
    )
    AND (
     (p_result->>'organizer_root'='https://www.trianglepopup.com/applications'
      AND src ~ '^https://www[.]trianglepopup[.]com/events/')
     OR (p_result->>'organizer_root'='https://thenightmarketcompany.com/'
      AND src ~ '^https://thenightmarketcompany[.]com/')
     OR (p_result->>'organizer_root'='https://www.geekandgrubmarket.com/vendorapplication'
      AND src ~ '^https://www[.]geekandgrubmarket[.]com/event-details/')
     OR (p_result->>'organizer_root'='https://westernwakefarmersmarket.org/'
      AND src ~ '^https://westernwakefarmersmarket[.]org/events/')
    )
   ))
 )
$gate$;
DECLARE old_recheck text := 'item.verification_policy is distinct from ''triangle-form-auto-v1''';
DECLARE new_recheck text := 'item.verification_policy is distinct from p_result->>''policy''';
BEGIN
 SELECT pg_get_functiondef('public.btb_research_publish_form(jsonb,uuid,timestamp with time zone)'::regprocedure) INTO olddef;
 IF olddef IS NULL OR position(old_policy IN olddef)=0 OR position(old_source IN olddef)=0 OR position(old_recheck IN olddef)=0
 THEN RAISE EXCEPTION 'Unexpected live publisher version; nothing changed';END IF;
 newdef:=replace(olddef,old_policy,new_policy);
 newdef:=replace(newdef,old_source,new_source);
 newdef:=replace(newdef,old_recheck,new_recheck);
 EXECUTE newdef;
END;
$migration$;
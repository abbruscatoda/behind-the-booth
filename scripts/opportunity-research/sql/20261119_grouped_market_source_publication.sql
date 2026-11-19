-- Extend the existing guarded form publisher to accept a fully verified,
-- organizer-linked event -> application chain from any CURRENT curated source.
-- No form can publish without its exact event date and future cutoff.
DO $migration$
DECLARE
 original text;
 revised text;
 old_gate text := $old$(p_result->>'policy'='triangle-form-calendar-v2'
   AND NOT ($old$;
 new_gate text := $new$(p_result->>'policy'='triangle-form-calendar-v2'
   AND NOT (($new$;
 old_tail text := $old$   ))
 )

   or not ($old$;
 new_tail text := $new$   ) OR (
      p_result->>'grouped_research'='true'
      AND p_result->>'organizer_root'=ANY(sources)
      AND p_result->>'calendar_url'=p_result->>'organizer_root'
      AND split_part(src,'/',3)=split_part(p_result->>'organizer_root','/',3)
      AND src ~ '^https://[A-Za-z0-9.-]+/(events|event|event-details|markets|market|upcoming|calendar)/[A-Za-z0-9_%/-]+$'
      AND length(coalesce(p_result->>'event_index_url','')) between 12 and 1200
      AND length(coalesce(p_result->>'application_index_url','')) between 12 and 1200
   )))
 )

   or not ($new$;
 old_assignment text := $old$verification_policy='triangle-form-auto-v1'$old$;
 new_assignment text := $new$verification_policy=p_result->>'policy'$new$;
BEGIN
 SELECT pg_get_functiondef('public.btb_research_publish_form(jsonb,uuid,timestamp with time zone)'::regprocedure)
 INTO original;
 IF original IS NULL OR position(old_gate IN original)=0
   OR position(old_tail IN original)=0 OR position(old_assignment IN original)=0
 THEN
   RAISE EXCEPTION 'Unexpected live public-form publisher; no changes applied';
 END IF;
 revised:=replace(original,old_gate,new_gate);
 revised:=replace(revised,old_tail,new_tail);
 revised:=replace(revised,old_assignment,new_assignment);
 IF position(new_gate IN revised)=0 OR position(new_tail IN revised)=0 THEN
   RAISE EXCEPTION 'Failed to install the grouped-form evidence gate';
 END IF;
 EXECUTE revised;
END;
$migration$;

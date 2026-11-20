-- Match form publisher's trusted source list to the synchronized official
-- source registry. Preserve all existing date, deadline, form, receipt, quality
-- and exact-link requirements; only replace the stale allowlist check.
DO $patch$
DECLARE
 olddef text;
 updated text;
 direct_old text:=$old$coalesce(src,'') <> all(sources)$old$;
 direct_new text:=$new$not exists(
    select 1 from btb_private.triangle_research_sources r
    where r.source_url=src and r.active)$new$;
 grouped_old text:=$old$p_result->>'organizer_root'=ANY(sources)$old$;
 grouped_new text:=$new$exists(
       select 1 from btb_private.triangle_research_sources r
       where r.source_url=p_result->>'organizer_root' and r.active)$new$;
BEGIN
 select pg_get_functiondef('public.btb_research_publish_form(jsonb,uuid,timestamp with time zone)'::regprocedure) into olddef;
 if olddef is null or position(direct_old in olddef)=0 or position(grouped_old in olddef)=0
 then raise exception 'Unexpected guarded form publisher; no changes applied';end if;
 updated:=replace(replace(olddef,direct_old,direct_new),grouped_old,grouped_new);
 if position(direct_old in updated)>0 or position(grouped_old in updated)>0
 then raise exception 'Stale allowlist check still present';end if;
 execute updated;
END $patch$;

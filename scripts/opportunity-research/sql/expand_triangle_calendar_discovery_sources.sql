-- Extend only exact reviewed calendar/root pairs and bound same-host paths.
-- Authorization, receipts, deadline, form completeness, quality, publication,
-- hidden-market and manual-hold checks remain unchanged. Existing grants persist.
DO $patch$
DECLARE olddef text; updated text; oldpiece text; newpiece text;
BEGIN
 select pg_get_functiondef('public.btb_research_publish_form(jsonb,uuid,timestamp with time zone)'::regprocedure) into olddef;
 if position('https://popupraleigh.com/home/' in olddef)>0 then return;end if;
 updated:=olddef;
 oldpiece:=$old0$('https://www.trianglepopup.com/applications','https://www.trianglepopup.com/events'),$old0$;
 newpiece:=$new0$('https://www.trianglepopup.com/applications','https://www.trianglepopup.com/events'),
     ('https://popupraleigh.com/9-2/','https://popupraleigh.com/home/'),
     ('https://raleighnc.gov/events','https://raleighnc.gov/events'),
     ('https://www.carync.gov/recreation-enjoyment/events','https://www.carync.gov/recreation-enjoyment/events'),
     ('https://www.apexnc.org/428/Special-Events-Festivals','https://www.apexnc.org/428/Special-Events-Festivals'),
     ('https://www.chapelhillarts.org/applications/','https://www.chapelhillarts.org/calendar/'),
     ('https://www.dprplaymore.org/331/Vendor-Performer-Information','https://www.dprplaymore.org/274/Special-Events'),
     ('https://durhamcentralpark.org/events/','https://durhamcentralpark.org/events/'),$new0$;
 if (length(updated)-length(replace(updated,oldpiece,'')))/length(oldpiece)<>1 then raise exception 'Unexpected calendar publisher guard 0; no change applied';end if;
 updated:=replace(updated,oldpiece,newpiece);
 oldpiece:=$old1$src ~ '^https://www[.]trianglepopup[.]com/events/[A-Za-z0-9_%/-]+$'$old1$;
 newpiece:=$new1$src ~ '^https://www[.]trianglepopup[.]com/events/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://popupraleigh[.]com/20[0-9]{2}/[0-9]{2}/[0-9]{2}/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://raleighnc[.]gov/parks-and-recreation/(news|events)/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://www[.]carync[.]gov/recreation-enjoyment/events/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://www[.]apexnc[.]org/[0-9]+/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://www[.]chapelhillarts[.]org/calendar/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://www[.]dprplaymore[.]org/[0-9]+/[A-Za-z0-9_%/-]+$'
      OR src ~ '^https://durhamcentralpark[.]org/(event|events)/[A-Za-z0-9_%/-]+$'$new1$;
 if (length(updated)-length(replace(updated,oldpiece,'')))/length(oldpiece)<>1 then raise exception 'Unexpected calendar publisher guard 1; no change applied';end if;
 updated:=replace(updated,oldpiece,newpiece);
 oldpiece:=$old2$(p_result->>'organizer_root'='https://www.trianglepopup.com/applications'
      AND src ~ '^https://www[.]trianglepopup[.]com/events/')$old2$;
 newpiece:=$new2$(p_result->>'organizer_root'='https://www.trianglepopup.com/applications'
      AND src ~ '^https://www[.]trianglepopup[.]com/events/')
     OR (p_result->>'organizer_root'='https://popupraleigh.com/9-2/' AND src ~ '^https://popupraleigh[.]com/20[0-9]{2}/[0-9]{2}/[0-9]{2}/[A-Za-z0-9_%/-]+$')
     OR (p_result->>'organizer_root'='https://raleighnc.gov/events' AND src ~ '^https://raleighnc[.]gov/parks-and-recreation/(news|events)/[A-Za-z0-9_%/-]+$')
     OR (p_result->>'organizer_root'='https://www.carync.gov/recreation-enjoyment/events' AND src ~ '^https://www[.]carync[.]gov/recreation-enjoyment/events/[A-Za-z0-9_%/-]+$')
     OR (p_result->>'organizer_root'='https://www.apexnc.org/428/Special-Events-Festivals' AND src ~ '^https://www[.]apexnc[.]org/[0-9]+/[A-Za-z0-9_%/-]+$')
     OR (p_result->>'organizer_root'='https://www.chapelhillarts.org/applications/' AND src ~ '^https://www[.]chapelhillarts[.]org/calendar/[A-Za-z0-9_%/-]+$')
     OR (p_result->>'organizer_root'='https://www.dprplaymore.org/331/Vendor-Performer-Information' AND src ~ '^https://www[.]dprplaymore[.]org/[0-9]+/[A-Za-z0-9_%/-]+$')
     OR (p_result->>'organizer_root'='https://durhamcentralpark.org/events/' AND src ~ '^https://durhamcentralpark[.]org/(event|events)/[A-Za-z0-9_%/-]+$')$new2$;
 if (length(updated)-length(replace(updated,oldpiece,'')))/length(oldpiece)<>1 then raise exception 'Unexpected calendar publisher guard 2; no change applied';end if;
 updated:=replace(updated,oldpiece,newpiece);
 if position('perform public.btb_research_authorize();' in updated)=0
  or position('btb_private.validate_research_quality' in updated)=0
  or position('btb_private.validate_worker_categories' in updated)=0
 then raise exception 'Missing original authorization or quality guards';end if;
 execute updated;
END $patch$;

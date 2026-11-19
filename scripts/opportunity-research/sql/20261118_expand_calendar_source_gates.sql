DO $migration$
DECLARE olddef text; newdef text;
DECLARE oldpair constant text:='(''https://westernwakefarmersmarket.org/'',''https://westernwakefarmersmarket.org/events'')';
DECLARE newpair constant text:='(''https://westernwakefarmersmarket.org/'',''https://westernwakefarmersmarket.org/events''),
     (''https://shoplocalraleigh.org/vendor-information/'',''https://shoplocalraleigh.org/events/''),
     (''https://www.thechapelhillfarmersmarket.com/'',''https://www.thechapelhillfarmersmarket.com/events.html'')';
DECLARE oldpath constant text:='OR src ~ ''^https://westernwakefarmersmarket[.]org/events/[A-Za-z0-9_%/-]+$''';
DECLARE newpath constant text:='OR src ~ ''^https://westernwakefarmersmarket[.]org/events/[A-Za-z0-9_%/-]+$''
      OR src ~ ''^https://shoplocalraleigh[.]org/events/[A-Za-z0-9_%/-]+$''
      OR src ~ ''^https://www[.]thechapelhillfarmersmarket[.]com/events/[A-Za-z0-9_%/-]+$''';
DECLARE oldowner constant text:='OR (p_result->>''organizer_root''=''https://westernwakefarmersmarket.org/''
      AND src ~ ''^https://westernwakefarmersmarket[.]org/events/'')';
DECLARE newowner constant text:='OR (p_result->>''organizer_root''=''https://westernwakefarmersmarket.org/''
      AND src ~ ''^https://westernwakefarmersmarket[.]org/events/'')
     OR (p_result->>''organizer_root''=''https://shoplocalraleigh.org/vendor-information/''
      AND src ~ ''^https://shoplocalraleigh[.]org/events/'')
     OR (p_result->>''organizer_root''=''https://www.thechapelhillfarmersmarket.com/''
      AND src ~ ''^https://www[.]thechapelhillfarmersmarket[.]com/events/'')';
BEGIN
 select pg_get_functiondef('public.btb_research_publish_form(jsonb,uuid,timestamp with time zone)'::regprocedure) into olddef;
 if position(oldpair in olddef)=0 or position(oldpath in olddef)=0 or position(oldowner in olddef)=0
 then raise exception 'Publisher does not match expected calendar gate';end if;
 if position('https://shoplocalraleigh.org/events/' in olddef)>0
 then raise exception 'Calendar sources already extended';end if;
 newdef:=replace(olddef,oldpair,newpair);
 newdef:=replace(newdef,oldpath,newpath);
 newdef:=replace(newdef,oldowner,newowner);
 execute newdef;
END;
$migration$;
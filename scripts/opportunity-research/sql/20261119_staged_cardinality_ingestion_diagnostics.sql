-- Return a safe stage token when a cardinality violation escapes the
-- existing per-lead exception handler. The PL/pgSQL exception block rolls
-- back ALL writes in this invocation; never treat this as successful ingestion.
DO $patch$
DECLARE original text;patched text;
BEGIN
 select pg_get_functiondef('public.btb_research_record_discovery_leads_v2(jsonb,jsonb)'::regprocedure) into original;
 if original is null
 or position('cardinality_conflicts integer:=0;' in original)=0
 or position('url text; source text; org text; town text; claimed_host text;' in original)=0
 or position('return jsonb_build_object(''saved'',saved,''skipped'',skipped,' in original)=0
 or position(chr(10)||'end $function$' in original)=0
 then raise exception 'Unexpected v2 ingest function; cannot install diagnostic safely';end if;
 patched:=replace(original,
  'url text; source text; org text; town text; claimed_host text;',
  'url text; source text; org text; town text; claimed_host text; stage text:=''start'';');
 patched:=replace(patched,
  'update btb_private.triangle_research_sources set active=false;',
  'stage:=''registry_reset'';'||chr(10)||' update btb_private.triangle_research_sources set active=false;');
 patched:=replace(patched,
  'insert into btb_private.triangle_research_sources(source_url,organizer,city,active)',
  'stage:=''source_upsert'';'||chr(10)||'  insert into btb_private.triangle_research_sources(source_url,organizer,city,active)');
 patched:=replace(patched,
  'insert into btb_private.triangle_discovery_leads(',
  'stage:=''lead_upsert'';'||chr(10)||'   insert into btb_private.triangle_discovery_leads(');
 patched:=replace(patched,
  'return jsonb_build_object(''saved'',saved,''skipped'',skipped,',
  'stage:=''return_summary'';'||chr(10)||' return jsonb_build_object(''saved'',saved,''skipped'',skipped,');
 patched:=replace(patched,chr(10)||'end $function$',
  chr(10)||'exception when cardinality_violation then'||chr(10)||
  ' return jsonb_build_object(''failed'',true,''sqlstate'',''21000'',''stage'',stage,'||
  '''saved'',0,''skipped'',0);'||chr(10)||'end $function$');
 if patched=original or position('exception when cardinality_violation then' in patched)=0
 then raise exception 'Cardinality diagnostic could not be installed';end if;
 execute patched;
END $patch$;

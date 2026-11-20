-- The worker and Supabase formerly maintained two independent source
-- allowlists (25 vs 20). Synchronize reviewed code-defined sources whenever
-- the worker saves new discoveries. The dedicated research secret is required.
create table if not exists btb_private.triangle_research_sources(
 source_url text primary key,
 organizer text not null,
 city text not null,
 active boolean not null default true,
 updated_at timestamptz not null default now(),
 constraint source_https check(
  source_url ~ '^https://[A-Za-z0-9.-]+(/[^[:space:]<>@?#]*)?$'
  and source_url !~* '^https://(localhost|[0-9]+[.]|[^/]+[.]internal|[^/]+[.]local)(/|$)'
  and length(source_url) <= 1200)
);
alter table btb_private.triangle_research_sources enable row level security;
revoke all on btb_private.triangle_research_sources from public,anon,authenticated;

create or replace function public.btb_research_record_discovery_leads(
 p_leads jsonb,p_sources jsonb
) returns jsonb
language plpgsql security definer set search_path='' as $save$
declare
 entry jsonb; saved integer:=0; skipped integer:=0;
 url text; source text; org text; town text; claimed_host text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('saved',0,'skipped',0,'paused',true);end if;
 if jsonb_typeof(p_sources) is distinct from 'array'
  or jsonb_array_length(p_sources) not between 1 and 75
  or octet_length(p_sources::text)>70000
  or jsonb_typeof(p_leads) is distinct from 'array'
  or jsonb_array_length(p_leads)>80
  or octet_length(p_leads::text)>100000
 then raise exception 'Invalid curated source or lead batch' using errcode='22023';end if;
 -- Transactional registry update; invalid inputs roll the whole operation back.
 update btb_private.triangle_research_sources set active=false;
 for entry in select value from jsonb_array_elements(p_sources) loop
  source:=entry->>'source_url';
  org:=entry->>'organizer';
  town:=entry->>'city';
  claimed_host:=split_part(coalesce(source,''),'/',3);
  if source is null or length(source)>1200
    or source !~ '^https://[A-Za-z0-9.-]+(/[^[:space:]<>@?#]*)?$'
    or claimed_host !~ '^[A-Za-z0-9][A-Za-z0-9.-]{3,240}[.](com|org|net|gov|edu)$'
    or claimed_host ~* '(^|[.])(localhost|local|internal)$'
    or length(coalesce(org,'')) not between 2 and 120
    or length(coalesce(town,'')) not between 3 and 80
  then raise exception 'Invalid code-defined official source' using errcode='22023';end if;
  insert into btb_private.triangle_research_sources(source_url,organizer,city,active)
  values(source,org,town,true)
  on conflict(source_url) do update set
   organizer=excluded.organizer,city=excluded.city,active=true,updated_at=now();
 end loop;
 for entry in select value from jsonb_array_elements(p_leads) loop
  url:=entry->>'target_url'; source:=entry->>'source_url';
  org:=entry->>'organizer';town:=entry->>'city';
  if url is null or length(url)>1200
    or url !~ '^https://[A-Za-z0-9.-]+(/[^[:space:]<>@]*)?([?][^[:space:]<>@]*)?$'
    or url ~* '^https://(localhost|127[.]|10[.]|192[.]168[.]|169[.]254[.]|172[.](1[6-9]|2[0-9]|3[01])[.])'
    or source is null
    or not exists(
      select 1 from btb_private.triangle_research_sources s
      where s.source_url=source and s.active and s.organizer=org and s.city=town)
    or length(coalesce(entry->>'title','')) not between 3 and 160
  then skipped:=skipped+1;continue;end if;
  insert into btb_private.triangle_discovery_leads(
   target_url,source_url,title,organizer,city,notes)
  values(url,source,entry->>'title',org,town,left(coalesce(entry->>'notes',''),500))
  on conflict(target_url) do update set
   last_seen=now(),source_url=excluded.source_url
  where btb_private.triangle_discovery_leads.organizer=excluded.organizer
    and btb_private.triangle_discovery_leads.city=excluded.city;
  if found then saved:=saved+1;
  else skipped:=skipped+1;end if;
 end loop;
 return jsonb_build_object('saved',saved,'skipped',skipped,
  'approved_sources',(select count(*) from btb_private.triangle_research_sources where active));
end $save$;
revoke all on function public.btb_research_record_discovery_leads(jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_record_discovery_leads(jsonb,jsonb) to anon,authenticated,service_role;

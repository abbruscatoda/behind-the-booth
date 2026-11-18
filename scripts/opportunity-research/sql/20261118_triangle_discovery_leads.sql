-- Installed in the live Behind the Booth project on 2026-11-18.
-- Private and RLS protected; worker writes through secret-guarded RPC only.
create table if not exists btb_private.triangle_discovery_leads (
 id uuid primary key default gen_random_uuid(),
 target_url text not null unique,
 source_url text not null,
 title text not null,
 organizer text not null,
 city text not null,
 notes text not null default '',
 review_state text not null default 'new' check (review_state in ('new','ignored','resolved')),
 first_seen timestamptz not null default now(),
 last_seen timestamptz not null default now(),
 constraint triangle_lead_target_https check (
  target_url ~ '^https://[A-Za-z0-9.-]+(/[^[:space:]<>@]*)?([?][^[:space:]<>@]*)?$'
  and length(target_url)<=1200),
 constraint triangle_lead_source_https check (
  source_url ~ '^https://[A-Za-z0-9.-]+(/[^[:space:]<>@]*)?$'
  and length(source_url)<=1200)
);
alter table btb_private.triangle_discovery_leads enable row level security;
revoke all on btb_private.triangle_discovery_leads from public,anon,authenticated;

create or replace function public.btb_research_record_discovery_leads(p_leads jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare entry jsonb; saved int:=0; skipped int:=0; url text; source text;
allowed text[]:=array[
 'https://www.trianglepopup.com/applications',
 'https://thenightmarketcompany.com/',
 'https://shoplocalraleigh.org/vendor-information/',
 'https://www.geekandgrubmarket.com/vendorapplication',
 'https://hummingbirdmarketnc.com/member-markets',
 'https://www.caryfarmersmarket.com/vendor-application/',
 'https://www.hillsboroughartscouncil.org/last-fridays-markets',
 'https://www.takethehighstreet.com/thebazaar',
 'https://blackfarmersmkt.org/the-market/',
 'https://www.durhamcraftmarket.com/saturdays-in-durham-central-park.html',
 'https://www.carrborofarmersmarket.com/',
 'https://www.apexfarmersmarket.com/',
 'https://www.thechapelhillfarmersmarket.com/',
 'https://www.hollyspringsnc.gov/319/Farmers-Market',
 'https://westernwakefarmersmarket.org/',
 'https://www.enoriverfarmersmarket.com/',
 'https://www.fvgrowersmarket.com/',
 'https://www.ymcatriangle.org/events/vendor-market',
 'https://artspacenc.org/calls-for-art/',
 'https://www.artsplosure.org/first-night-raleigh'];
begin
 perform public.btb_research_authorize();
 if not (select enabled from public.btb_research_settings where id=true) then
  return jsonb_build_object('saved',0,'skipped',0,'paused',true);
 end if;
 if jsonb_typeof(p_leads) is distinct from 'array'
  or jsonb_array_length(p_leads)>40
  or octet_length(p_leads::text)>80000 then
  raise exception 'Invalid discovery batch size' using errcode='22023';
 end if;
 for entry in select value from jsonb_array_elements(p_leads) loop
  url:=entry->>'target_url';source:=entry->>'source_url';
  if url is null or length(url)>1200
   or url !~ '^https://[A-Za-z0-9.-]+(/[^[:space:]<>@]*)?([?][^[:space:]<>@]*)?$'
   or url ~* '^https://(localhost|127[.]|10[.]|192[.]168[.]|169[.]254[.]|172[.](1[6-9]|2[0-9]|3[01])[.])'
   or source is null or not (source=any(allowed))
   or length(coalesce(entry->>'title','')) not between 3 and 160
   or length(coalesce(entry->>'organizer','')) not between 2 and 120
   or length(coalesce(entry->>'city','')) not between 3 and 80
  then skipped:=skipped+1;continue;end if;
  insert into btb_private.triangle_discovery_leads(target_url,source_url,title,organizer,city,notes)
   values(url,source,entry->>'title',entry->>'organizer',
          entry->>'city',left(coalesce(entry->>'notes',''),500))
   on conflict(target_url) do update
    set last_seen=now(),source_url=excluded.source_url;
  saved:=saved+1;
 end loop;
 return jsonb_build_object('saved',saved,'skipped',skipped);
end $$;
revoke all on function public.btb_research_record_discovery_leads(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_record_discovery_leads(jsonb) to anon,authenticated,service_role;

create or replace function public.btb_admin_discovery_leads()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare result jsonb;
begin
 if not coalesce(public.btb_is_admin(),false) then
  raise exception 'Admin access required' using errcode='42501';
 end if;
 select coalesce(jsonb_agg(to_jsonb(q) order by q.first_seen desc),'[]'::jsonb)
 into result from (
  select id,target_url,source_url,title,organizer,city,notes,
   review_state,first_seen,last_seen
  from btb_private.triangle_discovery_leads
  where review_state='new'
  order by first_seen desc limit 100
 ) q;
 return result;
end $$;
revoke all on function public.btb_admin_discovery_leads() from public,anon,authenticated;
grant execute on function public.btb_admin_discovery_leads() to authenticated,service_role;

create or replace function public.btb_admin_update_discovery_lead(p_id uuid,p_state text)
returns void language plpgsql security definer set search_path='' as $$
begin
 if not coalesce(public.btb_is_admin(),false) then
  raise exception 'Admin access required' using errcode='42501';
 end if;
 if p_state not in ('ignored','resolved','new') or p_state is null then
  raise exception 'Invalid discovery review state' using errcode='22023';
 end if;
 update btb_private.triangle_discovery_leads
  set review_state=p_state where id=p_id;
end $$;
revoke all on function public.btb_admin_update_discovery_lead(uuid,text) from public,anon,authenticated;
grant execute on function public.btb_admin_update_discovery_lead(uuid,text) to authenticated,service_role;

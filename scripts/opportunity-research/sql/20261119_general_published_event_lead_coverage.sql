-- A published event may cover multiple organizer-linked research URLs.
-- The worker must attest a current official root link, and for category paths
-- the published application hub must independently link to the same target.
alter table btb_private.triangle_discovery_leads
 add column if not exists coverage_evidence jsonb not null default '{}'::jsonb;

create or replace function public.btb_research_coverage_context()
returns jsonb language plpgsql stable security definer set search_path='' as $context$
declare result jsonb;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return '[]'::jsonb;end if;
 select coalesce(jsonb_agg(to_jsonb(x) order by x.id),'[]'::jsonb)
 into result from (
  select o.id,o.title,o.publication,o.application_url,o.source_url,
   o.city,m.organizer as market_organizer,m.city as market_city
  from public.vendor_opportunities o
  join public.markets m on m.id=o.market_id
  where o.publication='published'
   and (o.ends_on >= (now() at time zone 'America/New_York')::date
     or o.schedule_type in ('rolling_market','recurring_season','seasonal_application'))
  order by o.created_at desc limit 180
 ) x;
 return result;
end $context$;
revoke all on function public.btb_research_coverage_context() from public,anon,authenticated;
grant execute on function public.btb_research_coverage_context() to anon,authenticated,service_role;

create or replace function public.btb_research_reconcile_covered_leads(p_receipts jsonb)
returns jsonb language plpgsql security definer set search_path='' as $coverage$
declare
 item jsonb; o public.vendor_opportunities%rowtype; lead_row btb_private.triangle_discovery_leads%rowtype;
 count_resolved integer:=0; considered integer:=0;
 proof text; old_link text; new_link text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('resolved',0,'paused',true);end if;
 if jsonb_typeof(p_receipts) is distinct from 'array'
 or jsonb_array_length(p_receipts)>100 or octet_length(p_receipts::text)>80000
 then raise exception 'Invalid coverage evidence batch' using errcode='22023';end if;
 for item in select value from jsonb_array_elements(p_receipts) loop
  if jsonb_typeof(item) is distinct from 'object' then continue;end if;
  proof:=item->>'proof';
  if proof not in ('published_source','published_application','published_event_application_category')
    or (item->>'opportunity_id') is null
    or coalesce(item->>'target_url','') !~ '^https://[a-zA-Z0-9.-]+/'
    or coalesce(item->>'source_url','') !~ '^https://[a-zA-Z0-9.-]+/'
  then continue;end if;
  select * into lead_row from btb_private.triangle_discovery_leads
   where target_url=item->>'target_url'
    and source_url=item->>'source_url'
    and review_state in ('new','monitoring') limit 1 for update;
  if not found then continue;end if;
  select * into o from public.vendor_opportunities
   where id=(item->>'opportunity_id')::uuid and publication='published'
    and source_url=item->>'published_source_url'
    and application_url=item->>'published_application_url'
   limit 1;
  if not found then continue;end if;
  if lower(trim(o.city))<>lower(trim(lead_row.city))
    or regexp_replace(lower(trim(o.organizer)),'^the[[:space:]]+','')
      <>regexp_replace(lower(trim(lead_row.organizer)),'^the[[:space:]]+','')
    or split_part(lead_row.source_url,'/',3)<>split_part(o.source_url,'/',3)
  then continue;end if;
  old_link:=lead_row.target_url;
  new_link:=o.application_url;
  if proof='published_source' then
   if old_link<>o.source_url or old_link=lead_row.source_url then continue;end if;
  elsif proof='published_application' then
   if old_link<>new_link then continue;end if;
  else
   -- The Python verifier MUST have separately inspected both live link
   -- relationships. The DB rechecks the event program/host boundaries.
   if split_part(old_link,'/',3)<>split_part(new_link,'/',3)
      or split_part(old_link,'/',4)<>split_part(new_link,'/',4)
      or length(split_part(new_link,'/',4))<5
      or old_link=new_link
      or split_part(new_link,'/',4) in ('vendors','apply','applications','events')
   then continue;end if;
  end if;
  considered:=considered+1;
  update btb_private.triangle_discovery_leads
   set review_state='resolved',resolved_at=now(),
    published_opportunity_id=o.id,
    coverage_evidence=jsonb_build_object('proof',proof,'source',lead_row.source_url,
     'target',old_link,'opportunity_id',o.id,'verified_at',now())
   where id=lead_row.id and review_state in ('new','monitoring');
  if found then count_resolved:=count_resolved+1;end if;
 end loop;
 return jsonb_build_object('resolved',count_resolved,'validated',considered);
end $coverage$;
revoke all on function public.btb_research_reconcile_covered_leads(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_reconcile_covered_leads(jsonb) to anon,authenticated,service_role;

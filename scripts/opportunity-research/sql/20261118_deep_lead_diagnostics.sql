-- Store evidence-based reasons for why an independently discovered lead
-- has not been automatically published. Never store submitted form answers.
alter table btb_private.triangle_discovery_leads
 add column if not exists research_status text not null default 'not_checked',
 add column if not exists research_reason text not null default '',
 add column if not exists last_researched_at timestamptz;
do $migration$
begin
 if not exists(select 1 from pg_constraint where conrelid='btb_private.triangle_discovery_leads'::regclass
      and conname='triangle_discovery_research_status_check') then
  alter table btb_private.triangle_discovery_leads add constraint triangle_discovery_research_status_check
   check (research_status in ('not_checked','confirmed_seasonal','confirmed_rolling','restricted','closed','multi_date','form_gated','missing_event','source_unavailable','unlinked','not_application','needs_evidence'));
 end if;
end $migration$;

create or replace function public.btb_research_diagnose_leads(p_diagnostics jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare e jsonb;n int:=0;s text;reason_text text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false) then
  return jsonb_build_object('updated',0,'paused',true);
 end if;
 if jsonb_typeof(p_diagnostics) is distinct from 'array'
  or jsonb_array_length(p_diagnostics)>80
  or octet_length(p_diagnostics::text)>80000
 then raise exception 'Invalid lead diagnostic batch' using errcode='22023';end if;
 for e in select value from jsonb_array_elements(p_diagnostics) loop
  s:=e->>'status';reason_text:=coalesce(e->>'reason','');
  if s not in ('confirmed_seasonal','confirmed_rolling','restricted','closed','multi_date','form_gated',
       'missing_event','source_unavailable','unlinked','not_application','needs_evidence')
    or length(reason_text) not between 12 and 400
    or length(coalesce(e->>'target_url',''))>1200
    or length(coalesce(e->>'source_url',''))>1200
  then continue;end if;
  update btb_private.triangle_discovery_leads set research_status=s,
    research_reason=reason_text,last_researched_at=now()
  where target_url=e->>'target_url'
    and source_url=e->>'source_url'
    and review_state='new';
  if found then n:=n+1;end if;
 end loop;
 return jsonb_build_object('updated',n);
end $$;
revoke all on function public.btb_research_diagnose_leads(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_diagnose_leads(jsonb) to anon,authenticated,service_role;

create or replace function public.btb_admin_discovery_leads()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare result jsonb;
begin
 if not coalesce(public.btb_is_admin(),false) then
  raise exception 'Admin access required' using errcode='42501';
 end if;
 select coalesce(jsonb_agg(to_jsonb(q) order by q.first_seen desc),'[]'::jsonb)
 into result from (
  select id,target_url,source_url,title,organizer,city,notes,review_state,
         first_seen,last_seen,research_status,research_reason,last_researched_at
  from btb_private.triangle_discovery_leads where review_state='new'
  order by first_seen desc limit 100
 ) q;
 return result;
end $$;
revoke all on function public.btb_admin_discovery_leads() from public,anon,authenticated;
grant execute on function public.btb_admin_discovery_leads() to authenticated,service_role;

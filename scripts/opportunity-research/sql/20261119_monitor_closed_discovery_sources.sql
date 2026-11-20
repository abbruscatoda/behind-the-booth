-- Keep clearly closed/restricted sources under daily watch without showing them
-- in the actionable 'New vendor-application leads' admin queue.
-- Directory/self-link pseudo-leads are resolved, not mistaken for opportunities.
alter table btb_private.triangle_discovery_leads
 drop constraint if exists triangle_discovery_leads_review_state_check;
alter table btb_private.triangle_discovery_leads
 add constraint triangle_discovery_leads_review_state_check
 check (review_state in ('new','monitoring','ignored','resolved'));

create or replace function public.btb_research_discovery_backlog()
returns jsonb language plpgsql stable security definer set search_path='' as $backlog$
declare output jsonb;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return '[]'::jsonb;end if;
 select coalesce(jsonb_agg(to_jsonb(q) order by q.research_priority,q.target_url),'[]'::jsonb)
 into output from (
  select target_url,source_url,title,organizer,city,notes,last_seen,
   last_researched_at,review_state,
   row_number() over(order by last_researched_at asc nulls first,last_seen desc,target_url) as research_priority
  from btb_private.triangle_discovery_leads
  where review_state in ('new','monitoring')
  order by last_researched_at asc nulls first,last_seen desc,target_url
  limit 160
 ) q;
 return output;
end $backlog$;
revoke all on function public.btb_research_discovery_backlog() from public,anon,authenticated;
grant execute on function public.btb_research_discovery_backlog() to anon,authenticated,service_role;

create or replace function public.btb_research_diagnose_leads(p_diagnostics jsonb)
returns jsonb language plpgsql security definer set search_path='' as $diagnose$
declare e jsonb;n int:=0;s text;reason_text text; target text;src text; next_state text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('updated',0,'paused',true);end if;
 if jsonb_typeof(p_diagnostics) is distinct from 'array'
  or jsonb_array_length(p_diagnostics)>80
  or octet_length(p_diagnostics::text)>80000
 then raise exception 'Invalid lead diagnostic batch' using errcode='22023';end if;
 for e in select value from jsonb_array_elements(p_diagnostics) loop
  s:=e->>'status';reason_text:=coalesce(e->>'reason','');
  target:=coalesce(e->>'target_url','');src:=coalesce(e->>'source_url','');
  if s not in ('confirmed_seasonal','confirmed_rolling','restricted','closed','multi_date','form_gated',
    'missing_event','source_unavailable','unlinked','not_application','needs_evidence')
   or length(reason_text) not between 12 and 400
   or length(target)>1200 or length(src)>1200
  then continue;end if;
  -- Monitor temporary closed and invite-only applications; re-activate them
  -- if a later source check finds an eligible state.
  next_state:=case
   when s in ('closed','restricted') then 'monitoring'
   when s='not_application'
       and (rtrim(target,'/#')=rtrim(src,'/#') or right(target,2)='/#')
       then 'resolved'
   when s='source_unavailable' then null
   else 'new' end;
  update btb_private.triangle_discovery_leads set
   research_status=s,research_reason=reason_text,last_researched_at=now(),
   review_state=case when next_state is null then review_state else next_state end,
   resolved_at=case when next_state='resolved' then now() else resolved_at end
  where target_url=target and source_url=src
   and review_state in ('new','monitoring');
  if found then n:=n+1;end if;
 end loop;
 return jsonb_build_object('updated',n);
end $diagnose$;
revoke all on function public.btb_research_diagnose_leads(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_diagnose_leads(jsonb) to anon,authenticated,service_role;

-- Reconcile stale diagnostic rows only when the stored result is unambiguous.
update btb_private.triangle_discovery_leads set review_state='monitoring'
where review_state='new' and research_status in ('closed','restricted');
update btb_private.triangle_discovery_leads set review_state='resolved',resolved_at=now()
where review_state='new' and research_status='not_application'
  and (rtrim(target_url,'/#')=rtrim(source_url,'/#') or right(target_url,2)='/#');

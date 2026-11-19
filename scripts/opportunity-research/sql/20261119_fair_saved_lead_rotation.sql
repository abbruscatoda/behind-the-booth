-- Rotate unresolved source research fairly, including older saved leads.
-- This worker-only endpoint exposes no user/application response data.
create or replace function public.btb_research_discovery_backlog()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare output jsonb;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return '[]'::jsonb; end if;
 select coalesce(jsonb_agg(to_jsonb(q) order by q.research_priority,q.target_url),'[]'::jsonb)
 into output from (
  select target_url,source_url,title,organizer,city,notes,last_seen,last_researched_at,
   row_number() over (order by last_researched_at asc nulls first,last_seen desc,target_url) as research_priority
  from btb_private.triangle_discovery_leads
  where review_state='new'
  order by last_researched_at asc nulls first,last_seen desc,target_url
  limit 160
 ) q;
 return output;
end $$;
revoke all on function public.btb_research_discovery_backlog() from public,anon,authenticated;
grant execute on function public.btb_research_discovery_backlog() to anon,authenticated,service_role;

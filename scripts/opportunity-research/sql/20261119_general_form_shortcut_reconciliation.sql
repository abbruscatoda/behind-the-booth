-- Generalized source-linked URL identity reconciliation.
-- The worker verifies the official organizer page currently links to the
-- public forms.gle shortcut and follows only trusted redirects. This RPC
-- never creates an opportunity or assumes that an application is open.
create or replace function public.btb_research_reconcile_form_shortcuts(p_receipts jsonb)
returns jsonb language plpgsql security definer set search_path='' as $reconcile$
declare receipt jsonb; n int:=0; examined int:=0; lead_id uuid; opp_id uuid;
 source text; shortcut text; canonical text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('resolved',0,'paused',true);end if;
 if jsonb_typeof(p_receipts) is distinct from 'array'
    or jsonb_array_length(p_receipts)>24
    or octet_length(p_receipts::text)>32000
 then raise exception 'Invalid shortcut reconciliation batch' using errcode='22023';end if;
 for receipt in select value from jsonb_array_elements(p_receipts) loop
   source:=receipt->>'source_url';
   shortcut:=receipt->>'target_url';
   canonical:=receipt->>'canonical_application_url';
   if source is null or length(source)>1200
      or shortcut !~ '^https://forms[.]gle/[A-Za-z0-9_-]{6,60}$'
      or canonical !~ '^https://docs[.]google[.]com/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform$'
   then continue;end if;
   examined:=examined+1;
   select l.id into lead_id
   from btb_private.triangle_discovery_leads l
   where l.source_url=source and l.target_url=shortcut and l.review_state in ('new','monitoring')
   limit 1 for update;
   if lead_id is null then continue;end if;
   select o.id into opp_id from public.vendor_opportunities o
   join btb_private.triangle_discovery_leads l on l.id=lead_id
   where o.publication='published'
     and o.application_url=canonical
     and lower(trim(o.organizer))=lower(trim(l.organizer))
     and lower(trim(o.city))=lower(trim(l.city))
     -- The shortcut must be on the approved organizer host for the published
     -- opportunity; form identity alone cannot borrow another event.
     and split_part(l.source_url,'/',3)=split_part(o.source_url,'/',3)
   order by o.verified_at desc nulls last,o.id limit 1;
   if opp_id is null then continue;end if;
   update btb_private.triangle_discovery_leads
    set review_state='resolved',published_opportunity_id=opp_id,resolved_at=now()
    where id=lead_id and review_state in ('new','monitoring');
   if found then n:=n+1;end if;
   lead_id:=null;opp_id:=null;
 end loop;
 return jsonb_build_object('resolved',n,'examined',examined);
end $reconcile$;
revoke all on function public.btb_research_reconcile_form_shortcuts(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_reconcile_form_shortcuts(jsonb) to anon,authenticated,service_role;

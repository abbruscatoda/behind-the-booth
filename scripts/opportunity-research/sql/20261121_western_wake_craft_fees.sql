-- Evidence-gated Winter Wonderland Craft Fair price and availability publisher.
-- The organizer's currently linked PDF can establish the *craft application* fee;
-- an event-specific booth fee requires a readable organizer-linked Google Form.
-- Applied to live Supabase before the worker policy is enabled.
CREATE OR REPLACE FUNCTION public.btb_research_publish_western_craft(p_result jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
 c jsonb:=p_result->'candidate';
 v_checked timestamptz;
 v_fee numeric;
 v_booth numeric;
 v_item public.vendor_opportunities;
 v_evidence jsonb:=p_result->'fee_evidence';
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false) then
  return jsonb_build_object('action','skipped','reason','Research disabled');
 end if;
 if octet_length(p_result::text)>15000
    or p_result->>'policy' is distinct from 'western-wake-craft-official-v1'
    or p_result->>'decision' is distinct from 'publish'
    or jsonb_typeof(c) is distinct from 'object'
    or jsonb_typeof(v_evidence) is distinct from 'object'
    or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
    or coalesce(p_result->>'application_page_hash','') !~ '^[a-f0-9]{64}$'
    or length(coalesce(p_result->>'evidence','')) not between 120 and 700
    or p_result->>'fee_pdf_url' !~* '^https://westernwakefarmersmarket[.]org/s/[a-z0-9._-]{5,160}[.]pdf$'
    or p_result->>'fee_pdf_url' not ilike '%fee%'
    or p_result->>'fee_pdf_url' not ilike '%schedule%'
 then raise exception 'Missing official Western Wake craft evidence' using errcode='22023';end if;
 v_checked:=nullif(p_result->>'checked_at','')::timestamptz;
 if v_checked is null or not isfinite(v_checked)
    or v_checked<now()-interval '6 hours'
    or v_checked>now()+interval '5 minutes'
    or c->>'market_slug' is distinct from 'western-wake-farmers-market'
    or c->>'title' is distinct from 'Winter Wonderland Craft Fair — Western Wake Farmers Market'
    or c->>'organizer' is distinct from 'Western Wake Farmers Market'
    or c->>'city' is distinct from 'Morrisville'
    or c->>'state' is distinct from 'NC'
    or c->>'starts_on' is distinct from '2026-12-12'
    or c->>'ends_on' is distinct from '2026-12-12'
    or c->>'schedule_type' is distinct from 'dated_event'
    or c->>'deadline' is not null
    or c->>'availability' not in ('open','closed')
    or c->>'source_url' is distinct from 'https://westernwakefarmersmarket.org/events/winterwonderland2026'
    or c->>'application_url' is distinct from 'https://forms.gle/Xr31Pkd6MierZ2UK9'
    or c->>'deposit' is not null
    or c->'categories' is distinct from '[]'::jsonb
    or length(coalesce(c->>'fee_notes','')) not between 100 and 2000
    or length(coalesce(c->>'eligibility','')) not between 80 and 2000
    or length(coalesce(c->>'research_notes','')) not between 120 and 2000
 then raise exception 'Winter craft application identity or terms do not match' using errcode='22023';end if;
 if (now() at time zone 'America/New_York')::date>'2026-11-28'::date
    and c->>'availability' is distinct from 'closed'
 then raise exception 'Past craft fair application cutoff' using errcode='22023';end if;
 if c->'application_fee' is distinct from v_evidence->'application_fee'
    or c->'booth_fee' is distinct from v_evidence->'booth_fee'
 then raise exception 'Fee receipt mismatch' using errcode='22023';end if;
 if c->>'application_fee' is not null then
  if c->>'application_fee' !~ '^[0-9]{1,4}([.][0-9]{1,2})?$'
    or (
      not (
       c->'application_fee' = v_evidence->'pdf_craft_fee'
       and coalesce(p_result->>'fee_pdf_hash','') ~ '^[a-f0-9]{64}$'
      )
      and not (
       c->'application_fee' = v_evidence->'form_application_fee'
       and p_result->>'application_access'='readable_first_page'
       and coalesce(p_result->>'application_hash','') ~ '^[a-f0-9]{64}$'
      )
    )
  then raise exception 'Craft fee lacks PDF or form-backed receipt' using errcode='22023';end if;
  v_fee:=(c->>'application_fee')::numeric;
  if v_fee<=0 or v_fee>500 then raise exception 'Craft fee out of range' using errcode='22023';end if;
 end if;
 if c->>'booth_fee' is not null then
  if c->>'booth_fee' !~ '^[0-9]{1,4}([.][0-9]{1,2})?$'
     or p_result->>'application_access' is distinct from 'readable_first_page'
     or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$'
     or c->'booth_fee' is distinct from v_evidence->'form_booth_fee'
  then raise exception 'Unverified event-specific booth fee' using errcode='22023';end if;
  v_booth:=(c->>'booth_fee')::numeric;
  if v_booth<=0 or v_booth>1500 then raise exception 'Booth price outside safe limits' using errcode='22023';end if;
 end if;
 perform pg_advisory_xact_lock(hashtextextended('western-wake-2026-winter-craft',2));
 select * into v_item from public.vendor_opportunities
 where id='bf8b4727-556b-499a-af38-0902c997d13b'::uuid for update;
 if not found then
  return jsonb_build_object('action','skipped','reason','Approved craft listing missing');
 end if;
 if v_item.publication is distinct from 'published'
    or v_item.automation_hold
    or v_item.verification_policy is distinct from 'western-wake-craft-official-v1'
    or v_item.source_url is distinct from c->>'source_url'
    or v_item.application_url is distinct from c->>'application_url'
    or v_item.starts_on is distinct from '2026-12-12'::date
    or v_item.ends_on is distinct from '2026-12-12'::date
 then return jsonb_build_object('action','skipped','reason','Listing is held or its verified identity changed');end if;
 update public.vendor_opportunities set
   availability=c->>'availability',
   review_state=case when c->>'availability'='closed' then 'closed' else 'verified' end,
   review_reason='',
   booth_fee=coalesce(v_booth,v_item.booth_fee),
   application_fee=coalesce(v_fee,v_item.application_fee),
   fee_notes=case when v_fee is null and v_item.application_fee is not null
         then v_item.fee_notes else c->>'fee_notes' end,
   eligibility=c->>'eligibility',
   research_notes=c->>'research_notes',
   verified_at=v_checked,last_checked_at=now(),updated_at=now()
 where id=v_item.id;
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(v_item.id,'publish','Official dated craft fair and organizer fee schedule automatically verified; Google Form access may be blocked.',
   jsonb_build_object('policy',p_result->>'policy',
     'source',c->>'source_url','application',c->>'application_url',
     'source_hash',p_result->>'source_hash',
     'application_page_hash',p_result->>'application_page_hash',
     'fee_pdf_url',p_result->>'fee_pdf_url','fee_pdf_hash',p_result->>'fee_pdf_hash',
     'form_access',p_result->>'application_access','form_hash',p_result->>'application_hash',
     'checked_at',v_checked));
 return jsonb_build_object('action','publish','id',v_item.id,'reason','Verified organizer craft fair and supported fees');
end $function$
;
revoke all on function public.btb_research_publish_western_craft(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_publish_western_craft(jsonb) to anon,authenticated,service_role;

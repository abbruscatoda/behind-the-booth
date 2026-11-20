-- Official organizer-linked multi-date Jotform publication.
-- A date offered by the active vendor application is independently verified
-- from the form, not inferred from a generic application directory.
create or replace function public.btb_research_publish_multidate(p_result jsonb)
returns jsonb language plpgsql security definer set search_path='' as $publish$
declare
 c jsonb:=p_result->'candidate';
 checked timestamptz; event_day date; mid uuid; occurrence uuid; opportunity uuid;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('action','skipped','reason','Automation paused');end if;
 if octet_length(p_result::text)>16000
   or p_result->>'policy' is distinct from 'triangle-multidate-jotform-v1'
   or p_result->>'decision' is distinct from 'publish'
   or p_result->'form_complete' is distinct from 'true'::jsonb
   or p_result->'form_readable' is distinct from 'true'::jsonb
   or p_result->'date_verified' is distinct from 'true'::jsonb
   or p_result->'fee_verified' is distinct from 'true'::jsonb
   or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$'
   or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
   or length(coalesce(p_result->>'evidence','')) not between 80 and 600
 then raise exception 'Unverified multi-date application request' using errcode='22023';end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 event_day:=nullif(c->>'starts_on','')::date;
 if checked is null or checked<now()-interval '6 hours' or checked>now()+interval '5 minutes'
   or event_day is null or event_day<(now() at time zone 'America/New_York')::date+2
   or event_day>(now() at time zone 'America/New_York')::date+183
   or extract(year from event_day)<>2026
   or c->>'ends_on' is distinct from c->>'starts_on'
   or c->>'market_slug' is distinct from 'cary-night-market'
   or c->>'organizer' is distinct from 'The Night Market Company'
   or c->>'city' is distinct from 'Cary'
   or c->>'state' is distinct from 'NC'
   or c->>'venue' is distinct from 'Downtown Cary Park'
   or c->>'source_url' is distinct from 'https://thenightmarketcompany.com/plan-your-markets-vendor-info'
   or c->>'application_url' is distinct from 'https://pci.jotform.com/form/253207413592151'
   or p_result->>'organizer_root' is distinct from 'https://thenightmarketcompany.com/'
   or c->>'title' is distinct from 'Cary Night Market — '||trim(to_char(event_day,'FMMonth'))||' '||extract(day from event_day)::int||', '||extract(year from event_day)::int
   or c->>'schedule_type' is distinct from 'dated_event'
   or c->>'availability' is distinct from 'open'
   or c->>'deadline' is not null
   or coalesce(c->>'booth_fee','') not in ('140','160')
   or c->>'application_fee' is distinct from '10'
   or c->'categories' is distinct from '[]'::jsonb
   or length(coalesce(c->>'fee_notes',''))>2000
   or length(coalesce(c->>'eligibility',''))>2000
   or length(coalesce(c->>'research_notes',''))>4000
 then raise exception 'Multi-date source or date violates approved organizer policy' using errcode='22023';end if;
 select id into mid from public.markets
 where slug='cary-night-market' and name='Cary Night Market' and city='Cary'
 and organizer='The Night Market Company' and not is_hidden and not is_sample
 for update;
 if not found then raise exception 'Matching market profile is not approved' using errcode='22023';end if;
 perform pg_advisory_xact_lock(hashtextextended('cary-night-market:'||event_day::text,0));
 select id into opportunity from public.vendor_opportunities
 where market_id=mid and starts_on=event_day and publication='published' order by id limit 1 for update;
 if found then
   return jsonb_build_object('action','skipped','id',opportunity,'reason','Market date already published; existing listing not overwritten');
 end if;
 insert into public.market_occurrences(market_id,starts_on,ends_on,title)
 values(mid,event_day,event_day,c->>'title')
 on conflict(market_id,starts_on,ends_on) do update set title=excluded.title returning id into occurrence;
 insert into public.vendor_opportunities
 (title,market_id,occurrence_id,organizer,city,state,venue,starts_on,ends_on,
 deadline,application_url,source_url,availability,booth_fee,application_fee,deposit,
 categories,fee_notes,eligibility,research_notes,publication,verified_at,
 last_checked_at,review_state,review_reason,verification_policy,schedule_type)
 values(c->>'title',mid,occurrence,'The Night Market Company','Cary','NC','Downtown Cary Park',
 event_day,event_day,null,c->>'application_url',c->>'source_url','open',
 (c->>'booth_fee')::numeric,10,null,'{}'::text[],
 c->>'fee_notes',c->>'eligibility',c->>'research_notes',
 'published',checked,now(),'verified','','triangle-multidate-jotform-v1','dated_event')
 returning id into opportunity;
 update btb_private.triangle_discovery_leads
 set review_state='resolved',published_opportunity_id=opportunity,resolved_at=now()
 where review_state='new' and target_url=c->>'application_url'
   and source_url='https://thenightmarketcompany.com/';
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(opportunity,'publish','Organizer-linked future date and submit action independently verified in multi-date retail application',
 jsonb_build_object('policy',p_result->>'policy','source',c->>'source_url','form',c->>'application_url',
 'source_hash',p_result->>'source_hash','application_hash',p_result->>'application_hash',
 'event_date',event_day,'checked',checked));
 return jsonb_build_object('action','publish','id',opportunity,'reason','Future date offered in active organizer-linked retail application');
end $publish$;
revoke all on function public.btb_research_publish_multidate(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_publish_multidate(jsonb) to anon,authenticated,service_role;

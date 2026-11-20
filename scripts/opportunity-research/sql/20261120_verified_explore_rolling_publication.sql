-- General Explore Markets -> ongoing application publisher.
-- This is worker-secret-gated; callers may only publish under an existing,
-- visible market whose official website and linked application match the
-- proof returned by the deterministic public-form verifier.
create or replace function public.btb_research_publish_verified_rolling(p_result jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 c jsonb:=p_result->'candidate';
 checked timestamptz;
 start_day date;end_day date;
 m public.markets; old public.vendor_opportunities;
 occ uuid; target uuid;
 root_host text;src_host text;app_host text;
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('action','skipped','reason','Research disabled');end if;
 if octet_length(p_result::text)>16000
  or p_result->>'policy' is distinct from 'explore-rolling-official-v1'
  or p_result->>'decision' is distinct from 'publish'
  or jsonb_typeof(c) is distinct from 'object'
  or coalesce(p_result->>'market_source_hash','') !~ '^[a-f0-9]{64}$'
  or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
  or coalesce(p_result->>'application_hash','') !~ '^[a-f0-9]{64}$'
  or length(coalesce(p_result->>'evidence','')) not between 120 and 550
 then raise exception 'Unverified rolling-source receipt' using errcode='22023';end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 start_day:=nullif(c->>'starts_on','')::date;
 end_day:=nullif(c->>'ends_on','')::date;
 if checked is null or not isfinite(checked)
  or checked<now()-interval '6 hours' or checked>now()+interval '5 minutes'
  or start_day<>make_date(extract(year from (now() at time zone 'America/New_York'))::int,1,1)
  or end_day<>make_date(extract(year from start_day)::int+1,12,31)
  or length(coalesce(c->>'market_slug','')) not between 4 and 100
  or length(coalesce(c->>'title','')) not between 20 and 160
  or c->>'title' is distinct from (c->>'market_name')||' — Rolling Vendor Applications'
  or c->>'schedule_type' is distinct from 'rolling_market'
  or c->>'availability' is distinct from 'open'
  or c->>'deadline' is not null
  or c->>'state' is distinct from 'NC'
  or c->>'booth_fee' is not null or c->>'application_fee' is not null
  or c->>'deposit' is not null or c->'categories' is distinct from '[]'::jsonb
  or length(coalesce(c->>'fee_notes','')) not between 80 and 2000
  or length(coalesce(c->>'eligibility','')) not between 100 and 2000
  or length(coalesce(c->>'research_notes','')) not between 100 and 2000
 then raise exception 'Invalid or invented recurring application details' using errcode='22023';end if;
 root_host:=lower(regexp_replace(coalesce(substring(c->>'market_url' from '^https://([^/?#]+)'),''),'^www[.]',''));
 src_host:=lower(regexp_replace(coalesce(substring(c->>'source_url' from '^https://([^/?#]+)'),''),'^www[.]',''));
 app_host:=lower(regexp_replace(coalesce(substring(c->>'application_url' from '^https://([^/?#]+)'),''),'^www[.]',''));
 if root_host='' or root_host<>src_host
  or c->>'market_url' !~ '^https://[^?#]+$'
  or c->>'source_url' !~ '^https://[^?#]+$'
  or c->>'application_url' !~ '^https://[^?#]+$'
  or (app_host<>root_host and app_host not in ('form.jotform.com','pci.jotform.com','docs.google.com','forms.gle'))
  or (app_host='docs.google.com' and c->>'application_url' !~ '^https://docs[.]google[.]com/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform$')
  or (app_host='forms.gle' and c->>'application_url' !~ '^https://forms[.]gle/[A-Za-z0-9_-]{6,60}$')
  or (app_host='form.jotform.com' and c->>'application_url' !~ '^https://form[.]jotform[.]com/[0-9]{10,20}$')
  or (app_host='pci.jotform.com' and c->>'application_url' !~ '^https://pci[.]jotform[.]com/form/[0-9]{10,20}$')
 then raise exception 'Untrusted organizer or application URL' using errcode='22023';end if;

 perform pg_advisory_xact_lock(hashtextextended('rolling:'||c->>'market_slug',3));
 select * into m from public.markets where slug=c->>'market_slug' for update;
 if not found then return jsonb_build_object('action','skipped','reason','Market must already exist');end if;
 if m.is_hidden or m.is_sample or m.state<>'NC'
   or m.name is distinct from c->>'market_name'
   or m.city is distinct from c->>'city'
   or m.website_url is distinct from c->>'market_url'
 then return jsonb_build_object('action','skipped','reason','Market identity or visibility has changed');end if;
 -- Never attach a second organizer to an application already published or
 -- archived under another market.
 if exists(select 1 from public.vendor_opportunities
  where application_url=c->>'application_url' and market_id is distinct from m.id
   and publication in ('published','archived'))
 then return jsonb_build_object('action','skipped','reason','Application belongs to another market');end if;
 select * into old from public.vendor_opportunities
  where market_id=m.id and schedule_type='rolling_market'
    and publication='published'
  order by updated_at desc limit 1 for update;
 if found and (
   old.automation_hold
   or old.verification_policy is distinct from 'explore-rolling-official-v1'
   or old.application_url is distinct from c->>'application_url'
   or old.source_url is distinct from c->>'source_url'
 ) then return jsonb_build_object('action','skipped','reason','Existing rolling opportunity protected');end if;
 if not found and exists(select 1 from public.vendor_opportunities
  where market_id=m.id and publication='archived'
    and (schedule_type='rolling_market' or application_url=c->>'application_url'))
 then return jsonb_build_object('action','skipped','reason','Archived opportunity protected');end if;

 insert into public.market_occurrences(market_id,starts_on,ends_on,title)
 values(m.id,start_day,end_day,c->>'title')
 on conflict(market_id,starts_on,ends_on) do nothing;
 select id into occ from public.market_occurrences where market_id=m.id
 and starts_on=start_day and ends_on=end_day;
 if occ is null then raise exception 'Coverage occurrence could not be resolved';end if;
 if old.id is null then
  insert into public.vendor_opportunities(
   title,market_id,occurrence_id,organizer,city,state,venue,
   starts_on,ends_on,deadline,application_url,source_url,categories,
   availability,booth_fee,application_fee,deposit,fee_notes,eligibility,
   research_notes,publication,verified_at,last_checked_at,
   review_state,review_reason,verification_policy,schedule_type)
  values(c->>'title',m.id,occ,c->>'organizer',m.city,'NC',c->>'venue',
   start_day,end_day,null,c->>'application_url',c->>'source_url','{}'::text[],
   'open',null,null,null,c->>'fee_notes',c->>'eligibility',
   c->>'research_notes','published',checked,now(),
   'verified','','explore-rolling-official-v1','rolling_market')
  returning id into target;
 else
  target:=old.id;
  update public.vendor_opportunities set
   title=c->>'title',occurrence_id=occ,starts_on=start_day,ends_on=end_day,
   availability='open',deadline=null,fee_notes=c->>'fee_notes',
   eligibility=c->>'eligibility',research_notes=c->>'research_notes',
   verified_at=checked,last_checked_at=now(),review_state='verified',
   review_reason='',updated_at=now()
  where id=target;
 end if;
 insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
 values(target,'publish','Organizer-owned rolling intake and matching public form independently verified.',
  jsonb_build_object('policy',p_result->>'policy','market',m.slug,
   'source',c->>'source_url','application',c->>'application_url',
   'checked_at',checked,'market_hash',p_result->>'market_source_hash',
   'source_hash',p_result->>'source_hash','form_hash',p_result->>'application_hash'));
 return jsonb_build_object('action','publish','id',target,'reason','Verified existing market rolling application');
end $$;
revoke all on function public.btb_research_publish_verified_rolling(jsonb) from public,anon,authenticated;
grant execute on function public.btb_research_publish_verified_rolling(jsonb) to anon,authenticated,service_role;

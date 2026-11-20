-- Verified discovery links are evidence, not standalone opportunities.
-- Reconcile *exactly matched* links against published opportunities without
-- hiding other programs operated by the same market.
alter table btb_private.triangle_discovery_leads
 add column if not exists published_opportunity_id uuid references public.vendor_opportunities(id) on delete set null,
 add column if not exists resolved_at timestamptz;

create or replace function btb_private.resolve_published_discovery_leads()
returns integer language plpgsql security definer set search_path='' as $
begin
 with matching as (
  select l.id as lead_id, o.id as opportunity_id,
   row_number() over (partition by l.id order by o.verified_at desc nulls last,o.id) as precedence
  from btb_private.triangle_discovery_leads l
  join public.vendor_opportunities o
   on o.publication='published'
    and lower(trim(o.organizer))=lower(trim(l.organizer))
    and lower(trim(o.city))=lower(trim(l.city))
  where l.review_state='new'
    and (
      -- The exact published form is this lead's destination.
      l.target_url=o.application_url
      -- For recurring intakes, the official vendor application landing page
      -- is also evidence. Never resolve a generic organizer directory.
      or (o.schedule_type in ('rolling_market','seasonal_application','recurring_season')
          and l.target_url=o.source_url and l.target_url<>l.source_url)
      -- Verified direct-link alias: official WWFM 26/27 homepage form
      -- redirects to the same published regular-vendor Google Form.
      -- The separate craft fair link is NOT an alias.
      or (o.title='Western Wake Farmers Market — Rolling Vendor Applications'
          and o.source_url='https://westernwakefarmersmarket.org/apply'
          and o.application_url='https://forms.gle/DmuLW5ni7Bu3Avhj8'
          and l.source_url='https://westernwakefarmersmarket.org/'
          and l.target_url='https://forms.gle/NSUe3V11UyUW3K997')
    )
 )
 update btb_private.triangle_discovery_leads l
 set review_state='resolved',
     published_opportunity_id=m.opportunity_id,
     resolved_at=now()
 from matching m
 where l.id=m.lead_id and m.precedence=1 and l.review_state='new';
 return 1;
end $;

revoke all on function btb_private.resolve_published_discovery_leads() from public,anon,authenticated;

create or replace function btb_private.reconcile_discovery_trigger()
returns trigger language plpgsql security definer set search_path='' as $$
begin
 perform btb_private.resolve_published_discovery_leads();
 return null;
end $$;
revoke all on function btb_private.reconcile_discovery_trigger() from public,anon,authenticated;

drop trigger if exists btb_reconcile_published_opportunity_leads on public.vendor_opportunities;
create trigger btb_reconcile_published_opportunity_leads
after insert or update of publication,source_url,application_url
on public.vendor_opportunities
for each statement execute function btb_private.reconcile_discovery_trigger();

drop trigger if exists btb_reconcile_new_discovery_leads on btb_private.triangle_discovery_leads;
create trigger btb_reconcile_new_discovery_leads
after insert or update of source_url,target_url
on btb_private.triangle_discovery_leads
for each statement execute function btb_private.reconcile_discovery_trigger();

-- Backfill the already published opportunities and their pending source leads.
do $backfill$ begin
 perform btb_private.resolve_published_discovery_leads();
end $backfill$;

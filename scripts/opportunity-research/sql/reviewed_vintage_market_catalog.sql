-- Confirmed local markets belong in Explore independently of open intake.
-- Only reviewed source-bound catalog identities can be created by this RPC.
create table if not exists btb_private.market_catalog_receipts(
 catalog_key text primary key, market_id uuid not null references public.markets(id),
 source_url text not null, source_hash text not null, checked_at timestamptz not null
);
alter table btb_private.market_catalog_receipts enable row level security;
revoke all on btb_private.market_catalog_receipts from public,anon,authenticated;
create or replace function public.btb_research_publish_market_catalog(p_result jsonb)
returns jsonb language plpgsql security definer set search_path='' as $function$
declare
 catalog constant jsonb := $catalog${"nc-vintage-haven": {"slug": "nc-vintage-market-at-haven-farm", "name": "NC Vintage Market at Haven Farm", "city": "Knightdale", "organizer": "NC Vintage Market", "source": "https://www.eventbrite.com/o/nc-vintage-market-121068658483", "description": "NC Vintage Market at Haven Farm is a curated vendor market in Knightdale featuring vintage clothing, accessories, jewelry, home goods, and reworked items. Event details and participating vendors vary by edition."}, "nc-vintage-bazaar": {"slug": "nc-vintage-bazaar", "name": "NC Vintage Bazaar", "city": "Raleigh", "organizer": "NC Vintage Bazaar", "source": "https://ncvintagebazaar.com/", "description": "NC Vintage Bazaar is a vintage and secondhand market held at the North Carolina State Fairgrounds in Raleigh. Vendors offer clothing, accessories, and other vintage wearables. Dates and vendor lineups vary by event."}, "patchwork-durham": {"slug": "the-patchwork-market", "name": "The Patchwork Market", "city": "Durham", "organizer": "The Patchwork Market", "source": "https://thepatchworkmarket.com/applytobeavendor/", "description": "The Patchwork Market is a curated vendor market at the Durham Armory featuring handmade goods from local and regional makers. Vendor lineups, booth options, and application periods vary by edition."}, "rebus-sunday": {"slug": "rebus-sunday-funday-market", "name": "Rebus Sunday Funday Market", "city": "Raleigh", "organizer": "Rebus Works", "source": "https://www.rebusworks.us/sundayfundaymarket", "description": "Rebus Sunday Funday Market is a recurring curated market at Rebus Works in Raleigh, featuring small businesses, makers, and vintage sellers. Check the organizer for current dates and vendor participation details."}, "raleigh-retro-markets": {"slug": "raleigh-retro-gamers-markets", "name": "Raleigh Retro Gamers Markets", "city": "Raleigh", "organizer": "Raleigh Retro Gamers", "source": "https://raleighretrogamers.com/vendors/", "description": "Raleigh Retro Gamers organizes gaming and pop-culture vendor markets across Raleigh and the Triangle. Events feature retro and modern games, collectibles, vintage toys, clothing, and related goods. Venues, booth costs, and eligibility vary by event."}}$catalog$;
 key text:=p_result->>'catalog_key'; expected jsonb; checked timestamptz;
 existing public.markets; action_text text:='existing';
begin
 perform public.btb_research_authorize();
 if not coalesce((select enabled from public.btb_research_settings where id=true),false)
 then return jsonb_build_object('action','skipped','reason','Research disabled');end if;
 expected:=catalog->key;
 if expected is null or octet_length(p_result::text)>5000
  or p_result->>'policy' is distinct from 'reviewed-market-catalog-v1'
  or p_result->>'source_url' is distinct from expected->>'source'
  or coalesce(p_result->>'source_hash','') !~ '^[a-f0-9]{64}$'
  or length(coalesce(p_result->>'evidence','')) not between 100 and 600
 then raise exception 'Unverified market catalog identity' using errcode='22023';end if;
 checked:=nullif(p_result->>'checked_at','')::timestamptz;
 if checked is null or not isfinite(checked) or checked<now()-interval '6 hours' or checked>now()+interval '5 minutes'
 then raise exception 'Stale market catalog evidence' using errcode='22023';end if;
 perform pg_advisory_xact_lock(hashtextextended('market-catalog:'||key,9));
 select * into existing from public.markets m
 where m.slug=expected->>'slug' or (
  lower(m.city)=lower(expected->>'city') and m.state='NC'
  and regexp_replace(lower(m.name),'[^a-z0-9]','','g')=regexp_replace(lower(expected->>'name'),'[^a-z0-9]','','g'))
 order by (m.slug=expected->>'slug') desc limit 1 for update;
 if found then
  if existing.is_hidden or existing.is_sample or existing.city is distinct from expected->>'city'
    or existing.state is distinct from 'NC'
    or regexp_replace(lower(existing.name),'[^a-z0-9]','','g') is distinct from regexp_replace(lower(expected->>'name'),'[^a-z0-9]','','g')
  then return jsonb_build_object('action','skipped','reason','Existing profile is protected or has a conflicting identity');end if;
 else
  insert into public.markets(slug,name,city,state,organizer,description,website_url,is_sample,is_hidden)
  values(expected->>'slug',expected->>'name',expected->>'city','NC',expected->>'organizer',expected->>'description',expected->>'source',false,false)
  returning * into existing;
  action_text:='created';
 end if;
 insert into btb_private.market_catalog_receipts(catalog_key,market_id,source_url,source_hash,checked_at)
 values(key,existing.id,expected->>'source',p_result->>'source_hash',checked)
 on conflict(catalog_key) do update set market_id=excluded.market_id,source_url=excluded.source_url,source_hash=excluded.source_hash,checked_at=excluded.checked_at;
 return jsonb_build_object('action',action_text,'id',existing.id,'slug',existing.slug);
end $function$;
revoke all on function public.btb_research_publish_market_catalog(jsonb) from public;
grant execute on function public.btb_research_publish_market_catalog(jsonb) to anon,authenticated,service_role;

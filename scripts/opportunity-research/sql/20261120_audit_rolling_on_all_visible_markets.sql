-- Keep the original missing-any-opportunity count while also evaluating
-- every visible Explore Markets profile without an existing rolling listing.
create or replace function public.btb_research_market_gaps()
returns jsonb language plpgsql security definer set search_path='' as $$
declare missing jsonb; rolling jsonb;
begin
 perform public.btb_research_authorize();
 select coalesce(jsonb_agg(to_jsonb(q) order by q.name),'[]'::jsonb) into missing
 from (
  select m.slug,m.name,m.city,m.website_url
  from public.markets m
  where not m.is_hidden and not m.is_sample and m.website_url is not null
   and not exists(
    select 1 from public.vendor_opportunities o
    where o.market_id=m.id and o.publication='published'
      and o.ends_on >= (now() at time zone 'America/New_York')::date)
  order by m.name limit 100
 )q;
 select coalesce(jsonb_agg(to_jsonb(q) order by q.name),'[]'::jsonb) into rolling
 from (
  select m.slug,m.name,m.city,m.website_url
  from public.markets m
  where not m.is_hidden and not m.is_sample and m.website_url is not null
    and not exists(
      select 1 from public.vendor_opportunities o
      where o.market_id=m.id and o.publication='published'
       and o.schedule_type='rolling_market'
       and o.ends_on >= (now() at time zone 'America/New_York')::date)
  order by m.name limit 150
 )q;
 return jsonb_build_object('markets',missing,'count',jsonb_array_length(missing),
   'rolling_candidates',rolling,'rolling_candidate_count',jsonb_array_length(rolling));
end $$;
revoke all on function public.btb_research_market_gaps() from public,anon,authenticated;
grant execute on function public.btb_research_market_gaps() to anon,authenticated,service_role;

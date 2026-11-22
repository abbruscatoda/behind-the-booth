-- Require an explicit category choice for new reviews; preserve legacy reviews.
create or replace function public.btb_review_category_choice_valid(p_categories text[], p_other_category text)
returns boolean
language sql immutable
security invoker
set search_path = ''
as $$
  select coalesce(
    p_categories is not null
    and pg_catalog.cardinality(p_categories) > 0
    and pg_catalog.array_ndims(p_categories) = 1
    and pg_catalog.array_position(p_categories, null) is null
    and p_categories <@ array[
      'Food & Beverages', 'Jewelry & Accessories', 'Art & Photography',
      'Handmade Crafts', 'Clothing & Apparel', 'Bath, Body & Beauty',
      'Home Goods & Décor', 'Plants & Garden', 'Farm & Agricultural Products',
      'Pet Products', 'On-Site Services & Experiences', 'Other', 'Prefer not to disclose'
    ]::text[]
    and (not ('Prefer not to disclose' = any(p_categories))
      or (pg_catalog.cardinality(p_categories) = 1 and p_other_category is null))
    and (p_other_category is null or 'Other' = any(p_categories)), false);
$$;

revoke all on function public.btb_review_category_choice_valid(text[], text) from public, anon;
grant execute on function public.btb_review_category_choice_valid(text[], text) to authenticated, service_role;

create or replace function public.btb_validate_review_categories()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if TG_OP = 'UPDATE' then
    if new.vendor_categories is not distinct from old.vendor_categories
      and new.other_category is not distinct from old.other_category then
      return new;
    end if;
  end if;
  if not public.btb_review_category_choice_valid(new.vendor_categories, new.other_category) then
    raise exception 'Select at least one vendor category, or choose Prefer not to disclose by itself. Include Other to submit a category description.'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

revoke all on function public.btb_validate_review_categories() from public, anon;
grant execute on function public.btb_validate_review_categories() to authenticated, service_role;

drop trigger if exists btb_review_category_required on public.reviews;
create trigger btb_review_category_required
before insert or update of vendor_categories, other_category on public.reviews
for each row execute function public.btb_validate_review_categories();

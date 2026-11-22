-- Approval time is controlled by the database, never a vendor-supplied date.
alter table public.reviews add column if not exists approved_at timestamptz;
-- Historical approval timestamps were not recorded. Use the existing submission
-- date for those records rather than marking every old review new on rollout.
update public.reviews set approved_at=created_at where status='approved' and approved_at is null;
create or replace function btb_private.stamp_review_approval()
returns trigger language plpgsql set search_path='' as $function$
begin
 if TG_OP='INSERT' then
  new.approved_at:=case when new.status='approved' then now() else null end;
 elsif new.status='approved' and old.status is distinct from 'approved' then
  new.approved_at:=now();
 else
  new.approved_at:=old.approved_at;
 end if;
 return new;
end $function$;
revoke all on function btb_private.stamp_review_approval() from public,anon,authenticated;
drop trigger if exists btb_stamp_review_approval on public.reviews;
create trigger btb_stamp_review_approval before insert or update on public.reviews
for each row execute function btb_private.stamp_review_approval();

-- Keep the original RPC compatible. Only aggregate public activity is exposed;
-- vendor identity, review text and pending/rejected reviews remain private.
create or replace function public.btb_public_market_review_activity_v2()
returns table(market_id uuid,review_count bigint,overall_rating numeric,latest_review_at timestamptz)
language sql stable security definer set search_path='' as $function$
 select m.id,count(r.id),round(avg(r.overall),1),max(r.approved_at)
 from public.markets m
 left join public.reviews r on r.market_id=m.id and r.status='approved'
 where not m.is_hidden
 group by m.id;
$function$;
revoke all on function public.btb_public_market_review_activity_v2() from public;
grant execute on function public.btb_public_market_review_activity_v2() to anon,authenticated,service_role;

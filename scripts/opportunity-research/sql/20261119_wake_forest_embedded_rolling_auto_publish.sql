-- Curated Wake Forest recurring applications: verify official pages and exact
-- embedded form independently; retain public disclosure when the form cannot
-- be fully read by an automated client.
DO $migration$
DECLARE olddef text;updated text;
old_start text := $old$   and not (
      v_slug='western-wake-farmers-market'$old$;
new_start text := $new$   and not ((
      v_slug='western-wake-farmers-market'$new$;
old_end text := $old$   )
 then raise exception 'Unverified application without eligible official-source evidence'$old$;
new_end text := $new$   ) OR (
      v_slug='wake-forest-farmers-market'
      and v_schedule='rolling_market'
      and p_result->>'application_access' in ('http_auth_blocked','readable_first_page')
      and p_result->'form_complete'='false'::jsonb
      and (
       (p_result->>'application_access'='http_auth_blocked'
        and p_result->'form_readable'='false'::jsonb
        and p_result->>'application_hash' is null)
       or
       (p_result->>'application_access'='readable_first_page'
        and p_result->'form_readable'='true'::jsonb
        and coalesce(p_result->>'application_hash','') ~ '^[a-f0-9]{64}$')
      )
      and length(coalesce(p_result->>'evidence','')) between 120 and 600
      and c->>'research_notes' like '%embedded regular-vendor application%'
   ))
 then raise exception 'Unverified application without eligible official-source evidence'$new$;
old_branch text := $old$ else
  raise exception 'Seasonal organizer is not independently approved'$old$;
new_branch text := $new$ elsif v_slug='wake-forest-farmers-market' then
  if v_name is distinct from 'Wake Forest Farmers Market'
    or v_organizer is distinct from v_name
    or v_city is distinct from 'Wake Forest'
    or v_market_url is distinct from 'https://wakeforestmarket.org/vendors/become-a-vendor/'
    or v_src is distinct from 'https://wakeforestmarket.org/vendors/market-vendor-application/'
    or coalesce(v_app,'') !~ '^https://docs[.]google[.]com/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform$'
    or v_schedule is distinct from 'rolling_market'
    or v_start <> make_date(extract(year from (now() at time zone 'America/New_York'))::int,1,1)
    or v_end <> make_date(extract(year from v_start)::int+1,12,31)
    or c->>'title' is distinct from 'Wake Forest Farmers Market — Rolling Vendor Applications'
    or c->>'venue' is distinct from 'Wake Forest Farmers Market, Wake Forest, NC'
  then raise exception 'Wake Forest embedded year-round evidence does not match the approved market' using errcode='22023';end if;
 else
  raise exception 'Seasonal organizer is not independently approved'$new$;
BEGIN
 SELECT pg_get_functiondef('public.btb_research_publish_seasonal(jsonb)'::regprocedure) INTO olddef;
 IF olddef IS NULL OR position(old_start IN olddef)=0
   OR position(old_end IN olddef)=0 OR position(old_branch IN olddef)=0
 THEN RAISE EXCEPTION 'Unexpected approved seasonal publisher; no changes applied';END IF;
 updated:=replace(olddef,old_start,new_start);
 updated:=replace(updated,old_end,new_end);
 updated:=replace(updated,old_branch,new_branch);
 IF position(new_branch IN updated)=0 THEN RAISE EXCEPTION 'Wake Forest branch was not installed';END IF;
 EXECUTE updated;
END;
$migration$;

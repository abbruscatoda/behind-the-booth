-- Search categories are our taxonomy. Preserve bounded exact product wording
-- without granting permissions, changing eligibility status, or refreshing dates.
CREATE OR REPLACE FUNCTION btb_private.category_product_metadata(fact jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path='' AS $$
DECLARE term jsonb; words text; terms jsonb:='[]'::jsonb;
BEGIN
 IF jsonb_typeof(fact->'source_terms') IS DISTINCT FROM 'array' THEN RETURN '{}'::jsonb; END IF;
 IF jsonb_array_length(fact->'source_terms') NOT BETWEEN 1 AND 10 THEN RETURN '{}'::jsonb; END IF;
 FOR term IN SELECT value FROM jsonb_array_elements(fact->'source_terms') LOOP
  IF jsonb_typeof(term) IS DISTINCT FROM 'string' THEN RETURN '{}'::jsonb; END IF;
  words:=term#>>'{}';
  IF length(trim(words)) NOT BETWEEN 1 AND 180 OR position(words in coalesce(fact->>'excerpt',''))=0 THEN RETURN '{}'::jsonb; END IF;
  IF NOT terms ? words THEN terms:=terms||jsonb_build_array(words); END IF;
 END LOOP;
 RETURN jsonb_build_object('source_terms',terms);
END; $$;
REVOKE ALL ON FUNCTION btb_private.category_product_metadata(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION btb_private.category_product_metadata(jsonb) TO service_role;

CREATE OR REPLACE FUNCTION btb_private.validate_worker_categories(p_result jsonb, p_checked timestamp with time zone)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare receipt jsonb:=p_result->'category_evidence'; candidate jsonb:=p_result->'candidate';
 category text; fact jsonb; actual text[]; expected text[]; source text; route boolean; route_deadline timestamptz; cleaned jsonb:='{}'::jsonb;
begin
 if jsonb_typeof(receipt) is distinct from 'object'
  or receipt->>'application_url' is distinct from candidate->>'application_url'
  or nullif(receipt->>'checked_at','')::timestamptz is distinct from p_checked
  or jsonb_typeof(receipt->'categories') is distinct from 'object'
  or jsonb_typeof(candidate->'categories') is distinct from 'array' then
  raise exception 'Category receipt does not match the verified application.' using errcode='22023';end if;
 for category,fact in select key,value from jsonb_each(receipt->'categories') loop
  source:=fact->>'source_url';
  route:=p_result->>'policy' in ('makrs-eventeny-v4-details','makrs-eventeny-v5-quality')
    and category='Food Trucks'
    and source ~ '^https://www[.]eventeny[.]com/events/vendor/[?]id=[0-9]+$'
    and source is distinct from candidate->>'application_url'
    and fact->>'event_source_url'=candidate->>'source_url'
    and fact->>'starts_on'=candidate->>'starts_on'
    and fact->>'ends_on'=candidate->>'ends_on';
  if fact ? 'application_state' then
   if not coalesce(route,false) or coalesce(fact->>'application_state','') not in ('open','limited','waitlist','closed','unknown')
    or (fact->>'application_state'='closed' and fact->>'status'<>'unavailable')
    or (fact->>'application_state'<>'closed' and fact->>'status'<>'separate_application') then
    raise exception 'Separate application route is not bound to this event.' using errcode='22023';end if;
   route_deadline:=nullif(fact->>'application_deadline','')::timestamptz;
   if route_deadline is not null and not isfinite(route_deadline) then raise exception 'Invalid route deadline.' using errcode='22023';end if;
   if fact->>'application_state' in ('open','limited','waitlist') and (route_deadline is null or route_deadline<=p_checked) then
    raise exception 'Separate application lacks a future deadline.' using errcode='22023';end if;
  elsif coalesce(route,false) or fact ? 'application_deadline' then
   raise exception 'Separate application state is required.' using errcode='22023';
  end if;
  if category not in ('Food & Beverages','Food Trucks','Art & Photography','Handmade Crafts','Jewelry & Accessories','Clothing & Vintage','Bath, Body & Beauty','Plants & Farm Products','Pet Products','Services','Other')
   or jsonb_typeof(fact) is distinct from 'object'
   or coalesce(fact->>'status','') not in ('eligible','excluded','unavailable','separate_application')
   or coalesce(fact->>'source_hash','') !~ '^[a-f0-9]{64}$'
   or length(coalesce(fact->>'excerpt','')) not between 8 and 320
   or length(coalesce(fact->>'note','')) not between 8 and 300
   or not coalesce((route or source=candidate->>'source_url' or source=candidate->>'application_url'
    or (p_result->>'policy' in ('makrs-eventeny-v3-categories','makrs-eventeny-v4-details','makrs-eventeny-v5-quality') and source in
      ('https://makrs.com/'||(candidate->>'market_slug'),'https://makrs.com/market-applications','https://makrs.com/festival-applications'))),false) then
   raise exception 'Category fact lacks a scoped official source.' using errcode='22023';end if;
  if fact ? 'source_terms' and btb_private.category_product_metadata(fact)='{}'::jsonb then
   raise exception 'Product wording is not present in its source excerpt.' using errcode='22023';end if;
  cleaned:=cleaned||jsonb_build_object(category,jsonb_build_object('status',fact->>'status','note',fact->>'note','source_url',source,'source_hash',fact->>'source_hash','excerpt',fact->>'excerpt')||btb_private.category_product_metadata(fact)||case when coalesce(route,false) then jsonb_strip_nulls(jsonb_build_object('application_state',fact->>'application_state','application_deadline',fact->>'application_deadline')) else '{}'::jsonb end);
 end loop;
 select coalesce(array_agg(value order by value),'{}'::text[]) into actual from jsonb_array_elements_text(candidate->'categories');
 select coalesce(array_agg(key order by key),'{}'::text[]) into expected from jsonb_each(cleaned) where value->>'status'='eligible';
 if actual is distinct from expected then raise exception 'Category list contradicts its evidence.' using errcode='22023';end if;
 return jsonb_build_object('application_url',candidate->>'application_url','checked_at',p_checked,'categories',cleaned);
end; $function$
;

CREATE OR REPLACE FUNCTION btb_private.public_category_evidence(p_application_url text, p_evidence jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare checked timestamptz; deadline timestamptz; category text; fact jsonb; clean jsonb; result jsonb:='{}'::jsonb;
begin
 if p_evidence->>'application_url' is distinct from p_application_url or jsonb_typeof(p_evidence->'categories') is distinct from 'object' then return result;end if;
 begin checked:=(p_evidence->>'checked_at')::timestamptz;
 exception when invalid_datetime_format or datetime_field_overflow then return result;end;
 if checked is null or not isfinite(checked) or checked>now() or checked<=now()-interval '7 days' then return result;end if;
 for category,fact in select key,value from jsonb_each(p_evidence->'categories') loop
  if category not in ('Food & Beverages','Food Trucks','Art & Photography','Handmade Crafts','Jewelry & Accessories','Clothing & Vintage','Bath, Body & Beauty','Plants & Farm Products','Pet Products','Services','Other')
   or coalesce(fact->>'status','') not in ('eligible','excluded','unavailable','separate_application') or coalesce(fact->>'source_url','') not like 'https://%' then continue;end if;
  clean:=jsonb_build_object('status',fact->>'status','note',coalesce(fact->>'note',''),'source_url',fact->>'source_url','checked_at',checked)||btb_private.category_product_metadata(fact);
  if fact ? 'application_state' then
   if fact->>'application_state' not in ('open','limited','waitlist','closed','unknown') then continue;end if;
   begin deadline:=nullif(fact->>'application_deadline','')::timestamptz;
   exception when invalid_datetime_format or datetime_field_overflow then continue;end;
   if deadline is not null and not isfinite(deadline) then continue;end if;
   clean:=clean||jsonb_strip_nulls(jsonb_build_object('application_state',fact->>'application_state','application_deadline',deadline));
   if deadline<=now() and fact->>'application_state'<>'closed' then clean:=clean||jsonb_build_object('status','unavailable','application_state','closed','note','The separate food-truck application deadline has passed; the main vendor application has its own status.');end if;
  end if;
  result:=result||jsonb_build_object(category,clean);
 end loop;
 return result;
end; $function$
;

-- Public date-only index for Explore Markets. Do not fetch member application
-- details just to determine whether a market has an upcoming event.
CREATE FUNCTION public.btb_public_market_upcoming_dates()
RETURNS TABLE(market_id uuid,last_event_ends_on date)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
 SELECT o.market_id,max(o.ends_on)
 FROM public.vendor_opportunities o
 JOIN public.markets m ON m.id=o.market_id
 WHERE o.publication='published' AND NOT m.is_hidden AND NOT m.is_sample
 AND o.schedule_type='dated_event' AND isfinite(o.starts_on) AND isfinite(o.ends_on)
 AND o.ends_on >= (now() AT TIME ZONE 'America/New_York')::date
 -- Closed vendor applications do not imply a cancelled or completed event.
 GROUP BY o.market_id;
$$;
REVOKE ALL ON FUNCTION public.btb_public_market_upcoming_dates() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.btb_public_market_upcoming_dates() TO anon,authenticated,service_role;
COMMENT ON FUNCTION public.btb_public_market_upcoming_dates() IS 'Public published event dates for visible real markets; excludes past events and application/season/rolling placeholders.';
NOTIFY pgrst,'reload schema';

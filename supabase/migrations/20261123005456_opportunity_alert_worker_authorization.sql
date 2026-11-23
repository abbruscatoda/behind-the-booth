-- Keep the internal research authorizer inaccessible to client roles. The
-- scheduled edge worker uses this service-only bridge and must still supply
-- the existing dedicated research secret in the request header.
CREATE FUNCTION public.btb_authorize_opportunity_alert_worker()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 PERFORM public.btb_research_authorize();
END; $$;
REVOKE ALL ON FUNCTION public.btb_authorize_opportunity_alert_worker() FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.btb_authorize_opportunity_alert_worker() TO service_role;
NOTIFY pgrst,'reload schema';

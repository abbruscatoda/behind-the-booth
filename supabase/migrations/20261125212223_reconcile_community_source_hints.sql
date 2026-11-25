CREATE OR REPLACE FUNCTION public.btb_research_community_hints(p_hints jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE h jsonb;n integer:=0;
BEGIN
 PERFORM public.btb_research_authorize();
 IF NOT coalesce((SELECT enabled FROM public.btb_research_settings WHERE id),false) THEN RETURN jsonb_build_object('paused',true);END IF;
 IF jsonb_typeof(p_hints) IS DISTINCT FROM 'array' OR jsonb_array_length(p_hints)>60 OR octet_length(p_hints::text)>100000 THEN RAISE EXCEPTION 'Invalid community hints' USING errcode='22023';END IF;
 FOR h IN SELECT value FROM jsonb_array_elements(p_hints) LOOP
  IF h->>'id' ~ '^[a-f0-9-]{36}$' AND h ? 'reason' THEN
   UPDATE btb_private.community_discovery_inbox SET reason=left(h->>'reason',500),last_checked_at=now() WHERE id=(h->>'id')::uuid AND state='unverified';
   CONTINUE;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM btb_private.community_sources s WHERE s.source_key=h->>'source_key' AND s.active)
   OR coalesce(h->>'target_url','') !~ '^https://[^[:space:]<>]+$' OR length(h->>'target_url')>1200 OR length(coalesce(h->>'title','')) NOT BETWEEN 3 AND 160 THEN CONTINUE;END IF;
  -- The registered venue can be synced concurrently with its first publication.
  -- A calendar hint adds no evidence to an already staged, source-matched call.
  IF EXISTS(SELECT 1 FROM btb_private.community_discovery_inbox i
   WHERE i.source_key IS NULL AND i.target_url=h->>'target_url'
   AND i.proposal->>'reviewed_source_key'=h->>'source_key'
   AND jsonb_array_length(i.receipts)>0) THEN CONTINUE;END IF;
  INSERT INTO btb_private.community_discovery_inbox(source_key,target_url,title,notes)
  VALUES(h->>'source_key',h->>'target_url',h->>'title',left(coalesce(h->>'notes',''),3000))
  ON CONFLICT(source_key,target_url) DO UPDATE SET last_seen=now(),notes=CASE WHEN btb_private.community_discovery_inbox.proposal='{}' THEN excluded.notes ELSE btb_private.community_discovery_inbox.notes END;
  n:=n+1;
 END LOOP;
 RETURN jsonb_build_object('hints',n);
END; $$;

-- Reconcile an older empty hint with the actual published event. Keep the
-- original dated research and both observations, including their timestamps.
INSERT INTO btb_private.community_discovery_inbox AS dest
 (source_key,target_url,title,notes,proposal,receipts,state,reason,opportunity_id,first_seen,last_seen,last_checked_at)
SELECT s.source_key,p.target_url,p.title,p.notes,p.proposal,p.receipts,p.state,p.reason,
 p.opportunity_id,p.first_seen,p.last_seen,p.last_checked_at
FROM btb_private.community_discovery_inbox p
JOIN btb_private.community_sources s ON s.source_key=p.proposal->>'reviewed_source_key' AND s.active
JOIN btb_private.community_discovery_inbox h ON h.source_key=s.source_key AND h.target_url=p.target_url
JOIN public.vendor_opportunities o ON o.id=p.opportunity_id AND o.publication='published'
 AND o.starts_on=(p.proposal->>'starts_on')::date AND o.application_url=p.proposal->>'application_url'
WHERE p.source_key IS NULL AND p.state IN ('published','closed') AND jsonb_array_length(p.receipts)>0
 AND h.proposal='{}' AND h.opportunity_id IS NULL AND h.state='unverified'
 AND (SELECT enabled FROM public.btb_research_settings WHERE id)
ON CONFLICT(source_key,target_url) DO UPDATE SET
 title=excluded.title,notes=excluded.notes,proposal=excluded.proposal,receipts=excluded.receipts,
 state=excluded.state,reason=excluded.reason,opportunity_id=excluded.opportunity_id,
 first_seen=least(dest.first_seen,excluded.first_seen),last_seen=greatest(dest.last_seen,excluded.last_seen),
 last_checked_at=excluded.last_checked_at
WHERE dest.proposal='{}' AND dest.state='unverified' AND dest.opportunity_id IS NULL;

CREATE OR REPLACE FUNCTION public.btb_admin_community_discovery() RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 IF NOT coalesce(public.btb_is_admin(),false) THEN RAISE EXCEPTION 'Admin access required' USING errcode='42501';END IF;
 RETURN jsonb_build_object('sources',coalesce((SELECT jsonb_agg(config ORDER BY source_key) FROM btb_private.community_sources WHERE active),'[]'),
 'leads',coalesce((SELECT jsonb_agg(to_jsonb(q) ORDER BY q.last_seen DESC) FROM (
  SELECT i.id,i.source_key,i.target_url,i.title,i.notes,i.state,i.reason,i.first_seen,i.last_seen,i.last_checked_at,i.opportunity_id
  FROM btb_private.community_discovery_inbox i
  WHERE NOT (i.source_key IS NULL AND i.opportunity_id IS NOT NULL AND EXISTS(
   SELECT 1 FROM btb_private.community_discovery_inbox canonical
   WHERE canonical.source_key=i.proposal->>'reviewed_source_key' AND canonical.target_url=i.target_url
   AND canonical.opportunity_id=i.opportunity_id))
  ORDER BY i.last_seen DESC LIMIT 60) q),'[]'));
END; $$;

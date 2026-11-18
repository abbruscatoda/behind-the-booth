-- Behind the Booth: preserve prior approval when the worker cannot read a source.
-- Safe to apply only after reviewing this migration in Supabase SQL Editor.
-- Changes only the known transient-failure branch in btb_research_apply.
-- No current opportunity rows are modified by this migration.
--
-- This patch intentionally refuses to run if the live function differs from
-- the expected structure. Do not remove its guard to force installation.
BEGIN;
DO $migration$
DECLARE
  existing_definition text;
  patched_definition text;
  target_statement constant text :=
    'update public.vendor_opportunities set availability=''needs_recheck'',review_state=''needs_review'',review_reason=reason,last_checked_at=now(),updated_at=now() where id=item.id;';
  guarded_statement constant text := $replacement$
  -- An inaccessible source is not proof that a previously approved
  -- opportunity is inaccurate. Never renew verified_at or availability here.
  if item.publication='published'
     and candidate is null
     and decision='review'
     and reason='Official source could not be read reliably. The next successful run can resolve this automatically.'
  then
    update public.vendor_opportunities
       set last_checked_at=now()
     where id=item.id;
    insert into public.btb_research_audit(opportunity_id,action,reason,evidence)
    values(item.id,'skipped','Transient source-read failure; published approval preserved.',
           jsonb_build_object('original_reason',reason));
    return jsonb_build_object('action','skipped','id',item.id,
      'reason','Transient source-read failure; published approval preserved.');
  end if;
  update public.vendor_opportunities set availability='needs_recheck',review_state='needs_review',review_reason=reason,last_checked_at=now(),updated_at=now() where id=item.id;
$replacement$;
BEGIN
  SELECT pg_get_functiondef(
    'public.btb_research_apply(uuid,jsonb,timestamp with time zone)'::regprocedure
  ) INTO existing_definition;

  IF existing_definition IS NULL THEN
    RAISE EXCEPTION 'btb_research_apply not found; no changes made';
  END IF;
  IF position(target_statement in existing_definition)=0 THEN
    RAISE EXCEPTION 'Live function does not match the inspected version; no changes made';
  END IF;
  IF position('Transient source-read failure; published approval preserved.' in existing_definition)>0 THEN
    RAISE EXCEPTION 'This migration appears already applied; no changes made';
  END IF;
  patched_definition := replace(existing_definition,target_statement,guarded_statement);
  IF patched_definition=existing_definition THEN
    RAISE EXCEPTION 'Could not apply guarded patch; no changes made';
  END IF;
  EXECUTE patched_definition;
END;
$migration$;
COMMIT;

-- Verification after applying:
-- SELECT position('Transient source-read failure; published approval preserved.'
--     in pg_get_functiondef(
--     'public.btb_research_apply(uuid,jsonb,timestamp with time zone)'::regprocedure
--   )) > 0 AS patch_present;

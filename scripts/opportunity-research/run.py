"""Daily verifier. --dry-run never writes to Supabase. No AI key or third-party packages."""
from __future__ import annotations
import argparse, json, os, sys, re
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from research_quality import apply_quality_gate,add_review_suggestions
from review_policy import defer_inconclusive_review, transient_source_failure
from verifier import Fetcher, discover, verify, canonical_event, canonical_application, application_key, norm, Uncertain, verify_artspace
from discovery import discover_triangle

class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError("Database redirects are not allowed")

class Database:
 def __init__(self):
  self.url=os.environ.get('BTB_SUPABASE_URL','').rstrip('/')
  self.key=os.environ.get('BTB_SUPABASE_PUBLISHABLE_KEY','')
  self.secret=os.environ.get('BTB_RESEARCH_SECRET','')
  p=urlparse(self.url)
  if p.scheme!='https' or not p.hostname or not p.hostname.endswith('.supabase.co') or p.username or p.password or p.port not in (None,443) or p.path or p.query or p.fragment:raise ValueError('Set BTB_SUPABASE_URL to the project https://...supabase.co origin')
  if not self.key or len(self.secret)!=64:raise ValueError('Set BTB_SUPABASE_PUBLISHABLE_KEY and the dedicated BTB_RESEARCH_SECRET')
 def rpc(self,name,body=None):
  if name not in {'btb_research_context','btb_research_apply','btb_research_run','btb_research_record_discovery_leads','btb_research_record_discovery_leads_v2','btb_research_finalize_discovery_leads','btb_research_publish_discovery','btb_research_publish_form','btb_research_discovery_backlog','btb_research_publish_recurring','btb_research_publish_seasonal','btb_research_diagnose_leads','btb_research_publish_multidate','btb_research_reconcile_form_shortcuts','btb_research_coverage_context','btb_research_reconcile_covered_leads'}:raise ValueError('Worker RPC not allowed')
  # Credentials are sent only to the configured Supabase origin, never source pages.
  request=Request(self.url+'/rest/v1/rpc/'+name,data=json.dumps(body or {}).encode(),headers={'apikey':self.key,'Content-Type':'application/json','x-btb-research-secret':self.secret},method='POST')
  try:
   with build_opener(NoRedirect()).open(request,timeout=30) as response:return json.load(response)
  except HTTPError as cause:
   # Only expose known PostgREST / SQLSTATE *codes*. Response messages can
   # contain user-controlled URLs, secrets or SQL parameters, so never log
   # message, details, hints, request/response headers or response bodies.
   error_code='unknown'
   try:
    payload=json.loads(cause.read(4096).decode('utf-8','replace'))
    received=payload.get('code','') if isinstance(payload,dict) else ''
    if isinstance(received,str) and re.fullmatch(r'(?:[A-Z0-9]{5}|PGRST[0-9]{3})',received):
     error_code=received
   except (ValueError,UnicodeError,OSError):pass
   raise RuntimeError(f'{name} failed (HTTP {cause.code}, code {error_code}); inspect database diagnostics.') from None
  except Exception:
   raise RuntimeError(f'{name} failed (network or response error); inspect database diagnostics.') from None

def existing_result(item,found,fetcher,now):
 if item.get('verification_policy')=='seasonal-official-v1':
  from seasonal_research import PROVIDERS,check_provider
  matches=[p for p in PROVIDERS if p['slug']==item.get('market_slug')]
  if len(matches)!=1:raise Uncertain('Seasonal-market source configuration is missing.')
  result=check_provider(matches[0],fetcher,now)
  data=result['candidate']
  if data['starts_on']!=item['starts_on'] or data['application_url']!=item['application_url'] or data['schedule_type']!=item.get('schedule_type'):
   raise Uncertain('The official seasonal application or coverage window has changed; do not overwrite an existing listing.')
  return result
 if item.get('verification_policy')=='triangle-multidate-jotform-v1':
  from multidate_research import PROVIDERS,verify_provider
  matches=[p for p in PROVIDERS if p['slug']==item.get('market_slug')]
  if len(matches)!=1:raise Uncertain('No approved multi-date provider for the published market.')
  results=verify_provider(matches[0],fetcher,now)
  for result in results:
   c=result['candidate']
   if c['starts_on']==item['starts_on'] and c['application_url']==item['application_url']:
    return result
  raise Uncertain('The former market date is no longer offered in the official application.')
 if item.get('verification_policy')=='recurring-official-waitlist-v1':
  from recurring_market import PROVIDERS,check_recurring_provider
  providers=[provider for provider in PROVIDERS if provider['market_slug']==item.get('market_slug')]
  if len(providers)!=1:raise Uncertain('Recurring-market provider configuration is missing.')
  result=check_recurring_provider(providers[0],fetcher,now)
  if result['candidate']['application_url']!=item['application_url'] or result['candidate']['starts_on']!=item['starts_on']:
   raise Uncertain('Recurring market has a changed season or application link; cannot update the saved opportunity.')
  return result
 if item.get('verification_policy') in ('triangle-form-auto-v1','triangle-form-calendar-v2'):
  from form_discovery import verify_public_form
  lead={'source_url':item['source_url'],'target_url':item['application_url']}
  if item.get('verification_policy')=='triangle-form-calendar-v2':
   from calendar_research import CALENDARS
   matching=[(root,cal) for _,root,cal in CALENDARS
       if urlparse(item['source_url']).hostname==urlparse(cal).hostname]
   if len(matching)!=1:
    raise Uncertain('Cannot resolve the trusted official calendar for this market.')
   lead.update({'organizer_root':matching[0][0],'calendar_url':matching[0][1]})
  result=verify_public_form(lead,fetcher,now)
  if not result or result['candidate']['starts_on']!=item['starts_on'] or result['candidate']['ends_on']!=item['ends_on'] or norm(result['candidate']['organizer'])!=norm(item.get('market_organizer') or ''):
   raise Uncertain('A previously verified linked form has changed or lacks current evidence. Confirm the application with the organizer.')
  return result
 from first_night import handles,verify_first_night
 if handles(item):return verify_first_night(item,fetcher,now)
 from linked_forms import handles as handles_public_form, read as read_linked_public_form
 from verifier import ARTSPACE_APP
 if item['application_url']==ARTSPACE_APP:return verify_artspace(item,fetcher,now)
 if handles_public_form(item):
  if not item.get('source_url'):
   raise Uncertain('Unsupported Google Form: no separate organizer-bound source is configured.')
  return read_linked_public_form(item,fetcher,now)
 if urlparse(item['application_url']).hostname in {'forms.gle','docs.google.com','form.jotform.com'}:
  raise Uncertain('Unsupported Google Form or Jotform URL: an organizer-bound reader is required.')
 key=(canonical_application(item['application_url']),item['starts_on'])
 if key in found:return found[key]
 if not application_key(item['application_url']):return verify_artspace(item,fetcher,now)
 if norm(item.get('market_organizer') or '')!='themakrssociety' or item.get('verification_policy')=='triangle-eventeny-auto-v1':
  # Bind verification to the exact existing, manually approved market.
  # Applications can link back to the dated Eventeny page even when the
  # stored source is an organizer website or the application itself.
  app,_=fetcher.get(canonical_application(item['application_url']))
  sources=[]
  if canonical_event(item.get('source_url','')):sources.append(canonical_event(item['source_url']))
  for event in app.events():
   source=canonical_event(event.get('url',''))
   if source and source not in sources:sources.append(source)
  for link in app.root.links(canonical_application(item['application_url'])):
   source=canonical_event(link)
   if source and source not in sources:sources.append(source)
  if not sources:raise Uncertain('The Eventeny application does not identify a trusted dated event page.')
  for source in sources[:10]:
   doc,_=fetcher.get(source)
   if any(str(e.get('startDate',''))[:10]==item['starts_on'] for e in doc.events()):
    return verify(source,item['application_url'],fetcher,now,expected_item=item)
  raise Uncertain('The Eventeny application and saved event date do not match.')
 sources=[]
 if canonical_event(item['source_url']):sources.append(canonical_event(item['source_url']))
 app,_=fetcher.get(canonical_application(item['application_url']))
 for event in app.events():
  source=canonical_event(event.get('url',''))
  if source:sources.append(source)
 # Visit each source once, including the first series links (no skipped dates).
 seen=set()
 while sources and len(seen)<20:
  source=sources.pop(0)
  if source in seen:continue
  seen.add(source)
  doc,_=fetcher.get(source)
  if any(str(e.get('startDate',''))[:10]==item['starts_on'] for e in doc.events()):return verify(source,item['application_url'],fetcher,now)
  for link in doc.root.links(source):
   url=canonical_event(link)
   if url and url not in seen:sources.append(url)
 raise Uncertain('No exact dated event could be linked to this application. Check the event/date, not just the series form.')

def run(dry_run=False):
 db=Database();context=db.rpc('btb_research_context')
 if not context['enabled']:
  print('Automatic updates are paused in admin. No writes or source requests made.');return
 now=datetime.now(timezone.utc);fetcher=Fetcher(limit=360);run_id=None;counts=Counter();problems=[]
 if not dry_run:run_id=db.rpc('btb_research_run')
 try:
  # Read-only Brewgaloo public-form check; never changes listed fees.
  form_probe=None
  if getattr(fetcher,'browser_enabled',False):
   from form_probe import probe_public_form
   form_probe=probe_public_form(fetcher)
  results,problems=discover(fetcher,now)
  found={(r['candidate']['application_url'],r['candidate']['starts_on']):r for r in results}
  known={(canonical_application(i['application_url']) or i['application_url'],i['starts_on']) for i in context['items']}
  def apply(item,result):
   # Seasonal waitlists use a separate, tightly scoped official-source
   # verification policy. The dated-event quality gate expects an exact
   # event deadline and must not silently downgrade a verified waitlist.
   if result.get('policy') not in ('recurring-official-waitlist-v1','seasonal-official-v1','triangle-multidate-jotform-v1'):
    result=add_review_suggestions(item,apply_quality_gate(item,result))
   if defer_inconclusive_review(item,result):
    counts['deferred_inconclusive']+=1
    print(json.dumps({'title':item['title'],'action':'deferred_inconclusive','reason':'Previously published listing retained; inaccessible source is not evidence of a change.'},ensure_ascii=False))
    return
   if dry_run:
    counts['proposed_'+result['decision']]+=1
    print(json.dumps({'title':item['title'] if item else result['candidate']['title'],'proposed':result['decision'],'reason':result.get('reason',''),'source':result.get('candidate',{}).get('source_url') or result.get('research_suggestions',{}).get('source_url'),'categories':result.get('candidate',{}).get('categories',[]),'category_states':{c:e['status'] for c,e in result.get('category_evidence',{}).get('categories',{}).items()},'category_warnings':result.get('category_warnings',[]),'research_quality':result.get('research_quality'),'quality_issues':result.get('quality_issues',[]),'fee_notes':result.get('candidate',{}).get('fee_notes',''),'requirements':result.get('candidate',{}).get('eligibility',''),'research_suggestions':result.get('research_suggestions')},ensure_ascii=False));return
   if result.get('category_warnings'):print(json.dumps({'title':item['title'] if item else result['candidate']['title'],'category_warnings':result['category_warnings']},ensure_ascii=False))
   if result.get('policy')=='seasonal-official-v1' and result.get('decision')=='publish':
    response=db.rpc('btb_research_publish_seasonal',{'p_result':result})
   elif result.get('policy')=='triangle-multidate-jotform-v1' and result.get('decision')=='publish':
    response=db.rpc('btb_research_publish_multidate',{'p_result':result})
   elif result.get('policy')=='recurring-official-waitlist-v1' and result.get('decision')=='publish':
    response=db.rpc('btb_research_publish_recurring',{'p_result':result})
   elif result.get('policy') in ('triangle-form-auto-v1','triangle-form-calendar-v2') and result.get('decision')=='publish':
    response=db.rpc('btb_research_publish_form',{'p_result':result,
      'p_id':item['id'] if item else None,
      'p_expected_updated_at':item['updated_at'] if item else None})
   elif item is None and result.get('policy')=='triangle-eventeny-auto-v1' and result.get('decision')=='publish':
    response=db.rpc('btb_research_publish_discovery',{'p_result':result})
   else:
    response=db.rpc('btb_research_apply',{'p_id':item['id'] if item else None,'p_result':result,'p_expected_updated_at':item['updated_at'] if item else None})
   counts[response['action']]+=1
   print(json.dumps({'title':item['title'] if item else result['candidate']['title'],'action':response['action'],'reason':response.get('reason',''),'category_states':{c:e['status'] for c,e in result.get('category_evidence',{}).get('categories',{}).items()} if response['action']=='publish' else {}},ensure_ascii=False))
  for item in context['items']:
   if item['automation_hold']:counts['held']+=1;continue
   if item['ends_on']<now.astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).date().isoformat():
    apply(item,{'decision':'closed','reason':'Application deadline or event date has passed.'});continue
   try:result=existing_result(item,found,fetcher,now)
   except Uncertain as error:result={'decision':'closed' if item.get('deadline') and datetime.fromisoformat(item['deadline'].replace('Z','+00:00'))<now else 'review','reason':str(error)}
   except Exception as error:
    if not transient_source_failure(error):raise
    result={'decision':'closed' if item.get('deadline') and datetime.fromisoformat(item['deadline'].replace('Z','+00:00'))<now else 'review','reason':'Official source could not be read reliably. The next successful run can resolve this automatically.'}
   apply(item,result)
  for key,result in found.items():
   if key not in known:apply(None,result)
  # Broad discovery follows previously published rechecks. Newly discovered
  # opportunities are published only through the dedicated, guarded RPC after
  # both Eventeny identities, dates, application status and receipts match.
  # Inconclusive organizer links remain private admin research leads.
  # The backlog RPC is read-only and worker-secret guarded. Keep --dry-run
  # limited to the existing context call for compatibility with strict tests.
  backlog=[] if dry_run else db.rpc('btb_research_discovery_backlog')
  incoming,leads,discovery_stats=discover_triangle(fetcher,now,known=known|set(found),backlog=backlog)
  for candidate in incoming:
   data=candidate['candidate']
   key=(canonical_application(data['application_url']) or data['application_url'],data['starts_on'])
   if key in known or key in found:continue
   apply(None,candidate)
  from recurring_market import discover_recurring
  recurring_diagnostics=[]
  for candidate in discover_recurring(fetcher,now,diagnostics=recurring_diagnostics):
   data=candidate['candidate']
   key=(data['application_url'],data['starts_on'])
   if key not in known:
    apply(None,candidate)
  from multidate_research import discover_multidate
  multidate_notes=[]
  for candidate in discover_multidate(fetcher,now,diagnostics=multidate_notes):
   data=candidate['candidate']
   key=(data['application_url'],data['starts_on'])
   if key not in known and key not in found:
    apply(None,candidate)
  discovery_stats['multidate_research_notes']=multidate_notes[:8]
  from seasonal_research import discover_seasonal
  seasonal_notes=[]
  for candidate in discover_seasonal(fetcher,now,diagnostics=seasonal_notes):
   data=candidate['candidate']
   key=(data['application_url'],data['starts_on'])
   if key not in known and key not in found:
    apply(None,candidate)
  discovery_stats['seasonal_research_notes']=seasonal_notes[:12]
  # Research each saved/new lead and persist the *reason* it could not be
  # published. This is diagnostic evidence, never an automatic approval.
  from deep_research import diagnose_leads
  research_rows,research_counts=diagnose_leads(backlog+leads,fetcher,now,limit=80,reserve=24)
  discovery_stats['lead_research_states']=research_counts
  discovery_stats['diagnosed_leads']=len(research_rows)
  if dry_run:
   counts['proposed_lead_diagnostics']=len(research_rows)
  elif research_rows:
   diagnostic_result=db.rpc('btb_research_diagnose_leads',{'p_diagnostics':research_rows})
   counts['leads_diagnosed']=diagnostic_result.get('updated',0)
  if dry_run:
   counts['proposed_discovery_leads']=len(leads)
   for lead in leads[:10]:
    print(json.dumps({'action':'proposed_discovery_lead','title':lead['title'],
      'source':lead['source_url'],'target':lead['target_url']}))
  elif leads:
   # Registry and lead batches are now synchronized atomically: the SQL
   # worker cannot silently reject the five newest curated Triangle sources.
   from discovery import SOURCES
   approved=[{'organizer':name,'city':city,'source_url':url}
     for name,city,url in SOURCES]
   try:
    saved=db.rpc('btb_research_record_discovery_leads_v2',
                 {'p_leads':leads,'p_sources':approved})
   except RuntimeError as error:
    # Ingestion errors are visible and fail the run, but unrelated
    # already-published lead reconciliation can still proceed.
    problems.append(str(error)[:200])
    counts['discovery_lead_ingestion_failed']=1
   else:
    discovery_stats['source_registry_count']=saved.get('approved_sources')
    counts['discovery_leads_seen']=saved.get('saved',0)
    counts['discovery_leads_skipped']=saved.get('skipped',0)
    counts['lead_cardinality_conflicts']=saved.get('cardinality_conflicts',0)
    # Separate HTTP RPC = separate committed transaction. Never reconcile
    # freshly inserted lead rows within the same bulk upsert command.
    try:
     finalized=db.rpc('btb_research_finalize_discovery_leads')
    except RuntimeError as error:
     problems.append(str(error)[:200])
     counts['post_ingest_reconciliation_failed']=1
    else:
     counts['post_ingest_leads_resolved']=finalized.get('resolved',0)
  # Verify current official-page relationships before retiring saved or new
  # leads. Published listings on manual edit hold are still valid evidence.
  if backlog or leads:
   from lead_coverage import coverage_receipts
   from discovery import SOURCES as COVERAGE_SOURCES
   coverage_context=db.rpc('btb_research_coverage_context')
   coverage,coverage_stats=coverage_receipts(backlog+leads,coverage_context,
       fetcher,{root for _,_,root in COVERAGE_SOURCES})
   discovery_stats['published_lead_coverage']=coverage_stats
   if dry_run:
    counts['proposed_covered_leads']=len(coverage)
   elif coverage:
    coverage_result=db.rpc('btb_research_reconcile_covered_leads',
                           {'p_receipts':coverage})
    counts['covered_leads_resolved']=coverage_result.get('resolved',0)
  # Reconcile source-linked Google shortcuts to their real forms. This is
  # independent of vendor application openness: a redirect only proves two
  # URLs identify the same already-published application, never publication.
  # Check both old backlog and newly discovered leads every scheduled run.
  from lead_reconciliation import reconcile_shortcuts
  from discovery import SOURCES
  shortcut_receipts=reconcile_shortcuts(backlog+leads,fetcher,{root for _,_,root in SOURCES})
  discovery_stats['verified_shortcut_receipts']=len(shortcut_receipts)
  if dry_run:
   counts['proposed_shortcut_reconciliations']=len(shortcut_receipts)
  elif shortcut_receipts:
   reconciled=db.rpc('btb_research_reconcile_form_shortcuts',{'p_receipts':shortcut_receipts})
   counts['shortcuts_resolved']=reconciled.get('resolved',0)
  if fetcher.requests>=fetcher.limit:
   problems.append('Source request budget reached. Some checks may be deferred or need review.')
  discovery_stats['recurring_verification_notes']=recurring_diagnostics[:8]
  if getattr(fetcher,'browser_enabled',False):
   discovery_stats['browser_forms']={'attempts':fetcher.browser_attempts,
    'successful_public_renders':fetcher.browser_successes,
    'failure_reasons':getattr(fetcher,'browser_failures',{}),
    'attempt_limit':fetcher.browser_max_attempts,
    'brewgaloo_form_probe':form_probe}
  summary={'dry_run':dry_run,'counts':dict(counts),'issues':problems[:12],'source_requests':fetcher.requests,'discovery':discovery_stats}
  summary['failed']=bool(problems)
  if not dry_run:db.rpc('btb_research_run',{'p_id':run_id,'p_summary':summary})
  print(json.dumps(summary))
  if problems:raise RuntimeError('One or more official discovery sources failed. See admin run history.')
 except Exception:
  if run_id:
   try:db.rpc('btb_research_run',{'p_id':run_id,'p_summary':{'failed':True,'counts':dict(counts),'issues':problems[:12] or ['Worker stopped before completing; inspect GitHub Actions.']}})
   except Exception:pass
  raise
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
 try:run(args.dry_run)
 except Exception as error:print(str(error),file=sys.stderr);sys.exit(1)

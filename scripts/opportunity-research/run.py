"""Daily verifier. --dry-run never writes to Supabase. No AI key or third-party packages."""
from __future__ import annotations
import argparse, json, os, sys
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from research_quality import apply_quality_gate,add_review_suggestions
from review_policy import defer_inconclusive_review, transient_source_failure
from verifier import Fetcher, discover, verify, canonical_event, canonical_application, application_key, norm, Uncertain, verify_artspace

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
  if name not in {'btb_research_context','btb_research_apply','btb_research_run'}:raise ValueError('Worker RPC not allowed')
  # Credentials are sent only to the configured Supabase origin, never source pages.
  request=Request(self.url+'/rest/v1/rpc/'+name,data=json.dumps(body or {}).encode(),headers={'apikey':self.key,'Content-Type':'application/json','x-btb-research-secret':self.secret},method='POST')
  try:
   with build_opener(NoRedirect()).open(request,timeout=30) as response:return json.load(response)
  except Exception as cause:
   # Do not emit response bodies, headers or credentials into GitHub logs.
   raise RuntimeError(f'{name} failed; inspect configuration and the admin run history.') from None

def existing_result(item,found,fetcher,now):
 from first_night import handles,verify_first_night
 if handles(item):return verify_first_night(item,fetcher,now)
 if urlparse(item['application_url']).hostname in {'forms.gle','docs.google.com'}:
  raise Uncertain('Unsupported Google Form: no organizer-bound reader is configured. Application fees and requirements have NOT been verified; review the official form.')
 key=(canonical_application(item['application_url']),item['starts_on'])
 if key in found:return found[key]
 if not application_key(item['application_url']):return verify_artspace(item,fetcher,now)
 if norm(item.get('market_organizer') or '')!='themakrssociety':
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
 now=datetime.now(timezone.utc);fetcher=Fetcher(limit=120);run_id=None;counts=Counter();problems=[]
 if not dry_run:run_id=db.rpc('btb_research_run')
 try:
  results,problems=discover(fetcher,now)
  found={(r['candidate']['application_url'],r['candidate']['starts_on']):r for r in results}
  known={(canonical_application(i['application_url']),i['starts_on']) for i in context['items']}
  def apply(item,result):
   result=add_review_suggestions(item,apply_quality_gate(item,result))
   if defer_inconclusive_review(item,result):
    counts['deferred_inconclusive']+=1
    print(json.dumps({'title':item['title'],'action':'deferred_inconclusive','reason':'Previously published listing retained; inaccessible source is not evidence of a change.'},ensure_ascii=False))
    return
   if dry_run:
    counts['proposed_'+result['decision']]+=1
    print(json.dumps({'title':item['title'] if item else result['candidate']['title'],'proposed':result['decision'],'reason':result.get('reason',''),'source':result.get('candidate',{}).get('source_url') or result.get('research_suggestions',{}).get('source_url'),'categories':result.get('candidate',{}).get('categories',[]),'category_states':{c:e['status'] for c,e in result.get('category_evidence',{}).get('categories',{}).items()},'category_warnings':result.get('category_warnings',[]),'research_quality':result.get('research_quality'),'quality_issues':result.get('quality_issues',[]),'fee_notes':result.get('candidate',{}).get('fee_notes',''),'requirements':result.get('candidate',{}).get('eligibility',''),'research_suggestions':result.get('research_suggestions')},ensure_ascii=False));return
   if result.get('category_warnings'):print(json.dumps({'title':item['title'] if item else result['candidate']['title'],'category_warnings':result['category_warnings']},ensure_ascii=False))
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
  if fetcher.requests>=fetcher.limit:problems.append('Source request budget reached. Some checks may be deferred or need review.')
  summary={'dry_run':dry_run,'counts':dict(counts),'issues':problems[:12],'source_requests':fetcher.requests}
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

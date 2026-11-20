"""Resolve research leads covered by already-published opportunity evidence.

This is a conservative, organizer-bound graph of live public links. It does
not declare applications open, and does not discard category-specific details.
No generic organizer-name-based cleanup: all links need current provenance.
"""
from urllib.parse import urlparse
from collections import Counter
import re
from verifier import valid_url

MAX_LINKED_LEADS=100
MAX_HUB_PAGES=24
RESERVE_REQUESTS=20

def comparable_organizer(value):
 return re.sub(r'^the\s+', '', re.sub(r'\s+',' ', (value or '').strip().lower()))

def site(url):
 p=urlparse(url)
 return p.hostname.removeprefix('www.') if p.hostname else ''

def segment(url):
 p=urlparse(url)
 return next((x.lower() for x in p.path.split('/') if x),'')

def coverage_receipts(leads,opportunities,fetcher,approved_roots):
 """Return independently checked exact relationships, not speculative matches."""
 evidence=[]
 seen=set()
 hubs={}
 roots={}
 budget=lambda: getattr(fetcher,'requests',0)<getattr(fetcher,'limit',999999)-RESERVE_REQUESTS
 stats=Counter()
 for lead in leads:
  if len(seen)>=MAX_LINKED_LEADS or not budget():break
  target=lead.get('target_url','')
  source=lead.get('source_url','')
  key=(source,target)
  if key in seen:continue
  seen.add(key)
  if source not in approved_roots or not valid_url(target):continue
  if not valid_url(source):continue
  if source not in roots:
   try:roots[source]=set(fetcher.get(source)[0].root.links(source))
   except Exception:roots[source]=set()
  if target not in roots[source]:continue
  for opp in opportunities:
   if opp.get('publication')!='published':continue
   if (opp.get('market_city') or opp.get('city','')).casefold()!=(lead.get('city') or '').casefold():continue
   if comparable_organizer(opp.get('market_organizer') or opp.get('organizer'))!=comparable_organizer(lead.get('organizer')):continue
   published_source=opp.get('source_url','')
   published_application=opp.get('application_url','')
   if not all(valid_url(u) for u in (published_source,published_application)):continue
   if site(source)!=site(published_source):continue
   proof=None
   # A published opportunity's exact official event/application page
   # is a covered link even when the old lead used a broader index.
   if target==published_source and target!=source:
    proof='published_source'
   elif target==published_application:
    proof='published_application'
   # Applications in different categories for the SAME published event
   # may be served from the organizer's event-specific application hub.
   # Both the root and hub must currently link the category, and the
   # event path must agree. Do not archive external third-party forms.
   elif site(target)==site(published_application)==site(source) and segment(target) and segment(target)==segment(published_application):
    hub=published_application
    if hub not in hubs and len(hubs)<MAX_HUB_PAGES and budget():
     try:hubs[hub]=set(fetcher.get(hub)[0].root.links(hub))
     except Exception:hubs[hub]=set()
    if target in hubs.get(hub,set()) and target!=hub:
     proof='published_event_application_category'
   if not proof:continue
   receipt={'source_url':source,'target_url':target,
            'opportunity_id':opp['id'],'published_source_url':published_source,
            'published_application_url':published_application,'proof':proof}
   evidence.append(receipt)
   stats[proof]+=1
   break
 return evidence,{'coverage_links_checked':len(seen),'coverage_receipts':len(evidence),
                  'coverage_by_proof':dict(stats)}

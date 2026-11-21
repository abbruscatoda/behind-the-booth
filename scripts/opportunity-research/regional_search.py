"""Search hints never establish dates, fees, vendor availability, or source trust."""
from urllib.parse import urlparse,urlencode,urljoin,parse_qs
from urllib.request import Request,build_opener
import xml.etree.ElementTree as ET
import re

REGION_GROUPS=(
 'Raleigh Garner Knightdale','Durham Hillsborough Mebane',
 'Cary Apex Morrisville','Chapel Hill Carrboro Pittsboro Siler City',
 'Wake Forest Rolesville Youngsville Franklinton Creedmoor',
 'Holly Springs Fuquay-Varina Angier Clayton Wendell Zebulon',
)
INTENTS=('market festival vendor application','food truck artisan holiday market apply',
         'farmers market rolling seasonal vendor registration','call for vendors pop up craft fair')
MAX_QUERIES=24
MAX_RESULTS_PER_QUERY=10
MAX_SEARCH_PAGES=12
MAX_FALLBACK_QUERIES=6

def rotate(items,now,limit):
 items=list(items)
 if not items:return []
 slot=now.date().toordinal()*2+int(now.hour>=16)
 start=(slot*(limit if limit<len(items) else 1))%len(items)
 return (items[start:]+items[:start])[:limit]

def queries(now):
 from verifier import CITIES
 slot=now.date().toordinal()*2+int(now.hour>=16)
 # Search each community separately. Combining six town names in a query
 # produced generic tourism pages rather than actual vendor applications.
 return [f'"{city.title()}" North Carolina {INTENTS[(slot+i)%len(INTENTS)]} ({now.year} OR {now.year+1})'
         for i,city in enumerate(sorted(CITIES))]

def html_search(query,opener):
 """Independent fallback, read-only; reject interstitials and unsafe links."""
 from verifier import Document
 from discovery import is_safe_lead_url,MAX_FEED_BYTES
 endpoint='https://html.duckduckgo.com/html/?'+urlencode({'q':query})
 with opener.open(Request(endpoint,headers={'User-Agent':'BehindTheBoothDiscovery/2.0'}),timeout=8) as response:
  if urlparse(response.url).hostname!='html.duckduckgo.com':raise ValueError('Unexpected search host')
  raw=response.read(MAX_FEED_BYTES+1)
 if len(raw)>MAX_FEED_BYTES:raise ValueError('Oversized search page')
 doc=Document(raw.decode('utf-8','replace'))
 hits={}
 for node in doc.root.walk():
  if node.tag!='a' or 'result__a' not in node.attrs.get('class','').split():continue
  url=urljoin(endpoint,node.attrs.get('href',''))
  parsed=urlparse(url)
  if parsed.hostname in {'duckduckgo.com','html.duckduckgo.com'} and parsed.path=='/l/':
   url=(parse_qs(parsed.query).get('uddg') or [''])[0]
  if is_safe_lead_url(url):hits.setdefault(url,node.text()[:160])
  if len(hits)>=MAX_RESULTS_PER_QUERY:break
 return hits

def search_results(now,opener=None):
 from discovery import NoSearchRedirect,MAX_FEED_BYTES,is_safe_lead_url
 opener=opener or build_opener(NoSearchRedirect())
 hits={};failures=[];succeeded=0;empty_queries=[]
 for query in queries(now)[:MAX_QUERIES]:
  relevant=0
  endpoint='https://www.bing.com/search?'+urlencode({'q':query,'format':'rss'})
  try:
   with opener.open(Request(endpoint,headers={'User-Agent':'BehindTheBoothDiscovery/2.0'}),timeout=8) as response:
    if urlparse(response.url).hostname not in {'www.bing.com','bing.com'}:raise ValueError('Unexpected feed host')
    raw=response.read(MAX_FEED_BYTES+1)
   if len(raw)>MAX_FEED_BYTES or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('Invalid feed')
   root=ET.fromstring(raw)
   if root.tag!='rss':raise ValueError('Expected RSS feed')
   succeeded+=1
   for item in root.findall('.//item')[:MAX_RESULTS_PER_QUERY]:
    url=(item.findtext('link') or '').strip()
    title=item.findtext('title') or 'Regional event lead'
    context=title+' '+(item.findtext('description') or '')
    if not re.search(r'\b(?:vendors?|artisan|craft|farmers?|market|markets|festival|pop.up|food.truck)\b',context,re.I):continue
    if is_safe_lead_url(url):
     hits.setdefault(url,title[:160]);relevant+=1
  except (OSError,ValueError,ET.ParseError):failures.append(query)
  if not relevant:empty_queries.append(query)
 fallback_attempts=0;fallback_success=0;fallback_failures=0
 for query in rotate(empty_queries,now,MAX_FALLBACK_QUERIES):
  fallback_attempts+=1
  city=query.split('"')[1]
  try:
   found=html_search(f'{city} North Carolina vendor application market {now.year}',opener)
   if found:fallback_success+=1;hits.update(found)
   else:fallback_failures+=1
  except (OSError,ValueError):fallback_failures+=1
 return hits,{'fallback_queries_attempted':fallback_attempts,'fallback_queries_with_results':fallback_success,
              'fallback_queries_inconclusive':fallback_failures,'queries_without_relevant_rss_results':len(empty_queries),
              'queries_attempted':len(queries(now)[:MAX_QUERIES]),'queries_succeeded':succeeded,
              'query_failures':failures,'result_urls':len(hits)}

def discover_regional(fetcher,now,sources,root_docs,opener=None):
 from verifier import valid_url,canonical_event,canonical_application
 from discovery import extract_links
 hits,stats=search_results(now,opener)
 leads={};events=set();unapproved=[];unlinked=[];inspected=0
 for url,title in sorted(hits.items()):
  event=canonical_event(url)
  if event:events.add(event);continue
  app=canonical_application(url)
  if app:
   if inspected>=MAX_SEARCH_PAGES:continue
   try:
    doc,_=fetcher.get(app);inspected+=1
    for entry in doc.events():
     linked=canonical_event(entry.get('url',''))
     if linked:events.add(linked)
    es,_,_=extract_links(doc,app);events.update(es)
   except Exception:pass
   continue
  matching=[(name,city,root) for name,city,root in sources
            if urlparse(url).hostname==urlparse(root).hostname]
  if not matching:
   unapproved.append({'url':url,'title':title,'reason':'New source needs organizer approval; not fetched or published.'})
   continue
  if not valid_url(url):continue
  linked=[entry for entry in matching if entry[2] in root_docs and
          url in root_docs[entry[2]].root.links(entry[2]) and url!=entry[2]]
  if not linked:unlinked.append(url);continue
  name,city,root=linked[0]
  leads[url]={'target_url':url,'source_url':root,'title':title,
              'organizer':name,'city':city,
              'notes':'Regional search hint corroborated by a live official organizer link. Vendor availability still requires verification.'}
  if inspected>=MAX_SEARCH_PAGES:continue
  if getattr(fetcher,'requests',0)>=getattr(fetcher,'limit',100000)-100:continue
  try:
   doc,_=fetcher.get(url);inspected+=1
   es,_,_=extract_links(doc,url);events.update(es)
  except Exception:continue
 stats.update({'official_pages_inspected':inspected,'official_linked_leads':len(leads),
               'unapproved_source_count':len(unapproved),'unapproved_sources':rotate(unapproved,now,12),
               'unlinked_official_results':rotate(unlinked,now,8)})
 return list(leads.values()),events,stats

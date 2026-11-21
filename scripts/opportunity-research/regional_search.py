"""Search hints never establish dates, fees, vendor availability, or source trust."""
from urllib.parse import urlparse,urlencode
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

def search_results(now,opener=None):
 from discovery import NoSearchRedirect,MAX_FEED_BYTES,is_safe_lead_url
 opener=opener or build_opener(NoSearchRedirect())
 hits={};failures=[];succeeded=0
 for query in queries(now)[:MAX_QUERIES]:
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
    if is_safe_lead_url(url):hits.setdefault(url,title[:160])
  except (OSError,ValueError,ET.ParseError):failures.append(query)
 return hits,{'queries_attempted':len(queries(now)[:MAX_QUERIES]),'queries_succeeded':succeeded,
              'query_failures':failures,'result_urls':len(hits)}

def discover_regional(fetcher,now,sources,root_docs,opener=None):
 from verifier import valid_url,canonical_event
 from discovery import extract_links
 hits,stats=search_results(now,opener)
 leads={};events=set();unapproved=[];unlinked=[];inspected=0
 for url,title in sorted(hits.items()):
  event=canonical_event(url)
  if event:events.add(event);continue
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
               'unapproved_source_count':len(unapproved),'unapproved_sources':unapproved[:30],
               'unlinked_official_results':unlinked[:20]})
 return list(leads.values()),events,stats

"""Triangle-wide discovery: search hints + curated organizer sources, never blind publication.

Every incoming Internet link is untrusted. Fetch only exact approved HTTPS hosts,
validate Eventeny event + vendor-application metadata, and stage new listings as
unpublished drafts. Other organizer application links become private admin leads.
Standard library only; the search feed is optional and may be unavailable.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlencode, urlparse, urljoin
from urllib.request import Request, build_opener, HTTPRedirectHandler
import ipaddress
import re
import xml.etree.ElementTree as ET

from verifier import (Uncertain, canonical_event, canonical_application,
                      validate_event, verify, norm, source_error, CITIES)

# Official vendor/market sources distributed throughout the Triangle.
# These are *discovery hints*, not a license to auto-publish their listings.
# All addresses must also be covered by verifier.HOSTS.
SOURCES = (
 ('Triangle Pop-Up', 'Raleigh', 'https://www.trianglepopup.com/applications'),
 ('Night Market Company', 'Cary', 'https://thenightmarketcompany.com/'),
 ('Shop Local Raleigh', 'Raleigh', 'https://shoplocalraleigh.org/vendor-information/'),
 ('Geek and Grub', 'Raleigh', 'https://www.geekandgrubmarket.com/vendorapplication'),
 ('Hummingbird Market', 'Raleigh', 'https://hummingbirdmarketnc.com/member-markets'),
 ('Cary Farmers Market', 'Cary', 'https://www.caryfarmersmarket.com/vendor-application/'),
 ('Hillsborough Arts Council', 'Hillsborough', 'https://www.hillsboroughartscouncil.org/last-fridays-markets'),
 ('The Bazaar', 'Carrboro', 'https://www.takethehighstreet.com/thebazaar'),
 ('Black Farmers Market', 'Durham', 'https://blackfarmersmkt.org/the-market/'),
 ('Durham Craft Market', 'Durham', 'https://www.durhamcraftmarket.com/saturdays-in-durham-central-park.html'),
 ('Carrboro Farmers Market', 'Carrboro', 'https://www.carrborofarmersmarket.com/'),
 ('Apex Farmers Market', 'Apex', 'https://www.apexfarmersmarket.com/'),
 ('Artspace', 'Raleigh', 'https://artspacenc.org/calls-for-art/'),
 ('Artsplosure', 'Raleigh', 'https://www.artsplosure.org/first-night-raleigh'),
)
# Four-region search: no account or API key. Results supply *URLs only*, never
# dates, names, organizer, availability, or prices.
REGIONS = ('Raleigh', 'Durham', 'Cary Apex', 'Chapel Hill Carrboro')
MAX_FEED_BYTES = 300_000
MAX_LINKS = 40
MAX_EVENTS = 30
MAX_APPLICATIONS = 25
MAX_NEW_DRAFTS = 8
MAX_LEADS = 40

class NoSearchRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):
  raise ValueError('Search feed redirected')

def is_safe_lead_url(value):
 try:
  p=urlparse(value)
  host=p.hostname or ''
  if p.scheme!='https' or not host or not re.fullmatch(r'[A-Za-z0-9.-]{4,180}',host):
   return False
  if p.username or p.password or p.port not in (None,443) or p.fragment or len(value)>1200:
   return False
  if host in {'localhost','localhost.localdomain'} or host.endswith(('.localhost','.local','.internal','.test')):
   return False
  try:
   ipaddress.ip_address(host)
   return False
  except ValueError:
   pass
  return True
 except ValueError:return False

def is_application_hint(url,label):
 if not is_safe_lead_url(url):return False
 p=urlparse(url)
 if canonical_application(url):return True
 if p.hostname in {'docs.google.com','forms.gle','form.jotform.com'}:
  from verifier import valid_url
  return valid_url(url)
 words=(label+' '+p.path.replace('-',' ')+' '+p.query.replace('_',' ')).lower()
 return bool(re.search(r'\b(?:vendor|vendors|merchant|merchants|exhibitor|exhibitors|booth|apply|application|applications)\b',words))

def search_urls(now, opener=None):
 """Optional keyless search discovery. Fail closed to an empty set on outages."""
 opener=opener or build_opener(NoSearchRedirect())
 urls=set()
 for region in REGIONS:
  q=f'site:eventeny.com/events/ vendor application {region} North Carolina {now.year} {now.year+1}'
  endpoint='https://www.bing.com/search?'+urlencode({'q':q,'format':'rss'})
  try:
   with opener.open(Request(endpoint,headers={'User-Agent':'BehindTheBoothDiscovery/1.0'}),timeout=8) as response:
    if urlparse(response.url).hostname not in {'www.bing.com','bing.com'}:continue
    raw=response.read(MAX_FEED_BYTES+1)
   if len(raw)>MAX_FEED_BYTES or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():continue
   root=ET.fromstring(raw)
   if root.tag!='rss':continue
   for link in root.findall('.//item/link'):
    if link.text:
     event=canonical_event(link.text.strip())
     if event:urls.add(event)
  except (OSError,ValueError,ET.ParseError):
   # Search hints are never required for the existing verified-listing checks.
   continue
 return urls

def extract_links(doc, base):
 """Collect only bounded, explicit links from trusted source pages."""
 event_urls=set()
 app_urls=set()
 lead_urls=set()
 for node in doc.root.walk():
  if node.tag!='a' or not node.attrs.get('href'):continue
  url=urljoin(base,node.attrs['href'])
  event=canonical_event(url)
  if event:
   event_urls.add(event);continue
  app=canonical_application(url)
  if app:
   app_urls.add(app);continue
  label=node.text()[:180]
  if is_application_hint(url,label):lead_urls.add((url,label))
 return event_urls,app_urls,lead_urls

def _stage_event(source,app,fetcher,now):
 """An independently verifiable dated vendor application becomes a draft only."""
 doc,_=fetcher.get(source)
 metadata=list(doc.events())
 if len(metadata)!=1 or not isinstance(metadata[0].get('organizer'),dict):
  return None
 organizer=metadata[0]['organizer'].get('name','')
 if not organizer:return None
 try:
  _,start,end,addr=validate_event(doc,now,organizer)
 except (Uncertain,TypeError,ValueError):
  return None
 if not any(canonical_application(link)==app for node in doc.root.walk()
            if 'app-card' in node.attrs.get('class','').split()
            for link in node.links(source)):
  return None
 # This verifier checks *both* the event and application, including the organizer
 # account, dates, availability, deadline and enabled start controls.
 expected={'market_id':None,'market_organizer':organizer,
           'market_city':addr['addressLocality'],'market_state':'NC',
           'starts_on':start.date().isoformat(),'ends_on':end.date().isoformat()}
 try:
  result=verify(source,app,fetcher,now,expected_item=expected)
 except (Uncertain,ValueError,TypeError):
  return None
 candidate=result.get('candidate') or {}
 if candidate.get('availability') not in {'open','limited','waitlist'}:
  return None
 if not candidate.get('deadline') or candidate.get('state')!='NC':
  return None
 if (candidate.get('city') or '').lower() not in CITIES:
  return None
 # Newly discovered profiles cannot inherit another organizer's reviews.
 candidate['market_slug']=None
 result['decision']='review'
 result['policy']='triangle-discovery-v1'
 result['reason']='New Triangle vendor application found on an official dated event page. Confirm the organizer, linked market and terms before publishing.'
 return result

def discover_triangle(fetcher,now=None,include_search=True,known=None):
 """Returns (unpublished candidates, form leads, diagnostics).

 Errors on optional outside pages do not erase validated listings or turn
 source discovery into a false "no applications" claim.
 """
 now=now or datetime.now(timezone.utc)
 known=known or set()
 events=set()
 apps=set()
 raw_leads={}
 failures=[]
 for organizer,city,root in SOURCES:
  try:
   doc,_=fetcher.get(root)
   es,aa,links=extract_links(doc,root)
   events.update(es);apps.update(aa)
   for url,label in links:
    if url not in raw_leads:
     raw_leads[url]={'target_url':url,'source_url':root,
       'title':(label or 'Vendor application')[:160],
       'organizer':organizer,'city':city,
       'notes':'Found on a curated organizer page. Exact event date and application status have not been verified.'}
  except Exception as error:
   failures.append(f'{organizer}: {source_error(error)}')
 if include_search:
  events.update(search_urls(now))
 # Recognized vendor-application links can supply their *own* Eventeny event URL.
 for app in sorted(apps)[:MAX_APPLICATIONS]:
  try:
   doc,_=fetcher.get(app)
   for e in doc.events():
    url=canonical_event(e.get('url',''))
    if url:events.add(url)
   for link in doc.root.links(app):
    url=canonical_event(link)
    if url:events.add(url)
  except Exception:
   continue
 staged={}
 for event in sorted(events)[:MAX_EVENTS]:
  if len(staged)>=MAX_NEW_DRAFTS:break
  try:
   doc,_=fetcher.get(event)
   es,aa,_=extract_links(doc,event)
   appcards=set()
   for node in doc.root.walk():
    if 'app-card' not in node.attrs.get('class','').split():continue
    appcards.update(a for u in node.links(event) if (a:=canonical_application(u)))
   for app in sorted(appcards)[:8]:
    candidate=_stage_event(event,app,fetcher,now)
    if not candidate:continue
    data=candidate['candidate']
    key=(data['application_url'],data['starts_on'])
    if key in staged or key in known:continue
    staged[key]=candidate
    if len(staged)>=MAX_NEW_DRAFTS:break
  except Exception:
   continue
 leads=list(raw_leads.values())[:MAX_LEADS]
 stats={'discovery_sources':len(SOURCES),'optional_source_failures':failures[:10],
        'discovery_event_urls':len(events),'discovery_vendor_application_urls':len(apps),
        'discovery_reviewable_drafts':len(staged),'discovery_unconfirmed_leads':len(leads)}
 return list(staged.values()),leads,stats

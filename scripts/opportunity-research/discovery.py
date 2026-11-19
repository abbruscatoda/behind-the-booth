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
 ('Chapel Hill Farmers Market', 'Chapel Hill', 'https://www.thechapelhillfarmersmarket.com/'),
 ('Holly Springs Farmers Market', 'Holly Springs', 'https://www.hollyspringsnc.gov/319/Farmers-Market'),
 ('Western Wake Farmers Market', 'Morrisville', 'https://westernwakefarmersmarket.org/'),
 ('Eno River Farmers Market', 'Hillsborough', 'https://www.enoriverfarmersmarket.com/'),
 ('Fuquay-Varina Growers Market', 'Fuquay-Varina', 'https://www.fvgrowersmarket.com/'),
 ('YMCA of the Triangle', 'Cary', 'https://www.ymcatriangle.org/events/vendor-market'),
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
 # Discovery should surface actionable vendor applications, not the site's
 # vendor directory, employment application, PDF policies, or advertisements.
 if p.path.lower().endswith(('.pdf','.jpg','.png','.zip')):return False
 title=label.lower().strip()
 path=p.path.lower().replace('-',' ').replace('_',' ')
 combined=title+' '+path
 if re.search(r'\b(?:volunteer|musician|employment|work with us|careers?|staff|job|jobs|hiring|'
              r'faq|faqs|rules|policies|resources?|directories|members|our vendors|meet our vendors|'
              r'payment|payments|closed|fundrais(?:er|ing)|community booth|nonprofit|sponsor|'              r'survey|teaching artists?|workshops?|programs?\s*&\s*registration)\b',combined):
  return False
 if p.hostname in {'godaddy.com','www.godaddy.com'}:return False
 if canonical_application(url):return True
 if p.hostname in {'docs.google.com','forms.gle','form.jotform.com','pci.jotform.com'}:
  from verifier import valid_url
  if p.hostname=='pci.jotform.com':
   return bool(re.fullmatch(r'/form/[0-9]{10,20}',p.path) and not p.query)
  return valid_url(url)
 # A generic vendor information page is not a new application.
 if re.search(r'\b(?:info|information|opportunities|our vendors|vendor list)\b',combined) and not re.search(r'\b(?:apply|application|applications|register|registration)\b',title):
  return False
 return bool(re.search(r'\b(?:apply|application|applications|registration|register)\b',combined)
             or re.search(r'\b(?:be|become) a vendor\b',combined))

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
  if url.rstrip('/#')!=base.rstrip('/#') and is_application_hint(url,label):lead_urls.add((url,label))
 return event_urls,app_urls,lead_urls

def _stage_event(source,app,fetcher,now):
 """Verify a new dated Eventeny application before requesting automatic publication."""
 doc,_=fetcher.get(source)
 metadata=list(doc.events())
 if not metadata or not all(isinstance(e.get('organizer'),dict) for e in metadata):
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
 # A dated event cannot borrow a form from another occurrence just
 # because the event name or organizer matches. The application's structured
 # event date must either match or explicitly span this dated occurrence.
 try:
  app_doc,_=fetcher.get(app)
  dates=[]
  for entry in app_doc.events():
   app_start=datetime.fromisoformat(entry['startDate'])
   app_end=datetime.fromisoformat(entry['endDate'])
   if app_start.tzinfo is None or app_end.tzinfo is None:continue
   dates.append((app_start.date(),app_end.date()))
  if not any(a<=start.date() and b>=end.date() for a,b in dates):
   return None
 except (KeyError,TypeError,ValueError):
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
 # The database independently checks the submitted market identity, date,
 # linked source/application, category and quality receipts before publishing.
 # Never borrow an unrelated existing market or its historical reviews.
 if result.get('category_conflicts') or result.get('decision')=='closed':
  return None
 if result.get('decision')=='review' and result.get('reason')!='New or unmatched market profile: confirm identity and create/link a profile.':
  return None
 if result.get('research_quality',{}).get('fields',{}).get('identity',{}).get('status')!='confirmed':
  return None
 if result.get('research_quality',{}).get('fields',{}).get('availability',{}).get('status')!='confirmed':
  return None
 candidate['market_slug']=None
 result['decision']='publish'
 result['policy']='triangle-eventeny-auto-v1'
 result['reason']='Organizer account, dated event and enabled vendor application independently verified for automated publication.'
 return result

def discover_triangle(fetcher,now=None,include_search=True,known=None,include_calendars=True):
 """Returns (unpublished candidates, form leads, diagnostics).

 Errors on optional outside pages do not erase validated listings or turn
 source discovery into a false "no applications" claim. Unverified URLs remain
 private leads. Fully verified Eventeny opportunities are eligible for the
 separate database-side automatic publisher.
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
 # Join dated official event calendars to specific organizer applications.
 # This is an evidence-gathering layer, NOT permission to publish. Existing
 # Eventeny and public-form source validators still make the decision.
 from calendar_research import discover_calendars
 if include_calendars:
  cal_events,calendar_pairs,calendar_stats=discover_calendars(fetcher)
  events.update(cal_events)
 else:
  calendar_pairs=[]
  calendar_stats={'calendar_sources':0,'calendar_event_pages_inspected':0,
                  'calendar_eventeny_urls':0,'calendar_form_pairs':0,
                  'calendar_source_failures':[]}
 # Follow only one same-host application page from each curated organizer.
 # An organizer's front page often links to a separate, current application
 # index; that index can in turn link to a dated Eventeny event. Never crawl
 # unrelated domains, form submissions, arbitrary URLs, or multiple layers.
 from verifier import valid_url
 followed=set()
 for entry in list(raw_leads.values()):
  target=entry['target_url']
  source=entry['source_url']
  if len(followed)>=30:break
  if urlparse(target).hostname!=urlparse(source).hostname or not valid_url(target):continue
  if target in followed:continue
  followed.add(target)
  try:
   inner,_=fetcher.get(target)
   extra_events,extra_apps,_=extract_links(inner,target)
   events.update(extra_events)
   apps.update(extra_apps)
  except Exception:
   continue
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
 # A public Jotform/Google Form can qualify too, but only when it
 # independently matches a single dated official organizer event and exposes
 # a live Submit control plus an exact future deadline. Generic seasonal
 # forms are deliberately left as private leads.
 from form_discovery import verify_public_form
 verified_forms=0
 for lead in (calendar_pairs+list(raw_leads.values()))[:MAX_LEADS+30]:
  if len(staged)>=MAX_NEW_DRAFTS:break
  result=verify_public_form(lead,fetcher,now)
  if not result:continue
  data=result['candidate']
  key=(data['application_url'],data['starts_on'])
  if key in known or key in staged:continue
  staged[key]=result
  verified_forms+=1
 # Never put already-published applications back into the action queue,
 # regardless of whether their source uses Eventeny or a public form.
 known_apps={url for url,_ in known if url}
 leads=[lead for lead in raw_leads.values() if lead['target_url'] not in known_apps][:MAX_LEADS]
 stats={'discovery_sources':len(SOURCES),'optional_source_failures':failures[:10],
        'discovery_event_urls':len(events),'discovery_vendor_application_urls':len(apps),
        'discovery_followed_organizer_pages':len(followed),
        'discovery_verified_candidates':len(staged),
        'discovery_verified_public_forms':verified_forms,'discovery_unconfirmed_leads':len(leads),
        'calendar':calendar_stats}
 return list(staged.values()),leads,stats

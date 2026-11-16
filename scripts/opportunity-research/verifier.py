"""Deterministic, read-only official-source verification. Standard library only."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
import hashlib, json, re, time

POLICY = 'makrs-eventeny-v1'
ROOTS = ['https://makrs.com/market-applications','https://makrs.com/makrs-holiday-fest', 'https://makrs.com/moore-square-winterfaire']
# Exact series identity; a familiar organizer alone never borrows another market's reviews.
SERIES = {
 'durhamundergroundmarket':('durham-underground-market','Durham Underground Market'),
 'rtpundergroundmarket':('rtp-underground-market','RTP Underground Market'),
 'caryundergroundmarket':('cary-underground-market','Cary Underground Market'),
 'raleighundergroundmarket':('raleigh-underground-market','Raleigh Underground Market'),
 'apexundergroundmarket':('apex-underground-market','Apex Underground Market'),
 'wendellundergroundmarket':('wendell-underground-market','Wendell Underground Market'),
 'durhamfoodiefare':('durham-foodie-fare','Durham Foodie Fare'),
 'raleightwilightmarket':('raleigh-twilight-market','Raleigh Twilight Market'),
}
CITIES={'raleigh','durham','cary','apex','wendell','rolesville','wake forest','chapel hill','carrboro','holly springs','fuquay-varina','morrisville','garner','clayton','pittsboro','hillsborough'}
HOSTS={'makrs.com','www.makrs.com','eventeny.com','www.eventeny.com'}
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
def norm(value):return re.sub(r'[^a-z0-9]','',value.lower())
def clean(value):return ' '.join(unescape(value).split())
def valid_url(url):
 p=urlparse(url)
 return p.scheme=='https' and p.hostname in HOSTS and not p.username and not p.password and p.port in (None,443) and not p.fragment

def application_key(url):
 p=urlparse(url)
 ids=parse_qs(p.query).get('id',[])
 if p.hostname not in {'www.eventeny.com','eventeny.com'} or p.path.rstrip('/')!='/events/vendor' or len(ids)!=1 or not ids[0].isdigit():return None
 return ids[0]
def canonical_application(url):
 key=application_key(url)
 return 'https://www.eventeny.com/events/vendor/?id='+key if key else None

def canonical_event(url):
 p=urlparse(url)
 if p.hostname not in {'www.eventeny.com','eventeny.com'} or not re.fullmatch(r'/events/[a-zA-Z0-9-]+-\d+/?',p.path):return None
 series=parse_qs(p.query).get('series',[])
 return 'https://www.eventeny.com'+p.path.rstrip('/')+'/' + ('?'+urlencode({'series':series[0]}) if len(series)==1 and series[0].isdigit() else '')

@dataclass
class Node:
 tag:str; attrs:dict=field(default_factory=dict); children:list=field(default_factory=list)
 def text(self):return clean(' '.join(x.text() if isinstance(x,Node) else x for x in self.children if not isinstance(x,Node) or x.tag not in {'script','style','noscript'}))
 def walk(self):
  yield self
  for x in self.children:
   if isinstance(x,Node):yield from x.walk()
 def links(self,base):return [urljoin(base,n.attrs['href']) for n in self.walk() if n.attrs.get('href')]
class Document(HTMLParser):
 def __init__(self,html):
  super().__init__(convert_charrefs=True);self.root=Node('root');self.stack=[self.root];self.feed(html)
 def handle_starttag(self,tag,attrs):
  node=Node(tag,dict(attrs));self.stack[-1].children.append(node)
  if tag not in VOID:self.stack.append(node)
 def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==tag:self.stack=self.stack[:i];break
 def handle_data(self,data):self.stack[-1].children.append(data)
 def events(self):
  for n in self.root.walk():
   if n.tag=='script' and n.attrs.get('type')=='application/ld+json':
    try:obj=json.loads(''.join(x for x in n.children if isinstance(x,str)))
    except (ValueError,TypeError):continue
    for item in (obj if isinstance(obj,list) else obj.get('@graph',[obj])):
     if isinstance(item,dict) and item.get('startDate') and item.get('location'):yield item

class SafeRedirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  if not valid_url(newurl):raise ValueError('Redirect left trusted source hosts')
  return super().redirect_request(req,fp,code,msg,headers,newurl)
class Fetcher:
 def __init__(self,limit=90):self.limit=limit;self.requests=0;self.cache={};self.opener=build_opener(SafeRedirect())
 def get(self,url):
  if not valid_url(url):raise ValueError('Untrusted URL')
  if url in self.cache:return self.cache[url]
  if self.requests>=self.limit:raise ValueError('Source request budget reached')
  self.requests+=1
  time.sleep(.2)
  with self.opener.open(Request(url,headers={'User-Agent':'BehindTheBoothVerifier/1.0 (+https://www.behindtheboothhq.com/contact)'}),timeout=20) as response:
   if not valid_url(response.url):raise ValueError('Untrusted destination')
   if 'text/html' not in response.headers.get('Content-Type',''):raise ValueError('Expected an HTML source')
   raw=response.read(2_000_001)
   if len(raw)>2_000_000:raise ValueError('Source too large')
  html=raw.decode('utf-8',errors='replace');result=(Document(html),hashlib.sha256(raw).hexdigest());self.cache[url]=result;return result

class Uncertain(ValueError):pass

def exact_series(name):
 # Match a whole normalized name after a year and optional parenthetical venue.
 stem=norm(re.sub(r'\([^)]*\)','',re.sub(r'^\s*20\d{2}\s*','',name)).strip())
 return SERIES.get(stem)

def deadline_from(text):
 match=re.search(r'Deadline:\s*([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})\s+(\d{1,2}:\d{2})\s*(am|pm)\s*\(GMT([+-]\d{2}:\d{2})\)',text,re.I)
 if not match:raise Uncertain('Application deadline/timezone could not be verified')
 month,day,year,clock,ampm,offset=match.groups()
 stamp=f'{month[:3]} {day} {year} {clock} {ampm.upper()} {offset.replace(":","")}'
 return datetime.strptime(stamp,'%b %d %Y %I:%M %p %z')

def validate_event(doc,now):
 events=list(doc.events())
 # Reject contradictory metadata rather than picking whichever result looks convenient.
 dates={(e.get('startDate'),e.get('endDate'),e.get('name')) for e in events}
 if len(dates)!=1:raise Uncertain('Exact dated event metadata is missing or contradictory')
 event=events[0]
 if event.get('organizer',{}).get('url','').rstrip('/') not in {'https://www.eventeny.com/company/?c=27023','https://eventeny.com/company/?c=27023'}:raise Uncertain('Organizer identity is not the trusted MAKRS account')
 if norm(event['organizer'].get('name',''))!='themakrssociety':raise Uncertain('Organizer name does not match MAKRS')
 if event.get('eventStatus')!='https://schema.org/EventScheduled':raise Uncertain('Event is cancelled, postponed, or not confirmed scheduled')
 start=datetime.fromisoformat(event['startDate']);end=datetime.fromisoformat(event['endDate'])
 if start.tzinfo is None or end.tzinfo is None or end<start:raise Uncertain('Event dates or timezone are invalid')
 if (end.date()-start.date()).days>14:raise Uncertain('Source describes a series range, not a specific dated event')
 if end<now or start>now+timedelta(days=183):raise Uncertain('Event is outside the upcoming six-month window')
 addr=event['location'].get('address',{})
 if addr.get('addressRegion') not in {'NC','North Carolina'} or addr.get('addressLocality','').lower() not in CITIES:raise Uncertain('Event location is outside the Triangle source policy')
 return event,start,end,addr

def verify(source_url,application_url,fetcher,now=None):
 """Returns verified facts or raises Uncertain. No content supplied by an AI is trusted."""
 now=now or datetime.now(timezone.utc)
 source_url=canonical_event(source_url);application_url=canonical_application(application_url)
 if not source_url or not application_url:raise Uncertain('A dated Eventeny event and vendor application are required')
 doc,source_hash=fetcher.get(source_url);event,start,end,addr=validate_event(doc,now)
 cards=[n for n in doc.root.walk() if 'app-card' in n.attrs.get('class','').split() and any(application_key(u)==application_key(application_url) for u in n.links(source_url))]
 if len(cards)!=1:raise Uncertain('This application is not uniquely linked from the dated event')
 card=cards[0];card_text=card.text()
 buttons=[n for n in card.walk() if n.tag in {'a','button-element'} and application_key(urljoin(source_url,n.attrs.get('href','')))==application_key(application_url) and n.text().lower() in {'apply now','join waitlist','apply to waitlist'}]
 closed=not buttons and bool(re.search(r'\b(applications? (?:are |is )?closed|application closed|no longer accepting applications)\b',card_text,re.I))
 if not buttons and not closed:raise Uncertain('No active application action for this event/date')
 if not closed and not re.search(r'\b\d+\s+active applications\b',doc.root.text(),re.I):raise Uncertain('Dated page does not label its applications active')
 # Do not merge food truck applications into the artist/vendor opportunity.
 heading=' '.join(n.text() for n in card.walk() if n.tag=='a' and application_key(urljoin(source_url,n.attrs.get('href','')))==application_key(application_url))
 if re.search(r'food trucks?',heading,re.I):raise Uncertain('Food-truck application requires a separate category-specific listing')
 app,app_hash=fetcher.get(application_url);text=app.root.text()
 app_events=list(app.events())
 if not app_events or any(norm(e.get('organizer',{}).get('name',''))!='themakrssociety' for e in app_events):raise Uncertain('Application organizer could not be verified')
 if any(norm(e.get('name',''))!=norm(event.get('name','')) for e in app_events):raise Uncertain('Application and dated event identities disagree')
 if not closed and not re.search(r'\bStart Application\b',text,re.I):raise Uncertain('Application is not accepting starts')
 try:deadline=deadline_from(text)
 except Uncertain:
  if not closed:raise
  deadline=None
 if deadline and deadline<=now:closed=True
 status='closed' if closed else 'open'
 if closed:pass
 elif re.search(r'\b(waitlist only|join (?:the )?waitlist|apply to waitlist)\b',card_text+' '+text,re.I):status='waitlist'
 elif re.search(r'\blimited (?:vendor )?(?:spaces|booths|availability)\b',card_text+' '+text,re.I):status='limited'
 elif re.search(r'\b(sold out|fully booked|no longer accepting|applications? (?:are |is )?closed|application closed|deadline (?:has )?passed|waitlist|wait list)\b',card_text+' '+text,re.I):raise Uncertain('Closure, sold-out, or waitlist wording needs review')
 if status=='open' and any(n.text().lower()!='apply now' for n in buttons):raise Uncertain('Application action contradicts open status')
 amounts=set(re.findall(r'\$([\d,]+(?:\.\d{1,2})?)\s+(?:vendor|booth) fee\b',card_text,re.I))
 fee=float(next(iter(amounts)).replace(',','')) if len(amounts)==1 else None
 series=exact_series(event['name'])
 return {'policy':POLICY,'decision':('closed' if status=='closed' else 'publish') if series else 'review','reason':'' if series else 'New or unmatched market profile: confirm identity and create/link a profile.',
  'checked_at':now.isoformat(),'source_hash':source_hash,'application_hash':app_hash,'evidence':card_text[:600],
  'candidate':{'title':series[1] if series else event['name'][:160], 'market_slug':series[0] if series else None,'organizer':'The MAKRS Society', 'city':addr['addressLocality'],'state':'NC',
   'venue':', '.join(filter(None,[event['location'].get('name'),addr.get('streetAddress')])), 'starts_on':start.date().isoformat(),'ends_on':end.date().isoformat(), 'deadline':deadline.isoformat() if deadline else None,
   'application_url':application_url,'source_url':source_url,'availability':status,'booth_fee':fee,'application_fee':None,'deposit':None,'categories':[],
   'fee_notes':'Processing fees may be additional. Other booth types have separate pricing. Confirm totals with the organizer.',
   'eligibility':'The official event page lists an active application for this date. Acceptance and category availability are subject to organizer approval; remaining booth spaces are not published.'+(' No MLM businesses.' if re.search(r'no\s+mlm',text,re.I) else '')}}


def discover(fetcher,now=None):
 """Discover only linked official applications; never search random pages for positive phrases."""
 applications=set();events=set();problems=[]
 for root in ROOTS:
  try:
   doc,_=fetcher.get(root)
   for link in doc.root.links(root):
    if canonical_application(link):applications.add(canonical_application(link))
    if canonical_event(link):events.add(canonical_event(link))
  except Exception:problems.append('Official source could not be read: '+root)
 if not applications and not events:problems.append('Official discovery pages contained no recognized application links. Check for a source layout change.')
 for url in sorted(applications)[:25]:
  try:
   doc,_=fetcher.get(url)
   for event in doc.events():
    if canonical_event(event.get('url','')):events.add(canonical_event(event['url']))
   for link in doc.root.links(url):
    if canonical_event(link):events.add(canonical_event(link))
  except Exception:problems.append('Application could not be read: '+url)
 # Follow one series-date layer to get each occurrence instead of using a series date range.
 for url in sorted(events)[:25]:
  try:
   doc,_=fetcher.get(url)
   for link in doc.root.links(url):
    if canonical_event(link):events.add(canonical_event(link))
  except Exception:problems.append('Dated source could not be read: '+url)
 results=[];seen=set()
 for url in sorted(events)[:45]:
  try:
   doc,_=fetcher.get(url);event,start,end,addr=validate_event(doc,now or datetime.now(timezone.utc))
   for n in doc.root.walk():
    if 'app-card' not in n.attrs.get('class','').split():continue
    for link in n.links(url):
     app=canonical_application(link)
     key=(url,app)
     if app and key not in seen:
      seen.add(key)
      try:results.append(verify(url,app,fetcher,now))
      except Uncertain as error:
       if 'Food-truck application requires' in str(error):continue
       series=exact_series(event['name'])
       results.append({'decision':'review','reason':str(error),'candidate':{'title':series[1] if series else event['name'][:160], 'market_slug':series[0] if series else None,'organizer':'The MAKRS Society','city':addr['addressLocality'],'state':'NC','venue':', '.join(filter(None,[event['location'].get('name'),addr.get('streetAddress')])), 'starts_on':start.date().isoformat(),'ends_on':end.date().isoformat(),'application_url':app,'source_url':url,'deadline':None,'categories':[]}})
  except Exception:continue
 grouped={}
 for result in results:
  candidate=result['candidate'];key=(candidate['application_url'],candidate['starts_on'])
  if key in grouped:
   prior=grouped[key]
   fields=('ends_on','deadline','availability','city','market_slug')
   if any(prior['candidate'].get(field)!=candidate.get(field) for field in fields):
    grouped[key]={'decision':'review','reason':'Official pages disagree about this application/date. Confirm the current details.','candidate':candidate}
  else:grouped[key]=result
 return list(grouped.values()),problems

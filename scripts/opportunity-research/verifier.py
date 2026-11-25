"""Deterministic, read-only official-source verification. Standard library only."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import hashlib, json, re, time, os

POLICY = 'makrs-eventeny-v5-quality'
ROOTS = ['https://makrs.com/market-applications','https://makrs.com/makrs-holiday-fest', 'https://makrs.com/moore-square-winterfaire']
# Exact series identity; a familiar organizer alone never borrows another market's reviews.
SERIES = {
 'makrsholidayfest':('makrs-holiday-fest','MAKRS Holiday Fest'),
 'mooresquarewinterfaire':('moore-square-winterfaire','Moore Square Winterfaire'),
 'durhamundergroundmarket':('durham-underground-market','Durham Underground Market'),
 'rtpundergroundmarket':('rtp-underground-market','RTP Underground Market'),
 'caryundergroundmarket':('cary-underground-market','Cary Underground Market'),
 'raleighundergroundmarket':('raleigh-underground-market','Raleigh Underground Market'),
 'apexundergroundmarket':('apex-underground-market','Apex Underground Market'),
 'wendellundergroundmarket':('wendell-underground-market','Wendell Underground Market'),
 'durhamfoodiefare':('durham-foodie-fare','Durham Foodie Fare'),
 'raleightwilightmarket':('raleigh-twilight-market','Raleigh Twilight Market'),
}
CITIES={'raleigh','durham','cary','apex','wendell','rolesville','wake forest','chapel hill','carrboro','holly springs','fuquay-varina','morrisville','garner','clayton','pittsboro','hillsborough','knightdale','zebulon','youngsville','creedmoor','angier','siler city','mebane','franklinton'}
HOSTS={'forms.monday.com','linktr.ee','grlmarket.com','www.grlmarket.com','www.dogwoodraleigh.com','www.hartwellraleigh.com','www.visitnorthhills.com','www.grasshopperfarmsnc.com','www.unhingedcoffee.co','downtownraleigh.org','managemymarket.com','www.cognitoforms.com','www.queerolina.org','queerolina.org','www.eventbrite.com','www.havenofknightdale.com','havenofknightdale.com',
 'ncvintagebazaar.com','www.ncvintagebazaar.com','thepatchworkmarket.com','www.thepatchworkmarket.com',
 'www.rebusworks.us','rebusworks.us','raleighretrogamers.com','www.raleighretrogamers.com','www.artsplosure.org','docs.google.com','forms.gle','makrs.com','www.makrs.com','eventeny.com','www.eventeny.com','artspacenc.org','form.jotform.com','pci.jotform.com',
 'www.trianglepopup.com','trianglepopup.com','thenightmarketcompany.com','www.thenightmarketcompany.com',
 'shoplocalraleigh.org','www.shoplocalraleigh.org','www.geekandgrubmarket.com','geekandgrubmarket.com',
 'hummingbirdmarketnc.com','www.hummingbirdmarketnc.com','www.caryfarmersmarket.com','caryfarmersmarket.com',
 'www.hillsboroughartscouncil.org','hillsboroughartscouncil.org','www.takethehighstreet.com','takethehighstreet.com',
 'blackfarmersmkt.org','www.blackfarmersmkt.org','www.durhamcraftmarket.com','durhamcraftmarket.com',
 'www.carrborofarmersmarket.com','carrborofarmersmarket.com','www.apexfarmersmarket.com','apexfarmersmarket.com',
 'www.thechapelhillfarmersmarket.com','thechapelhillfarmersmarket.com','www.hollyspringsnc.gov','hollyspringsnc.gov',
 'westernwakefarmersmarket.org','www.westernwakefarmersmarket.org','www.enoriverfarmersmarket.com','enoriverfarmersmarket.com',
 'www.fvgrowersmarket.com','fvgrowersmarket.com','www.ymcatriangle.org','ymcatriangle.org',
 'wakeforestmarket.org','www.wakeforestmarket.org',
 'www.theraleighmarket.com','theraleighmarket.com','chathammillsfarmersmarket.com','www.chathammillsfarmersmarket.com',
 'www.durhamfarmersmarket.com','durhamfarmersmarket.com','www.downtownrolesvillefarmersmarket.com','downtownrolesvillefarmersmarket.com',
 'www.cfcmnc.org','cfcmnc.org','fearringtonfarmersmarket.com','www.fearringtonfarmersmarket.com',
 'www.thepittsborofarmersmarket.org','thepittsborofarmersmarket.org',
 'www.northdurhamfarmersmarket.com','northdurhamfarmersmarket.com','southdurhamfarmersmarket.com','www.southdurhamfarmersmarket.com',
 'midtownfarmers.com','www.midtownfarmers.com','www.dgfleamarket.com','dgfleamarket.com',
 'popupraleigh.com','www.popupraleigh.com','www.artpostnc.com','artpostnc.com','www.cecysgallery.com','cecysgallery.com',
 'raleighnc.gov','www.raleighnc.gov','dprplaymore.org','www.dprplaymore.org','durhamcentralpark.org','www.durhamcentralpark.org',
 'carync.gov','www.carync.gov','apexnc.org','www.apexnc.org',
 'chapelhillarts.org','www.chapelhillarts.org','wakeforestnc.gov','www.wakeforestnc.gov',
 'rolesvillenc.gov','www.rolesvillenc.gov','wendellchamber.com','www.wendellchamber.com',
 'sweetwaterapex.com','www.sweetwaterapex.com','triangleartworks.org','www.triangleartworks.org',
 'garnernc.gov','www.garnernc.gov','knightdalenc.gov','www.knightdalenc.gov','ncagr.gov','www.ncagr.gov'}
HOSTS.update({'www.theoptimistraleigh.com','www.songbird.bar','www.nomadascoffee.com',
 'www.frontpaigemedia.org','raleighironworks.com','downtowndurham.com','www.ncarts.org',
 'www.zapplication.org','www.caryquilting.com'})
MAX_SOURCE_BYTES=4_000_000
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
def norm(value):return re.sub(r'[^a-z0-9]','',value.lower())
def clean(value):return ' '.join(unescape(value).split())
def valid_url(url):
 p=urlparse(url)
 if p.hostname=='linktr.ee' and (p.path.rstrip('/') not in {'/Grlmarket','/oakandinknc','/frontpaigemedia'} or p.query):return False
 if p.hostname=='forms.monday.com' and (not re.fullmatch(r'/forms/[a-f0-9]{32}',p.path) or p.query not in ('','r=use1')):return False
 if p.hostname=='downtownraleigh.org' and (p.path.rstrip('/')!='/do/fairy-lights-bazaar' or p.query):return False
 if p.hostname=='www.cognitoforms.com' and (p.query or p.path!='/TownOfWakeForestPRCR1/_2027TownOfWakeForestParksRecreationCulturalResourcesSpecialEventFoodVendingOpportun'):return False
 if p.hostname=='managemymarket.com' and (p.path!='/VendorRegister.aspx' or p.query!='orgID=933'):return False
 if p.hostname=='www.eventbrite.com' and (p.query or not (p.path.rstrip('/')=='/o/nc-vintage-market-121068658483' or re.fullmatch(r'/e/[A-Za-z0-9-]+-[0-9]+/?',p.path))):return False
 if p.hostname=='www.artsplosure.org' and (p.path.rstrip('/') not in {'/first-night-raleigh','/artsplosuretheraleighartsfestival-1'} or p.query):return False
 if p.hostname=='www.zapplication.org' and (p.path!='/event-info.php' or not re.fullmatch(r'ID=[0-9]{1,8}',p.query)):return False
 if p.hostname=='downtowndurham.com' and (p.path.rstrip('/')!='/organizer/bull-city-treasure-hunt' or p.query):return False
 # Form IDs may vary, but the path stays scoped to a real hosted application.
 # Google Docs/Forms must not be used to fetch documents, sign-in, prefill,
 # entry values, or arbitrary query paths.
 if p.hostname=='forms.gle' and (not re.fullmatch(r'/[A-Za-z0-9_-]{6,60}',p.path) or p.query):return False
 if p.hostname=='docs.google.com' and (not re.fullmatch(r'/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform',p.path) or p.query not in ('','usp=send_form','usp=sf_link','usp=sharing','usp=header')):return False
 if p.hostname=='artspacenc.org' and p.path.rstrip('/')!='/calls-for-art':return False
 if p.hostname=='form.jotform.com' and (not re.fullmatch(r'/[0-9]{10,20}',p.path) or p.query):return False
 if p.hostname=='pci.jotform.com' and (not re.fullmatch(r'/form/[0-9]{10,20}',p.path) or p.query):return False
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
 def __init__(self,limit=90):
  self.limit=limit;self.requests=0;self.cache={};self.failures={};self.opener=build_opener(SafeRedirect())
  self.browser_enabled=os.environ.get('BTB_BROWSER_FALLBACK')=='1'
  self.browser_attempts=0;self.browser_successes=0;self.browser_failures={}
  self.browser_max_attempts=6
 def _browser_form(self,url):
  from browser_forms import public_google_form,render_public_form,BrowserUnavailable
  if (not self.browser_enabled or not public_google_form(url)
      or self.browser_attempts>=self.browser_max_attempts
      or self.requests>=self.limit):return None
  self.browser_attempts+=1
  self.requests+=1
  try:
   result=render_public_form(url)
  except BrowserUnavailable as error:
   # Only bounded, internally generated reason labels; never raw site content.
   reason=str(error)[:110]
   self.browser_failures[reason]=self.browser_failures.get(reason,0)+1
   return None
  self.browser_successes+=1
  return result
 def get(self,url):
  if not valid_url(url):raise ValueError('Untrusted URL')
  if url in self.cache:return self.cache[url]
  if url in self.failures:raise self.failures[url]
  if self.requests>=self.limit:raise ValueError('Source request budget reached')
  self.requests+=1
  time.sleep(.2)
  try:
   with self.opener.open(Request(url,headers={'User-Agent':'BehindTheBoothVerifier/1.0 (+https://www.behindtheboothhq.com/contact)'}),timeout=20) as response:
    if not valid_url(response.url):raise ValueError('Untrusted destination')
    if 'text/html' not in response.headers.get('Content-Type',''):raise ValueError('Expected an HTML source')
    raw=response.read(MAX_SOURCE_BYTES+1)
    if len(raw)>MAX_SOURCE_BYTES:raise ValueError('HTML source exceeds the 4 MB limit')
  except HTTPError as exc:
   # Do not bypass sign-in or permissions. A browser may render a publicly
   # accessible Google Form even when the static fetch receives 401/403.
   if exc.code in (401,403):
    browser_result=self._browser_form(url)
    if browser_result:
     self.cache[url]=browser_result
     return browser_result
   self.failures[url]=exc
   raise
  except (OSError,ValueError) as exc:
   self.failures[url]=exc
   raise
  html=raw.decode('utf-8',errors='replace')
  result=(Document(html),hashlib.sha256(raw).hexdigest())
  # Public Forms frequently render their questions with JavaScript. Only
  # replace a thin shell if the browser actually returns more visible text.
  if self.browser_enabled:
   from browser_forms import public_google_form
   if public_google_form(url):
    from category_rules import visible_text
    baseline=visible_text(result[0].root)
    if len(baseline)<260:
     alternative=self._browser_form(url)
     if alternative and len(visible_text(alternative[0].root))>len(baseline):
      result=alternative
  self.cache[url]=result
  return result

def source_error(error):
 # Emit diagnostic categories, never raw response bodies or arbitrary exception text.
 if isinstance(error,HTTPError):return f'HTTP {error.code}'
 if isinstance(error,(TimeoutError,URLError)):return 'Network request failed or timed out'
 if isinstance(error,ValueError) and str(error) in {'HTML source exceeds the 4 MB limit','Expected an HTML source','Source request budget reached','Untrusted URL','Untrusted destination','Redirect left trusted source hosts'}:return str(error)
 return 'Request or page parsing failed'

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

def eventeny_organizer_identity(url):
 """A stable, canonical account reference for either Eventeny profile format.

 No arbitrary external domains, fragments, credentials, query parameters,
 numeric-id lookalikes or account-root URLs are permitted.
 """
 p=urlparse(url)
 if p.scheme!='https' or p.hostname not in {'eventeny.com','www.eventeny.com'} or p.username or p.password or p.port not in (None,443) or p.fragment:return None
 if p.path.rstrip('/')=='/company':
  params=parse_qs(p.query)
  if set(params)!={'c'} or len(params['c'])!=1 or not re.fullmatch(r'[0-9]+',params['c'][0]):return None
  return ('id',params['c'][0])
 if p.query:return None
 slug=re.fullmatch(r'/company/([a-zA-Z0-9][a-zA-Z0-9_-]{1,80})/?',p.path)
 return ('slug',slug[1].lower()) if slug else None

def validate_event(doc,now,expected_organizer=None):
 events=list(doc.events())
 # Reject contradictory metadata rather than picking whichever result looks convenient.
 try:dates={(datetime.fromisoformat(e.get('startDate','')),datetime.fromisoformat(e.get('endDate','')),e.get('name')) for e in events}
 except (TypeError,ValueError):raise Uncertain('Exact dated event metadata is invalid')
 if len(dates)!=1:raise Uncertain('Exact dated event metadata is missing or contradictory')
 event=events[0]
 if any(e.get('organizer')!=event.get('organizer') or e.get('location')!=event.get('location') or e.get('eventStatus')!=event.get('eventStatus') for e in events):raise Uncertain('Event identity metadata is contradictory')
 organizer=event.get('organizer') or {}
 organizer_url=organizer.get('url','')
 if expected_organizer is None:
  if organizer_url.rstrip('/') not in {'https://www.eventeny.com/company/?c=27023','https://eventeny.com/company/?c=27023'}:raise Uncertain('Organizer identity is not the trusted MAKRS account')
  if norm(organizer.get('name',''))!='themakrssociety':raise Uncertain('Organizer name does not match MAKRS')
 else:
  if eventeny_organizer_identity(organizer_url) is None or norm(organizer.get('name',''))!=norm(expected_organizer):
   raise Uncertain('Eventeny organizer account or name does not match the approved market')
 if event.get('eventStatus')!='https://schema.org/EventScheduled':raise Uncertain('Event is cancelled, postponed, or not confirmed scheduled')
 start=datetime.fromisoformat(event['startDate']);end=datetime.fromisoformat(event['endDate'])
 if start.tzinfo is None or end.tzinfo is None or end<start:raise Uncertain('Event dates or timezone are invalid')
 if (end.date()-start.date()).days>14:raise Uncertain('Source describes a series range, not a specific dated event')
 if end<now or start>now+timedelta(days=183):raise Uncertain('Event is outside the upcoming six-month window')
 addr=event['location'].get('address',{})
 if addr.get('addressRegion') not in {'NC','North Carolina'} or addr.get('addressLocality','').lower() not in CITIES:raise Uncertain('Event location is outside the Triangle source policy')
 return event,start,end,addr


def category_research(doc,app,source_url,application_url,fetcher,now,source_hash,app_hash,series=None):
 from category_rules import research_categories, nodes_with_parents, visible_text, question_options
 supplements=[]
 # Exact known market pages, tied to the same application. No search-engine
 # snippets, unrelated vendors, photos, or event names are category evidence.
 if series:
  festival=series[0] in {'makrs-holiday-fest','moore-square-winterfaire'}
  urls=[('https://makrs.com/'+series[0],'organizer_event'),('https://makrs.com/'+('festival-applications' if festival else 'market-applications'),'organizer_criteria')]
  failures=getattr(fetcher,'category_failures',set())
  for url,kind in urls:
   if url in failures:continue
   try:
    extra,digest=fetcher.get(url)
    if not any(application_key(link)==application_key(application_url) for link in extra.root.links(url)):continue
    if kind=='organizer_event' and not any(n.tag in {'h1','h2','h3'} and norm(series[1]) in norm(visible_text(n)) for n,_ in nodes_with_parents(extra.root)):continue
    supplements.append((extra,url,digest,kind))
   except Exception:failures.add(url)
  fetcher.category_failures=failures
 receipt,conflicts=research_categories(doc,app,source_url,application_url,now,source_hash,app_hash,supplements)
 if series:
  from application_routes import research_routes
  routes,warnings=research_routes(doc,source_url,application_url,supplements,fetcher,now)
  # These facts describe the separate route, never acceptance into the main form.
  if 'Food Trucks' not in conflicts and receipt['categories'].get('Food Trucks',{}).get('status') not in {'excluded','eligible','unavailable'}:receipt['categories'].update(routes)
  receipt['warnings']=warnings
 if re.search(r'please choose your medium category|which category best fits your work',visible_text(app.root),re.I) and not question_options(app):
  receipt.setdefault('warnings',[]).append('The public application names a category question but does not expose its choices; review category coverage with the organizer.')
 return receipt,conflicts

def verify(source_url,application_url,fetcher,now=None,expected_item=None):
 """Returns verified facts or raises Uncertain. No content supplied by an AI is trusted."""
 now=now or datetime.now(timezone.utc)
 source_url=canonical_event(source_url);application_url=canonical_application(application_url)
 if not source_url or not application_url:raise Uncertain('A dated Eventeny event and vendor application are required')
 doc,source_hash=fetcher.get(source_url);event,start,end,addr=validate_event(doc,now,expected_item.get('market_organizer') if expected_item else None)
 cards=[n for n in doc.root.walk() if 'app-card' in n.attrs.get('class','').split() and any(application_key(u)==application_key(application_url) for u in n.links(source_url))]
 if len(cards)!=1:raise Uncertain('This application is not uniquely linked from the dated event')
 card=cards[0];card_text=card.text()
 buttons=[n for n in enabled_nodes(card) if n.tag in {'a','button-element'} and application_key(urljoin(source_url,n.attrs.get('href','')))==application_key(application_url) and n.text().lower() in {'apply now','join waitlist','apply to waitlist'}]
 closed=not buttons and bool(re.search(r'\b(applications? (?:are |is )?closed|application closed|no longer accepting applications)\b',card_text,re.I))
 if not buttons and not closed:raise Uncertain('No active application action for this event/date')
 # Do not merge food truck applications into the artist/vendor opportunity.
 heading=' '.join(n.text() for n in card.walk() if n.tag=='a' and application_key(urljoin(source_url,n.attrs.get('href','')))==application_key(application_url))
 if re.search(r'food trucks?',heading,re.I):raise Uncertain('Food-truck application requires a separate category-specific listing')
 app,app_hash=fetcher.get(application_url);text=app.root.text()
 from category_rules import availability_text
 status_text=availability_text(card)+' '+availability_text(app)
 status_problem=''
 app_events=list(app.events())
 if not app_events or any(norm(e.get('organizer',{}).get('name',''))!=norm(event['organizer']['name']) or eventeny_organizer_identity(e.get('organizer',{}).get('url','')) != eventeny_organizer_identity(event['organizer'].get('url','')) for e in app_events):raise Uncertain('Application organizer account does not match the event organizer')
 if any(norm(e.get('name',''))!=norm(event.get('name','')) for e in app_events):raise Uncertain('Application and dated event identities disagree')
 if re.search(r'\b(applications? (?:are |is )?closed|application closed|no longer accepting applications|not accepting applications|fully booked)\b',status_text,re.I):closed=True
 try:deadline=deadline_from(text)
 except Uncertain:
  if not closed:raise
  deadline=None
 if deadline and deadline<=now:closed=True
 if not closed and not has_start_action(app):raise Uncertain('Application has no enabled start action')
 status='closed' if closed else 'open'
 if closed:pass
 elif re.search(r'\b(waitlist only|join (?:the )?waitlist|apply to waitlist)\b',status_text,re.I):status='waitlist'
 elif re.search(r'\blimited (?:vendor )?(?:spaces|booths|availability)\b',status_text,re.I):status='limited'
 elif re.search(r'\b(sold out|fully booked|no longer accepting|applications? (?:are |is )?closed|application closed|deadline (?:has )?passed|waitlist|wait list)\b',status_text,re.I):status_problem='Unscoped closure, sold-out, or waitlist wording needs review.'
 if status=='open' and any(n.text().lower()!='apply now' for n in buttons):raise Uncertain('Application action contradicts open status')
 amounts=set(re.findall(r'\$([\d,]+(?:\.\d{1,2})?)\s+(?:vendor|booth) fee\b',card_text,re.I))
 fee=float(next(iter(amounts)).replace(',','')) if len(amounts)==1 else None
 from category_rules import application_facts
 details=application_facts(app)
 fee_conflict=fee is not None and details['standard_fee'] is not None and fee!=details['standard_fee']
 if fee is None:fee=details['standard_fee']
 if details['standard_unavailable'] or details['standard_conflict']:fee=None
 series=exact_series(event['name']) if not expected_item else None
 series_deadline=any(str(e.get('startDate',''))[:10]!=start.date().isoformat() or str(e.get('endDate',''))[:10]!=end.date().isoformat() for e in app_events)
 category_evidence,category_conflicts=category_research(doc,app,source_url,application_url,fetcher,now,source_hash,app_hash,series)
 linked=bool(expected_item and expected_item.get('market_id') and norm(expected_item.get('market_organizer',''))==norm(event['organizer']['name']) and (expected_item.get('market_city') or '').lower()==addr['addressLocality'].lower() and expected_item.get('market_state')=='NC' and expected_item.get('starts_on')==start.date().isoformat() and expected_item.get('ends_on')==end.date().isoformat())
 result = {'policy':('eventeny-organizer-v1' if expected_item else POLICY),'decision':('closed' if status=='closed' else 'publish') if series or linked else 'review','reason':'' if series or linked else 'New or unmatched market profile: confirm identity and create/link a profile.',
  'checked_at':now.isoformat(),'source_hash':source_hash,'application_hash':app_hash,'evidence':card_text[:600],
  'candidate':{'title':series[1] if series else event['name'][:160], 'market_slug':series[0] if series else (expected_item.get('market_slug') if expected_item else None),'organizer':event['organizer']['name'], 'city':addr['addressLocality'],'state':'NC',
   'venue':', '.join(filter(None,[event['location'].get('name'),addr.get('streetAddress')])), 'starts_on':start.date().isoformat(),'ends_on':end.date().isoformat(), 'deadline':deadline.isoformat() if deadline else None,
   'application_url':application_url,'source_url':source_url,'availability':status,'booth_fee':fee,'application_fee':details['application_fee'],'deposit':details['deposit'],'categories':sorted(c for c,e in category_evidence['categories'].items() if e['status']=='eligible'),
   'fee_notes':(details['fee_notes']+' ' if details['fee_notes'] else '')+("Series application deadline; confirm this event date's cutoff with the organizer. " if series_deadline else '')+'Processing fees may be additional. Other booth types have separate pricing. Confirm totals with the organizer.',
   'eligibility':(details['requirements']+' ' if details['requirements'] else '')+'The official event page lists an active application for this date. Acceptance and category availability are subject to organizer approval; remaining booth spaces are not published.'}}
 if status_problem or details['standard_unavailable'] or details['standard_conflict'] or details['overflow']:
  if result['decision']!='closed':
   result['decision']='review';result['reason']=status_problem or ('The standard vendor option is unavailable; review remaining options.' if details['standard_unavailable'] else 'Standard prices conflict or published terms exceed field limits; review the source.')
 if fee_conflict and result['decision']=='publish':
  result['decision']='review';result['reason']='Published booth prices disagree between event and application; confirm the applicable fee.'
 from research_quality import build_quality
 result['category_evidence']=category_evidence
 result['research_quality']=build_quality(result,app,details['requirements'])
 result['category_warnings']=category_evidence.get('warnings',[])
 if category_conflicts:
  result['category_conflicts']=category_conflicts
  if result['decision']=='publish':
   result['decision']='review';result['reason']='Conflicting category statements require review: '+', '.join(category_conflicts)
 return result


def discover(fetcher,now=None):
 """Discover only linked official applications; never search random pages for positive phrases."""
 applications=set();events=set();problems=[]
 for root in ROOTS:
  try:
   doc,_=fetcher.get(root)
   for link in doc.root.links(root):
    if canonical_application(link):applications.add(canonical_application(link))
    if canonical_event(link):events.add(canonical_event(link))
  except Exception as error:problems.append('Official source could not be read: '+root+' ('+source_error(error)+')')
 if not applications and not events:problems.append('Official discovery pages contained no recognized application links. Check for a source layout change.')
 for url in sorted(applications)[:25]:
  try:
   doc,_=fetcher.get(url)
   for event in doc.events():
    if canonical_event(event.get('url','')):events.add(canonical_event(event['url']))
   for link in doc.root.links(url):
    if canonical_event(link):events.add(canonical_event(link))
  except Exception as error:problems.append('Application could not be read: '+url+' ('+source_error(error)+')')
 # Follow one series-date layer to get each occurrence instead of using a series date range.
 for url in sorted(events)[:25]:
  try:
   doc,_=fetcher.get(url)
   for link in doc.root.links(url):
    if canonical_event(link):events.add(canonical_event(link))
  except Exception as error:problems.append('Dated source could not be read: '+url+' ('+source_error(error)+')')
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

# Positive UI evidence is required; an old page merely remaining online is insufficient.
def enabled_nodes(root):
 def visit(node,blocked=False):
  style=node.attrs.get('style','').replace(' ','').lower()
  blocked=blocked or 'disabled' in node.attrs or 'hidden' in node.attrs or node.attrs.get('aria-disabled')=='true' or node.attrs.get('aria-hidden')=='true' or 'display:none' in style or 'visibility:hidden' in style
  if not blocked:yield node
  for child in node.children:
   if isinstance(child,Node):yield from visit(child,blocked)
 yield from visit(root)

def has_start_action(doc):
 return any(n.tag in {'a','button','button-element'} and n.text().lower() in {'start application','join waitlist','apply to waitlist'} for n in enabled_nodes(doc.root))

ARTSPACE_SOURCE='https://artspacenc.org/calls-for-art/'
ARTSPACE_APP='https://form.jotform.com/252944311617153'
ARTSPACE_TITLE='The Mini Mall at Artspace, Holiday Edition'
ARTSPACE_NAMES={norm(ARTSPACE_TITLE),norm('Artspace Holiday Mini Mall'),norm('Artspace Holiday Mini Mall Vendors'),norm('Holiday Mini Mall'),norm('The Mini Mall at Artspace'),norm('Mini Mall at Artspace')}

def artspace_section(doc):
 nodes=[];collect=False
 for node in doc.root.walk():
  if node.tag in {'h1','h2'}:
   if collect:break
   collect=node.tag=='h2' and 'callforholidayminimallvendors' in norm(node.text())
  if collect:nodes.append(node)
 if not nodes:raise Uncertain('Current Artspace vendor-call section could not be identified')
 text=clean(' '.join(n.text() for n in nodes if n.tag in {'h2','h3','p','a','button'}))
 links=[urljoin(ARTSPACE_SOURCE,n.attrs['href']) for n in nodes if n.attrs.get('href')]
 if ARTSPACE_APP not in links:raise Uncertain('Artspace does not link this exact application in its current call')
 return text

def verify_artspace(item,fetcher,now):
 """Read only the organizer-linked form. Never submit a test application."""
 from zoneinfo import ZoneInfo
 if item.get('source_url','').rstrip('/')!=ARTSPACE_SOURCE.rstrip('/') or item.get('application_url')!=ARTSPACE_APP:
  raise Uncertain('Official source/form pair is not yet supported; verify the event-specific form manually')
 if norm(item.get('title','')) not in ARTSPACE_NAMES or item.get('starts_on')!=item.get('ends_on'):
  raise Uncertain('Artspace event title or occurrence identity needs confirmation')
 source,source_hash=fetcher.get(ARTSPACE_SOURCE);section=artspace_section(source)
 app,app_hash=fetcher.get(ARTSPACE_APP);text=app.root.text()
 if norm(ARTSPACE_TITLE) not in norm(text) or 'artspacenc.org' not in text:
  raise Uncertain('Artspace application identity could not be confirmed')
 # Exact calendar date must occur in the current call AND the form, not just its URL.
 try:
  event_date=datetime.fromisoformat(item['starts_on']).date()
 except (ValueError,KeyError):raise Uncertain('Invalid occurrence date')
 date_pattern=r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}\b'
 def dates(value):return {datetime.strptime(x,'%B %d, %Y').date() for x in re.findall(date_pattern,value)}
 if event_date not in dates(section) or event_date not in dates(text):raise Uncertain('Form and official call do not confirm this exact event date')
 today=now.astimezone(ZoneInfo('America/New_York')).date()
 if event_date<today or event_date>today+timedelta(days=183):raise Uncertain('Event is outside the upcoming six-month window')
 # Parse the deadline from the application itself; retain exact published cutoff internally.
 match=re.search(r'Application Deadline:\s*(?:[A-Za-z]+,\s*)?([A-Za-z]+\s+\d{1,2},\s+20\d{2}),?\s+(\d{1,2}:\d{2})\s*(AM|PM)',text,re.I)
 if not match:raise Uncertain('Artspace application deadline could not be confirmed')
 deadline=datetime.strptime(' '.join(match.groups()),'%B %d, %Y %I:%M %p').replace(tzinfo=ZoneInfo('America/New_York'))
 # The linked application is authoritative if its deadline differs from the overview.
 # Record that discrepancy rather than silently picking a later overview deadline.
 overview=re.search(r'Call closes:\s*(?:[A-Za-z]+,\s*)?([A-Za-z]+)\s+(\d{1,2})',section,re.I)
 note=''
 if overview:
  overview_date=datetime.strptime(f'{overview[1]} {overview[2]} {event_date.year}','%B %d %Y').date()
  if overview_date!=deadline.date():note='Organizer overview lists a different deadline; the earlier, application-form deadline is used. Confirm on the official application.'
  if overview_date<deadline.date():raise Uncertain('Organizer overview gives an earlier deadline than the form; confirm the conflict')
 combined=section+' '+text
 closed=bool(re.search(r'\b(applications? (?:are |is )?closed|no longer accepting applications|not accepting applications|fully booked|form (?:is )?(?:closed|disabled)|not accepting submissions)\b',combined,re.I)) or deadline<=now
 if closed:status='closed'
 elif re.search(r'\b(waitlist only|join (?:the )?waitlist|apply to waitlist)\b',combined,re.I):status='waitlist'
 elif re.search(r'\b(limited (?:vendor )?(?:spaces|booths|availability)|only \d+ (?:spaces|booths) (?:remain|left))\b',combined,re.I):status='limited'
 elif re.search(r'\b(sold out|waitlist|wait list)\b',combined,re.I):raise Uncertain('Category-specific closure or waitlist wording requires review')
 else:status='open'
 if not closed:
  forms=[n for n in enabled_nodes(app.root) if n.tag=='form' and n.attrs.get('action')=='https://submit.jotform.com/submit/252944311617153' and n.attrs.get('method','').lower()=='post']
  def live_form(form):
   nodes=list(enabled_nodes(form))
   return any(n.tag=='button' and n.attrs.get('type')=='submit' and n.text().lower()=='submit' for n in nodes) and any(n.tag=='input' and n.attrs.get('type')=='email' for n in nodes)
  if not any(live_form(form) for form in forms):raise Uncertain('Artspace form has no enabled submission controls; verify manually')
 slug=item.get('market_slug')
 linked=bool(item.get('market_id') and slug and norm(item.get('market_name','')) in ARTSPACE_NAMES and norm(item.get('market_organizer',''))=='artspace' and item.get('market_city','').lower()=='raleigh' and item.get('market_state')=='NC')
 from artspace_details import form_details,ConflictingTablePrices
 try:details=form_details(app)
 except ConflictingTablePrices as error:raise Uncertain(str(error))
 category_evidence,category_conflicts=category_research(source,app,ARTSPACE_SOURCE,ARTSPACE_APP,fetcher,now,source_hash,app_hash)
 result = {'policy':'artspace-jotform-v4-quality','decision':('closed' if closed else 'publish') if linked else 'review','reason':'' if linked else 'Confirm and link the Artspace market profile once before automatic updates.',
 'checked_at':now.isoformat(),'source_hash':source_hash,'application_hash':app_hash,'evidence':clean(text)[:600],
 'candidate':{'title':ARTSPACE_TITLE,'market_slug':slug,'organizer':'Artspace','city':'Raleigh','state':'NC','venue':'Artspace, 201 E Davie Street',
 'starts_on':event_date.isoformat(),'ends_on':event_date.isoformat(),'deadline':deadline.isoformat(),'application_url':ARTSPACE_APP,'source_url':ARTSPACE_SOURCE,'availability':status,
 'booth_fee':details['booth_fee'],'application_fee':0 if re.search(r'no application fee|free to apply',combined,re.I) else None,'deposit':None,'categories':sorted(c for c,e in category_evidence['categories'].items() if e['status']=='eligible'),
 'fee_notes':(details['fee_notes'] or 'Table prices are unconfirmed; check the official application.')+' '+note,
 'eligibility':(details['requirements']+' ' if details['requirements'] else '')+'The official organizer links a dated vendor form with enabled submission controls. Acceptance is juried; a working form does not guarantee acceptance or category availability. '+note}}

 from research_quality import build_quality
 result['category_evidence']=category_evidence
 result['research_quality']=build_quality(result,app,details['requirements'])
 result['category_warnings']=category_evidence.get('warnings',[])
 if category_conflicts and result['decision']=='publish':
  result['decision']='review';result['reason']='Conflicting category statements require review: '+', '.join(category_conflicts);result['category_conflicts']=category_conflicts
 return result

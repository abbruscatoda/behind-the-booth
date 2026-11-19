"""Strong-evidence public form verification for new Triangle market listings.

Only the exact, public application linked by a known organizer's dated official
event page may be published. Never submit, log in, scrape respondent data, infer
unknown cutoffs, or treat generic season-wide forms as specific event openings.
"""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
import re

from verifier import CITIES, norm, clean, valid_url
from google_forms import read_public_form
from category_rules import visible_text
from research_quality import build_quality

POLICY='triangle-form-auto-v1'
CALENDAR_POLICY='triangle-form-calendar-v2'
# These exact organizer-root/calendar combinations are independently
# allowlisted by the database. Unknown calendar hosts are research-only.
CALENDAR_ROUTES={
 ('https://www.trianglepopup.com/applications','https://www.trianglepopup.com/events'):
   'https://www.trianglepopup.com/events/',
 ('https://thenightmarketcompany.com/','https://thenightmarketcompany.com/'):
   'https://thenightmarketcompany.com/',
 ('https://www.geekandgrubmarket.com/vendorapplication','https://www.geekandgrubmarket.com/upcoming-events'):
   'https://www.geekandgrubmarket.com/event-details/',
 ('https://westernwakefarmersmarket.org/','https://westernwakefarmersmarket.org/events'):
   'https://westernwakefarmersmarket.org/events/'
}

def permitted_calendar_event(source_url,root,calendar):
 prefix=CALENDAR_ROUTES.get((root,calendar))
 if not prefix or source_url in {root,calendar}:return False
 if not source_url.startswith(prefix):return False
 if (root,calendar)==('https://thenightmarketcompany.com/','https://thenightmarketcompany.com/'):
  return bool(re.fullmatch(r'https://thenightmarketcompany[.]com/(?:events|event|markets)/[A-Za-z0-9_%/-]+',source_url))
 return bool(re.fullmatch(re.escape(prefix)+r'[A-Za-z0-9_%/-]+',source_url))

def calendar_provenance(source_url):
 for root,calendar in CALENDAR_ROUTES:
  if permitted_calendar_event(source_url,root,calendar):
   return root,calendar
 return None

DATE_FMT='%B %d, %Y'
CUTOFF=re.compile(
 r'\b(?:Application|Vendor)\s+deadline\s*[:\-–]?\s*'
 r'(January|February|March|April|May|June|July|August|September|October|November|December)'
 r'\s+(\d{1,2}),?\s+(20\d{2})\s*(?:at|by)?\s*(\d{1,2}:\d{2})\s*(AM|PM)'
 r'\s*(ET|EST|EDT)\b',re.I)

def supported_form(url):
 if not valid_url(url):return False
 p=urlparse(url)
 return p.hostname in {'docs.google.com','forms.gle','form.jotform.com','pci.jotform.com'}

def verify_public_form(lead,fetcher,now=None):
 """Return a fully checked publish candidate or None when evidence is incomplete."""
 from discovery import SOURCES
 now=now or datetime.now(timezone.utc)
 source_url=lead.get('source_url','')
 curated_root=lead.get('curated_source_url') or source_url
 linking_page=lead.get('linking_page_url') or curated_root
 app_url=lead.get('target_url') or lead.get('application_url','')
 if not supported_form(app_url):return None
 from_calendar=source_url!=curated_root
 if from_calendar:
  if not permitted_calendar_event(source_url,curated_root,linking_page):return None
 organizer_label=next((organizer for organizer,_,url in SOURCES if url==curated_root),None)
 if not organizer_label:return None
 # An organizer's date-specific event page must be reached from an approved
 # official root, optionally via one same-host calendar/application index.
 # Re-check the actual links; a supplied URL or domain match alone is not proof.
 try:
  if source_url!=curated_root:
   root_doc,root_hash=fetcher.get(curated_root)
   from verifier import valid_url
   if not valid_url(source_url):return None
   if urlparse(source_url).hostname!=urlparse(curated_root).hostname:return None
   if linking_page!=curated_root:
    if not valid_url(linking_page) or urlparse(linking_page).hostname!=urlparse(curated_root).hostname:return None
    if linking_page not in root_doc.root.links(curated_root):return None
    link_doc,_=fetcher.get(linking_page)
    if source_url not in link_doc.root.links(linking_page):return None
   elif source_url not in root_doc.root.links(curated_root):return None
  source,source_hash=fetcher.get(source_url)
  if app_url not in source.root.links(source_url):return None
  events=list(source.events())
  if len(events)!=1:return None
  event=events[0]
  if event.get('eventStatus')!='https://schema.org/EventScheduled':return None
  name=clean(event.get('name',''))
  if len(name)<10 or len(name)>160:return None
  organizer=event.get('organizer') or {}
  if not isinstance(organizer,dict):return None
  organizer_name=clean(organizer.get('name',''))
  if not organizer_name or norm(organizer_name)!=norm(organizer_label):return None
  loc=event.get('location') or {}
  if not isinstance(loc,dict):return None
  addr=loc.get('address') or {}
  if not isinstance(addr,dict):return None
  city=clean(addr.get('addressLocality',''))
  if city.lower() not in CITIES or addr.get('addressRegion') not in ('NC','North Carolina'):return None
  starts=datetime.fromisoformat(event.get('startDate',''))
  ends=datetime.fromisoformat(event.get('endDate',''))
  if starts.tzinfo is None or ends.tzinfo is None:return None
  today=now.astimezone(ZoneInfo('America/New_York')).date()
  if not today<=starts.date()<=today+timedelta(days=183):return None
  if ends.date()<starts.date() or ends.date()>starts.date()+timedelta(days=14):return None
  # A generic application for multiple events cannot safely be labeled open
  # for one occurrence without explicit, matching form-level date evidence.
  if starts.date()!=ends.date():return None

  form,app_hash=fetcher.get(app_url)
  facts=read_public_form(form)
  if facts['closed'] or not facts['complete'] or facts.get('issues'):return None
  text=visible_text(form.root)
  if norm(name) not in norm(text):return None
  formatted=f'{starts.date():%B} {starts.day}, {starts.year}'
  if formatted.lower() not in text.lower():return None
  if not re.search(r'\b(?:artist|vendor|exhibitor|merchant)\s+application\b',text,re.I):return None
  # Reject page-wide closure. Partial category availability must not be
  # presented as a universally open application.
  if re.search(r'\b(?:no longer accepting|applications? closed|fully booked|sold out)\b',
               visible_text(source.root)+' '+text,re.I):return None
  cutoffs=set()
  for match in CUTOFF.finditer(text):
   month,day,year,clock,ampm,zone=match.groups()
   try:
    deadline=datetime.strptime(f'{month} {day}, {year} {clock} {ampm.upper()}',
      '%B %d, %Y %I:%M %p').replace(tzinfo=ZoneInfo('America/New_York'))
    if deadline.tzname().upper()!=zone.upper() and zone.upper()!='ET':return None
    cutoffs.add(deadline.isoformat())
   except ValueError:return None
  if len(cutoffs)!=1:return None
  deadline=datetime.fromisoformat(next(iter(cutoffs)))
  if deadline<=now or deadline.date()>starts.date():return None

  venue=clean(', '.join(x for x in (loc.get('name',''),addr.get('streetAddress','')) if x))
  if len(venue)>300:return None
  candidate={'title':name,'market_slug':None,'organizer':organizer_name,
   'city':city,'state':'NC','venue':venue,
   'starts_on':starts.date().isoformat(),'ends_on':ends.date().isoformat(),
   'deadline':deadline.isoformat(),'application_url':app_url,'source_url':source_url,
   'availability':'open','booth_fee':facts.get('booth_fee'),
   'application_fee':facts.get('application_fee'),'deposit':facts.get('deposit'),
   'categories':[],'organizer_source_url':curated_root,'fee_notes':facts.get('fee_notes') or '',
   'eligibility':facts.get('eligibility') or ''}
  receipt={'application_url':app_url,'checked_at':now.isoformat(),'categories':{}}
  result={'policy':CALENDAR_POLICY if from_calendar else POLICY,
   'organizer_root':curated_root,'calendar_url':linking_page,
   'decision':'publish','form_complete':True,'form_readable':True,
   'reason':'Official dated organizer page and public vendor form independently match; enabled submission and exact future deadline verified.',
   'checked_at':now.isoformat(),'source_hash':source_hash,
   'application_hash':app_hash,'organizer_source_url':curated_root,
   'evidence':'Official dated event page links the exact public form. Event, organizer, application date, and live submission controls agree.',
   'candidate':candidate,'category_evidence':receipt}
  result['research_quality']=build_quality(result,form,candidate['eligibility'])
  return result
 except (ValueError,KeyError,TypeError,AttributeError):
  # Insufficient or contradictory public evidence is not authority to publish.
  return None

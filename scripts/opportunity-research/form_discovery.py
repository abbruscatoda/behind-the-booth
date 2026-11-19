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
EVENT_DATE=re.compile(
 r'\b(January|February|March|April|May|June|July|August|September|October|November|December)'
 r'\s+([0-3]?\d),?\s+(20\d{2})\b',re.I)

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
 app_url=lead.get('target_url') or lead.get('application_url','')
 if not supported_form(app_url):return None
 organizer_root=lead.get('organizer_root') or source_url
 calendar_url=lead.get('calendar_url')
 if calendar_url:
  from calendar_research import CALENDARS
  if lead.get('grouped_research'):
   # Curated organizer roots, never incoming arbitrary websites.
   organizer_label=next((organizer for organizer,_,root in SOURCES
      if root==organizer_root and calendar_url==organizer_root),None)
  else:
   organizer_label=next((organizer for organizer,root,calendar in CALENDARS
      if root==organizer_root and calendar==calendar_url),None)
  if not organizer_label or not valid_url(source_url):return None
  if urlparse(source_url).hostname!=urlparse(calendar_url).hostname:return None
 else:
  organizer_label=next((organizer for organizer,_,url in SOURCES if url==source_url),None)
 if not organizer_label:return None
 try:
  if calendar_url:
   from calendar_research import calendar_event_provenance,calendar_event_pages,same_organizer_host
   root_doc,_=fetcher.get(organizer_root)
   if lead.get('grouped_research'):
    event_index=lead.get('event_index_url')
    if event_index==organizer_root:
     if source_url not in calendar_event_pages(root_doc,organizer_root):return None
    else:
     if not same_organizer_host(event_index or '',organizer_root):return None
     if event_index not in root_doc.root.links(organizer_root):return None
     index_doc,_=fetcher.get(event_index)
     if source_url not in calendar_event_pages(index_doc,event_index):return None
   elif not calendar_event_provenance(fetcher,calendar_url,source_url):return None
  source,source_hash=fetcher.get(source_url)
  from calendar_research import calendar_form_links
  if app_url not in calendar_form_links(source,source_url):
   # The application must be linked by the official organizer directly or
   # via a currently linked same-host application page, not just discovered
   # somewhere on the internet.
   if not calendar_url:return None
   if lead.get('grouped_research'):
    app_index=lead.get('application_index_url')
    if app_index==organizer_root:
     if app_url not in calendar_form_links(root_doc,organizer_root):return None
    else:
     if not same_organizer_host(app_index or '',organizer_root):return None
     if app_index not in root_doc.root.links(organizer_root):return None
     app_index_doc,_=fetcher.get(app_index)
     if app_url not in calendar_form_links(app_index_doc,app_index):return None
   elif app_url not in root_doc.root.links(organizer_root):return None
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
  if calendar_url:
   # A currently reachable legacy form does not override a source-wide,
   # explicit closure of the organizer's applications for this event year.
   root_text=visible_text(root_doc.root)
   closed_years={int(y) for y in re.findall(
     r'\b(?:all\s+)?(20\d{2})\s+(?:vendor\s+)?applications\s+(?:have\s+)?closed\b',
     root_text,re.I)}
   if starts.year in closed_years:return None

  form,app_hash=fetcher.get(app_url)
  facts=read_public_form(form)
  if facts['closed'] or not facts['complete'] or facts.get('issues'):return None
  text=visible_text(form.root)
  if norm(name) not in norm(text):return None
  formatted=f'{starts.date():%B} {starts.day}, {starts.year}'
  if formatted.lower() not in text.lower():return None
  # Multiple distinct event dates indicate a seasonal or multi-event
  # application. Merely mentioning the target date cannot certify that
  # its individual category/application is available.
  dates=set()
  for month,day,year in EVENT_DATE.findall(text):
   try:
    dates.add(datetime.strptime(f'{month} {int(day)} {year}','%B %d %Y').date())
   except ValueError:return None
  if len(dates)>2 or (len(dates)==2 and starts.date() not in dates):return None
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
  if dates-{deadline.date()}!={starts.date()}:return None

  venue=clean(', '.join(x for x in (loc.get('name',''),addr.get('streetAddress','')) if x))
  if len(venue)>300:return None
  candidate={'title':name,'market_slug':None,'organizer':organizer_name,
   'city':city,'state':'NC','venue':venue,
   'starts_on':starts.date().isoformat(),'ends_on':ends.date().isoformat(),
   'deadline':deadline.isoformat(),'application_url':app_url,'source_url':source_url,
   'availability':'open','booth_fee':facts.get('booth_fee'),
   'application_fee':facts.get('application_fee'),'deposit':facts.get('deposit'),
   'categories':[],'fee_notes':facts.get('fee_notes') or '',
   'eligibility':facts.get('eligibility') or ''}
  receipt={'application_url':app_url,'checked_at':now.isoformat(),'categories':{}}
  result={'policy':CALENDAR_POLICY if calendar_url else POLICY,
   'decision':'publish','form_complete':True,'form_readable':True,
   'reason':'Official dated organizer page and public vendor form independently match; enabled submission and exact future deadline verified.',
   'checked_at':now.isoformat(),'source_hash':source_hash,
   'application_hash':app_hash,
   'evidence':'Official dated event page links the exact public form. Event, organizer, application date, and live submission controls agree.',
   'candidate':candidate,'category_evidence':receipt}
  if calendar_url:
   result['organizer_root']=organizer_root
   result['calendar_url']=calendar_url
   if lead.get('grouped_research'):
    result['grouped_research']=True
    result['event_index_url']=lead.get('event_index_url')
    result['application_index_url']=lead.get('application_index_url')
  result['research_quality']=build_quality(result,form,candidate['eligibility'])
  return result
 except (ValueError,KeyError,TypeError,AttributeError):
  # Insufficient or contradictory public evidence is not authority to publish.
  return None

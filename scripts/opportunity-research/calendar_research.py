"""Bounded exploration of official Triangle event calendars.

Calendars identify dated event pages, never prove that vendors can apply.
Candidate applications go through the existing event/form verification gates.
Only curated organizer hosts and configured calendar paths are fetched.
"""
from datetime import datetime,timezone
import re
from urllib.parse import urljoin,urlparse,urlunparse,parse_qsl
from verifier import valid_url,canonical_event,canonical_application
from form_discovery import supported_form

# Each calendar belongs to an existing, explicitly curated organizer source.
CALENDARS=(
 ('Hartwell','https://www.hartwellraleigh.com/retail-markets','https://www.hartwellraleigh.com/monthlyeventcalendar'),
 ('North Hills','https://www.visitnorthhills.com/signature-events/midtown-makers-market','https://www.visitnorthhills.com/events'),
 ('Grasshopper Farms','https://www.grasshopperfarmsnc.com/special-events','https://www.grasshopperfarmsnc.com/makers-markets'),
 ('Unhinged Coffee & Co.','https://www.unhingedcoffee.co/','https://www.unhingedcoffee.co/'),
 ('NC Vintage Market','https://www.eventbrite.com/o/nc-vintage-market-121068658483','https://www.eventbrite.com/o/nc-vintage-market-121068658483'),
 ('Haven Farm','https://www.havenofknightdale.com/work-with-haven','https://www.havenofknightdale.com/community-events'),
 ('NC Vintage Bazaar','https://ncvintagebazaar.com/vendor-booths/','https://ncvintagebazaar.com/'),
 ('The Patchwork Market','https://thepatchworkmarket.com/applytobeavendor/','https://thepatchworkmarket.com/'),
 ('Rebus Works','https://www.rebusworks.us/sundayfundaymarket','https://www.rebusworks.us/calendar'),
 ('Raleigh Retro Gamers','https://raleighretrogamers.com/vendors/','https://raleighretrogamers.com/events/'),
 ('Durham Parks & Recreation','https://www.dprplaymore.org/331/Vendor-Performer-Information','https://www.dprplaymore.org/274/Special-Events'),
 ('Durham Central Park','https://durhamcentralpark.org/events/','https://durhamcentralpark.org/events/'),
 ('Triangle Pop-Up','https://www.trianglepopup.com/applications','https://www.trianglepopup.com/events'),
 ('Pop-Up Raleigh','https://popupraleigh.com/9-2/','https://popupraleigh.com/home/'),
 ('City of Raleigh','https://raleighnc.gov/events','https://raleighnc.gov/events'),
 ('Town of Cary','https://www.carync.gov/recreation-enjoyment/events','https://www.carync.gov/recreation-enjoyment/events'),
 ('Town of Apex','https://www.apexnc.org/428/Special-Events-Festivals','https://www.apexnc.org/428/Special-Events-Festivals'),
 ('Chapel Hill Community Arts & Culture','https://www.chapelhillarts.org/applications/','https://www.chapelhillarts.org/calendar/'),
 ('The Night Market Company','https://thenightmarketcompany.com/','https://thenightmarketcompany.com/'),
 ('Geek and Grub','https://www.geekandgrubmarket.com/vendorapplication','https://www.geekandgrubmarket.com/upcoming-events'),
 ('Western Wake Farmers Market','https://westernwakefarmersmarket.org/','https://westernwakefarmersmarket.org/events'),
 ('Shop Local Raleigh','https://shoplocalraleigh.org/vendor-information/','https://shoplocalraleigh.org/events/'),
 ('Chapel Hill Farmers Market','https://www.thechapelhillfarmersmarket.com/','https://www.thechapelhillfarmersmarket.com/events.html'),
)
MAX_CALENDAR_EVENT_PAGES=8*len(CALENDARS)
MAX_EVENTS_PER_CALENDAR=8
MAX_FORMS_PER_CALENDAR=6
MAX_INDEXES_PER_CALENDAR=3
MAX_CALENDAR_FORMS=80
MAX_CALENDAR_INDEX_PAGES=18

def same_organizer_host(url,calendar):
 a=urlparse(url);b=urlparse(calendar)
 return bool(valid_url(url) and a.hostname==b.hostname and
   a.path not in ('/','') and a.path!=b.path and not a.query and
   not a.path.lower().endswith(('.pdf','.jpg','.png','.css','.js')))

def calendar_event_pages(doc,base):
 """Follow only event-oriented internal links or explicit Eventeny events."""
 result=set()
 for node in doc.root.walk():
  if node.tag!='a' or not node.attrs.get('href'):continue
  url=urljoin(base,node.attrs['href'])
  event=canonical_event(url)
  if event:
   result.add(event)
   continue
  p=urlparse(url)
  label=node.text().lower()
  if p.hostname=='www.eventbrite.com' and same_organizer_host(url,base) and p.path.startswith('/e/'):
   result.add(url);continue
  if same_organizer_host(url,base) and any(tag in p.path.lower() for tag in
      ('/events/','/event-details/','/calendar/','/markets/','/market/','/event/','/upcoming/','/news/')) or (same_organizer_host(url,base) and any(tag in label for tag in ('market','festival','craft fair','vendor'))):
   result.add(url)
 return result

def calendar_index_pages(doc,base):
 """Bounded same-host calendar indexes, not arbitrary external links."""
 result=set()
 for link in doc.root.links(base):
  url=urljoin(base,link)
  if not same_organizer_host(url,base):continue
  path=urlparse(url).path.lower()
  if any(tag in path for tag in ('/calendar','/upcoming','/events','/markets','/schedule')):
   result.add(url)
 return result

def calendar_event_provenance(fetcher,calendar_url,event_url):
 """Require a live calendar -> detail or calendar -> index -> detail path."""
 calendar,_=fetcher.get(calendar_url)
 if event_url in calendar_event_pages(calendar,calendar_url):return True
 for index_url in sorted(calendar_index_pages(calendar,calendar_url))[:MAX_CALENDAR_INDEX_PAGES]:
  if index_url==event_url:continue
  try:
   index,_=fetcher.get(index_url)
   if event_url in calendar_event_pages(index,index_url):return True
  except Exception:continue
 return False

def embedded_form_url(value,base):
 """Normalize only public, unprefilled iframe URLs (not arbitrary embeds)."""
 try:
  url=urljoin(base,value)
  p=urlparse(url)
  if p.query:
   if parse_qsl(p.query,keep_blank_values=True)!=[('embedded','true')]:
    return None
   url=urlunparse(p._replace(query=''))
  return url if supported_form(url) else None
 except (ValueError,TypeError):
  return None

def calendar_form_links(doc,base):
 """Collect linked or explicitly embedded public forms from official pages."""
 links=set()
 for link in doc.root.links(base):
  url=urljoin(base,link)
  if supported_form(url) or canonical_application(url):
   links.add(canonical_application(url) or url)
 for node in doc.root.walk():
  if node.tag!='iframe' or not node.attrs.get('src'):continue
  form=embedded_form_url(node.attrs['src'],base)
  if form:links.add(form)
 return links

def discover_calendars(fetcher,now=None):
 """Return (Eventeny URLs, form event-source leads, diagnostics).

 Each form lead carries a verified provenance path:
 organizer_root -> curated calendar -> dated event page -> exact form.
 No event or form is considered open here.
 """
 from regional_search import rotate
 from discovery import SOURCES
 trusted={url:(name,city) for name,city,url in SOURCES}
 now=now or datetime.now(timezone.utc)
 event_hints={}
 deferred=0
 eventeny=set()
 form_leads={}
 failures=[]
 visited=set()
 inspected=0
 indexes_inspected=0
 for organizer,root,calendar in rotate(CALENDARS,now,len(CALENDARS)):
  if not valid_url(calendar) or not valid_url(root):
   failures.append(organizer+': untrusted source configuration')
   continue
  try:
   cal,_=fetcher.get(calendar)
   root_doc,_=fetcher.get(root)
   # Root-level applications may cover an explicitly identified date, but
   # the subsequent verifier must prove that exact date in the actual form.
   organizer_forms=calendar_form_links(root_doc,root)
   event_urls=set(calendar_event_pages(cal,calendar))
   # A current organizer index may lead to individual dated market pages.
   for index_url in rotate(sorted(calendar_index_pages(cal,calendar)),now,MAX_INDEXES_PER_CALENDAR):
    try:
     index_doc,_=fetcher.get(index_url)
     indexes_inspected+=1
     event_urls.update(calendar_event_pages(index_doc,index_url))
    except Exception:continue
   selected=rotate(sorted(event_urls),now,MAX_EVENTS_PER_CALENDAR)
   deferred+=max(0,len(event_urls)-len(selected))
   local_forms=0
   for event_url in selected:
    if len(visited)>=MAX_CALENDAR_EVENT_PAGES:break
    if event_url in visited:continue
    if getattr(fetcher,'requests',0)>=getattr(fetcher,'limit',100000)-100:
     deferred+=1;continue
    visited.add(event_url)
    if canonical_event(event_url):
     eventeny.add(canonical_event(event_url))
     continue
    if not same_organizer_host(event_url,calendar):continue
    try:
     event_page,_=fetcher.get(event_url)
     inspected+=1
     title=next((n.text().strip()[:160] for n in event_page.root.walk() if n.tag=='h1'), '')
     if root in trusted and re.search(r'\b(?:market|vendors?|festival|craft fair)\b',title,re.I):
      owner,city=trusted[root]
      event_hints[event_url]={'target_url':event_url,'source_url':root,
       'title':title or 'Official market/event lead','organizer':owner,'city':city,
       'notes':'Found on the official event calendar. This event is not a confirmed open vendor application.'}
     for deep in calendar_event_pages(event_page,event_url):
      if canonical_event(deep):eventeny.add(canonical_event(deep))
     # Form URL may be linked either on the event page or organizer's
     # official application page, but organizer identity and date must be
     # independently confirmed by the later public-form verifier.
     for app in calendar_form_links(event_page,event_url)|organizer_forms:
      if len(form_leads)>=MAX_CALENDAR_FORMS or local_forms>=MAX_FORMS_PER_CALENDAR:break
      if supported_form(app):
       key=(event_url,app)
       if key not in form_leads:local_forms+=1
       form_leads[key]={
        'source_url':event_url,'target_url':app,
        'organizer_root':root,'calendar_url':calendar,
        'organizer':organizer}
    except Exception:
     continue
  except Exception:
   failures.append(organizer+': calendar temporarily unavailable')
 return eventeny,list(form_leads.values()),{
  'calendar_sources':len(CALENDARS),'calendar_events_deferred':deferred,'_event_leads':list(event_hints.values()),
  'calendar_event_pages_inspected':inspected,
  'calendar_indexes_inspected':indexes_inspected,
  'calendar_eventeny_urls':len(eventeny),
  'calendar_form_pairs':len(form_leads),
  'calendar_source_failures':failures[:8],
 }

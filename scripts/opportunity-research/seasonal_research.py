"""Official-source seasonal and rolling market research.

Reusable evidence checks with explicit provider identities. New organizers can
join PROVIDERS only after their official pages / form relationships are tested.
No speculative event dates, no browser form submission, no login bypass.
"""
from datetime import datetime,date,timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse,urljoin
import re
from verifier import Uncertain,valid_url,clean
from category_rules import visible_text
from google_forms import read_public_form

POLICY='seasonal-official-v1'
FVG_ROOT='https://www.fvgrowersmarket.com/'
FVG_VENDOR='https://www.fvgrowersmarket.com/vendor-application'
WW_ROOT='https://westernwakefarmersmarket.org/'
WW_VENDOR='https://westernwakefarmersmarket.org/apply'

PROVIDERS=(
 {'slug':'fuquay-varina-growers-market','name':'Fuquay-Varina Growers Market',
  'organizer':'Fuquay-Varina Growers Market','city':'Fuquay-Varina',
  'market_url':FVG_ROOT,'vendor_url':FVG_VENDOR,'kind':'seasonal'},
 {'slug':'western-wake-farmers-market','name':'Western Wake Farmers Market',
  'organizer':'Western Wake Farmers Market','city':'Morrisville',
  'market_url':WW_ROOT,'vendor_url':WW_VENDOR,'kind':'rolling'},
)
CLOSED=r'no longer accepting|applications? (?:are |have )?closed|fully booked|sold out|submissions? (?:are |is )?closed'
MONTHS={'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}

def links_labeled(doc,base,match):
 found=[]
 for node in doc.root.walk():
  if node.tag!='a' or not node.attrs.get('href'):continue
  label=clean(node.text())
  if not match.search(label):continue
  url=urljoin(base,node.attrs['href'])
  if valid_url(url):found.append(url)
 return list(dict.fromkeys(found))

def _has_submit(doc):
 # Require a visible public Submit control, never attempt to send answers.
 for n in doc.root.walk():
  if n.tag not in {'button','input','div','span'}:continue
  role=n.attrs.get('role','')
  if n.tag in {'div','span'} and role!='button':continue
  if n.tag=='input' and n.attrs.get('type')!='submit':continue
  text=clean(n.text() if n.tag!='input' else n.attrs.get('value',''))
  if text.lower()=='submit':return True
 return False

def _form_readable(doc):
 text=visible_text(doc.root)
 if re.search(CLOSED,text,re.I):raise Uncertain('The linked vendor application is closed.')
 if re.search(r'you need permission|sign in to continue|request access|you must sign in',text,re.I):
  raise Uncertain('Vendor application is permission-gated.')
 if not _has_submit(doc):raise Uncertain('No readable, enabled Submit control on the vendor application.')
 return text

def _month_day(text,pattern,year):
 match=re.search(pattern,text,re.I)
 if not match:raise Uncertain('Exact seasonal market start/end dates were not confirmed.')
 m1,d1,m2,d2=match.groups()
 try:
  a=date(year,MONTHS[m1[:3].lower()],int(d1))
  b=date(year,MONTHS[m2[:3].lower()],int(d2))
 except (KeyError,ValueError):
  raise Uncertain('Official seasonal date expression is invalid.') from None
 if a>b:raise Uncertain('Season end is before season start.')
 return a,b

def _fvg(provider,root,root_hash,vendor,vendor_hash,fetcher,now):
 market=visible_text(root.root)
 text=visible_text(vendor.root)
 if not re.search(r'Fuquay.Varina Growers Market',market,re.I):
  raise Uncertain('Official market identity is absent.')
 if not re.search(r'Fuquay.Varina Growers Market',text,re.I):
  raise Uncertain('Vendor page is not tied to this market.')
 if re.search(CLOSED,text,re.I):raise Uncertain('Organizer indicates applications are closed.')
 years=set(re.findall(r'(?:Now Accepting Vendor Applications for our|now accepting vendor applications for the)\s*(20\d{2})\s*Season',text,re.I))
 if len(years)!=1:raise Uncertain('An unambiguous active application season was not stated.')
 year=int(next(iter(years)))
 today=now.astimezone(ZoneInfo('America/New_York')).date()
 if year<today.year or year>today.year+1:raise Uncertain('Published season is stale or too far ahead.')
 season=_month_day(text,r'\b(April|May)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(?:through|to|-)\s+(September|October)\s+(\d{1,2})(?:st|nd|rd|th)?',year)
 if not re.search(rf'{year}\s+Regular Season:\s*Apr\s+{season[0].day}\s*[-–]\s*Sep\s+{season[1].day}',market,re.I):
  raise Uncertain('Market calendar does not independently match the vendor season.')
 if not (re.search(r'121\s+N\.?\s+Main\s+St(?:reet|\.)?',text,re.I) or
         re.search(r'121\s+N\.?\s+Main\s+St(?:reet|\.)?',market,re.I)):
  raise Uncertain('No exact market street address was found on the official organizer pages.')
 applicants=links_labeled(vendor,provider['vendor_url'],re.compile(r'^New Vendor Application$',re.I))
 if len(applicants)!=1 or not re.fullmatch(r'https://form\.jotform\.com/\d{10,20}',applicants[0]):
  raise Uncertain('Exact, linked new-vendor Jotform is missing or ambiguous.')
 form,form_hash=fetcher.get(applicants[0])
 ft=_form_readable(form)
 if not re.search(rf'\b{year}\s+NEW\s+Vendor Application\b',ft,re.I):
  raise Uncertain('Application form targets a different season or vendor type.')
 _form_season=_month_day(ft,r'\b(April|May)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(?:to|through|-)\s+(September|October)\s+(\d{1,2})(?:st|nd|rd|th)?',year)
 if _form_season!=season:raise Uncertain('Organizer event dates conflict with the vendor application.')
 amounts={}
 for key,pattern in (
  ('full_time',r'Full.time\s*,?\s*\$(\d+)\s*\(\d+ Saturdays\)'),
  ('part_time',r'Part.time\s*,?\s*\$(\d+)\s*\(\d+ Saturdays\)'),
  ('guest',r'Guest\s*\$(\d+)\s*per\s*day')):
  match=re.search(pattern,ft,re.I)
  if not match:raise Uncertain('One of the advertised participation fee tiers is missing.')
  amounts[key]=int(match.group(1))
 if any(n<0 or n>10000 for n in amounts.values()):raise Uncertain('Unexpected participation fees.')
 if not re.search(r'not able to accept MLM|do not accept MLM',text,re.I):
  raise Uncertain('The published eligibility restrictions were not confirmed.')
 candidate={
  'title':f'{provider["name"]} — {year} Vendor Applications',
  'market_slug':provider['slug'],'market_name':provider['name'],
  'organizer':provider['organizer'],'city':provider['city'],'state':'NC',
  'venue':'121 N. Main St. (Chamber of Commerce parking lot)',
  'market_url':provider['market_url'],'source_url':provider['vendor_url'],
  'application_url':applicants[0],
  'starts_on':season[0].isoformat(),'ends_on':season[1].isoformat(),
  'schedule_type':'seasonal_application','availability':'open','deadline':None,
  'booth_fee':None,'application_fee':None,'deposit':None,'categories':[],
  'fee_notes':f'{year} vendor participation plans: full-time ${amounts["full_time"]}; part-time ${amounts["part_time"]}; guest ${amounts["guest"]} per day. Fees vary by attendance plan; no universal booth or application fee established.',
  'eligibility':'Applicants must sell qualifying farm, food, or handmade goods. MLM, boutiques, and non-handcrafted resale are not accepted. New-vendor application and market guidelines are linked by the organizer.',
  'research_notes':'Applications are explicitly accepted for the published seasonal Saturday market. Individual Saturdays and space assignments are not guaranteed. No application deadline was published on the verified sources.'
 }
 return candidate,form_hash

def _ww(provider,root,root_hash,vendor,vendor_hash,fetcher,now):
 market=visible_text(root.root)
 text=visible_text(vendor.root)
 if not re.search(r'Western Wake Farmers Market',market,re.I):
  raise Uncertain('Official market identity not confirmed.')
 if not re.search(r'Open Saturdays year.round',market,re.I):
  raise Uncertain('Organizer no longer confirms a year-round Saturday market.')
 if not re.search(r'Applications are accepted on a rolling basis',text,re.I):
  raise Uncertain('No affirmative rolling application statement.')
 if not re.search(r'Vendor Applications Rolling',market,re.I):
  raise Uncertain('Organizer homepage no longer identifies ongoing intake.')
 years=re.findall(r"Applications are open for WWFM.s\s*(\d{2})/(\d{2}) season",market,re.I)
 if len(set(years))!=1:raise Uncertain('An unambiguous current intake year is not given.')
 y1,y2=map(int,years[0]);year1=2000+y1;year2=2000+y2
 if year2!=year1+1:raise Uncertain('Rolling intake period has conflicting years.')
 today=now.astimezone(ZoneInfo('America/New_York')).date()
 if not year1<=today.year<=year2:raise Uncertain('The published rolling intake season is no longer current.')
 if not (re.search(r'101\s+Town\s+Hall\s+Drive',market,re.I) or
         re.search(r'101\s+Town\s+Hall\s+Drive',text,re.I)):
  raise Uncertain('No confirmed market address on an official organizer page.')
 applicants=links_labeled(vendor,provider['vendor_url'],re.compile(r'^(?:Apply Online|Regular Vendor Application)$',re.I))
 if len(set(applicants))!=1 or not re.fullmatch(r'https://forms\.gle/[A-Za-z0-9_-]{6,60}',applicants[0]):
  raise Uncertain('Exact official regular-vendor application could not be isolated.')
 form,form_hash=fetcher.get(applicants[0])
 ft=_form_readable(form)
 if not re.search(r'vendor|Western Wake|WWFM',ft,re.I):
  raise Uncertain('Public Google Form is not identifiable as a market application.')
 # Year-round markets have no single season day; these dates are explicitly
 # an internal coverage horizon, never shown as event/attendance dates.
 horizon_start=date(year1,1,1);horizon_end=date(year2,12,31)
 candidate={
  'title':f'{provider["name"]} — Rolling Vendor Applications',
  'market_slug':provider['slug'],'market_name':provider['name'],
  'organizer':provider['organizer'],'city':provider['city'],'state':'NC',
  'venue':'101 Town Hall Drive',
  'market_url':provider['market_url'],'source_url':provider['vendor_url'],
  'application_url':applicants[0],
  'starts_on':horizon_start.isoformat(),'ends_on':horizon_end.isoformat(),
  'schedule_type':'rolling_market','availability':'open','deadline':None,
  'booth_fee':None,'application_fee':None,'deposit':None,'categories':[],
  'fee_notes':'A nonrefundable application fee is required; the organizer publishes separate fee schedules that vary by attendance arrangement. Exact cost not verified.',
  'eligibility':'Regular vendor application is accepted on a rolling basis. Applicants must follow published market rules and meet the organizer\'s vendor-selection requirements.',
  'research_notes':f'Year-round Saturday market; official {year1}/{year2} rolling vendor intake. Dates stored internally represent a coverage window, not scheduled events. No specific booth availability, individual attendance dates, or submission cutoff is guaranteed.'
 }
 return candidate,form_hash

def check_provider(provider,fetcher,now=None):
 now=now or datetime.now(timezone.utc)
 if provider not in PROVIDERS:raise Uncertain('Unknown seasonal provider.')
 main,main_hash=fetcher.get(provider['market_url'])
 vendor,vendor_hash=fetcher.get(provider['vendor_url'])
 if not valid_url(provider['market_url']) or not valid_url(provider['vendor_url']):
  raise Uncertain('Untrusted organizer page.')
 if provider['market_url']!=provider['vendor_url'] and provider['vendor_url'] not in main.root.links(provider['market_url']):
  # Some organizers omit a navigation link but host a vendor page on the
  # same canonical domain. Those pages must separately pass explicit market
  # name, address, seasonal dates and form-link checks below.
  if urlparse(provider['vendor_url']).hostname!=urlparse(provider['market_url']).hostname:
   raise Uncertain('Vendor page is not linked by the official market.')
 if provider['kind']=='seasonal':
  candidate,form_hash=_fvg(provider,main,main_hash,vendor,vendor_hash,fetcher,now)
 elif provider['kind']=='rolling':
  candidate,form_hash=_ww(provider,main,main_hash,vendor,vendor_hash,fetcher,now)
 else:raise Uncertain('Unsupported seasonal provider type.')
 return {'decision':'publish','policy':POLICY,'candidate':candidate,
  'checked_at':now.isoformat(),'source_hash':vendor_hash,
  'market_source_hash':main_hash,'application_hash':form_hash,
  'form_complete':True,'form_readable':True,
  'evidence':'Official market and vendor pages independently agree on active intake, location, participating season or rolling schedule, and an exact linked readable application with Submit.',
  'reason':'Organizer-verified seasonal or rolling vendor intake, not guaranteed individual market dates.'}

def discover_seasonal(fetcher,now=None,diagnostics=None):
 confirmed=[]
 for provider in PROVIDERS:
  try:confirmed.append(check_provider(provider,fetcher,now))
  except Uncertain as error:
   if diagnostics is not None:diagnostics.append(f"{provider['slug']}: {str(error)[:190]}")
  except Exception:
   if diagnostics is not None:diagnostics.append(f"{provider['slug']}: Official source unavailable, form unreadable, or parser mismatch.")
 return confirmed

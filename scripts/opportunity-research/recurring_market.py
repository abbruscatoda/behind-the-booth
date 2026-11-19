"""Officially documented recurring-market vendor waitlists.

A season-long *waitlist* is not a guaranteed event date or an open booth.
Only explicit approved organizer pages may trigger automatic publication.
Provider configuration is deliberately narrow: extend with tested official
source patterns, not with guessed recurrence or generic registration links.
"""
from __future__ import annotations
from datetime import datetime,date,timezone
from urllib.parse import urljoin,urlparse,parse_qs
import re
from verifier import Uncertain,valid_url,clean
from category_rules import visible_text

HOLLY_MARKET='https://www.hollyspringsnc.gov/319/Farmers-Market'
HOLLY_VENDOR='https://www.hollyspringsnc.gov/1824/Become-a-Vendor'
HOLLY_VISIT='https://www.hollyspringsnc.gov/574/Plan-Your-Visit'
HOLLY_APPLICATION='https://managemymarket.com/VendorRegister.aspx?orgID=933'
POLICY='recurring-official-waitlist-v1'

# Explicit, independently reviewed provider configuration. Never infer an
# application's target from a link labeled "Online Registration".
PROVIDERS=(
 {'market_name':'Holly Springs Farmers Market',
  'organizer':'Town of Holly Springs','city':'Holly Springs',
  'market_slug':'holly-springs-farmers-market',
  'market_url':HOLLY_MARKET,'vendor_url':HOLLY_VENDOR,'visit_url':HOLLY_VISIT,
  'application_url':HOLLY_APPLICATION,
  'provider':'ManageMyMarket'},
)

def _linked(doc,base,target):
 return target in {
  urljoin(base,url) for url in doc.root.links(base)
 }

def official_registration_link(doc,base,provider):
 """Canonicalize only an exact, organizer-linked ManageMyMarket registration.

 Reject other organizations, login/prefill URLs and user-supplied registration
 destinations. A municipality may link HTTP or www variants; we always
 publish its exact expected HTTPS registration URL.
 """
 expected=urlparse(provider['application_url'])
 expected_id=parse_qs(expected.query).get('orgID',[''])[0]
 for url in doc.root.links(base):
  try:
   p=urlparse(url)
   query=parse_qs(p.query)
   if (p.scheme in ('http','https')
    and p.hostname in ('managemymarket.com','www.managemymarket.com')
    and p.path.lower() in ('/vendorregister.aspx','/landing.aspx')
    and set(query)=={'orgID'} and query['orgID']==[expected_id]
    and expected_id.isdigit() and not p.username and not p.password
    and p.port in (None,80,443) and not p.fragment):
    return provider['application_url']
  except ValueError:
   continue
 return None

def check_recurring_provider(provider,fetcher,now=None):
 now=now or datetime.now(timezone.utc)
 from zoneinfo import ZoneInfo
 today=now.astimezone(ZoneInfo('America/New_York')).date()
 main,main_hash=fetcher.get(provider['market_url'])
 vendor,vendor_hash=fetcher.get(provider['vendor_url'])
 # CivicPlus places the market breadcrumb on the vendor page rather than
 # necessarily showing a direct vendor link on every market landing page.
 if not _linked(vendor,provider['vendor_url'],provider['market_url']):
  raise Uncertain('Official vendor page is not linked back to this farmers market.')
 if official_registration_link(vendor,provider['vendor_url'],provider) is None:
  # Keep the official third-party link bound to the exact market account.
  raise Uncertain('Official vendor page does not link the approved ManageMyMarket organization registration.')
 if not valid_url(provider['vendor_url']):raise Uncertain('Untrusted official vendor page.')
 main_text=visible_text(main.root)
 text=visible_text(vendor.root)
 # Reject the common false positive: the municipality's generic classes and
 # recreation portal are NOT vendor applications for this market.
 if not re.search(r'Holly Springs Farmers Market',main_text,re.I):
  raise Uncertain('Official market identity missing.')
 if not re.search(r'Open Every Saturday|Every Saturday|Almost every Saturday',main_text,re.I):
  raise Uncertain('Recurring market schedule is no longer confirmed.')
 if not re.search(r'We accept applications all year long',text,re.I):
  raise Uncertain('Year-round vendor applications are not clearly confirmed.')
 if not re.search(r'considered for our waiting list',text,re.I):
  raise Uncertain('Waitlist availability is not clearly confirmed.')
 if not re.search(r'We are not currently accepting food trucks',text,re.I):
  raise Uncertain('Food truck restrictions changed; review source.')
 if not re.search(r'(?:Farmers Market )?Fees\s*:\s*Season\s*20\s*\(?May\s+20(\d{2})\s*-\s*April\s+20(\d{2})\)?',text,re.I):
  raise Uncertain('Exact dated seasonal fee schedule unavailable.')
 years=re.findall(r'(?:Farmers Market )?Fees\s*:\s*Season\s*20\s*\(?May\s+(20\d{2})\s*-\s*April\s+(20\d{2})\)?',text,re.I)
 if len(set(years))!=1:raise Uncertain('Market season dates conflict.')
 start_year,end_year=map(int,years[0])
 if end_year!=start_year+1:raise Uncertain('Market season spans an unsupported period.')
 starts=date(start_year,5,1)
 ends=date(end_year,4,30)
 if today>ends or today<starts:raise Uncertain('Not within the organizer-confirmed market season.')
 if not re.search(r'Application Fee\s*\$20\b',text,re.I):
  raise Uncertain('Published application fee changed.')
 if not re.search(r'Weekly Vendor\s*\(50 dates\)\s*\$442',text,re.I):
  raise Uncertain('Extended-season price or number of dates changed.')
 if not re.search(r'Winter Season',text,re.I):raise Uncertain('Winter market schedule unavailable.')
 if not re.search(r'seeking farmers and producers from across North Carolina',text,re.I):
  raise Uncertain('Official eligibility no longer identifies North Carolina farmers and producers.')
 if not re.search(r'liability insurance',text,re.I) or not re.search(r'tax ID',text,re.I):
  raise Uncertain('Vendor requirements incomplete.')
 # The municipality maintains a separate, authoritative visitor page
 # for the location and schedule. A page's footer can be its Town Hall
 # address; verify the MARKET address, not the municipal mailing address.
 visit,visit_hash=fetcher.get(provider['visit_url'])
 if not _linked(visit,provider['visit_url'],provider['market_url']):
  raise Uncertain('Official visitor page does not identify the same farmers market.')
 visit_text=visible_text(visit.root)
 if not re.search(r'farmers market is located at\s+300\s+W\.?\s+Ballentine\s+St\.?',visit_text,re.I):
  raise Uncertain('Official visitor page no longer confirms the market street address.')
 if not re.search(r'now open every Saturday year-round',visit_text,re.I):
  raise Uncertain('Official year-round market schedule was not confirmed.')
 # Never claim that an individual Saturday is scheduled: exceptions are
 # published without all exact excluded dates. This is a seasonal listing.
 price_notes=(
  'Season 20 (May 2026–April 2027): extended weekly $442 (50 dates), '
  'extended alternate weeks $264 (25 dates); traditional weekly $287, '
  'alternate weeks $172, day $20; winter weekly $207, '
  'alternate weeks $103, day $20. Additional booth space and electricity cost extra. '
  'Prices vary by attendance plan. Application fee $20.'
 )
 eligibility=(
  'Vendor applications are accepted year-round for the waiting list, '
  'not for a guaranteed booth. Primarily North Carolina farmers and food producers; '
  'this is a food-focused market. Food trucks are not currently accepted. '
  'Tax ID required; approved vendors must provide proof of liability insurance '
  'and applicable permits, inspections and labeling.'
 )
 data={
  'title':'Holly Springs Farmers Market — 2026–2027 Vendor Waitlist',
  'market_slug':provider['market_slug'],'organizer':provider['organizer'],
  'city':provider['city'],'state':'NC','venue':'300 W. Ballentine St.',
  'starts_on':starts.isoformat(),'ends_on':ends.isoformat(),
  'deadline':None,'application_url':provider['application_url'],
  'source_url':provider['vendor_url'],'market_url':provider['market_url'],
  'availability':'waitlist','schedule_type':'recurring_season',
  'application_fee':20,'booth_fee':None,'deposit':None,
  'categories':[],'fee_notes':price_notes,'eligibility':eligibility,
  'research_notes':'Season-long market waitlist. Saturdays except organizer-announced holiday/town-event exceptions. Summer 8 a.m.–noon; winter 9 a.m.–noon. Vendor registration is handled externally by ManageMyMarket. Confirm individual dates and availability with the organizer.'
 }
 return {'decision':'publish','policy':POLICY,'candidate':data,
  'checked_at':now.isoformat(),'source_hash':vendor_hash,
  'market_source_hash':main_hash,'visit_source_hash':visit_hash,
  'evidence':'Official municipality market page links to vendor page which explicitly confirms year-round waitlist applications, season dates, fees, eligibility and exact ManageMyMarket application.',
  'reason':'Official municipal organizer confirms current-season waitlist applications without a cutoff; not represented as an open booth.'}

def discover_recurring(fetcher,now=None,diagnostics=None):
 found=[]
 for provider in PROVIDERS:
  try:found.append(check_recurring_provider(provider,fetcher,now))
  except Uncertain as error:
   # Only raise statements authored in this module. Never log arbitrary
   # webpage text, credentials, source contents, or application responses.
   if diagnostics is not None:diagnostics.append(provider['market_slug']+': '+str(error)[:180])
  except Exception:
   # Other verified publications must not be altered by website outages.
   if diagnostics is not None:diagnostics.append(provider['market_slug']+': official source unavailable or parser failed')
 return found

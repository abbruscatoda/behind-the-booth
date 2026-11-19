"""Officially documented recurring-market vendor waitlists.

A season-long *waitlist* is not a guaranteed event date or an open booth.
Only explicit approved organizer pages may trigger automatic publication.
Provider configuration is deliberately narrow: extend with tested official
source patterns, not with guessed recurrence or generic registration links.
"""
from __future__ import annotations
from datetime import datetime,date,timezone
from urllib.parse import urljoin
import re
from verifier import Uncertain,valid_url,clean
from category_rules import visible_text

HOLLY_MARKET='https://www.hollyspringsnc.gov/319/Farmers-Market'
HOLLY_VENDOR='https://www.hollyspringsnc.gov/1824/Become-a-Vendor'
HOLLY_APPLICATION='https://managemymarket.com/VendorRegister.aspx?orgID=933'
POLICY='recurring-official-waitlist-v1'

# Explicit, independently reviewed provider configuration. Never infer an
# application's target from a link labeled "Online Registration".
PROVIDERS=(
 {'market_name':'Holly Springs Farmers Market',
  'organizer':'Town of Holly Springs','city':'Holly Springs',
  'market_slug':'holly-springs-farmers-market',
  'market_url':HOLLY_MARKET,'vendor_url':HOLLY_VENDOR,
  'application_url':HOLLY_APPLICATION,
  'provider':'ManageMyMarket'},
)

def _linked(doc,base,target):
 return target in {
  urljoin(base,url) for url in doc.root.links(base)
 }

def check_recurring_provider(provider,fetcher,now=None):
 now=now or datetime.now(timezone.utc)
 from zoneinfo import ZoneInfo
 today=now.astimezone(ZoneInfo('America/New_York')).date()
 main,main_hash=fetcher.get(provider['market_url'])
 vendor,vendor_hash=fetcher.get(provider['vendor_url'])
 if not _linked(main,provider['market_url'],provider['vendor_url']):
  raise Uncertain('Main official market page no longer links its vendor information.')
 if not _linked(vendor,provider['vendor_url'],provider['application_url']):
  raise Uncertain('Official vendor page no longer links the configured vendor application.')
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
 if not re.search(r'food only',main_text,re.I):
  raise Uncertain('Market food-focused eligibility has changed.')
 if not re.search(r'liability insurance',text,re.I) or not re.search(r'tax ID',text,re.I):
  raise Uncertain('Vendor requirements incomplete.')
 if not re.search(r'300 W\.? Ballentine St\.?',main_text,re.I):
  raise Uncertain('Official venue address not confirmed.')
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
  'market_source_hash':main_hash,
  'evidence':'Official municipality market page links to vendor page which explicitly confirms year-round waitlist applications, season dates, fees, eligibility and exact ManageMyMarket application.',
  'reason':'Official municipal organizer confirms current-season waitlist applications without a cutoff; not represented as an open booth.'}

def discover_recurring(fetcher,now=None):
 found=[]
 for provider in PROVIDERS:
  try:found.append(check_recurring_provider(provider,fetcher,now))
  except (Uncertain,ValueError,TypeError,KeyError,IndexError):
   continue
  except Exception:
   # Other verified publications must not be altered by website outages.
   continue
 return found

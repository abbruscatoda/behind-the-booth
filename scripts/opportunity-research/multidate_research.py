"""Guarded, config-driven extraction of future dates from official multi-date Jotforms.

A date offered in the organizer's *current linked application* is evidence of
vendor intake when the organizer explicitly says displayed dates remain open.
Never infer a cutoff, read private responses, or submit the application.
"""
from datetime import datetime,timezone,date,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from calendar import month_name
import re

from verifier import Uncertain,valid_url
from category_rules import visible_text

POLICY='triangle-multidate-jotform-v1'
PROVIDERS=(
 {'slug':'cary-night-market','name':'Cary Night Market',
  'organizer':'The Night Market Company','city':'Cary',
  'source':'https://thenightmarketcompany.com/plan-your-markets-vendor-info',
  'market_root':'https://thenightmarketcompany.com/',
  'form_hint':'https://pci.jotform.com/form/253207413592151',
  'vendor_label':'Cary Night Market Vendor Application',
  'venue':'Downtown Cary Park'},
)
MONTHS='|'.join(month_name[i] for i in range(1,13))
DATED=re.compile(r'\\b('+MONTHS+r')\\s+(\\d{1,2}),?\\s+(20\\d{2})\\s+(?:Market|\\(Holiday[^)]*\\))',re.I)
FEE=re.compile(r'\\$\\s*(\\d{1,4})(?:\\.\\d{2})?')
SUBMIT=re.compile(r'\\bSubmit Form\\b',re.I)
CLOSED=re.compile(r'no longer accepting responses|form.{0,30}closed|applications? are closed',re.I)

def verify_provider(provider,fetcher,now=None):
 now=now or datetime.now(timezone.utc)
 today=now.astimezone(ZoneInfo('America/New_York')).date()
 source=provider['source']
 root,_=fetcher.get(provider['market_root'])
 vendor,vendor_hash=fetcher.get(source)
 root_links=set(root.root.links(provider['market_root']))
 if source not in root_links:
  raise Uncertain('Organizer no longer links its current market application page.')
 source_text=visible_text(vendor.root)
 if not re.search('Applications Are Now OPEN|Vendor Applications are now open',source_text,re.I):
  raise Uncertain('Official organizer does not affirm an active vendor intake.')
 if not re.search(r'if market dates are still on the application.{0,80}still accepting vendors',source_text,re.I):
  raise Uncertain('Organizer does not confirm that listed application dates remain available.')
 candidates=[url for url in vendor.root.links(source)
             if valid_url(url) and urlparse(url).hostname=='pci.jotform.com'
             and urlparse(url).path.startswith('/form/')]
 # Require the exact current application to remain explicitly linked by
 # the organizer. Do not guess from archival lead URLs.
 app=provider['form_hint']
 if app not in candidates:raise Uncertain('Current linked organizer form has changed; verify the new form before publication.')
 form,app_hash=fetcher.get(app)
 details=visible_text(form.root)
 if CLOSED.search(details):raise Uncertain('Application is closed.')
 if not re.search(r'The Night Market Company.{0,40}Vendor Application',details,re.I|re.S):
  raise Uncertain('Form organizer and vendor type do not match.')
 if not re.search(r'Fall Cary Night Market 2026',details,re.I):
  raise Uncertain('The linked form does not identify the approved 2026 market season.')
 if not SUBMIT.search(details):
  raise Uncertain('Public form has no readable Submit Form action.')
 app_fee=re.search(r'Application Fee.{0,180}?\\$\\s*10(?:\\.00)?',details,re.I|re.S)
 if not app_fee:raise Uncertain('Application fee has changed and needs verification.')
 results=[]
 seen=set()
 for match in DATED.finditer(details):
  month,day,year=match.groups()
  try:when=datetime.strptime(month+' '+day+' '+year,'%B %d %Y').date()
  except ValueError:continue
  if when in seen or when<today+timedelta(days=2) or when>today+timedelta(days=183):continue
  # Reject conflicting year from an old seasonal form; form says 2026.
  if when.year!=2026:continue
  nearby=details[match.end():match.end()+240]
  price=FEE.search(nearby)
  if not price:continue
  booth=int(price.group(1))
  if booth not in (140,160):continue
  seen.add(when)
  title=f"Cary Night Market — {when.strftime('%B')} {when.day}, {when.year}"
  candidate={
   'title':title,'market_slug':provider['slug'],
   'organizer':provider['organizer'],'city':provider['city'],'state':'NC',
   'venue':provider['venue'],'starts_on':when.isoformat(),'ends_on':when.isoformat(),
   'schedule_type':'dated_event','deadline':None,'availability':'open',
   'source_url':source,'application_url':app,
   'booth_fee':booth,'application_fee':10,'deposit':None,'categories':[],
   'fee_notes':f'The live organizer-linked 2026 retail form offers this date at ${booth} plus a one-time ${10} nonrefundable application fee. Acceptance and booth availability are not guaranteed.',
   'eligibility':'For eligible local retail, handmade and artisan vendors. Food trucks must use the separate food-truck application. A valid NC sales tax ID and organizer approval may be required.',
   'research_notes':'This date appeared as a selectable paid market in the official, current multi-date 2026 Jotform. Organizer states listed dates are accepting vendors; no deadline is published for this individual date. Confirm remaining availability before paying.'
  }
  results.append({'policy':POLICY,'decision':'publish','candidate':candidate,
                  'checked_at':now.isoformat(),'source_hash':vendor_hash,
                  'application_hash':app_hash,'form_readable':True,
                  'form_complete':True,'date_verified':True,
                  'fee_verified':True,'organizer_root':provider['market_root'],
                  'evidence':'The official organizer links an active 2026 vendor form and states every displayed date is accepting applications. The exact future date and price are visible in that form, with a public Submit Form action.'})
 return results

def discover_multidate(fetcher,now=None,diagnostics=None):
 found=[]
 for provider in PROVIDERS:
  try:found.extend(verify_provider(provider,fetcher,now))
  except Exception as exc:
   if diagnostics is not None:diagnostics.append({'organizer':provider['organizer'],'reason':str(exc)[:240]})
 return found

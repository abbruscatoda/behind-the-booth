"""Reusable evidence-bound seasonal application research.

A market season is one opportunity, never a promise that every Saturday has
vendor space. Supported organizers are registered as exact trusted sources.
New providers must pass the same independent page/form checks and DB allowlist.
No responses are submitted and no application is filled out.
"""
from datetime import datetime,date,timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
import re
from verifier import clean,Uncertain,valid_url
from category_rules import visible_text
from google_forms import read_public_form

POLICY="seasonal-official-form-v1"
PROVIDERS=(
 dict(market_slug="fuquay-varina-growers-market",market_name="Fuquay-Varina Growers Market",
      organizer="Fuquay-Varina Growers Market",city="Fuquay-Varina",
      market_url="https://www.fvgrowersmarket.com/",
      vendor_url="https://www.fvgrowersmarket.com/vendor-application",
      form_url="https://form.jotform.com/242064838372157",
      kind="fixed_season",season_year=2027,season_start=(4,10),season_end=(9,4),
      venue="121 N. Main St.",availability="open"),
 dict(market_slug="western-wake-farmers-market",market_name="Western Wake Farmers Market",
      organizer="Western Wake Farmers Market",city="Morrisville",
      market_url="https://westernwakefarmersmarket.org/",
      vendor_url="https://westernwakefarmersmarket.org/apply",
      form_url="https://forms.gle/DmuLW5ni7Bu3Avhj8",
      kind="rolling",season_year=2026,season_start=(4,1),season_end=(3,31),
      venue="101 Town Hall Drive",availability="open"),
)

def linked(doc,base,target):
 return target in doc.root.links(base)

def normalize_text(t):
 return re.sub(r'\s+',' ',clean(t)).lower()

def form_is_live(doc):
 facts=read_public_form(doc)
 if facts['closed'] or not facts['complete'] or facts.get('issues'):
  raise Uncertain("The application is closed, incomplete, or has conflicting fields.")
 return facts

def check_provider(provider,fetcher,now=None):
 now=now or datetime.now(timezone.utc)
 today=now.astimezone(ZoneInfo("America/New_York")).date()
 main,main_hash=fetcher.get(provider['market_url'])
 vendor,vendor_hash=fetcher.get(provider['vendor_url'])
 if not valid_url(provider['form_url']) or not linked(main,provider['market_url'],provider['vendor_url']):
  raise Uncertain('Official market does not currently link to the vendor application page.')
 if not linked(vendor,provider['vendor_url'],provider['form_url']):
  raise Uncertain('Vendor page does not currently link to the exact approved application.')
 main_text=normalize_text(visible_text(main.root))
 vendor_text=normalize_text(visible_text(vendor.root))
 if not all(word in main_text+" "+vendor_text for word in ('market','vendor')):
  raise Uncertain('Official market identity is not confirmed.')
 if provider['kind']=='fixed_season':
  year=provider['season_year']
  if not re.search(r'now accepting vendor applications for (?:our )?'+str(year)+r' season',vendor_text):
   raise Uncertain('The application is not currently confirmed open for the named season.')
  if not (re.search(r'saturdays,? (?:10 apr|apr(?:il)? 10)\s*[-–]\s*(?:04 sep|sep(?:tember)? 4)',vendor_text)
          or ('april 10th through september 4th' in vendor_text)):
   raise Uncertain('Official season dates are missing or changed.')
  if '121 n. main st' not in vendor_text or '121 n main street' not in main_text:
   raise Uncertain('Official market address changed.')
  start=date(year,*provider['season_start'])
  end=date(year,*provider['season_end'])
 else:
  if 'applications are accepted on a rolling basis' not in vendor_text:
   raise Uncertain('Organizer does not confirm rolling applications.')
  if not re.search(r'(?:vendor applications rolling|applications are open).*?(?:26/27|2026/27|2026-27)',main_text):
   raise Uncertain("The market is not confirmed accepting this season’s vendors.")
  if 'open saturdays year-round' not in main_text or '101 town hall drive' not in main_text:
   raise Uncertain('Official seasonal schedule or venue missing.')
  start=date(provider['season_year'],*provider['season_start'])
  end=date(provider['season_year']+1,*provider['season_end'])
 if end<today or start>today.replace(year=today.year+2):
  raise Uncertain('Official application season is not current or upcoming.')
 form,form_hash=fetcher.get(provider['form_url'])
 facts=form_is_live(form)
 form_text=normalize_text(visible_text(form.root))
 if provider['kind']=='fixed_season':
  if not ('2027 new vendor application' in form_text and
          'saturdays, april 10th to september 4th' in form_text):
   raise Uncertain('Application is for a different event or season.')
  if 'full-time, $260' not in form_text or 'guest $30 per day' not in form_text:
   raise Uncertain('Application fee schedule changed.')
  if re.search(r'\b(?:not accepting applications|applications are closed)\b',form_text):
   raise Uncertain('The application is closed.')
  fee_notes=('2027: Full-time $260 (22 Saturdays), part-time $180 (11 Saturdays), '
             'guest $30 per day. Organizer confirms preferred dates and vendor-category '
             'capacity separately; the listed season does not guarantee a booth on each Saturday.')
  eligibility=('New vendor application; farmers, producers and artisans. No MLM, boutiques or '
               'non-handcrafted commercial items. Required tax ID and applicable inspections; '
               'artisans may participate as guest vendors only (maximum once every three weeks).')
 else:
  if not re.search(r'western wake|wwfm',form_text):
   raise Uncertain('Public form does not confirm the intended farmers market.')
  if not re.search(r'(?:vendor|market) application',form_text):
   raise Uncertain('Public form is not clearly a vendor application.')
  fee_notes=('Non-refundable application fee required; participation prices vary '
             'by vendor arrangement and frequency. Consult the organizer fee schedule.')
  eligibility=('Rolling applications; applications are reviewed by the market, '
               'and acceptance is not guaranteed. Review market rules before applying.')
 # A season-long application is NOT evidence of availability on individual dates.
 research_notes=('Seasonal vendor application; individual Saturday participation '
                 'depends on organizer approval and remaining date/category capacity. '
                 'Contact organizer to confirm specific dates.')
 candidate={'title':provider['market_name']+' — '+str(start.year)+(('–'+str(end.year)) if end.year!=start.year else '')+' Vendor Applications',
  'market_slug':provider['market_slug'],'organizer':provider['organizer'],
  'city':provider['city'],'state':'NC','venue':provider['venue'],
  'starts_on':start.isoformat(),'ends_on':end.isoformat(),
  'deadline':None,'application_url':provider['form_url'],
  'source_url':provider['vendor_url'],'market_url':provider['market_url'],
  'availability':provider['availability'],
  'schedule_type':'seasonal_application' if provider['kind']=='fixed_season' else 'rolling_market',
  'booth_fee':None,'application_fee':None,'deposit':None,
  'categories':[],'fee_notes':fee_notes,'eligibility':eligibility,
  'research_notes':research_notes}
 return {'policy':POLICY,'decision':'publish','candidate':candidate,
   'checked_at':now.isoformat(),'source_hash':vendor_hash,
   'market_source_hash':main_hash,'application_hash':form_hash,
   'evidence':'Official organizer market and vendor page link an exact readable live application that confirms this season and access rules.',
   'reason':'Independently validated official seasonal application; no individual market date or fee inferred.'}

def discover_seasonal(fetcher,now=None,diagnostics=None):
 results=[]
 for provider in PROVIDERS:
  try:results.append(check_provider(provider,fetcher,now))
  except Uncertain as error:
   if diagnostics is not None:diagnostics.append(provider['market_slug']+': '+str(error)[:180])
  except Exception:
   if diagnostics is not None:diagnostics.append(provider['market_slug']+': official page or application could not be checked')
 return results

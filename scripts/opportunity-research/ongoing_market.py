"""Conservative year-round market verification, grounded in official live sources.

The Raleigh Market is the first approved adapter. Other Explore Markets are
audited as gaps, not automatically declared open merely because they recur.
"""
from datetime import datetime,date,timezone
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
import re
from verifier import Uncertain,clean,valid_url
from category_rules import visible_text

POLICY="raleigh-rolling-official-v1"
ROOT="https://www.theraleighmarket.com/"
SOURCE="https://www.theraleighmarket.com/sell-with-us"
APPLICATION="https://form.jotform.com/200075436464149"
SLUG="the-raleigh-market"

def verify_raleigh(fetcher,now=None):
 now=now or datetime.now(timezone.utc)
 homepage,home_hash=fetcher.get(ROOT)
 source,source_hash=fetcher.get(SOURCE)
 if SOURCE not in homepage.root.links(ROOT):
  raise Uncertain("Market homepage no longer links the official vendor information page.")
 text=visible_text(source.root)
 if not re.search(r'The Raleigh Market',text,re.I) or not re.search(r'4285\s+Trinity',text,re.I):
  raise Uncertain("Market identity or location missing from the official page.")
 if not re.search(r'Saturday and Sunday\s+9\s*am\s*-\s*5\s*pm',text,re.I):
  raise Uncertain("Current weekend market schedule is not independently confirmed.")
 if not re.search(r'TEMPORARY OUTDOOR VENDORS',text,re.I) or not re.search(r'weekly call.for.vendors',text,re.I):
  raise Uncertain("Ongoing temporary-vendor intake no longer confirmed.")
 if not re.search(r'no need to re.submit each week',text,re.I):
  raise Uncertain("Official application is no longer confirmed to be rolling.")
 if re.search(r'no longer accepting (?:temporary|outdoor|new) vendors|temporary vendor applications (?:are )?closed',text,re.I):
  raise Uncertain("Organizer reports closed temporary-vendor intake.")
 links={urljoin(SOURCE,n.attrs['href']) for n in source.root.walk()
        if n.tag=='a' and n.attrs.get('href') and re.search(r'(?:request to be a vendor|request to become a vendor)',clean(n.text()),re.I)}
 if links!={APPLICATION}:
  raise Uncertain("Official vendor page no longer links the expected application.")
 if not re.search(r'Weekend\s*\$50\s*/\s*10',text,re.I) or not re.search(r'\$30\s*/\s*day',text,re.I):
  raise Uncertain("Temporary outdoor booth prices have changed or cannot be verified.")
 if not re.search(r'Food trucks and vendors wishing to sell food or beverages may NOT drop in',text,re.I):
  raise Uncertain("Category-specific food restrictions changed.")
 form,form_hash=fetcher.get(APPLICATION)
 form_text=visible_text(form.root)
 if not re.search(r'The Raleigh Market',form_text,re.I):
  raise Uncertain("Application no longer names the verified organizer.")
 if not re.search(r'(?:Submit Application|Submit)',form_text,re.I):
  raise Uncertain("Public Jotform does not expose its submission control.")
 if not re.search(r'Outdoor 10.{0,6}20.{0,30}\$50/weekend.{0,20}\$30/day',form_text,re.I):
  raise Uncertain("Application pricing no longer matches organizer pricing.")
 if re.search(r'(?:form is closed|no longer accepting submissions|submission disabled)',form_text,re.I):
  raise Uncertain("Official vendor form says applications are closed.")
 year=now.astimezone(ZoneInfo("America/New_York")).year
 candidate={
  "title":"The Raleigh Market — Rolling Vendor Applications",
  "market_slug":SLUG,"market_name":"The Raleigh Market",
  "organizer":"The Raleigh Market","city":"Raleigh","state":"NC",
  "venue":"4285 Trinity Rd, Raleigh, NC 27607",
  "market_url":ROOT,"source_url":SOURCE,"application_url":APPLICATION,
  "starts_on":date(year,1,1).isoformat(),
  "ends_on":date(year+1,12,31).isoformat(),
  "schedule_type":"rolling_market","availability":"open","deadline":None,
  "booth_fee":30,"application_fee":None,"deposit":None,"categories":[],
  "fee_notes":"Temporary outdoor 10 × 20 ft space: $30 for one day or $50 for the weekend. Permanent outdoor spaces have different pricing. Food concessions require advance approval and may have different fees.",
  "eligibility":"Temporary vendors submit the organizer's request form once for weekly vendor communication. Individual weekend placements depend on availability. Food trucks and food or beverage vendors require advance reservation and approval; no drop-in food vendors. CBD and hemp products are not accepted.",
  "research_notes":"Saturday and Sunday year-round market, 9 a.m.–5 p.m. Rolling request to become a temporary vendor; no single bookable date or application cutoff is implied. Internal start/end dates are verification coverage dates, not confirmed attendance. Apply only with the organizer."
 }
 return {"decision":"publish","policy":POLICY,"candidate":candidate,
         "checked_at":now.isoformat(),"source_hash":source_hash,
         "market_source_hash":home_hash,"application_hash":form_hash,
         "evidence":"Official market home links the live Sell With Us page; organizer explicitly invites one-time temporary vendor requests and publishes matching $30/day, $50/weekend prices; live official Jotform names the same market and exposes its submit control.",
         "reason":"Verified rolling temporary vendor intake; no guaranteed weekend space."}

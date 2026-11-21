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

def _temporary_rates(text):
 """Read only the organizer's temporary-outdoor rate section.

 Never confuse permanent-vendor rent with temporary booth pricing.
 The format may change independently of vendor intake availability.
 """
 section=re.split(r'PERMANENT OUTDOOR VENDORS',text.split('TEMPORARY OUTDOOR VENDORS',1)[-1],maxsplit=1,flags=re.I)[0]
 weekend=re.search(r'\bWeekend\s*\$\s*(\d{1,4}(?:\.\d{1,2})?)\s*/\s*10',section,re.I)
 daily=re.search(r'\$\s*(\d{1,4}(?:\.\d{1,2})?)\s*/\s*day\b',section,re.I)
 day=float(daily.group(1)) if daily else None
 weekend_rate=float(weekend.group(1)) if weekend else None
 if day is not None and not (0<day<=1000):day=None
 if weekend_rate is not None and not (0<weekend_rate<=1000):weekend_rate=None
 return day,weekend_rate

def _form_rate_conflict(text,day,weekend):
 """A missing or differently formatted price is not a closure signal."""
 option=re.search(r'Outdoor\s*10.{0,8}20.{0,90}',text,re.I)
 if not option:return False
 form=option.group(0)
 d=re.search(r'\$\s*(\d{1,4}(?:\.\d{1,2})?)\s*/\s*day\b',form,re.I)
 w=re.search(r'\$\s*(\d{1,4}(?:\.\d{1,2})?)\s*/\s*weekend\b',form,re.I)
 return bool((d and day is not None and float(d.group(1))!=day)
          or (w and weekend is not None and float(w.group(1))!=weekend))

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
 # Pricing can change without closing the application. Extract current rates
 # from the official organizer page; do not turn price formatting into a
 # user-facing "Needs rechecking" status.
 day_rate,weekend_rate=_temporary_rates(text)
 if not re.search(r'Food trucks and vendors wishing to sell food or beverages may NOT drop in',text,re.I):
  raise Uncertain("Category-specific food restrictions changed.")
 form,form_hash=fetcher.get(APPLICATION)
 form_text=visible_text(form.root)
 if not re.search(r'The Raleigh Market',form_text,re.I):
  raise Uncertain("Application no longer names the verified organizer.")
 if not re.search(r'(?:Submit Application|Submit)',form_text,re.I):
  raise Uncertain("Public Jotform does not expose its submission control.")
 # A responsive Jotform can render price labels in a different order,
 # punctuation or HTML layout. The official organizer's pricing page is
 # sufficient evidence; a clearly conflicting named form option is disclosed
 # without wrongly claiming that the APPLICATION is closed.
 price_conflict=_form_rate_conflict(form_text,day_rate,weekend_rate)
 if re.search(r'(?:form is closed|no longer accepting submissions|submission disabled)',form_text,re.I):
  raise Uncertain("Official vendor form says applications are closed.")
 year=now.astimezone(ZoneInfo("America/New_York")).year
 money=lambda amount: f"${amount:,.2f}".removesuffix(".00")
 if price_conflict:
  fee_notes=("The official vendor page and application list conflicting temporary-outdoor prices. "
             "Verify the amount charged with the organizer before paying; a booth price is deliberately not displayed. "
             "Permanent spaces and food concessions have separate pricing.")
 elif day_rate is not None and weekend_rate is not None:
  fee_notes=(f"Temporary outdoor 10 × 20 ft space: {money(day_rate)} for one day or "
             f"{money(weekend_rate)} for the weekend. Permanent outdoor spaces have different pricing. "
             "Food concessions require advance approval and may have different fees.")
 else:
  fee_notes=("The organizer still accepts temporary outdoor vendor requests, but a complete standard "
             "outdoor booth fee could not be confirmed from the official page. "
             "Confirm current daily/weekend charges before paying; food and permanent spaces have different fees.")
 candidate={
  "title":"The Raleigh Market — Rolling Vendor Applications",
  "market_slug":SLUG,"market_name":"The Raleigh Market",
  "organizer":"The Raleigh Market","city":"Raleigh","state":"NC",
  "venue":"4285 Trinity Rd, Raleigh, NC 27607",
  "market_url":ROOT,"source_url":SOURCE,"application_url":APPLICATION,
  "starts_on":date(year,1,1).isoformat(),
  "ends_on":date(year+1,12,31).isoformat(),
  "schedule_type":"rolling_market","availability":"open","deadline":None,
  "booth_fee":day_rate if weekend_rate is not None and not price_conflict else None,
  "application_fee":None,"deposit":None,"categories":[],
  "fee_notes":fee_notes,
  "eligibility":"Temporary vendors submit the organizer's request form once for weekly vendor communication. Individual weekend placements depend on availability. Food trucks and food or beverage vendors require advance reservation and approval; no drop-in food vendors. CBD and hemp products are not accepted.",
  "research_notes":"Saturday and Sunday year-round market, 9 a.m.–5 p.m. Rolling request to become a temporary vendor; no single bookable date or application cutoff is implied. Internal start/end dates are verification coverage dates, not confirmed attendance. Apply only with the organizer."
 }
 return {"decision":"publish","policy":POLICY,"candidate":candidate,
         "checked_at":now.isoformat(),"source_hash":source_hash,
         "market_source_hash":home_hash,"application_hash":form_hash,
         "official_source_prices":{"day":day_rate,"weekend":weekend_rate},
         "form_price_discrepancy":price_conflict,
         "evidence":"Official market home links the live Sell With Us page; the organizer explicitly invites ongoing one-time temporary-vendor requests. Its official Jotform identifies the same market and exposes an active Submit Application control. Any missing or disputed prices are disclosed separately rather than treated as a closed application.",
         "reason":"Verified rolling temporary vendor intake; no guaranteed weekend space."}

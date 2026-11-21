"""Reusable verified rolling vendor applications for existing Explore Markets.

Only source-linked public intake with organizer identity and a readable application
may publish. Generic recurring schedules and stale forms never count as open.
No external form is submitted, no fees inferred, and no dates fabricated.
"""
from datetime import datetime, date, timezone
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo
import re
from verifier import valid_url, Uncertain, clean, norm
from category_rules import visible_text
from form_fees import extract_labeled_fees

POLICY = "explore-rolling-official-v1"
APPLICATION_WORDS = re.compile(
 r'\b(?:vendor application|apply (?:to be|as) (?:a )?vendor|vendor registration|'
 r'become a vendor|sell with us|apply now|apply here|application form|apply to vend|new vendor form)\b',re.I)
ROLLING_WORDS = re.compile(
 r'\b(?:year[- ]round (?:vendor )?applications?|(?:vendor )?applications? (?:are )?accepted '
 r'(?:on a rolling basis|year[- ]round|all year|anytime|throughout the year)|'
 r'(?:vendor )?applications? (?:are )?open (?:year[- ]round|all year)|'
 r'(?:apply|applications?) (?:at )?any time|'
 r'rolling (?:vendor )?applications?|weekly call[- ]for[- ]vendors|'
 r'no need to re[- ]submit each week)\b',re.I)
# A year-round schedule PLUS explicit current vendor intake can establish an
# ongoing application even if the organizer never writes the word 'rolling'.
# A recurring schedule alone never qualifies.
YEAR_ROUND = re.compile(r'\b(?:year[- ]round|every (?:saturday|sunday|week)|weekly market|open (?:all year|every week))\b',re.I)
CURRENT_INTAKE = re.compile(r'\b(?:now accepting (?:new )?vendors?|(?:vendor )?applications? (?:are )?(?:now |currently )?open|accepting (?:new )?vendor applications?)\b',re.I)
CLOSED_WORDS = re.compile(
 r'\b(?:applications? (?:are|have|is) (?:now )?closed|'
 r'no longer accepting (?:new )?(?:vendor )?applications?|'
 r'not (?:currently )?accepting (?:new )?(?:vendor )?applications?|'
 r'applications? (?:have )?ended|form is no longer accepting responses|'
 r'waitlist only|invitation only|returning vendors only)\b',re.I)
DATE_LOCK = re.compile(r'\b(?:applications? (?:for|open for) (?:the )?20\d{2} (?:festival|holiday|event)|'
 r'(?:applications?|vendor registration) (?:close|closed|end|deadline) (?:on|at|by)|'
 r'apply for (?:our|the) (?:next|upcoming) (?:event|festival))\b',re.I)
FORM_HOSTS = {"form.jotform.com","pci.jotform.com","docs.google.com","forms.gle"}
SUBMIT = re.compile(r'\b(?:submit|apply now|next)\b',re.I)

def _same_host(a,b):
 def host(url):return (urlparse(url).hostname or "").removeprefix("www.")
 return bool(host(a)) and host(a)==host(b)

def _named(text,name):
 return norm(name) in norm(text) and len(norm(name))>=9

def _links(doc,base):
 return [(clean(n.text()),urljoin(base,n.attrs['href']))
   for n in doc.root.walk() if n.tag=="a" and n.attrs.get("href")]

def _form_controls(doc):
 # Explicitly enabled buttons only; no responses or form submission.
 return any(
  n.tag in {"button","input","div","span"} and
  (n.tag not in {"div","span"} or n.attrs.get("role")=="button") and
  n.attrs.get("disabled") is None and n.attrs.get("aria-disabled")!="true" and
  SUBMIT.search(clean(n.attrs.get("value","") if n.tag=="input" else n.text()))
  for n in doc.root.walk())

def verify_generic_market(market,fetcher,now=None):
 now=now or datetime.now(timezone.utc)
 slug=market.get("slug","")
 name=clean(market.get("name",""))
 city=clean(market.get("city",""))
 website=market.get("website_url","")
 if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug) or len(name)<9 or len(city)<3:
  raise Uncertain("Explore Market identity is incomplete.")
 if not valid_url(website):
  raise Uncertain("Market website is outside approved official-source hosts.")
 root,root_hash=fetcher.get(website)
 root_text=visible_text(root.root)
 if not _named(root_text,name):
  raise Uncertain("Official market website does not identify this exact market.")
 root_links=_links(root,website)
 # Only follow vendor-specific links directly advertised on the official home
 # page; never discover an unrelated application through an internet search.
 possibilities=[(website,root,root_hash)]
 for label,url in root_links:
  if not APPLICATION_WORDS.search(label) or not _same_host(website,url) or not valid_url(url):
   continue
  if url!=website:
   try:doc,receipt=fetcher.get(url)
   except Exception:continue
   possibilities.append((url,doc,receipt))
  if len(possibilities)>=5:break

 for source_url,doc,source_hash in possibilities:
  source_text=visible_text(doc.root)
  if source_url!=website and not _named(source_text,name):
   continue
  # Reject event-specific and expired seasonal pages, regardless of whether
  # an old form is still reachable.
  if CLOSED_WORDS.search(source_text) or DATE_LOCK.search(source_text):
   continue
  if not (ROLLING_WORDS.search(source_text) or
          (YEAR_ROUND.search(root_text+' '+source_text) and
           CURRENT_INTAKE.search(source_text))):
   continue
  if not APPLICATION_WORDS.search(source_text):
   continue
  links=[(label,url) for label,url in _links(doc,source_url)
    if APPLICATION_WORDS.search(label) and url!=source_url and valid_url(url)
    and (_same_host(website,url) or urlparse(url).hostname in FORM_HOSTS)]
  # If a form is already linked on the official root but intake confirmation
  # is on a linked vendor page, require that vendor page to link it again.
  for label,application in links[:6]:
   if application==website or application==source_url:continue
   try:form,form_hash=fetcher.get(application)
   except Exception:continue
   form_text=visible_text(form.root)
   if CLOSED_WORDS.search(form_text) or DATE_LOCK.search(form_text):continue
   if not _named(form_text,name):continue
   if not _form_controls(form):continue
   year=now.astimezone(ZoneInfo("America/New_York")).year
   fees=extract_labeled_fees(form_text)
   verified_fees=[]
   if fees['application_fee'] is not None:
    verified_fees.append(f"The linked official application lists a ${fees['application_fee']:,.2f} application fee.")
   if fees['booth_fee'] is not None:
    verified_fees.append(f"The linked official application lists a ${fees['booth_fee']:,.2f} booth fee per event.")
   # Never guess a missing fee or vendor category.
   candidate={
    "title":name+" — Rolling Vendor Applications",
    "market_slug":slug,"market_name":name,"organizer":name,
    "city":city,"state":"NC","venue":name+", "+city+", NC",
    "market_url":website,"source_url":source_url,"application_url":application,
    "starts_on":date(year,1,1).isoformat(),
    "ends_on":date(year+1,12,31).isoformat(),
    "schedule_type":"rolling_market","availability":"open","deadline":None,
    "booth_fee":fees['booth_fee'],"application_fee":fees['application_fee'],"deposit":None,"categories":[],
    "fee_notes":" ".join(verified_fees)+" Confirm other category-specific rates, required extras, and the total cost before applying. Missing fee types are unconfirmed, not free." if verified_fees else "No universal standard vendor booth or application fee verified. Ask the organizer about category-specific rates, required extras, and the total cost before applying.",
    "eligibility":"The official organizer currently advertises ongoing vendor intake for a recurring market. Individual event dates, vendor eligibility, food permits, booth acceptance and available spaces must be confirmed directly with the organizer.",
    "research_notes":"Ongoing organizer intake verified from the named market's official website and linked readable application. Dates saved internally are a verification horizon, not bookable market dates. No fixed application deadline or guaranteed booth is represented."
   }
   return {"decision":"publish","policy":POLICY,"candidate":candidate,
    "checked_at":now.isoformat(),"market_source_hash":root_hash,
    "source_hash":source_hash,"application_hash":form_hash,
    "evidence":"Official market website identifies the named organizer, directly links a vendor page advertising rolling intake, and links a currently readable same-market application with enabled submission controls. No dated event, price, or guaranteed availability was inferred.",
    "form_fee_evidence":fees,
    "reason":"Official market and application independently confirm current rolling vendor intake."}
 raise Uncertain("No current, fully readable organizer-linked rolling application verified.")

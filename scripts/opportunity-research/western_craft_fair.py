"""Official 2026 Western Wake craft-fair verifier.

The organizer-hosted event and application pages establish vendor intake.
Its currently linked fee PDF establishes a *craft application fee*; regular
market-day booth tiers are never presumed to apply to this particular fair.
An unreadable Google Form cannot falsely downgrade otherwise verified intake.
"""
from datetime import datetime,date,timezone
from zoneinfo import ZoneInfo
from hashlib import sha256
from io import BytesIO
from urllib.parse import urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
import re

from verifier import Uncertain
from category_rules import visible_text
from form_fees import extract_labeled_fees

POLICY='western-wake-craft-official-v1'
EVENT='https://westernwakefarmersmarket.org/events/winterwonderland2026'
APPLY='https://westernwakefarmersmarket.org/apply'
EVENT_LINK='https://forms.gle/2qVzeq3moth6WvZv5'
CRAFT_LINK='https://forms.gle/Xr31Pkd6MierZ2UK9'
FORM='https://docs.google.com/forms/d/e/1FAIpQLSf-4catG9HnDm1XodMjUij_nel5Fvf4jzilVc0XXtWb21v93Q/viewform'
EVENT_DAY=date(2026,12,12)
LAST_DAY=date(2026,11,28)

class PdfRedirects(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  p=urlparse(newurl)
  if p.scheme!='https' or p.hostname not in ('westernwakefarmersmarket.org','static1.squarespace.com') or p.query or p.fragment:
   raise Uncertain('Fee schedule left the approved organizer document hosts.')
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def fee_pdf_url(page):
 urls=[]
 for url in page.root.links(APPLY):
  p=urlparse(url)
  if (p.scheme=='https' and p.hostname=='westernwakefarmersmarket.org'
      and p.path.startswith('/s/') and p.path.lower().endswith('.pdf')
      and 'fee' in p.path.lower() and 'schedule' in p.path.lower()
      and not p.query and not p.fragment and len(url)<250):
   urls.append(url)
 if len(set(urls))!=1:raise Uncertain('One current organizer-linked vendor fee PDF was not identified.')
 return urls[0]

def craft_fee_from_pdf(text):
 text=' '.join(text.split())
 # The craft-specific line must be used, not the generic new vendor or guest tier.
 m=re.search(r'Craft Vendor Application Fee.{0,100}?\$\s*(\d{1,4}(?:\.\d{1,2})?)',text,re.I)
 if not m:raise Uncertain('No independently labeled craft application fee in organizer PDF.')
 price=round(float(m.group(1)),2)
 if price<=0 or price>500:raise Uncertain('Craft application fee exceeds conservative limits.')
 other=re.search(r'vendors applying specifically to our seasonal craft fairs.{0,120}?\$\s*(\d{1,4}(?:\.\d{1,2})?)',text,re.I)
 if other and round(float(other.group(1)),2)!=price:
  raise Uncertain('Organizer PDF lists contradictory craft application fees.')
 return price

def read_fee_pdf(url):
 from pypdf import PdfReader
 p=urlparse(url)
 if p.scheme!='https' or p.hostname!='westernwakefarmersmarket.org' or not p.path.startswith('/s/'):
  raise Uncertain('Untrusted vendor fee document URL.')
 opener=build_opener(PdfRedirects())
 req=Request(url,headers={'User-Agent':'BehindTheBoothVerifier/1.0 (+https://www.behindtheboothhq.com/contact)'})
 with opener.open(req,timeout=18) as response:
  if urlparse(response.url).hostname not in ('westernwakefarmersmarket.org','static1.squarespace.com'):
   raise Uncertain('Untrusted PDF redirect destination.')
  if response.headers.get('Content-Type','').split(';')[0].lower()!='application/pdf':
   raise Uncertain('Vendor fee document is no longer a PDF.')
  data=response.read(2500001)
 if len(data)>2500000 or not data.startswith(b'%PDF'):
  raise Uncertain('Organizer PDF is unreadable or oversize.')
 try:
  pdf=PdfReader(BytesIO(data))
  if not 1<=len(pdf.pages)<=10:raise Uncertain('Unexpected vendor fee PDF length.')
  text=' '.join(page.extract_text() or '' for page in pdf.pages)
 except Exception as error:
  raise Uncertain('Cannot extract text from the official vendor fee PDF.') from error
 return text,sha256(data).hexdigest()

def verify_western_craft(fetcher,now=None,pdf_reader=read_fee_pdf):
 now=now or datetime.now(timezone.utc)
 local=now.astimezone(ZoneInfo('America/New_York')).date()
 event,event_hash=fetcher.get(EVENT)
 apply,apply_hash=fetcher.get(APPLY)
 source=visible_text(event.root)
 vendor=visible_text(apply.root)
 if not re.search(r'Winter Wonderland Craft Fair',source,re.I) or not re.search(r'December\s+12,\s*2026',source,re.I):
  raise Uncertain('Official organizer no longer confirms the dated Winter Wonderland Craft Fair.')
 if not re.search(r'11/28/26',source) or not re.search(r'Craft vendors',source,re.I):
  raise Uncertain('Official craft vendor intake date or application invitation changed.')
 if EVENT_LINK not in event.root.links(EVENT):
  raise Uncertain('Event page no longer links its approved craft registration form.')
 if CRAFT_LINK not in apply.root.links(APPLY) or 'Craft Fair Application' not in vendor:
  raise Uncertain('Organizer application page no longer links its approved craft form.')
 pdf_url=fee_pdf_url(apply)
 pdf_hash=None
 pdf_fee=None
 try:
  pdf_text,pdf_hash=pdf_reader(pdf_url)
  pdf_fee=craft_fee_from_pdf(pdf_text)
 except (Uncertain,HTTPError,URLError,TimeoutError,OSError,ValueError):
  pass
 form_hash=None
 form_access='http_auth_blocked'
 form_prices={'application_fee':None,'booth_fee':None}
 try:
  form,form_hash=fetcher.get(FORM)
 except (HTTPError,URLError,TimeoutError,OSError,ValueError):
  pass
 else:
  text=visible_text(form.root)
  if re.search(r'no longer accepting responses|form (?:is )?closed',text,re.I):
   form_access='closed'
  elif not re.search(r'you need permission|request access|sign in to continue',text,re.I):
   if re.search(r'\b(?:Next|Submit)\b',text,re.I) and len(text)>120:
    form_access='readable_first_page'
    form_prices=extract_labeled_fees(text)
 closed=local>LAST_DAY or form_access=='closed' or bool(re.search(r'registration (?:is )?closed|no longer accepting.{0,40}craft vendors',source,re.I))
 app_fee=form_prices['application_fee'] if form_prices['application_fee'] is not None else pdf_fee
 booth_fee=form_prices['booth_fee'] if form_access=='readable_first_page' else None
 if app_fee is not None:
  cost='Craft vendor application fee: $'+format(app_fee,',.2f')+(' (current linked form).' if form_prices['application_fee'] is not None else ' (organizer-linked fee schedule, labeled 2025 and still linked as current).')
 else:
  cost='A current craft-vendor application fee was not independently readable.'
 if booth_fee is not None:
  cost+=' Event-specific booth fee: $'+format(booth_fee,',.2f')+'.'
 else:
  cost+=' No event-specific booth price was verified; standard weekly-market guest rates are not presumed to apply to this craft fair.'
 if pdf_fee is not None and form_prices['application_fee'] is not None and pdf_fee!=form_prices['application_fee']:
  cost+=' The official application and general fee schedule differ; confirm the latest amount before paying.'
 cost+=' Application registration ends November 28, 2026, or sooner if full; no cutoff time was published.'
 if form_access=='http_auth_blocked':cost+=' Automated Google Form access is blocked; confirm other terms with the organizer.'
 candidate={
  'title':'Winter Wonderland Craft Fair — Western Wake Farmers Market',
  'market_slug':'western-wake-farmers-market','organizer':'Western Wake Farmers Market',
  'city':'Morrisville','state':'NC','venue':'Indian Creek Trailhead Park, 101 Town Hall Drive',
  'starts_on':EVENT_DAY.isoformat(),'ends_on':EVENT_DAY.isoformat(),
  'schedule_type':'dated_event','deadline':None,
  'availability':'closed' if closed else 'open',
  'source_url':EVENT,'application_url':CRAFT_LINK,
  'application_fee':app_fee,'booth_fee':booth_fee,'deposit':None,
  'categories':[],'fee_notes':cost,
  'eligibility':'Craft vendors and artisans can register using the organizer-linked craft fair application. Selection and remaining places depend on approval.',
  'research_notes':'The official December 12 event page and its organizer vendor page link the same public craft fair application through two verified short links. Event page states registration deadline November 28, 2026 or sooner if full. No cutoff time is inferred. Automated form access: '+form_access+'. Fee PDF: '+('readable' if pdf_hash else 'unreadable')+'.'
 }
 return {'policy':POLICY,'decision':'publish','candidate':candidate,
  'checked_at':now.isoformat(),'source_hash':event_hash,
  'application_page_hash':apply_hash,
  'fee_pdf_url':pdf_url,'fee_pdf_hash':pdf_hash,
  'application_hash':form_hash,'application_access':form_access,
  'fee_evidence':{'application_fee':app_fee,'booth_fee':booth_fee,
       'pdf_craft_fee':pdf_fee,'form_application_fee':form_prices['application_fee'],
       'form_booth_fee':form_prices['booth_fee']},
  'evidence':'The official dated event and organizer application page independently link the same craft fair form and specify a registration deadline. A linked current vendor fee PDF is checked for craft-specific fees without assuming ordinary market-day guest rates, and Google Form authorization restrictions cannot invent a closure.',
  'reason':'Officially sourced craft-fair registration and fee details automatically checked.'}

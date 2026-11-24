"""Reviewed venue watchlist and private research inbox; never trust a search snippet.

The companion public-web research sweep supplies primary-source receipts. The
scheduled worker validates those receipts against this code-reviewed watchlist.
Blocked Instagram pages stay private leads. No accounts or messages are used.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlparse
import hashlib, json, re
from verifier import Uncertain, norm, source_error

WATCHLIST=json.loads(Path(__file__).with_name('community_sources.json').read_text())
SOURCES={entry['key']:entry for entry in WATCHLIST}
POLICY='reviewed-community-call-v1'
MONTHS='January February March April May June July August September October November December'.split()
EMAIL=re.compile(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,240}[A-Za-z0-9])?\.[A-Za-z]{2,24}')
CLOSED=re.compile(r'no longer accepting|applications?\s+(?:have\s+|are\s+)?closed|vendor\s+(?:spaces?\s+)?sold out|not accepting (?:any |new )?vendors',re.I)
CALL=re.compile(r'call(?:ing)?\s+(?:for\s+)?(?:local\s+)?(?:vendors?|makers?|artists?)|(?:seeking|looking for|accepting|inviting)\s+(?:local\s+|new\s+)?(?:vendors?|makers?|artists?)|(?:vendor|artist)\s+(?:application|call|registration)|applications?\s+open|apply\s+(?:now|today|to vend|to this show)|become a vendor',re.I)

def safe_url(value):
 try:
  p=urlparse(value)
  return bool(p.scheme=='https' and p.hostname and not p.username and not p.password and p.port in (None,443) and not p.fragment and len(value)<=1200)
 except (ValueError,TypeError):return False

def official_url(url,source):
 if not safe_url(url):return False
 p=urlparse(url)
 for root in source['sources']:
  r=urlparse(root)
  if p.hostname==r.hostname and (not r.query or r.query==p.query) and (r.path in ('','/') or p.path.rstrip('/')==r.path.rstrip('/') or p.path.startswith(r.path.rstrip('/')+'/')):return True
 # A social post needs a separate ownership receipt, checked below.
 return p.hostname in {'www.instagram.com','instagram.com'} and bool(re.fullmatch(r'/(?:p|reel)/[A-Za-z0-9_-]+/?',p.path)) and not p.query

def date_attested(day,text):
 """Require an explicit year and date; never roll an old December flyer forward."""
 try:d=datetime.fromisoformat(day).date()
 except (ValueError,TypeError):return False
 if day in text:return True
 month=MONTHS[d.month-1]
 patterns=[rf'\b{month}(?:\s+|\s*[/·]\s*){d.day}(?:st|nd|rd|th)?(?:\s*[-–—&]+\s*\d{{1,2}})?\s*,?\s*{d.year}\b',
           rf'\b{month[:3]}\.?\s+{d.day}(?:st|nd|rd|th)?(?:\s*[-–—&]+\s*\d{{1,2}})?\s*,?\s*{d.year}\b',
           rf'\b0?{d.month}/0?{d.day}/(?:{d.year}|{str(d.year)[2:]})\b']
 # The second day in an explicitly dated range is independently supported.
 patterns.append(rf'\b(?:{month}|{month[:3]}\.?)\s+\d{{1,2}}(?:st|nd|rd|th)?\s*[-–—&]+\s*{d.day}(?:st|nd|rd|th)?\s*,?\s*{d.year}\b')
 return any(re.search(p,text,re.I) for p in patterns)

def validated_receipts(lead,source,now):
 receipts=lead.get('receipts',[])
 if not isinstance(receipts,list) or not 1<=len(receipts)<=8:raise Uncertain('Primary-source receipts are missing.')
 valid=[]
 for receipt in receipts:
  if not isinstance(receipt,dict):raise Uncertain('Invalid research receipt.')
  url=receipt.get('url','');text=' '.join(str(receipt.get('text','')).split())
  try:checked=datetime.fromisoformat(receipt.get('checked_at','').replace('Z','+00:00'))
  except (ValueError,TypeError):raise Uncertain('Receipt has no verified check time.')
  if checked.tzinfo is None or not -300<=(now-checked).total_seconds()<=6*3600:raise Uncertain('Primary-source research receipt is stale; re-read the source.')
  if not safe_url(url) or not 20<=len(text)<=12000 or receipt.get('access')!='public_read':raise Uncertain('A search snippet, login wall or screenshot is not a current primary-source read.')
  is_official=official_url(url,source)
  if urlparse(url).hostname in {'www.instagram.com','instagram.com'}:
   owner=receipt.get('owner','').lower().lstrip('@')
   if owner not in source['instagram'] or not re.search(r'(?:@|\b)'+re.escape(owner)+r'\b',text,re.I):raise Uncertain('Instagram post ownership is unverified; vendor reposts cannot establish availability.')
  if not is_official and receipt.get('role') not in {'application','fee'}:raise Uncertain('Event evidence is outside the reviewed organizer sources.')
  valid.append({**receipt,'text':text,'official':is_official,'sha256':hashlib.sha256(text.encode()).hexdigest()})
 return valid

def verify_research_lead(lead,now=None):
 now=now or datetime.now(timezone.utc)
 today=now.astimezone(ZoneInfo('America/New_York')).date()
 source=SOURCES.get(lead.get('source_key'))
 if not source or not source['publish']:raise Uncertain('Source is monitored for discovery; this event identity still needs review.')
 c=dict(lead.get('proposal') or {})
 receipts=validated_receipts(lead,source,now)
 events=[r for r in receipts if r.get('role')=='event' and r['official']]
 intakes=[r for r in receipts if r.get('role') in {'intake','application','opening'}]
 if not events or not intakes:raise Uncertain('Both the dated event and its vendor intake need primary-source evidence.')
 title=c.get('title','');venue=c.get('venue','')
 if not 3<=len(title)<=160 or not 5<=len(venue)<=300:raise Uncertain('Event title or venue is incomplete.')
 try:start=datetime.fromisoformat(c['starts_on']).date();end=datetime.fromisoformat(c['ends_on']).date()
 except (KeyError,ValueError,TypeError):raise Uncertain('An exact dated occurrence is required.')
 if not today<=start<=end or (start-today).days>550 or (end-start).days>31:raise Uncertain('Event is past, too distant, or not a single dated market.')
 event=next((r for r in events if date_attested(start.isoformat(),r['text']) and date_attested(end.isoformat(),r['text']) and all(term.lower() in r['text'].lower() for term in source['venue_terms']) and norm(title) in norm(r['text'])),None)
 if not event:raise Uncertain('Exact event name, year, date and reviewed venue could not be corroborated together.')
 # Explicit closures anywhere in the scoped current-event receipts win over
 # old Apply Today prose. The researcher must not mix unrelated event blocks.
 texts=' '.join(r['text'] for r in receipts)
 closed=bool(CLOSED.search(texts))
 method=c.get('application_method','form');contact=c.get('application_contact','')
 app=c.get('application_url','');opening=c.get('opens_on')
 if method not in {'form','email','instagram'} or not safe_url(app):raise Uncertain('Unsupported application method or URL.')
 intake=next((r for r in intakes if CALL.search(r['text'])),None)
 if not intake:raise Uncertain('A vendor invitation is required; a general contact address is insufficient.')
 if not (date_attested(start.isoformat(),intake['text']) or norm(title) in norm(intake['text'])):raise Uncertain('The vendor invitation is not scoped to this exact event.')
 if re.search(r'interest list|mailing list|receive (?:future|upcoming) (?:event )?applications|not an application',intake['text'],re.I):raise Uncertain('A general interest list is not a dated vendor application.')
 # External forms must be visibly linked by an official source read. Reading
 # an arbitrary matching form is not proof the organizer owns the application.
 if method!='instagram' and not official_url(app,source) and not any(app in r['text'] for r in receipts if r['official']):raise Uncertain('The official source does not link this exact vendor application.')
 status='closed' if closed else 'open'
 if opening:
  try:opens=datetime.fromisoformat(opening).date()
  except (ValueError,TypeError):raise Uncertain('Invalid application opening date.')
  if not date_attested(opening,intake['text']) or opens>start:raise Uncertain('Application opening date is unverified.')
  if not closed and opens>today:status='announced'
 if method=='email':
  if not EMAIL.fullmatch(contact) or contact.lower() not in intake['text'].lower() or not re.search(r'\b(?:email|e-mail|contact|reach out)\b',intake['text'],re.I):raise Uncertain('No explicit vendor email invitation was verified.')
 elif method=='instagram':
  if contact.lower() not in source['instagram'] or not re.search(r'\b(?:DM|direct message|message us)\b',intake['text'],re.I):raise Uncertain('No direct-message vendor invitation was verified.')
  if app!=f'https://www.instagram.com/{contact}/':raise Uncertain('DM action must open the reviewed organizer profile.')
 elif not closed and status!='announced':
  if intake.get('form_state')!='accepting' or not re.search(r'\b(?:submit|apply|application|register)\b',intake['text'],re.I):raise Uncertain('The live vendor form is not confirmed to be accepting applications.')
 # Date-only cutoffs stay date-only; no midnight deadline is invented here.
 if c.get('deadline_date') and not date_attested(c['deadline_date'],texts):raise Uncertain('Application deadline is not source-attested.')
 if c.get('deadline_date') and datetime.fromisoformat(c['deadline_date']).date()<today:status='closed'
 fees={}
 for field in ('booth_fee','application_fee','deposit'):
  value=c.get(field)
  if value is not None:
   if not isinstance(value,(int,float)) or isinstance(value,bool) or not 0<=value<=100000:raise Uncertain('Invalid sourced fee.')
   proof=next((r for r in receipts if r.get('role') in {'fee','application'} and any(float(m.replace(',',''))==value for m in re.findall(r'\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)',r['text']))),None)
   if not proof or not re.search({'booth_fee':r'booth|vendor fee|table|space','application_fee':r'application|jury','deposit':r'deposit'}[field],proof['text'],re.I):raise Uncertain('A fee needs its own application-specific labeled evidence.')
  fees[field]=value
 options=c.get('pricing_options',[])
 if not isinstance(options,list) or len(options)>12:raise Uncertain('Invalid published pricing options.')
 for option in options:
  if not isinstance(option,dict) or option.get('kind') not in {'booth','application','addon'} or option.get('unit') not in {'day','event','season','program','application'}:raise Uncertain('Invalid pricing option type.')
  amount=option.get('amount')
  kind_pattern={'booth':r'booth|vendor fee|table|space','application':r'application|jury','addon':r'additional|electricity|corner|deposit'}[option['kind']]
  proof=next((r for r in receipts if r['url']==option.get('source_url') and r.get('role') in {'fee','application'} and re.search(kind_pattern,r['text'],re.I) and any(float(m.replace(',',''))==amount for m in re.findall(r'\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)',r['text']))),None)
  if not isinstance(amount,(int,float)) or isinstance(amount,bool) or not 0<=amount<=100000 or not proof:raise Uncertain('Pricing option amount is not source-attested.')
  if not re.search({'booth':r'booth|vendor fee|table|space','application':r'application|jury','addon':r'additional|electricity|corner|deposit'}[option['kind']],proof['text'],re.I) or not 3<=len(option.get('label',''))<=180 or len(option.get('conditions',''))>700:raise Uncertain('Pricing option label or conditions need review.')
 # Product groups remain unknown until exact source choices pass the existing
 # category verifier. General attendee descriptions cannot broaden eligibility.
 candidate={**c,**fees,'availability':status,'organizer':source['organizer'],'city':source['city'],'state':'NC',
  'market_slug':source['slug'],'market_name':source['market_name'],'source_url':event['url'],'schedule_type':'dated_event',
  'categories':[],'deadline':None,'application_contact':contact if method!='form' else '',
  'fee_notes':str(c.get('fee_notes',''))[:1800],
  'eligibility':str(c.get('eligibility','Organizer selection is required. Only explicitly listed products and setups are supported.'))[:1800],
  'research_notes':'Primary-source public research checked against the reviewed organizer, exact event year and dates, vendor intake and contact method. Closed or inaccessible sources cannot establish a new opening.'}
 return {'policy':POLICY,'decision':'publish','source_key':source['key'],'candidate':candidate,'checked_at':now.isoformat(),
  'receipts':receipts,'evidence':event['text'][:1200]+' '+intake['text'][:1800]}

def research_inbox(db,now=None,dry_run=False):
 now=now or datetime.now(timezone.utc)
 context=db.rpc('btb_research_community_context')
 results=[];notes=[]
 for lead in context.get('leads',[])[:40]:
  try:result=verify_research_lead(lead,now)
  except (Uncertain,ValueError,TypeError,KeyError,AttributeError) as error:
   notes.append({'id':lead.get('id'),'title':str(lead.get('title',''))[:160],'reason':str(error)[:220]})
  else:results.append(result)
 if notes and not dry_run:db.rpc('btb_research_community_hints',{'p_hints':[{'id':row['id'],'reason':row['reason']} for row in notes if row['id']]})
 return results,{'watchlist_sources':len(WATCHLIST),'inbox_checked':len(context.get('leads',[])[:40]),'verified_calls':len(results),'unconfirmed':notes[:20]}

def website_hints(fetcher):
 """Independent request budget for reviewed venues and public embedded captions."""
 leads=[];failures=[]
 for source in WATCHLIST:
  for root in source['sources'][:2]:
   try:
    doc,_=fetcher.get(root)
    for node in doc.root.walk():
     text=node.attrs.get('alt','') if node.tag=='img' else node.text() if node.tag in {'p','h1','h2','h3'} else ''
     if not CALL.search(text) and not CLOSED.search(text):continue
     leads.append({'source_key':source['key'],'target_url':root,'title':source['market_name'],
       'notes':text[:1400],'proposal':{},'receipts':[]})
     break
   except Exception as error:failures.append({'source':source['key'],'url':root,'reason':source_error(error)})
 return leads,failures

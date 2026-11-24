"""Reviewed independent venues and public WorkForms. No applications are sent.

Old flyers identify organizers to monitor; they never establish a new date.
GRL dates require the live organizer calendar, its reviewed link hub, and the
public application schema. Extract only published questions, never responses.
"""
import json,re
from datetime import datetime,timezone,date
from zoneinfo import ZoneInfo
from html import escape
from hashlib import sha256
from urllib.parse import urlparse,urljoin
from verifier import Document,Uncertain
from category_rules import visible_text,evidence

POLICY='independent-market-applications-v1'
GRL='https://grlmarket.com/'
GRL_HUB='https://linktr.ee/Grlmarket'
# Exact application associations read from the organizer's official hub. These
# retain provenance when the hub is temporarily unreadable; they do not cache
# application availability, fees or the calendar, which must still be fetched.
REVIEWED_HUB_AT='2026-11-23T13:26:22.513673+00:00'
REVIEWED_HUB_HASH='ff3d2b1c50826ef9f1e1e686291d414106fe267c9a47e85f07f1bd950bab2781'
REVIEWED_APPS=(
 ('2026-12-05','VENDOR APP | DECEMBER 5TH | WAVERLY PLACE CARY','https://forms.monday.com/forms/94fb54c1182e4047950f44edc41d5680?r=use1'),
 ('2026-12-19','VENDOR APP | DECEMBER 19TH | TRANSFER FOOD HALL','https://forms.monday.com/forms/4a67767baa6c0b42d7e3cf8773383ce1?r=use1'),
 ('2026-12-20','VENDOR APP | DECEMBER 20TH | SEABOARD STATION','https://forms.monday.com/forms/c15a0d4bf1c2aa9a179696aa59ed2a59?r=use1'),
)
WATCHLIST=(
 ('Dogwood Bar & Eatery','Raleigh','https://www.dogwoodraleigh.com/','Christmas Pop-Up Market','The supplied December 5 flyer advertises vendor applications, but its application route and year require current official confirmation.'),
 ('Fairy Lights Bazaar','Raleigh','https://downtownraleigh.org/do/fairy-lights-bazaar','Fairy Lights Bazaar','Historical Morgan Street Food Hall event. Preserve the original year; monitor for a newly dated vendor application.'),
 ('Hartwell','Raleigh','https://www.hartwellraleigh.com/retail-markets','Hartwell Makers Markets','St. Nick of Time flyers are historical and duplicated. Current December 2026 closure notices override older apply-now language. Private venue hire is not vendor intake.'),
 ('M.I.N.E.','Durham','https://www.eventeny.com/events/krampusmarket-24719/','Krampus Market','The pictured event is December 13, 2025 and ended. Monitor the organizer for a fresh edition; never roll its year forward.'),
 ('GRL Market','Raleigh',GRL,'GRL Market','Track venue-specific dates and the reviewed application hub; each venue has different booth and food rules.'),
 ('North Hills','Raleigh','https://www.visitnorthhills.com/signature-events/midtown-makers-market','Midtown Makers Market','Distinct from Midtown Farmers Market. The linked Manage My Market login is not proof of current dates or fees inside the application.'),
 ('Grasshopper Farms','Knightdale','https://www.grasshopperfarmsnc.com/special-events','Grasshopper Farms Makers Market','Follow the Makers Markets page and its real vendor form. Attendee tickets and kids-market fees do not prove adult booth prices.'),
 ('Unhinged Coffee & Co.','Knightdale','https://www.unhingedcoffee.co/','Unhinged Markets','Follow the specifically labeled Vendor Interest Form. Ignore employment, crochet classes and other attendee registrations.'),
)
VENUES={
 'waverly':dict(slug='grl-market-at-waverly-place',name='GRL Market at Waverly Place',city='Cary',match=r'WAVERLY',venue='Waverly Place, 302 Colonades Way, Cary, NC'),
 'transfer':dict(slug='grl-market-at-transfer-food-hall',name='GRL Market at Transfer Food Hall',city='Raleigh',match=r'TRANSFER FOOD HALL',venue='Transfer Food Hall, 500 E Davie Street, Raleigh, NC'),
 'seaboard':dict(slug='grl-market-at-seaboard-station',name='GRL Market at Seaboard Station',city='Raleigh',match=r'SEABOARD STATION',venue='Seaboard Station, 20 Seaboard Avenue, Raleigh, NC'),
}

def monitoring_leads():
 return [dict(organizer=org,city=city,source_url=url,target_url=url,title=title,notes=note) for org,city,url,title,note in WATCHLIST]

def monday_url(url):
 p=urlparse(url)
 return (p.scheme=='https' and p.hostname=='forms.monday.com' and not p.username and not p.password
  and p.port in (None,443) and not p.fragment and re.fullmatch(r'/forms/[a-f0-9]{32}',p.path)
  and p.query in ('','r=use1'))

def read_monday(doc,url):
 """Decode a bounded JSON value already shipped in the public form HTML."""
 if not monday_url(url):raise Uncertain('Not an approved public WorkForm URL.')
 if re.search(r'(?:this form|applications?) (?:is |are |have )?(?:closed|deactivated|no longer accepting)',visible_text(doc.root),re.I):
  return dict(closed=True,title='',text=visible_text(doc.root),options=[])
 scripts=[''.join(child for child in n.children if isinstance(child,str)) for n in doc.root.walk() if n.tag=='script']
 matches=[]
 for script in scripts:
  match=re.search(r'\bwindow\.form_data\s*=\s*',script)
  if match:
   try:value,_=json.JSONDecoder().raw_decode(script[match.end():]);matches.append(value)
   except (ValueError,TypeError):raise Uncertain('Public WorkForm data could not be decoded.')
 if len(matches)!=1 or not isinstance(matches[0],dict):raise Uncertain('Public WorkForm schema is unavailable; do not infer missing fields.')
 data=matches[0];settings=data.get('board_view_settings',{})
 if isinstance(settings,str):settings=json.loads(settings)
 if data.get('token')!=urlparse(url).path.rsplit('/',1)[-1] or not isinstance(settings,dict):raise Uncertain('WorkForm identity changed.')
 if settings.get('restrictByDate') or any(data.get(k) or settings.get(k) for k in ('is_closed','is_disabled','deactivated','requireLogin','passwordProtected')):
  raise Uncertain('WorkForm access or date restrictions require review.')
 fields=settings.get('columns',{});columns=data.get('included_columns',[])
 if not isinstance(fields,dict) or not isinstance(columns,list) or not all(isinstance(c,dict) for c in columns):raise Uncertain('WorkForm public questions are missing.')
 title=settings.get('formTitle','');welcome=settings.get('welcomeViewDescription','');description=settings.get('formDescription','')
 if not all(isinstance(v,str) for v in (title,welcome,description)):raise Uncertain('WorkForm public text has changed format.')
 html='<h1>'+escape(title)+'</h1><section>'+welcome+description+'</section>'
 options=[];questions=[]
 for column in columns:
  field=fields.get(column.get('id'),{})
  if field.get('visible') is not True:continue
  question=field.get('question') or column.get('title','');questions.append(question)
  html+='<section><h2>'+escape(question)+'</h2>'+str(field.get('description') or '')+'</section>'
  if re.fullmatch(r'categories|vendor categor(?:y|ies)',question.strip(),re.I):
   labels=column.get('settings',{}).get('labels',[])
   disabled=column.get('settings',{}).get('deactivated_labels',[])
   options=[label['name'] for label in labels if isinstance(label,dict) and isinstance(label.get('name'),str) and label.get('id') not in disabled]
   html+='<fieldset><legend>Which category best fits your work</legend>'+''.join('<label>'+escape(label)+'</label>' for label in options)+'</fieldset>'
 html+='<button type="submit">Submit</button>'
 rendered=Document(html);text=visible_text(rendered.root)
 if re.search(r'applications? (?:are |have )?closed|no longer accepting|form (?:is )?(?:closed|deactivated)',text,re.I):return dict(closed=True,title=title,text=text,options=options)
 if not all(any(re.search(pattern,q,re.I) for q in questions) for pattern in ('business name','vendor email','business description')) or len(options)<2:
  raise Uncertain('The page is not a complete public vendor application.')
 return dict(closed=False,title=title,text=text,options=options,document=rendered)

def grl_results(fetcher,now=None):
 now=now or datetime.now(timezone.utc);today=now.astimezone(ZoneInfo('America/New_York')).date()
 source,source_hash=fetcher.get(GRL)
 text=visible_text(source.root)
 years=set(re.findall(r'\b(20\d{2})\s+MARKETS\b',text,re.I))
 if len(years)!=1:raise Uncertain('The organizer calendar does not identify one current market year.')
 year=int(next(iter(years)));results=[];notes=[];seen=set()
 try:
  hub,hub_hash=fetcher.get(GRL_HUB)
  links=[(node.text(),node.attrs['href']) for node in hub.root.walk() if node.tag=='a' and node.attrs.get('href')]
  link_provenance=dict(method='live_official_hub',source_url=GRL_HUB,checked_at=now.isoformat(),source_hash=hub_hash)
 except (OSError,ValueError) as exc:
  notes.append({'market':'GRL Market','reason':'Official application hub unavailable; only previously reviewed exact-date links can be rechecked: '+str(exc)[:100]})
  links=[(label,url) for day,label,url in REVIEWED_APPS if date.fromisoformat(day).year==year and date.fromisoformat(day)>=today]
  hub_hash=REVIEWED_HUB_HASH
  link_provenance=dict(method='reviewed_official_hub',source_url=GRL_HUB,checked_at=REVIEWED_HUB_AT,source_hash=hub_hash)
 for label,href in links:
  match=re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?\b',label,re.I)
  venue=next((v for v in VENUES.values() if re.search(v['match'],label,re.I)),None)
  if not match or not venue or not re.search(r'vendor app',label,re.I):continue
  day=datetime.strptime(f'{match[1]} {match[2]} {year}','%B %d %Y').date()
  if day<today:continue
  # A current hub label alone cannot establish the year or venue date.
  month_day=re.escape(str(day.month))+'/'+str(day.day)
  if not re.search(r'(?<!\d)'+month_day+r'(?!\d).{0,80}'+venue['match'],text,re.I):
   notes.append({'market':venue['name'],'reason':'Application date is not corroborated by the current official calendar.'});continue
  app=urljoin(GRL_HUB,href)
  if urlparse(app).hostname=='wkf.ms':
   # The reviewed public shortcut for this venue resolves to this WorkForm.
   # New shortcut IDs are retained for review, never guessed or auto-trusted.
   app={'https://wkf.ms/4zS6ipN':'https://forms.monday.com/forms/c15a0d4bf1c2aa9a179696aa59ed2a59?r=use1'}.get(app,'')
  if not monday_url(app):continue
  reviewed_day=next((date.fromisoformat(d) for d,_,url in REVIEWED_APPS if url==app),None)
  if reviewed_day is not None and day!=reviewed_day:
   notes.append({'market':venue['name'],'reason':'A previously reviewed application cannot be reused for a different event date or year.'});continue
  if (app,day) in seen:continue
  seen.add((app,day))
  try:
   doc,digest=fetcher.get(app);form=read_monday(doc,app)
   if form.get('closed'):
    candidate=dict(market_slug=venue['slug'],market_name=venue['name'],organizer='GRL Market',city=venue['city'],state='NC',title=venue['name'],venue=venue['venue'],starts_on=day.isoformat(),ends_on=day.isoformat(),schedule_type='dated_event',source_url=GRL,application_url=app,deadline=None,booth_fee=None,application_fee=None,deposit=None,categories=[],availability='closed',eligibility='The currently linked vendor application explicitly reports closed intake. Previously published fees and category evidence are retained for reference; new vendor spaces are not confirmed.',fee_notes='The currently linked vendor application reports closed intake. Previously verified fee details, if any, are preserved.',research_notes='A current, official-source-linked application reports closed intake. This can close an existing automated listing but cannot create a new opportunity.')
    results.append(dict(policy=POLICY,decision='publish',candidate=candidate,checked_at=now.isoformat(),source_hash=source_hash,form_hash=digest,hub_hash=hub_hash,link_provenance=link_provenance,category_evidence={},evidence='The current organizer calendar and reviewed official application association identify this exact event and application. The live application explicitly reports closed intake; only an existing automated opportunity may be closed by this observation.'))
    continue
   if not re.search(venue['match'],form['title'],re.I) or not re.search(r'\b'+re.escape(match[1])+r'\s+'+str(day.day)+r'(?:st|nd|rd|th)?\b',form['title'],re.I):raise Uncertain('Application date or venue does not match the live calendar.')
   fee=re.search(r'standard vendor fee.{0,100}?\bis\s*\$([0-9]+(?:\.[0-9]{1,2})?)',form['text'],re.I)
   if not fee:raise Uncertain('A current application-specific booth price was not found.')
   setup='one 6 ft table' if venue is VENUES['transfer'] else 'a 10 x 10 ft tent and table'
   requirements=f'Bring {setup}, decor and payment equipment. Arrive one hour before the market and remain for its full duration. Product approval and category capacity are subject to organizer selection.'
   options=form['options'];mapping={'Handmade Crafts':r'crochet|pottery|sticker','Jewelry & Accessories':r'jewelry','Clothing & Vintage':r'clothing|headwear','Bath, Body & Beauty':r'body care|skincare','Art & Photography':r'^art$','Food & Beverages':r'baked goods|lemonade|hot dog|coffee|tea|food product','Services':r'tooth gems|bouquet bar'}
   categories={};stamp=now.isoformat()
   for category,pattern in mapping.items():
    choices=[v for v in options if re.search(pattern,v,re.I)]
    if choices:categories[category]=evidence('eligible','Only these listed products are supported. Other products, product-specific restrictions and remaining space require organizer review.',app,digest,', '.join(choices),source_terms=choices)
   if venue is VENUES['transfer']:
    faq,faq_hash=fetcher.get('https://grlmarket.com/faq')
    if re.search(r'Transfer Food Hall.{0,100}No food vendors',visible_text(faq.root),re.I):
     categories['Food & Beverages']=evidence('unavailable','The organizer FAQ says no food vendors at Transfer Food Hall.', 'https://grlmarket.com/faq',faq_hash,'Transfer Food Hall: No food vendors')
     requirements+=' The FAQ excludes food vendors at this venue. The form contains conflicting indoor/outdoor wording; confirm the assigned setup with the organizer.'
   elif venue is VENUES['waverly']:
    requirements+=' Coffee and matcha pop-up bars are explicitly excluded; the form separately lists baked goods and lemonade. Calendar and form list different end times; confirm event hours.'
   candidate=dict(market_slug=venue['slug'],market_name=venue['name'],organizer='GRL Market',city=venue['city'],state='NC',title=venue['name'],venue=venue['venue'],starts_on=day.isoformat(),ends_on=day.isoformat(),schedule_type='dated_event',source_url=GRL,application_url=app,deadline=None,booth_fee=float(fee[1]),application_fee=None,deposit=None,categories=sorted(c for c,e in categories.items() if e['status']=='eligible'),availability='open',eligibility=requirements,fee_notes=f'Standard space: ${float(fee[1]):g} for {setup}. Vendor fees are non-refundable and due within three days of approval. No separate application fee, deposit or application cutoff is verified.',research_notes='Current calendar year, exact public application date/venue, published questions, category choices and welcome-page fee verified. No application was filled in or submitted.')
   results.append(dict(policy=POLICY,decision='publish',form_state='public_questions_visible',candidate=candidate,checked_at=stamp,source_hash=source_hash,form_hash=digest,hub_hash=hub_hash,link_provenance=link_provenance,category_evidence={'application_url':app,'checked_at':stamp,'categories':categories},evidence='The live official calendar supplies the year and venue date. A reviewed official hub association identifies this exact event application. The live form, welcome terms, fee, questions and category choices were verified without submitting any data.'))
  except (ValueError,OSError) as exc:notes.append({'market':venue['name'],'reason':str(exc)[:160]})
 return results,notes

def discover_independent(fetcher,now=None):
 if not callable(getattr(fetcher,'get',None)):return [],[]
 try:return grl_results(fetcher,now)
 except (ValueError,OSError,AttributeError,TypeError) as exc:return [],[{'market':'GRL Market','reason':str(exc)[:160]}]

def catalog_additions():
 result={}
 for key,v in VENUES.items():
  place={'waverly':'Waverly Place','transfer':'Transfer Food Hall','seaboard':'Seaboard Station'}[key]
  result['grl-'+key]=dict(slug=v['slug'],name=v['name'],city=v['city'],organizer='GRL Market',source=GRL,
   description=f"{v['name']} is a curated vendor market in {v['city']}, North Carolina, featuring local small businesses. Event dates, product eligibility and application requirements vary by edition.",
   signals=(r'GRL Market',place,v['city']))
 definitions=(
  ('grasshopper-makers','grasshopper-farms-makers-market','Grasshopper Farms Makers Market','Knightdale','Grasshopper Farms','https://www.grasshopperfarmsnc.com/special-events','Grasshopper Farms hosts makers markets at its Poole Road farm in Knightdale. Dates include daytime, night and youth-focused editions; participation requirements vary by event.',(r'Grasshopper Farms',r'Makers Market',r'Knightdale')),
  ('midtown-makers','midtown-makers-market','Midtown Makers Market','Raleigh','North Hills','https://www.visitnorthhills.com/signature-events/midtown-makers-market','Midtown Makers Market is an evening market in the North Hills Innovation District in Raleigh featuring local makers, artisans and small businesses. Dates and vendor requirements vary by season.',(r'Midtown Makers Market',r'North Hills Innovation District',r'Raleigh')),
  ('hartwell-markets','hartwell-makers-markets','Hartwell Makers Markets','Raleigh','Hartwell','https://www.hartwellraleigh.com/retail-markets','Hartwell hosts curated makers markets and seasonal vendor events on West South Street in Raleigh. Dates, themes and vendor application windows vary by edition.',(r'Hartwell',r'Raleigh',r'monthly markets')),
  ('unhinged-markets','unhinged-markets','Unhinged Markets','Knightdale','Unhinged Coffee & Co.','https://www.unhingedcoffee.co/','Unhinged Coffee & Co. hosts local vendor markets at its First Avenue location in Knightdale. Event dates, themes and vendor requirements vary by edition.',(r'Unhinged',r'Knightdale',r'vendor market')),
  ('krampus-durham','krampus-market-durham','Krampus Market','Durham','M.I.N.E. and Trailer Park Fantasy','https://www.eventeny.com/events/krampusmarket-24719/','Krampus Market is an adult-oriented holiday vendor market at Durham Central Park organized by M.I.N.E. and Trailer Park Fantasy. The documented 2025 edition was an 18-and-over event. Future dates and participation requirements require organizer confirmation.',(r'Krampus Market',r'Durham',r'2025',r'M.I.N.E')),
 )
 for key,slug,name,city,org,source,description,signals in definitions:
  result[key]=dict(slug=slug,name=name,city=city,organizer=org,source=source,description=description,signals=signals)
 return result

"""Source-scoped category facts. Missing categories are never exclusions.

Only call after the existing verifier has confirmed the event/application pair.
Category keys are our search groups, not organizer labels or blanket product
approval. Preserve exact enabled choices/phrases and never infer drinks or
food-truck eligibility from food-only evidence.
This module never submits forms or decides if a vendor's individual products
will be accepted. All evidence is partial and refreshed on each successful run.
"""
from __future__ import annotations
import re
from datetime import timezone
from urllib.parse import urljoin, urlparse, parse_qs

CATEGORIES = ('Food & Beverages', 'Food Trucks', 'Art & Photography',
 'Handmade Crafts', 'Jewelry & Accessories', 'Clothing & Vintage',
 'Bath, Body & Beauty', 'Plants & Farm Products', 'Pet Products', 'Services', 'Other')
PATTERNS = {
 'Food & Beverages': r'\b(?:food\s*(?:and|&)\s*(?:art|beverage)s?\s+vendors?|food vendors?|beverage vendors?|baked goods|savory food items|prepackaged (?:food|items)|packaged food)\b',
 'Art & Photography': r'\b(?:original (?:art|artwork)|photograph(?:y|ers)|art vendors?|artists)\b',
 'Handmade Crafts': r'\b(?:handmade|craft vendors?|crafters)\b',
 'Jewelry & Accessories': r'\b(?:jewel(?:ry|lery|ers)|accessories vendors)\b',
 'Clothing & Vintage': r'\b(?:vintage (?:goods|clothing)|apparel|t-shirts|clothing vendors?)\b',
 'Bath, Body & Beauty': r'\b(?:soaps?|bath\s*(?:and|&|\+)\s*body|bath products)\b',
 'Plants & Farm Products': r'\b(?:plant vendors?|farm products|farm produce|locally grown produce)\b',
 'Pet Products': r'\b(?:pet products|pet treats|pet accessories)\b',
 'Services': r'\b(?:unique services|services/workshop|face painting|fairy hair|henna|tarot)\b',
}
BLOCKED_TAGS={'script','style','noscript','nav','header','footer','aside'}

def blocked(node):
 attrs=node.attrs;style=attrs.get('style','').replace(' ','').lower()
 return node.tag in BLOCKED_TAGS or 'hidden' in attrs or 'disabled' in attrs or attrs.get('aria-hidden')=='true' or attrs.get('aria-disabled')=='true' or 'display:none' in style or 'visibility:hidden' in style

def visible_text(node):
 if blocked(node):return ''
 return ' '.join(' '.join(visible_text(x) if hasattr(x,'tag') else x for x in node.children).split())

def nodes_with_parents(root,parents=()):
 if blocked(root):return
 yield root,parents
 for child in root.children:
  if hasattr(child,'tag'):yield from nodes_with_parents(child,parents+(root,))

def sections(doc,names):
 """Collect visible section prose across layout wrappers until the next heading."""
 result=[];parts=[];active=False
 def visit(node):
  nonlocal active,parts
  if blocked(node):return
  if node.tag in {'h1','h2','h3','h4','h5','h6'}:
   if active and parts:result.append(' '.join(' '.join(parts).split()))
   parts=[];active=visible_text(node).lower().strip(' :') in names
   return
  for child in node.children:
   if hasattr(child,'tag'):visit(child)
   elif active:parts.append(child)
 visit(doc.root)
 if active and parts:result.append(' '.join(' '.join(parts).split()))
 return [text for text in result if text]

def question_options(doc):
 options=[]
 for node,parents in nodes_with_parents(doc.root):
  if node.tag not in {'label','legend','h2','h3'} and not (node.tag=='span' and 'form-label' in node.attrs.get('class','').split()):continue
  label=re.sub(r'[^a-z]','',visible_text(node).lower())
  if label not in {'whichcategorybestfitsyourwork','pleasechooseyourmediumcategory','chooseyourmediumcategory'}:continue
  for ancestor in reversed(parents):
   if ancestor.tag in {'li','fieldset'} or 'form-line' in ancestor.attrs.get('class','').split():
    for option,_ in nodes_with_parents(ancestor):
     if option.tag=='option' or (option.tag=='label' and option is not node):
      value=visible_text(option)
      if value and value.lower() not in {'select','please select','select an option'}:options.append(value)
     elif option.tag=='input' and option.attrs.get('type') in {'radio','checkbox'}:
      # Jotform's visible, enabled inputs carry the authoritative option
      # values even when duplicate visual labels are aria-hidden.
      value=option.attrs.get('value','').strip()
      if value:options.append(value)
    break
 return list(dict.fromkeys(options))

def app_id(url):
 p=urlparse(url)
 return parse_qs(p.query).get('id',[''])[0] if p.hostname in {'eventeny.com','www.eventeny.com'} and p.path.rstrip('/')=='/events/vendor' else None

def evidence(status,note,url,digest,excerpt,source_terms=()):
 terms=[]
 for term in source_terms:
  term=' '.join(term.split())
  if not term or len(term)>180 or term in terms:continue
  if len(terms)>=10 or len(' · '.join(terms+[term]))>300:break
  terms.append(term)
 result={'status':status,'note':note,'source_url':url,'source_hash':digest,'excerpt':' '.join(excerpt.split())[:320]}
 if terms:
  # Keep every quoted term in the bounded evidence excerpt as well. A label
  # synthesized from our taxonomy must never be substituted for source words.
  result.update(source_terms=terms,excerpt=' · '.join(terms) if len(' · '.join(terms))>=8 else result['excerpt'])
 return result

def research_categories(event_doc,app_doc,source_url,app_url,now,source_hash,app_hash,supplements=()):
 found={};conflicts=[]
 def record(category,status,note,url,digest,text,scope,terms=()):
  prior=found.get(category)
  if prior and prior[0]==scope and prior[1]['status']!=status:
   conflicts.append(category);return
  # Application-specific restrictions outrank an event's general description.
  if prior and prior[0]>scope:return
  if prior and prior[0]==scope and prior[1]['status']==status and prior[1]['source_url']==url:
   terms=prior[1].get('source_terms',[])+list(terms)
  found[category]=(scope,evidence(status,note,url,digest,text,terms))
 def positive(text,url,digest,scope,only=None,literal=False):
  for category,pattern in PATTERNS.items():
   if only and category not in only:continue
   for match in re.finditer(pattern,text,re.I):
    # Prohibitions require explicit wording, never absence from a list.
    before=text[max(0,match.start()-60):match.start()]
    after=text[match.end():match.end()+60]
    negative=(re.search(r'\b(?:no|not accepting|do not accept|not permitted|not allowed|without)\s+(?:any\s+)?$',before,re.I) or re.match(r'\s*(?:are |is |will be )?(?:not accepted|not permitted|not allowed|excluded)\b',after,re.I))
    if negative:
     if scope>=3:record(category,'excluded','The application explicitly excludes this category.',url,digest,text,scope)
     continue
    note='The source mentions these products. Other products in this search group and remaining space are unconfirmed.'
    if category=='Food & Beverages':note='Only the listed food or drink types are supported. Freshly prepared drinks and other products are not confirmed unless explicitly listed.'
    record(category,'eligible',note,url,digest,text[max(0,match.start()-80):match.end()+200],scope,[text if literal else match[0]])
  # A category question explicitly scopes these short options to vendors.
  # The same words in attendee/event prose must not establish vendor intake.
  if literal and re.search(r'\b(?:beverages?|drinks?|lemonade|coffee|tea|matcha|smoothies|juices?)\b',text,re.I):
   match=re.search(r'\b(?:beverages?|drinks?|lemonade|coffee|tea|matcha|smoothies|juices?)\b',text,re.I)
   before=text[:match.start()];after=text[match.end():]
   if not (re.search(r'\b(?:no|not accepting|do not accept|without)\s*$',before,re.I) or re.match(r'\s*(?:are |is )?(?:not allowed|not accepted|not permitted)\b',after,re.I)):
    record('Food & Beverages','eligible','Only the listed food or drink types are supported. Other products and setups are unconfirmed.',url,digest,text,scope,[text])
 # Typed event metadata was already identity/date-validated by the caller.
 for event in event_doc.events():
  if isinstance(event.get('description'),str):positive(event['description'],source_url,source_hash,1)
 for text in sections(event_doc,{'about the event'}):positive(text,source_url,source_hash,1)
 application_sections=sections(app_doc,{'about the application'})
 for text in application_sections:positive(text,app_url,app_hash,3)
 options=question_options(app_doc)
 for text in options:
  positive(text,app_url,app_hash,3,literal=True)
  if text.lower().strip()=='other':record('Other','eligible','Other is an application option for organizer review; it does not confirm eligibility for any particular product.',app_url,app_hash,text+' is an explicit category option on the organizer application.',3,[text])
  if re.search(r'food trucks?|food trailers?',text,re.I):record('Food Trucks','eligible','The form lists trucks/trailers; confirm setup, fees, and availability.',app_url,app_hash,text+' is an explicit category option on the organizer application.',3,[text])
 # Negatives require application prose or a category-labelled price row.
 for text in application_sections:
  for category,pattern in [('Food Trucks',r'\b(?:no|not accepting|do not accept) food trucks?\b'),('Food & Beverages',r'\b(?:no|not accepting|do not accept) (?:food(?:\s*(?:and|&)\s*beverage)?|beverage) vendors?\b')]:
   match=re.search(pattern,text,re.I)
   if match:record(category,'excluded','The application explicitly excludes this category.',app_url,app_hash,match.group(0)+' in the organizer application requirements.',3)
 for title,text in price_rows(app_doc):
  # The option name carries its category. Descriptions carry conditions, not
  # additional categories (e.g. a sponsor package mentioning food trucks).
  categories=[c for c,pattern in PATTERNS.items() if re.search(pattern,title,re.I)]
  if re.search(r'food trucks?|food trailers?',title,re.I):categories.append('Food Trucks')
  for category in categories:
   unavailable=bool(re.search(r'\b(sold out|unavailable|fully booked|waitlist)\b',text,re.I))
   conditional=bool(re.search(r'only choose.*discussed|prior (?:approval|discussion)|pre.?approval',text,re.I))
   amount=re.search(r'\$\s*[\d,]+(?:\.\d{1,2})?',text)
   note=('The application lists this product/setup option'+(' at '+amount[0] if amount else '')+'. ')
   note+=(('This option is waitlisted; check with the organizer.' if re.search(r'waitlist',text,re.I) else 'This option is marked unavailable.') if unavailable else 'Prior organizer discussion is required before selecting this option.' if conditional else 'Confirm product approval and remaining availability with the organizer.')
   record(category,'unavailable' if unavailable else 'eligible',note,app_url,app_hash,text,4 if unavailable else 3,[title])
 for doc,url,digest,kind in supplements:
  if kind=='organizer_event':
   # Caller checks exact official-market identity and its outgoing application.
   main=next((n for n,_ in nodes_with_parents(doc.root) if n.tag=='main'),doc.root)
   positive(visible_text(main),url,digest,1)
  elif kind=='organizer_criteria':
   # Only scope a generic criteria page to the category it actually supports.
   texts=sections(doc,{'here are a few things we look for when reviewing applications'})
   for text in texts:positive(text,url,digest,1,only={'Handmade Crafts'})
 # Another active dated application is a route, not acceptance into this one.
 cards=[n for n,_ in nodes_with_parents(event_doc.root) if 'app-card' in n.attrs.get('class','').split()]
 for card in cards:
  for link,_ in nodes_with_parents(card):
   if link.tag=='a' and re.search(r'food trucks?',visible_text(link),re.I):
    other=urljoin(source_url,link.attrs.get('href',''))
    if app_id(other) and app_id(other)!=app_id(app_url) and any(n.tag in {'a','button-element'} and visible_text(n).lower() in {'apply now','join waitlist','apply to waitlist'} for n,_ in nodes_with_parents(card)):
     if not found.get('Food Trucks') or found['Food Trucks'][0]<3:record('Food Trucks','separate_application','A separate food-truck application is linked; its current availability is unconfirmed. Check its fees and deadline.',source_url,source_hash,visible_text(card),2)
 categories={key:value[1] for key,value in found.items() if key not in conflicts}
 return {'application_url':app_url,'checked_at':now.astimezone(timezone.utc).isoformat(),'categories':categories},sorted(set(conflicts))


def price_rows(doc):
 """Published option rows with a price or explicit unavailability."""
 for node,_ in nodes_with_parents(doc.root):
  if node.tag!='tr':continue
  cells=[visible_text(n) for n in node.children if hasattr(n,'tag') and n.tag in {'td','th'}]
  if len(cells)<2 or not re.search(r'\$\s*[\d,]+|\bsold out\b|\bunavailable\b|\bfully booked\b|\bwaitlist\b',' '.join(cells[1:]),re.I):continue
  yield cells[0], ' '.join(cells)


def application_facts(doc):
 """Read each option independently and retain its conditions, never a total."""
 prices=[];standard=[];standard_unavailable=False;amount_fields={"application_fee":set(),"deposit":set()};amount_conflict=False
 for node,_ in nodes_with_parents(doc.root):
  if node.tag!='tr':continue
  cells=[visible_text(n) for n in node.children if hasattr(n,'tag') and n.tag in {'td','th'}]
  if len(cells)<2:continue
  title=cells[0];text=' '.join(cells)
  if not re.search(r'\$\s*[\d,]+|\bsold out\b|\bunavailable\b|\bfully booked\b|\bwaitlist\b',' '.join(cells[1:]),re.I):continue
  is_standard=bool(re.fullmatch(r'(?:10\s*[x×]\s*10 (?:space|booth)|vendor booth|vendor space|full table)',title.strip(),re.I))
  unavailable=bool(re.search(r'\b(sold out|unavailable|fully booked|waitlist)\b',text,re.I))
  # Amount must come from the price cell, never a description's group rate.
  amount=re.search(r'\$\s*([\d,]+(?:\.\d{1,2})?)',cells[1])
  value=float(amount[1].replace(',','')) if amount else None
  condition='; prior organizer discussion required' if re.search(r'only choose.*discussed|prior (?:approval|discussion)|pre.?approval',text,re.I) else ''
  price=f'${value:,.2f}' if value is not None else 'price not published'
  if unavailable:price+='; '+('waitlist only' if re.search(r'waitlist',text,re.I) else 'marked unavailable')
  prices.append(f'{title}: {price}'+condition+'.')
  # Preserve special tier/bundle/refund qualifiers in the source description.
  description=' '.join(cells[2:])
  if description and re.search(r'\$|only choose|prior (?:approval|discussion)|pre.?approval|minimum|all \d+|per event',description,re.I):prices.append(f'{title} terms: {description}')
  for key,pattern in [('application_fee',r'application fee'),('deposit',r'(?:refundable |security )?deposit')]:
   if re.fullmatch(pattern,title.strip(),re.I) and not unavailable and value is not None:amount_fields[key].add(value)
  if value is not None and not 0<=value<=10000:amount_conflict=True
  if is_standard:
   if unavailable:standard_unavailable=True
   elif value is not None:standard.append(value)
 text=' '.join(sections(doc,{'about the application','terms & conditions','additional information','picture requirements'}))
 requirements=[]
 for pattern,message in [
  (r'no\s+mlm|no\s+multi.level.marketing','No MLM businesses.'),
  (r'bring your own 10\s*[x×]\s*10 tent','Bring your own 10×10 tent for the 10×10 vendor option.'),
  (r'4\s*[-–]\s*20\s*lb (?:bagged )?tent weights|20lb bagged tent weights per corner','Four 20 lb bagged tent weights are required.'),
  (r'must be sand filled bags|sand bag tent weights filled with rocks or sand','The application specifies filled, bagged tent weights; check its material requirements.'),
  (r'no circular weights','Circular tent weights are not allowed.'),
  (r'fees? will be due when accepted','Vendor and platform fees are due upon acceptance.'),
  (r'no refunds|no refund or market credit','The application says no refunds or market credits; check organizer cancellation exceptions.'),
  (r'cancel.{0,160}75% refund','The organizer states a 75% refund if it cancels due to unforeseen circumstances.'),
  (r'electricity is needed.*special request','Electricity requires a special request and an additional fee.'),
  (r'rain or shine','The event is rain or shine.'),
  (r'not a THC/CBD Vendor or Mobile Boutique','THC/CBD vendors and mobile boutiques are excluded from this application.'),
  (r'at least 3 photos of your products, 1 photo of your booth set up, and 1 photo of your tent weights','Include at least three product photos, one booth setup photo, and one tent-weight photo.'),
 ]:
  if re.search(pattern,text,re.I):requirements.append(message)
 if re.search(r'(?:^|[.!?])\s*(?:There is )?no application fee\s*[.!?]',text,re.I):amount_fields['application_fee'].add(0)
 amount_conflict=amount_conflict or any(len(values)>1 for values in amount_fields.values())
 fee_notes=' '.join(prices);rules=' '.join(requirements)
 return {'standard_fee':standard[0] if len(set(standard))==1 and not standard_unavailable else None,
         'standard_unavailable':standard_unavailable,'standard_conflict':len(set(standard))>1 or amount_conflict,
         **{key:next(iter(values)) if len(values)==1 and 0<=next(iter(values))<=10000 else None for key,values in amount_fields.items()},
         'overflow':len(fee_notes)>1800 or len(rules)>1600,
         'fee_notes':fee_notes if len(fee_notes)<=1800 else '', 'requirements':rules if len(rules)<=1600 else ''}


def availability_text(doc):
 """Overall application status excludes structured option-price rows only.

A nonprofit/sponsor row marked sold out is not a closure of the whole form.
Unscoped closure text elsewhere remains authoritative or review-worthy.
"""
 def visit(node):
  if blocked(node):return ''
  if node.tag=='tr':
   cells=[visible_text(n) for n in node.children if hasattr(n,'tag') and n.tag in {'td','th'}]
   if len(cells)>=2 and not re.fullmatch(r'(?:applications?|application status|application availability|status|availability|all (?:applications|booths|vendors))',cells[0].strip(),re.I) and re.search(r'\$\s*[\d,]+|\bsold out\b|\bunavailable\b|\bfully booked\b|\bwaitlist\b',' '.join(cells[1:]),re.I):return ''
  return ' '.join(visit(x) if hasattr(x,'tag') else x for x in node.children)
 return ' '.join(visit(doc.root if hasattr(doc,'root') else doc).split())

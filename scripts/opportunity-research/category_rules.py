"""Source-scoped category facts. Missing categories are never exclusions.

Only call after the existing verifier has confirmed the event/application pair.
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
 """Visible prose following exact headings, not a footer or vendor directory."""
 result=[]
 for parent,_ in nodes_with_parents(doc.root):
  for index,child in enumerate(parent.children):
   if not hasattr(child,'tag') or child.tag not in {'h1','h2','h3','h4'} or visible_text(child).lower().strip(' :') not in names:continue
   prose=[]
   for sibling in parent.children[index+1:]:
    if hasattr(sibling,'tag') and sibling.tag in {'h1','h2','h3','h4'}:break
    text=visible_text(sibling) if hasattr(sibling,'tag') else sibling
    if text:prose.append(text)
   value=' '.join(prose)
   if value:result.append(value)
 return result

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

def evidence(status,note,url,digest,excerpt):
 return {'status':status,'note':note,'source_url':url,'source_hash':digest,'excerpt':' '.join(excerpt.split())[:320]}

def research_categories(event_doc,app_doc,source_url,app_url,now,source_hash,app_hash,supplements=()):
 found={};conflicts=[]
 def record(category,status,note,url,digest,text,scope):
  prior=found.get(category)
  if prior and prior[0]==scope and prior[1]['status']!=status:
   conflicts.append(category);return
  # Application-specific restrictions outrank an event's general description.
  if prior and prior[0]>scope:return
  found[category]=(scope,evidence(status,note,url,digest,text))
 def positive(text,url,digest,scope,only=None):
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
    note='The organizer lists this type; product approval and space are still subject to review.'
    if category=='Food & Beverages' and re.search(r'baked goods|prepackaged|packaged food|savory food',text,re.I):note='Baked/savory or packaged foods are listed; ask about freshly prepared drinks.'
    record(category,'eligible',note,url,digest,text,scope)
 # Typed event metadata was already identity/date-validated by the caller.
 for event in event_doc.events():
  if isinstance(event.get('description'),str):positive(event['description'],source_url,source_hash,1)
 for text in sections(event_doc,{'about the event'}):positive(text,source_url,source_hash,1)
 application_sections=sections(app_doc,{'about the application'})
 for text in application_sections:positive(text,app_url,app_hash,3)
 options=question_options(app_doc)
 for text in options:
  positive(text,app_url,app_hash,3)
  if text.lower().strip()=='other':record('Other','eligible','Describe other products for organizer consideration.',app_url,app_hash,text+' is an explicit category option on the organizer application.',3)
  if re.search(r'food trucks?|food trailers?',text,re.I):record('Food Trucks','eligible','The form lists trucks/trailers; confirm setup, fees, and availability.',app_url,app_hash,text+' is an explicit category option on the organizer application.',3)
 # Negatives require application prose or a category-labelled price row.
 for text in application_sections:
  for category,pattern in [('Food Trucks',r'\b(?:no|not accepting|do not accept) food trucks?\b'),('Food & Beverages',r'\b(?:no|not accepting|do not accept) (?:food(?:\s*(?:and|&)\s*beverage)?|beverage) vendors?\b')]:
   match=re.search(pattern,text,re.I)
   if match:record(category,'excluded','The application explicitly excludes this category.',app_url,app_hash,match.group(0)+' in the organizer application requirements.',3)
 for node,_ in nodes_with_parents(app_doc.root):
  if node.tag=='tr':
   text=visible_text(node)
   if re.search(r'\bfood trucks?\b',text,re.I) and re.search(r'\bsold out\b',text,re.I):record('Food Trucks','unavailable','Food-truck spaces are marked sold out on this application.',app_url,app_hash,text,4)
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
     if not found.get('Food Trucks') or found['Food Trucks'][0]<3:record('Food Trucks','separate_application','This event has a separate food-truck application with its own fees and deadline.',source_url,source_hash,visible_text(card),2)
 categories={key:value[1] for key,value in found.items() if key not in conflicts}
 return {'application_url':app_url,'checked_at':now.astimezone(timezone.utc).isoformat(),'categories':categories},sorted(set(conflicts))

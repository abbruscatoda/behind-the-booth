"""Organizer-bound First Night Raleigh adapter; no authenticated form scraping."""
import re
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from verifier import Uncertain,clean,norm,source_error
from category_rules import visible_text,nodes_with_parents
from google_forms import read_public_form

POLICY='artsplosure-google-v1'
SOURCE='https://www.artsplosure.org/first-night-raleigh'
SHORT='https://forms.gle/e8JRmQUUcEirUzzY9'
FORM='https://docs.google.com/forms/d/e/1FAIpQLScPXt0euH9ziXcAR3tA9BkXTQ4qtnTK9V6aqttIYbxlittBlA/viewform'

def handles(item):return item.get('application_url','').split('?')[0] in {SHORT,FORM}

def verify_first_night(item,fetcher,now):
 if not handles(item):raise Uncertain('Unsupported Google Form. An organizer-bound source adapter is required before automatic verification.')
 if norm(item.get('market_name') or item.get('title','')) not in {'firstnightraleigh','wralfirstnightraleigh'} or item.get('market_state') not in {None,'NC'} or (item.get('market_city') or 'Raleigh').lower()!='raleigh':
  raise Uncertain('First Night form does not match the linked Raleigh market profile.')
 doc,digest=fetcher.get(SOURCE);text=visible_text(doc.root)
 if SHORT not in doc.root.links(SOURCE) and FORM not in doc.root.links(SOURCE):raise Uncertain('Organizer no longer links the expected First Night application; review the replacement form.')
 date=re.findall(r'December\s+31,?\s+(20\d{2})',text,re.I)
 dates={year+'-12-31' for year in date}
 if dates!={item['starts_on']} or item['ends_on']!=item['starts_on']:raise Uncertain('Organizer event year/date differs from this occurrence; no fees copied across editions.')
 paragraphs=list(dict.fromkeys(clean(visible_text(n)) for n,_ in nodes_with_parents(doc.root) if n.tag=='p' and visible_text(n)))
 terms=[p for p in paragraphs if re.search(r'\b(?:application|deposit|vendor|checks will|paypal)\b',p,re.I) and not re.search(r'volunteer|accessibility|diversity|copyright',p,re.I)]
 # Only use an explicit clock and month/day, anchored to the verified event year.
 deadlines=set()
 for p in terms:
  for m in re.finditer(r'by\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s+on\s+([A-Za-z]+)\s+(\d{1,2})(?:,?\s+(20\d{2}))?',p,re.I):
   hour,minute,ampm,month,day,year=m.groups();year=year or item['starts_on'][:4]
   try:d=datetime.strptime(f'{month} {day} {year} {hour}:{minute} {ampm.upper()}','%B %d %Y %I:%M %p').replace(tzinfo=ZoneInfo('America/New_York'));deadlines.add(d.isoformat())
   except ValueError:pass
 cutoff=next(iter(deadlines)) if len(deadlines)==1 else None
 # Public page describes category-specific deposits, not a single universal fee.
 public_fees='\n'.join(p for p in terms if re.search(r'\$|deposit|paypal|checks will',p,re.I))
 public_rules='\n'.join(p for p in terms if re.search(r'photo|rules|reject|acceptance|notified|checks',p,re.I))
 notes=[];app=None;app_hash=None
 try:app,app_hash=fetcher.get(FORM);facts=read_public_form(app)
 except Exception as error:
  facts=None;notes.append(str(error) if isinstance(error,Uncertain) else 'Application could not be read by the public worker ('+source_error(error)+').')
 if facts:
  notes+=facts.get('issues',[])
  if facts['closed']:notes.append('The Google Form says it is no longer accepting responses; confirm closure with the organizer.')
  if not facts['complete']:notes.append('Google Form is incomplete, multi-page, or has no enabled Submit control; remaining sections need review.')
  apptext=' '.join(facts['blocks'])
  if 'firstnightraleigh' not in norm(apptext) or not re.search(r'December\s+31,?\s+'+item['starts_on'][:4],apptext,re.I):
   notes.append('Application event identity/date could not be verified; no application facts were copied.');facts=None
  # Preserve form-level terms first; public source adds independently sourced terms.
 def merge(a,b):return '\n'.join(dict.fromkeys(x for x in [a,b] if x))
 fee_notes=merge(facts['fee_notes'] if facts else '',public_fees)
 eligibility=merge(facts['eligibility'] if facts else '',public_rules)
 if len(fee_notes)>2000 or len(eligibility)>2000:notes.append('Combined published terms exceed field limits; full source review required.')
 # No unreviewed truncated terms are suggested into the editor.
 suggestions={k:v for k,v in {'deadline':cutoff,'fee_notes':fee_notes if len(fee_notes)<=2000 else None,'eligibility':eligibility if len(eligibility)<=2000 else None,
   **({k:facts[k] for k in ('booth_fee','application_fee','deposit')} if facts else {})}.items() if v is not None and v!=''}
 if not cutoff:notes.append('An exact application cutoff could not be verified.')
 # This adapter deliberately stages reviewed facts until a full Google form
 # fixture is captured. It never claims a gated/multi-page form is complete.
 reason=' '.join(notes) or 'Readable Google Form researched; confirm category eligibility and full application terms before publishing.'
 return {'decision':'review','policy':POLICY,'reason':reason,'checked_at':now.isoformat(),'source_hash':digest,'application_hash':app_hash,
  'evidence':'Public organizer page links this exact form and matches this event date.',
  'research_suggestions':{'application_url':item['application_url'],'starts_on':item['starts_on'],'ends_on':item['ends_on'],
   'source_url':SOURCE,'source_hash':digest,'checked_at':now.isoformat(),'fields':suggestions,
   'notes':reason,'form_readable':facts is not None,'complete':bool(facts and facts['complete'])}}

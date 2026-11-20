"""Bounded official-site survey of Explore Markets without opportunities.

This is evidence gathering, not authority to publish. Future vetted adapters
can convert repeated public intake evidence into verified opportunities.
"""
from datetime import datetime,timezone
from urllib.parse import urljoin
import re
from verifier import valid_url,clean
from category_rules import visible_text

INTAKE=re.compile(r'\b(?:vendor applications?|apply (?:to be|as) (?:a )?vendor|become a vendor|sell with us|vendor registration)\b',re.I)
ROLLING=re.compile(r'\b(?:year.round|rolling basis|apply any time|applications? (?:accepted|open) (?:all|year)|weekly call.for.vendors)\b',re.I)
CLOSED=re.compile(r'\b(?:vendor applications? (?:are |have )?closed|no longer accepting (?:vendor|new vendor) applications?)\b',re.I)
LINK=re.compile(r'\b(?:apply|application|register|registration|sell with us|become a vendor)\b',re.I)

def audit_missing_markets(rows,fetcher,now=None,limit=8):
 """Rotate bounded source probes to avoid ignoring later alphabetic markets."""
 now=now or datetime.now(timezone.utc)
 ordered=sorted((m for m in rows if isinstance(m,dict) and m.get('slug')),key=lambda m:m['slug'])
 if not ordered:return {'checked':0,'skipped':0,'signals':[]}
 start=now.date().toordinal()%len(ordered)
 selected=(ordered[start:]+ordered[:start])[:limit]
 signals=[];checked=0;skipped=0
 for market in selected:
  url=market.get('website_url','')
  if not valid_url(url):
   skipped+=1
   continue
  try:
   doc,_=fetcher.get(url)
  except Exception:
   signals.append({'slug':market['slug'],'state':'official_page_unreadable'})
   continue
  checked+=1
  text=visible_text(doc.root)
  links=[]
  for n in doc.root.walk():
   if n.tag!='a' or not n.attrs.get('href') or not LINK.search(clean(n.text())):continue
   target=urljoin(url,n.attrs['href'])
   if valid_url(target) and target!=url:links.append(target)
  state=('explicitly_closed' if CLOSED.search(text)
         else 'possible_rolling_intake' if INTAKE.search(text) and ROLLING.search(text) and links
         else 'application_link_needs_verification' if links
         else 'no_confirmed_application')
  signals.append({'slug':market['slug'],'state':state,'linked_applications':len(set(links))})
 return {'checked':checked,'skipped':skipped,'signals':signals}

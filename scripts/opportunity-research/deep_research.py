"""Read-only, source-bound diagnostics for unresolved Triangle vendor leads.

Explain why a lead cannot yet be published without claiming information the
worker did not actually verify. No form answers, accounts, submissions, cookies
or arbitrary out-of-allowlist URLs are accessed or stored.
"""
from __future__ import annotations
from collections import Counter
from urllib.parse import urlparse
from datetime import datetime,timezone
import re
from verifier import valid_url,source_error,Uncertain,clean
from category_rules import visible_text
from form_discovery import supported_form

APP_RE=re.compile(r'\b(?:apply|applications?|register|registration|be(?:come)? a vendor|guest vendors?|vendor opportunities?|vend with us)\b',re.I)
EXCLUDE_RE=re.compile(r'\b(volunteer|musician|teaching artist|sponsor|career|survey|event tickets?|donate|advertis(?:ing|ement))\b',re.I)
CLOSE_RE=re.compile(r'\b(?:applications?(?: for 20\d{2} (?:market )?season)? (?:are now |are |have )?(?:closed|ended)|(?:not currently|currently not|is not currently) accepting (?:(?:new|guest|vendor) )*applications?|no longer accepting (?:vendor )?applications?)\b',re.I)
RESTRICT_RE=re.compile(r'\b(?:only accepting applications.{0,130}(?:returning|invited)|returning vendors or those invited|invitation only|existing vendors only)\b',re.I)
ROLL_RE=re.compile(r'\b(?:applications (?:are )?accepted on a rolling basis|applications rolling|year.round applications|apply any time)\b',re.I)
SEASON_RE=re.compile(r'\b(?:accepting (?:vendor )?applications.{0,70}20\d{2} season|20\d{2} (?:vendor )?applications (?:are )?open|apply for (?:our|the) 20\d{2} season)\b',re.I)
GATE_RE=re.compile(r'\b(?:must sign in|sign in to continue|you need permission|request access|cannot access this form)\b',re.I)
DIRECTORY_PATHS={'applications','vendor-info','vendor-information','opportunities','vendor-opportunities'}
MULTI_RE=re.compile(r'\b(?:select (?:your |the )?(?:event )?dates?|choose (?:event )?dates?|multiple market dates|different (?:event )?dates|market series|Cary Night Market Dates|please only choose the markets)\b',re.I)

def diagnose_one(lead,fetcher,now=None,allow_target=True):
 target=lead.get('target_url','')
 source=lead.get('source_url','')
 name=clean(lead.get('title',''))[:160]
 def out(status,reason):return {'target_url':target,'source_url':source,'status':status,'reason':reason[:400]}
 if not valid_url(source):return out('source_unavailable','Organizer source is not an approved HTTPS research URL.')
 if target.rstrip('/#')==source.rstrip('/#') or target.endswith('/#'):
  return out('not_application','This link points to the organizer directory itself or a page anchor, not a distinct vendor application.')
 if EXCLUDE_RE.search(name) and not re.search(r'\bvendor\b',name,re.I):
  return out('not_application','The link is labeled for a non-vendor activity rather than a market booth application.')
 try:
  root,_=fetcher.get(source)
 except Exception as error:
  return out('source_unavailable','Official organizer page could not be read: '+source_error(error)+'.')
 if target not in root.root.links(source):
  return out('unlinked','The current official organizer page does not link this exact application; an old saved URL cannot establish current availability.')
 text=visible_text(root.root)
 linked_text=''
 doc=None
 if allow_target and valid_url(target):
  try:
   doc,_=fetcher.get(target)
   linked_text=visible_text(doc.root)
  except Exception as error:
   return out('source_unavailable','Linked organizer application or form could not be read: '+source_error(error)+'.')
 if doc is None:
  return out('needs_evidence','The linked target could not be examined as a supported public application URL; further official-source evidence is required.')
 # Classify the actual application type before concluding that a vendor
 # market is missing dates. Workshop enrollment and permanent retail
 # consignment are distinct programs, not event booth opportunities.
 if (re.search(r'\\b(?:workshop|master class|printing session)\\b',linked_text,re.I)
     and re.search(r'\\b(?:register|registration|participants?|printing day|master class)\\b',linked_text,re.I)
     and re.search(r'\\b(?:tuition|printing|woodblock|master class)\\b',linked_text,re.I)):
  return out('not_application','Not a vendor market: this is an instructional workshop registration, not an event booth application.')
 if (re.search(r'you are applying to have your products sold (?:in|at)',linked_text,re.I)
     and re.search(r'(?:at.will contract|no stated ending date|initial inventory|products sold in the store|products sold at the store)',linked_text,re.I)):
  return out('not_application','Not a vendor market: this is a permanent retail store placement or consignment application, not an event booth.')
 if not APP_RE.search(name) and not supported_form(target) and urlparse(target).path.strip('/').split('/')[-1].lower() not in DIRECTORY_PATHS:
  return out('needs_evidence','The linked source is not identified as an open vendor-market application.')
 combined=' '.join([text,linked_text])
 # Restriction/closure on the *target* page outweighs the menu label.
 # A menu link *labeled* "Applications Closed" is navigation, not
 # proof this entire market application is closed. Follow official status.
 direct_status_text=' '.join(
  ''.join(part for part in node.children if isinstance(part,str))
  for node in doc.root.walk()
  if node.tag not in ('a','script','style','noscript','nav','header','footer'))
 if CLOSE_RE.search(direct_status_text):
  return out('closed','The linked application page explicitly says this intake is closed; the worker must not publish it as open.')
 if RESTRICT_RE.search(linked_text):
  return out('restricted','The organizer accepts only returning or manager-invited applicants. A generic public open-application listing would be misleading.')
 # Organizer application hubs often keep a generic "Apply" banner while
 # their linked season-specific status page explicitly says intake is closed.
 # Do not privilege generic marketing copy over the *current linked status*.
 from urllib.parse import urljoin
 from calendar_research import same_organizer_host
 explicit_closures=[]
 for node in doc.root.walk():
  if node.tag!='a' or not node.attrs.get('href'):continue
  label=clean(node.text())
  if not re.search(r'\b(?:applications?\s+closed|closed\s+applications?|application\s+status)\b',label,re.I):
   continue
  status_url=urljoin(target,node.attrs['href'])
  if not valid_url(status_url) or not same_organizer_host(status_url,target):continue
  explicit_closures.append(status_url)
 for status_url in list(dict.fromkeys(explicit_closures))[:2]:
  try:
   status_doc,_=fetcher.get(status_url)
  except (OSError,ValueError):continue
  status_text=visible_text(status_doc.root)
  if CLOSE_RE.search(status_text) or re.search(
      r'\bApplications\s+closed!|Application for the new year will be open in January',status_text,re.I):
   return out('closed','Official linked application-status page confirms this intake is closed; generic organizer Apply navigation does not establish an open window.')
 # A general index is a research source, not a dated opportunity.
 # Recheck the index daily and examine its child applications separately.
 path_tail=urlparse(target).path.rstrip('/').split('/')[-1].lower()
 if path_tail in DIRECTORY_PATHS and not supported_form(target):
  outgoing={url for url in doc.root.links(target) if valid_url(url) and url!=target}
  if outgoing:
   return out('application_directory',
              'Official organizer application index contains more links; research its individual market and vendor forms rather than publishing the index as a market.')
 if GATE_RE.search(linked_text):
  return out('form_gated','The linked form requests sign-in or permissions, so its submission state cannot be independently verified.')
 if ROLL_RE.search(linked_text) or ROLL_RE.search(text):
  return out('confirmed_rolling','The organizer describes rolling applications. Publishing requires a confirmed regular vendor form, market identity, and an approved rolling-market verification policy.')
 if SEASON_RE.search(linked_text) or SEASON_RE.search(text):
  return out('confirmed_seasonal','An upcoming vendor season is announced. Publishing requires a linked form confirming that exact season and an active submission control.')
 if MULTI_RE.search(linked_text):
  return out('multi_date','The form covers multiple event dates; individual dates or categories must be verified before a dated-event listing can be published.')
 if CLOSE_RE.search(text):
  return out('needs_evidence','The organizer mentions closed applications, but the page also links this lead. A year- and event-specific status is needed before publishing.')
 if supported_form(target):
  if not linked_text:return out('form_gated','The public application could not be read well enough to verify an enabled submission control.')
  return out('missing_event','A public form link exists but no single matching future event and independently supported application window has been confirmed.')
 return out('missing_event','The official page links the opportunity, but an exact dated event or eligible recurring-market application window is not yet corroborated.')

def diagnose_leads(leads,fetcher,now=None,limit=80,reserve=24):
 results=[]
 seen=set()
 for entry in leads:
  if len(results)>=limit:break
  url=entry.get('target_url')
  if not url or url in seen:continue
  seen.add(url)
  # Keep spare request budget for updates to already-published listings.
  can_fetch=fetcher.requests<fetcher.limit-reserve
  if not can_fetch:
   results.append({'target_url':url,'source_url':entry.get('source_url',''),
    'status':'source_unavailable','reason':'Research request budget exhausted; will retry in a later worker run.'})
   continue
  results.append(diagnose_one(entry,fetcher,now,allow_target=can_fetch))
 return results,dict(Counter(item['status'] for item in results))

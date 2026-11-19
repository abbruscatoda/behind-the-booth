"""Correlate all saved and newly discovered leads by exact curated organizer.

The investigator follows a bounded chain of official same-host pages, never
search snippets or form submissions. It combines applications from the same
organizer with independently dated event pages; the existing public-form
verifier still decides whether an opportunity can be published.
"""
from collections import defaultdict
from urllib.parse import urlparse
from verifier import valid_url
from calendar_research import (calendar_event_pages,calendar_index_pages,
                               calendar_form_links,same_organizer_host)

MAX_GROUPS=30
MAX_HUBS_PER_GROUP=8
MAX_EVENTS_PER_GROUP=12
MAX_PAIRS=100
RESERVE_REQUESTS=28

def investigate_groups(leads,fetcher):
 from discovery import SOURCES
 trusted={root:(name,city) for name,city,root in SOURCES}
 groups=defaultdict(list)
 for entry in leads:
  root=entry.get('source_url','')
  target=entry.get('target_url','')
  if root not in trusted or not valid_url(target):continue
  if target==root or target.rstrip('/#')==root.rstrip('/#'):continue
  if not (same_organizer_host(target,root) or
          target in calendar_form_links_from_url(target)):
   continue
  groups[root].append(entry)

 pairs={}
 investigated=0
 event_pages=0
 inspected_hubs=0
 skipped=[]
 for root in sorted(groups)[:MAX_GROUPS]:
  if fetcher.requests>=fetcher.limit-RESERVE_REQUESTS:break
  organizer,city=trusted[root]
  investigated+=1
  try:
   root_doc,_=fetcher.get(root)
  except Exception:
   skipped.append(organizer+': official organizer root unavailable')
   continue
  root_links=set(root_doc.root.links(root))
  forms=set(calendar_form_links(root_doc,root))
  event_urls=set(calendar_event_pages(root_doc,root))
  # Saved links alone never authorize research. The current organizer root
  # must still link to the exact lead target.
  hubs=set()
  for lead in groups[root]:
   target=lead['target_url']
   if target not in root_links:continue
   if same_organizer_host(target,root):hubs.add(target)
   elif target in calendar_form_links_from_url(target):forms.add(target)
  hubs.update(calendar_index_pages(root_doc,root))
  for hub in sorted(hubs)[:MAX_HUBS_PER_GROUP]:
   if fetcher.requests>=fetcher.limit-RESERVE_REQUESTS:break
   try:
    doc,_=fetcher.get(hub)
   except Exception:continue
   inspected_hubs+=1
   event_urls.update(calendar_event_pages(doc,hub))
   # Forms found deeper in a hub carry the exact root -> hub -> form path.
   for form in calendar_form_links(doc,hub):
    if form not in forms:forms.add(form)
   # An event linked from a hub is valid only if that hub remains linked
   # from the organizer root, rechecked by calendar_event_provenance.
  for event in sorted(event_urls)[:MAX_EVENTS_PER_GROUP]:
   if len(pairs)>=MAX_PAIRS or fetcher.requests>=fetcher.limit-RESERVE_REQUESTS:break
   if not same_organizer_host(event,root):continue
   try:
    doc,_=fetcher.get(event)
   except Exception:continue
   event_pages+=1
   for form in sorted(forms|calendar_form_links(doc,event)):
    if len(pairs)>=MAX_PAIRS:break
    # The strict verifier reconfirms root-to-event provenance and form
    # linkage, organizer identity, exact date, cutoff and submission control.
    pair=(event,form)
    pairs[pair]={'source_url':event,'target_url':form,
                 'organizer_root':root,'calendar_url':root,
                 'organizer':organizer,'city':city,
                 'grouped_research':True}
 return list(pairs.values()),{
  'grouped_organizers_researched':investigated,
  'grouped_hubs_inspected':inspected_hubs,
  'grouped_event_pages_inspected':event_pages,
  'grouped_application_event_pairs':len(pairs),
  'grouped_research_warnings':skipped[:8]}

def calendar_form_links_from_url(url):
 """Return the exact URL only for a supported, validated public form."""
 from form_discovery import supported_form
 return {url} if supported_form(url) else set()

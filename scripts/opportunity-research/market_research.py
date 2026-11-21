"""Correlate all saved and newly discovered leads by exact curated organizer.

The investigator follows a bounded chain of official same-host pages, never
search snippets or form submissions. It combines applications from the same
organizer with independently dated event pages; the existing public-form
verifier still decides whether an opportunity can be published.
"""
from collections import defaultdict
from datetime import datetime,timezone
from urllib.parse import urlparse
from verifier import valid_url
from calendar_research import (calendar_event_pages,calendar_index_pages,
                               calendar_form_links,same_organizer_host)

MAX_GROUPS=30
MAX_HUBS_PER_GROUP=8
MAX_EVENTS_PER_GROUP=12
MAX_PAIRS=240
MAX_PAIRS_PER_GROUP=8
RESERVE_REQUESTS=28

def investigate_groups(leads,fetcher,now=None):
 from regional_search import rotate
 now=now or datetime.now(timezone.utc)
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
 # Backlog arrival order is least-recently-researched first, preventing
 # older organizers from being starved by alphabetical source ordering.
 for root in rotate(list(groups),now,MAX_GROUPS):
  if getattr(fetcher,'requests',0)>=getattr(fetcher,'limit',100000)-RESERVE_REQUESTS:break
  organizer,city=trusted[root]
  investigated+=1
  try:
   root_doc,_=fetcher.get(root)
  except Exception:
   skipped.append(organizer+': official organizer root unavailable')
   continue
  root_links=set(root_doc.root.links(root))
  form_routes={form:root for form in calendar_form_links(root_doc,root)}
  event_routes={event:root for event in calendar_event_pages(root_doc,root)}
  # Saved links alone never authorize research. The current organizer root
  # must still link to the exact lead target.
  hubs=set()
  for lead in groups[root]:
   target=lead['target_url']
   if target not in root_links:continue
   if same_organizer_host(target,root):hubs.add(target)
   elif target in calendar_form_links_from_url(target):form_routes[target]=root
  hubs.update(calendar_index_pages(root_doc,root))
  for hub in rotate(sorted(hubs),now,MAX_HUBS_PER_GROUP):
   if getattr(fetcher,'requests',0)>=getattr(fetcher,'limit',100000)-RESERVE_REQUESTS:break
   try:
    doc,_=fetcher.get(hub)
   except Exception:continue
   inspected_hubs+=1
   for event in calendar_event_pages(doc,hub):
    event_routes.setdefault(event,hub)
   for form in calendar_form_links(doc,hub):
    form_routes.setdefault(form,hub)
   # An event linked from a hub is valid only if that hub remains linked
   # from the organizer root, rechecked by calendar_event_provenance.
  # Collect the dated event pages first, then prioritize applications
  # directly linked from each event. Generic organizer-wide forms are used
  # only as a fallback and still must match the event in the verifier.
  event_docs=[]
  for event in rotate(sorted(event_routes),now,MAX_EVENTS_PER_GROUP):
   if getattr(fetcher,'requests',0)>=getattr(fetcher,'limit',100000)-RESERVE_REQUESTS:break
   if not same_organizer_host(event,root):continue
   try:doc,_=fetcher.get(event)
   except Exception:continue
   event_pages+=1
   event_docs.append((event,calendar_form_links(doc,event)))
  group_count=0
  for direct_only in (True,False):
   if group_count>=MAX_PAIRS_PER_GROUP or len(pairs)>=MAX_PAIRS:break
   for event,direct_forms in event_docs:
    if group_count>=MAX_PAIRS_PER_GROUP or len(pairs)>=MAX_PAIRS:break
    candidates=direct_forms if direct_only else set(form_routes)-direct_forms
    for form in sorted(candidates):
     if group_count>=MAX_PAIRS_PER_GROUP or len(pairs)>=MAX_PAIRS:break
     pair=(event,form)
     if pair in pairs:continue
     pairs[pair]={'source_url':event,'target_url':form,
                  'organizer_root':root,'calendar_url':root,
                  'event_index_url':event_routes[event],
                  'application_index_url':event if direct_only else form_routes[form],
                  'organizer':organizer,'city':city,
                  'grouped_research':True}
     group_count+=1
 return list(pairs.values()),{
  'grouped_organizers_researched':investigated,
  'grouped_hubs_inspected':inspected_hubs,
  'grouped_event_pages_inspected':event_pages,
  'grouped_application_event_pairs':len(pairs),
  'grouped_pair_budget_exhausted':len(pairs)>=MAX_PAIRS,
  'grouped_research_warnings':skipped[:8]}

def calendar_form_links_from_url(url):
 """Return the exact URL only for a supported, validated public form."""
 from form_discovery import supported_form
 return {url} if supported_form(url) else set()

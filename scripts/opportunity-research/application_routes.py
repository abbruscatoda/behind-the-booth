"""Check explicitly linked, separate food-truck applications. Read-only."""
import re
from urllib.parse import urljoin
from verifier import canonical_application, application_key, validate_event, norm, deadline_from, has_start_action
from category_rules import nodes_with_parents, visible_text, evidence, application_facts, availability_text


def research_routes(event_doc, source_url, application_url, supplements, fetcher, now):
 links=set();warnings=[];facts={}
 docs=[(event_doc,source_url)]+[(d,u) for d,u,_,kind in supplements if kind=='organizer_event']
 for doc,base in docs:
  for node,_ in nodes_with_parents(doc.root):
   if node.tag!='a' or not re.search(r'\bfood trucks?\b',visible_text(node),re.I):continue
   url=canonical_application(urljoin(base,node.attrs.get('href','')))
   if url and application_key(url)!=application_key(application_url):links.add(url)
 if not links:return facts,warnings
 try:parent,start,end,addr=validate_event(event_doc,now)
 except Exception:return facts,['Separate application could not be tied to a validated dated event.']
 results=[]
 failures=getattr(fetcher,'route_failures',set())
 for url in sorted(links)[:3]:
  if url in failures:
   warnings.append('Separate food-truck application could not be verified; confirm availability with the organizer.');continue
  try:
   doc,digest=fetcher.get(url)
   event,route_start,route_end,route_addr=validate_event(doc,now)
   if norm(event['name'])!=norm(parent['name']) or route_start!=start or route_end!=end or route_addr.get('addressLocality')!=addr.get('addressLocality'):
    warnings.append('Separate food-truck application has a different event/date/location; confirm the route.');continue
   title=' '.join(visible_text(n) for n,_ in nodes_with_parents(doc.root) if n.tag=='h1')
   if not re.search(r'\bfood trucks?\b',title,re.I):
    warnings.append('Linked food-truck application type could not be confirmed.');continue
   text=availability_text(doc)
   try:deadline=deadline_from(text)
   except Exception:deadline=None
   closed=bool((deadline and deadline<=now) or re.search(r'\b(application deadline has passed|applications? (?:are |is )?closed|no longer accepting applications|fully booked)\b',text,re.I))
   state='closed' if closed else 'unknown'
   if not closed and deadline and has_start_action(doc):
    state='waitlist' if re.search(r'waitlist only|join (?:the )?waitlist|apply to waitlist',text,re.I) else 'limited' if re.search(r'limited (?:vendor )?(?:spaces|booths|availability)',text,re.I) else 'unknown' if re.search(r'sold out|waitlist|wait list',text,re.I) else 'open'
   note={'closed':'The separate food-truck application is closed; the main vendor application has its own status.',
         'open':'Food trucks use a separate application, currently listed as open.',
         'limited':'Food trucks use a separate application with limited options.',
         'waitlist':'Food trucks use a separate application, currently waitlist only.',
         'unknown':'Food trucks use a separate application; current availability needs organizer confirmation.'}[state]
   price=application_facts(doc)['fee_notes']
   if price:note+=' '+price[:140]
   fact=evidence('unavailable' if closed else 'separate_application',note[:300],url,digest,text)
   fact.update({'application_state':state,'event_source_url':source_url,'starts_on':start.date().isoformat(),'ends_on':end.date().isoformat()})
   if deadline:fact['application_deadline']=deadline.isoformat()
   results.append(fact)
  except Exception:
   failures.add(url)
   warnings.append('Separate food-truck application could not be verified; confirm availability with the organizer.')
 fetcher.route_failures=failures
 if len(results)==1:facts['Food Trucks']=results[0]
 elif len(results)>1:warnings.append('Multiple food-truck application routes require organizer confirmation.')
 if len(links)>3:warnings.append('Additional food-truck application links require manual review.')
 return facts,warnings

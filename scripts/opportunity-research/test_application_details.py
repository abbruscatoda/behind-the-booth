import json,unittest
from datetime import datetime,timezone
from category_rules import research_categories,application_facts,sections
from application_routes import research_routes
from verifier import Document,validate_event,verify
from test_verifier import SOURCE,APP,NOW,fixtures,FakeFetcher

TRUCK='https://www.eventeny.com/events/vendor/?id=999'

def route_pages(text='',event_changes=None,duplicate=False):
 source,app=fixtures()
 source+=f'<div class="app-card"><a href="{TRUCK}">Food Truck Application</a><button-element>Apply now</button-element></div>'
 metadata=next(Document(app).events()).copy();metadata.update(event_changes or {})
 raw=f'<script type="application/ld+json">{json.dumps(metadata)}</script>'
 if duplicate:
  second=dict(metadata);second['startDate']=second['startDate'].replace(':00-05:00','-05:00');second['endDate']=second['endDate'].replace(':00-05:00','-05:00')
  raw+=f'<script type="application/ld+json">{json.dumps(second)}</script>'
 raw+='<h1>Food Truck</h1>'+text
 class Pages:
  def get(self,url):
   if url!=TRUCK:raise ValueError('unexpected URL')
   return Document(raw),'c'*64
 return Document(source),Pages()

class ApplicationDetailsTests(unittest.TestCase):
 def test_wrapped_section_is_read_and_stops_at_next_heading(self):
  d=Document('<section><div><h2>About the application</h2></div><div><p>No MLM. Bring your own 10x10 tent and 4-20lb bagged tent weights. No circular weights. No refunds. If electricity is needed add a special request.</p></div></section><h2>About the event</h2><p>Entertainment.</p>')
  self.assertNotIn('Entertainment',' '.join(sections(d,{'about the application'})))
  r=application_facts(d);self.assertIn('Four 20 lb',r['requirements']);self.assertIn('Electricity requires',r['requirements']);self.assertIn('No MLM',r['requirements'])
 def test_conflicting_event_card_and_standard_booth_fee_needs_review(self):
  source,app=fixtures(app_text='<p>Deadline: Nov 29, 2026 11:59 pm (GMT-05:00) Eastern Time</p><a>Start Application</a><table><tr><td>10x10 Space</td><td>$250</td></tr></table>')
  r=verify(SOURCE,APP,FakeFetcher(source,app),NOW);self.assertEqual(r['decision'],'review');self.assertIn('prices disagree',r['reason'])
 def test_services_price_and_condition(self):
  d=Document('<table><tr><td>Services/Workshop/Guest Experience</td><td>$150</td><td>Only choose if you have discussed a partnership with the organizer.</td></tr></table>')
  r,c=research_categories(Document(''),d,SOURCE,APP,NOW,'a'*64,'b'*64)
  self.assertEqual(r['categories']['Services']['status'],'eligible');self.assertIn('$150',r['categories']['Services']['note']);self.assertIn('Prior organizer discussion',r['categories']['Services']['note'])
 def test_price_description_is_not_additional_category(self):
  d=Document('<table><tr><td>Sponsor Booth</td><td>$750</td><td>Near food trucks and handmade artists.</td></tr></table>')
  r,c=research_categories(Document(''),d,SOURCE,APP,NOW,'a'*64,'b'*64);self.assertEqual(r['categories'],{})
 def test_soldout_service_and_conflicting_exclusion(self):
  d=Document('<table><tr><td>Services/Workshop</td><td>$150</td><td>Sold out</td></tr></table>')
  r,c=research_categories(Document(''),d,SOURCE,APP,NOW,'a'*64,'b'*64);self.assertEqual(r['categories']['Services']['status'],'unavailable')
  d=Document('<h2>About the application</h2><p>No food vendors.</p><h2>Prices</h2><table><tr><td>Food vendors</td><td>$100</td></tr></table>')
  r,c=research_categories(Document(''),d,SOURCE,APP,NOW,'a'*64,'b'*64);self.assertEqual(c,['Food & Beverages'])
 def test_fee_does_not_use_lowest_addon(self):
  d=Document('<table><tr><td>Electricity</td><td>$25</td></tr><tr><td>Services/Workshop</td><td>$150</td></tr><tr><td>10x10 Space</td><td>$250</td></tr></table>')
  self.assertEqual(application_facts(d)['standard_fee'],250)
 def test_conflicting_or_soldout_standard_prices_not_assumed(self):
  d=Document('<table><tr><td>10x10 Space</td><td>$250</td></tr><tr><td>10x10 Space</td><td>$300</td></tr></table>')
  self.assertIsNone(application_facts(d)['standard_fee'])
  self.assertIsNone(application_facts(Document('<table><tr><td>10x10 Space</td><td>$250</td><td>Sold out</td></tr></table>'))['standard_fee'])
 def check_route(self,text,event_changes=None,duplicate=False):
  doc,f=route_pages(text,event_changes,duplicate)
  return research_routes(doc,SOURCE,APP,[],f,NOW)
 def test_closed_route_does_not_close_main_application(self):
  facts,w=self.check_route('<p>Deadline: Nov 14, 2026 11:59 pm (GMT-05:00) Eastern Time</p><p>Application deadline has passed</p>')
  fact=facts['Food Trucks'];self.assertEqual(fact['application_state'],'closed');self.assertEqual(fact['status'],'unavailable');self.assertEqual(fact['source_url'],TRUCK);self.assertEqual(w,[])
 def test_open_route_requires_start_action_and_future_deadline(self):
  facts,w=self.check_route('<p>Deadline: Nov 25, 2026 11:59 pm (GMT-05:00) Eastern Time</p><a>Start Application</a>')
  self.assertEqual(facts['Food Trucks']['application_state'],'open');self.assertEqual(facts['Food Trucks']['status'],'separate_application')
 def test_route_waitlist(self):
  facts,w=self.check_route('<p>Deadline: Nov 25, 2026 11:59 pm (GMT-05:00) Eastern Time</p><a>Join waitlist</a>')
  self.assertEqual(facts['Food Trucks']['application_state'],'waitlist')
 def test_disabled_or_missing_deadline_route_is_unknown(self):
  for text in ['<a>Start Application</a>','<p>Deadline: Nov 25, 2026 11:59 pm (GMT-05:00) Eastern Time</p><a disabled>Start Application</a>']:
   facts,w=self.check_route(text);self.assertEqual(facts['Food Trucks']['application_state'],'unknown')
 def test_wrong_event_date_or_organizer_rejected(self):
  for changes in [{'name':'Other Market'},{'startDate':'2026-11-28T11:00:00-05:00'},{'organizer':{'name':'Someone Else','url':'https://www.eventeny.com/company/?c=999'}}]:
   facts,w=self.check_route('<a>Start Application</a>',changes);self.assertEqual(facts,{});self.assertTrue(w)
 def test_equivalent_iso_dates_do_not_create_false_conflicts(self):
  facts,w=self.check_route('<p>Deadline: Nov 14, 2026 11:59 pm (GMT-05:00) Eastern Time</p>',duplicate=True)
  self.assertEqual(facts['Food Trucks']['application_state'],'closed')
 def test_source_failure_produces_warning_not_positive(self):
  doc,f=route_pages()
  def fail(url):raise ValueError('failed')
  f.get=fail;facts,w=research_routes(doc,SOURCE,APP,[],f,NOW);self.assertEqual(facts,{});self.assertTrue(w)
 def test_unrelated_links_and_nontruck_app_types_ignored(self):
  doc=Document(f'<a href="{TRUCK}">Sponsor Application</a>')
  self.assertEqual(research_routes(doc,SOURCE,APP,[],None,NOW),({},[]))
 def test_verifier_keeps_service_condition_in_candidate(self):
  source,app=fixtures(app_text='<p>Deadline: Nov 29, 2026 11:59 pm (GMT-05:00) Eastern Time</p><a>Start Application</a><h2>Prices</h2><table><tr><td>Services/Workshop</td><td>$150</td><td>Only choose if you have discussed a partnership.</td></tr></table>')
  r=verify(SOURCE,APP,FakeFetcher(source,app),NOW);self.assertIn('Services',r['candidate']['categories']);self.assertIn('prior organizer discussion required',r['candidate']['fee_notes'])

if __name__=='__main__':unittest.main()

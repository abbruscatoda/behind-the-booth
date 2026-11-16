import contextlib, io, json, unittest
from datetime import datetime,timezone
from unittest.mock import patch
import verifier
import run as worker

SOURCE='https://www.eventeny.com/events/2026-durham-underground-market-durham-central-park-25990/'
APP='https://www.eventeny.com/events/vendor/?id=40696'
NOW=datetime(2026,11,16,tzinfo=timezone.utc)

def fixtures(**changes):
 event={'@type':'Festival','name':'2026 Durham Underground Market (Durham Central Park)','startDate':'2026-11-29T11:00:00-05:00','endDate':'2026-11-29T15:00:00-05:00','eventStatus':'https://schema.org/EventScheduled','organizer':{'name':'The Makrs Society','url':'https://www.eventeny.com/company/?c=27023'},'location':{'name':'Durham Central Park','address':{'addressLocality':'Durham','addressRegion':'NC','streetAddress':'501 Foster St'}},'offers':{'lowPrice':0,'isAccessibleForFree':True}}
 event.update(changes.get('event',{}))
 app_event=dict(event);app_event.update(changes.get('app_event',{}))
 card=changes.get('card',f'<div class="app-card"><a href="{APP}">Artist/Vendor Application</a><button-element href="{APP}">Apply now</button-element><p>$100 vendor fee plus processing fees</p></div>')
 source=f'<script type="application/ld+json">{json.dumps(event)}</script><p>2 active applications</p>'+card
 app=f'<script type="application/ld+json">{json.dumps(app_event)}</script>'+changes.get('app_text','<p>Deadline: Nov 29, 2026 11:59 pm (GMT-05:00) Eastern Time</p><a>Start Application</a>')
 return source,app
class FakeFetcher:
 def __init__(self,source,app):self.source=source;self.app=app
 def get(self,url):return verifier.Document(self.app if verifier.application_key(url) else self.source),'a'*64
class VerificationTests(unittest.TestCase):
 def check_result(self,**changes):return verifier.verify(SOURCE,APP,FakeFetcher(*fixtures(**changes)),NOW)
 def test_positive_date_and_fee(self):
  r=self.check_result();self.assertEqual(r['decision'],'publish');self.assertEqual(r['candidate']['starts_on'],'2026-11-29');self.assertEqual(r['candidate']['booth_fee'],100)
 def test_free_admission_is_not_vendor_fee(self):
  card=f'<div class="app-card"><a href="{APP}">Artist/Vendor Application</a><button-element href="{APP}">Apply now</button-element><p>Free admission!</p></div>'
  self.assertIsNone(self.check_result(card=card)['candidate']['booth_fee'])
 def test_other_organizer_same_name_is_not_trusted(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(event={'organizer':{'name':'The Makrs Society','url':'https://www.eventeny.com/company/?c=999'}})
 def test_series_range_is_not_an_occurrence(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(event={'startDate':'2026-03-22T11:00:00-04:00'})
 def test_missing_event_date(self):
  with self.assertRaises((verifier.Uncertain,ValueError)):self.check_result(event={'startDate':None})
 def test_unlinked_application(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(card='<div class="app-card"><a href="https://www.eventeny.com/events/vendor/?id=999">Apply now</a></div>')
 def test_footer_apply_button_is_not_evidence(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(card=f'<div class="app-card"><a href="{APP}">Artist/Vendor Application</a></div><a href="{APP}">Apply now</a>')
 def test_conflicting_app_identity(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(app_event={'name':'Other Market'})
 def test_ambiguous_sold_out(self):
  source,app=fixtures();source=source.replace('$100 vendor fee','One booth sold out. $100 vendor fee')
  with self.assertRaises(verifier.Uncertain):verifier.verify(SOURCE,APP,FakeFetcher(source,app),NOW)
 def test_explicit_waitlist(self):
  source,app=fixtures();source=source.replace('Apply now','Join waitlist');self.assertEqual(verifier.verify(SOURCE,APP,FakeFetcher(source,app),NOW)['candidate']['availability'],'waitlist')
 def test_explicit_limited(self):
  source,app=fixtures();source=source.replace('$100 vendor fee','Limited spaces. $100 vendor fee');self.assertEqual(verifier.verify(SOURCE,APP,FakeFetcher(source,app),NOW)['candidate']['availability'],'limited')
 def test_explicit_closure(self):
  card=f'<div class="app-card"><a href="{APP}">Artist/Vendor Application</a><p>Applications are closed</p></div>'
  result=self.check_result(card=card,app_text='<p>Applications are closed</p>');self.assertEqual(result['decision'],'closed')
 def test_expired_deadline_closes(self):
  self.assertEqual(self.check_result(app_text='<p>Deadline: Nov 10, 2026 11:59 pm (GMT-05:00) Eastern Time</p><a>Start Application</a>')['decision'],'closed')
 def test_missing_timezone_is_uncertain(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(app_text='<p>Deadline: Nov 29, 2026</p><a>Start Application</a>')
 def test_cancelled_event(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(event={'eventStatus':'https://schema.org/EventCancelled'})
 def test_new_market_is_an_exception(self):
  r=self.check_result(event={'name':'2026 New Holiday Event'});self.assertEqual(r['decision'],'review');self.assertIsNone(r['candidate']['market_slug'])
 def test_no_loose_series_name_match(self):
  self.assertIsNone(verifier.exact_series('Durham Underground Market Afterparty'));self.assertEqual(verifier.exact_series('2027 Durham Underground Market (Durham Central Park)')[0],'durham-underground-market')
 def test_url_and_redirect_guards(self):
  for url in ['http://www.eventeny.com/events/a-1/','https://127.0.0.1/','https://169.254.169.254/','https://makrs.com.evil.test/','https://user:secret@makrs.com/','https://makrs.com:8080/']:
   self.assertFalse(verifier.valid_url(url))
  with self.assertRaises(ValueError):verifier.SafeRedirect().redirect_request(None,None,302,'',{},'https://evil.test/')
 def test_discovery_deduplicates_official_series_links(self):
  root='https://makrs.com/market-applications';variant=SOURCE+'?series=9547';source,app=fixtures()
  source+=f'<a href="{variant}">November</a>'
  class Pages:
   def get(self,url):return verifier.Document(f'<a href="{SOURCE}">Event</a>' if url==root else app if verifier.application_key(url) else source),'a'*64
  with patch.object(verifier,'ROOTS',[root]):results,problems=verifier.discover(Pages(),NOW)
  self.assertEqual(problems,[]);self.assertEqual(len(results),1);self.assertEqual(results[0]['decision'],'publish')
 def test_discovery_conflicts_need_review(self):
  root='https://makrs.com/market-applications';variant=SOURCE+'?series=9547';source,app=fixtures();source+=f'<a href="{variant}">November</a>'
  class Pages:
   def get(self,url):
    html=f'<a href="{SOURCE}">Event</a>' if url==root else app if verifier.application_key(url) else source.replace('$100 vendor fee','Limited spaces. $100 vendor fee') if '?series=' in url else source
    return verifier.Document(html),'a'*64
  with patch.object(verifier,'ROOTS',[root]):results,problems=verifier.discover(Pages(),NOW)
  self.assertEqual(len(results),1);self.assertEqual(results[0]['decision'],'review')
 def test_dry_run_does_not_write(self):
  result=self.check_result();item={**result['candidate'],'id':'test','automation_hold':False,'updated_at':NOW.isoformat()};calls=[]
  class FakeDB:
   def rpc(self,name,body=None):
    calls.append(name)
    if name!='btb_research_context':raise AssertionError('Dry run attempted a database write')
    return {'enabled':True,'items':[item]}
  with patch.object(worker,'Database',FakeDB),patch.object(worker,'discover',return_value=([result],[])),contextlib.redirect_stdout(io.StringIO()):worker.run(True)
  self.assertEqual(calls,['btb_research_context'])
 def test_paused_worker_does_no_research(self):
  class FakeDB:
   def rpc(self,*args):return {'enabled':False,'items':[]}
  with patch.object(worker,'Database',FakeDB),patch.object(worker,'discover') as research,contextlib.redirect_stdout(io.StringIO()):worker.run(False)
  research.assert_not_called()


class ActiveApplicationTests(unittest.TestCase):
 def check_result(self,**changes):return verifier.verify(SOURCE,APP,FakeFetcher(*fixtures(**changes)),NOW)
 def test_no_active_count_label_required(self):
  source,app=fixtures();source=source.replace('<p>2 active applications</p>','')
  self.assertEqual(verifier.verify(SOURCE,APP,FakeFetcher(source,app),NOW)['candidate']['availability'],'open')
 def test_missing_start_action_is_not_open(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(app_text='<p>Deadline: Nov 29, 2026 11:59 pm (GMT-05:00) Eastern Time</p><p>Start Application</p>')
 def test_disabled_start_is_not_open(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(app_text='<p>Deadline: Nov 29, 2026 11:59 pm (GMT-05:00) Eastern Time</p><button disabled>Start Application</button>')
 def test_hidden_start_is_not_open(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(app_text='<p>Deadline: Nov 29, 2026 11:59 pm (GMT-05:00) Eastern Time</p><div hidden><button>Start Application</button></div>')
 def test_app_closure_overrides_stale_button(self):
  result=self.check_result(app_text='<p>Applications are closed</p><button>Start Application</button>')
  self.assertEqual(result['candidate']['availability'],'closed')
 def test_disabled_dated_action_is_not_open(self):
  with self.assertRaises(verifier.Uncertain):self.check_result(card=f'<div class="app-card"><button-element disabled href="{APP}">Apply now</button-element></div>')

class ArtspaceTests(unittest.TestCase):
 def item(self):return {'title':verifier.ARTSPACE_TITLE,'source_url':verifier.ARTSPACE_SOURCE,'application_url':verifier.ARTSPACE_APP,'starts_on':'2026-12-13','ends_on':'2026-12-13','market_id':'known','market_slug':'artspace-holiday-mini-mall','market_name':verifier.ARTSPACE_TITLE,'market_organizer':'Artspace','market_city':'Raleigh','market_state':'NC'}
 def pages(self,extra='',form_extra='',submit=''):
  source=f'<h2>Call for Holiday Mini Mall Vendors</h2><p>Event: The Mini Mall at Artspace, Holiday Edition. December 13, 2026.</p><p>Call closes: Wednesday, November 26, 11:59pm</p><a href="{verifier.ARTSPACE_APP}">Apply</a><p>{extra}</p><h2>Holiday Mini Mall Vendors (closed)</h2><p>Applications are closed. December 14, 2025.</p>'
  app=f'<h1>{verifier.ARTSPACE_TITLE}</h1><p>December 13, 2026. Contact info@artspacenc.org</p><p>Application Deadline: Wednesday, November 25, 2026, 11:59 PM</p><p>{form_extra}</p><form method="post" action="https://submit.jotform.com/submit/252944311617153"><input type="email"><button type="submit" {submit}>Submit</button></form>'
  class Pages:
   def get(self,url):return verifier.Document(source if url==verifier.ARTSPACE_SOURCE else app),'a'*64
  return Pages()
 def test_linked_active_form_is_open_without_open_label(self):
  r=verifier.verify_artspace(self.item(),self.pages(),NOW);self.assertEqual(r['decision'],'publish');self.assertEqual(r['candidate']['availability'],'open')
 def test_old_closed_listing_does_not_close_current_call(self):
  self.assertEqual(verifier.verify_artspace(self.item(),self.pages(),NOW)['candidate']['availability'],'open')
 def test_earlier_form_deadline_retained_and_disclosed(self):
  r=verifier.verify_artspace(self.item(),self.pages(),NOW);self.assertEqual(r['candidate']['deadline'],'2026-11-25T23:59:00-05:00');self.assertIn('different deadline',r['candidate']['fee_notes'])
 def test_missing_profile_requires_one_time_link(self):
  item=self.item();item['market_id']=None
  self.assertEqual(verifier.verify_artspace(item,self.pages(),NOW)['decision'],'review')
 def test_disabled_form_does_not_publish(self):
  with self.assertRaises(verifier.Uncertain):verifier.verify_artspace(self.item(),self.pages(submit='disabled'),NOW)
 def test_wrong_date_does_not_publish(self):
  item=self.item();item['starts_on']=item['ends_on']='2026-12-14'
  with self.assertRaises(verifier.Uncertain):verifier.verify_artspace(item,self.pages(),NOW)
 def test_waitlist_overrides_active_submit(self):
  self.assertEqual(verifier.verify_artspace(self.item(),self.pages(form_extra='Join the waitlist'),NOW)['candidate']['availability'],'waitlist')
 def test_explicit_closure_overrides_active_submit(self):
  self.assertEqual(verifier.verify_artspace(self.item(),self.pages(form_extra='Applications are closed'),NOW)['candidate']['availability'],'closed')
 def test_expired_deadline_closes(self):
  self.assertEqual(verifier.verify_artspace(self.item(),self.pages(),datetime(2026,11,26,12,tzinfo=timezone.utc))['candidate']['availability'],'closed')
 def test_generic_limited_space_jury_does_not_mean_limited_openings(self):
  self.assertEqual(verifier.verify_artspace(self.item(),self.pages(form_extra='Due to limited space, submissions are juried.'),NOW)['candidate']['availability'],'open')
 def test_actual_limited_spaces(self):
  self.assertEqual(verifier.verify_artspace(self.item(),self.pages(form_extra='Limited vendor spaces'),NOW)['candidate']['availability'],'limited')
 def test_other_forms_remain_uncertain(self):
  item=self.item();item['application_url']='https://form.jotform.com/999'
  with self.assertRaises(verifier.Uncertain):verifier.verify_artspace(item,self.pages(),NOW)
 def test_other_provider_paths_are_not_fetchable(self):
  for url in ['https://form.jotform.com/999','https://artspacenc.org/other-call/']:self.assertFalse(verifier.valid_url(url))



class WorkerRoutingTests(unittest.TestCase):
 item=ArtspaceTests.item
 pages=ArtspaceTests.pages
 def test_worker_routes_artspace_to_official_form_reader(self):
  r=worker.existing_result(self.item(),{},self.pages(),NOW)
  self.assertEqual(r['policy'],'artspace-jotform-v1');self.assertEqual(r['decision'],'publish')



class SourceSizeTests(unittest.TestCase):
 def fetch_bytes(self,raw):
  class Response:
   url='https://makrs.com/moore-square-winterfaire'
   headers={'Content-Type':'text/html;charset=utf-8'}
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,limit):return raw[:limit]
  class Opener:
   def open(self,*args,**kwargs):return Response()
  fetcher=verifier.Fetcher();fetcher.opener=Opener()
  with patch.object(verifier.time,'sleep'):return fetcher.get(Response.url)
 def test_legitimate_page_over_old_limit_is_read(self):
  raw=b'<html><body>'+b' ' * 2_400_000+b'<a href="https://www.eventeny.com/events/vendor/?id=46460">Vendor Application</a></body></html>'
  doc,checksum=self.fetch_bytes(raw)
  self.assertIn('https://www.eventeny.com/events/vendor/?id=46460',doc.root.links('https://makrs.com/moore-square-winterfaire'))
  self.assertEqual(len(checksum),64)
 def test_oversize_still_rejected(self):
  with self.assertRaisesRegex(ValueError,'4 MB limit'):self.fetch_bytes(b' '*(verifier.MAX_SOURCE_BYTES+1))
 def test_limit_is_inclusive(self):
  self.fetch_bytes(b' '*verifier.MAX_SOURCE_BYTES)
 def test_errors_are_categorized_without_arbitrary_exception_text(self):
  self.assertEqual(verifier.source_error(ValueError('HTML source exceeds the 4 MB limit')),'HTML source exceeds the 4 MB limit')
  self.assertEqual(verifier.source_error(RuntimeError('private diagnostic detail')),'Request or page parsing failed')
 def test_discovery_keeps_real_source_failure_visible(self):
  class Broken:
   def get(self,url):raise ValueError('HTML source exceeds the 4 MB limit')
  with patch.object(verifier,'ROOTS',['https://makrs.com/moore-square-winterfaire']):results,problems=verifier.discover(Broken(),NOW)
  self.assertEqual(results,[]);self.assertTrue(any('4 MB limit' in p for p in problems))

if __name__=='__main__':unittest.main()

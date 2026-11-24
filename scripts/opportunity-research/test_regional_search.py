"""Regression coverage for the missed independent/municipal discovery routes."""
import unittest
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from urllib.parse import urlparse,parse_qs
from verifier import Document,CITIES,valid_url
import discovery
import regional_search as regional
import calendar_research as calendar

NOW=datetime(2026,11,20,17,tzinfo=timezone.utc)
ROOT='https://popupraleigh.com/9-2/'
EVENT='https://popupraleigh.com/2026/11/19/holiday-markets/'
FORM='https://forms.gle/NSUe3V11UyUW3K997'
class Pages:
 requests=0;limit=480
 def __init__(self,pages):self.pages=pages;self.calls=[]
 def get(self,url):
  self.calls.append(url)
  if url not in self.pages:raise ValueError('unavailable')
  return Document(self.pages[url]),'a'*64
class Reply:
 url='https://www.bing.com/search'
 def __init__(self,body):self.body=body
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,limit):return self.body[:limit]
class Search:
 def __init__(self,body):self.body=body;self.calls=[]
 def open(self,request,timeout):self.calls.append(request.full_url);return Reply(self.body)

class RegionalTests(unittest.TestCase):
 def test_all_policy_cities_searched_every_run_and_next_year(self):
  text=' '.join(regional.queries(NOW)).lower()
  for city in CITIES:self.assertIn(city,text)
  self.assertEqual(len(regional.queries(NOW)),24)
  self.assertIn('2027',text)
  self.assertNotEqual(regional.queries(NOW),regional.queries(NOW+timedelta(days=1)))
 def test_rss_search_is_not_limited_to_eventeny(self):
  feed=Search(('<rss><channel><item><title>Holiday market</title><link>'+EVENT+'</link></item></channel></rss>').encode())
  hits,stats=regional.search_results(NOW,feed)
  self.assertIn(EVENT,hits);self.assertEqual(stats['queries_succeeded'],32)
  self.assertTrue(all('site:eventeny' not in parse_qs(urlparse(url).query)['q'][0] for url in feed.calls))
 def test_generic_tourism_search_result_is_not_an_actionable_lead(self):
  hits,_=regional.search_results(NOW,Search(b'<rss><channel><item><title>Raleigh Wikipedia</title><description>Capital city of North Carolina</description><link>https://en.wikipedia.org/wiki/Raleigh</link></item></channel></rss>'))
  self.assertFalse(hits)
 def test_generic_and_out_of_region_rss_results_do_not_count_as_vendor_discovery(self):
  query='"Clayton" North Carolina vendor applications 2026'
  self.assertFalse(regional.relevant_result('https://www.theclayton.com/chicago','Fulton Market Chicago','Discover Chicago membership',query))
  self.assertFalse(regional.relevant_result('https://www.gartner.com/','Gartner','Market insights for executives','"Garner" NC vendor applications'))
  self.assertTrue(regional.relevant_result('https://organizer.example/apply','Clayton vendor application','Craft market in Clayton, NC',query))
 def test_independent_fallback_recovers_vendor_results_from_generic_rss(self):
  class Engines:
   def open(self,request,timeout):
    if urlparse(request.full_url).hostname=='html.duckduckgo.com':
     reply=Reply(b'<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fpopupraleigh.com%2F9-2%2F">Pop-Up Raleigh vendor applications</a>')
     reply.url=request.full_url
     return reply
    return Reply(b'<rss><channel><item><title>Raleigh Wikipedia</title><link>https://en.wikipedia.org/wiki/Raleigh</link></item></channel></rss>')
  hits,stats=regional.search_results(NOW,Engines())
  self.assertIn(ROOT,hits)
  self.assertEqual(stats['fallback_queries_attempted'],6)
  self.assertEqual(stats['fallback_queries_with_results'],6)
 def test_html_fallback_drops_unsafe_targets_and_interstitials(self):
  class Engine:
   def open(self,request,timeout):
    r=Reply(b'<a class="result__a" href="https://127.0.0.1/market">Market</a><a class="result__a" href="javascript:alert(1)">Apply</a>');r.url=request.full_url;return r
  self.assertFalse(regional.html_search('Raleigh',Engine()))
 def test_feed_errors_are_reported_not_silently_empty(self):
  hits,stats=regional.search_results(NOW,Search(b'<html>blocked</html>'))
  self.assertFalse(hits);self.assertEqual(len(stats['query_failures']),32)
 def test_search_snippet_cannot_publish_or_authorize_an_unknown_host(self):
  pages=Pages({})
  with patch.object(regional,'search_results',return_value=({'https://unknown-organizer.example/market':'Open $10 booths'},{})):
   leads,events,stats=regional.discover_regional(pages,NOW,discovery.SOURCES,{})
  self.assertFalse(leads);self.assertFalse(events);self.assertFalse(pages.calls)
  self.assertEqual(stats['unapproved_source_count'],1)
 def test_new_source_report_is_bounded_rotates_and_keeps_total(self):
  import json
  hits={'https://organizer'+str(i)+'.example/'+('a'*1000):'New market' for i in range(30)}
  with patch.object(regional,'search_results',side_effect=[(hits,{}),(hits,{})]):
   _,_,stats=regional.discover_regional(Pages({}),NOW,discovery.SOURCES,{})
   _,_,later=regional.discover_regional(Pages({}),NOW.replace(hour=13),discovery.SOURCES,{})
  self.assertEqual(stats['unapproved_source_count'],30)
  self.assertEqual(len(stats['unapproved_sources']),12)
  self.assertLess(len(json.dumps(stats).encode()),20000)
  self.assertNotEqual([x['url'] for x in stats['unapproved_sources']],[x['url'] for x in later['unapproved_sources']])
 def test_search_requires_live_official_link_then_retains_event_lead(self):
  doc=Document('<a href="'+EVENT+'">Holiday market</a>')
  pages=Pages({EVENT:'<h1>Holiday Market</h1><a href="'+FORM+'">Waiting list</a>'})
  sources=[('Pop-Up Raleigh','Raleigh',ROOT)]
  with patch.object(regional,'search_results',return_value=({EVENT:'Holiday Market'},{})):
   leads,events,stats=regional.discover_regional(pages,NOW,sources,{ROOT:doc})
   self.assertEqual(leads[0]['target_url'],EVENT)
   self.assertNotIn('availability',leads[0]);self.assertFalse(events)
   leads,_,_=regional.discover_regional(pages,NOW,sources,{ROOT:Document('No link')})
   self.assertFalse(leads)
 def test_rotation_covers_late_entries_and_changes_full_order(self):
  seen=set()
  for i in range(20):seen.update(regional.rotate(range(65),NOW+timedelta(hours=12*i),8))
  self.assertEqual(seen,set(range(65)))
  self.assertNotEqual(regional.rotate(range(11),NOW,11),regional.rotate(range(11),NOW+timedelta(days=1),11))
 def test_failed_official_fetch_is_cached_only_within_run(self):
  from verifier import Fetcher,source_error
  from urllib.error import HTTPError
  class Blocked:
   calls=0
   def open(self,*args,**kwargs):
    self.calls+=1;raise HTTPError(ROOT,403,'Forbidden',{},None)
  blocked=Blocked();fetcher=Fetcher(limit=10);fetcher.opener=blocked
  with patch('verifier.time.sleep'):
   for _ in range(2):
    with self.assertRaises(HTTPError) as caught:fetcher.get(ROOT)
    self.assertEqual(source_error(caught.exception),'HTTP 403')
   self.assertEqual(blocked.calls,1)
   self.assertEqual(fetcher.requests,1)
   later=Fetcher(limit=10);later.opener=blocked
   with self.assertRaises(HTTPError):later.get(ROOT)
   self.assertEqual(blocked.calls,2)
 def test_missed_sources_are_curated(self):
  roots={url for _,_,url in discovery.SOURCES}
  self.assertIn(ROOT,roots)
  self.assertTrue(any('apply-be-holiday-sip-n-shop-vendor' in url for url in roots))
  self.assertTrue(all(valid_url(url) for url in roots))
 def test_calendar_recognizes_municipal_news_and_civicplus_market_labels(self):
  root='https://raleighnc.gov/events'
  target='https://raleighnc.gov/parks-and-recreation/news/sip-n-shop-holiday-market'
  self.assertIn(target,calendar.calendar_event_pages(Document('<a href="'+target+'">Holiday Market</a>'),root))
  apex='https://www.apexnc.org/428/Special-Events-Festivals'
  self.assertIn('https://www.apexnc.org/1970/Annual-Kids-Holiday-Craft-Fair',calendar.calendar_event_pages(Document('<a href="/1970/Annual-Kids-Holiday-Craft-Fair">Craft Fair Market</a>'),apex))
 def test_one_busy_calendar_cannot_starve_another(self):
  roots=['https://www.trianglepopup.com/applications',ROOT]
  calendars=[('Triangle Pop-Up',roots[0],'https://www.trianglepopup.com/events'),('Pop-Up Raleigh',ROOT,'https://popupraleigh.com/home/')]
  pages={roots[0]:'',ROOT:''}
  for _,root,cal in calendars:
   urls=[cal.rstrip('/')+'/market-'+str(i) for i in range(20)]
   pages[cal]=''.join('<a href="'+u+'">Holiday Market</a>' for u in urls)
   for u in urls:pages[u]='<h1>Holiday Market</h1>'
  fetch=Pages(pages)
  with patch.object(calendar,'CALENDARS',calendars):
   _,_,stats=calendar.discover_calendars(fetch,NOW)
  hints=stats['_event_leads']
  self.assertTrue(any(l['source_url']==ROOT for l in hints))
  self.assertTrue(any(l['source_url']==roots[0] for l in hints))
  self.assertLessEqual(stats['calendar_event_pages_inspected'],16)
  self.assertGreater(stats['calendar_events_deferred'],0)
 def test_waitlist_form_is_collected_without_guessing_open(self):
  rootdoc='<a href="'+FORM+'">December 19th WAITING LIST</a>'
  fetch=Pages({ROOT:rootdoc,FORM:'<h1>Sign in required</h1>'})
  with patch.object(discovery,'SOURCES',[('Pop-Up Raleigh','Raleigh',ROOT)]):
   candidates,leads,stats=discovery.discover_triangle(fetch,NOW,include_search=False,include_calendars=False)
  self.assertFalse(candidates)
  self.assertEqual(leads[0]['target_url'],FORM)

if __name__=='__main__':unittest.main()

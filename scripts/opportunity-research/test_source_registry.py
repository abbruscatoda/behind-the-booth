"""Ensure official source registry cannot drift from Triangle discovery sources."""
import contextlib
import io
import unittest
from unittest.mock import patch
import discovery
import verifier
import run as worker
import recurring_market
import seasonal_research
import multidate_research
import deep_research
import lead_reconciliation

class SourceRegistryTests(unittest.TestCase):
 def test_all_curated_roots_are_safe_and_unique(self):
  self.assertGreaterEqual(len(discovery.SOURCES),25)
  urls=[root for _,_,root in discovery.SOURCES]
  self.assertEqual(len(urls),len(set(urls)))
  for organizer,city,root in discovery.SOURCES:
   with self.subTest(root=root):
    self.assertTrue(verifier.valid_url(root))
    self.assertGreaterEqual(len(organizer),2)
    self.assertGreaterEqual(len(city),3)

 def test_worker_saves_leads_with_exact_current_source_list(self):
  calls=[]
  class FakeDB:
   def rpc(self,name,body=None):
    calls.append((name,body))
    if name=='btb_research_context':return {'enabled':True,'items':[]}
    if name=='btb_research_run':
     return 'test-run'
    if name=='btb_research_discovery_backlog':return []
    if name=='btb_research_coverage_context':return []
    if name=='btb_research_finalize_discovery_leads':return {'resolved':0}
    if name=='btb_research_record_discovery_leads_v2':
     self.assertEqual(len(body['p_sources']),len(discovery.SOURCES))
     return {'saved':1,'approved_sources':len(body['p_sources'])}
    raise AssertionError('unexpected RPC '+name)
   def assertEqual(self,a,b):
    if a!=b:raise AssertionError((a,b))
  class FakeFetcher:
   def __init__(self,limit):self.limit=limit;self.requests=0
  lead={'target_url':'https://forms.gle/NSUe3V11UyUW3K997',
        'source_url':'https://westernwakefarmersmarket.org/',
        'organizer':'Western Wake Farmers Market','city':'Morrisville',
        'title':'Learn more and apply'}
  with patch.object(worker,'Database',FakeDB),patch.object(worker,'Fetcher',FakeFetcher),\
       patch.object(worker,'discover',return_value=([],[])),\
       patch.object(worker,'discover_triangle',return_value=([],[lead],{})),\
       patch.object(recurring_market,'discover_recurring',return_value=[]),\
       patch.object(seasonal_research,'discover_seasonal',return_value=[]),\
       patch.object(multidate_research,'discover_multidate',return_value=[]),\
       patch.object(deep_research,'diagnose_leads',return_value=([],{})),\
       patch.object(lead_reconciliation,'reconcile_shortcuts',return_value=[]),\
       contextlib.redirect_stdout(io.StringIO()):
   worker.run(False)
  record=[body for name,body in calls if name=='btb_research_record_discovery_leads_v2']
  self.assertEqual(len(record),1)
  self.assertLess([n for n,_ in calls].index('btb_research_record_discovery_leads_v2'),
                  [n for n,_ in calls].index('btb_research_finalize_discovery_leads'))
  self.assertEqual(record[0]['p_sources'],
   [{'organizer':name,'city':city,'source_url':root} for name,city,root in discovery.SOURCES])

if __name__=='__main__':unittest.main()

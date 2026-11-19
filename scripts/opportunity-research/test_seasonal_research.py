"""Seasonal application research and publishing regression tests."""
import contextlib,io,unittest
from datetime import datetime,timezone
from unittest.mock import patch
import seasonal_research as seasonal
import run as worker
from verifier import Document,Uncertain

NOW=datetime(2026,11,18,23,tzinfo=timezone.utc)
FV=seasonal.PROVIDERS[0]
WW=seasonal.PROVIDERS[1]

def text_page(*parts):
 return ''.join('<p>'+p+'</p>' for p in parts)

class Pages:
 def __init__(self,provider=FV,closed=False,wrong_form=False):
  self.calls=[]
  root=provider['market_url'];vendor=provider['vendor_url'];form=provider['form_url']
  if provider['kind']=='fixed_season':
   root_text='Fuquay-Varina Growers Market at 121 N Main Street'
   vendor_text=('Now Accepting Vendor Applications for our 2027 Season! '
     'Saturdays, 10 Apr - 04 Sep. 121 N. Main St. Farmers Market vendor application.')
   form_text='2027 NEW Vendor Application. Saturdays, April 10th to September 4th. Full-time, $260 (22 Saturdays). Guest $30 per day.'
  else:
   root_text=('Western Wake Farmers Market. Vendor Applications Rolling! '
    'Applications are open for WWFM’s 26/27 season! Open Saturdays year-round. '
    '101 Town Hall Drive Morrisville NC')
   vendor_text=('Western Wake Farmers Market Vendor Application. '
    'Applications are accepted on a rolling basis.')
   form_text='Western Wake Farmers Market Regular Vendor Application'
  if closed:form_text+=' Applications are closed.'
  if wrong_form:form_text='Unrelated market application'
  self.docs={root:'<h1>'+root_text+'</h1><a href="'+vendor+'">Vendor Application</a>',
   vendor:'<h1>'+vendor_text+'</h1><a href="'+form+'">Apply Online</a>',
   form:'<h1>'+form_text+'</h1><button>Submit</button>'}
 def get(self,url):
  self.calls.append(url)
  if url not in self.docs:raise ValueError('URL was not allowlisted')
  return Document(self.docs[url]),'a'*64

class SeasonTests(unittest.TestCase):
 def valid(self,provider,**kwargs):
  with patch.object(seasonal,'read_public_form',return_value={
    'closed':kwargs.get('closed',False),'complete':True,'issues':[]}) as form_reader:
   return seasonal.check_provider(provider,Pages(provider,**kwargs),NOW)
 def test_fv_verified_season_not_individual_saturdays(self):
  result=self.valid(FV)
  candidate=result['candidate']
  self.assertEqual(result['decision'],'publish')
  self.assertEqual(candidate['schedule_type'],'seasonal_application')
  self.assertEqual(candidate['availability'],'open')
  self.assertEqual((candidate['starts_on'],candidate['ends_on']),('2027-04-10','2027-09-04'))
  self.assertIsNone(candidate['deadline'])
  self.assertIn('does not guarantee',candidate['fee_notes'])
 def test_rolling_market_verified(self):
  result=self.valid(WW)
  self.assertEqual(result['candidate']['schedule_type'],'rolling_market')
  self.assertEqual(result['candidate']['ends_on'],'2027-03-31')
 def test_closed_form_blocks_publication(self):
  with patch.object(seasonal,'read_public_form',return_value={'closed':True,'complete':False}):
   with self.assertRaises(Uncertain):
    seasonal.check_provider(FV,Pages(FV,closed=True),NOW)
 def test_unreadable_form_blocks_publication(self):
  with patch.object(seasonal,'read_public_form',side_effect=Uncertain('Not publicly readable')):
   with self.assertRaises(Uncertain):
    seasonal.check_provider(WW,Pages(WW),NOW)
 def test_wrong_market_form_blocks_publication(self):
  with patch.object(seasonal,'read_public_form',return_value={'closed':False,'complete':True,'issues':[]}):
   with self.assertRaises(Uncertain):
    seasonal.check_provider(FV,Pages(FV,wrong_form=True),NOW)
 def test_unlinked_application_blocks_publication(self):
  pages=Pages(FV)
  pages.docs[FV['vendor_url']]=pages.docs[FV['vendor_url']].replace(FV['form_url'],'https://form.jotform.com/000000000000000')
  with self.assertRaises(Uncertain):
   seasonal.check_provider(FV,pages,NOW)
 def test_worker_uses_guarded_publisher(self):
  result=self.valid(FV);calls=[]
  class FakeDB:
   def rpc(self,name,body=None):
    calls.append(name)
    if name=='btb_research_context':return {'enabled':True,'items':[]}
    if name=='btb_research_run':return 'run'
    if name=='btb_research_discovery_backlog':return []
    if name=='btb_research_publish_seasonal':return {'action':'publish','reason':'Confirmed seasonal application published'}
    raise AssertionError('Unexpected RPC '+name)
  class Fetcher:
   def __init__(self,limit):self.requests=0;self.limit=limit
  with (patch.object(worker,'Database',FakeDB),
   patch.object(worker,'Fetcher',Fetcher),
   patch.object(worker,'discover',return_value=([],[])),
   patch.object(worker,'discover_triangle',return_value=([],[],{})),
   patch('seasonal_research.discover_seasonal',return_value=[result]),
   patch('recurring_market.discover_recurring',return_value=[]),
   contextlib.redirect_stdout(io.StringIO())):
   worker.run(False)
  self.assertIn('btb_research_publish_seasonal',calls)
  self.assertNotIn('btb_research_apply',calls)
if __name__=='__main__':unittest.main()

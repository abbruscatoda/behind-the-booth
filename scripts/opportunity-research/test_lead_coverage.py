"""Same-market URLs must be proven live before covered leads are retired."""
import unittest
from verifier import Document
from lead_coverage import coverage_receipts

ROOT='https://shoplocalraleigh.org/vendor-information/'
HUB='https://shoplocalraleigh.org/brewgaloo/brewgaloo-applications/'
EVENT='https://shoplocalraleigh.org/brewgaloo/'
CHILD='https://shoplocalraleigh.org/brewgaloo/vendors/'
OTHER='https://shoplocalraleigh.org/another-festival/vendors/'
CARY_ROOT='https://thenightmarketcompany.com/'
CARY_SOURCE='https://thenightmarketcompany.com/plan-your-markets-vendor-info'
CARY_APP='https://pci.jotform.com/form/253207413592151'

class Fetch:
 def __init__(self):
  self.requests=0
  self.limit=180
  self.docs={
   ROOT:'<a href="'+CHILD+'">Brewgaloo retail</a><a href="'+OTHER+'">Different event</a>',
   HUB:'<a href="'+CHILD+'">Local vendors</a>',
   CARY_ROOT:'<a href="'+CARY_SOURCE+'">2026 market applications</a>'
  }
 def get(self,url):
  self.requests+=1
  if url not in self.docs:raise ValueError('Not currently linked')
  return Document(self.docs[url]),'a'*64

def pub(id='brew',**kw):
 return dict(id=id,publication='published',source_url=EVENT,application_url=HUB,
             market_organizer='Shop Local Raleigh',market_city='Raleigh',**kw)
def lead(url=CHILD,root=ROOT,city='Raleigh',organizer='Shop Local Raleigh'):
 return dict(target_url=url,source_url=root,city=city,organizer=organizer)

class GeneralCoverageTests(unittest.TestCase):
 def test_live_event_category_is_covered_by_published_event(self):
  receipts,stats=coverage_receipts([lead()],[pub()],Fetch(),{ROOT})
  self.assertEqual(len(receipts),1)
  self.assertEqual(receipts[0]['proof'],'published_event_application_category')
  self.assertEqual(stats['coverage_by_proof']['published_event_application_category'],1)

 def test_unrelated_event_category_is_not_archived(self):
  self.assertEqual(coverage_receipts([lead(OTHER)],[pub()],Fetch(),{ROOT})[0],[])

 def test_organizer_source_must_still_link_the_target(self):
  pages=Fetch();pages.docs[ROOT]='<a href="'+OTHER+'">Wrong event</a>'
  self.assertEqual(coverage_receipts([lead()],[pub()],pages,{ROOT})[0],[])

 def test_hub_must_still_link_event_category(self):
  pages=Fetch();pages.docs[HUB]='<p>Category removed</p>'
  self.assertEqual(coverage_receipts([lead()],[pub()],pages,{ROOT})[0],[])

 def test_same_name_different_city_not_merged(self):
  self.assertEqual(coverage_receipts([lead(city='Durham')],[pub()],Fetch(),{ROOT})[0],[])

 def test_published_app_hub_is_exact_covered_source_with_the_alias_organizer(self):
  opp=dict(id='cary',publication='published',source_url=CARY_SOURCE,
           application_url=CARY_APP,market_organizer='The Night Market Company',market_city='Cary')
  result,_=coverage_receipts([lead(CARY_SOURCE,CARY_ROOT,'Cary','Night Market Company')],
                              [opp],Fetch(),{CARY_ROOT})
  self.assertEqual(len(result),1)
  self.assertEqual(result[0]['proof'],'published_source')

 def test_different_application_in_same_organizer_is_not_covered(self):
  source='https://shoplocalraleigh.org/brewgaloo/different-form/'
  pages=Fetch();pages.docs[ROOT]+='<a href="'+source+'">Other application</a>'
  self.assertEqual(coverage_receipts([lead(source)],[pub()],pages,{ROOT})[0],[])

 def test_held_published_opportunity_still_provides_coverage(self):
  p=pub(automation_hold=True)
  self.assertEqual(len(coverage_receipts([lead()],[p],Fetch(),{ROOT})[0]),1)

if __name__=='__main__':unittest.main()

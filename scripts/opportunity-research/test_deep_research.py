"""Every unresolved application receives a bounded, evidence-based diagnosis."""
import unittest
from verifier import Document
import deep_research as research

ROOT='https://www.caryfarmersmarket.com/vendor-application/'
APP='https://pci.jotform.com/form/251375591118156'
class Pages:
 def __init__(self,linked=True,reason=''):
  self.docs={
   ROOT:('<h1>Cary Downtown Farmers Market - Vendor Application</h1>'+
    ('<a href="'+APP+'">Fill Out Application</a>' if linked else '<p>Form removed</p>')),
   APP:'<h1>Cary Downtown Farmers Market Vendor Application</h1><p>'+reason+'</p><button>Submit</button>'
  }
  self.requests=0;self.limit=220
 def get(self,url):
  self.requests+=1
  if url not in self.docs:raise ValueError('Unlisted source')
  return Document(self.docs[url]),'a'*64
def lead(url=APP):
 return {'title':'Fill Out Application','target_url':url,'source_url':ROOT}

class DiagnosticsTests(unittest.TestCase):
 def test_restricted_market_is_explained_not_published(self):
  pages=Pages(reason='We are only accepting applications for returning vendors or those invited to apply directly by the market manager.')
  result=research.diagnose_one(lead(),pages)
  self.assertEqual(result['status'],'restricted')
  self.assertIn('returning',result['reason'])

 def test_closed_application_is_not_falsely_open(self):
  pages=Pages(reason='2026 vendor applications are closed.')
  self.assertEqual(research.diagnose_one(lead(),pages)['status'],'closed')

 def test_old_unlinked_form_is_not_used_as_current_evidence(self):
  pages=Pages(linked=False)
  self.assertEqual(research.diagnose_one(lead(),pages)['status'],'unlinked')
  self.assertEqual(pages.requests,1)

 def test_gated_form_is_identified(self):
  pages=Pages(reason='You need permission to continue.')
  self.assertEqual(research.diagnose_one(lead(),pages)['status'],'form_gated')

 def test_ordinary_form_without_event_stays_unpublished(self):
  pages=Pages()
  self.assertEqual(research.diagnose_one(lead(),pages)['status'],'missing_event')

 def test_self_link_is_not_counted_as_an_application(self):
  pages=Pages()
  self.assertEqual(research.diagnose_one(lead(ROOT+'#'),pages)['status'],'not_application')
  self.assertEqual(pages.requests,0)

 def test_request_budget_never_causes_unsupported_publication(self):
  pages=Pages();pages.requests=pages.limit-12
  rows,counts=research.diagnose_leads([lead()],pages)
  self.assertEqual(rows[0]['status'],'source_unavailable')
  self.assertEqual(rows[0]['reason'],'Research request budget exhausted; will retry in a later worker run.')
  self.assertEqual(pages.requests,pages.limit-12)

if __name__=='__main__':unittest.main()

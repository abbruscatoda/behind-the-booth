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

 def test_explicit_2026_season_closure_is_recognized(self):
  pages=Pages(reason='Applications for 2026 market season are now closed.')
  self.assertEqual(research.diagnose_one(lead(),pages)['status'],'closed')

 def test_jotform_with_selectable_market_dates_is_classified_multidate(self):
  pages=Pages(reason='Cary Night Market Dates - Please only choose the markets you are prepared to pay for.')
  self.assertEqual(research.diagnose_one(lead(),pages)['status'],'multi_date')

 def test_apex_general_apply_menu_does_not_override_current_closure(self):
  source='https://www.apexfarmersmarket.com/'
  apply='https://www.apexfarmersmarket.com/apply'
  closed='https://www.apexfarmersmarket.com/applicationclose'
  pages=Pages()
  pages.docs[source]='<a href="'+apply+'">Apply Now</a>'
  pages.docs[apply]='<a href="'+closed+'">Application Closed!</a><p>Become a Vendor</p>'
  pages.docs[closed]='<h1>Applications closed!</h1><p>Come back in January!</p>'
  lead={'source_url':source,'target_url':apply,'title':'Apply Now'}
  self.assertEqual(research.diagnose_one(lead,pages)['status'],'closed')

 def test_generic_closed_status_link_on_another_organizer(self):
  source='https://www.carrborofarmersmarket.com/'
  target='https://www.carrborofarmersmarket.com/apply'
  status='https://www.carrborofarmersmarket.com/application-closed'
  pages=Pages()
  pages.docs[source]='<a href="'+target+'">Apply to the Market</a>'
  pages.docs[target]='<h1>Apply to the Market</h1><a href="'+status+'">Applications Closed</a>'
  pages.docs[status]='Applications for 2026 market season are now closed.'
  result=research.diagnose_one(
   {'source_url':source,'target_url':target,'title':'Apply to the Market'},pages)
  self.assertEqual(result['status'],'closed')

 def test_offsite_closure_status_is_never_fetched(self):
  source='https://www.carrborofarmersmarket.com/'
  target='https://www.carrborofarmersmarket.com/apply'
  pages=Pages()
  pages.docs[source]='<a href="'+target+'">Apply to the Market</a>'
  pages.docs[target]='<a href="https://example.com/private">Applications Closed</a>'
  result=research.diagnose_one(
   {'source_url':source,'target_url':target,'title':'Apply to the Market'},pages)
  self.assertEqual(result['status'],'missing_event')
  self.assertEqual(pages.requests,2)

 def test_linked_third_party_page_does_not_crash_worker(self):
  source='https://artspacenc.org/calls-for-art/'
  outside='https://www.bigink.org/workshops/artspace-2027/'
  pages=Pages()
  pages.docs[source]='<a href="'+outside+'">Learn More: Registration closes February 1, 2027</a>'
  result=research.diagnose_one(
   {'source_url':source,'target_url':outside,'title':'Learn More: Registration closes February 1, 2027'},pages)
  self.assertEqual(result['status'],'needs_evidence')
  self.assertEqual(pages.requests,1)

 def test_generic_application_index_is_monitored_not_counted_as_event(self):
  source='https://www.trianglepopup.com/applications'
  target='https://www.trianglepopup.com/vendor-info'
  pages=Pages()
  pages.docs[source]='<a href="'+target+'">Vendor Info</a>'
  pages.docs[target]=('<h1>Vendor Information</h1><a href="https://form.jotform.com/233513866839165">Apply at Crabtree</a>')
  data={'target_url':target,'source_url':source,'title':'Vendor Info'}
  result=research.diagnose_one(data,pages)
  self.assertEqual(result['status'],'application_directory')

 def test_directory_without_current_link_is_not_monitorable(self):
  source='https://www.trianglepopup.com/applications'
  target='https://www.trianglepopup.com/vendor-info'
  pages=Pages()
  pages.docs[source]='<a href="https://www.trianglepopup.com/other">Other</a>'
  pages.docs[target]='<h1>Vendor information</h1><a href="https://form.jotform.com/233513866839165">Apply</a>'
  result=research.diagnose_one({'source_url':source,'target_url':target,'title':'Vendor Info'},pages)
  self.assertEqual(result['status'],'unlinked')

 def test_be_a_vendor_label_is_actually_read_before_classification(self):
  pages=Pages(reason='Applications for 2026 market season are now closed.')
  entry={**lead(),'title':'Be A Vendor'}
  self.assertEqual(research.diagnose_one(entry,pages)['status'],'closed')
  self.assertEqual(pages.requests,2)

 def test_guest_vendors_label_is_checked_and_closed(self):
  pages=Pages(reason='The Market is not currently accepting guest vendor applications.')
  entry={**lead(),'title':'Guest Vendors'}
  self.assertEqual(research.diagnose_one(entry,pages)['status'],'closed')
  self.assertEqual(pages.requests,2)

 def test_currently_not_accepting_word_order_is_recognized(self):
  pages=Pages(reason='Our market is currently not accepting new applications.')
  self.assertEqual(research.diagnose_one(lead(),pages)['status'],'closed')

 def test_instructional_workshop_is_not_a_vendor_market(self):
  pages=Pages(reason='BIG INK printmaking workshop registration. Participants attend a printing day after an online master class.')
  entry={**lead(),'title':'Learn More: Registration closes February 1'}
  self.assertEqual(research.diagnose_one(entry,pages)['status'],'not_application')

 def test_permanent_store_consignment_is_not_an_event_application(self):
  pages=Pages(reason='You are applying to have your products sold at Curate in downtown Raleigh. This is an at-will contract with no stated ending date following acceptance.')
  entry={**lead(),'title':'Curate Downtown Raleigh'}
  self.assertEqual(research.diagnose_one(entry,pages)['status'],'not_application')

 def test_real_market_application_is_not_falsely_excluded(self):
  pages=Pages(reason='Cary Night Market 2026 Vendor Application. Apply to vend on December 18, 2026. Submit Form.')
  result=research.diagnose_one(lead(),pages)
  self.assertNotEqual(result['status'],'not_application')

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

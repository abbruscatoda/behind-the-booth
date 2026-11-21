"""Form research regression cases: multipage schema, official PDFs, access gaps."""
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from verifier import Document
from google_forms import read_public_form
from published_form_metadata import public_form_sections
from official_fee_documents import fee_document_links, inspect_official_fee_documents

FORM='https://docs.google.com/forms/d/e/1FAIpQLSf-4catG9HnDm1XodMjUij_nel5Fvf4jzilVc0XXtWb21v93Q/viewform'
ORGANIZER='https://westernwakefarmersmarket.org/events/winterwonderland2026'
PDF='https://westernwakefarmersmarket.org/s/Vendor-Fee-Schedule-v01-2025.pdf'

PUBLIC_SCHEMA=(
 '<script>var FB_PUBLIC_LOAD_DATA_ = '
 '[null,[null,[["Application fees","$10 nonrefundable application fee, waived for current vendors."],'
 '["Page 2 booth terms","$30 per event: 10x10 booth fee, payable upon acceptance."]]]];</script>'
)


class CoverageTests(unittest.TestCase):
 def test_read_publicly_authored_google_schema_across_pages(self):
  doc=Document('<h1>WWFM Craft Fair Vendor Registration</h1>'
               '<p>Registration details on page one.</p>'
               '<div role="button">Next</div>'+PUBLIC_SCHEMA)
  facts=read_public_form(doc)
  self.assertEqual(facts['application_fee'],10)
  self.assertEqual(facts['booth_fee'],30)
  self.assertFalse(facts['complete'])
  self.assertGreaterEqual(facts['published_schema_fee_sections'],2)

 def test_researches_author_linked_table_of_fees_on_later_page(self):
  form=Document('<h1>Vendor Application</h1>'
    '<div role="button">Next</div>'
    '<script>var FB_PUBLIC_LOAD_DATA_ = [null,[null,[["Page 2",'
    '"See &lt;a href=\\"https://westernwakefarmersmarket.org/s/Vendor-Fee-Schedule-v01-2025.pdf\\"&gt;Table of Fees&lt;/a&gt;."],'
    '["Requirement","Food vendors must provide current liability insurance and NC Sales Tax ID."]]]];</script>')
  links=fee_document_links(form,FORM,ORGANIZER)
  self.assertEqual(links,[PDF])
  facts=read_public_form(form)
  self.assertIn('insurance',facts['eligibility'])
  self.assertFalse(facts['complete'])

 def test_do_not_promote_raw_hidden_script_or_random_json(self):
  doc=Document('<h1>Other public form</h1><p>Please register</p>'
               '<script>var OTHER_DATA = [null,[["$999 booth fee"]]];</script>'
               '<input hidden value="$666 booth fee"/>'
               '<div role="button">Next</div>')
  facts=read_public_form(doc)
  self.assertEqual(facts['published_schema_fee_sections'],0)
  self.assertIsNone(facts['booth_fee'])

 def test_broken_or_oversized_form_schema_gracefully_falls_back(self):
  doc=Document('<h1>Application</h1><p>Pay $15 application fee.</p>'
               '<script>var FB_PUBLIC_LOAD_DATA_ = {invalid};</script>'
               '<div role="button">Next</div>')
  self.assertEqual(public_form_sections(doc),[])
  self.assertEqual(read_public_form(doc)['application_fee'],15)

 def test_official_pdf_link_from_application_or_organizer(self):
  organizer=Document('<h1>WWFM craft fair</h1><a href="/s/Vendor-Fee-Schedule-v01-2025.pdf">Vendor Fee Schedule</a>')
  form=Document('<h1>WWFM craft registration</h1>'
                '<a href="'+PDF+'">Table of Fees</a>')
  evidence=inspect_official_fee_documents(
    [(organizer,ORGANIZER),(form,FORM)], ORGANIZER,
    reader=lambda url,origin: (
      'Vendor Fee Schedule. Additional Fees: Second Space Fee $20. '
      'Co-op Vending Arrangement Fee Assessed per tent: $10.', 'b'*64))
  self.assertEqual(evidence['linked_count'],1)
  self.assertEqual(evidence['readable_count'],1)
  self.assertTrue(evidence['complete'])
  self.assertEqual(evidence['documents'][0]['optional_fees'],
                   {'second_space':20,'co_op_tent':10})

 def test_blocked_fee_document_is_not_silently_marked_readable(self):
  organizer=Document('<a href="'+PDF+'">Table of Fees</a>')
  def blocked(url,organizer_url):
   raise HTTPError(url,401,'Unauthorized',{},None)
  evidence=inspect_official_fee_documents([(organizer,ORGANIZER)],ORGANIZER,reader=blocked)
  self.assertEqual(evidence['blocked_count'],1)
  self.assertEqual(evidence['readable_count'],0)
  self.assertFalse(evidence['complete'])

 def test_reject_external_or_credentials_or_query_pdf_links(self):
  doc=Document('<a href="https://evil.example/vendors.pdf">Table of Fees</a>'
               '<a href="http://westernwakefarmersmarket.org/s/fee-schedule.pdf">Vendor Fee Schedule</a>'
               '<a href="https://westernwakefarmersmarket.org/s/fee-schedule.pdf?token=secret">Fee Schedule</a>'
               '<a href="'+PDF+'">Fee Schedule</a>')
  self.assertEqual(fee_document_links(doc,ORGANIZER,ORGANIZER),[PDF])

 def test_unrelated_regular_vendor_rates_never_define_specific_event_booth(self):
  from form_fees import extract_linked_fee_options,extract_labeled_fees
  pdf='Regular market vendor daily rate $30; guest vendor $40. Second Space Fee $20.'
  self.assertIsNone(extract_labeled_fees(pdf)['booth_fee'])
  self.assertEqual(extract_linked_fee_options(pdf)['second_space'],20)


if __name__=='__main__':
 unittest.main()

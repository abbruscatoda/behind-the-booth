"""Regression coverage for the held Western Wake December craft fair."""
import unittest
from datetime import datetime,timezone
from urllib.error import HTTPError
from verifier import Document,Uncertain
import western_craft_fair as craft

NOW=datetime(2026,11,21,14,tzinfo=timezone.utc)
SOURCE='<h1>Winter Wonderland Craft Fair</h1><p>Saturday, December 12, 2026</p><p>Craft vendors: <a href="'+craft.EVENT_LINK+'">register here</a>. Registration deadline: 11/28/26 or until spots are filled.</p>'
APPLY='<h2>Craft Fair Application</h2><a href="'+craft.CRAFT_LINK+'">Craft Fair Application</a><a href="https://westernwakefarmersmarket.org/s/Vendor-Fee-Schedule-v01-2025.pdf">Download Fees PDF</a>'
PDF='Craft Vendor Application Fee Covers craft review costs $10 Returning Vendor Application Fee $25 Vendors applying specifically to our seasonal craft fairs will submit payment in the amount of $10 with their craft application. Regular market Guest Vendor Daily Rate $30.'
FORM='<h1>Western Wake Farmers Market craft fair</h1><p>2026 Craft Fair for artisans at Indian Creek Trailhead in Morrisville. Please provide business and contact information to register for the December 12 fair. $12 application fee. $45 event booth fee.</p><button>Next</button>'

class Fetch:
 def __init__(self,event=SOURCE,apply=APPLY,form=FORM):
  self.pages={craft.EVENT:event,craft.APPLY:apply,craft.FORM:form}
 def get(self,url):
  if url==craft.FORM and self.pages[url] is None:
   raise HTTPError(url,401,'Unauthorized',{},None)
  return Document(self.pages[url]),'a'*64

def pdf(url):
 return PDF,'b'*64

class WesternCraftTests(unittest.TestCase):
 def test_blocked_google_form_uses_only_pdf_craft_fee(self):
  r=craft.verify_western_craft(Fetch(form=None),NOW,pdf)
  self.assertEqual(r['candidate']['application_fee'],10)
  self.assertIsNone(r['candidate']['booth_fee'])
  self.assertEqual(r['candidate']['availability'],'open')
  self.assertEqual(r['application_access'],'http_auth_blocked')
  self.assertEqual(r['fee_pdf_hash'],'b'*64)
  self.assertIn('not presumed',r['candidate']['fee_notes'])

 def test_readable_public_form_pricing_takes_precedence(self):
  r=craft.verify_western_craft(Fetch(),NOW,pdf)
  self.assertEqual(r['candidate']['application_fee'],12)
  self.assertEqual(r['candidate']['booth_fee'],45)
  self.assertEqual(r['application_access'],'readable_first_page')

 def test_real_2026_craft_form_extracts_event_fee_waiver_and_pdf_addons(self):
  form=('<h1>WWFM Craft Fair Vendor Registration</h1>'
        '<p>We are accepting craft vendors during the 2026-27 season.</p>'
        "<h3>CRAFT FAIR FEES:</h3><p>$10 nonrefundable application fee, "
        "payable when application is submitted (waived for current vendors).</p>"
        "<p>$30 per event: 10'x10' booth fee, payable upon acceptance.</p>"
        '<p>See Table of Fees for a second tent or cooperative vending.</p>'
        '<p>Winter Wonderland Craft Fair (December 12), deadline November 28.</p>'
        '<button>Next</button>')
  pdf_full=(PDF+" Additional Fees Second Space Fee Available if space permits $20 "
            "Co-op Vending Arrangement Fee Assessed per tent; see Rules for details. $10")
  result=craft.verify_western_craft(Fetch(form=form),NOW,lambda url:(pdf_full,'b'*64))
  self.assertEqual(result['candidate']['booth_fee'],30)
  self.assertEqual(result['candidate']['application_fee'],10)
  self.assertIn('waived for current vendors',result['candidate']['fee_notes'])
  self.assertIn('$20.00',result['candidate']['fee_notes'])
  self.assertIn('$10.00 per tent',result['candidate']['fee_notes'])
  self.assertEqual(result['fee_evidence']['pdf_optional_fees'],
                   {'second_space':20.0,'co_op_tent':10.0})

 def test_after_published_registration_date_is_closed_automatically(self):
  r=craft.verify_western_craft(Fetch(form=None),datetime(2026,11,29,15,tzinfo=timezone.utc),pdf)
  self.assertEqual(r['candidate']['availability'],'closed')

 def test_mismatched_official_form_link_stays_uncertain(self):
  with self.assertRaises(Uncertain):
   craft.verify_western_craft(Fetch(event=SOURCE.replace(craft.EVENT_LINK,'https://forms.gle/some-other-form')),NOW,pdf)

 def test_no_unverified_regular_market_fee(self):
  self.assertEqual(craft.craft_fee_from_pdf(PDF),10)
  with self.assertRaises(Uncertain):
   craft.craft_fee_from_pdf('New Vendor Application Fee $35 Guest Vendor Daily Rate $30')

 def test_pdf_failure_does_not_close_application_or_guess_fee(self):
  def blocked(_):
   raise HTTPError('https://westernwakefarmersmarket.org',403,'Forbidden',{},None)
  r=craft.verify_western_craft(Fetch(form=None),NOW,blocked)
  self.assertEqual(r['candidate']['availability'],'open')
  self.assertIsNone(r['candidate']['application_fee'])
  self.assertIsNone(r['candidate']['booth_fee'])

if __name__=='__main__':unittest.main()

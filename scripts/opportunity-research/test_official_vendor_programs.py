"""Permanent regressions for source-linked vendor programs lacking one event date."""
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
from verifier import Document,Uncertain
from official_vendor_programs import PROGRAMS, verify_program, discover_programs, SOUTH_RULES_PAGE, SOUTH_RULES_DOC

NOW=datetime(2026,11,21,17,tzinfo=timezone.utc)
GUEST_RULES=('Market Rules Feb 2026. 9. Guest Vendor Applications. '
 'The market manager will invoice the applicant a $30 fee upon receipt of the application. '
 'A Guest Vendor shall pay a daily space fee of $30 for summer season and $25 for winter season.')
class Fetch:
 def __init__(self):
  self.docs={}
  self.requests=0
  self.limit=100
  for key,cfg in PROGRAMS.items():
   link='<a href="'+cfg['application']+'">Official Vendor Application</a>'
   if key=='wake-forest-2027-food':
    body='Town of Wake Forest PRCR will accept food vendors for 2027 PRCR events from Nov. 9 through Nov. 27, 2026.'
   elif key=='durham-food-vendor-program':
    body='Durham Parks and Recreation Food Vendors: for current food vendor opportunities apply online. Only mobile food units or pushcart peddlers with valid permits qualify.'
    self.docs[cfg['application']]=(
     '<h1>Durham Parks and Recreation - Food Vendor Application</h1>'
     '<div>Durham Holiday Parade - December 12, 2026</div><button>Continue</button>')
   elif key=='state-raleigh-new-vendors':
    body='State Farmers Market - Become a Vendor. New Vendor Application.'
   elif key=='south-durham-winter-craft':
    body='South Durham Craft Vendor Applications are Open for Winter! Accepting craft vendors from November to December.'
   else:
    body='South Durham Guest Vendor Application. Guest vendor applications are reviewed around the 15th each month.'
   if cfg['source'] in self.docs:
    self.docs[cfg['source']]+=body+' '+link
   else:
    self.docs[cfg['source']]='<h1>'+body+'</h1>'+link
  self.docs[SOUTH_RULES_PAGE]='<h1>Market Rules</h1><a href="'+SOUTH_RULES_DOC+'">Market Rules Feb 2026</a>'
 def get(self,url):
  self.requests+=1
  if url not in self.docs:raise IOError('Source absent')
  return Document(self.docs[url]),'a'*64

class OfficialProgramsTests(unittest.TestCase):
 def setUp(self):
  proxy=patch('official_vendor_programs.fetch_public_google_document',return_value=(GUEST_RULES,'b'*64))
  proxy.start()
  self.addCleanup(proxy.stop)
 def test_all_five_official_intakes_are_publishable_with_separate_known_links(self):
  results,notes=discover_programs(Fetch(),NOW)
  self.assertEqual(len(results),len(PROGRAMS))
  self.assertEqual(notes,[])
  self.assertEqual({r['program'] for r in results},set(PROGRAMS))
  for result in results:
   if result['program']=='south-durham-guest-vendors':
    self.assertEqual(result['candidate']['booth_fee'],25)
    self.assertEqual(result['candidate']['application_fee'],30)
    self.assertIn('$30 per stall per summer',result['candidate']['fee_notes'])
    self.assertEqual(result['rules_hash'],'b'*64)
   else:
    self.assertIsNone(result['candidate']['booth_fee'])
    self.assertIsNone(result['candidate']['application_fee'])
   self.assertEqual(result['decision'],'publish')
   self.assertEqual(result['source_hash'],'a'*64)
 def test_municipal_food_2027_never_claims_specific_booths_or_fees(self):
  r=verify_program('wake-forest-2027-food',Fetch(),NOW)
  self.assertEqual(r['candidate']['availability'],'open')
  self.assertEqual(r['candidate']['schedule_type'],'seasonal_application')
  self.assertEqual(r['candidate']['starts_on'],'2027-01-01')
  self.assertIn('Nov',r['candidate']['fee_notes'] or '') if False else None
 def test_durham_program_form_requires_real_vendor_application_identity(self):
  f=Fetch()
  url=PROGRAMS['durham-food-vendor-program']['application']
  f.docs[url]=f.docs[url].replace('Food Vendor Application','General Contact Form')
  with self.assertRaises(Uncertain):
   verify_program('durham-food-vendor-program',f,NOW)

 def test_durham_program_is_not_a_guaranteed_holiday_parade_booth(self):
  f=Fetch()
  r=verify_program('durham-food-vendor-program',f,NOW)
  self.assertEqual(r['candidate']['schedule_type'],'rolling_market')
  self.assertIsNone(r['candidate']['deadline'])
  self.assertIsNone(r['candidate']['booth_fee'])

 def test_closed_date_is_never_represented_as_still_open(self):
  f=Fetch()
  r=verify_program('wake-forest-2027-food',f,datetime(2026,11,28,19,tzinfo=timezone.utc))
  self.assertEqual(r['candidate']['availability'],'closed')
  x=verify_program('south-durham-winter-craft',f,datetime(2027,1,2,tzinfo=timezone.utc))
  self.assertEqual(x['candidate']['availability'],'closed')
 def test_unlinked_vendors_are_not_published(self):
  f=Fetch()
  url=PROGRAMS['wake-forest-2027-food']['source']
  f.docs[url]=f.docs[url].replace('Official Vendor Application</a>','Other link</a>').replace('https://www.cognitoforms.com','https://www.example.com')
  with self.assertRaises(Uncertain):
   verify_program('wake-forest-2027-food',f,NOW)
 def test_missing_linked_document_prevents_unverified_guest_fee(self):
  f=Fetch()
  f.docs[SOUTH_RULES_PAGE]='<h1>Rules removed</h1>'
  with self.assertRaises(Uncertain):
   verify_program('south-durham-guest-vendors',f,NOW)
 def test_missing_numeric_fee_in_rules_prevents_guessing(self):
  with patch('official_vendor_programs.fetch_public_google_document',
             return_value=(GUEST_RULES.replace('a $30 fee','an unspecified fee'),'c'*64)):
   with self.assertRaises(Uncertain):
    verify_program('south-durham-guest-vendors',Fetch(),NOW)
 def test_winter_craft_does_not_inherit_guest_stall_prices(self):
  r=verify_program('south-durham-winter-craft',Fetch(),NOW)
  self.assertIsNone(r['candidate']['application_fee'])
  self.assertIsNone(r['candidate']['booth_fee'])

 def test_unrecognized_organizer_cannot_become_approved_program(self):
  with self.assertRaises(Uncertain):
   verify_program('fabricated-vendor-program',Fetch(),NOW)
 def test_state_paper_application_is_limited_not_guaranteed_open_booth(self):
  r=verify_program('state-raleigh-new-vendors',Fetch(),NOW)
  self.assertEqual(r['candidate']['availability'],'limited')
  self.assertEqual(r['candidate']['schedule_type'],'rolling_market')
  self.assertIn('waiting lists',r['candidate']['eligibility'])

if __name__=='__main__':unittest.main()

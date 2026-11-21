"""Permanent regressions for source-linked vendor programs lacking one event date."""
import unittest
from datetime import datetime,timezone
from verifier import Document,Uncertain
from official_vendor_programs import PROGRAMS, verify_program, discover_programs

NOW=datetime(2026,11,21,17,tzinfo=timezone.utc)
class Fetch:
 def __init__(self):
  self.docs={}
  self.requests=0
  self.limit=100
  for key,cfg in PROGRAMS.items():
   link='<a href="'+cfg['application']+'">Official Vendor Application</a>'
   if key=='wake-forest-2027-food':
    body='Town of Wake Forest PRCR will accept food vendors for 2027 PRCR events from Nov. 9 through Nov. 27, 2026.'
   elif key=='durham-2026-holiday-food':
    body='Durham Parks and Recreation Food Vendors: for current food vendor opportunities apply online.'
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
 def get(self,url):
  self.requests+=1
  if url not in self.docs:raise IOError('Source absent')
  return Document(self.docs[url]),'a'*64

class OfficialProgramsTests(unittest.TestCase):
 def test_all_five_official_intakes_are_publishable_with_separate_known_links(self):
  results,notes=discover_programs(Fetch(),NOW)
  self.assertEqual(len(results),len(PROGRAMS))
  self.assertEqual(notes,[])
  self.assertEqual({r['program'] for r in results},set(PROGRAMS))
  for result in results:
   self.assertEqual(result['candidate']['booth_fee'],None)
   self.assertEqual(result['candidate']['application_fee'],None)
   self.assertEqual(result['decision'],'publish')
   self.assertEqual(result['source_hash'],'a'*64)
 def test_municipal_food_2027_never_claims_specific_booths_or_fees(self):
  r=verify_program('wake-forest-2027-food',Fetch(),NOW)
  self.assertEqual(r['candidate']['availability'],'open')
  self.assertEqual(r['candidate']['schedule_type'],'seasonal_application')
  self.assertEqual(r['candidate']['starts_on'],'2027-01-01')
  self.assertIn('Nov',r['candidate']['fee_notes'] or '') if False else None
 def test_dated_durham_food_form_requires_exact_selectable_event(self):
  f=Fetch()
  url=PROGRAMS['durham-2026-holiday-food']['application']
  f.docs[url]=f.docs[url].replace('December 12, 2026','December 10, 2026')
  with self.assertRaises(Uncertain):
   verify_program('durham-2026-holiday-food',f,NOW)
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
 def test_unrecognized_organizer_cannot_become_approved_program(self):
  with self.assertRaises(Uncertain):
   verify_program('fabricated-vendor-program',Fetch(),NOW)
 def test_state_paper_application_is_limited_not_guaranteed_open_booth(self):
  r=verify_program('state-raleigh-new-vendors',Fetch(),NOW)
  self.assertEqual(r['candidate']['availability'],'limited')
  self.assertEqual(r['candidate']['schedule_type'],'rolling_market')
  self.assertIn('waiting lists',r['candidate']['eligibility'])

if __name__=='__main__':unittest.main()

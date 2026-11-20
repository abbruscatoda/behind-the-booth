"""Regression checks for source-linked future multi-date application parsing."""
import unittest
from datetime import datetime,timezone
from verifier import Document,Uncertain
from multidate_research import verify_provider,PROVIDERS

ROOT=PROVIDERS[0]['market_root']
SOURCE=PROVIDERS[0]['source']
FORM=PROVIDERS[0]['form_hint']
NOW=datetime(2026,11,19,22,tzinfo=timezone.utc)
class Pages:
 def __init__(self):
  self.docs={
   ROOT:'<a href="'+SOURCE+'">Plan Your Markets</a>',
   SOURCE:('<h1>Applications Are Now OPEN!</h1>'
           '<p>If market dates are still on the application, that means we are still accepting vendors for that date!</p>'
           '<a href="'+FORM+'">Cary Night Market Vendor Application</a>'),
   FORM:('<h1>The Night Market Company Vendor Application</h1><h2>Fall Cary Night Market 2026</h2>'
         '<p>Application Fee: $10.00 non-refundable</p>'
         '<p>October 16, 2026 Market $140.00</p>'
         '<p>December 18, 2026 Market 5pm-9pm $140.00</p>'
         '<p>December 19, 2027 Market $140.00</p>'
         '<button>Submit Form</button>')
  }
 def get(self,url):
  if url not in self.docs:raise ValueError('Unapproved document')
  return Document(self.docs[url]),'a'*64

class MultiDateTests(unittest.TestCase):
 def test_publishes_only_future_dates_explicitly_offered(self):
  result=verify_provider(PROVIDERS[0],Pages(),NOW)
  self.assertEqual(len(result),1)
  self.assertEqual(result[0]['candidate']['starts_on'],'2026-12-18')
  self.assertEqual(result[0]['candidate']['booth_fee'],140)
  self.assertEqual(result[0]['candidate']['application_fee'],10)
  self.assertEqual(result[0]['policy'],'triangle-multidate-jotform-v1')

 def test_rejects_unlinked_application(self):
  fetch=Pages()
  fetch.docs[SOURCE]=fetch.docs[SOURCE].replace(FORM,'https://pci.jotform.com/form/000000000000000')
  with self.assertRaises(Uncertain):verify_provider(PROVIDERS[0],fetch,NOW)

 def test_rejects_closed_form(self):
  fetch=Pages()
  fetch.docs[FORM]+='<p>Applications are closed</p>'
  with self.assertRaises(Uncertain):verify_provider(PROVIDERS[0],fetch,NOW)

 def test_rejects_mismatched_form_year(self):
  fetch=Pages()
  fetch.docs[FORM]=fetch.docs[FORM].replace('Fall Cary Night Market 2026','Fall Cary Night Market 2025')
  with self.assertRaises(Uncertain):verify_provider(PROVIDERS[0],fetch,NOW)

 def test_does_not_publish_old_dates_or_2027_typos(self):
  fetch=Pages()
  fetch.docs[FORM]=fetch.docs[FORM].replace('December 18, 2026 Market','December 18, 2025 Market')
  self.assertEqual(verify_provider(PROVIDERS[0],fetch,NOW),[])

if __name__=='__main__':unittest.main()

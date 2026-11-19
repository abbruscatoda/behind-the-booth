"""Saved lead research never treats an old link as publication evidence."""
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from verifier import Document
import discovery

NOW=datetime(2026,11,18,20,tzinfo=timezone.utc)
ROOT='https://www.trianglepopup.com/applications'
def lead(n):
 return {'source_url':ROOT,
   'target_url':f'https://www.trianglepopup.com/apply-to-be-a-vendor-{n:03d}',
   'title':'Vendor Application','organizer':'Triangle Pop-Up','city':'Raleigh'}

class Pages:
 def __init__(self,links):
  self.root=Document(''.join('<a href="'+url+'">Vendor Application</a>' for url in links))
 def get(self,url):
  if url==ROOT:return self.root,'a'*64
  raise ValueError('No unrelated web pages available')

class BacklogTests(unittest.TestCase):
 def test_previous_lead_is_prioritized_even_with_many_new_links(self):
  urls=[lead(i)['target_url'] for i in range(150)]
  saved=lead(149)
  checked=[]
  def inspect(entry,fetcher,now):
   checked.append(entry['target_url'])
   return None
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]),patch('form_discovery.verify_public_form',side_effect=inspect):
   _,_,stats=discovery.discover_triangle(Pages(urls),NOW,include_search=False,include_calendars=False,backlog=[saved])
  self.assertTrue(checked)
  self.assertEqual(checked[0],saved['target_url'])
  self.assertEqual(stats['previous_leads_rechecked'],1)

 def test_unlinked_old_application_cannot_reenter_verification(self):
  existing=lead(1)
  stale=lead(999)
  checked=[]
  def inspect(entry,fetcher,now):
   checked.append(entry['target_url'])
   return None
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]),patch('form_discovery.verify_public_form',side_effect=inspect):
   _,_,stats=discovery.discover_triangle(Pages([existing['target_url']]),NOW,include_search=False,include_calendars=False,backlog=[stale])
  self.assertNotIn(stale['target_url'],checked)
  self.assertEqual(stats['previous_leads_rechecked'],0)

 def test_saved_lead_from_unapproved_source_is_ignored(self):
  saved={'source_url':'https://untrusted.example/vendors',**lead(3)}
  saved['source_url']='https://untrusted.example/vendors'
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]):
   _,_,stats=discovery.discover_triangle(Pages([lead(3)['target_url']]),NOW,include_search=False,include_calendars=False,backlog=[saved])
  self.assertEqual(stats['previous_leads_rechecked'],0)

if __name__=='__main__':unittest.main()

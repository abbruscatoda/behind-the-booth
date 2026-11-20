"""Regression cases from real 2026 Triangle lead classification mistakes."""
import unittest
from urllib.error import HTTPError
from verifier import Document
from lead_reconciliation import reconcile_shortcuts,resolve_shortcut,google_form_identity

ROOT='https://www.artsplosure.org/first-night-raleigh'
SHORT='https://forms.gle/e8JRmQUUcEirUzzY9'
FULL='https://docs.google.com/forms/d/e/1FAIpQLScPXt0euH9ziXcAR3tA9BkXTQ4qtnTK9V6aqttIYbxlittBlA/viewform'
OTHER='https://forms.gle/ZHrbGDeeoLobscM39'
class Response:
 def __init__(self,url):self.url=url
 def geturl(self):return self.url
 def __enter__(self):return self
 def __exit__(self,*args):return False

class Opener:
 def __init__(self,mapping):self.mapping=mapping
 def open(self,request,timeout):
  u=request.full_url
  if u not in self.mapping:raise ValueError('Unapproved shortcut')
  dest=self.mapping[u]
  if isinstance(dest,Exception):raise dest
  return Response(dest)

class Fetch:
 def __init__(self,linked=True,mapping=None):
  self.requests=0;self.limit=100
  self.root=Document('<a href="'+SHORT+'">Apply Here</a>' if linked else '<a href="'+OTHER+'">Other form</a>')
  self.opener=Opener(mapping or {SHORT:FULL})
 def get(self,url):
  self.requests+=1
  if url!=ROOT:raise ValueError('Unexpected source URL')
  return self.root,'a'*64

def lead(target=SHORT,source=ROOT):
 return {'source_url':source,'target_url':target,'organizer':'Artsplosure','city':'Raleigh'}

class ShortcutRegressionTests(unittest.TestCase):
 def test_same_event_short_url_yields_canonical_receipt(self):
  out=reconcile_shortcuts([lead()],Fetch(),{ROOT})
  self.assertEqual(out,[{'source_url':ROOT,'target_url':SHORT,'canonical_application_url':FULL}])

 def test_google_401_after_redirect_still_proves_url_identity(self):
  error=HTTPError(FULL,401,'Unauthorized',{},None)
  fetch=Fetch(mapping={SHORT:error})
  self.assertEqual(resolve_shortcut(SHORT,fetch),FULL)

 def test_safe_google_share_query_can_canonicalize(self):
  self.assertEqual(google_form_identity(FULL+'?usp=sf_link'),FULL)
  self.assertEqual(google_form_identity(FULL+'?usp=sharing'),FULL)
  self.assertIsNone(google_form_identity(FULL+'?entry.221=private'))
  self.assertIsNone(google_form_identity(FULL+'?usp=sf_link&entry.221=private'))

 def test_unlinked_saved_shortcut_is_not_trusted(self):
  self.assertEqual(reconcile_shortcuts([lead()],Fetch(linked=False),{ROOT}),[])

 def test_unknown_official_source_is_not_researched(self):
  self.assertEqual(reconcile_shortcuts([lead(source='https://other.example/')],Fetch(),{ROOT}),[])

 def test_same_shortcut_on_wrong_target_is_not_canonical(self):
  self.assertIsNone(google_form_identity('https://docs.google.com/forms/d/e/x/edit'))
  self.assertIsNone(google_form_identity('https://docs.google.com/forms/d/e/'+FULL.split('/e/')[1].split('/')[0]+'/viewform?entry.123=abc'))
  self.assertIsNone(google_form_identity('https://example.com/forms/d/e/'+FULL.split('/e/')[1].split('/')[0]+'/viewform'))

 def test_shortcut_without_redirect_cannot_be_archived(self):
  self.assertEqual(reconcile_shortcuts([lead()],Fetch(mapping={SHORT:SHORT}),{ROOT}),[])

 def test_source_budget_prevents_unbounded_checks(self):
  fetch=Fetch();fetch.requests=fetch.limit-15
  self.assertEqual(reconcile_shortcuts([lead()],fetch,{ROOT}),[])
  self.assertEqual(fetch.requests,fetch.limit-15)

 def test_only_one_check_for_duplicate_source_shortcut(self):
  fetch=Fetch()
  self.assertEqual(len(reconcile_shortcuts([lead(),lead()],fetch,{ROOT})),1)
  self.assertEqual(fetch.requests,2)

if __name__=='__main__':unittest.main()

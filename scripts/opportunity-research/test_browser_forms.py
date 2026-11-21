"""Google Forms browser fallback is read-only, bounded, and optional."""
import io,os,unittest
from urllib.error import HTTPError
from unittest.mock import patch
from verifier import Fetcher,Document
from browser_forms import public_google_form,BrowserUnavailable
from form_probe import probe_public_form

FORM='https://docs.google.com/forms/d/e/1FAIpQLSdfqVaXAuhAV0Ujh7iEp-gHaViqeKEEz5Lq9BqM-ayGyof2TA/viewform'
SHORT='https://forms.gle/e8JRmQUUcEirUzzY9'

class FakeResponse:
 def __init__(self,content):
  self.url=FORM;self.headers={'Content-Type':'text/html'}
  self.content=content.encode()
 def read(self,n):return self.content
 def __enter__(self):return self
 def __exit__(self,*args):return False
class FakeOpener:
 def __init__(self,blocked=False,body='<h1>Loading</h1>'):
  self.blocked=blocked;self.body=body
 def open(self,*args,**kwargs):
  if self.blocked:
   raise HTTPError(FORM,401,'Denied',{},io.BytesIO(b''))
  return FakeResponse(self.body)

class PublicBrowserTests(unittest.TestCase):
 def test_read_only_navigation_collects_public_pages_without_submit(self):
  from browser_forms import _collect_public_pages
  class Fake:
   url=FORM
   def __init__(self,stuck=False):
    self.pages=['Page 1: $10 craft application fee',
                'Page 2: $30 per event: 10x10 booth fee',
                'Page 3: Insurance required; Submit']
    self.index=0
    self.clicked=[]
    self.stuck=stuck
   def content(self):
    return '<h1>'+self.pages[self.index]+'</h1>'
   def locator(self,selector):
    assert selector=='body'
    return self
   def inner_text(self,timeout=3000):
    return self.pages[self.index]
   def wait_for_timeout(self,ms):
    pass
   def get_by_role(self,kind,name,exact):
    assert kind=='button' and exact
    self.label=name
    return self
   def count(self):
    return int((self.label=='Submit' and self.index==2)
               or (self.label=='Next' and self.index<2))
   @property
   def first(self):
    return self
   def click(self,timeout=1800):
    if self.label!='Next':
     raise AssertionError('A public-form reader must not click Submit')
    self.clicked.append(self.label)
    if not self.stuck:
     self.index+=1
  page=Fake()
  snapshots,finished=_collect_public_pages(page,page.pages[0])
  self.assertEqual(len(snapshots),3)
  self.assertTrue(finished)
  self.assertEqual(page.clicked,['Next','Next'])
  blocked=Fake(stuck=True)
  snapshots,finished=_collect_public_pages(blocked,blocked.pages[0])
  self.assertEqual(len(snapshots),1)
  self.assertFalse(finished)

 def test_full_page_marker_is_only_accepted_with_submit_control(self):
  from google_forms import read_public_form
  partial=read_public_form(Document('<h1>Vendor form</h1><div role="button">Next</div>'
       '<span data-btb-all-public-pages-read="true"></span>'))
  self.assertFalse(partial['complete'])
  complete=read_public_form(Document('<h1>Vendor form</h1><div role="button">Next</div>'
       '<p>Booth fee: $30</p><div role="button">Submit</div>'
       '<span data-btb-all-public-pages-read="true"></span>'))
  self.assertTrue(complete['complete'])

 def test_public_forms_only_no_prefill_or_google_docs(self):
  self.assertTrue(public_google_form(FORM))
  self.assertTrue(public_google_form(SHORT))
  self.assertFalse(public_google_form(FORM+'?entry.123=private'))
  self.assertFalse(public_google_form('https://docs.google.com/document/d/test/edit'))
  self.assertFalse(public_google_form('https://accounts.google.com/signin'))

 def test_401_can_use_public_browser_render_without_submission(self):
  with patch.dict(os.environ,{'BTB_BROWSER_FALLBACK':'1'}):
   fetcher=Fetcher(limit=30)
  fetcher.opener=FakeOpener(blocked=True)
  rendered=(Document('<h1>Brewgaloo Vendor Form</h1><p>Booth fee $250</p>'),'a'*64)
  with patch('browser_forms.render_public_form',return_value=rendered):
   result=fetcher.get(FORM)
  self.assertEqual(result,rendered)
  self.assertEqual(fetcher.browser_attempts,1)
  self.assertEqual(fetcher.browser_successes,1)
  self.assertEqual(fetcher.get(FORM),rendered)
  self.assertEqual(fetcher.browser_attempts,1)

 def test_inaccessible_public_form_is_not_reported_as_readable(self):
  with patch.dict(os.environ,{'BTB_BROWSER_FALLBACK':'1'}):
   fetcher=Fetcher(limit=30)
  fetcher.opener=FakeOpener(blocked=True)
  with patch('browser_forms.render_public_form',side_effect=BrowserUnavailable('No access')):
   with self.assertRaises(HTTPError):
    fetcher.get(FORM)
  self.assertEqual(fetcher.browser_successes,0)
  self.assertEqual(fetcher.browser_failures.get('No access'),1)

 def test_untrusted_source_never_opens_browser(self):
  with patch.dict(os.environ,{'BTB_BROWSER_FALLBACK':'1'}):
   fetcher=Fetcher(limit=30)
  with patch('browser_forms.render_public_form') as browser:
   with self.assertRaises(ValueError):
    fetcher.get('https://evil.example/forms/viewform')
   browser.assert_not_called()

 def test_legacy_fetcher_mode_has_no_browser_dependency(self):
  with patch.dict(os.environ,{'BTB_BROWSER_FALLBACK':'0'}):
   fetcher=Fetcher(limit=30)
  fetcher.opener=FakeOpener(body='<h1>Regular HTML</h1>')
  with patch('browser_forms.render_public_form') as browser:
   result=fetcher.get(FORM)
   self.assertIn('Regular HTML',result[0].root.text())
   browser.assert_not_called()

 def test_fee_probe_never_asserts_unverified_booth_cost(self):
  class Reader:
   def get(self,url):
    return Document('<h1>Brewgaloo public vendor form</h1><p>Retail $225, Food truck $400</p>'),'a'*64
  report=probe_public_form(Reader())
  self.assertEqual(report['dollar_amounts_found'],[225,400])
  self.assertTrue(report['price_not_confirmed'])
if __name__=='__main__':unittest.main()

"""Read-only Playwright fallback for public Google Forms.

Only approved public /forms/d/e/.../viewform and forms.gle URLs. Browser
does not submit forms, log in, bypass access restrictions, or follow external
links. Never parse visitor responses or prefilled query parameters.
Playwright is imported lazily so ordinary verifier tests need no dependency.
"""
from __future__ import annotations
from hashlib import sha256
from html import escape
from urllib.parse import urlparse
import re

from verifier import Document, valid_url, MAX_SOURCE_BYTES

ALLOWED_SUBRESOURCE_HOSTS={
 'docs.google.com','forms.gle','www.gstatic.com','ssl.gstatic.com',
 'fonts.gstatic.com','fonts.googleapis.com','lh3.googleusercontent.com',
}
GOOGLE_FORM=re.compile(r'/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform')

class BrowserUnavailable(Exception):
 pass

def public_google_form(url):
 if not valid_url(url):return False
 p=urlparse(url)
 return (p.hostname=='forms.gle'
     or (p.hostname=='docs.google.com' and GOOGLE_FORM.fullmatch(p.path) is not None))

def _collect_public_pages(page, first_visible, max_extra_pages=5):
 """Capture only public text/links while optionally advancing a Next control.

 No field is filled. POST/PUT/DELETE requests remain blocked by the caller.
 A required field usually prevents advancing and leaves the walk incomplete.
 The Submit button is NEVER clicked.
 """
 snapshots=[(page.content(), first_visible)]
 current=first_visible
 reached_submit=False
 for _ in range(max_extra_pages+1):
  submit=page.get_by_role('button',name='Submit',exact=True)
  if submit.count():
   reached_submit=True
   break
  nxt=page.get_by_role('button',name='Next',exact=True)
  if not nxt.count() or len(snapshots)>max_extra_pages:
   break
  try:
   nxt.first.click(timeout=1800)
   page.wait_for_timeout(350)
   updated=page.locator('body').inner_text(timeout=3000)
  except Exception:
   break
  if not public_google_form(page.url.split('?')[0]):
   break
  if not updated.strip() or updated.strip()==current.strip():
   break
  if re.search(r'you need permission|request access|sign in to continue',updated,re.I):
   break
  if any(updated == previous for _,previous in snapshots):
   break
  snapshots.append((page.content(),updated))
  current=updated
 return snapshots,reached_submit


def render_public_form(url,timeout_ms=16000):
 """Return Document/hash only when a public form loaded successfully."""
 if not public_google_form(url):raise BrowserUnavailable('Not a public Google Form')
 try:
  from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
 except ImportError as exc:
  raise BrowserUnavailable('Browser package unavailable') from exc
 try:
  with sync_playwright() as playwright:
   browser=playwright.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    context=browser.new_context(
     java_script_enabled=True,accept_downloads=False,
     service_workers='block',ignore_https_errors=False,
     locale='en-US',timezone_id='America/New_York')
    page=context.new_page()
    page.set_default_timeout(4000)
    def guard(route):
     req=route.request
     parsed=urlparse(req.url)
     # Never submit an application, even if a site initiates a request.
     if req.method.upper() not in ('GET','HEAD') or parsed.scheme!='https':
      return route.abort()
     if parsed.hostname not in ALLOWED_SUBRESOURCE_HOSTS:return route.abort()
     if req.resource_type in ('image','media','font','stylesheet'):return route.abort()
     return route.continue_()
    page.route('**/*',guard)
    # Only the official published form and Google's public embed view.
    # Never submit, authenticate, or access respondent content.
    last_status='unknown'
    for candidate in ((url,url+'?embedded=true') if '/viewform' in url else (url,)):
     try:
      response=page.goto(candidate,wait_until='domcontentloaded',timeout=timeout_ms)
     except PlaywrightTimeout:
      last_status='timeout'
      continue
     last_status=str(response.status) if response else 'no_response'
     if response and response.status<400:
      break
    else:
     raise BrowserUnavailable('Public form browser status: '+last_status)
    page.wait_for_timeout(900)
    landed=page.url
    if not public_google_form(landed.split('?')[0]):
     raise BrowserUnavailable('Form requires authorization or redirected')
    visible=page.locator('body').inner_text(timeout=5000)
    if re.search(r'(?:you need permission|request access|sign in to continue|you must sign in)',visible,re.I):
     raise BrowserUnavailable('Form requires authorization')
    if not visible.strip():raise BrowserUnavailable('No public form text rendered')
    pages,all_read=_collect_public_pages(page,visible)
    # Keep actual visible HTML anchors/fee-document links from each reached
    # page, plus rendered text. This is not a form submission and contains
    # no answers because none are entered and all POSTs are blocked.
    combined=''.join(
      html+'<section data-btb-rendered-public-form="true">'+escape(text)+'</section>'
      for html,text in pages)
    if all_read:
     combined+='<span data-btb-all-public-pages-read="true"></span>'
    raw=combined.encode('utf-8')
    if len(raw)>MAX_SOURCE_BYTES:raise BrowserUnavailable('Rendered form exceeds size limit')
    return Document(combined),sha256(raw).hexdigest()
   finally:
    browser.close()
 except BrowserUnavailable:
  raise
 except PlaywrightTimeout as exc:
  raise BrowserUnavailable('Public form browser timeout') from exc
 except Exception as exc:
  raise BrowserUnavailable('Public form browser runtime failure') from exc

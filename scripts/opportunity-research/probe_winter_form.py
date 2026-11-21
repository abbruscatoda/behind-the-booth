"""One-time, read-only public-form evidence probe for Western Wake craft fair.

Only extracts labels near posted prices, never form responses or private data.
The same bounded Playwright renderer used by the daily worker is used here.
"""
import json,re
from browser_forms import render_public_form,BrowserUnavailable
from category_rules import visible_text
from verifier import Fetcher

URL='https://docs.google.com/forms/d/e/1FAIpQLSf-4catG9HnDm1XodMjUij_nel5Fvf4jzilVc0XXtWb21v93Q/viewform'
def inspect(label,text):
 text=' '.join(text.split())
 windows=[]
 for match in re.finditer(r'\$\s*[0-9][0-9,.]*|(?:application|booth|craft|tent|stall|table|registration|space)[ -]?(?:fees?|cost|price|sizes?)',text,re.I):
  span=text[max(0,match.start()-70):min(len(text),match.end()+100)]
  if span not in windows and len(windows)<35: windows.append(span)
 return {'method':label,'text_length':len(text),'money_and_fee_context':windows,'has_submit':bool(re.search(r'\bSubmit\b',text,re.I)),'has_next':bool(re.search(r'\bNext\b',text,re.I)),'closed':bool(re.search('no longer accepting responses|form is closed',text,re.I))}
try:
 fetcher=Fetcher(limit=8)
 fetcher.browser_enabled=True
 doc,digest=fetcher.get(URL)
 print('WINTER_FORM_STATIC_OR_BROWSER '+json.dumps(inspect('worker_fetch',visible_text(doc.root)))[:8000])
except Exception as exc:
 print('WINTER_FORM_FETCH_ERROR '+type(exc).__name__+': '+str(exc)[:110])
try:
 doc,digest=render_public_form(URL)
 print('WINTER_FORM_CHROMIUM '+json.dumps(inspect('chromium',visible_text(doc.root)))[:8000])
except BrowserUnavailable as exc:
 print('WINTER_FORM_BROWSER_ERROR '+str(exc)[:150])

try:
 from western_craft_fair import read_fee_pdf,craft_fee_from_pdf
 pdf_text,digest=read_fee_pdf('https://westernwakefarmersmarket.org/s/Vendor-Fee-Schedule-v01-2025.pdf')
 print('WESTERN_CRAFT_PDF_FEE '+str(craft_fee_from_pdf(pdf_text)))
 print('WESTERN_CRAFT_PDF_LENGTH '+str(len(pdf_text)))
except Exception as exc:
 print('WESTERN_CRAFT_PDF_ERROR '+type(exc).__name__+': '+str(exc)[:120])

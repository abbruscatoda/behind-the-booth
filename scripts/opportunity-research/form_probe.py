"""Read-only report of public Google Form price text for Brewgaloo.

This probes a specifically organizer-linked form for extraction quality.
Raw form responses and arbitrary page text are never logged. A public fee
mention is not sufficient evidence to change a published listing.
"""
import re
from verifier import source_error,clean
from category_rules import visible_text

BREWGALOO_FORM='https://docs.google.com/forms/d/e/1FAIpQLSdfqVaXAuhAV0Ujh7iEp-gHaViqeKEEz5Lq9BqM-ayGyof2TA/viewform'

def probe_public_form(fetcher,url=BREWGALOO_FORM):
 try:
  doc,_=fetcher.get(url)
 except Exception as exc:
  return {'status':'inaccessible','reason':source_error(exc)}
 text=clean(visible_text(doc.root))
 # Report amounts only, without inferring which vendor class each applies to.
 amounts=sorted({int(value.replace(',','')) for value in re.findall(r'\$\s*([0-9]{1,5}(?:,[0-9]{3})*)',text)})
 return {'status':'public_text_available','text_characters':len(text),
         'dollar_amounts_found':amounts[:16],
         'price_not_confirmed':True}

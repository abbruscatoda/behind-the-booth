"""Read-only text extraction for organizer-linked public Google Docs.

Callers must first verify the *exact* document is linked from the organizer's
official site. No Google login, form submission, prefill or access bypass.
"""
from __future__ import annotations
import hashlib
import re
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Public document redirected outside its approved URL')

def export_url(document):
    p=urlparse(document)
    m=re.fullmatch(r'/document/d/([A-Za-z0-9_-]{20,120})/edit',p.path)
    if (p.scheme!='https' or p.hostname!='docs.google.com' or p.username
        or p.password or p.port not in (None,443) or p.fragment or
        p.query not in ('','usp=sharing') or not m):
        raise ValueError('Not an approved public Google Doc link')
    return 'https://docs.google.com/document/d/'+m.group(1)+'/export?format=txt'

def fetch_public_google_document(document):
    """Fetch the public TXT export only, bounded to 250 KiB."""
    url=export_url(document)
    request=Request(url,headers={'User-Agent':'BehindTheBoothVerifier/1.0 (+https://www.behindtheboothhq.com/contact)'})
    with build_opener(NoRedirect()).open(request,timeout=20) as response:
        if response.url!=url or not response.headers.get('Content-Type','').lower().startswith('text/plain'):
            raise ValueError('Official document text export unavailable')
        raw=response.read(250_001)
        if len(raw)>250_000:raise ValueError('Official document exceeds limit')
    return raw.decode('utf-8-sig','replace'), hashlib.sha256(raw).hexdigest()

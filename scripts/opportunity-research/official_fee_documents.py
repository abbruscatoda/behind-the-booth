"""Bounded, provenance-preserving research of organizer-linked fee documents.

Only follow document links explicitly present on a verified organizer page or
its already verified public application. Supports host-local and Squarespace
CDN PDFs; never searches unrelated URLs or reads/responds to form submissions.
Do not translate regular-market or category-specific prices to a universal
event booth fee.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import re

MAX_PDF_BYTES = 2_500_000
MAX_PAGES = 12
MAX_LINKS = 3
MAX_TEXT = 24_000

PUBLIC_PDF_URL = re.compile(r"https://[^\s\"'<>\\]{8,1550}?\.pdf", re.I)

FEE_LABEL = re.compile(
    r"\b(?:table of fees|vendor fee schedule|fee schedule|vendor fees|"
    r"booth fees|booth prices|pricing|fee details|space rates|"
    r"vendor rates|craft fair fees|registration fees)\b", re.I
)


def _hosts(organizer_url):
    p = urlparse(organizer_url)
    if p.scheme != 'https' or not p.hostname:
        raise ValueError('The organizer origin is not HTTPS')
    host = p.hostname.lower().removeprefix('www.')
    return {host, 'www.' + host, 'static1.squarespace.com'}


def _safe_pdf(url, organizer_url):
    p = urlparse(url)
    if (p.scheme != 'https' or p.hostname not in _hosts(organizer_url)
        or p.username or p.password or p.port not in (None, 443)
        or p.query or p.fragment or len(url) > 1600
        or not p.path.lower().endswith('.pdf')):
        return False
    if p.hostname == 'static1.squarespace.com':
        return p.path.startswith('/static/')
    return True


def fee_document_links(document, page_url, organizer_url):
    """Find fee-named PDF links on an already approved organizer/form page."""
    links = []
    for node in document.root.walk():
        if node.tag != 'a' or not node.attrs.get('href'):
            continue
        label = ' '.join(
            (node.text(), node.attrs.get('title', ''), node.attrs.get('aria-label', ''))
        )
        href = urljoin(page_url, node.attrs['href'])
        if FEE_LABEL.search(label) and _safe_pdf(href, organizer_url) and href not in links:
            links.append(href)
        if len(links) >= MAX_LINKS:
            break
    # The form's published, authored metadata may contain a Table of Fees
    # hyperlink on a later page, even when the first-page DOM does not.
    # Only accept the explicitly named public PDF and approved organizer/CDN
    # host. Never follow random URLs embedded in other script data.
    try:
        from published_form_metadata import public_form_sections
        authored = public_form_sections(document)
    except (ValueError, TypeError):
        authored = []
    for section in authored:
        if not FEE_LABEL.search(section):
            continue
        for candidate in PUBLIC_PDF_URL.findall(section):
            url = candidate.rstrip('.,;)')
            if _safe_pdf(url, organizer_url) and url not in links:
                links.append(url)
                if len(links) >= MAX_LINKS:
                    break
        if len(links) >= MAX_LINKS:
            break
    return links


class _BoundedRedirects(HTTPRedirectHandler):
    def __init__(self, organizer):
        self.organizer = organizer

    def redirect_request(self, request, fp, code, msg, headers, url):
        if not _safe_pdf(url, self.organizer):
            raise ValueError('Organizer fee PDF redirected to an unapproved origin')
        return super().redirect_request(request, fp, code, msg, headers, url)


def read_official_pdf(url, organizer_url):
    """Return (plain text, sha256) from a small, public, approved PDF."""
    if not _safe_pdf(url, organizer_url):
        raise ValueError('Fee document origin is not organizer-authorized')
    from pypdf import PdfReader
    opener = build_opener(_BoundedRedirects(organizer_url))
    req = Request(url, headers={'User-Agent': 'BehindTheBoothVerifier/1.0'})
    with opener.open(req, timeout=18) as response:
        if not _safe_pdf(response.url, organizer_url):
            raise ValueError('Fee PDF arrived from an unapproved origin')
        data = response.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES or len(data) < 100 or not data.startswith(b'%PDF'):
        raise ValueError('Fee PDF is oversized or unreadable')
    pdf = PdfReader(BytesIO(data), strict=True)
    if not 1 <= len(pdf.pages) <= MAX_PAGES:
        raise ValueError('Fee PDF has unsupported pagination')
    text = ' '.join(page.extract_text() or '' for page in pdf.pages)
    if len(text) > MAX_TEXT:
        raise ValueError('Fee PDF has unusually large text content')
    return text, sha256(data).hexdigest()


def inspect_official_fee_documents(pages, organizer_url, reader=read_official_pdf):
    """Return structured evidence and finite audit diagnostics.

    pages is [(Document, page_url)] already verified as an organizer page
    or the same official application. Text stays internal to the worker.
    A missing/mismatched fee never becomes zero or makes intake closed.
    """
    from form_fees import extract_linked_fee_options
    found = []
    for document, page_url in pages:
        for url in fee_document_links(document, page_url, organizer_url):
            if url not in found:
                found.append(url)
            if len(found) >= MAX_LINKS:
                break
    evidence = []
    blocked = 0
    for url in found[:MAX_LINKS]:
        try:
            content, digest = reader(url, organizer_url)
            optional = extract_linked_fee_options(content)
            evidence.append({
                'url': url,
                'hash': digest,
                'optional_fees': optional,
                'text': content[:MAX_TEXT],
                'source': 'organizer_linked_pdf',
            })
        except Exception:
            # Unexpected PDF encoding/formatting is inconclusive evidence,
            # not a reason to fail an unrelated source verification run.
            blocked += 1
    return {
        'documents': evidence,
        'linked_count': len(found),
        'readable_count': len(evidence),
        'blocked_count': blocked,
        'complete': not blocked and len(evidence) == len(found),
    }

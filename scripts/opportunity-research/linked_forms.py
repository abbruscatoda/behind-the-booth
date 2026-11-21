"""Read linked, public vendor forms without logging in or submitting.

This adapter collects reviewable facts. It does not automatically publish a
generic form until that organizer/platform has a verified publication policy.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from verifier import Uncertain, clean, norm, valid_url, canonical_event, validate_event, source_error
from google_forms import read_public_form
from official_fee_documents import inspect_official_fee_documents
from category_rules import visible_text
import re

POLICY = 'organizer-linked-public-form-v1'

def handles(item):
    url=item.get('application_url','')
    parsed=urlparse(url)
    return parsed.hostname in {'docs.google.com','forms.gle','form.jotform.com'} and valid_url(url)

def read(item, fetcher, now):
    url=item.get('application_url','')
    source_url=item.get('source_url','')
    if not handles(item):
        raise Uncertain('This form platform is not yet supported by the public reader.')
    if not valid_url(source_url) or source_url==url:
        raise Uncertain('The public form requires a separately verified official organizer page.')

    source, source_hash=fetcher.get(source_url)
    # A previously approved source must link this same form: search snippets
    # and a form title alone never establish organizer ownership.
    links=source.root.links(source_url)
    if url not in links:
        raise Uncertain('The official event page no longer links the saved form.')
    if canonical_event(source_url):
        event, start, end, address=validate_event(source,now,item.get('market_organizer'))
        if start.date().isoformat()!=item.get('starts_on') or end.date().isoformat()!=item.get('ends_on'):
            raise Uncertain('The organizer-linked event date differs from this listing.')
        if address.get('addressLocality','').lower()!=item.get('market_city','').lower():
            raise Uncertain('The linked event location differs from the approved market.')
    else:
        # Non-Eventeny organizer sites need both named identity and a clearly
        # printed full date. This is intentionally stricter than a link alone.
        text=visible_text(source.root)
        if norm(item.get('market_name','')) not in norm(text):
            raise Uncertain('The official source does not identify the approved market.')
        date=datetime.fromisoformat(item['starts_on']).date()
        display=f'{date:%B} {date.day}, {date.year}'
        if display.lower() not in text.lower() or item['ends_on']!=item['starts_on']:
            raise Uncertain('The official source does not confirm the exact event date.')

    facts=None
    form_hash=None
    form_doc=None
    messages=[]
    try:
        doc,form_hash=fetcher.get(url)
        form_doc=doc
        facts=read_public_form(doc)
    except Exception as error:
        messages.append(str(error) if isinstance(error,Uncertain) else
            'Public form could not be read ('+source_error(error)+').')
    if facts:
        messages.extend(facts.get('issues',[]))
        if facts['closed']:
            messages.append('The form says it is closed; confirm availability before listing it as open.')
        if not facts['complete']:
            messages.append('The form is not fully readable or does not expose a Submit control.')
    else:
        messages.append('Fields behind sign-in or inaccessible pages cannot be verified.')
    suggestions={key:value for key in ('booth_fee','application_fee','deposit','fee_notes','eligibility')
                 if facts and (value:=facts.get(key)) is not None and value!=''}
    # A blocked Google Form does not end the research. Follow only fee-named
    # documents already linked by the verified organizer event page or this
    # exact readable form. Never use unrelated PDFs to invent a universal
    # event booth price; surface them as context with source receipts.
    fee_documents={'documents':[],'linked_count':0,'readable_count':0,'blocked_count':0,'complete':True}
    if getattr(fetcher,'requests',0) < getattr(fetcher,'limit',100000)-8:
        pages=[(source,source_url)]
        if form_doc is not None:
            pages.append((form_doc,url))
        fee_documents=inspect_official_fee_documents(pages,source_url)
    option_notes=[]
    for doc in fee_documents['documents']:
        options=doc['optional_fees']
        extras=[]
        if options.get('second_space') is not None:
            extras.append('second space '+format(options['second_space'],'.2f')+' USD')
        if options.get('co_op_tent') is not None:
            extras.append('cooperative vending per tent '+format(options['co_op_tent'],'.2f')+' USD')
        if extras:
            option_notes.append('Organizer-linked fee PDF lists '+', '.join(extras)+
                '; confirm applicability to this specific event.')
    if option_notes:
        suggestions['fee_notes']=' '.join(
            [suggestions.get('fee_notes',''),*option_notes]).strip()[:2000]
    if fee_documents['blocked_count']:
        messages.append('At least one official linked fee document could not be read.')
    if fee_documents['readable_count'] and not facts:
        messages.append('Organizer-linked fee schedule checked despite inaccessible application.')
    reason=' '.join(messages) or 'Organizer-linked public application researched; confirm remaining vendor eligibility and submission details.'
    return {
        'decision':'review','policy':POLICY,'reason':reason,
        'form_closed':bool(facts and facts['closed']),
        'checked_at':now.isoformat(),'source_hash':source_hash,'application_hash':form_hash,
        'evidence':'Official event source links the exact public application.',
        'research_suggestions':{
          'application_url':url,'source_url':source_url,
          'starts_on':item['starts_on'],'ends_on':item['ends_on'],
          'checked_at':now.isoformat(),'source_hash':source_hash,
          'fields':suggestions,'notes':reason,
          'form_readable':facts is not None,
          'fee_document_count':fee_documents['readable_count'],
          'fee_document_status':'complete' if fee_documents['complete'] else 'partial',
          'fee_documents':[{'url':p['url'],'sha256':p['hash'],'optional_fees':p['optional_fees']} for p in fee_documents['documents']],
          'complete':bool(facts and facts['complete'] and not facts.get('issues') and not facts['closed'])
        }
    }

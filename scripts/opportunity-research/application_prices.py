"""Read published vendor prices, including forms linked by application hubs.

This reader never answers, submits or authenticates. A readable price is useful
even when the form has later required pages; it does not establish open intake.
"""
import re
from urllib.parse import urlparse, urljoin, parse_qsl

from verifier import valid_url, Uncertain, clean, norm
from category_rules import visible_text
from google_forms import read_public_form, published_blocks

MONEY=re.compile(r'\$\s*((?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]{1,2})?)(?!\d|,\d|\.\d)')
VENDOR_PRICE=re.compile(r'\b(?:booth|stall|tent|space|table)\b.{0,45}\b(?:fee|cost|price|rate)\b|\b(?:vendor|exhibitor)\s+(?:fee|cost|price|rate)s?\b|\b(?:retail|food|craft|novelty|non.food)\s+vendors?\s*[:–-]',re.I)
NON_VENDOR=re.compile(r'\b(?:sponsor(?:ship)?|admission|attendee|beer tickets?|sampling tickets?|merchandise|t.shirt)\b',re.I)


def public_form_url(url):
    """Drop only known Google sharing metadata, never prefilled answers."""
    p=urlparse(url)
    if p.scheme!='https' or p.username or p.password or p.fragment or p.port not in (None,443):return None
    if p.hostname=='docs.google.com':
        if not re.fullmatch(r'/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform',p.path):return None
        if any(k not in {'usp','ouid'} for k,_ in parse_qsl(p.query,keep_blank_values=True)):return None
        candidate='https://docs.google.com'+p.path
        return candidate if valid_url(candidate) else None
    return url if p.hostname=='forms.gle' and valid_url(url) else None


def vendor_form_links(doc,base):
    found=[]
    for node in doc.root.walk():
        if node.tag!='a' or not node.attrs.get('href'):continue
        label=visible_text(node)
        if not re.search(r'\bvendors?\b|food\s*trucks?',label,re.I) or NON_VENDOR.search(label):continue
        url=public_form_url(urljoin(base,node.attrs['href']))
        if url and url not in found:found.append(url)
    return found[:4]


def _matches_event(doc,item):
    headings=[visible_text(node) for node in doc.root.walk() if node.tag in {'h1','h2'} or node.attrs.get('role')=='heading']
    title=headings[0] if headings else ''
    years=set(re.findall(r'\b20\d{2}\b',title))
    if years and item['starts_on'][:4] not in years:return False
    # Brewgaloo's hub mixes different applicant types. Every linked form must
    # still name the actual festival; an unrelated named form is not a match.
    if item.get('market_slug')=='brewgaloo' and 'brewgaloo' not in norm(title):return False
    return True


def application_materials(doc,url,item,fetcher,initial_hash=None):
    """Bounded, directly linked public forms; failures stay explicit."""
    direct=public_form_url(url)
    targets=[direct] if direct else vendor_form_links(doc,url)
    materials=[];diagnostics=[]
    for target in targets:
        try:
            page,digest=(doc,initial_hash) if direct and initial_hash else fetcher.get(target)
            if not _matches_event(page,item):
                raise Uncertain('Application title or year does not match this event.')
            form=read_public_form(page)
            if form.get('closed'):
                diagnostics.append({'source_url':target,'status':'closed'});continue
            headings=[visible_text(n) for n in page.root.walk() if n.tag in {'h1','h2'} or n.attrs.get('role')=='heading']
            materials.append({'source_url':target,'source_hash':digest,'blocks':form['blocks'],'title':headings[0][:180] if headings else '',
                'access':'readable' if form.get('complete') else 'partial'})
        except (OSError,ValueError,KeyError):
            diagnostics.append({'source_url':target,'status':'access_limited'})
    return materials,diagnostics


def published_price_options(blocks,url,digest,scope=''):
    """One explicit amount per authored clause, retaining tiers and units.

    Unlabeled amounts, conflicting prices for one label, admission and sponsor
    prices never become a vendor's standard booth fee.
    """
    options=[];seen=set()
    for block in blocks:
        for raw in re.split(r'[;\n•]|[.]\s+(?=[A-Z])',block):
            clause=clean(raw)
            amounts=list(MONEY.finditer(clause))
            if len(amounts)!=1 or len(clause)>900 or NON_VENDOR.search(clause):continue
            amount=amounts[0];value=float(amount[1].replace(',',''))
            if not 0<=value<=20000:continue
            if re.search(r'\bapplication\s+(?:fee|cost|charge)\b',clause,re.I):kind='application'
            elif re.search(r'\b(?:refundable\s+)?deposit\b|\b(?:electricity|power|additional space|second space)\s+(?:fee|cost|charge)\b',clause,re.I):kind='addon'
            elif VENDOR_PRICE.search(clause):kind='booth'
            else:continue
            prefix=clause[:amount.start()].strip(' :–-(')
            suffix=clause[amount.end():].strip(' :–-')
            label=prefix if len(prefix)>=3 else re.split(r'[,.;]|\b(?:payable|due|non.refundable)\b',suffix,flags=re.I)[0].strip()
            # A long paragraph is not a stable price label. Exact labeled
            # fields near its end can still be captured without its preamble.
            if len(label)>110:
                m=re.search(r'((?:(?:food|retail|craft|novelty|non.food|standard)\s+)?(?:vendor|booth|stall|table|space|application|refundable deposit)\s*(?:fee|cost|price|charge)?[^$]{0,35})$',prefix,re.I)
                if not m:continue
                label=m[1].strip(' :–-')
            if not 3<=len(label)<=110:continue
            unit=('application' if kind=='application' else 'season' if re.search(r'per\s+season|full\s+season|season\s+(?:fee|cost)',clause,re.I)
                else 'day' if re.search(r'per\s+day|each\s+day|daily\s+(?:booth|vendor)',clause,re.I) else 'event')
            unavailable=bool(re.search(r'sold\s*out|fully\s*booked|not\s+available|unavailable',clause,re.I))
            key=(norm(label),value,unit,kind)
            if key in seen:continue
            seen.add(key)
            option={'label':label,'amount':value,'unit':unit,'kind':kind,'applicable':not unavailable,
                'conditions':((scope+': ') if scope else '')+clause,
                'source_url':url,'source_hash':digest,'excerpt':clause[:350]}
            option['conditions']=option['conditions'][:400]
            if unavailable:option['unavailable']=True
            options.append(option)
    conflicts={}
    for option in options:
        key=(norm(option['label']),option['unit'],option['kind'])
        conflicts.setdefault(key,set()).add(option['amount'])
    return [o for o in options if len(conflicts[(norm(o['label']),o['unit'],o['kind'])])==1][:12]

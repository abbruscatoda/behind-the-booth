"""Refresh optional public facts without changing application availability.

Receipts bind every fact to the exact published opportunity, official source,
application, dates and source hash. Multiple prices retain their units and
conditions. A sign-in wall is never evidence that a fee is absent or free.
"""
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse,urljoin
import re

from verifier import Uncertain, valid_url, norm
from category_rules import visible_text, nodes_with_parents, price_rows
from form_fees import extract_labeled_fees,extract_linked_fee_options
from official_fee_documents import inspect_official_fee_documents
from application_prices import application_materials,published_price_options

POLICY = 'published-field-evidence-v1'
MONTHS = {name: i + 1 for i, name in enumerate(
    ('january','february','march','april','may','june','july','august','september','october','november','december'))}
BLOCKED = re.compile(r'you need permission|sign in to continue|request access|you must sign in|enable cookies', re.I)

def _snippet(text, pattern):
    found = re.search(pattern, text, re.I)
    return text[max(0, found.start()-30):found.end()+100][:350] if found else text[:350]

def _proof(url, digest, text):
    return {'source_url': url, 'source_hash': digest, 'excerpt': ' '.join(text.split())[:350]}

def linked_application(doc,source,application):
    target=urlparse(application)
    urls=doc.root.links(source)+[urljoin(source,n.attrs['src']) for n in doc.root.walk()
        if n.tag=='iframe' and n.attrs.get('src')]
    for url in urls:
        p=urlparse(url)
        if url==application:return True
        if (p.scheme==target.scheme and p.hostname==target.hostname and p.path==target.path
            and target.hostname in {'docs.google.com','www.ncagr.gov'}):return True
    if target.hostname=='managemymarket.com':
        from recurring_market import official_registration_link
        return official_registration_link(doc,source,{'application_url':application}) is not None
    return False

def _option(label, amount, unit, proof, conditions='', kind='booth', applicable=True):
    amount = float(amount)
    if not 0 <= amount <= 20000: raise Uncertain('Unexpected published fee amount.')
    return {'label': label, 'amount': amount, 'unit': unit, 'conditions': conditions,
            'kind': kind, 'applicable': applicable, **proof}

def date_only_deadline(text):
    """Application-scoped date clauses only; never borrow an event date/year."""
    found = []
    for m in re.finditer(r'\b(?:application|registration)(?:s)?\s+(?:deadline\s*:?|close[sd]?\s*(?:on)?|ends?\s*(?:on)?)\s*'
                         r'(?:(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})|(\d{1,2})/(\d{1,2})/(20\d{2}|\d{2}))\b', text, re.I):
        try:
            day = date(int(m[3]), MONTHS[m[1].lower()], int(m[2])) if m[1] else date(int(m[6])+(2000 if len(m[6])==2 else 0), int(m[4]), int(m[5]))
        except ValueError: continue
        # A timestamp is already handled by the existing exact-deadline parser.
        tail=text[m.end():m.end()+60]
        if re.search(r'\b\d{1,2}:\d{2}\s*(?:am|pm)|\bat\s+\d{1,2}\s*(?:am|pm)',tail,re.I):continue
        found.append((day.isoformat(),m.group(0),bool(re.search(r'until spots are filled|sooner if full|earlier if full',tail,re.I))))
    unique={x[0] for x in found}
    return found[0] if len(unique)==1 else None

def fvg_options(text, proof):
    result=[]
    for name, pattern in [('Full season',r'Full.time\s*,?\s*\$(\d+)\s*\((\d+) Saturdays\)'),
                          ('Part season',r'Part.time\s*,?\s*\$(\d+)\s*\((\d+) Saturdays\)')]:
        m=re.search(pattern,text,re.I)
        if not m:raise Uncertain('A published participation plan is no longer readable.')
        result.append(_option(name,m[1],'season',proof,f'{m[2]} Saturdays'))
    m=re.search(r'Guest\s*\$(\d+)\s*per\s*day',text,re.I)
    if not m:raise Uncertain('Guest-day pricing is no longer readable.')
    return [_option('Guest vendor',m[1],'day',proof),*result]

def western_regular_options(text, proof):
    out=[]
    for label, pattern, kind, unit in [
        ('New vendor',r'New Vendor Application Fee.{0,65}?\$\s*(\d+)','application','application'),
        ('Returning vendor',r'Returning Vendor Application Fee.{0,65}?\$\s*(\d+)','application','application'),
        ('Regular vendor',r'Regular Vendor Attends at least (\d+) days per year\s*\$(\d+)','booth','day'),
        ('Seasonal / part-time',r'Seasonal or Part.Time Vendor Attends at least (\d+) days per year\s*\$(\d+)','booth','day'),
        ('Guest vendor',r'Guest Vendor Attends fewer than (\d+) days per year\s*\$(\d+)','booth','day'),
    ]:
        m=re.search(pattern,text,re.I)
        if not m:raise Uncertain('The linked regular-vendor fee schedule changed.')
        out.append(_option(label,m[2] if kind=='booth' else m[1],unit,proof,
            (f'{"Fewer than" if label=="Guest vendor" else "At least"} {m[1]} attendance days per year') if kind=='booth' else 'Nonrefundable; confirm the applicable applicant type',kind))
        out[-1]['excerpt']=m.group(0)[:350]
    return out

def state_fee_options(text, proof):
    """Parse only a current, explicitly effective schedule, preserving seasons."""
    effective=re.search(r'Effective\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})',text,re.I)
    if not effective:raise Uncertain('The fee schedule has no unambiguous effective date.')
    effective_day=date(int(effective[3]),MONTHS[effective[1].lower()],int(effective[2]))
    patterns=[
      ('Farmers · weekday',r'Farmers Area:.*?Monday through Friday\)\s*\$(\d+)\s*\$(\d+)','In-state farmers; Monday–Friday'),
      ('Farmers · occasional weekend',r'Farmers Area:.*?Saturday/Sunday if attendance less than 6 days per week\)\s*\$(\d+)\s*\$(\d+)','In-state farmers attending fewer than 6 days per week'),
      ('Crafts / baked goods · weekday',r'Non.Farmer Vendors in Farmers Area.*?Monday through Friday\)\s*\$(\d+)\s*\$(\d+)','In-state craft / baked-goods vendors; Monday–Friday'),
      ('Crafts / baked goods · occasional weekend',r'Non.Farmer Vendors in Farmers Area.*?Saturday/Sunday if attendance less than 6 days per week\)\s*\$(\d+)\s*\$(\d+)','In-state craft / baked-goods vendors attending fewer than 6 days per week'),
    ]
    options=[]
    for label,pattern,condition in patterns:
        m=re.search(pattern,text,re.I)
        if not m:raise Uncertain('Current state-market fee rows are not fully readable.')
        for amount,season in [(m[1],'April–December'),(m[2],'January–March')]:
            options.append(_option(label,amount,'day',{**proof,'excerpt':m.group(0)[-350:]},f'{condition}; {season}; per selling space. Out-of-state rates are double.'))
    return effective_day,options

def audit_item(item, fetcher, now=None, document_inspector=inspect_official_fee_documents):
    now=now or datetime.now(timezone.utc)
    source=item['source_url'];application=item['application_url']
    if not valid_url(source) or not valid_url(application):raise Uncertain('Unapproved published source.')
    root,root_hash=fetcher.get(source)
    root_text=visible_text(root.root)
    pages=[(root,source)]
    app=None;app_hash=None;app_text='';access='access_limited'
    try:
        app,app_hash=fetcher.get(application)
        app_text=visible_text(app.root)
        if len(app_text)>=180 and not BLOCKED.search(app_text):
            if urlparse(application).hostname in {'docs.google.com','forms.gle'}:
                from google_forms import read_public_form
                form=read_public_form(app)
                access='readable' if form.get('complete') else 'partial'
                app_text=' '.join([app_text,*form.get('blocks',[])])
            else:
                controls=any(n.tag in {'button','input','a'} and re.search(r'\b(?:submit|start application)\b',visible_text(n)+' '+n.attrs.get('value',''),re.I) for n,_ in nodes_with_parents(app.root))
                access='readable' if controls else 'partial'
            if application!=source:pages.append((app,application))
    except (OSError,ValueError,Uncertain):
        app=None;app_hash=None;app_text=''
    # Existing publication is not itself new ownership evidence. Require the
    # exact linked form, or an exact Eventeny app naming the saved market.
    app_title=norm(item['title'].split(' — ')[0])
    eventeny=urlparse(application).hostname in {'www.eventeny.com','eventeny.com'}
    bound=(application==source or linked_application(root,source,application)
        or (eventeny and app is not None and app_title in norm(app_text)))
    if not bound and urlparse(application).hostname=='docs.google.com':
        from lead_reconciliation import resolve_shortcut,google_form_identity
        target=google_form_identity(application)
        for shortcut in [url for url in root.root.links(source) if urlparse(url).hostname=='forms.gle'][:3]:
            if target and resolve_shortcut(shortcut,fetcher)==target:
                bound=True;break
    if not bound:
        # Western Wake's two organizer-advertised short links identify the same
        # already reviewed craft form. The existing dedicated adapter checks it.
        if not (item.get('verification_policy')=='western-wake-craft-official-v1' and 'register here' in root_text.lower()):
            raise Uncertain('The current source no longer binds this saved application.')
    documents=document_inspector(pages,source)
    materials,material_diagnostics=application_materials(app,application,item,fetcher,app_hash) if app is not None else ([],[])
    if materials:
        access='readable' if not material_diagnostics and all(m['access']=='readable' for m in materials) else 'partial'
    facts={}
    proof=_proof(application,app_hash,app_text[:350]) if app_hash else _proof(source,root_hash,root_text[:350])
    options=[]
    costs_status='unconfirmed';costs_summary='Exact participation costs could not be confirmed from readable materials.'
    key=item.get('market_slug','')
    # Strong, source-specific parsers prevent applying a related program's
    # prices, insurance coverage, sponsorship or a whole season as a daily fee.
    if key=='fuquay-varina-growers-market' and access=='readable':
        if not re.search(r'\b'+item['starts_on'][:4]+r' NEW Vendor Application',app_text,re.I):raise Uncertain('Vendor application season changed.')
        options=fvg_options(app_text,_proof(application,app_hash,_snippet(app_text,r'Full.time')))
        costs_status='options';costs_summary='Choose a guest day, part-season plan or full-season plan. These are participation prices, not additional application charges.'
    if key=='western-wake-farmers-market' and item.get('schedule_type')=='rolling_market':
        for document in documents['documents']:
            text=' '.join(document['text'].split())
            if not re.search(r'New Vendor Application Fee',text,re.I):continue
            options=western_regular_options(text,_proof(document['url'],document['hash'],_snippet(text,r'New Vendor Application Fee')))
            extra=extract_linked_fee_options(text)
            for key,label,unit in [('second_space','Additional space','event'),('co_op_tent','Co-op vending arrangement','event')]:
                if key in extra:options.append(_option(label,extra[key],unit,_proof(document['url'],document['hash'],_snippet(text,label.split()[0])),
                    'Optional; subject to availability and the market rules. Co-op charge is per tent.' if key=='co_op_tent' else 'Optional additional space, subject to availability.',kind='addon'))
            costs_status='options';costs_summary='Daily booth rates depend on attendance commitment. New and returning application charges differ. The organizer currently links this January 2025 schedule as its current rates; confirm applicability before paying.'
            break
    if key=='state-farmers-market':
        candidates=[]
        for document in documents['documents']:
            try:
                effective,plans=state_fee_options(' '.join(document['text'].split()),_proof(document['url'],document['hash'],document['text'][:350]))
                if effective<=now.astimezone(ZoneInfo('America/New_York')).date():candidates.append((effective,plans))
            except (ValueError,Uncertain):continue
        if candidates:
            effective,options=max(candidates,key=lambda p:p[0]);costs_status='options'
            costs_summary=f'The latest readable official fee schedule is effective {effective.isoformat()}. Prices depend on season, selling area, attendance and residency; listed daily options are examples, not every possible arrangement.'
    if key=='holly-springs-farmers-market':
        season=re.search(r'Fees\s*:\s*Season\s*\d+\s*\(?May\s+(20\d{2})\s*[-–]\s*April\s+(20\d{2})',root_text,re.I)
        if season and season[1]==item['starts_on'][:4] and season[2]==item['ends_on'][:4]:
            for label,text in price_rows(root):
                match=re.search(r'\$\s*(\d+)',text)
                if match and re.search(r'(?:Extended|Traditional|Winter) Season .+Vendor',label,re.I):
                    unit='day' if 'Daily' in label else 'season'
                    options.append(_option(label,match[1],unit,_proof(source,root_hash,text),
                        'Current town-page attendance plan; applications are for the waiting list. Confirm individual dates and placement.'))
            if options:
                costs_status='options';costs_summary=f'The town page lists these May {season[1]}–April {season[2]} attendance plans. Registration is for the waiting list, not a guaranteed booth. Older linked PDFs must not override this current-season page.'
    if key=='wake-forest-prcr-special-events':
        match=re.search(r'Nov\.?\s+9,\s*(20\d{2}).{0,600}?application will be activated through Friday,?\s*Nov\.?\s+(\d{1,2})',root_text,re.I)
        if match:
            cutoff=date(int(match[1]),11,int(match[2])).isoformat()
            facts['deadline']={'status':'date_only','date':cutoff,'summary':'The town publishes the closing date without a cutoff time.',**_proof(source,root_hash,match[0][:30]+' … '+match[0][-190:])}
        costs_status='varies_by_event';costs_summary='The town says participation fees apply to individual events. Confirm the fee for your assigned 2027 event.'
        for document in documents['documents']:
            text=' '.join(document['text'].split())
            section=re.search(r'Fee Structure (.+?) Hold Harmless',text,re.I)
            if section:
                for m in re.finditer(r'\$(\d+)\s*\|\s*\$(\d+)\s*RD\s*\(([^)]+)\)',section[1],re.I):
                    p=_proof(document['url'],document['hash'],section[0])
                    options.extend([_option(m[3].strip(),m[1],'program',p,'Sample town agreement; confirm the rate for the 2027 event.',applicable=False),_option(m[3].strip()+' · resident',m[2],'program',p,'Sample agreement resident discount for Wake Forest taxpayers; confirm eligibility and current event rate.',applicable=False)])
    if key=='first-night-raleigh' and re.search(r'December\s+31,?\s+'+item['starts_on'][:4],root_text,re.I):
        deposits=re.search(r'\$(\d+)\s*\(food vendor\)\s*or\s*\$(\d+)\s*\(novelty vendor\)\s*refundable deposit',root_text,re.I)
        if deposits:
            p=_proof(source,root_hash,deposits[0])
            options=[_option('Food-vendor refundable deposit',deposits[1],'program',p,'Refundable deposit, not the total booth fee. Read the organizer refund and payment terms.',kind='addon'),
                     _option('Novelty-vendor refundable deposit',deposits[2],'program',p,'Refundable deposit, not the total booth fee. Read the organizer refund and payment terms.',kind='addon')]
            costs_status='options';costs_summary='These are category-specific refundable deposits. A total booth or participation charge could not be confirmed from the readable materials.'
    if not facts.get('deadline') and item.get('deadline') is None:
        # A deadline on the verified organizer page can be usable even when
        # a Google/Cognito form cannot be read; do not invent its exact time.
        matches=[]
        for text,url,digest in [(root_text,source,root_hash),(app_text,application,app_hash)]:
            result=date_only_deadline(text)
            if result:
                day,quote,early=result
                if day<=item['ends_on']:matches.append({'status':'date_only','date':day,'early_close':early,'summary':'Time not published.'+( ' May close earlier if full.' if early else ''),**_proof(url,digest,quote)})
        if len({m['date'] for m in matches})==1:facts['deadline']=matches[0]
    if not facts.get('deadline') and item.get('deadline') is None and app_hash and re.search(r'applications\s+(?:are\s+)?open\s+year[- ]round',app_text,re.I):
        facts['deadline']={'status':'rolling','summary':'The organizer explicitly accepts applications year-round. Review timing and approval are separate from an application closing date.',**_proof(application,app_hash,_snippet(app_text,r'applications\s+(?:are\s+)?open\s+year'))}
    facts.setdefault('deadline',{'status':'rolling' if item.get('schedule_type')=='rolling_market' else 'access_limited' if access!='readable' else 'not_listed','summary':'No single application cutoff applies to this rolling intake.' if item.get('schedule_type')=='rolling_market' else 'A cutoff could not be confirmed from all application materials.' if access!='readable' else 'No application closing date was found in the readable application and checked linked materials.',**proof})
    pricing_proof=proof
    if not options:
        for material in materials:
            options.extend(published_price_options(material['blocks'],material['source_url'],material['source_hash'],material['title']))
        options=options[:12]
        if options:
            costs_status='options';costs_summary='Published prices from the linked vendor applications. Compare each vendor type, space and payment condition; these are not one universal fee.'
            pricing_proof={k:options[0][k] for k in ('source_url','source_hash','excerpt')}
    # Exact application fees are parsed only from this specific application.
    # A booth charge, deposit or silence never becomes a $0 application fee.
    fees=extract_labeled_fees(app_text) if access in {'readable','partial'} else {}
    app_amount=fees.get('application_fee')
    if options and any(o['kind']=='application' for o in options):
        facts['application_fee']={'status':'options','summary':'New and returning applicant charges differ; see the published options.',**proof}
    elif app_amount is not None:
        facts['application_fee']={'status':'confirmed','amount':app_amount,'summary':'The application explicitly labels this application charge.',**_proof(application,app_hash,_snippet(app_text,r'application fee|applying costs nothing|applications? are free'))}
    else:
        facts['application_fee']={'status':'not_listed' if access=='readable' else 'access_limited','summary':'No separate application charge was identified in the readable application; this does not establish that applying is free.' if access=='readable' else 'The complete application could not be read, so a separate application charge remains unconfirmed.',**proof}
    if not options and eventeny and app is not None:
        for label,text in price_rows(app):
            # Sponsorship, optional requests and sold-out options are not the
            # price of the booth a vendor is currently applying for.
            extra=bool(re.search(r'sponsor|special request|non.profit|lead sponsor|deposit',label,re.I))
            if re.search(r'application fee',label,re.I):continue
            m=re.search(r'\$\s*([\d,]+(?:\.\d{1,2})?)',text)
            if m:
                unavailable=bool(re.search(r'sold out|unavailable|fully booked',text,re.I))
                option=_option(label,m[1].replace(',',''),'program' if re.search(r'all\s+\d+|lead sponsor',label,re.I) else 'event',_proof(application,app_hash,text),text[:220],kind='addon' if extra else 'booth',applicable=not unavailable)
                if unavailable:option['unavailable']=True
                options.append(option)
        if options:costs_status='options';costs_summary='These options are listed in the exact vendor application; acceptance and remaining space are subject to organizer approval.'
    if costs_status=='unconfirmed' and re.search(r'(?:fees|costs|pricing|rates).{0,55}var(?:y|ies)|vendor fee associated with participation',root_text+' '+app_text,re.I):
        costs_status='varies_by_event';costs_summary='The organizer describes variable participation pricing; confirm your event, space and vendor type.'
    facts['pricing']={'status':costs_status,'summary':costs_summary,**pricing_proof}
    facts['pricing_options']=options[:12]
    facts['application_access']=access
    # A reviewed, explicit application category invitation is safe even if the
    # source's form widget omits its category question choices.
    facts['categories']=[]
    facts['restrictions']=[]
    if key=='fuquay-varina-growers-market':
        # Jotform puts its published checkbox text in input values while the
        # visual duplicate is aria-hidden. Read authored choices, never answers,
        # hidden inputs, disabled choices or unrelated script state.
        category_text=app_text+' '+' '.join(n.attrs.get('value','') for n,_ in nodes_with_parents(app.root)
            if n.tag=='input' and n.attrs.get('type') in {'checkbox','radio'} and n.attrs.get('value','').startswith('Category ')) if app is not None else app_text
        for category,pattern in [('Food & Beverages',r'Category 2:\s*Processed/Prepared Food & Beverage'),('Handmade Crafts',r'Category 4:\s*Non.Edible Craft and Artisan Products'),('Plants & Farm Products',r'Category 1:\s*Raw or minimally processed farm products')]:
            if re.search(pattern,category_text,re.I):facts['categories'].append(category)
        if re.search(r'Artisans may only apply as guest vendors',app_text,re.I):
            facts['restrictions'].append('Artisans may apply only as guest vendors; season plans are for other eligible vendor types.')
            for option in options:
                if option['unit']=='season':option['conditions']+='; artisans are not eligible for this plan'
    if eventeny and 'heart' in item['title'].lower() and re.search(r'Create original, handmade, or artist.designed work',app_text,re.I):
        invitation=re.search(r'We strongly encourage applications from artists working in:(.+?)(?:The more unique|Important Values|Application Review)',app_text,re.I)
        if invitation:
            for category,pattern in [('Handmade Crafts',r'Handmade & crafted goods'),('Art & Photography',r'Illustration, painting, prints'),('Jewelry & Accessories',r'goods\s*\(jewelry,')]:
                if re.search(pattern,invitation[1],re.I):facts['categories'].append(category)
        requirements=['The application prioritizes original handmade or artist-designed work.']
        for pattern,message in [
          (r'not resale or generic wholesale','Resale and generic wholesale are excluded.'),
          (r'Indoor spaces will accommodate a 6.{0,3} table','Indoor spaces accommodate a 6-foot table.'),
          (r'Outdoor spaces will be 10.{0,4}10','Outdoor spaces are 10 × 10 feet; check equipment requirements.'),
          (r'3[–-]6 photos of your work are required','Submit 3–6 photos of your work.'),
          (r'fee will be charged.{0,60}after your application is approved','The vendor charge is due after acceptance.'),
          (r'Vendor fees are non.refundable','Vendor fees are nonrefundable.'),
        ]:
            if re.search(pattern,app_text,re.I):requirements.append(message)
        facts['requirements']={'summary':' '.join(requirements),**_proof(application,app_hash,_snippet(app_text,r'What We.re Looking For'))}
    if key=='wake-forest-prcr-special-events':facts['categories']=['Food Trucks','Food & Beverages']
    return {'policy':POLICY,'id':item['id'],'source_url':source,'application_url':application,
            'starts_on':item['starts_on'],'ends_on':item['ends_on'],'checked_at':now.isoformat(),
            'source_hash':root_hash,'application_hash':app_hash,'facts':facts,
            'anchor':{k:item.get(k) for k in ('booth_fee','application_fee','deposit','deadline')},
            'application_sources':[{'source_url':m['source_url'],'source_hash':m['source_hash'],'access':m['access']} for m in materials],
            'application_source_diagnostics':material_diagnostics,
            'documents_checked':documents['readable_count'],'documents_blocked':documents['blocked_count']}

def audit_published(db, fetcher, dry_run=False, now=None, context=None):
    if not callable(getattr(fetcher,'get',None)):return {'unavailable':True,'reason':'Public source reader unavailable'}
    context=context if context is not None else db.rpc('btb_research_fact_context')
    if not context.get('enabled'):return {'paused':True}
    summary={'checked':0,'updated':0,'retained':0,'skipped':0,'inconclusive':[],'held':context.get('held',0)}
    for item in context.get('items',[]):
        if fetcher.requests>=fetcher.limit-3:
            summary['inconclusive'].append({'title':item['title'],'reason':'Bounded field-audit budget reached; retry next run.'});break
        try:result=audit_item(item,fetcher,now)
        except (Uncertain,OSError,ValueError) as error:
            summary['inconclusive'].append({'title':item['title'],'reason':str(error)[:160] if isinstance(error,Uncertain) else 'Official source unavailable; existing facts retained.'});continue
        summary['checked']+=1
        if result.get('application_source_diagnostics'):
            summary['inconclusive'].append({'title':item['title'],'reason':'Some linked vendor applications remain unreadable or mismatched; only independently verified fields can be saved.'})
        if not dry_run:
            outcome=db.rpc('btb_research_record_facts',{'p_result':result})
            if outcome.get('action')=='updated':summary['updated']+=1
            elif outcome.get('action')=='retained':
                summary['retained']+=1
                summary['inconclusive'].append({'title':item['title'],'reason':outcome.get('reason','Source details need rechecking')})
            else:summary['skipped']+=1
    return summary

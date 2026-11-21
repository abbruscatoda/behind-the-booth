"""Reusable, source-bound public vendor programs overlooked by dated-event discovery.

These providers have independently established official applications, but no
single guaranteed event booth/date; do not fabricate one. A live organizer
application link is necessary. Form access failures never invent prices.

Supported types:
  - seasonal multi-event vendor application with dated intake window
  - rolling vendor/guest application for regularly scheduled markets
  - event-specific food-vendor application with exact selectable date
  - downloadable state-market paper application with availability restrictions
"""
from __future__ import annotations
from datetime import datetime, timezone, date
from urllib.parse import urlparse, urljoin
from zoneinfo import ZoneInfo
import re

from verifier import Uncertain, valid_url
from category_rules import visible_text
from official_documents import fetch_public_google_document

POLICY='official-vendor-program-v1'
DPR_SOURCE='https://www.dprplaymore.org/331/Vendor-Performer-Information'
DPR_FORM='https://www.dprplaymore.org/FormCenter/Vendor-Registration-8/Food-Vendor-Application-50'
WAKE_SOURCE='https://www.wakeforestnc.gov/parks-recreation-cultural-resources/prcr-food-vendors'
WAKE_FORM='https://www.cognitoforms.com/TownOfWakeForestPRCR1/_2027TownOfWakeForestParksRecreationCulturalResourcesSpecialEventFoodVendingOpportun'
STATE_SOURCE='https://www.ncagr.gov/divisions/marketing/farmers-markets-agricultural-centers/state-farmers-market-raleigh/vendor-information'
STATE_FORM='https://www.ncagr.gov/media/5343/download?attachment='
SOUTH_SOURCE='https://southdurhamfarmersmarket.com/become-a-vendor'
SOUTH_CRAFT_FORM='https://docs.google.com/forms/d/e/1FAIpQLSeXV0kAKDUDK3e44KLfoV9pXMd94CjlS1Up5y2TkwUOQ1D__g/viewform'
SOUTH_GUEST_FORM='https://docs.google.com/forms/d/e/1FAIpQLSc4n-7Ht3GntUJpGP0HaGPmUvYA3XMbnnqxy8VePtlAm2Uv-g/viewform'
SOUTH_RULES_PAGE='https://southdurhamfarmersmarket.com/market-rules-%2B-bylaws'
SOUTH_RULES_DOC='https://docs.google.com/document/d/1QVgqQan9naZBfJSjxcRQg51B8gXJ9NzNVOYIBveCdRk/edit?usp=sharing'

PROGRAMS={
 'wake-forest-2027-food':{
  'source':WAKE_SOURCE,'application':WAKE_FORM,'market_slug':'wake-forest-prcr-special-events',
  'market_name':'Wake Forest PRCR Special Events','organizer':'Town of Wake Forest Parks, Recreation & Cultural Resources',
  'city':'Wake Forest','title':'Wake Forest PRCR — 2027 Special Event Food Vendor Applications',
  'venue':'Multiple PRCR events in Wake Forest, NC','starts':'2027-01-01','ends':'2027-12-31',
  'schedule':'seasonal_application','until':'2026-11-27','price':None,
  'eligibility':'Food vendors for 2027 PRCR events. Wake County MFU or TFE permit, background screening, and general/automobile liability insurance of at least $1 million are required. Local vendors and quiet generators receive priority; selection is not guaranteed.',
  'fees':'The town says a vendor fee typically applies to individual events, but does not publish one universal booth or application fee. Online applications are advertised November 9–27, 2026; no cutoff time is published.',
 },
 'durham-food-vendor-program':{
  'source':DPR_SOURCE,'application':DPR_FORM,'market_slug':'durham-prcr-special-events',
  'market_name':'Durham Parks & Recreation Special Events','organizer':'Durham Parks & Recreation',
  'city':'Durham','title':'Durham Parks & Recreation — Food Vendor Applications',
  'venue':'Durham, NC (locations assigned for each event)','starts':'2026-01-01','ends':'2027-12-31',
  'schedule':'rolling_market','until':None,'price':None,
  'eligibility':'Food vendors can submit an application for eligible current DPR special events. Mobile Food Units and Push Cart Peddlers must hold current Durham County food-service permits. DPR staff select vendors and may place applicants on a waitlist; an application is not a guaranteed event or selling space.',
  'fees':'Food-vendor participation fees are provided by DPR to selected applicants, with payment due within two business days. No single published booth rate is verified for the series. Choose current event options in the official form; do not assume any individual event remains selectable.',
 },
 'state-raleigh-new-vendors':{
  'source':STATE_SOURCE,'application':STATE_FORM,'market_slug':'state-farmers-market',
  'market_name':'State Farmers Market','organizer':'North Carolina Department of Agriculture & Consumer Services',
  'city':'Raleigh','title':'State Farmers Market — New Vendor Applications',
  'venue':'1201 Agriculture Street, Raleigh, NC','starts':'2026-01-01','ends':'2027-12-31',
  'schedule':'rolling_market','until':None,'price':None,
  'eligibility':'New vendors apply using the two-page State Farmers Market application and return it to the market office. Management determines space and eligibility. Many areas have waiting lists; an application must be resubmitted by February 28 each year to maintain waitlist status. The currently linked application was revised in 2017.',
  'fees':'Rates vary by selling area, season, and vendor type. The organizer links fee schedules (some dated 2023). No single universal booth price is assumed; confirm current applicable selling-space charges before applying.',
 },
 'south-durham-winter-craft':{
  'source':SOUTH_SOURCE,'application':SOUTH_CRAFT_FORM,'market_slug':'south-durham-farmers-market',
  'market_name':'South Durham Farmers Market','organizer':'South Durham Farmers Market',
  'city':'Durham','title':'South Durham Farmers Market — Winter Craft Applications',
  'venue':'HUB RTP, 500 Park Offices Drive, Durham, NC','starts':'2026-11-01','ends':'2026-12-31',
  'schedule':'seasonal_application','until':'2026-12-31','price':None,
  'eligibility':'The organizer currently invites craft vendors for one or two holiday market dates from November through December 2026. Vendors must produce their work locally and meet market eligibility requirements. Exact dates and space are subject to organizer confirmation.',
  'fees':'The organizer links a dedicated winter craft Google Form. Its questions, fees, and deadline were not independently readable to unauthenticated checks; this does not establish that the organizer published no prices or cutoff. The official guest-vendor fee schedule is a different intake and must not be copied to this application. Check the linked form for exact craft fees and dates.',
 },
 'south-durham-guest-vendors':{
  'source':SOUTH_SOURCE,'application':SOUTH_GUEST_FORM,'market_slug':'south-durham-farmers-market',
  'market_name':'South Durham Farmers Market','organizer':'South Durham Farmers Market',
  'city':'Durham','title':'South Durham Farmers Market — Guest Vendor Applications',
  'venue':'HUB RTP, 500 Park Offices Drive, Durham, NC','starts':'2026-01-01','ends':'2027-12-31',
  'schedule':'rolling_market','until':None,'price':None,
  'eligibility':'The organizer accepts guest vendor applications for its year-round market and reviews them around the 15th of each month. Farm, prepared-food and craft producers may apply; liability insurance and legally required certifications are necessary. Participation and dates are subject to Board selection.',
  'fees':'Guest vendors need not pay annual membership dues but may pay stall/guest fees. The organizer does not publish a complete reliable numeric standard rate on its public page; verify the current amount before applying.',
 },
}

def _linked(doc,source,target):
    path=urlparse(target)
    return any(urlparse(link).scheme==path.scheme and urlparse(link).hostname==path.hostname
            and urlparse(link).path==path.path
            for link in doc.root.links(source))

def verified_guest_rates(fetcher):
    """Read the *official linked rules*, not an unrelated Durham market fee schedule."""
    page,_=fetcher.get(SOUTH_RULES_PAGE)
    if not _linked(page,SOUTH_RULES_PAGE,SOUTH_RULES_DOC):
        raise Uncertain('The organizer no longer links the approved South Durham Market Rules.')
    try:
        rules,digest=fetch_public_google_document(SOUTH_RULES_DOC)
    except (OSError,ValueError) as exc:
        raise Uncertain('South Durham public Market Rules text unavailable for fee verification.') from exc
    normalized=' '.join(rules.split())
    if not (re.search('Market Rules',normalized,re.I)
            and re.search('Guest Vendor Applications',normalized,re.I)):
        raise Uncertain('The linked document does not confirm South Durham guest vendor rules.')
    application=re.search(r'market manager will invoice the applicant a\s*\$([0-9]+(?:\.[0-9]{1,2})?)\s*fee upon receipt of the application',normalized,re.I)
    daily=re.search(r'Guest Vendor shall pay a daily space fee of\s*\$([0-9]+(?:\.[0-9]{1,2})?).{0,35}?for summer season and\s*\$([0-9]+(?:\.[0-9]{1,2})?).{0,35}?for winter season',normalized,re.I)
    if not application or not daily:
        raise Uncertain('Current guest fees could not be unambiguously extracted from official rules.')
    app,summer,winter=(float(application.group(1)),float(daily.group(1)),float(daily.group(2)))
    if min(app,summer,winter)<0 or max(app,summer,winter)>500:
        raise Uncertain('Out-of-range fee in official guest-vendor rules.')
    return {'application':app,'summer':summer,'winter':winter,'hash':digest}

def verify_program(program,fetcher,now=None):
    if program not in PROGRAMS:
        raise Uncertain('Unrecognized vendor program.')
    cfg=PROGRAMS[program]
    now=now or datetime.now(timezone.utc)
    today=now.astimezone(ZoneInfo('America/New_York')).date()
    until=date.fromisoformat(cfg['until']) if cfg['until'] else None
    closed=bool(until and today>until)
    # An objectively elapsed advertised application window closes without
    # relying on a possible later organizer outage.
    doc,digest=fetcher.get(cfg['source'])
    text=visible_text(doc.root)
    if not _linked(doc,cfg['source'],cfg['application']):
        raise Uncertain('The official organizer no longer links the approved vendor application.')
    if program=='wake-forest-2027-food':
        if not (re.search(r'2027\s+PRCR\s+events?',text,re.I)
             and re.search(r'Nov[.]?\s*27',text,re.I)
             and re.search('food vendors?',text,re.I)):
            raise Uncertain('Town page no longer confirms 2027 food-vendor dates and application period.')
    elif program=='durham-food-vendor-program':
        # The official municipal page explicitly advertises current food
        # vendor opportunities across DPR events. Its CivicPlus form
        # dynamically renders the event selector, which may be absent from
        # a read-only static fetch. Do NOT claim one exact event date.
        if not (re.search(r'Food Vendors?',text,re.I)
                and re.search(r'current food vendor opportunities',text,re.I)
                and re.search(r'mobile food units or pushcart peddlers',text,re.I)):
            raise Uncertain('Durham official current event food-vendor intake no longer confirmed.')
        app,app_hash=fetcher.get(cfg['application'])
        app_text=visible_text(app.root)
        if not (re.search('Durham Parks and Recreation',app_text,re.I)
                and re.search('Food Vendor Application',app_text,re.I)):
            raise Uncertain('The official CivicPlus vendor form identity no longer matches DPR.')
    elif program=='state-raleigh-new-vendors':
        if not re.search('State Farmers Market',text,re.I) or not re.search('New Vendor Application',text,re.I):
            raise Uncertain('The state no longer links a new-vendor market application.')
    elif program=='south-durham-winter-craft':
        if not (re.search(r'Craft Vendor Applications are Open for Winter',text,re.I)
                and re.search(r'craft vendors',text,re.I)
                and re.search(r'November to December',text,re.I)):
            if not closed:raise Uncertain('South Durham winter craft vendor intake not currently confirmed.')
    elif program=='south-durham-guest-vendors':
        if not (re.search(r'Guest Vendor Application',text,re.I)
                and re.search(r'guest vendor applications are reviewed',text,re.I)):
            raise Uncertain('South Durham guest vendor application intake not confirmed.')

    rates=(verified_guest_rates(fetcher) if program=='south-durham-guest-vendors' else None)

    # Don't reuse stale pre-2027 periods indefinitely. Only real event/program
    # dates established by the organizer are represented.
    status=('closed' if closed else
            'limited' if program=='state-raleigh-new-vendors' else 'open')
    cfg_categories=(['Food Trucks','Food & Beverages'] if 'food' in program else [])
    if program=='south-durham-winter-craft':cfg_categories=['Handmade Crafts']
    candidate={
      'title':cfg['title'],'market_slug':cfg['market_slug'],
      'market_name':cfg['market_name'],'organizer':cfg['organizer'],
      'city':cfg['city'],'state':'NC','venue':cfg['venue'],
      'source_url':cfg['source'],'application_url':cfg['application'],
      'starts_on':cfg['starts'],'ends_on':cfg['ends'],
      'schedule_type':cfg['schedule'],'availability':status,'deadline':None,
      'booth_fee':None,'application_fee':None,'deposit':None,
      'categories':cfg_categories,
      'fee_notes':cfg['fees'],'eligibility':cfg['eligibility'],
      'research_notes':('Official organizer page directly links this specific public vendor application. '
        'The listing is for a vendor intake program; individual event places and exact dates '
        'are not guaranteed. Application window checked '+now.date().isoformat()+
        '. External forms were not submitted or filled.'),
    }
    if rates:
      candidate['application_fee']=rates['application']
      # Database/website must label this as a WINTER rate, not the annual rate.
      candidate['booth_fee']=rates['winter']
      candidate['fee_notes']=(f"Official February 2026 South Durham Market Rules, Guest Vendor Applications: "
          f"${rates['application']:g} application fee invoiced on receipt; "
          f"${rates['winter']:g} per 10 x 10 ft stall per winter market day; "
          f"${rates['summer']:g} per stall per summer market day. "
          "The displayed booth price is the WINTER rate, not a year-round price. "
          "Guest vendors pay no annual membership fee. Rules: "+SOUTH_RULES_DOC)
      candidate['eligibility']+=(' The official guest-vendor rules allow eight market days, '
          'with the option to apply for eight more.')
      candidate['research_notes']+=(' Verified the numeric guest application and seasonal daily booth fees '
          'against the official organizer-linked Market Rules, SHA-256 '+rates['hash']+
          '. These guest fees do not automatically apply to the separate Winter Craft application.')
    return {'decision':'publish','policy':POLICY,'program':program,'candidate':candidate,
            'rules_hash':rates['hash'] if rates else None,
            'source_hash':digest,'checked_at':now.isoformat(),
            'evidence':('The currently linked official organizer vendor page independently identifies '
                        'the named market or municipal program, applicant category, and the publicly '
                        'available application link. A specific event date or disclosed intake period '
                        'is required when applicable; no fees are inferred and no application is submitted.'),
            'reason':'Official vendor program application and intake rules verified.'}

def discover_programs(fetcher,now=None):
    """Try all vetted providers on every worker run; one failing site does not block others."""
    results=[]
    notes=[]
    if not callable(getattr(fetcher,'get',None)):
        return [],[{'program':'all','reason':'Fetcher unavailable for official vendor programs'}]
    for program in PROGRAMS:
        if getattr(fetcher,'requests',0)>=getattr(fetcher,'limit',999999)-18:
            break
        try:results.append(verify_program(program,fetcher,now))
        except (Uncertain,OSError,ValueError,AttributeError) as exc:
            notes.append({'program':program,'reason':str(exc)[:150]})
    return results,notes

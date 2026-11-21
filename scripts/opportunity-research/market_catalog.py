"""Reviewed local market identities, independent of application availability.

This catalog creates reviewable profiles only. It never declares vendor spaces
open or publishes an opportunity. Fresh live identity/location signals are
required; existing names, reviews, manual edits and hidden states are preserved.
"""
from datetime import datetime,timezone
from dataclasses import replace
import re
from verifier import Uncertain,valid_url
from category_rules import visible_text

POLICY='reviewed-market-catalog-v1'
CATALOG={
 'nc-vintage-haven':dict(slug='nc-vintage-market-at-haven-farm',name='NC Vintage Market at Haven Farm',city='Knightdale',organizer='NC Vintage Market',
  source='https://www.eventbrite.com/o/nc-vintage-market-121068658483',
  description='NC Vintage Market at Haven Farm is a curated vendor market in Knightdale featuring vintage clothing, accessories, jewelry, home goods, and reworked items. Event details and participating vendors vary by edition.',
  signals=(r'NC Vintage Market',r'Triangle',r'vintage sellers')),
 'nc-vintage-bazaar':dict(slug='nc-vintage-bazaar',name='NC Vintage Bazaar',city='Raleigh',organizer='NC Vintage Bazaar',
  source='https://ncvintagebazaar.com/',
  description='NC Vintage Bazaar is a vintage and secondhand market held at the North Carolina State Fairgrounds in Raleigh. Vendors offer clothing, accessories, and other vintage wearables. Dates and vendor lineups vary by event.',
  signals=(r'NC Vintage Bazaar',r'(?:State Fairgrounds|NC Fairgrounds)',r'vintage vendors')),
 'patchwork-durham':dict(slug='the-patchwork-market',name='The Patchwork Market',city='Durham',organizer='The Patchwork Market',
  source='https://thepatchworkmarket.com/applytobeavendor/',
  description='The Patchwork Market is a curated vendor market at the Durham Armory featuring handmade goods from local and regional makers. Vendor lineups, booth options, and application periods vary by edition.',
  signals=(r'Patchwork Market',r'Durham Armory',r'vendor')),
 'rebus-sunday':dict(slug='rebus-sunday-funday-market',name='Rebus Sunday Funday Market',city='Raleigh',organizer='Rebus Works',
  source='https://www.rebusworks.us/sundayfundaymarket',
  description='Rebus Sunday Funday Market is a recurring curated market at Rebus Works in Raleigh, featuring small businesses, makers, and vintage sellers. Check the organizer for current dates and vendor participation details.',
  signals=(r'Rebus Sunday Market',r'Raleigh',r'curated market')),
 'raleigh-retro-markets':dict(slug='raleigh-retro-gamers-markets',name='Raleigh Retro Gamers Markets',city='Raleigh',organizer='Raleigh Retro Gamers',
  source='https://raleighretrogamers.com/vendors/',
  description='Raleigh Retro Gamers organizes gaming and pop-culture vendor markets across Raleigh and the Triangle. Events feature retro and modern games, collectibles, vintage toys, clothing, and related goods. Venues, booth costs, and eligibility vary by event.',
  signals=(r'Raleigh Retro Gamers',r'(?:Triangle|North Carolina)',r'(?:pop.up|markets)',r'vintage')),
}

def verify_catalog_entry(key,fetcher,now=None):
 cfg=CATALOG[key]
 if not valid_url(cfg['source']):raise Uncertain('Catalog source is not approved for public fetching.')
 doc,digest=fetcher.get(cfg['source'])
 text=visible_text(doc.root)+' '+ ' '.join(visible_text(replace(n,tag='section')) for n in doc.root.walk() if n.tag=='footer')
 if not all(re.search(pattern,text,re.I) for pattern in cfg['signals']):
  raise Uncertain('Official source no longer confirms the reviewed market identity and location.')
 return {'policy':POLICY,'catalog_key':key,'source_url':cfg['source'],
         'source_hash':digest,'checked_at':(now or datetime.now(timezone.utc)).isoformat(),
         'evidence':'The reviewed official source currently confirms the market identity, Triangle location, and vendor-market activity. This receipt authorizes a reviewable directory profile only; it establishes no current vendor application or booth availability.'}

def discover_catalog(fetcher,now=None):
 if not callable(getattr(fetcher,'get',None)):return [],[]
 results=[];notes=[]
 for key in CATALOG:
  if getattr(fetcher,'requests',0)>=getattr(fetcher,'limit',999999)-min(20,getattr(fetcher,'limit',999999)//4):break
  try:results.append(verify_catalog_entry(key,fetcher,now))
  except (Uncertain,OSError,ValueError,AttributeError):
   notes.append({'market':key,'reason':'Live identity/location confirmation unavailable; existing directory data retained.'})
 return results,notes

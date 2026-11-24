"""Synchronize reviewed sources, market identities and verified vendor intake."""
from run import Database,register_discovery_sources
from independent_markets import monitoring_leads,discover_independent

def main():
 db=Database()
 result=register_discovery_sources(db,monitoring_leads())
 if result.get('paused'):
  print('Automatic research is paused; source synchronization skipped.')
 else:
  print('Reviewed discovery sources synchronized:',result['approved_sources'])
  from community_discovery import WATCHLIST,research_inbox
  synced=db.rpc('btb_research_community_sync',{'p_sources':WATCHLIST})
  if synced.get('sources')!=len(WATCHLIST):raise RuntimeError('Community source synchronization failed.')
  community,community_stats=research_inbox(db)
  for candidate in community:
   db.rpc('btb_research_publish_community_call',{'p_result':candidate})
  print('Community sources synchronized:',synced['sources'],'Verified calls:',len(community))
  from verifier import Fetcher
  from market_catalog import discover_catalog
  from official_vendor_programs import verify_program
  import json
  fetcher=Fetcher(limit=48)
  receipts,notes=discover_catalog(fetcher)
  for receipt in receipts:
   outcome=db.rpc('btb_research_publish_market_catalog',{'p_result':receipt})
   print(json.dumps({'catalog_market':receipt['catalog_key'],'action':outcome.get('action')}))
  print(json.dumps({'catalog_sources_unconfirmed':notes}))
  candidates,notes=discover_independent(fetcher)
  for candidate in candidates:
   outcome=db.rpc('btb_research_publish_independent_market',{'p_result':candidate})
   print(json.dumps({'independent_market':candidate['candidate']['title'],'date':candidate['candidate']['starts_on'],'action':outcome.get('action')}))
  print(json.dumps({'independent_market_sources_unconfirmed':notes}))
  try:program=verify_program('raleigh-retro-vendor-intake',fetcher)
  except (OSError,ValueError):
   print('Raleigh Retro vendor intake is currently unconfirmed; no listing was published.')
  else:
   outcome=db.rpc('btb_research_publish_official_program',{'p_result':program})
   print(json.dumps({'program':program['program'],'action':outcome.get('action')}))

if __name__=='__main__':main()

"""Synchronize reviewed sources, market identities and verified vendor intake."""
from run import Database,register_discovery_sources

def main():
 db=Database()
 result=register_discovery_sources(db,[])
 if result.get('paused'):
  print('Automatic research is paused; source synchronization skipped.')
 else:
  print('Reviewed discovery sources synchronized:',result['approved_sources'])
  from verifier import Fetcher
  from market_catalog import discover_catalog
  from official_vendor_programs import verify_program
  import json
  fetcher=Fetcher(limit=16)
  receipts,notes=discover_catalog(fetcher)
  for receipt in receipts:
   outcome=db.rpc('btb_research_publish_market_catalog',{'p_result':receipt})
   print(json.dumps({'catalog_market':receipt['catalog_key'],'action':outcome.get('action')}))
  print(json.dumps({'catalog_sources_unconfirmed':notes}))
  try:program=verify_program('raleigh-retro-vendor-intake',fetcher)
  except (OSError,ValueError):
   print('Raleigh Retro vendor intake is currently unconfirmed; no listing was published.')
  else:
   outcome=db.rpc('btb_research_publish_official_program',{'p_result':program})
   print(json.dumps({'program':program['program'],'action':outcome.get('action')}))

if __name__=='__main__':main()

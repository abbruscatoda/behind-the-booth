"""Fast authenticated deployment check for the reviewed source registry."""
from run import Database,register_discovery_sources

def main():
 result=register_discovery_sources(Database(),[])
 if result.get('paused'):
  print('Automatic research is paused; source synchronization skipped.')
 else:
  print('Reviewed discovery sources synchronized:',result['approved_sources'])

if __name__=='__main__':main()

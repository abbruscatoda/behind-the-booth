"""Run the same optional-field audit used by each scheduled worker run."""
import argparse,json
from run import Database
from verifier import Fetcher
from fact_research import audit_published

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    summary=audit_published(Database(),Fetcher(limit=120),args.dry_run)
    print(json.dumps(summary))
    if not summary.get('paused') and not summary.get('checked'):
        raise RuntimeError('No published applications could be audited; inspect source diagnostics.')

"""Invoke the opted-in digest worker. Uses the existing dedicated research credentials."""
import argparse
import json
import os
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
import re


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Alert worker redirects are not allowed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    base = os.environ.get("BTB_SUPABASE_URL", "").rstrip("/")
    url = urlparse(base)
    if (url.scheme != "https" or not url.hostname or not url.hostname.endswith(".supabase.co")
            or url.username or url.password or url.port not in (None, 443) or url.path or url.query or url.fragment):
        raise ValueError("Invalid Supabase origin")
    key = os.environ.get("BTB_SUPABASE_PUBLISHABLE_KEY", "")
    secret = os.environ.get("BTB_RESEARCH_SECRET", "")
    if not key or len(secret) != 64:
        raise ValueError("Alert worker credentials are missing")
    for _ in range(10):
        request = Request(base + "/functions/v1/opportunity-alerts", method="POST",
                          data=json.dumps({"dry_run": args.dry_run}).encode(),
                          headers={"apikey": key, "Content-Type": "application/json", "x-btb-research-secret": secret})
        try:
            with build_opener(NoRedirect()).open(request, timeout=120) as response:
                result = json.load(response)
        except HTTPError as error:
            stage = code = "unknown"
            try:
                detail = json.loads(error.read(4096))
                if re.fullmatch(r"[a-z_]{1,40}", str(detail.get("stage", ""))):
                    stage = detail["stage"]
                if re.fullmatch(r"[A-Za-z0-9_]{1,60}", str(detail.get("code", ""))):
                    code = detail["code"]
            except (ValueError, UnicodeError):
                pass
            raise RuntimeError(f"Opportunity alert batch failed (HTTP {error.code}, stage {stage}, code {code}). No credentials or recipient details are logged.") from None
        except Exception:
            raise RuntimeError("Opportunity alert batch failed. Inspect the worker status; credentials and recipient details are not logged.") from None
        print(json.dumps({k: result[k] for k in ("dry_run", "configured", "due_members", "sent", "skipped", "failed", "more") if k in result}))
        if args.dry_run or not result.get("more"):
            break


if __name__ == "__main__":
    main()

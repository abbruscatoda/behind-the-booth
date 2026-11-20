"""Resolve public application shortcuts without downloading responses or form answers.

Only exact, currently linked public Google Forms shortcuts are eligible.
A redirect is evidence about URL identity, NOT evidence the form is open.
"""
from urllib.error import HTTPError
from urllib.request import Request
from urllib.parse import urlparse
import re
from verifier import valid_url

MAX_REDIRECT_CHECKS=24
RESERVE_REQUESTS=20

def google_form_identity(url):
 """Canonical destination must be a permitted public application, not edit/prefill."""
 if not isinstance(url,str) or not valid_url(url):return None
 p=urlparse(url)
 if p.hostname!='docs.google.com':return None
 if not re.fullmatch(r'/forms/d/e/[A-Za-z0-9_-]{20,120}/viewform',p.path):return None
 return 'https://docs.google.com'+p.path

def resolve_shortcut(shortcut,fetcher):
 """Inspect the terminal redirect even when Google returns 401 to a bot."""
 if not valid_url(shortcut) or urlparse(shortcut).hostname!='forms.gle':return None
 if getattr(fetcher,'requests',0)>=getattr(fetcher,'limit',100000)-RESERVE_REQUESTS:return None
 # Use the same redirect-restricted opener as the regular fetcher.
 fetcher.requests+=1
 try:
  with fetcher.opener.open(
   Request(shortcut,method='GET',
           headers={'User-Agent':'BehindTheBoothVerifier/1.0 (+https://www.behindtheboothhq.com/contact)'}),
   timeout=15) as response:
   final=response.geturl()
 except HTTPError as error:
  if error.code not in (401,403):return None
  final=error.geturl()
 except (OSError,ValueError):return None
 return google_form_identity(final)

def reconcile_shortcuts(leads,fetcher,approved_sources):
 """Return exact source, shortcut and canonical-form receipts for the DB gate."""
 verified=[]
 seen=set()
 for lead in leads:
  if len(verified)>=MAX_REDIRECT_CHECKS:break
  target=lead.get('target_url','')
  source=lead.get('source_url','')
  if source not in approved_sources or not valid_url(target):continue
  if urlparse(target).hostname!='forms.gle':continue
  pair=(source,target)
  if pair in seen:continue
  seen.add(pair)
  if getattr(fetcher,'requests',0)>=getattr(fetcher,'limit',100000)-RESERVE_REQUESTS:break
  try:
   root,_=fetcher.get(source)
  except (OSError,ValueError):continue
  if target not in root.root.links(source):continue
  final=resolve_shortcut(target,fetcher)
  if final and final!=target:
   verified.append({'source_url':source,'target_url':target,
                    'canonical_application_url':final})
 return verified

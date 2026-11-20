"""RPC failures report only allowlisted diagnostic codes, never payloads."""
import io
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from run import Database

ENV={'BTB_SUPABASE_URL':'https://btb-example.supabase.co',
     'BTB_SUPABASE_PUBLISHABLE_KEY':'test-publishable',
     'BTB_RESEARCH_SECRET':'x'*64}

class BrokenOpener:
 def __init__(self,code,body):
  self.code=code;self.body=body
 def open(self,*args,**kwargs):
  raise HTTPError('https://btb-example.supabase.co/rest/v1/rpc/btb_research_context',
     self.code,'error',{},io.BytesIO(self.body))

class ErrorDiagnosticTests(unittest.TestCase):
 def test_constraint_code_is_visible_but_sensitive_payload_hidden(self):
  with patch.dict(os.environ,ENV),patch('run.build_opener',
         return_value=BrokenOpener(400,b'{"code":"23514","message":"private-secret"}')):
   with self.assertRaises(RuntimeError) as raised:
    Database().rpc('btb_research_context')
  self.assertIn('HTTP 400, code 23514',str(raised.exception))
  self.assertNotIn('private-secret',str(raised.exception))

 def test_unknown_postgrest_error_is_not_reflected(self):
  with patch.dict(os.environ,ENV),patch('run.build_opener',
         return_value=BrokenOpener(500,b'{"code":"EVILSECRET","message":"private-secret"}')):
   with self.assertRaises(RuntimeError) as raised:
    Database().rpc('btb_research_context')
  self.assertIn('code unknown',str(raised.exception))
  self.assertNotIn('EVILSECRET',str(raised.exception))

if __name__=='__main__':unittest.main()

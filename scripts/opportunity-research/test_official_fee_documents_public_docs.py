"""Regression tests for organizer-linked, public Google Docs in fee research."""
import unittest
from unittest.mock import patch
from verifier import Document
from official_fee_documents import fee_document_links, inspect_official_fee_documents

ORGANIZER='https://example-market.org/become-a-vendor'
DOC='https://docs.google.com/document/d/1QVgqQan9naZBfJSjxcRQg51B8gXJ9NzNVOYIBveCdRk/edit?usp=sharing'

class OfficialPublicDocumentTests(unittest.TestCase):
 def test_explicit_market_rules_doc_is_followed_with_read_only_export(self):
  page=Document('<a href="'+DOC+'">Market Rules</a>')
  self.assertEqual(fee_document_links(page,ORGANIZER,ORGANIZER),[DOC])
  with patch('official_fee_documents.fetch_public_google_document',return_value=('Guest Vendor application fee: $30. Daily booth fee: $25.','a'*64)) as read:
   result=inspect_official_fee_documents([(page,ORGANIZER)],ORGANIZER,reader=lambda *args: self.fail('No PDF expected'))
  read.assert_called_once_with(DOC)
  self.assertEqual(result['readable_count'],1)
  self.assertEqual(result['documents'][0]['hash'],'a'*64)
  self.assertEqual(result['documents'][0]['source'],'organizer_linked_public_document')
 def test_unapproved_doc_urls_are_not_followed(self):
  links=[
   DOC.replace('/edit?usp=sharing','/edit?usp=drive_link'),
   DOC.replace('/edit?usp=sharing','/edit?usp=sharing#private'),
   DOC.replace('/edit?usp=sharing','/view?usp=sharing'),
   'https://example.com/document/d/1QVgqQan9naZBfJSjxcRQg51B8gXJ9NzNVOYIBveCdRk/edit'
  ]
  page=Document(''.join('<a href="'+u+'">Market Rules</a>' for u in links))
  self.assertEqual(fee_document_links(page,ORGANIZER,ORGANIZER),[])

if __name__=='__main__':unittest.main()

import copy, unittest
from datetime import datetime,timezone,timedelta
from community_discovery import verify_research_lead,date_attested,official_url,SOURCES,Uncertain
from verifier import valid_url

NOW=datetime(2026,11,24,20,tzinfo=timezone.utc)
EVENT='https://www.songbird.bar/calendar/holiday-market'
FORM='https://docs.google.com/forms/d/e/'+'a'*40+'/viewform'
def lead(method='email'):
 event='Songbird Holiday Market. December 12, 2026. 1020 E Whitaker Mill Rd, Raleigh. Local makers and holiday shopping.'
 intake='Songbird Holiday Market. December 12, 2026. Looking for vendors. Email vendors@songbird.bar to apply.'
 proposal={'title':'Songbird Holiday Market','venue':'1020 E Whitaker Mill Rd','starts_on':'2026-12-12','ends_on':'2026-12-12','application_method':method,'application_contact':'vendors@songbird.bar','application_url':EVENT}
 if method=='instagram':
  intake='Songbird Holiday Market. December 12, 2026. Looking for vendors. DM us at @songbird.nc to apply.'
  proposal.update(application_contact='songbird.nc',application_url='https://www.instagram.com/songbird.nc/')
 if method=='form':
  event+=' Apply here: '+FORM
  intake='Songbird Holiday Market vendor application. December 12, 2026. Submit your application. Vendor fee $40 per booth.'
  proposal.update(application_url=FORM,application_contact='',booth_fee=40,fee_notes='Vendor fee $40 per booth.')
 return {'source_key':'songbird-raleigh','title':proposal['title'],'proposal':proposal,'receipts':[
  {'url':EVENT,'text':event,'role':'event','access':'public_read','checked_at':NOW.isoformat()},
  {'url':FORM if method=='form' else EVENT,'text':intake,'role':'application' if method=='form' else 'intake','access':'public_read','checked_at':NOW.isoformat(),'form_state':'accepting'}]}

class CommunityTests(unittest.TestCase):
 def test_explicit_vendor_email_and_dm_work_without_a_web_form(self):
  for method in ('email','instagram'):
   result=verify_research_lead(lead(method),NOW)
   self.assertEqual(result['candidate']['availability'],'open')
   self.assertEqual(result['candidate']['application_method'],method)
   self.assertEqual(result['candidate']['categories'],[])
 def test_live_source_linked_form_retains_labeled_vendor_fee(self):
  result=verify_research_lead(lead('form'),NOW)
  self.assertEqual(result['candidate']['booth_fee'],40)
  self.assertIsNone(result['candidate']['application_fee'])
 def test_tiered_options_find_their_own_fee_receipt_not_an_unrelated_same_amount(self):
  item=lead('form')
  item['receipts'].append({'url':FORM,'role':'fee','text':'Booth space $25. Additional electricity $40, subject to availability.','access':'public_read','checked_at':NOW.isoformat()})
  item['proposal']['pricing_options']=[{'kind':'addon','label':'Electricity','amount':40,'unit':'event','conditions':'Subject to availability.','applicable':True,'source_url':FORM}]
  self.assertEqual(verify_research_lead(item,NOW)['candidate']['pricing_options'][0]['amount'],40)
 def test_general_email_is_not_a_vendor_call(self):
  item=lead();item['receipts'][1]['text']='Contact vendors@songbird.bar for general inquiries. Songbird Holiday Market.'
  with self.assertRaisesRegex(Uncertain,'invitation'):verify_research_lead(item,NOW)
 def test_old_flyers_snippets_unreadable_sources_and_vendor_reposts_cannot_publish(self):
  changes=[lambda x:x['proposal'].update(starts_on='2025-12-12',ends_on='2025-12-12'),
   lambda x:x['receipts'][0].update(access='search_snippet'),
   lambda x:x['receipts'][0].update(checked_at=(NOW-timedelta(hours=7)).isoformat()),
   lambda x:x['receipts'][0].update(url='https://www.instagram.com/p/abcdef/',owner='theshopkiki'),
   lambda x:x['receipts'][1].update(text='General interest list. Songbird Holiday Market vendor application. December 12, 2026.')]
  for change in changes:
   item=lead();change(item)
   with self.subTest(item=item),self.assertRaises(Uncertain):verify_research_lead(item,NOW)
 def test_closed_override_beats_apply_today_and_cannot_be_open(self):
  item=lead();item['receipts'][1]['text']+=' UPDATE: APPLICATIONS HAVE CLOSED AS OF 11/16. APPLY TODAY!'
  self.assertEqual(verify_research_lead(item,NOW)['candidate']['availability'],'closed')
 def test_announcement_does_not_become_open_on_its_opening_date_without_new_form_proof(self):
  item=lead('form');item['proposal']['opens_on']='2026-12-01';item['receipts'][1].update(text='Songbird Holiday Market vendor application. December 12, 2026. Applications open December 1, 2026. Vendor fee $40.',form_state='not_open')
  self.assertEqual(verify_research_lead(item,NOW)['candidate']['availability'],'announced')
  later=datetime(2026,12,1,12,tzinfo=timezone.utc)
  for receipt in item['receipts']:receipt['checked_at']=later.isoformat()
  with self.assertRaisesRegex(Uncertain,'live vendor form'):verify_research_lead(item,later)
 def test_future_opening_and_date_only_cutoff_are_separate(self):
  item=lead();item['proposal'].update(opens_on='2026-12-01',deadline_date='2026-12-08')
  item['receipts'][1]['text']+=' Applications open December 1, 2026. Applications close December 8, 2026.'
  c=verify_research_lead(item,NOW)['candidate'];self.assertEqual(c['deadline_date'],'2026-12-08');self.assertIsNone(c['deadline'])
 def test_unlinked_form_and_wrong_venue_do_not_publish(self):
  item=lead('form');item['receipts'][0]['text']=item['receipts'][0]['text'].split(' Apply here:')[0]
  with self.assertRaisesRegex(Uncertain,'exact vendor application'):verify_research_lead(item,NOW)
  item=lead();item['receipts'][0]['text']=item['receipts'][0]['text'].replace('1020 E Whitaker Mill Rd','Elsewhere')
  with self.assertRaisesRegex(Uncertain,'reviewed venue'):verify_research_lead(item,NOW)
 def test_explicit_year_and_range_dates(self):
  self.assertTrue(date_attested('2027-08-29','August 28–29, 2027'))
  self.assertFalse(date_attested('2027-08-29','August 28–29, 2026'))
  self.assertFalse(date_attested('2027-08-29','August 28–29'))
 def test_reviewed_website_roots_are_fetchable_and_query_scoped(self):
  for source in SOURCES.values():
   for url in source['sources']:self.assertTrue(valid_url(url),url)
  source=SOURCES['lazy-daze-cary']
  self.assertFalse(official_url('https://www.zapplication.org/event-info.php?ID=99999',source))
  self.assertFalse(valid_url('https://linktr.ee/random-profile'))
  self.assertFalse(valid_url('https://www.zapplication.org/account'))

if __name__=='__main__':unittest.main()

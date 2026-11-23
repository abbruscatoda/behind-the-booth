import unittest,json
from datetime import datetime,timezone
from verifier import Document,Uncertain,valid_url
from independent_markets import read_monday,discover_independent,monitoring_leads,GRL,GRL_HUB

APP='https://forms.monday.com/forms/'+'a'*32+'?r=use1'
NOW=datetime(2026,11,23,15,tzinfo=timezone.utc)
def payload(title='DECEMBER 5TH MARKET | WAVERLY PLACE CARY',fee=85):
 return {'token':'a'*32,'board_view_settings':{'formTitle':title,'formDescription':'LOCATION: WAVERLY PLACE CARY | 302 Colonades Way',
  'welcomeViewDescription':f'The standard vendor fee for an outdoor 10ft x 10ft tent (required) is ${fee}. Fees are non-refundable.',
  'columns':{k:{'visible':True,'question':title} for k,title in [('business','Business Name'),('email','Vendor Email'),('desc','Business Description'),('cats','Categories')]}},
  'included_columns':[{'id':'business'},{'id':'email'},{'id':'desc'},{'id':'cats','settings':{'labels':[{'id':1,'name':'Baked Goods'},{'id':2,'name':'Lemonade'},{'id':3,'name':'Coffee & Tea products (pop coffee & matcha bars are not allowed)'},{'id':4,'name':'Jewelry'}]}}]}
def page(data):return Document('<script>window.form_data = '+json.dumps(data)+';</script>')
class Pages:
 limit=100;requests=0
 def __init__(self,data=None,year=2026,label='WAVERLY PLACE CARY',day='12/5'):
  self.docs={GRL:Document(f'<h2>{year} MARKETS</h2><h3>{day}</h3><h4>{label}</h4>'),GRL_HUB:Document(f'<a href="{APP}">VENDOR APP | DECEMBER 5TH | WAVERLY PLACE CARY</a>'),APP:page(data or payload())}
 def get(self,url):
  if url not in self.docs:raise OSError('unavailable')
  return self.docs[url],'a'*64

class IndependentMarketTests(unittest.TestCase):
 def test_public_welcome_fee_and_visible_options_are_read_without_running_javascript(self):
  form=read_monday(page(payload()),APP)
  self.assertIn('$85',form['text']);self.assertIn('Lemonade',form['options'])
  results,notes=discover_independent(Pages(),NOW)
  self.assertEqual(len(results),1);self.assertFalse(notes)
  c=results[0]['candidate'];self.assertEqual(c['booth_fee'],85)
  self.assertIsNone(c['deadline']);self.assertIsNone(c['application_fee']);self.assertIsNone(c['deposit'])
  self.assertIn('explicitly excluded',c['eligibility']);self.assertEqual(c['starts_on'],'2026-12-05')
 def test_historical_calendar_does_not_roll_forward_or_publish_from_new_year_guess(self):
  self.assertFalse(discover_independent(Pages(year=2025),NOW)[0])
  self.assertFalse(discover_independent(Pages(),datetime(2027,1,1,tzinfo=timezone.utc))[0])
 def test_exact_date_and_venue_pair_must_be_corrobated(self):
  self.assertFalse(discover_independent(Pages(label='TRANSFER FOOD HALL',day='12/5'),NOW)[0])
  self.assertFalse(discover_independent(Pages(day='12/19'),NOW)[0])
  self.assertFalse(discover_independent(Pages(payload(title='DECEMBER 19TH | WAVERLY PLACE CARY')),NOW)[0])
 def test_disabled_or_unreadable_forms_never_become_open_applications(self):
  data=payload();data['board_view_settings']['restrictByDate']=True
  self.assertFalse(discover_independent(Pages(data),NOW)[0])
  pages=Pages();pages.docs[APP]=Document('<h1>Loading</h1>')
  self.assertFalse(discover_independent(pages,NOW)[0])
 def test_explicit_closure_can_only_propose_closed_intake(self):
  pages=Pages();pages.docs[APP]=Document('<h1>This form is closed</h1>')
  result,_=discover_independent(pages,NOW)
  self.assertEqual(result[0]['candidate']['availability'],'closed')
  self.assertIsNone(result[0]['candidate']['booth_fee'])
 def test_unpublished_questions_and_disabled_choices_are_not_used_as_facts(self):
  data=payload();data['included_columns'][-1]['settings']['deactivated_labels']=[2]
  data['board_view_settings']['columns']['secret']={'visible':False,'question':'Hidden fee is $1'}
  data['included_columns'].append({'id':'secret'})
  result=read_monday(page(data),APP)
  self.assertNotIn('Lemonade',result['options']);self.assertNotIn('Hidden fee',result['text'])
 def test_malformed_payloads_and_mismatched_public_form_ids_fail_closed(self):
  data=payload();data['token']='b'*32
  with self.assertRaises(Uncertain):read_monday(page(data),APP)
  with self.assertRaises(Uncertain):read_monday(Document('<script>window.form_data={broken};</script>'),APP)
 def test_reviewed_link_hub_scope_does_not_allow_other_profiles_admin_or_prefilled_forms(self):
  self.assertTrue(valid_url(GRL_HUB));self.assertTrue(valid_url(APP))
  for url in ['https://linktr.ee/unreviewed','https://forms.monday.com/admin','https://forms.monday.com/forms/'+'a'*32+'?email=private@example.org']:
   self.assertFalse(valid_url(url))
 def test_all_supplied_organizers_are_preserved_as_monitoring_leads_without_open_claims(self):
  leads=monitoring_leads();self.assertEqual(len(leads),8)
  self.assertTrue(all(valid_url(x['source_url']) for x in leads))
  self.assertTrue(all('availability' not in x and 'starts_on' not in x for x in leads))

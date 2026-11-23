"""Synthetic regressions for missed published prices; not real event fees."""
import json,unittest
from datetime import datetime,timezone
from verifier import Document
from google_forms import read_public_form
from application_prices import published_price_options,public_form_url,vendor_form_links
from fact_research import audit_item
from test_fact_research import Fetch,item,documents

SOURCE='https://shoplocalraleigh.org/brewgaloo/'
HUB=SOURCE+'brewgaloo-applications/'
APP='https://docs.google.com/forms/d/e/'+'a'*30+'/viewform'
FOOD='https://docs.google.com/forms/d/e/'+'b'*30+'/viewform'
NOW=datetime(2026,11,23,17,tzinfo=timezone.utc)
def form(body,year=2027,control='Submit'):
    return f'<h1>Brewgaloo {year} Vendor Application</h1>'+body+f'<div role="button">{control}</div>'
def listing(app=HUB):
    return item(SOURCE,app,'brewgaloo',title='Brewgaloo 2027 — Vendor Applications',starts_on='2027-04-23',ends_on='2027-04-24',schedule_type='dated_event')
def audit(pages,app=HUB):return audit_item(listing(app),Fetch(pages),NOW,documents())

class ApplicationPriceTests(unittest.TestCase):
    def test_google_price_visible_before_next_is_published_as_a_scoped_option(self):
        source=f'<a href="{APP}">Vendor application</a>'
        r=audit({SOURCE:source,APP:form('<p>Retail vendor booth fee: $350 per event, payable upon acceptance.</p><p>Application fee: $15.</p>',control='Next')},APP)
        self.assertEqual([(p['amount'],p['kind']) for p in r['facts']['pricing_options']],[(350,'booth'),(15,'application')])
        self.assertEqual(r['facts']['application_access'],'partial')
        self.assertEqual(r['facts']['application_fee']['status'],'options')
        self.assertIsNone(r['anchor']['booth_fee'])
    def test_application_hub_reads_distinct_vendor_forms_and_retains_source_and_vendor_type(self):
        hub=f'<p>Applications are open year-round.</p><a href="{APP}">Vendors</a><a href="{FOOD}">Food Truck Application</a><a href="{APP}">Vendors</a>'
        r=audit({SOURCE:f'<a href="{HUB}">Applications</a>',HUB:hub,APP:form('<p>Retail vendor booth fee: $350 per event.</p>'),FOOD:form('<p>Food truck vendor fee: $800 per event.</p>')})
        prices=r['facts']['pricing_options']
        self.assertEqual([(p['amount'],p['source_url']) for p in prices],[(350,APP),(800,FOOD)])
        self.assertIn('Food truck',prices[1]['label'])
        self.assertEqual(r['facts']['deadline']['status'],'rolling')
        self.assertEqual(len(r['application_sources']),2)
        self.assertIsNone(r['anchor']['deadline'])
    def test_blocked_form_does_not_discard_another_public_forms_prices_or_claim_complete_access(self):
        r=audit({SOURCE:f'<a href="{HUB}">Applications</a>',HUB:f'<a href="{APP}">Vendors</a><a href="{FOOD}">Food Trucks</a>',APP:form('<p>Booth fee: $350.</p>'),FOOD:OSError('requires login')})
        self.assertEqual(r['facts']['pricing_options'][0]['amount'],350)
        self.assertEqual(r['facts']['application_access'],'partial')
        self.assertEqual(r['application_source_diagnostics'][0]['status'],'access_limited')
    def test_signin_and_old_year_forms_never_supply_a_price(self):
        for body in ['<h1>Sign in to continue</h1>',form('<p>Booth fee: $999.</p>',year=2026)]:
            r=audit({SOURCE:f'<a href="{HUB}">Applications</a>',HUB:f'<a href="{APP}">Vendor Application</a>',APP:body})
            self.assertEqual(r['facts']['pricing_options'],[])
            self.assertEqual(r['facts']['pricing']['status'],'unconfirmed')
    def test_long_published_schema_intro_is_not_dropped_with_its_fee_terms(self):
        intro='Vendor information and festival participation details. '*40+'. Retail vendor booth fee: $350 per event.'
        data=[None,[intro]]
        doc=Document(form('<script>var FB_PUBLIC_LOAD_DATA_='+json.dumps(data)+';</script>',control='Next'))
        parsed=read_public_form(doc)
        self.assertTrue(any('$350' in b for b in parsed['blocks']))
        self.assertEqual(published_price_options(parsed['blocks'],APP,'a'*64)[0]['amount'],350)
        self.assertFalse(parsed['complete'])
    def test_deposits_sponsors_admission_and_conflicting_standards_do_not_become_booth_prices(self):
        prices=published_price_options(['Booth fee: $100.','Booth fee: $150.','Refundable deposit: $200.','Festival admission: $25.','Sponsorship booth fee: $1000.'],APP,'a'*64)
        self.assertEqual([(p['amount'],p['kind']) for p in prices],[(200,'addon')])
    def test_price_units_and_sold_out_options_remain_distinct(self):
        prices=published_price_options(['Daily booth fee: $30 per day.','Season vendor fee: $500 per season.','Large booth fee: $150, sold out.'],APP,'a'*64)
        self.assertEqual([p['unit'] for p in prices],['day','season','event'])
        self.assertFalse(prices[2]['applicable']);self.assertTrue(prices[2]['unavailable'])
    def test_only_direct_vendor_links_and_safe_google_sharing_parameters_are_used(self):
        html=Document(f'<a href="{APP}?ouid=123&usp=sharing">Vendor Application</a><a href="{FOOD}">Band Application</a><a href="{FOOD}?entry.1=answer">Food Trucks</a><a href="{FOOD}">Sponsorship Vendor Booth</a>')
        self.assertEqual(vendor_form_links(html,HUB),[APP])
        self.assertIsNone(public_form_url(APP+'?entry.1=answer'))
    def test_unlinked_hub_never_borrows_a_related_events_forms(self):
        with self.assertRaisesRegex(ValueError,'no longer binds'):
            audit({SOURCE:'<p>Brewgaloo 2027</p>',HUB:f'<a href="{APP}">Vendors</a>',APP:form('<p>Booth fee: $999.</p>')})

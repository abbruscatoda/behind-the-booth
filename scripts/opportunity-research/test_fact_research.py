"""Regression fixtures for the actual missing-field failures vendors reported."""
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
from verifier import Document,valid_url,Uncertain
from fact_research import audit_item,audit_published,date_only_deadline
from official_fee_documents import _safe_pdf,fee_document_links
from form_fees import extract_labeled_fees

NOW=datetime(2026,11,22,16,tzinfo=timezone.utc)
FVG_SOURCE='https://www.fvgrowersmarket.com/vendor-application'
FVG_APP='https://form.jotform.com/242064838372157'
WAKE='https://www.wakeforestnc.gov/parks-recreation-cultural-resources/prcr-food-vendors'
COGNITO='https://www.cognitoforms.com/TownOfWakeForestPRCR1/_2027TownOfWakeForestParksRecreationCulturalResourcesSpecialEventFoodVendingOpportun'
WW='https://westernwakefarmersmarket.org/apply'
WW_APP='https://forms.gle/DmuLW5ni7Bu3Avhj8'
STATE='https://www.ncagr.gov/divisions/marketing/farmers-markets-agricultural-centers/state-farmers-market-raleigh/vendor-information'
STATE_APP='https://www.ncagr.gov/media/5343/download?attachment='

class Fetch:
    def __init__(self,pages):self.pages=pages;self.requests=0;self.limit=120
    def get(self,url):
        self.requests+=1
        html=self.pages[url]
        if isinstance(html,Exception):raise html
        return Document(html),'a'*64

def item(source,app,slug='test-market',**overrides):
    return {'id':'test-id','title':'Test Market','source_url':source,'application_url':app,
            'starts_on':'2027-01-01','ends_on':'2027-12-31','market_slug':slug,
            'schedule_type':'seasonal_application','booth_fee':None,'application_fee':None,
            'deposit':None,'deadline':None,**overrides}

def documents(*texts):
    return lambda pages,source:{'documents':[{'text':text,'url':f'https://westernwakefarmersmarket.org/s/fees-{i}.pdf','hash':str(i+1)*64} for i,text in enumerate(texts)],'readable_count':len(texts),'blocked_count':0}

def state_schedule(year,price):
    return f'''State Farmers Market Effective April 1, {year}
    In Season (Apr-Dec) Off Season (Jan-Mar)
    Farmers Area: (Farmers In-State): Per Selling Space/per Day (Monday through Friday) ${price} $15
    Farmers Area: (Farmers In-State): Per Selling Space/per Day (Saturday/Sunday if attendance less than 6 days per week) $50 $15
    Non-Farmer Vendors in Farmers Area (Crafters, Baked Good Sellers, etc. In-State): Per Selling Space/per Day (Monday through Friday) $45 $35
    Non-Farmer Vendors in Farmers Area (Crafters, Baked Good Sellers, etc. In-State): Per Selling Space/per Day (Saturday/Sunday if attendance less than 6 days per week) $75 $35'''

class OptionalFactTests(unittest.TestCase):
    def test_explicit_free_application_words_are_distinct_from_free_admission(self):
        for text in ['Applications are free. Booth costs vary by event.',
                     'Applying costs nothing; booths are billed separately.',
                     'No cost associated with your application.']:
            self.assertEqual(extract_labeled_fees(text)['application_fee'],0)
        self.assertIsNone(extract_labeled_fees('Free admission. Vendor Fee $60.')['application_fee'])
    def test_date_only_deadline_is_not_an_event_date_or_invented_clock(self):
        for text in ['Event: November 27, 2026. Apply now.',
                     'Applications open November 9, 2026.',
                     'Registration deadline: February 30, 2027.',
                     'Application deadline: November 27, 2026 at 5 PM.']:
            self.assertIsNone(date_only_deadline(text))
        self.assertEqual(date_only_deadline('Registration deadline: 11/28/26 or until spots are filled.'),
                         ('2026-11-28','Registration deadline: 11/28/26',True))
        self.assertIsNone(date_only_deadline('Application deadline: November 27, 2026. Application deadline: December 1, 2026.'))

    def test_fvg_retains_guest_and_season_prices_with_units(self):
        source=f'<a href="{FVG_APP}">New Vendor Application</a>'
        app='<h1>2027 NEW Vendor Application</h1><p>Full-time, $260 (22 Saturdays). Part-time, $180 (11 Saturdays). Guest $30 per day. Category 2: Processed/Prepared Food & Beverage. Category 4: Non-Edible Craft and Artisan Products.</p><button>Submit</button>'
        result=audit_item(item(FVG_SOURCE,FVG_APP,'fuquay-varina-growers-market'),Fetch({FVG_SOURCE:source,FVG_APP:app}),NOW,documents())
        facts=result['facts'];options=facts['pricing_options']
        self.assertEqual([(p['amount'],p['unit']) for p in options],[(30,'day'),(260,'season'),(180,'season')])
        self.assertEqual(options[1]['conditions'],'22 Saturdays')
        self.assertNotIn('amount',facts['application_fee'])
        self.assertEqual(facts['application_fee']['status'],'not_listed')
        self.assertIn('Food & Beverages',facts['categories'])

    def test_jotform_published_choices_and_guest_only_artisan_restriction(self):
        source=f'<a href="{FVG_APP}">New Vendor Application</a>'
        app='<h1>2027 NEW Vendor Application</h1><p>Full-time, $260 (22 Saturdays). Part-time, $180 (11 Saturdays). Guest $30 per day. Artisans may only apply as guest vendors.</p><input type="checkbox" value="Category 2: Processed/Prepared Food &amp; Beverage"><input type="checkbox" value="Category 4: Non-Edible Craft and Artisan Products"><input type="hidden" value="Category 1: Raw or minimally processed farm products"><button>Submit</button>'
        facts=audit_item(item(FVG_SOURCE,FVG_APP,'fuquay-varina-growers-market'),Fetch({FVG_SOURCE:source,FVG_APP:app}),NOW,documents())['facts']
        self.assertEqual(facts['categories'],['Food & Beverages','Handmade Crafts'])
        self.assertIn('Artisans may apply only as guest',facts['restrictions'][0])
        self.assertTrue(all('artisans are not eligible' in option['conditions'] for option in facts['pricing_options'] if option['unit']=='season'))

    def test_wake_public_deadline_survives_dynamic_form(self):
        source=f'<p>Beginning Monday, Nov. 9, 2026, the department accepts applications for 2027 PRCR events. The online application will be activated through Friday, Nov. 27.</p><a href="{COGNITO}">Application</a><p>There typically is a vendor fee associated with participation at events.</p>'
        pdf='Fee Structure $40 | $30 RD (Event - 4 Hours) $175 | $150 RD (Special Event) Hold Harmless'
        result=audit_item(item(WAKE,COGNITO,'wake-forest-prcr-special-events'),Fetch({WAKE:source,COGNITO:'<h1>Loading application</h1>'}),NOW,documents(pdf))
        facts=result['facts']
        self.assertEqual(facts['deadline']['date'],'2026-11-27')
        self.assertEqual(facts['application_access'],'access_limited')
        self.assertEqual(facts['pricing']['status'],'varies_by_event')
        self.assertTrue(all(not p['applicable'] for p in facts['pricing_options']))
        self.assertIn('Food Trucks',facts['categories'])
        self.assertIsNone(result['anchor']['deadline'])

    def test_regular_market_pdf_prices_never_become_craft_prices(self):
        source=f'<a href="{WW_APP}">Regular Vendor Application</a>'
        pdf='New Vendor Application Fee Covers initial review costs $35 Craft Vendor Application Fee Covers craft review costs $10 Returning Vendor Application Fee Covers updates $25 Regular Vendor Attends at least 30 days per year $20 Seasonal or Part-Time Vendor Attends at least 16 days per year $25 Guest Vendor Attends fewer than 16 days per year $30'
        receipt=audit_item(item(WW,WW_APP,'western-wake-farmers-market',schedule_type='rolling_market'),Fetch({WW:source,WW_APP:OSError('not readable')}),NOW,documents(pdf.replace(' ','  ')))
        options=receipt['facts']['pricing_options']
        self.assertEqual([(p['label'],p['amount']) for p in options[:2]],[('New vendor',35),('Returning vendor',25)])
        self.assertEqual([p['amount'] for p in options[2:]],[20,25,30])
        self.assertFalse(any(p['amount']==10 for p in options))
        self.assertEqual(receipt['facts']['application_fee']['status'],'options')

    def test_newer_state_schedule_wins_over_still_linked_legacy_pdf(self):
        source=f'<a href="{STATE_APP}">New Vendor Application</a>'
        receipt=audit_item(item(STATE,STATE_APP,'state-farmers-market',schedule_type='rolling_market'),Fetch({STATE:source,STATE_APP:ValueError('PDF')}),NOW,documents(state_schedule(2023,20),state_schedule(2026,25)))
        facts=receipt['facts']
        self.assertIn('2026-04-01',facts['pricing']['summary'])
        self.assertEqual(facts['pricing_options'][0]['amount'],25)
        self.assertEqual(facts['pricing_options'][1]['amount'],15)
        self.assertIn('January–March',facts['pricing_options'][1]['conditions'])

    def test_current_holly_season_table_supersedes_old_linked_document(self):
        source='https://www.hollyspringsnc.gov/1824/Become-a-Vendor'
        app='https://managemymarket.com/VendorRegister.aspx?orgID=933'
        html=f'<p>Farmers Market Fees: Season 20 (May 2026 - April 2027)</p><a href="{app}">Register</a><table><tr><td>Extended Season Weekly Vendor (50 dates)</td><td>$442</td></tr><tr><td>Winter Season Daily Vendor</td><td>$20</td></tr><tr><td>Electricity</td><td>$25</td></tr></table>'
        result=audit_item(item(source,app,'holly-springs-farmers-market',starts_on='2026-05-01',ends_on='2027-04-30',schedule_type='recurring_season'),Fetch({source:html,app:OSError('Not readable')}),NOW,documents('Season 19: May 2025–April 2026. Daily rate $999'))
        self.assertEqual([p['amount'] for p in result['facts']['pricing_options']],[442,20])
        self.assertIn('waiting list',result['facts']['pricing']['summary'])

    def test_fee_download_and_special_form_hosts_are_narrowly_scoped(self):
        self.assertTrue(_safe_pdf('https://www.ncagr.gov/marketing/sfm-fee-schedule/download?attachment=',STATE))
        self.assertTrue(_safe_pdf('https://www.ncagr.gov/marketing/sfm-fee-schedule/download?attachment',STATE))
        self.assertEqual(fee_document_links(Document('<a href="/s/Vendor-Fee-Schedule.pdf">Download Fees PDF</a>'),WW,WW),['https://westernwakefarmersmarket.org/s/Vendor-Fee-Schedule.pdf'])
        self.assertFalse(_safe_pdf('https://www.ncagr.gov/marketing/sfm-fee-schedule/download?url=https://evil.test',STATE))
        self.assertFalse(_safe_pdf('https://www.ncagr.gov/media/other/download?attachment=',STATE))
        self.assertTrue(valid_url(COGNITO))
        self.assertFalse(valid_url('https://www.cognitoforms.com/SomeoneElse/OtherForm'))
        self.assertFalse(valid_url('https://managemymarket.com/VendorRegister.aspx?orgID=123'))

    def test_missing_fee_and_sponsorship_never_become_free_or_booth_price(self):
        app='https://www.eventeny.com/events/vendor/?id=59229'
        text='<h1>Test Market</h1><p>'+'Vendor applications and original handmade products. '*5+'</p><table><tr><td>Vendor Fee</td><td>$60.00</td><td>Charged after acceptance</td></tr><tr><td>Lead Sponsor</td><td>$1000</td></tr></table><a>Start Application</a>'
        result=audit_item(item(app,app),Fetch({app:text}),NOW,documents())
        booths=[p for p in result['facts']['pricing_options'] if p['kind']=='booth']
        self.assertEqual(len(booths),1)
        self.assertEqual(booths[0]['amount'],60)
        self.assertTrue(any(p['kind']=='addon' and p['amount']==1000 for p in result['facts']['pricing_options']))
        self.assertNotIn('amount',result['facts']['application_fee'])

    def test_unlinked_application_cannot_be_used_as_evidence(self):
        with self.assertRaises(Uncertain):
            audit_item(item(FVG_SOURCE,FVG_APP),Fetch({FVG_SOURCE:'<p>Market</p>',FVG_APP:'<p>Some unrelated form</p>'}),NOW,documents())

    def test_short_link_identity_is_distinct_from_form_openness_or_booth_cost(self):
        source='https://www.artsplosure.org/first-night-raleigh'
        app='https://docs.google.com/forms/d/e/1FAIpQLScPXt0euH9ziXcAR3tA9BkXTQ4qtnTK9V6aqttIYbxlittBlA/viewform'
        html='<p>First Night Raleigh December 31, 2026. Submit a $200 (food vendor) or $50 (novelty vendor) refundable deposit.</p><a href="https://forms.gle/e8JRmQUUcEirUzzY9">Apply Here</a>'
        with patch('lead_reconciliation.resolve_shortcut',return_value=app):
            receipt=audit_item(item(source,app,'first-night-raleigh',starts_on='2026-12-31'),Fetch({source:html,app:OSError('Not readable')}),NOW,documents())
        self.assertEqual(receipt['facts']['application_access'],'access_limited')
        self.assertTrue(all(p['kind']=='addon' for p in receipt['facts']['pricing_options']))
        self.assertEqual([p['amount'] for p in receipt['facts']['pricing_options']],[200,50])

    def test_dry_run_reads_context_and_sources_without_writes(self):
        calls=[]
        class DB:
            def rpc(self,name,body=None):
                calls.append(name)
                if name!='btb_research_fact_context':raise AssertionError('Unexpected write')
                return {'enabled':True,'items':[]}
        self.assertEqual(audit_published(DB(),Fetch({}),True,NOW)['checked'],0)
        self.assertEqual(calls,['btb_research_fact_context'])

if __name__=='__main__':unittest.main()

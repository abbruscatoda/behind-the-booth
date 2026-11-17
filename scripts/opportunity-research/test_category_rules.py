import unittest
from datetime import datetime, timezone
from verifier import Document, category_research, verify
from category_rules import research_categories
from test_verifier import fixtures, FakeFetcher, SOURCE, APP, NOW

class CategoryRulesTests(unittest.TestCase):
 def facts(self,event='',app='',extras=()):
  return research_categories(Document(event),Document(app),SOURCE,APP,NOW,'a'*64,'b'*64,extras)
 def test_foodie_name_alone_is_not_food_evidence(self):
  r,c=self.facts('<h1>Durham Foodie Fare</h1><p>Food trucks and music!</p>')
  self.assertEqual(r['categories'],{});self.assertEqual(c,[])
 def test_explicit_food_vendor_description(self):
  r,c=self.facts('<h2>About the event</h2><p>Local food and art vendors.</p>')
  self.assertEqual(r['categories']['Food & Beverages']['status'],'eligible')
  self.assertNotIn('Food Trucks',r['categories'])
  self.assertEqual(r['application_url'],APP);self.assertTrue(r['checked_at'])
 def test_partial_list_does_not_exclude_food(self):
  r,c=self.facts(app='<h2>About the application</h2><p>Handmade craft vendors.</p>')
  self.assertIn('Handmade Crafts',r['categories']);self.assertNotIn('Food & Beverages',r['categories'])
 def test_form_options_are_scoped_and_disabled_ignored(self):
  r,c=self.facts(app='<fieldset><legend>Which category best fits your work?</legend><select><option>Baked goods</option><option>Soap</option><option disabled>Pet products</option><option>Other</option></select></fieldset><label>Jewelry</label>')
  self.assertEqual(set(r['categories']),{'Food & Beverages','Bath, Body & Beauty','Other'})
  self.assertIn('freshly prepared drinks',r['categories']['Food & Beverages']['note'])
 def test_jotform_span_question_and_enabled_radio_values(self):
  r,c=self.facts(app='<li class="form-line"><span class="form-label">Which category best fits your work? *</span><input type="radio" value="Baked Goods"><label aria-hidden="true">Baked Goods</label><input type="radio" value="Food Trucks or Trailers"><input type="radio" disabled value="Pet Products"></li>')
  self.assertEqual(set(r['categories']),{'Food & Beverages','Food Trucks'})
 def test_footer_hidden_and_scripts_are_not_facts(self):
  r,c=self.facts(app='<h2>About the application</h2><footer>Food vendors</footer><p hidden>Handmade</p><div aria-hidden="true">Jewelry</div><p style="display:none">Soap</p><script>Artists</script>')
  self.assertEqual(r['categories'],{})
 def test_application_exclusion_overrides_general_description(self):
  r,c=self.facts('<h2>About the event</h2><p>Food vendors</p>','<h2>About the application</h2><p>No food vendors. No food trucks.</p>')
  self.assertEqual(r['categories']['Food & Beverages']['status'],'excluded')
  self.assertEqual(r['categories']['Food Trucks']['status'],'excluded');self.assertEqual(c,[])
 def test_suffix_exclusion_and_other_types(self):
  r,c=self.facts(app='<h2>About the application</h2><p>Jewelry is not accepted. No pet products.</p>')
  self.assertEqual(r['categories']['Jewelry & Accessories']['status'],'excluded')
  self.assertEqual(r['categories']['Pet Products']['status'],'excluded')
 def test_conflicting_application_facts_are_removed(self):
  r,c=self.facts(app='<h2>About the application</h2><p>Food vendors welcome. No food vendors.</p>')
  # Explicit positive and negative wording in one source must not silently win.
  self.assertEqual(c,['Food & Beverages']);self.assertNotIn('Food & Beverages',r['categories'])
 def test_food_truck_sold_out_is_not_general_food_exclusion(self):
  r,c=self.facts(app='<table><tr><td>Food Trucks</td><td>Sold out</td></tr></table>')
  self.assertEqual(r['categories']['Food Trucks']['status'],'unavailable');self.assertNotIn('Food & Beverages',r['categories'])
 def test_separate_active_application(self):
  r,c=self.facts('<div class="app-card"><a href="/events/vendor/?id=999">Food Trucks</a><button-element>Apply now</button-element></div>')
  self.assertEqual(r['categories']['Food Trucks']['status'],'separate_application')
 def test_inactive_separate_application_is_not_advertised(self):
  r,c=self.facts('<div class="app-card"><a href="/events/vendor/?id=999">Food Trucks</a><button-element disabled>Apply now</button-element></div>')
  self.assertNotIn('Food Trucks',r['categories'])
 def test_wrong_supplement_application_or_heading_is_ignored(self):
  class Pages:
   def get(self,url):return Document('<h1>Other Market</h1><p>Food vendors</p><a href="'+APP+'">Apply</a>'),'c'*64
  r,c=category_research(Document(''),Document(''),SOURCE,APP,Pages(),NOW,'a'*64,'b'*64,('durham-foodie-fare','Durham Foodie Fare'))
  self.assertNotIn('Food & Beverages',r['categories'])
 def test_matching_official_market_page_supports_food(self):
  class Pages:
   def get(self,url):return Document('<main><h1>Durham Foodie Fare</h1><p>Local food and art vendors.</p><a href="'+APP+'">Apply</a></main>'),'c'*64
  r,c=category_research(Document(''),Document(''),SOURCE,APP,Pages(),NOW,'a'*64,'b'*64,('durham-foodie-fare','Durham Foodie Fare'))
  fact=r['categories']['Food & Beverages'];self.assertEqual(fact['source_hash'],'c'*64);self.assertEqual(fact['source_url'],'https://makrs.com/durham-foodie-fare')
 def test_supplement_failure_keeps_unknown(self):
  class Pages:
   def get(self,url):raise ValueError('unavailable')
  r,c=category_research(Document(''),Document(''),SOURCE,APP,Pages(),NOW,'a'*64,'b'*64,('durham-foodie-fare','Durham Foodie Fare'))
  self.assertEqual(r['categories'],{})
 def test_verifier_routes_category_conflicts_to_review(self):
  source,app=fixtures(app_text='<p>Deadline: Nov 29, 2026 11:59 pm (GMT-05:00) Eastern Time</p><a>Start Application</a><h2>About the application</h2><p>Food vendors welcome. No food vendors.</p>')
  r=verify(SOURCE,APP,FakeFetcher(source,app),NOW)
  self.assertEqual(r['decision'],'review');self.assertEqual(r['category_conflicts'],['Food & Beverages'])

if __name__=='__main__':unittest.main()

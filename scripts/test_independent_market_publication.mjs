import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';

test('independent market publication preserves authorization, evidence, and manual holds',async t=>{
 const db=new PGlite();
 await db.exec(await readFile(new URL('./fixtures/membership.sql',import.meta.url),'utf8'));
 await db.exec(`
 ALTER TABLE public.markets ALTER COLUMN id SET DEFAULT gen_random_uuid();
 ALTER TABLE public.markets ADD COLUMN name text,ADD COLUMN city text,ADD COLUMN state text,ADD COLUMN organizer text,ADD COLUMN description text,ADD COLUMN website_url text,ADD COLUMN is_sample boolean DEFAULT false;
 ALTER TABLE public.vendor_opportunities ADD COLUMN automation_hold boolean DEFAULT false,ADD COLUMN verification_policy text,ADD COLUMN last_checked_at timestamptz,ADD COLUMN research_notes text,ADD COLUMN review_reason text,ADD COLUMN updated_at timestamptz DEFAULT now();
 CREATE TABLE public.btb_research_settings(id boolean PRIMARY KEY,enabled boolean);INSERT INTO public.btb_research_settings VALUES(true,true);
 CREATE TABLE public.market_occurrences(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),market_id uuid,starts_on date,ends_on date,title text,UNIQUE(market_id,starts_on,ends_on));
 CREATE TABLE public.btb_research_audit(opportunity_id uuid,action text,reason text,evidence jsonb);
 CREATE TABLE btb_private.market_catalog_receipts(catalog_key text PRIMARY KEY,market_id uuid,source_url text,source_hash text,checked_at timestamptz);
 CREATE TABLE btb_private.triangle_research_sources(source_url text PRIMARY KEY,organizer text,city text,active boolean,updated_at timestamptz DEFAULT now());
 CREATE TABLE btb_private.triangle_discovery_leads(target_url text UNIQUE,source_url text,title text,organizer text,city text,notes text,review_state text,published_opportunity_id uuid,resolved_at timestamptz,research_reason text,last_seen timestamptz);
 `);
 const root=new URL('../supabase/migrations/',import.meta.url);
 const migration=(await readdir(root)).find(path=>path.endsWith('_independent_market_discovery.sql'));
 try{await db.exec(await readFile(new URL(migration,root),'utf8'));}catch(error){delete error.query;throw error;}
 const now=(await db.query('select now()::text as stamp')).rows[0].stamp;
 const day=(await db.query("select ((now() at time zone 'America/New_York')::date+12)::text as day")).rows[0].day;
 const c={market_slug:'grl-market-at-waverly-place',market_name:'GRL Market at Waverly Place',organizer:'GRL Market',city:'Cary',state:'NC',title:'GRL Market at Waverly Place',venue:'Waverly Place, 302 Colonades Way, Cary, NC',starts_on:day,ends_on:day,schedule_type:'dated_event',source_url:'https://grlmarket.com/',application_url:'https://forms.monday.com/forms/'+'a'.repeat(32)+'?r=use1',deadline:null,booth_fee:85,application_fee:null,deposit:null,categories:['Handmade Crafts'],availability:'open',eligibility:'Bring your own 10 x 10 tent, table and equipment. Product approval and category capacity remain subject to organizer selection.',fee_notes:'Standard vendor fee is $85 for one outdoor 10 x 10 tent. Fees are non-refundable and due within three days of approval.',research_notes:'Current official calendar year and exact venue date were corroborated with the public WorkForm questions, category choices and welcome-page fee.'};
 const result={policy:'independent-market-applications-v1',decision:'publish',candidate:c,checked_at:now,source_hash:'a'.repeat(64),form_hash:'b'.repeat(64),hub_hash:'c'.repeat(64),category_evidence:{categories:{}},evidence:'The current official organizer calendar independently supplies the year and venue date. The reviewed application hub links a matching, complete, public WorkForm with current fee and vendor questions.'};
 async function value(sql,args=[]){return (await db.query(sql,args)).rows[0]?.result;}
 const publish=(r=result)=>value('select public.btb_research_publish_independent_market($1) as result',[r]);
 await t.test('a public RPC still requires the dedicated worker secret',async()=>{
  await assert.rejects(publish(),/authorization required/);
  await db.query("select set_config('request.headers',$1,false)",[JSON.stringify({'x-btb-research-secret':'f'.repeat(64)})]);
 });
 await t.test('reviewed profile is created separately and cannot imply an open vendor application',async()=>{
  const receipt={policy:'reviewed-market-catalog-v1',catalog_key:'grl-waverly',source_url:'https://grlmarket.com/',source_hash:'a'.repeat(64),checked_at:now,evidence:'The reviewed official source currently confirms the market identity, Triangle location, and vendor-market activity. This receipt creates a directory profile only and establishes no current vendor availability.'};
  const profile=await value('select public.btb_research_publish_market_catalog($1) as result',[receipt]);assert.equal(profile.action,'created');
  assert.equal((await db.query('select count(*)::int as n from public.vendor_opportunities where application_url=$1',[c.application_url])).rows[0].n,0);
 });
 await t.test('fresh venue/date/application receipts publish once and refresh fees on a later check',async()=>{
  const first=await publish();assert.equal(first.action,'publish');assert.equal((await publish()).id,first.id);
  await publish({...result,candidate:{...c,booth_fee:90}});
  const rows=(await db.query('select booth_fee,availability from public.vendor_opportunities where id=$1',[first.id])).rows;
  assert.equal(Number(rows[0].booth_fee),90);assert.equal(rows[0].availability,'open');
  assert.equal((await db.query('select count(*)::int as n from public.vendor_opportunities where application_url=$1',[c.application_url])).rows[0].n,1);
 });
 await t.test('missing hashes, stale receipts, wrong identity, untrusted forms and past dates cannot publish',async()=>{
  for(const r of [{...result,form_hash:''},{...result,checked_at:'2000-01-01T00:00:00Z'},
   {...result,candidate:{...c,source_url:'https://unreviewed.example/'}},{...result,candidate:{...c,application_url:'https://forms.monday.com/admin'}},
   {...result,candidate:{...c,market_name:'Different market'}},{...result,candidate:{...c,starts_on:'2025-12-13',ends_on:'2025-12-13'}},
   {...result,candidate:{...c,booth_fee:null}},{...result,candidate:{...c,application_fee:0}}])await assert.rejects(publish(r),/not verified|Invalid date/);
 });
 await t.test('manual holds and hidden markets are preserved',async()=>{
  await db.query('update public.vendor_opportunities set automation_hold=true where application_url=$1',[c.application_url]);
  assert.equal((await publish()).action,'skipped');
  await db.query('update public.vendor_opportunities set automation_hold=false where application_url=$1',[c.application_url]);
  await db.query('update public.markets set is_hidden=true where slug=$1',[c.market_slug]);assert.equal((await publish()).action,'skipped');
  await db.query('update public.markets set is_hidden=false where slug=$1',[c.market_slug]);
 });
 await t.test('explicit closure updates an existing listing while retaining fees and never creates a new opening',async()=>{
  const closed={...result,candidate:{...c,availability:'closed',booth_fee:null,categories:[]}};
  await publish(closed);
  const row=(await db.query('select booth_fee,availability,categories from public.vendor_opportunities where application_url=$1',[c.application_url])).rows[0];
  assert.equal(row.availability,'closed');assert.equal(Number(row.booth_fee),90);assert.deepEqual(row.categories,['Handmade Crafts']);
  assert.equal((await publish({...closed,candidate:{...closed.candidate,application_url:'https://forms.monday.com/forms/'+'d'.repeat(32)}})).action,'skipped');
 });
 await t.test('reviewed .co venues synchronize without weakening source identity checks',async()=>{
  const sources=[{source_url:'https://www.unhingedcoffee.co/',organizer:'Unhinged Coffee & Co.',city:'Knightdale'}];
  const synced=await value('select public.btb_research_record_discovery_leads_v2($1,$2) as result',[[],sources]);assert.equal(synced.approved_sources,1);
  await assert.rejects(value('select public.btb_research_record_discovery_leads_v2($1,$2)',[[],[{...sources[0],source_url:'https://127.0.0.1/private'}]]),/Invalid code-defined official source/);
 });
 await db.close();
});

/** Isolated publication checks. Synthetic prices only; no production writes. */
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';

test('application price refresh keeps holds, source anchors and worker authorization',async t=>{
 const db=new PGlite();
 await db.exec(await readFile(new URL('./fixtures/membership.sql',import.meta.url),'utf8'));
 await db.exec(`
  ALTER TABLE public.markets ADD COLUMN is_sample boolean DEFAULT false;
  ALTER TABLE public.vendor_opportunities ADD COLUMN automation_hold boolean DEFAULT false;
  ALTER TABLE public.vendor_opportunities ADD COLUMN verification_policy text DEFAULT 'manual';
  CREATE TABLE public.btb_research_settings(id boolean PRIMARY KEY,enabled boolean);
  INSERT INTO public.btb_research_settings VALUES(true,true);
  CREATE TABLE public.btb_research_audit(opportunity_id uuid,action text,reason text,evidence jsonb);
 `);
 const base=await readFile(new URL('./opportunity-research/sql/published_field_evidence.sql',import.meta.url),'utf8');
 await db.exec(base.split('-- Extend the existing public projection')[0]);
 const root=new URL('../supabase/migrations/',import.meta.url);
 const migration=(await readdir(root)).find(x=>x.endsWith('_application_hub_price_refresh.sql'));
 try{await db.exec(await readFile(new URL(migration,root),'utf8'));}catch(error){delete error.query;throw error;}
 const market='00000000-0000-0000-0000-000000000001',otherMarket='00000000-0000-0000-0000-000000000002';
 await db.query('insert into public.markets(id,slug) values($1,$2),($3,$4)',[market,'brewgaloo',otherMarket,'different-market']);
 const opp=(await db.query(`insert into public.vendor_opportunities(market_id,title,organizer,starts_on,ends_on,application_url,source_url,automation_hold,verification_policy,booth_fee,application_fee,deposit,deadline)
 values($1,'Brewgaloo 2027 — Vendor Applications','Shop Local Raleigh','2027-04-23','2027-04-24','https://shoplocalraleigh.org/brewgaloo/brewgaloo-applications/','https://shoplocalraleigh.org/brewgaloo/',true,'manual-official-application-hub-v1',null,null,null,null) returning id`,[market])).rows[0].id;
 const other=(await db.query(`insert into public.vendor_opportunities(market_id,title,automation_hold) values($1,'Different held market',true) returning id`,[otherMarket])).rows[0].id;
 const now=(await db.query('select now()::text as stamp')).rows[0].stamp;
 const proof={source_url:'https://docs.google.com/forms/d/e/'+'a'.repeat(30)+'/viewform',source_hash:'b'.repeat(64),excerpt:'Synthetic retail vendor booth fee: $350 per event.'};
 const result={policy:'published-field-evidence-v1',id:opp,source_url:'https://shoplocalraleigh.org/brewgaloo/',application_url:'https://shoplocalraleigh.org/brewgaloo/brewgaloo-applications/',starts_on:'2027-04-23',ends_on:'2027-04-24',checked_at:now,source_hash:'a'.repeat(64),anchor:{booth_fee:null,application_fee:null,deposit:null,deadline:null},facts:{
  pricing:{status:'options',summary:'Published retail vendor fees from the exact linked application.',...proof},
  pricing_options:[{label:'Retail vendor booth fee',amount:350,unit:'event',kind:'booth',conditions:'Synthetic one-event price; payment due after acceptance.',applicable:true,...proof}],
  application_fee:{status:'access_limited',summary:'A separate application charge remains unverified.',...proof},
  deadline:{status:'rolling',summary:'The organizer accepts applications year-round.',...proof},
  categories:[],application_access:'partial'
 }};
 const call=async(r=result)=>(await db.query('select public.btb_research_record_facts($1) as result',[r])).rows[0].result;
 await t.test('the public RPC requires the existing dedicated secret',async()=>{
  await assert.rejects(call(),/authorization required/);
  await db.query("select set_config('request.headers',$1,false)",[JSON.stringify({'x-btb-research-secret':'f'.repeat(64)})]);
 });
 await t.test('only this reviewed held hub enters the field-audit queue',async()=>{
  const context=(await db.query('select public.btb_research_fact_context() as result')).rows[0].result;
  assert.ok(context.items.some(x=>x.id===opp));assert.ok(!context.items.some(x=>x.id===other));
 });
 await t.test('price evidence becomes visible while the parent listing hold and availability stay intact',async()=>{
  assert.equal((await call()).action,'updated');
  const facts=(await db.query('select btb_private.public_opportunity_facts($1) as result',[opp])).rows[0].result;
  assert.equal(facts.pricing_options[0].amount,350);
  const parent=(await db.query('select automation_hold,availability,publication,booth_fee from public.vendor_opportunities where id=$1',[opp])).rows[0];
  assert.equal(parent.automation_hold,true);assert.equal(parent.availability,'open');assert.equal(parent.publication,'published');assert.equal(parent.booth_fee,null);
 });
 await t.test('other held listings cannot receive an override',async()=>{
  assert.equal((await call({...result,id:other})).action,'skipped');
 });
 await t.test('a changed source, event date or price anchor invalidates the receipt',async()=>{
  for(const change of [{application_url:'https://example.org/other'},{starts_on:'2027-04-24'},{anchor:{...result.anchor,booth_fee:20}}]) assert.equal((await call({...result,...change})).action,'skipped');
 });
 await t.test('missing prices on a later access failure retain the last verified receipt',async()=>{
  assert.equal((await call({...result,facts:{...result.facts,pricing_options:[]}})).action,'retained');
  assert.equal((await db.query('select receipt from btb_private.opportunity_field_facts where opportunity_id=$1',[opp])).rows[0].receipt.facts.pricing_options[0].amount,350);
 });
 await t.test('hidden markets remain protected',async()=>{
  await db.query('update public.markets set is_hidden=true where id=$1',[market]);
  assert.equal((await call()).action,'skipped');
  await db.query('update public.markets set is_hidden=false where id=$1',[market]);
 });
 await t.test('private helpers remain inaccessible to public roles',async()=>{
  const allowed=(await db.query("select has_function_privilege('anon','btb_private.opportunity_facts_refresh_allowed(public.vendor_opportunities)','execute') as allowed")).rows[0].allowed;
  assert.equal(allowed,false);
 });
 await db.close();
});

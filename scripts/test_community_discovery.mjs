import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';

test('community calls preserve evidence, membership, expiry and moderation boundaries',async t=>{
 const db=new PGlite();
 await db.exec(await readFile(new URL('./fixtures/membership.sql',import.meta.url),'utf8'));
 await db.exec(`
 ALTER TABLE public.markets ALTER COLUMN id SET DEFAULT gen_random_uuid();
 ALTER TABLE public.markets ADD COLUMN name text,ADD COLUMN city text,ADD COLUMN state text,ADD COLUMN organizer text,ADD COLUMN description text,ADD COLUMN website_url text,ADD COLUMN is_sample boolean DEFAULT false;
 ALTER TABLE public.vendor_opportunities ADD CONSTRAINT vendor_opportunities_availability_check CHECK(availability IN ('open','limited','waitlist','closed','needs_recheck'));
 ALTER TABLE public.vendor_opportunities ADD COLUMN automation_hold boolean DEFAULT false,ADD COLUMN verification_policy text,ADD COLUMN last_checked_at timestamptz,ADD COLUMN research_notes text,ADD COLUMN review_reason text,ADD COLUMN updated_at timestamptz DEFAULT now();
 CREATE TABLE public.btb_research_settings(id boolean PRIMARY KEY,enabled boolean);INSERT INTO public.btb_research_settings VALUES(true,true);
 CREATE TABLE public.market_occurrences(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),market_id uuid,starts_on date,ends_on date,title text,UNIQUE(market_id,starts_on,ends_on));
 CREATE TABLE public.btb_research_audit(opportunity_id uuid,action text,reason text,evidence jsonb);
 `);
 const dir=new URL('../supabase/migrations/',import.meta.url);
 const file=(await readdir(dir)).find(p=>p.endsWith('_community_vendor_discovery.sql'));
 try{await db.exec(await readFile(new URL(file,dir),'utf8'));}catch(error){delete error.query;throw error;}
 const intakeUpdate=(await readdir(dir)).find(p=>p.endsWith('_community_verified_intake.sql'));
 await db.exec(await readFile(new URL(intakeUpdate,dir),'utf8'));
 const hintUpdate=(await readdir(dir)).find(p=>p.endsWith('_reconcile_community_source_hints.sql'));
 await db.exec(await readFile(new URL(hintUpdate,dir),'utf8'));
 const sources=JSON.parse(await readFile(new URL('./opportunity-research/community_sources.json',import.meta.url),'utf8'));
 const now=(await db.query('select now()::text as v')).rows[0].v;
 const day=(await db.query("select (current_date+12)::text as v")).rows[0].v;
 const opening=(await db.query("select (current_date+2)::text as v")).rows[0].v;
 const event='https://www.songbird.bar/calendar/holiday-market';
 const c={market_slug:'east-end-the-market-at-songbird',market_name:'East End: THE Market at Songbird',organizer:'Songbird',city:'Raleigh',state:'NC',title:'Songbird Holiday Market',venue:'1020 E Whitaker Mill Rd',starts_on:day,ends_on:day,schedule_type:'dated_event',source_url:event,application_url:event,application_method:'email',application_contact:'vendors@songbird.bar',deadline:null,booth_fee:null,application_fee:null,deposit:null,categories:[],availability:'open',fee_notes:'Fees are not published.',eligibility:'Organizer selection is required.',research_notes:'Exact event, source and vendor email invitation were independently read.'};
 const text='Songbird Holiday Market, Raleigh, at 1020 E Whitaker Mill Rd. Vendor applications accepted by email. Email vendors@songbird.bar to apply. Organizer approval is required.';
 const receipt={url:event,access:'public_read',text,checked_at:now,sha256:'a'.repeat(64)};
 const result={policy:'reviewed-community-call-v1',decision:'publish',source_key:'songbird-raleigh',candidate:c,checked_at:now,receipts:[{...receipt,role:'event'},{...receipt,role:'intake'}],evidence:text};
 const query=async(sql,args=[]) => (await db.query(sql,args)).rows[0]?.result;
 const publish=r=>query('select public.btb_research_publish_community_call($1) as result',[r??result]);
 await t.test('anonymous callers cannot use the worker bridge',async()=>{
  await assert.rejects(publish(),/authorization required/);
  await db.query("select set_config('request.headers',$1,false)",[JSON.stringify({'x-btb-research-secret':'f'.repeat(64)})]);
  assert.equal((await query('select public.btb_research_community_sync($1) as result',[sources])).sources,sources.length);
  assert.equal((await query('select public.btb_research_community_sync($1) as result',[sources])).sources,sources.length);
 });
 let id;
 await t.test('verified email calls publish once with unknown fees preserved',async()=>{
  const first=await publish();id=first.id;assert.equal(first.action,'publish');assert.equal((await publish()).id,id);
  const row=(await db.query('select application_method,application_contact,booth_fee from public.vendor_opportunities where id=$1',[id])).rows[0];
  assert.equal(row.application_method,'email');assert.equal(row.application_contact,'vendors@songbird.bar');assert.equal(row.booth_fee,null);
 });
 await t.test('membership redaction hides application contacts but retains opening dates',async()=>{
  await db.query("select set_config('request.jwt.claims','{}',false)");
  const anonymous=await query('select public.btb_public_opportunities() as result');
  const preview=anonymous.items.find(x=>x.id===id);assert.equal(preview.access,'preview');assert.equal(preview.application_url,'');assert.equal(preview.application_contact,undefined);
  await db.query("select set_config('request.jwt.claims',$1,false)",[JSON.stringify({role:'authenticated',sub:'11111111-1111-4111-8111-111111111111'})]);
  const member=await query('select public.btb_public_opportunities() as result');assert.equal(member.items.find(x=>x.id===id).application_contact,'vendors@songbird.bar');
 });
 await t.test('unreviewed, stale and malformed receipts cannot publish',async()=>{
  for(const r of [{...result,source_key:'unreviewed'}, {...result,checked_at:'2000-01-01T00:00:00Z'},
   {...result,candidate:{...c,source_url:'https://unreviewed.example/'}},
   {...result,candidate:{...c,application_contact:'victim@example.com?bcc=elsewhere@example.com'}},
   {...result,receipts:[{...receipt,role:'event',checked_at:null},{...receipt,role:'intake'}]}])
   await assert.rejects(publish(r),/Unverified|Invalid|Stale|reviewed/);
 });
 await t.test('a pending lead resolves through its reviewed venue and reconciles in place',async()=>{
  const staged={...c,reviewed_source_key:'songbird-raleigh'};
  await db.query('insert into btb_private.community_discovery_inbox(target_url,title,proposal,receipts) values($1,$2,$3,$4)',[event,c.title,staged,JSON.stringify(result.receipts)]);
  await query('select public.btb_research_community_hints($1) as result',[JSON.stringify([{source_key:'songbird-raleigh',target_url:event,title:c.title,notes:'A calendar hint.'}])]);
  const pending=(await query('select public.btb_research_community_context() as result')).leads.find(x=>x.target_url===event);
  assert.equal(pending.source_key,'songbird-raleigh');
  await publish();
  const rows=(await db.query('select source_key,state,opportunity_id from btb_private.community_discovery_inbox where target_url=$1',[event])).rows;
  assert.deepEqual(rows,[{source_key:'songbird-raleigh',state:'published',opportunity_id:id}]);
 });
 await t.test('waitlist status requires explicit proof and stays waitlist in the public feed',async()=>{
  const wait={...result,candidate:{...c,availability:'waitlist'}};
  await assert.rejects(publish(wait),/Waitlist-only/);
  const intake={...receipt,role:'intake',text:text+' Waiting list only.'};
  assert.equal((await publish({...wait,receipts:[result.receipts[0],intake]})).id,id);
  const row=(await query('select public.btb_public_opportunities() as result')).items.find(x=>x.id===id);
  assert.equal(row.effective_status,'waitlist');
 });
 await t.test('an older empty hint inherits its exact published occurrence',async()=>{
  const target=event+'?calendar';
  await db.query("insert into btb_private.community_discovery_inbox(target_url,title,proposal,receipts,state,opportunity_id) values($1,$2,$3,$4,'published',$5)",[target,c.title,{...c,reviewed_source_key:'songbird-raleigh'},JSON.stringify(result.receipts),id]);
  await db.query("insert into btb_private.community_discovery_inbox(source_key,target_url,title) values('songbird-raleigh',$1,$2)",[target,c.title]);
  await db.exec(await readFile(new URL(hintUpdate,dir),'utf8'));
  const canonical=(await db.query("select state,opportunity_id from btb_private.community_discovery_inbox where source_key='songbird-raleigh' and target_url=$1",[target])).rows[0];
  assert.deepEqual(canonical,{state:'published',opportunity_id:id});
 });
 await t.test('opening day needs new verification instead of automatically claiming open',async()=>{
  await publish({...result,candidate:{...c,availability:'announced',opens_on:opening}});
  const before=await query('select public.btb_public_opportunities() as result');assert.equal(before.items.find(x=>x.id===id).effective_status,'announced');
  await db.query('update public.vendor_opportunities set opens_on=current_date where id=$1',[id]);
  const due=await query('select public.btb_public_opportunities() as result');assert.equal(due.items.find(x=>x.id===id).effective_status,'needs_recheck');
 });
 await t.test('conditional booth options retain amounts, conditions and source privacy',async()=>{
  const options=[{label:'Resident single booth',amount:25,kind:'booth',unit:'event',conditions:'Residents only.',applicable:true,source_url:event},{label:'Nonresident single booth',amount:40,kind:'booth',unit:'event',conditions:'Nonresidents only.',applicable:true,source_url:event}];
  await publish({...result,receipts:[...result.receipts,{...receipt,role:'fee',text:'Booth prices: resident single booth $25; nonresident single booth $40.'}],candidate:{...c,pricing_options:options}});
  const full=await query('select public.btb_public_opportunities() as result');
  assert.deepEqual(full.items.find(x=>x.id===id).field_facts.pricing_options,options);
  await db.query("select set_config('request.jwt.claims','{}',false)");
  const redacted=await query('select public.btb_public_opportunities() as result');
  assert.equal(redacted.items.find(x=>x.id===id).field_facts.pricing_options[0].source_url,'');
 });
 await t.test('holds and hidden profiles are not overwritten',async()=>{
  await db.query('update public.vendor_opportunities set automation_hold=true where id=$1',[id]);assert.equal((await publish()).action,'skipped');
  await db.query('update public.vendor_opportunities set automation_hold=false where id=$1',[id]);
  await db.query('update public.markets set is_hidden=true where slug=$1',[c.market_slug]);assert.equal((await publish()).action,'skipped');
  await db.query('update public.markets set is_hidden=false where slug=$1',[c.market_slug]);
 });
 await t.test('closure cannot create a new opportunity',async()=>{
  const next=(await db.query('select (current_date+15)::text as v')).rows[0].v;
  assert.equal((await publish({...result,candidate:{...c,starts_on:next,ends_on:next,availability:'closed'}})).action,'skipped');
 });
 await db.close();
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';
import {safeReturnPath,accountLink} from '../src/lib/accountLinks.ts';
import {handleOpportunityAlerts,buildOpportunityDigest} from '../supabase/functions/opportunity-alerts/index.ts';

const user='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222';
const first='aaaaaaaa-0001-4000-8000-000000000001',second='aaaaaaaa-0002-4000-8000-000000000002';
const durham='bbbbbbbb-0003-4000-8000-000000000003';
const db=new PGlite();
const ready=(async()=>{
  await db.exec(await readFile(new URL('./fixtures/membership.sql',import.meta.url),'utf8'));
  try{await db.exec(await readFile(new URL('../supabase/migrations/20261122232113_opportunity_membership_and_alerts.sql',import.meta.url),'utf8'));}
  catch(error){delete error.query;throw error;}
})();
async function value(sql,params=[]){return (await db.query(sql,params)).rows[0]?.result;}
async function role(name,id,run,extra={}){
  await db.exec(`set role ${name}`);
  await db.query("select set_config('request.jwt.claims',$1,false)",[JSON.stringify({role:name,...(id?{sub:id}:{}),...extra})]);
  try{return await run();}finally{await db.exec('reset role');await db.query("select set_config('request.jwt.claims','{}',false)");}
}
async function save(id,options={}){
  return role('authenticated',id,()=>value('select public.btb_save_opportunity_alerts($1,$2,$3,$4,$5) as result',
    [options.new??true,options.reminders??false,options.cities??[],options.categories??[],options.unknown??false]));
}
async function service(run){return role('service_role',null,run);}

test('membership and opt-in database contracts',async t=>{
  await ready;
  await t.test('guests receive real summaries and exactly one global full example',async()=>{
    const data=await role('anon',null,()=>value('select public.btb_public_opportunities() as result'));
    assert.equal(data.is_member,false);assert.equal(data.items.length,3);
    assert.equal(data.items.filter(i=>i.access==='example').length,1);
    assert.equal(data.example_id,first);
    const preview=data.items.find(i=>i.id===second);
    assert.equal(preview.booth_fee,25);assert.equal(preview.application_url,'');assert.equal(preview.deadline,null);
    assert.equal(preview.source_url,'');assert.equal(preview.eligibility,'');
    assert.equal(JSON.stringify(preview).includes('Private full details'),false);
    const filtered=await role('anon',null,()=>value("select public.btb_public_opportunities('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',0) as result"));
    assert.equal(filtered.example_id,first);assert.equal(filtered.items[0].access,'preview');
    await assert.rejects(role('anon',null,()=>value('select btb_private.full_opportunities() as result')),/permission denied/);
    await assert.rejects(role('anon',null,()=>db.query('select * from public.vendor_opportunities')),/permission denied/);
  });
  await t.test('confirmed members have full access without a vendor profile; unconfirmed/anonymous users do not',async()=>{
    const data=await role('authenticated',user,()=>value('select public.btb_public_opportunities() as result'));
    assert.equal(data.is_member,true);assert(data.items.every(i=>i.access==='full'&&i.application_url));
    for(const [id,extra] of [['33333333-3333-4333-8333-333333333333',{}],[user,{is_anonymous:true}]]){
      const list=await role('authenticated',id,()=>value('select public.btb_public_opportunities() as result'),extra);
      assert.equal(list.is_member,false);
    }
  });
  await t.test('no subscription is created by reading; settings are private and cannot enqueue delivery',async()=>{
    assert.equal(await role('authenticated',user,()=>value('select public.btb_my_opportunity_alerts() as result')),null);
    await save(user,{new:false});
    await save(other,{new:false});
    assert.deepEqual(await service(()=>value('select public.btb_due_opportunity_alerts() as result')),[]);
    const rows=await role('authenticated',user,()=>db.query('select user_id,new_matches from public.opportunity_alert_preferences'));
    assert.deepEqual(rows.rows,[{user_id:user,new_matches:false}]);
    await assert.rejects(role('authenticated',user,()=>db.query('select unsubscribe_token from public.opportunity_alert_preferences')),/permission denied/);
    await assert.rejects(role('authenticated',user,()=>db.query("update public.opportunity_alert_preferences set last_sent_at=now()")),/permission denied/);
    await assert.rejects(role('authenticated',user,()=>value('select public.btb_due_opportunity_alerts() as result')),/permission denied/);
    await assert.rejects(role('anon',null,()=>value('select public.btb_my_opportunity_alerts() as result')),/permission denied/);
    await assert.rejects(save(user,{categories:['Made up category']}),/alert_categories_valid/);
  });
  await t.test('explicit opt-in respects location, category evidence, and newly published baseline',async()=>{
    await save(user,{cities:['Raleigh'],categories:['Handmade Crafts']});
    assert.equal(await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[user])),null);
    await db.query("update public.opportunity_alert_preferences set requested_at=now()-interval '1 day' where user_id=$1",[user]);
    await db.query("update public.vendor_opportunities set category_evidence=jsonb_build_object('Handmade Crafts',jsonb_build_object('status','excluded','checked_at',now(),'source_url','https://example.org/apply','note','Excluded')) where id=$1",[second]);
    const job=await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[user]));
    assert.deepEqual(job.entries.map(e=>e.item.id),[first]);
    assert.equal(await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[user])),null);
    await service(()=>value("select public.btb_finish_opportunity_alert($1,$2,'failed') as result",[job.id,job.claim_token]));
    const retry=await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[user]));
    assert.equal(retry.id,job.id);assert.notEqual(retry.claim_token,job.claim_token);
    const payload={to:['fixture@example.org'],text:'A frozen test payload'};
    assert.deepEqual(await service(()=>value('select public.btb_prepare_opportunity_alert($1,$2,$3) as result',[retry.id,retry.claim_token,payload])),payload);
    assert.deepEqual(await service(()=>value('select public.btb_prepare_opportunity_alert($1,$2,$3) as result',[retry.id,retry.claim_token,{text:'Different'}])),payload);
    await service(()=>value("select public.btb_finish_opportunity_alert($1,$2,'sent','fixture-provider-id') as result",[retry.id,retry.claim_token]));
    assert.equal(await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[user])),null);
    assert.equal((await db.query('select count(*)::integer as n from btb_private.opportunity_alert_receipts where user_id=$1',[user])).rows[0].n,1);
  });
  await t.test('unknown categories require opt-in; explicit exclusions and stale sources do not count',async()=>{
    await save(other,{cities:['Durham'],categories:['Food Trucks'],unknown:false});
    await db.query("update public.opportunity_alert_preferences set requested_at=now()-interval '1 day' where user_id=$1",[other]);
    assert.equal(await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[other])),null);
    await save(other,{cities:['Durham'],categories:['Food Trucks'],unknown:true});
    await db.query("update public.opportunity_alert_preferences set requested_at=now()-interval '1 day' where user_id=$1",[other]);
    await db.query("update public.vendor_opportunities set verified_at=now()-interval '8 days' where id=$1",[durham]);
    assert.equal(await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[other])),null);
    await db.query('update public.vendor_opportunities set verified_at=now() where id=$1',[durham]);
    const job=await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[other]));
    assert.equal(job.entries[0].item.id,durham);
    const token=(await db.query('select unsubscribe_token from public.opportunity_alert_preferences where user_id=$1',[other])).rows[0].unsubscribe_token;
    await role('anon',null,()=>value('select public.btb_unsubscribe_opportunity_alerts($1) as result',[token]));
    assert.equal(await service(()=>value('select public.btb_prepare_opportunity_alert($1,$2,$3) as result',[job.id,job.claim_token,{text:'Should not send'}])),null);
    assert.equal((await role('authenticated',other,()=>value('select public.btb_my_opportunity_alerts() as result'))).new_matches,false);
    await db.query('delete from btb_private.opportunity_alert_deliveries where user_id=$1',[other]);
  });
  await t.test('saved reminders use confirmed future cutoffs, not series or unconfirmed deadlines',async()=>{
    await save(other,{new:false,reminders:true});
    await db.query('insert into public.saved_opportunities values($1,$2)',[other,first]);
    await db.query("update public.vendor_opportunities set fee_notes='Series application deadline; confirm availability.' where id=$1",[first]);
    assert.equal(await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[other])),null);
    await db.query("update public.vendor_opportunities set fee_notes='',fixture_coverage='{\"deadline\":{\"status\":\"unconfirmed\"}}' where id=$1",[first]);
    assert.equal(await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[other])),null);
    await db.query("update public.vendor_opportunities set fixture_coverage='{}' where id=$1",[first]);
    const job=await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[other]));
    assert.equal(job.entries.length,1);assert.equal(job.entries[0].kind,'deadline');
    // A retry created yesterday still counts against today's actual send cap.
    await db.query("update btb_private.opportunity_alert_deliveries set delivery_day=current_date-1 where id=$1",[job.id]);
    await service(()=>value("select public.btb_finish_opportunity_alert($1,$2,'sent','fixture-reminder') as result",[job.id,job.claim_token]));
    assert.equal(await service(()=>value('select public.btb_claim_opportunity_alert($1) as result',[other])),null);
    assert.equal((await service(()=>value('select public.btb_due_opportunity_alerts() as result'))).includes(other),false);
  });
  await t.test('pagination never gives a new public example for a different page',async()=>{
    await db.exec("insert into public.vendor_opportunities(title,market_id,starts_on,ends_on) select 'Later fixture '||n,'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',current_date+30,current_date+30 from generate_series(1,103) n");
    const page=await role('anon',null,()=>value('select public.btb_public_opportunities(null,100) as result'));
    assert.equal(page.example_id,first);assert(page.items.every(i=>i.access==='preview'));
    const all=await service(()=>db.query('select count(*)::integer as n from btb_private.alert_opportunity_items()'));
    assert.equal(all.rows[0].n,106);
  });
  await db.close();
});

test('account redirects preserve relevant destinations and reject external/auth/admin paths',()=>{
  assert.equal(safeReturnPath('/opportunities?city=Raleigh&details=123#123'),'/opportunities?city=Raleigh&details=123#123');
  assert.equal(safeReturnPath('/login#opportunity-alerts'),'/login#opportunity-alerts');
  for(const input of ['https://evil.example','//evil.example','/\\evil.example','/admin','/auth/callback','/login?next=https://evil.example','/%2f%2fevil.example','/opportunities\n'])assert.equal(safeReturnPath(input),null);
  assert.equal(new URL(accountLink('/verify'),'https://example.org').searchParams.get('next'),'/verify');
});

test('digest markup escapes market content and includes working unsubscribe headers',()=>{
  const digest=buildOpportunityDigest([{kind:'new',item:{id:first,title:'<script>bad</script>',city:'Raleigh',state:'NC',starts_on:'2026-12-10',ends_on:'2026-12-10',effective_status:'limited'},fingerprint:'x'}],'https://www.behindtheboothhq.com',user);
  assert(!digest.html.includes('<script>'));assert(digest.html.includes('&lt;script&gt;'));
  assert(digest.text.includes('Limited options'));assert(digest.text.includes('Unsubscribe:'));
  assert.equal(digest.headers['List-Unsubscribe-Post'],'List-Unsubscribe=One-Click');
});

test('worker authenticates before delivery; dry runs never claim jobs or call the email provider',async()=>{
  const config={SUPABASE_URL:'https://fixture.supabase.co',SUPABASE_ANON_KEY:'fixture-public',SUPABASE_SERVICE_ROLE_KEY:'fixture-service',RESEND_API_KEY:'fixture-provider',MEMBER_NOTIFICATION_FROM:'Behind the Booth <test@example.org>'};
  const calls=[];
  const mock=async(url,init)=>{calls.push({url,init});return Response.json(url.endsWith('btb_due_opportunity_alerts')?[user]:null);};
  const unauthorized=await handleOpportunityAlerts(new Request('https://fixture/worker',{method:'POST'}),n=>config[n],mock);
  assert.equal(unauthorized.status,401);assert.equal(calls.length,0);
  const request=new Request('https://fixture/worker',{method:'POST',headers:{'x-btb-research-secret':'a'.repeat(64),'Content-Type':'application/json'},body:JSON.stringify({dry_run:true})});
  const result=await handleOpportunityAlerts(request,n=>config[n],mock);
  assert.equal(result.status,200);assert.deepEqual(await result.json(),{dry_run:true,configured:true,due_members:1});
  assert.equal(calls.length,2);assert(calls.every(c=>!c.url.includes('claim')&&!c.url.includes('resend.com')));
});

function deliveryScenario({consent=true,status='open',failFirst=false}={}){
  const item={id:first,title:'Local fixture market',city:'Raleigh',state:'NC',starts_on:'2026-12-10',ends_on:'2026-12-10',deadline:null,effective_status:status};
  const job={id:second,user_id:user,claim_token:other,entries:[{kind:'new',item,fingerprint:'fixture-new'}],payload:null,unsubscribe_token:user};
  let finished=false;
  const sends=[],finishes=[],requests=[];
  const config={SUPABASE_URL:'https://fixture.supabase.co',SUPABASE_ANON_KEY:'fixture-public',SUPABASE_SERVICE_ROLE_KEY:'fixture-service',RESEND_API_KEY:'fixture-provider',MEMBER_NOTIFICATION_FROM:'Behind the Booth <test@example.org>'};
  const mock=async(url,init)=>{
    requests.push(url);
    const input=init.body?JSON.parse(init.body):{};
    if(url.endsWith('btb_research_authorize'))return new Response(null,{status:204});
    if(url.endsWith('btb_due_opportunity_alerts'))return Response.json([user]);
    if(url.endsWith('btb_claim_opportunity_alert'))return Response.json(finished?null:job);
    if(url.includes('/auth/v1/admin/users/'))return Response.json({email:'trusted-fixture@example.org',email_confirmed_at:'2026-11-01T00:00:00Z'});
    if(url.endsWith('btb_public_opportunities'))return Response.json({items:[item],total:1,is_member:true});
    if(url.endsWith('btb_prepare_opportunity_alert')){
      if(!consent)return Response.json(null);
      job.payload??=input.p_payload;return Response.json(job.payload);
    }
    if(url.endsWith('btb_finish_opportunity_alert')){
      finishes.push(input.p_state);finished=input.p_state!=='failed';return new Response(null,{status:204});
    }
    if(url==='https://api.resend.com/emails'){
      sends.push({key:init.headers['Idempotency-Key'],payload:input});
      if(failFirst&&sends.length===1)throw Error('Simulated uncertain network response');
      return Response.json({id:'fixture-email-id'});
    }
    throw Error('Unexpected request');
  };
  const run=()=>handleOpportunityAlerts(new Request('https://fixture/worker',{method:'POST',headers:{'x-btb-research-secret':'b'.repeat(64),'Content-Type':'application/json'},body:JSON.stringify({dry_run:false})}),n=>config[n],mock);
  return {run,sends,finishes,requests};
}

test('delivery resolves the trusted recipient, sends once, and finishes the claimed job',async()=>{
  const scenario=deliveryScenario();
  assert.equal((await scenario.run()).status,200);
  assert.equal((await scenario.run()).status,200);
  assert.equal(scenario.sends.length,1);
  assert.deepEqual(scenario.sends[0].payload.to,['trusted-fixture@example.org']);
  assert.deepEqual(scenario.finishes,['sent']);
});

test('uncertain delivery retry uses the exact frozen payload and provider idempotency key',async()=>{
  const scenario=deliveryScenario({failFirst:true});
  assert.equal((await scenario.run()).status,502);
  assert.equal((await scenario.run()).status,200);
  assert.equal(scenario.sends.length,2);
  assert.equal(scenario.sends[0].key,scenario.sends[1].key);
  assert.deepEqual(scenario.sends[0].payload,scenario.sends[1].payload);
  assert.deepEqual(scenario.finishes,['failed','sent']);
});

test('revoked consent and a closed opportunity each prevent the provider call',async()=>{
  for(const options of [{consent:false},{status:'closed'}]){
    const scenario=deliveryScenario(options);
    assert.equal((await scenario.run()).status,200);
    assert.equal(scenario.sends.length,0);
    assert.deepEqual(scenario.finishes,['skipped']);
  }
});

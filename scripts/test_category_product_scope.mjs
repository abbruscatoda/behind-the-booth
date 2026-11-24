import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';

const db=new PGlite();
const ready=(async()=>{
  await db.exec('create schema btb_private; create role anon; create role authenticated; create role service_role;');
  await db.exec(await readFile(new URL('../supabase/migrations/20261124021427_category_product_scope.sql',import.meta.url),'utf8'));
})();
after(()=>db.close());
const app='https://example.org/application';
const words=['Baked Goods / Savory Food Items','Prepackaged Items (Honey, Hot Sauce, etc.)'];
const fact={status:'eligible',note:'Only these listed food types are supported; beverage eligibility is unconfirmed.',source_url:app,source_hash:'a'.repeat(64),excerpt:words.join(' · '),source_terms:words};
async function value(sql,args=[]){return (await db.query(sql,args)).rows[0].result;}
function receipt(checked,entry=fact){return {application_url:app,checked_at:checked,categories:{'Food & Beverages':entry}};}

test('the worker validator and public projection preserve exact product words',async()=>{
  await ready;
  const checked=await value('select now()::text as result');
  const result={policy:'artspace-jotform-v4-quality',candidate:{application_url:app,source_url:'https://example.org/event',categories:['Food & Beverages']},category_evidence:receipt(checked)};
  const validated=await value('select btb_private.validate_worker_categories($1,$2) as result',[result,checked]);
  assert.deepEqual(validated.categories['Food & Beverages'].source_terms,words);
  const projected=await value('select btb_private.public_category_evidence($1,$2) as result',[app,validated]);
  assert.deepEqual(projected['Food & Beverages'].source_terms,words);
  assert.equal(projected['Food & Beverages'].status,'eligible');
});
test('invented, malformed and oversized source terms cannot become quotes',async()=>{
  await ready;
  for(const terms of [['Food & Beverages'],['x'.repeat(181)],[],[false],Array(11).fill(words[0])]){
    const checked=await value('select now()::text as result');
    const result={candidate:{application_url:app,source_url:app,categories:['Food & Beverages']},category_evidence:receipt(checked,{...fact,source_terms:terms})};
    assert.deepEqual(await value('select btb_private.category_product_metadata($1) as result',[{...fact,source_terms:terms}]),{});
    await assert.rejects(value('select btb_private.validate_worker_categories($1,$2) as result',[result,checked]),/Product wording/);
  }
});
test('old receipts stay readable without fabricated quotes; application identity and freshness still apply',async()=>{
  await ready;
  const checked=await value('select now()::text as result');
  const legacy={...fact};delete legacy.source_terms;
  const projected=await value('select btb_private.public_category_evidence($1,$2) as result',[app,receipt(checked,legacy)]);
  assert.equal(projected['Food & Beverages'].source_terms,undefined);
  assert.deepEqual(await value('select btb_private.public_category_evidence($1,$2) as result',['https://example.org/different',receipt(checked)]),{});
  const stale=await value("select (now()-interval '8 days')::text as result");
  assert.deepEqual(await value('select btb_private.public_category_evidence($1,$2) as result',[app,receipt(stale)]),{});
});

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';
import { photoDimensions,photoInputError,submitReviewWithPhotos } from '../src/lib/reviewPhotos.ts';

const vendor='11111111-1111-4111-8111-111111111111',pending='22222222-2222-4222-8222-222222222222';
const member='33333333-3333-4333-8333-333333333333',unconfirmed='44444444-4444-4444-8444-444444444444',admin='55555555-5555-4555-8555-555555555555';
const market='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',review='eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee';
const photoId='ffffffff-ffff-4fff-8fff-ffffffffffff',path=`${review}/${photoId}.jpg`;
const draft={market_id:market,attended_on:'2026-01-01',vendor_categories:['Prefer not to disclose'],booth_value:4,foot_traffic:4,organization:4,promotion:4,overall:4,experience:'Useful firsthand account.',would_return:'Yes'};
const attachment={path,width:1200,height:900,caption:'Market layout'};

test('private photo storage, atomic submissions, and moderation',async t=>{
 const db=new PGlite();
 await db.exec(await readFile(new URL('./fixtures/review_photos.sql',import.meta.url),'utf8'));
 await db.exec(await readFile(new URL('../supabase/migrations/20261122201528_required_review_category_choice.sql',import.meta.url),'utf8'));
 try{await db.exec(await readFile(new URL('../supabase/migrations/20261123030432_vendor_review_photos.sql',import.meta.url),'utf8'));}catch(error){delete error.query;throw error;}
 async function role(name,id,fn,extra={}){
  await db.exec(`set role ${name}`);
  await db.query("select set_config('request.jwt.claims',$1,false)",[JSON.stringify({role:name,sub:id,...extra})]);
  try{return await fn();}finally{await db.exec('reset role');await db.query("select set_config('request.jwt.claims','{}',false)");}
 }
 const as=(id,fn,extra)=>role('authenticated',id,fn,extra);
 const value=async(sql,args=[]) => (await db.query(sql,args)).rows[0]?.result;
 const upload=(owner=vendor,name=path)=>as(owner,()=>db.query("insert into storage.objects(bucket_id,name,owner_id,metadata) values('review-photos',$1,$2,'{\"size\":12000,\"mimetype\":\"image/jpeg\"}')",[name,owner]));
 const submit=(id=review,values=draft,photos=[attachment],actor=vendor)=>as(actor,()=>value('select public.btb_submit_vendor_review($1,$2,$3) as result',[id,values,photos]));
 await t.test('only confirmed approved vendors upload; anonymous, pending and unconfirmed users cannot',async()=>{
  await assert.rejects(upload(pending),/row-level security/);
  await assert.rejects(upload(unconfirmed),/row-level security/);
  await assert.rejects(role('anon',null,()=>db.query("insert into storage.objects(bucket_id,name,owner_id) values('review-photos',$1,$2)",[path,vendor])),/permission denied/);
  await assert.rejects(as(vendor,()=>db.query("insert into storage.objects(bucket_id,name,owner_id) values('review-photos',$1,$2)",[path,vendor]),{is_anonymous:true}),/row-level security/);
  await assert.rejects(upload(vendor,'personal-name.jpg'),/row-level security/);
  await assert.rejects(submit(review,draft,[],pending),/approved vendor/);
  await assert.rejects(submit(review,draft,[],unconfirmed),/approved vendor/);
  await upload();
  assert.equal(await as(member,()=>value('select count(*)::int as result from storage.objects')),0);
  assert.equal(await as(vendor,()=>value('select count(*)::int as result from storage.objects')),1);
  await assert.rejects(as(member,()=>value('select btb_private.review_photo_entries($1,true)',[review])),/permission denied/);
 });
 await t.test('missing, stolen, oversized, invalid and duplicate photos never create a partial review',async()=>{
  await assert.rejects(submit(review,draft,[{...attachment,path:`${review}/00000000-0000-4000-8000-000000000000.jpg`}]),/photo is missing/);
  await db.query('update storage.objects set owner_id=$1',[member]);
  await assert.rejects(submit(),/photo is missing/);
  await db.query('update storage.objects set owner_id=$1,metadata=$2',[vendor,{size:4000000,mimetype:'image/jpeg'}]);
  await assert.rejects(submit(),/photo is missing/);
  await db.query('update storage.objects set metadata=$1',[{size:12000,mimetype:'image/svg+xml'}]);
  await assert.rejects(submit(),/photo is missing/);
  await db.query('update storage.objects set metadata=$1',[{size:12000,mimetype:'image/jpeg'}]);
  await assert.rejects(submit(review,draft,Array(5).fill(attachment)),/up to 4/);
  await assert.rejects(submit(review,draft,[{...attachment,width:9000}]),/photo size/);
  await assert.rejects(submit(review,draft,[{...attachment,caption:'x'.repeat(161)}]),/photo size/);
  await assert.rejects(submit(review,draft,[attachment,attachment]),/unique constraint/);
  await assert.rejects(submit(review,{...draft,vendor_categories:[]}),/category/i);
  assert.equal(await value('select count(*)::int as result from public.reviews'),0);
  assert.equal(await value('select count(*)::int as result from public.review_photos'),0);
 });
 await t.test('submission is atomic, pending and idempotent; client identities and status are ignored',async()=>{
  assert.equal(await submit(review,{...draft,status:'approved',vendor_id:member}),review);
  assert.equal(await submit(),review);
  assert.equal(await value('select count(*)::int as result from public.reviews'),1);
  const stored=(await db.query('select vendor_id,status from public.reviews')).rows[0];
  assert.deepEqual(stored,{vendor_id:vendor,status:'pending'});
  assert.equal(await as(member,()=>value('select count(*)::int as result from public.review_photos')),0);
  assert.equal(await as(admin,()=>value('select count(*)::int as result from public.review_photos')),1);
  assert.equal(await as(vendor,()=>value('select count(*)::int as result from public.review_photos')),1);
  assert.equal((await as(admin,()=>value("select public.btb_admin_queue_with_attendance('reviews') as result"))).items[0].photos.length,1);
  assert.equal((await as(vendor,()=>value('select public.btb_my_reviews() as result'))).items[0].photos.length,1);
 });
 await t.test('a reviewer cannot append, replace or delete already attached photos',async()=>{
  await assert.rejects(upload(vendor,`${review}/aaaaaaaa-0000-4000-8000-000000000000.jpg`),/row-level security/);
  assert.equal((await as(vendor,()=>db.query("update storage.objects set metadata='{}' returning id"))).rows.length,0);
  assert.equal((await as(vendor,()=>db.query('delete from storage.objects returning id'))).rows.length,0);
  await assert.rejects(as(vendor,()=>db.query("update public.review_photos set caption='changed'")),/permission denied/);
  await submit(review,draft,[]);
  assert.equal(await value('select count(*)::int as result from public.review_photos'),1);
 });
 await t.test('only approved, visible photos in visible markets become member-readable',async()=>{
  await assert.rejects(as(member,()=>value('select public.btb_admin_set_review_photo_visibility($1,true,false)',[photoId])),/Admin access/);
  await db.exec("update public.reviews set status='approved'");
  assert.equal(await as(member,()=>value('select count(*)::int as result from storage.objects')),1);
  assert.equal(await as(member,()=>value('select count(*)::int as result from public.review_photos')),1);
  assert.equal(await as(unconfirmed,()=>value('select count(*)::int as result from storage.objects')),0);
  const entries=await as(member,()=>value('select public.btb_market_reviews_with_attendance($1) as result',[market]));
  assert.equal(entries[0].photos.length,1);assert.equal(entries[0].vendor_id,undefined);
  const id=(await db.query('select id from public.review_photos')).rows[0].id;
  await as(admin,()=>value('select public.btb_admin_set_review_photo_visibility($1,true,false)',[id]));
  assert.equal(await as(member,()=>value('select count(*)::int as result from storage.objects')),0);
  assert.equal((await as(member,()=>value('select public.btb_market_reviews_with_attendance($1) as result',[market])))[0].photos.length,0);
  await assert.rejects(as(admin,()=>value('select public.btb_admin_set_review_photo_visibility($1,false,false)',[id])),/photo changed/);
  await as(admin,()=>value('select public.btb_admin_set_review_photo_visibility($1,false,true)',[id]));
  await db.exec('update public.markets set is_hidden=true');
  assert.equal(await as(member,()=>value('select count(*)::int as result from storage.objects')),0);
  await db.exec("update public.markets set is_hidden=false; update public.reviews set status='rejected'");
  assert.equal(await as(member,()=>value('select count(*)::int as result from storage.objects')),0);
 });
 await t.test('old unfinished files can be cleaned, attached photos remain protected',async()=>{
  const stale=`aaaaaaaa-eeee-4eee-8eee-eeeeeeeeeeee/${photoId}.jpg`;
  await upload(vendor,stale);
  await db.exec("update storage.objects set created_at=now()-interval '2 days'");
  assert.deepEqual(await as(vendor,()=>value('select public.btb_my_unused_review_photos() as result')),[stale]);
  assert.equal((await as(vendor,()=>db.query('delete from storage.objects returning name'))).rows.length,1);
  assert.equal(await value('select count(*)::int as result from storage.objects'),1);
 });
 await t.test('reviews without photos still work and date, visibility and duplicate guards remain active',async()=>{
  const next='eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee2';
  await assert.rejects(submit(next,{...draft,attended_on:'2999-01-01'},[]),/check constraint/);
  await db.exec('update public.markets set is_hidden=true');
  await assert.rejects(submit(next,{...draft,attended_on:'2026-01-02'},[]),/not available/);
  await db.exec('update public.markets set is_hidden=false');
  await assert.rejects(submit(next,draft,[]),/unique constraint/);
  assert.equal(await submit(next,{...draft,attended_on:'2026-01-02'},[]),next);
  assert.equal((await db.query('select status from public.reviews where id=$1',[next])).rows[0].status,'pending');
  assert.equal(await value('select count(*)::int as result from public.review_photos'),1);
 });
 await db.close();
});

test('photo validation and responsive image dimensions',()=>{
 assert.deepEqual(photoDimensions(6000,4000),{width:2048,height:1365});
 assert.deepEqual(photoDimensions(3000,6000),{width:1024,height:2048});
 assert.deepEqual(photoDimensions(800,600),{width:800,height:600});
 assert.throws(()=>photoDimensions(0,900));
 assert(photoInputError({type:'image/svg+xml',size:100}));
 assert(photoInputError({type:'image/jpeg',size:21*1024*1024}));
 assert.equal(photoInputError({type:'image/heic',size:4*1024*1024}),null);
});

test('upload retries reuse files and recover a committed review without duplicate submission',async()=>{
 const calls=[];let committed=false;let lostResponse=true;
 const api={from(){const query={select(){return query;},eq(){return query;},async maybeSingle(){return {data:committed?{id:review}:null,error:null};}};return query;},
 storage:{from(){return {async upload(name){calls.push(['upload',name]);return {error:null};},async remove(){return {error:null};}};}},
 async rpc(name){calls.push([name]);if(name==='btb_my_unused_review_photos')return {data:[],error:null};if(lostResponse){committed=true;lostResponse=false;return {error:{message:'network',code:''}};}throw new Error('Unexpected second submission');}};
 const photo={id:photoId,blob:new Blob(['pixels']),width:1200,height:900,caption:'Layout',preview:'blob:local'};
 const attempt={id:review,uploaded:new Set()};
 await submitReviewWithPhotos(api,vendor,draft,[photo],attempt,()=>{});
 await submitReviewWithPhotos(api,vendor,draft,[photo],attempt,()=>{});
 assert.equal(calls.filter(c=>c[0]==='upload').length,1);
 assert.equal(calls.filter(c=>c[0]==='btb_submit_vendor_review').length,1);
});

test('failed uploads keep the draft retryable and never submit a partial review',async()=>{
 let fail=true,submissions=0;const uploads=[];
 const api={from(){const query={select(){return query;},eq(){return query;},async maybeSingle(){return {data:null,error:null};}};return query;},
 storage:{from(){return {async upload(name){uploads.push(name);return {error:fail?new Error('offline'):null};},async info(){return {error:new Error('missing')};},async remove(){return {error:null};}};}},
 async rpc(name){if(name==='btb_my_unused_review_photos')return {data:[],error:null};submissions++;return {error:null};}};
 const photos=[{id:photoId,blob:new Blob(['pixels']),width:1200,height:900,caption:'',preview:'blob:local'}],attempt={id:review,uploaded:new Set()};
 await assert.rejects(submitReviewWithPhotos(api,vendor,draft,photos,attempt,()=>{}),/couldn't upload/);
 assert.equal(submissions,0);assert.equal(photos.length,1);
 fail=false;await submitReviewWithPhotos(api,vendor,draft,photos,attempt,()=>{});
 assert.equal(submissions,1);assert.equal(new Set(uploads).size,1);
});

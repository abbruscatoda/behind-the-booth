/** Isolated account-report security checks; no real users or production writes. */
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';

const admin='11111111-1111-4111-8111-111111111111';
const vendor='22222222-2222-4222-8222-222222222222';
const unconfirmed='33333333-3333-4333-8333-333333333333';
const older='44444444-4444-4444-8444-444444444444';
test('private admin account reporting',async t=>{
 const db=new PGlite();
 await db.exec(`
  CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS;
  CREATE SCHEMA auth; CREATE SCHEMA btb_private;
  CREATE TABLE auth.users(id uuid PRIMARY KEY,email text,created_at timestamptz,email_confirmed_at timestamptz,
   last_sign_in_at timestamptz,deleted_at timestamptz,banned_until timestamptz,is_anonymous boolean DEFAULT false,
   encrypted_password text DEFAULT 'NEVER-RETURN-PASSWORD',raw_user_meta_data jsonb DEFAULT '{"private":"NEVER-RETURN-METADATA"}');
  CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE AS $$SELECT coalesce(nullif(current_setting('request.jwt.claims',true),'')::jsonb,'{}')$$;
  CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$SELECT (auth.jwt()->>'sub')::uuid$$;
  CREATE TABLE btb_private.admins(user_id uuid PRIMARY KEY REFERENCES auth.users(id));
  CREATE FUNCTION public.btb_is_admin() RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
   SELECT EXISTS(SELECT 1 FROM btb_private.admins a WHERE a.user_id=auth.uid())
  $$;
  CREATE TABLE public.vendor_profiles(user_id uuid PRIMARY KEY REFERENCES auth.users(id),business_name text,business_url text,
   verification_status text,created_at timestamptz DEFAULT now(),verification_notes text DEFAULT 'NEVER-RETURN-VERIFICATION-NOTES');
 `);
 const root=new URL('../supabase/migrations/',import.meta.url);
 const migration=(await readdir(root)).find(x=>x.endsWith('_admin_account_activity.sql'));
 try {await db.exec(await readFile(new URL(migration,root),'utf8'));} catch(error) {delete error.query;throw error;}
 await db.query(`INSERT INTO auth.users(id,email,created_at,email_confirmed_at,last_sign_in_at) VALUES
  ($1,'admin@example.test',now()-interval '10 days',now(),now()),
  ($2,'vendor@example.test',now()-interval '2 days',now(),now()-interval '1 day'),
  ($3,'awaiting@example.test',now()-interval '1 day',null,null),
  ($4,'older@example.test',now()-interval '40 days',now(),null)`,[admin,vendor,unconfirmed,older]);
 await db.query('INSERT INTO btb_private.admins VALUES($1)',[admin]);
 await db.query(`INSERT INTO public.vendor_profiles(user_id,business_name,business_url,verification_status) VALUES
  ($1,'Triangle Handmade','https://example.test/vendor','approved'),
  ($2,'Late Profile Submission',null,'pending')`,[vendor,older]);
 await db.exec(`INSERT INTO auth.users(id,email,created_at,deleted_at,is_anonymous) VALUES
  ('55555555-5555-4555-8555-555555555555','deleted@example.test',now(),now(),false),
  ('66666666-6666-4666-8666-666666666666','anonymous@example.test',now(),null,true),
  ('77777777-7777-4777-8777-777777777777','future@example.test',now()+interval '1 day',null,false)`);
 async function as(role,id,fn,extra={}) {
  await db.exec(`set role ${role}`);
  await db.query("select set_config('request.jwt.claims',$1,false)",[JSON.stringify({role,...(id?{sub:id}:{}),...extra})]);
  try{return await fn();}finally{await db.exec('reset role');await db.query("select set_config('request.jwt.claims','{}',false)");}
 }
 const report=(days=5,search='',offset=0)=>(db.query('select public.btb_admin_accounts($1,$2,$3) as report',[days,search,offset])).then(x=>x.rows[0].report);
 const authorized=(days=5,search='',offset=0)=>as('authenticated',admin,()=>report(days,search,offset));
 await t.test('signed-out and regular members cannot read account emails or counts',async()=>{
  await assert.rejects(as('anon',null,()=>report()),/permission denied/);
  await assert.rejects(as('authenticated',vendor,()=>report()),/Admin access required/);
  await assert.rejects(as('authenticated',null,()=>report()),/Admin access required/);
  await assert.rejects(as('service_role',null,()=>report()),/permission denied/);
 });
 await t.test('user-editable metadata and admin-looking JWT claims do not grant administrator access',async()=>{
  await db.query("update auth.users set raw_user_meta_data='{\"is_admin\":true,\"role\":\"admin\"}' where id=$1",[vendor]);
  await assert.rejects(as('authenticated',vendor,()=>report(),{is_admin:true,user_metadata:{is_admin:true}}),/Admin access required/);
 });
 await t.test('signup counts use account creation dates, include unconfirmed emails, and exclude deleted/anonymous/future users',async()=>{
  const result=await authorized();
  assert.deepEqual(result.summary,{total:4,last_5_days:2,last_30_days:3});
  assert.equal(result.total,2);assert.equal(result.page_size,20);
  assert.deepEqual(result.items.map(x=>x.id),[unconfirmed,vendor]);
  assert.equal(result.items[0].email_confirmed_at,null);assert.equal(result.items[0].vendor_status,'not_applied');
  assert.equal(result.items[1].business_name,'Triangle Handmade');assert.equal(result.items[1].vendor_status,'approved');
  assert.equal((await authorized(null,'late profile')).items[0].id,older);
 });
 await t.test('report fields are explicitly limited and direct auth-table reads remain denied',async()=>{
  const result=await authorized(null);
  assert.equal(result.items.find(x=>x.id===admin).is_admin,true);
  assert.deepEqual(Object.keys(result.items[0]).sort(),['id','email','created_at','email_confirmed_at','last_sign_in_at','business_name','business_url','vendor_status','is_admin'].sort());
  assert.doesNotMatch(JSON.stringify(result),/NEVER-RETURN|encrypted_password|raw_user_meta_data|verification_notes/);
  await assert.rejects(as('authenticated',admin,()=>db.query('select email from auth.users')),/permission denied/);
 });
 await t.test('search is case-insensitive and treats SQL wildcard and injection text literally',async()=>{
  assert.equal((await authorized(null,'TRIANGLE')).items[0].id,vendor);
  assert.equal((await authorized(null,'Awaiting@')).items[0].id,unconfirmed);
  assert.equal((await authorized(null,'%')).total,0);
  assert.equal((await authorized(null,"' OR true --")).total,0);
  assert.equal((await authorized(null,'no match')).items.length,0);
 });
 await t.test('revoked, unconfirmed, banned or deleted administrators cannot fetch the report',async()=>{
  await db.query('delete from btb_private.admins where user_id=$1',[admin]);
  await assert.rejects(authorized(),/Admin access required/);
  await db.query('insert into btb_private.admins values($1)',[admin]);
  for(const change of ["email_confirmed_at=null","banned_until=now()+interval '1 day'","deleted_at=now()","is_anonymous=true"]) {
   await db.query(`update auth.users set ${change} where id=$1`,[admin]);
   await assert.rejects(authorized(),/Admin access required/);
   await db.query('update auth.users set email_confirmed_at=now(),banned_until=null,deleted_at=null,is_anonymous=false where id=$1',[admin]);
  }
 });
 await t.test('unsupported periods, oversized searches and invalid offsets are rejected',async()=>{
  for(const args of [[-1,'',0],[0,'',0],[999,'',0],[5,'a'.repeat(101),0],[5,'',-1],[5,'',1000001],[5,'',null]]) await assert.rejects(authorized(...args),/Invalid account report/);
 });
 await t.test('newest-first pagination is bounded and preserves a stable order for equal timestamps',async()=>{
  await db.exec(`INSERT INTO auth.users(id,email,created_at,email_confirmed_at)
   SELECT ('aaaaaaaa-aaaa-4aaa-8aaa-'||lpad(n::text,12,'0'))::uuid,'page-'||n||'@example.test',now()-interval '20 days',now() FROM generate_series(1,23) n`);
  const first=await authorized(null,'page-'),second=await authorized(null,'page-',20);
  assert.equal(first.total,23);assert.equal(first.items.length,20);assert.equal(second.items.length,3);
  assert.equal(new Set([...first.items,...second.items].map(x=>x.id)).size,23);
  assert.deepEqual(first.items.map(x=>x.id),[...first.items.map(x=>x.id)].sort());
  assert.equal((await authorized(null,'page-',40)).items.length,0);
 });
 await db.close();
});

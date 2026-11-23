import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';

test('directory upcoming dates use published events without exposing application details', async t => {
 const db = new PGlite();
 await db.exec(`
 CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role;
 CREATE TABLE public.markets(id uuid PRIMARY KEY,is_hidden boolean DEFAULT false,is_sample boolean DEFAULT false);
 CREATE TABLE public.vendor_opportunities(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),market_id uuid REFERENCES public.markets(id),
 starts_on date,ends_on date,schedule_type text DEFAULT 'dated_event',publication text DEFAULT 'published',
 availability text DEFAULT 'open',deadline timestamptz,application_url text DEFAULT 'https://example.org/member-only-application'
 );
 ALTER TABLE public.vendor_opportunities ENABLE ROW LEVEL SECURITY;
 `);
 const root = new URL('../supabase/migrations/', import.meta.url);
 const migrations = (await readdir(root)).filter(path => path.endsWith('_market_directory_upcoming_events.sql'));
 assert.equal(migrations.length, 1);
 await db.exec(await readFile(new URL(migrations[0], root), 'utf8'));
 const day = (await db.query("select (now() at time zone 'America/New_York')::date::text as day")).rows[0].day;
 const id = n => `aaaaaaaa-aaaa-4aaa-8aaa-${String(n).padStart(12,'0')}`;
 for (let n=1;n<=8;n++) await db.query('insert into public.markets(id,is_hidden,is_sample) values($1,$2,$3)',[id(n),n===5,n===6]);
 async function opportunity(n,start,end,{publication='published',schedule='dated_event',availability='open',deadline=null}={}) {
  await db.query(`insert into public.vendor_opportunities(market_id,starts_on,ends_on,publication,schedule_type,availability,deadline)
   values($1,$2::date+$3::int,$2::date+$4::int,$5,$6,$7,$8)`,[id(n),day,start,end,publication,schedule,availability,deadline]);
 }
 await opportunity(1,3,3);await opportunity(1,8,9);await opportunity(1,12,12,{publication:'draft'});
 await opportunity(2,-2,-1);
 await opportunity(3,-1,1);
 await opportunity(4,0,0);
 await opportunity(5,4,4);await opportunity(6,4,4);
 await opportunity(7,10,20,{publication:'draft'});await opportunity(7,20,20,{publication:'archived'});
 for (const schedule of ['seasonal_application','rolling_market','recurring_season']) await opportunity(7,1,100,{schedule});
 await opportunity(8,2,2,{availability:'closed',deadline:'2000-01-01T00:00:00Z'});
 async function dates(role='anon') {
  await db.exec(`set role ${role}`);
  try{return (await db.query('select * from public.btb_public_market_upcoming_dates() order by market_id')).rows;}
  finally{await db.exec('reset role');}
 }
 await t.test('multiple opportunities produce one market; past-only, hidden, demo and unpublished dates are excluded',async()=>{
  const data=await dates();assert.deepEqual(data.map(row=>row.market_id),[id(1),id(3),id(4),id(8)]);
  const last=(await db.query('select ($1::date+9)::text as day',[day])).rows[0].day;
  assert.equal(data[0].last_event_ends_on.toISOString().slice(0,10),last);
 });
 await t.test('multi-day events in progress and events happening today count',async()=>{
  const data=await dates();assert(data.some(row=>row.market_id===id(3)));assert(data.some(row=>row.market_id===id(4)));
 });
 await t.test('application periods and rolling placeholders do not count as event dates',async()=>{
  assert(!(await dates()).some(row=>row.market_id===id(7)));
 });
 await t.test('closed applications do not remove an event that has yet to happen',async()=>{
  assert((await dates()).some(row=>row.market_id===id(8)));
 });
 await t.test('guest and member results match and expose only market ID and event date',async()=>{
  assert.deepEqual(await dates('authenticated'),await dates());
  for(const row of await dates())assert.deepEqual(Object.keys(row).sort(),['last_event_ends_on','market_id']);
  await assert.rejects(db.exec('set role anon;select * from public.vendor_opportunities'),/permission denied/);
  await db.exec('reset role');
 });
 await t.test('event expiry uses the North Carolina calendar rather than the database/session timezone',async()=>{
  const original=await dates();
  await db.exec("set time zone 'Pacific/Kiritimati'");assert.deepEqual(await dates(),original);
  await db.exec("set time zone 'America/Los_Angeles'");assert.deepEqual(await dates(),original);
  await db.query('update public.vendor_opportunities set starts_on=$1::date-2,ends_on=$1::date-1 where market_id=$2',[day,id(4)]);
  assert(!(await dates()).some(row=>row.market_id===id(4)));
 });
 await db.close();
});

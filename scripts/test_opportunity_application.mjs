import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),out=mkdtempSync(join(tmpdir(),'btb-call-actions-'));
execFileSync(process.execPath,[require.resolve('typescript/bin/tsc'),'src/lib/opportunityApplication.ts','src/lib/opportunitySearchUrl.ts','--outDir',out,'--module','commonjs','--target','es2022','--skipLibCheck','--esModuleInterop']);
const {opportunityApplication}=require(join(out,'opportunityApplication.js'));
const {filterOpportunities}=require(join(out,'opportunities.js'));
const {opportunityDeadline}=require(join(out,'opportunityPresentation.js'));
const {readOpportunitySearch,writeOpportunitySearch}=require(join(out,'opportunitySearchUrl.js'));
after(()=>rmSync(out,{recursive:true,force:true}));
const base={effective_status:'open',application_url:'https://organizer.example/market',application_method:'form',application_contact:'',opens_on:null};
test('email action opens only the published vendor address, without message headers',()=>{
 const action=opportunityApplication({...base,application_method:'email',application_contact:'vendors@example.org'});
 assert.equal(action.href,'mailto:vendors@example.org');assert.equal(action.label,'Email organizer');assert.equal(action.external,false);
 for(const value of ['vendors@example.org?bcc=other@example.org','a@example.org\r\nBcc:elsewhere@example.org','mailto:a@example.org'])assert.equal(opportunityApplication({...base,application_method:'email',application_contact:value}).href,null);
});
test('Instagram contact actions are restricted to the reviewed profile',()=>{
 const action=opportunityApplication({...base,application_method:'instagram',application_contact:'songbird.nc',application_url:'https://www.instagram.com/songbird.nc/'});
 assert.equal(action.label,'Message organizer');assert.match(action.note,/tap Message/);
 assert.equal(opportunityApplication({...base,application_method:'instagram',application_contact:'songbird.nc',application_url:'https://instagram.com.evil.example/songbird.nc/'}).href,null);
});
test('announced and closed states never expose an Apply now action',()=>{
 const announced=opportunityApplication({...base,effective_status:'announced',opens_on:'2026-12-01'});
 assert.equal(announced.label,'View application details');assert.match(announced.note,/December 1, 2026/);
 for(const state of ['closed','needs_recheck','unavailable'])assert.equal(opportunityApplication({...base,effective_status:state}).href,null);
});
test('opening soon is included in active browsing and persists in shared filters',()=>{
 const item={...base,categories:[],title:'Market',organizer:'Host',city:'Cary',venue:'Venue',starts_on:'2027-08-28',ends_on:'2027-08-29',booth_fee:null,effective_status:'announced',deadline:null};
 const filters={search:'',city:'',month:'',category:'',status:'active'};
 assert.equal(filterOpportunities([item],filters).length,1);
 const url=writeOpportunitySearch(new URL('https://www.behindtheboothhq.com/opportunities'),{...filters,status:'announced'},'date');
 assert.equal(readOpportunitySearch(url.searchParams).filters.status,'announced');
});
test('community date-only deadlines remain dates and sort correctly',()=>{
 const deadline=opportunityDeadline({starts_on:'2027-08-28',deadline:null,deadline_date:'2027-02-28'});
 assert.equal(deadline.calendarDate,'2027-02-28');assert.match(deadline.value,/time not specified/);
});

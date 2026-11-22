/** Run with node --test scripts/test_opportunity_facts.mjs. */
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRequire } from "node:module";
const require=createRequire(import.meta.url), output=mkdtempSync(join(tmpdir(),"btb-fact-tests-"));
execFileSync(process.execPath,[require.resolve("typescript/bin/tsc"),"src/lib/opportunities.ts","--outDir",output,"--module","commonjs","--target","es2022","--skipLibCheck","--esModuleInterop"]);
const {applicationFeePresentation,hasPublishedApplicationFee,comparableBoothFee}=require(join(output,"opportunityFacts.js"));
const {opportunityBoothPrice,opportunityDeadline,opportunityDetailSections}=require(join(output,"opportunityPresentation.js"));
const {filterOpportunities}=require(join(output,"opportunities.js"));
const {listedOpportunityCategories}=require(join(output,"opportunityCategories.js"));
after(()=>rmSync(output,{recursive:true,force:true}));
const option=(label,amount,unit,kind="booth",applicable=true)=>({label,amount,unit,kind,applicable,conditions:"Source conditions",source_url:"https://example.org/fees"});
const base={id:"a",title:"Market",city:"Raleigh",organizer:"Organizer",venue:"Venue",starts_on:"2027-01-01",ends_on:"2027-12-31",deadline:null,booth_fee:null,application_fee:null,fee_notes:"",categories:[],effective_status:"open",schedule_type:"seasonal_application"};
test("guest-day and season charges stay separate in cards and budget filters",()=>{
  const item={...base,field_facts:{pricing_options:[option("Guest",30,"day"),option("Full season",260,"season"),option("Part season",180,"season")]}};
  const display=opportunityBoothPrice(item);
  assert.equal(display.value,"$30.00 / day");assert.match(display.note,/Full season: \$260.00/);
  assert.equal(comparableBoothFee(item),30);
  assert.equal(filterOpportunities([item],{status:"all",search:"",maxBoothFee:"35",priceAvailability:"published"},null,0).length,1);
});
test("unknown application fees never become free; separate applicant plans are visible",()=>{
  assert.equal(applicationFeePresentation(base).value,"Confirm with organizer");
  assert.equal(hasPublishedApplicationFee(base),false);
  assert.equal(hasPublishedApplicationFee({...base,application_fee:0}),true);
  assert.equal(applicationFeePresentation({...base,field_facts:{application_fee:{status:"not_listed",summary:"No separate charge identified."}}}).value,"Not separately listed");
  assert.equal(applicationFeePresentation({...base,application_fee:0}).value,"$0.00");
  assert.equal(applicationFeePresentation({...base,application_fee:10,field_facts:{application_fee:{status:"confirmed",amount:15,summary:"Current exact application charge."}}}).value,"$15.00");
  const plans={...base,field_facts:{pricing_options:[option("New",35,"application","application"),option("Returning",25,"application","application")]}};
  assert.equal(applicationFeePresentation(plans).value,"$25.00–$35.00");
});
test("a sample agreement does not establish a current event price",()=>{
  const item={...base,field_facts:{pricing:{status:"varies_by_event",summary:"Confirm your event rate."},pricing_options:[option("Sample resident price",30,"program","booth",false)]}};
  assert.equal(opportunityBoothPrice(item).value,"Varies by event");assert.equal(comparableBoothFee(item),null);
});
test("older prose prices cannot contradict the newly source-checked options",()=>{
  const item={...base,fee_notes:"Guest $20 per day. Exact cost not verified. Fees are nonrefundable.",eligibility:"Bring your own table.",field_facts:{pricing_options:[option("Guest",30,"day")]}};
  assert.deepEqual(opportunityDetailSections(item).fees,["Fees are nonrefundable."]);
  assert.equal(opportunityBoothPrice(item).value,"$30.00 / day");
});
test("confirmed calendar deadlines display and filter without fabricating a timestamp",()=>{
  const item={...base,field_facts:{deadline:{status:"date_only",date:"2026-11-27",summary:"No cutoff time published."}}};
  const display=opportunityDeadline(item);
  assert.match(display.value,/Nov 27, 2026 · time not specified/);assert.equal(item.deadline,null);
  assert.equal(filterOpportunities([item],{status:"all",search:"",deadlineBefore:"2026-11-27"},null,0).length,1);
  assert.equal(filterOpportunities([item],{status:"all",search:"",deadlineBefore:"2026-11-26"},null,0).length,0);
});
test("new category facts never override an explicit exclusion",()=>{
  const item={...base,field_facts:{categories:["Handmade Crafts","Food Trucks"]},category_evidence:{"Food Trucks":{status:"excluded",checked_at:"2026-11-22T00:00:00Z"}}};
  assert.deepEqual(listedOpportunityCategories(item,Date.parse("2026-11-22T16:00:00Z")),["Handmade Crafts"]);
});

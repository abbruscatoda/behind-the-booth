/** Run with node --test scripts/test_opportunity_facts.mjs. */
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRequire } from "node:module";
const require=createRequire(import.meta.url), output=mkdtempSync(join(tmpdir(),"btb-fact-tests-"));
execFileSync(process.execPath,[require.resolve("typescript/bin/tsc"),"src/lib/opportunities.ts","src/lib/opportunitySourceLink.ts","--outDir",output,"--module","commonjs","--target","es2022","--skipLibCheck","--esModuleInterop"]);
const {applicationFeePresentation,hasPublishedApplicationFee,comparableBoothFee}=require(join(output,"opportunityFacts.js"));
const {opportunityBoothPrice,opportunityDeadline,opportunityDetailSections}=require(join(output,"opportunityPresentation.js"));
const {filterOpportunities}=require(join(output,"opportunities.js"));
const {listedOpportunityCategories,categorySourceTerms,categoryEvidenceLabel,categoryScopeNote,categoryMatchLabel}=require(join(output,"opportunityCategories.js"));
const {opportunitySourceLink}=require(join(output,"opportunitySourceLink.js"));
after(()=>rmSync(output,{recursive:true,force:true}));
const option=(label,amount,unit,kind="booth",applicable=true)=>({label,amount,unit,kind,applicable,conditions:"Source conditions",source_url:"https://example.org/fees"});
const base={id:"a",title:"Market",city:"Raleigh",organizer:"Organizer",venue:"Venue",starts_on:"2027-01-01",ends_on:"2027-12-31",deadline:null,booth_fee:null,application_fee:null,fee_notes:"",categories:[],effective_status:"open",schedule_type:"seasonal_application"};
test("source labels distinguish organizer sites, hosted listings, applications and documents",()=>{
  for (const [url,label] of [
    ["https://grlmarket.com/","Visit organizer website"],
    ["https://artspacenc.org/calls-for-art/","Visit organizer website"],
    ["https://www.eventeny.com/events/market-123/","View listing on Eventeny"],
    ["https://www.eventeny.com/events/vendor/?id=38737","View application on Eventeny"],
    ["https://form.jotform.com/252944311617153","View application form"],
    ["https://docs.google.com/forms/d/e/example/viewform","View Google Form"],
    ["https://forms.gle/example","View Google Form"],
    ["https://www.zapplication.org/event-info.php?ID=14901","View application on ZAPP"],
    ["https://example.org/fees.PDF?download=1","View organizer PDF"],
    ["https://docs.google.com/document/d/example/edit","View organizer document"],
  ]) {
    const result=opportunitySourceLink(url);assert.equal(result.label,label);assert.equal(result.href,new URL(url).href);
    assert.match(result.title,/in a new tab$/);
  }
  assert.equal(opportunitySourceLink("https://example.org/apply","https://example.org/apply").label,"View application information");
  assert.equal(opportunitySourceLink("https://example.org/","invalid").label,"Visit organizer website");
  assert.equal(opportunitySourceLink("https://eventeny.com.example.org/events/123").label,"Visit organizer website");
  for(const url of ["javascript:alert(1)","http://example.org","https://user:password@example.org/","invalid"]){assert.equal(opportunitySourceLink(url),null);}
});
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
test("a dated festival can explicitly accept applications year-round",()=>{
  const display=opportunityDeadline({...base,schedule_type:"dated_event",field_facts:{deadline:{status:"rolling",summary:"The organizer accepts applications year-round."}}});
  assert.equal(display.value,"Applications accepted year-round");assert.equal(display.sortAt,Infinity);
});
test("published application prices replace missing main-field prices without inventing a universal tier",()=>{
  const item={...base,field_facts:{pricing_options:[option("Retail vendor",350,"event"),option("Food truck",800,"event"),option("Refundable deposit",200,"event","addon")]}};
  assert.equal(opportunityBoothPrice(item).value,"$350.00–$800.00 / event");
  assert.equal(comparableBoothFee(item),350);
  assert.equal(opportunityBoothPrice({...base,field_facts:{pricing:{status:"unconfirmed",summary:"Application requires Google sign-in."}}}).value,"Price not yet verified");
  assert.equal(opportunityBoothPrice({...base,field_facts:{pricing:{status:"unconfirmed",summary:"Published booth pricing. Full costs and eligibility are available with a free account."}}}).note,"Current application costs have not yet been verified.");
});
test("new category facts never override an explicit exclusion",()=>{
  const item={...base,field_facts:{categories:["Handmade Crafts","Food Trucks"]},category_evidence:{"Food Trucks":{status:"excluded",checked_at:"2026-11-22T00:00:00Z"}}};
  assert.deepEqual(listedOpportunityCategories(item,Date.parse("2026-11-22T16:00:00Z")),["Handmade Crafts"]);
});
test("food-only evidence quotes the organizer's products and leaves beverages unconfirmed",()=>{
  const fact={status:"eligible",source_terms:["Baked Goods / Savory Food Items","Prepackaged Items (Honey, Hot Sauce, etc.)"]};
  assert.equal(categoryEvidenceLabel(fact),"Organizer lists these products");
  assert.match(categoryMatchLabel("Food & Beverages",fact),/beverages unconfirmed/);
  assert.match(categoryScopeNote("Food & Beverages",fact),/Beverage vendors are not explicitly listed/);
  assert.match(categoryScopeNote("Food & Beverages",fact),/food trucks are not confirmed/);
  assert.deepEqual(categorySourceTerms(fact),fact.source_terms);
});
test("legacy category groups never masquerade as exact source wording or product approval",()=>{
  const fact={status:"eligible",note:"The organizer lists this type."};
  assert.equal(categoryEvidenceLabel(fact),"Related products mentioned");
  assert.deepEqual(categorySourceTerms(fact),[]);
  assert.match(categoryScopeNote("Art & Photography",fact),/eligibility is unconfirmed/);
  assert.match(categoryScopeNote("Food & Beverages",fact),/eligibility is unconfirmed/);
  assert.match(categoryScopeNote("Other",{...fact,source_terms:["Other"]}),/does not confirm eligibility/);
});
test("mixed and drink-only options remain limited to the products actually named",()=>{
  for (const terms of [["Lemonade"],["Baked goods","Coffee & Tea products"]]) {
    const note=categoryScopeNote("Food & Beverages",{status:"eligible",source_terms:terms});
    assert.match(note,/Only the listed food and drink types/);assert.match(note,/Other products and setups are unconfirmed/);
  }
  assert.match(categoryScopeNote("Food & Beverages",{status:"eligible",source_terms:["Baked goods; no beverages"]}),/Beverage restrictions/);
});
test("search uses fresh exact product words without making a broad food label a beverage match",()=>{
  const now=Date.parse("2026-11-23T12:00:00Z");
  const item={...base,categories:["Food & Beverages"],category_evidence:{"Food & Beverages":{status:"eligible",checked_at:"2026-11-23T00:00:00Z",source_terms:["Baked goods"]}}};
  const filters={status:"all",search:"baked goods",category:"Food & Beverages"};
  assert.equal(filterOpportunities([item],filters,null,now).length,1);
  assert.equal(filterOpportunities([item],{...filters,search:"beverages"},null,now).length,0);
  assert.equal(filterOpportunities([item],filters,null,now+8*86400000).length,0);
});

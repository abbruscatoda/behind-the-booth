import { safeExternalUrl, type Opportunity } from "./opportunities";
import { formatAttendanceDate } from "./attendanceDate";

/** Action labels describe the real destination; emails never gain query headers. */
export function opportunityApplication(item: Pick<Opportunity,"effective_status"|"application_url"|"application_method"|"application_contact"|"opens_on">) {
 const url=safeExternalUrl(item.application_url);
 if(item.effective_status==="announced")return {href:url,label:"View application details",external:true,note:item.opens_on?`Applications open ${formatAttendanceDate(item.opens_on)}.`:"Applications are not open yet."};
 if(!["open","limited","waitlist"].includes(item.effective_status))return {href:null,label:item.effective_status==="closed"?"Application closed":"Application not currently verified",external:false,note:""};
 if(item.application_method==="email") {
  const contact=item.application_contact??"";
  if(!/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}$/.test(contact))return {href:null,label:"Vendor contact not verified",external:false,note:""};
  return {href:`mailto:${contact}`,label:"Email organizer",external:false,note:"Apply by email. Organizer selection is required."};
 }
 if(item.application_method==="instagram") {
  const handle=item.application_contact??"";
  if(!/^[a-z0-9._]{2,30}$/.test(handle)||url!==`https://www.instagram.com/${handle}/`)return {href:null,label:"Vendor contact not verified",external:false,note:""};
  return {href:url,label:"Message organizer",external:true,note:`Open @${handle} on Instagram and tap Message to ask about vending.`};
 }
 return {href:url,label:item.effective_status==="waitlist"?"Official waitlist":"Official application",external:true,note:""};
}

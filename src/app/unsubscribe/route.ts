import { NextRequest, NextResponse } from "next/server";

const validToken = (value:string|null):value is string => Boolean(value&&/^[a-f\d]{8}-(?:[a-f\d]{4}-){3}[a-f\d]{12}$/i.test(value));
const headers = {"Content-Type":"text/html; charset=utf-8","Cache-Control":"private, no-store","Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"};
function screen(text:string,token:string|null=null,status=200){
  return new NextResponse(`<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Opportunity email preferences | Behind the Booth</title><body style="margin:0;background:#F4F0E6;color:#252521;font:16px/1.6 Arial,sans-serif"><main style="max-width:560px;margin:10vh auto;padding:24px"><p style="color:#07472B;font-weight:bold">BEHIND THE BOOTH</p><h1 style="font-family:Georgia,serif">Opportunity emails</h1><p>${text}</p>${token?`<form method="post" action="/unsubscribe?token=${token}"><button style="padding:14px 20px;border:0;background:#07472B;color:white;font-size:16px;cursor:pointer">Stop opportunity emails</button></form>`:""}<p><a style="color:#07472B" href="/login#opportunity-alerts">Manage preferences in My Account</a></p></main></body></html>`,{status,headers});
}
export async function GET(request:NextRequest){
  const token=request.nextUrl.searchParams.get("token");
  if(!validToken(token))return screen("This unsubscribe link is invalid. You can turn off alerts in My Account.",null,400);
  return screen("Choose the button below to stop new-opportunity emails and saved-deadline reminders. Your account and saved opportunities will stay available.",token);
}
export async function POST(request:NextRequest){
  const token=request.nextUrl.searchParams.get("token");
  if(!validToken(token))return screen("This unsubscribe link is invalid. You can turn off alerts in My Account.",null,400);
  const base=process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key=process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if(!base||!key)return screen("We couldn't update your preferences. Please try again or use My Account.",token,503);
  try{
    const result=await fetch(`${base.replace(/\/$/,"")}/rest/v1/rpc/btb_unsubscribe_opportunity_alerts`,{
      method:"POST",headers:{apikey:key,"Content-Type":"application/json"},body:JSON.stringify({p_token:token}),cache:"no-store",signal:AbortSignal.timeout(12000),
    });
    if(!result.ok)throw Error("Unsubscribe failed");
    return screen("You won't receive further opportunity digests or saved-deadline reminders for this subscription. You can choose to enable them again in My Account.");
  }catch{return screen("We couldn't update your preferences. Please try again or use My Account.",token,502);}
}

// Scheduled, explicitly opted-in digests. All provider credentials stay server-side.
// verify_jwt=false is intentional: the existing private research-worker header
// is checked by the database before any delivery operation is available.
declare const Deno:{env:{get(name:string):string|undefined};serve(handler:(req:Request)=>Promise<Response>):void};
type Entry={kind:"new"|"deadline";item:Record<string,any>;fingerprint:string};
type Job={id:string;user_id:string;claim_token:string;entries:Entry[];payload:Record<string,any>|null;unsubscribe_token:string};
const response=(status:number,body:Record<string,unknown>)=>Response.json(body,{status,headers:{"Cache-Control":"no-store"}});
const escape=(value:unknown)=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]!));
const day=(value:string)=>new Date(value+"T12:00:00Z").toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"America/New_York"});

export function buildOpportunityDigest(entries:Entry[],origin:string,unsubscribeToken:string){
  const unsubscribe=`${origin}/unsubscribe?${new URLSearchParams({token:unsubscribeToken})}`;
  const parts=entries.map(({kind,item})=>{
    const link=`${origin}/opportunities?${new URLSearchParams({details:item.id})}#${item.id}`;
    const window=item.schedule_type==="rolling_market"?"Ongoing market":day(item.starts_on)+(item.ends_on!==item.starts_on?` – ${day(item.ends_on)}`:"");
    const deadline=item.field_facts?.deadline?.status==="date_only"?day(item.field_facts.deadline.date):item.deadline?new Date(item.deadline).toLocaleString("en-US",{timeZone:"America/New_York",dateStyle:"medium",timeStyle:"short"}):"Confirm with organizer";
    const state=({open:"Applications open",limited:"Limited options",waitlist:"Waitlist only"} as Record<string,string>)[item.effective_status]??"Check current availability";
    const label=kind==="deadline"?"Saved deadline approaching":"New matching opportunity";
    const detail=kind==="deadline"?`Application deadline: ${deadline}`:window;
    return {text:`${label}\n${item.title}\n${item.city}, ${item.state} · ${state}\n${detail}\nView details: ${link}`,
      html:`<section style="border-top:1px solid #d6d4bf;padding:20px 0"><p style="font-size:13px;color:#626C57">${label}</p><h2 style="font:700 22px Georgia,serif">${escape(item.title)}</h2><p>${escape(item.city)}, ${escape(item.state)} · ${escape(state)}</p><p>${escape(detail)}</p><a style="color:#07472B;font-weight:bold" href="${escape(link)}">View opportunity details</a></section>`};
  });
  const introduction="Here are your optional opportunity updates from Behind the Booth. Categories and remaining spaces still need organizer confirmation; limited options and waitlists are labeled below.";
  return {subject:"Your opportunity updates — Behind the Booth",
    text:`Your opportunity updates\n\n${introduction}\n\n${parts.map(p=>p.text).join("\n\n")}\n\nManage preferences: ${origin}/login#opportunity-alerts\nUnsubscribe: ${unsubscribe}\n\nYou're receiving this because you enabled opportunity emails in My Account. Behind the Booth supports Raleigh and Triangle vendors.`,
    html:`<div style="font:16px/1.6 Arial,sans-serif;color:#252521;background:#FFFCF6;max-width:580px;margin:auto;padding:28px"><p style="color:#07472B;font-weight:bold">BEHIND THE BOOTH</p><h1 style="font-family:Georgia,serif">Your opportunity updates</h1><p>${introduction}</p>${parts.map(p=>p.html).join("")}<p><a style="color:#07472B" href="${origin}/login#opportunity-alerts">Manage preferences</a> · <a style="color:#07472B" href="${escape(unsubscribe)}">Unsubscribe</a></p><p style="font-size:13px;color:#626C57">You're receiving this because you enabled opportunity emails in My Account. Behind the Booth supports Raleigh and Triangle vendors.</p></div>`,
    headers:{"List-Unsubscribe":`<${unsubscribe}>`,"List-Unsubscribe-Post":"List-Unsubscribe=One-Click"},
  };
}

export async function handleOpportunityAlerts(req:Request,env:(name:string)=>string|undefined=name=>Deno.env.get(name),fetcher:typeof fetch=fetch):Promise<Response>{
  if(req.method!=="POST")return response(405,{error:"POST required."});
  const supplied=req.headers.get("x-btb-research-secret")??"";
  if(!/^[a-f\d]{64}$/i.test(supplied))return response(401,{error:"Unauthorized."});
  const base=(env("SUPABASE_URL")??"").replace(/\/$/,"");
  const publicKey=env("SUPABASE_ANON_KEY");
  const service=env("SUPABASE_SERVICE_ROLE_KEY");
  const provider=env("RESEND_API_KEY");
  const from=env("MEMBER_NOTIFICATION_FROM")?.trim();
  const origin=(env("MEMBER_SITE_URL")??"https://www.behindtheboothhq.com").replace(/\/$/,"");
  try{const site=new URL(origin);if(site.protocol!=="https:"||site.username||site.password||site.pathname!=="/"||site.search||site.hash)throw Error();}
  catch{return response(503,{error:"Invalid site configuration."});}
  if(!base||!publicKey||!service||!provider||!from||/[\r\n]/.test(from))return response(503,{error:"Alert delivery is not configured."});
  let authorization:Response;
  try{authorization=await fetcher(`${base}/rest/v1/rpc/btb_research_authorize`,{method:"POST",headers:{apikey:publicKey,"Content-Type":"application/json","x-btb-research-secret":supplied},body:"{}",signal:AbortSignal.timeout(12000)});}
  catch{return response(502,{error:"Could not verify worker authorization."});}
  if(!authorization.ok)return response(authorization.status===401||authorization.status===403?401:502,{error:"Worker authorization failed."});
  if(!req.headers.get("content-type")?.startsWith("application/json"))return response(415,{error:"Use application/json."});
  let dryRun:boolean;
  try{const text=await req.text();if(text.length>1024)throw Error();const body=JSON.parse(text);if(typeof body.dry_run!=="boolean")throw Error();dryRun=body.dry_run;}
  catch{return response(400,{error:"Provide an explicit dry_run boolean."});}
  const headers={apikey:service,Authorization:`Bearer ${service}`,"Content-Type":"application/json"};
  async function api(path:string,init:RequestInit={}){
    const result=await fetcher(`${base}${path}`,{...init,headers,signal:AbortSignal.timeout(12000)});
    if(!result.ok)throw Error(`database_${result.status}`);
    const text=await result.text();return text?JSON.parse(text):null;
  }
  const rpc=(name:string,body:Record<string,unknown>={})=>api(`/rest/v1/rpc/${name}`,{method:"POST",body:JSON.stringify(body)});
  try{
    const due:string[]=await rpc("btb_due_opportunity_alerts");
    if(dryRun)return response(200,{dry_run:true,configured:true,due_members:due.length});
    let sent=0,skipped=0,failed=0;
    let current:Map<string,Record<string,any>>|null=null;
    for(const userId of due){
      let job:Job|null=null;
      try{
        job=await rpc("btb_claim_opportunity_alert",{p_user_id:userId});
        if(!job){skipped++;continue;}
        const finish=(state:string,id:string|null=null)=>rpc("btb_finish_opportunity_alert",{p_id:job!.id,p_token:job!.claim_token,p_state:state,p_resend_id:id});
        const user=await api(`/auth/v1/admin/users/${job.user_id}`);
        if(!user.email||!user.email_confirmed_at||user.deleted_at||(user.banned_until&&new Date(user.banned_until)>new Date())){await finish("skipped");skipped++;continue;}
        if(!current){
          current=new Map();let offset=0;
          while(true){const list=await rpc("btb_public_opportunities",{p_market_id:null,p_offset:offset});for(const item of list.items)current.set(item.id,item);offset+=100;if(offset>=list.total||list.items.length===0)break;}
        }
        // Recheck current publication/availability before sending a persisted retry.
        if(!job.entries.every(entry=>{const now=current!.get(entry.item.id);return now&&["open","limited","waitlist"].includes(now.effective_status)&&now.deadline===entry.item.deadline&&JSON.stringify(now.field_facts?.deadline)===JSON.stringify(entry.item.field_facts?.deadline);})){await finish("skipped");skipped++;continue;}
        if(job.payload&&job.payload.to?.[0]!==user.email){await finish("skipped");skipped++;continue;}
        const content=job.payload??{from,to:[user.email],...buildOpportunityDigest(job.entries,origin,job.unsubscribe_token)};
        // This also rechecks that consent is still enabled and unchanged.
        const payload=await rpc("btb_prepare_opportunity_alert",{p_id:job.id,p_token:job.claim_token,p_payload:content});
        if(!payload){await finish("skipped");skipped++;continue;}
        const result=await fetcher("https://api.resend.com/emails",{method:"POST",headers:{Authorization:`Bearer ${provider}`,"Content-Type":"application/json","Idempotency-Key":`btb-opportunity-alert/${job.id}`},body:JSON.stringify(payload),signal:AbortSignal.timeout(15000)});
        if(!result.ok)throw Error(`provider_${result.status}`);
        const delivery=await result.json();if(typeof delivery.id!=="string")throw Error("provider_invalid_response");
        await finish("sent",delivery.id);sent++;
        // Respect the provider's request rate without overlapping sends.
        await new Promise(resolve=>setTimeout(resolve,550));
      }catch{
        failed++;
        if(job){try{await rpc("btb_finish_opportunity_alert",{p_id:job.id,p_token:job.claim_token,p_state:"failed",p_resend_id:null});}catch{/* The lease and stable provider key make an uncertain response safe to retry. */}}
      }
    }
    return response(failed?502:200,{sent,skipped,failed,more:due.length===10});
  }catch{return response(502,{error:"Alert batch failed. No recipient details are logged."});}
}
if(typeof Deno!=="undefined")Deno.serve(req=>handleOpportunityAlerts(req));

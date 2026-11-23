"use client";

import { useEffect, useState } from "react";
import { createClient } from "../lib/supabase/client";

export type AdminAccount = {
  id: string; email: string | null; created_at: string | null;
  email_confirmed_at: string | null; last_sign_in_at: string | null;
  business_name: string | null; business_url: string | null;
  vendor_status: "not_applied" | "pending" | "approved" | "rejected"; is_admin: boolean;
};
export type AdminAccountReport = {
  checked_at: string; page_size: number; total: number; items: AdminAccount[];
  summary: {total: number; last_5_days: number; last_30_days: number};
};
type Period = "5" | "7" | "30" | "90" | "all";
type ViewProps = {
  report: AdminAccountReport | null; period: Period; search: string; offset: number;
  loading: boolean; error: string; onPeriod: (value: Period) => void;
  onSearch: (value: string) => void; onRefresh: () => void; onOffset: (value: number) => void;
};
const inputClass = "mt-2 min-h-11 w-full rounded-sm border border-[#252521]/25 bg-[#FFFCF6] px-3 py-2.5 text-base outline-none focus:border-[#07472B]";
const buttonClass = "min-h-11 rounded-sm border border-[#07472B]/40 px-4 py-2 text-sm font-semibold text-[#07472B] hover:bg-[#E9E7DA] disabled:opacity-50";
const vendorLabels: Record<AdminAccount["vendor_status"], string> = {
  not_applied: "No application", pending: "Pending approval", approved: "Approved vendor", rejected: "Not approved",
};
function stamp(value: string | null) {
  const date = value ? new Date(value) : null;
  if (!date || !Number.isFinite(date.getTime())) return "Not recorded";
  return date.toLocaleString("en-US", {timeZone:"America/New_York",year:"numeric",month:"short",day:"numeric",hour:"numeric",minute:"2-digit"});
}
function Business({account}:{account:AdminAccount}) {
  let website: string | null = null;
  try {
    const url = new URL(account.business_url ?? "");
    if (["http:","https:"].includes(url.protocol) && !url.username && !url.password) website = url.href;
  } catch { /* A submitted URL is never trusted as markup or a script. */ }
  return <div className="mt-1 text-sm text-[#55554E]">
    <p className="break-words">{account.business_name || "Business not provided"}</p>
    {website && <a className="mt-1 inline-flex min-h-8 items-center font-semibold text-[#07472B] underline underline-offset-4" href={website} target="_blank" rel="noopener noreferrer">Business website</a>}
  </div>;
}
function EmailStatus({account}:{account:AdminAccount}) {
  return <span className={account.email_confirmed_at ? "font-semibold text-[#07472B]" : "font-semibold text-[#8A591A]"}>{account.email_confirmed_at ? "Confirmed" : "Awaiting confirmation"}</span>;
}

/** Presentational view is separate so private account layouts can be checked
 * using synthetic records without signing into or seeding real accounts. */
export function AdminAccountsView({report,period,search,offset,loading,error,onPeriod,onSearch,onRefresh,onOffset}:ViewProps) {
  const rangeLabel = period === "all" ? "all accounts" : `the last ${period} days`;
  return <details id="recent-accounts" className="group mt-8 min-w-0 rounded-sm border border-[#252521]/20 bg-[#FFFCF6] p-5 md:p-6">
    <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 [&::-webkit-details-marker]:hidden">
      <div><h2 className="font-serif text-2xl font-bold">Recent accounts</h2><p className="mt-1 text-sm text-[#626C57]">{report ? `${report.summary.last_5_days} new in the last 5 days · ${report.summary.total} total accounts` : loading ? "Checking account activity…" : "View account activity"}</p></div>
      <span className="flex items-center gap-2 text-sm font-semibold text-[#07472B]"><span className="group-open:hidden">View accounts</span><span className="hidden group-open:inline">Hide accounts</span><svg aria-hidden="true" className="h-4 w-4 transition-transform group-open:rotate-180" viewBox="0 0 16 16" fill="none"><path d="m4 6 4 4 4-4" stroke="currentColor" strokeWidth="1.5" /></svg></span>
    </summary>
    <div className="mt-5 border-t border-[#252521]/15 pt-5">
      {report && <dl className="grid grid-cols-3 gap-2 sm:gap-4">{([["Total accounts",report.summary.total],["Last 5 days",report.summary.last_5_days],["Last 30 days",report.summary.last_30_days]] as const).map(([label,count]) => <div key={label} className="min-w-0 bg-[#F4F0E6] p-3"><dt className="text-sm text-[#626C57]">{label}</dt><dd className="mt-1 text-2xl font-bold text-[#07472B]">{count}</dd></div>)}</dl>}
      <div className="mt-5 grid min-w-0 items-end gap-4 sm:grid-cols-[minmax(0,1fr)_11rem_auto]">
        <label className="min-w-0 text-sm font-semibold" htmlFor="admin-account-search">Search accounts<input id="admin-account-search" type="search" className={inputClass} value={search} maxLength={100} onChange={event=>onSearch(event.target.value)} placeholder="Email or business name" autoComplete="off" /></label>
        <label className="text-sm font-semibold" htmlFor="admin-account-period">Created<select id="admin-account-period" className={inputClass} value={period} onChange={event=>onPeriod(event.target.value as Period)}><option value="5">Last 5 days</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option><option value="all">All accounts</option></select></label>
        <button type="button" className={buttonClass} disabled={loading} onClick={onRefresh}>Refresh accounts</button>
      </div>
      <p className="mt-3 text-sm text-[#626C57]">Newest accounts first. All times are Eastern Time.</p>
      {loading ? <p role="status" className="py-8 text-sm">Loading accounts…</p> : error ? <div role="alert" className="mt-4 border-l-2 border-[#9B3E35] bg-[#F0E3DA] p-4 text-sm text-[#9B3E35]">{error}</div> : report && !report.items.length ? <div className="py-8 text-center"><h3 className="font-serif text-xl font-bold">No accounts found</h3><p className="mt-2 text-sm text-[#626C57]">{search.trim() ? "No accounts match this search and date range." : period === "all" ? "No accounts are available to show." : `No accounts were created in ${rangeLabel}. Choose All accounts to view existing members.`}</p></div> : report && <>
        <table className="mt-5 hidden w-full table-fixed border-collapse text-left text-sm lg:table">
          <caption className="sr-only">Accounts created in {rangeLabel}</caption>
          <thead><tr className="border-y border-[#252521]/15 text-[#626C57]"><th scope="col" className="w-[34%] py-3 pr-4">Account / business</th><th scope="col" className="w-[18%] py-3 pr-4">Created</th><th scope="col" className="w-[15%] py-3 pr-4">Email</th><th scope="col" className="w-[15%] py-3 pr-4">Vendor status</th><th scope="col" className="w-[18%] py-3">Last sign-in</th></tr></thead>
          <tbody>{report.items.map(account=><tr key={account.id} className="border-b border-[#252521]/15 align-top"><td className="py-4 pr-4"><p className="break-all font-semibold">{account.email || "Email not provided"}</p>{account.is_admin && <span className="mt-1 inline-block border border-[#07472B]/25 bg-[#E9E7DA] px-2 py-0.5 text-xs font-semibold text-[#07472B]">Admin</span>}<Business account={account} /></td><td className="py-4 pr-4">{stamp(account.created_at)}</td><td className="py-4 pr-4"><EmailStatus account={account} /></td><td className="py-4 pr-4">{vendorLabels[account.vendor_status] || "No application"}</td><td className="py-4">{account.last_sign_in_at ? stamp(account.last_sign_in_at) : "No sign-in yet"}</td></tr>)}</tbody>
        </table>
        <div className="mt-5 space-y-3 lg:hidden">{report.items.map(account=><article key={account.id} className="min-w-0 rounded-sm border border-[#252521]/15 p-4">
          <h3 className="break-all text-base font-semibold">{account.email || "Email not provided"}</h3>{account.is_admin && <p className="mt-1 text-sm font-semibold text-[#07472B]">Admin</p>}<Business account={account} />
          <dl className="mt-4 grid min-w-0 grid-cols-2 gap-x-4 gap-y-3 text-sm"><div className="min-w-0"><dt className="text-[#626C57]">Created</dt><dd className="mt-1">{stamp(account.created_at)}</dd></div><div className="min-w-0"><dt className="text-[#626C57]">Last sign-in</dt><dd className="mt-1">{account.last_sign_in_at ? stamp(account.last_sign_in_at) : "No sign-in yet"}</dd></div><div className="min-w-0"><dt className="text-[#626C57]">Email</dt><dd className="mt-1"><EmailStatus account={account} /></dd></div><div className="min-w-0"><dt className="text-[#626C57]">Vendor status</dt><dd className="mt-1">{vendorLabels[account.vendor_status] || "No application"}</dd></div></dl>
        </article>)}</div>
      </>}
      {report && !loading && !error && <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm"><p aria-live="polite">{report.total ? `${offset+1}–${Math.min(offset+report.page_size,report.total)} of ${report.total} accounts` : "0 accounts"}</p>{report.total>report.page_size && <div className="flex gap-2"><button type="button" className={buttonClass} disabled={offset===0} onClick={()=>onOffset(Math.max(0,offset-report.page_size))}>Previous</button><button type="button" className={buttonClass} disabled={offset+report.page_size>=report.total} onClick={()=>onOffset(offset+report.page_size)}>Next</button></div>}<p className="w-full text-sm text-[#626C57]">Updated {stamp(report.checked_at)}</p></div>}
    </div>
  </details>;
}

export default function AdminAccounts({ownerId}:{ownerId:string}) {
  const [period,setPeriod]=useState<Period>("5");
  const [search,setSearch]=useState("");
  const [query,setQuery]=useState("");
  const [offset,setOffset]=useState(0);
  const [revision,setRevision]=useState(0);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [response,setResponse]=useState<{ownerId:string;key:string;report:AdminAccountReport}|null>(null);
  const requestKey=`${period}\n${query}\n${offset}\n${revision}`;
  useEffect(()=>{
    const timer=setTimeout(()=>setQuery(search.trim()),250);
    return ()=>clearTimeout(timer);
  },[search]);
  useEffect(()=>{
    let active=true;
    setLoading(true);setError("");
    void (async()=>{
      try {
        const {data,error}=await createClient().rpc("btb_admin_accounts",{p_days:period==="all" ? null : Number(period),p_search:query,p_offset:offset});
        if (error) throw error;
        if (!active) return;
        const report=data as AdminAccountReport;
        if (offset>0 && !report.items.length) setOffset(Math.max(0,offset-report.page_size));
        else setResponse({ownerId,key:requestKey,report});
      } catch {
        if (active) {setResponse(null);setError("Account information could not be loaded. Refresh accounts to check your admin access and try again.");}
      } finally {if (active) setLoading(false);}
    })();
    return ()=>{active=false;};
  },[ownerId,period,query,offset,requestKey]);
  // Never render a response belonging to another identity or an old filter.
  const report=response?.ownerId===ownerId && response.key===requestKey ? response.report : null;
  return <AdminAccountsView report={report} period={period} search={search} offset={offset} loading={loading || query!==search.trim()} error={error}
    onPeriod={value=>{setPeriod(value);setOffset(0);}} onSearch={value=>{setSearch(value);setOffset(0);}}
    onRefresh={()=>setRevision(value=>value+1)} onOffset={setOffset} />;
}

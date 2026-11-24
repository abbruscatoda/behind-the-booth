import OpportunityBoard from "../../components/OpportunityBoard";
import { pageMetadata } from "../../lib/siteMetadata";
export const metadata=pageMetadata("Find Vendor Opportunities — Raleigh & the Triangle","Find upcoming Triangle markets accepting vendor applications. Compare deadlines, published fees, eligibility, and past vendor reviews.","/opportunities");
export default function OpportunitiesPage() {
  return <main className="opportunities-page mx-auto w-full max-w-6xl px-6 py-8 md:py-10">
    <p className="brand-eyebrow">Your next opportunity</p>
    <h1 className="heritage-heading mt-4 max-w-4xl text-4xl md:text-5xl">Find your next <span className="text-[#07472B]">place to sell.</span></h1>
    <p className="mt-3 max-w-3xl text-base leading-relaxed text-[#55554E]">Find upcoming Triangle markets, compare fees and deadlines, and apply directly with the organizer.</p>
    <details className="mt-4 max-w-3xl border-l-2 border-[#07472B] bg-[#E9E7DA] px-4 py-2 text-sm">
      <summary className="min-h-8 cursor-pointer py-1 font-semibold text-[#07472B]">How listings and applications work</summary>
      <p className="pb-2 pt-2 leading-relaxed text-[#55554E]">Open applications do not guarantee a booth or eligibility. Fees and category availability can change. Listings need rechecking after seven days; deadlines expire automatically. Our links take you to the organizer—we do not collect application payments. Unconfirmed categories may accept your business type; check the organizer’s requirements before applying.</p>
    </details>
    <OpportunityBoard />
  </main>;
}

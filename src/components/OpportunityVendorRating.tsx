import Link from "next/link";
import { getRatingColor, getRatingDescriptor } from "../lib/ratingColors";

export default function OpportunityVendorRating({score,reviewCount,marketSlug,marketTitle}:{score:number;reviewCount:number;marketSlug:string;marketTitle:string}) {
  const color=getRatingColor(score);
  const descriptor=getRatingDescriptor(score);
  const reviews=`${reviewCount} vendor ${reviewCount===1?"review":"reviews"}`;
  return <Link href={`/markets/${marketSlug}#vendor-reviews`}
    aria-label={`Read ${reviews} for ${marketTitle}. Overall vendor rating: ${score.toFixed(1)} out of 5, ${descriptor}.`}
    className="group mt-2 flex min-h-11 items-center gap-2.5 rounded-sm border-l-2 bg-[#FFFCF6] px-2.5 py-1.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]"
    style={{borderLeftColor:color}}>
    <span className="shrink-0 text-xl font-bold leading-none tracking-tight" style={{color}}>{score.toFixed(1)}<span className="ml-0.5 text-xs font-semibold">/5</span></span>
    <span className="min-w-0">
      <span className="block text-[10px] font-bold uppercase tracking-[0.06em] text-[#55554E]">Overall vendor rating</span>
      <span className="mt-0.5 block text-xs leading-snug"><strong style={{color}} title="1 Poor · 2 Below Average · 3 Average · 4 Good · 5 Exceptional">{descriptor}</strong><span className="text-[#55554E]"> · <span className="underline underline-offset-2 group-hover:decoration-2">{reviews}</span></span></span>
    </span>
  </Link>;
}

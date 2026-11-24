import { opportunitySourceLink } from "../lib/opportunitySourceLink";
import ExternalLinkIcon from "./ExternalLinkIcon";

/** Show the market's saved official destination using the same labels as opportunities. */
export default function MarketWebsiteLink({href,className}:{href:string|null;className?:string}) {
  const destination=opportunitySourceLink(href??"",undefined,"market");
  if (!destination) return null;
  return <a href={destination.href} target="_blank" rel="noopener noreferrer" title={destination.title} className={className}>
    {destination.label} <ExternalLinkIcon /><span className="sr-only"> (opens in a new tab)</span>
  </a>;
}

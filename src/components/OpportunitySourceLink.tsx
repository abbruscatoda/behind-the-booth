import { opportunitySourceLink } from "../lib/opportunitySourceLink";
import ExternalLinkIcon from "./ExternalLinkIcon";

export default function OpportunitySourceLink({href,applicationUrl,className}:{href:string;applicationUrl?:string;className?:string}) {
  const destination=opportunitySourceLink(href,applicationUrl);
  if (!destination) return null;
  return <a href={destination.href} target="_blank" rel="noopener noreferrer" title={destination.title} className={className}>
    {destination.label} <ExternalLinkIcon /><span className="sr-only"> (opens in a new tab)</span>
  </a>;
}

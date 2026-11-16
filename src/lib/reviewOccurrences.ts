export type Occurrence = { id: string; title: string; starts_on: string; ends_on: string };
export type OwnDatedReview = { id: string; status: string; attended_on: string | null; occurrence_id: string | null };
export function occurrenceReviewError(date: string, selectedId: string, occurrences: Occurrence[], existing: OwnDatedReview[]): string {
 const matches=occurrences.filter(item=>date>=item.starts_on && date<=item.ends_on);
 const selected=selectedId?occurrences.find(item=>item.id===selectedId):matches.length===1?matches[0]:undefined;
 if(selectedId && (!selected || date<selected.starts_on || date>selected.ends_on))return "Choose an attendance date within the selected event, or clear the event selection.";
 if(!selectedId && matches.length>1)return "More than one event matches this date. Choose the event you attended.";
 if(existing.some(review=>review.attended_on===date || (selected && (review.occurrence_id===selected.id || Boolean(review.attended_on && review.attended_on>=selected.starts_on && review.attended_on<=selected.ends_on)))))return "You already submitted a review for this market date or event occurrence. Check My Account for its status.";
 return "";
}

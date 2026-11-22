import { test } from "node:test";
import assert from "node:assert/strict";
import { hasNewReviews, latestReviewTime } from "../src/lib/marketReviewRecency.ts";
const now = Date.parse("2026-11-22T15:00:00Z");
const activity = latest => ({count:1,overall:4,latest});
test("review badges use public approval recency with a seven-day boundary", () => {
  assert.equal(hasNewReviews(activity("2026-11-21T15:00:00Z"),"week",null,now),true);
  assert.equal(hasNewReviews(activity("2026-11-15T15:00:00Z"),"week",null,now),false);
  assert.equal(hasNewReviews(activity("2026-11-23T15:00:00Z"),"week",null,now),false);
  assert.equal(hasNewReviews(activity(null),"week",null,now),false);
  assert.equal(hasNewReviews(activity("bad"),"week",null,now),false);
  assert.equal(hasNewReviews({...activity("2026-11-21T15:00:00Z"),count:0},"week",null,now),false);
  assert.equal(latestReviewTime(undefined),null);
});
test("since-last-visit includes older unread-period activity without calling it this week", () => {
  const old=activity("2026-11-10T15:00:00Z");
  assert.equal(hasNewReviews(old,"since","2026-11-01T15:00:00Z",now),true);
  assert.equal(hasNewReviews(old,"week",null,now),false);
  assert.equal(hasNewReviews(old,"since","2026-11-10T15:00:00Z",now),false);
  for(const baseline of [null,"bad","2026-12-01T15:00:00Z"])
    assert.equal(hasNewReviews(old,"since",baseline,now),false);
});

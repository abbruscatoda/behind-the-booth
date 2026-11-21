/** Run with: node --experimental-strip-types --test scripts/test_opportunity_recency.mjs */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  firstPublishedTime, isNewlyPosted, isPostedSince,
} from "../src/lib/opportunityRecency.ts";

const now = Date.parse("2026-11-21T20:00:00.000Z");
const item = published_at => ({published_at});

test("an opportunity is new for seven days after first publication", () => {
  assert.equal(isNewlyPosted(item("2026-11-20T20:00:00.000Z"),now),true);
  assert.equal(isNewlyPosted(item("2026-11-14T20:00:00.000Z"),now),false);
  assert.equal(isNewlyPosted(item("2026-11-22T20:00:00.000Z"),now),false);
  assert.equal(isNewlyPosted(item(null),now),false);
  assert.equal(isNewlyPosted(item("not a date"),now),false);
});
test("new listings since a prior visit use first publish date", () => {
  const baseline = "2026-11-19T20:00:00.000Z";
  assert.equal(isPostedSince(item("2026-11-20T20:00:00.000Z"),baseline,now),true);
  assert.equal(isPostedSince(item("2026-11-19T20:00:00.000Z"),baseline,now),false);
  assert.equal(isPostedSince(item("2026-11-18T20:00:00.000Z"),baseline,now),false);
  assert.equal(isPostedSince(item("2026-11-20T20:00:00.000Z"),null,now),false);
});
test("worker updates do not alter recency", () => {
  const old = {published_at:"2026-10-01T20:00:00.000Z",updated_at:"2026-11-21T19:58:00.000Z"};
  assert.equal(isNewlyPosted(old,now),false);
  assert.equal(isPostedSince(old,"2026-11-20T00:00:00.000Z",now),false);
  assert.equal(firstPublishedTime(old),Date.parse(old.published_at));
});

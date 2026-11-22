import { test } from "node:test";
import assert from "node:assert/strict";
import { PREFER_NOT_TO_DISCLOSE as withheld, validReviewCategoryChoice, toggleReviewCategory, publicReviewCategories } from "../src/lib/reviewCategories.ts";

test("a reviewer must choose categories or explicitly decline disclosure", () => {
  assert.equal(validReviewCategoryChoice([]), false);
  assert.equal(validReviewCategoryChoice(["Food & Beverages", "Other"]), true);
  assert.equal(validReviewCategoryChoice([withheld]), true);
  assert.equal(validReviewCategoryChoice([withheld, "Food & Beverages"]), false);
  assert.equal(validReviewCategoryChoice(["Not a category"]), false);
});

test("declining disclosure replaces every selected category, and sharing replaces that choice", () => {
  assert.deepEqual(toggleReviewCategory(["Food & Beverages", "Other"], withheld), [withheld]);
  assert.deepEqual(toggleReviewCategory([withheld], "Handmade Crafts"), ["Handmade Crafts"]);
  assert.deepEqual(toggleReviewCategory([withheld], withheld), []);
  assert.deepEqual(toggleReviewCategory(["Food & Beverages", "Other"], "Other"), ["Food & Beverages"]);
});

test("non-disclosure is excluded from public tags and category totals, including malformed mixed data", () => {
  assert.deepEqual(publicReviewCategories([withheld]), []);
  assert.deepEqual(publicReviewCategories([withheld, "Food & Beverages"]), []);
  assert.deepEqual(publicReviewCategories([]), []);
  assert.deepEqual(publicReviewCategories(["Handmade Crafts", "Other"]), ["Handmade Crafts", "Other"]);
});

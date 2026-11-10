"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { createClient } from "../lib/supabase/client";

const ratingLabels = [
  "Poor",
  "Below Average",
  "Average",
  "Good",
  "Exceptional",
];

const vendorCategories = [
  "Food & Beverages",
  "Jewelry & Accessories",
  "Art & Photography",
  "Handmade Crafts",
  "Clothing & Apparel",
  "Bath, Body & Beauty",
  "Home Goods & Décor",
  "Plants & Garden",
  "Farm & Agricultural Products",
  "Pet Products",
  "On-Site Services & Experiences",
  "Other",
];

const categories = [
  {
    key: "value",
    label: "Booth Value",
    description: "Was the booth fee worthwhile?",
    guidance:
      "Consider the booth fee relative to your sales, exposure, and overall return.",
  },
  {
    key: "traffic",
    label: "Foot Traffic",
    description: "How was customer attendance?",
    guidance:
      "Consider the number of potential customers visiting the event.",
  },
  {
    key: "organization",
    label: "Event Organization",
    description: "How smoothly was the event run?",
    guidance:
      "Consider setup, communication, logistics, and event management.",
  },
  {
    key: "promotion",
    label: "Event Promotion",
    description: "How effectively was the event advertised?",
    guidance:
      "Consider how effectively the organizer advertised and promoted the event.",
  },
  {
    key: "overall",
    label: "Overall Experience",
    description: "How satisfied were you with the event?",
    guidance:
      "Consider your overall satisfaction and whether the event met your expectations.",
  },
] as const;

type CategoryKey = (typeof categories)[number]["key"];
type BoothDuration = "" | "single" | "multi";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export default function ReviewForm({ marketId }: { marketId: string }) {
  const [access, setAccess] = useState<"loading" | "signin" | "verify" | "ready" | "exists" | "error">("loading");
  const [reviewStatus, setReviewStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const submitting = useRef(false);

  useEffect(() => {
    let active = true;
    async function checkAccess() {
      setAccess("loading");
      setError("");
      setSubmitted(false);
      try {
        const supabase = createClient();
        const { data: auth, error: authError } = await supabase.auth.getUser();
        if (authError && authError.name !== "AuthSessionMissingError") throw authError;
        if (!auth.user) {
          if (active) setAccess("signin");
          return;
        }
        const { data: review, error: reviewError } = await supabase
          .from("reviews").select("status")
          .eq("market_id", marketId).eq("vendor_id", auth.user.id).maybeSingle();
        if (reviewError) throw reviewError;
        if (review) {
          if (active) { setReviewStatus(review.status); setAccess("exists"); }
          return;
        }
        const { data: profile, error: profileError } = await supabase
          .from("vendor_profiles").select("verification_status")
          .eq("user_id", auth.user.id).maybeSingle();
        if (profileError) throw profileError;
        if (active) setAccess(profile?.verification_status === "approved" ? "ready" : "verify");
      } catch (cause) {
        console.error("Unable to check review access:", cause);
        if (active) {
          setError("We couldn't check your review access. Please refresh to try again.");
          setAccess("error");
        }
      }
    }
    void checkAccess();
    return () => { active = false; };
  }, [marketId]);
  const [ratings, setRatings] = useState<
    Partial<Record<CategoryKey, number>>
  >({});

  const [selectedVendorCategories, setSelectedVendorCategories] =
    useState<string[]>([]);

  const [otherCategory, setOtherCategory] = useState("");

  // Optional booth fee information
  const [boothCost, setBoothCost] = useState("");
  const [boothDuration, setBoothDuration] =
    useState<BoothDuration>("");
  const [numberOfDays, setNumberOfDays] = useState("");

  const [experience, setExperience] = useState("");
  const [wouldReturn, setWouldReturn] = useState("");
  const [showPreview, setShowPreview] = useState(false);

  const allRated = categories.every(
    (category) => ratings[category.key] !== undefined
  );

  // Validate optional cost
  const hasBoothCost = boothCost.trim() !== "";

  const parsedBoothCost = Number(boothCost);

  const validBoothCost =
    hasBoothCost &&
    Number.isFinite(parsedBoothCost) &&
    parsedBoothCost >= 0 &&
    parsedBoothCost <= 99999999.99 &&
    Math.abs(parsedBoothCost * 100 - Math.round(parsedBoothCost * 100)) < 0.00001;

  // Calculate event duration
  const parsedDays = Number(numberOfDays);

  const validMultiDay =
    boothDuration === "multi" &&
    numberOfDays.trim() !== "" &&
    Number.isInteger(parsedDays) &&
    parsedDays >= 2 && parsedDays <= 2147483647;

  const totalDays =
    boothDuration === "single"
      ? 1
      : validMultiDay
        ? parsedDays
        : null;

  const dailyBoothCost =
    validBoothCost && totalDays !== null
      ? parsedBoothCost / totalDays
      : null;

  function toggleVendorCategory(category: string) {
    setSelectedVendorCategories((previous) =>
      previous.includes(category)
        ? previous.filter((item) => item !== category)
        : [...previous, category]
    );

    setShowPreview(false);
  }

  function handlePreview() {
    if (!allRated || !experience.trim() || !wouldReturn) {
      alert(
        "Please complete all five ratings, your written experience, and the return question before previewing."
      );
      return;
    }

    if (hasBoothCost && !validBoothCost) {
      alert(
        "Please enter a booth cost between $0 and $99,999,999.99 with up to two decimal places, or leave it blank."
      );
      return;
    }

    if (
      boothDuration === "multi" &&
      numberOfDays.trim() !== "" &&
      !validMultiDay
    ) {
      alert(
        "For a multi-day event, enter 2 or more days, or leave the number of days blank."
      );
      return;
    }

    setShowPreview(true);
  }

  async function handleSubmit() {
    if (submitting.current || !showPreview || access !== "ready") return;
    if (!allRated || !experience.trim() || !["Yes", "No", "Maybe"].includes(wouldReturn) ||
      (hasBoothCost && !validBoothCost) ||
      (boothDuration === "multi" && numberOfDays.trim() !== "" && !validMultiDay)) {
      setError("Please check your answers and preview the review again.");
      setShowPreview(false);
      return;
    }
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const supabase = createClient();
      const { data: auth, error: authError } = await supabase.auth.getUser();
      if (authError || !auth.user) {
        setAccess("signin");
        throw new Error("Please sign in again before submitting.");
      }
      const { error: insertError } = await supabase.from("reviews").insert({
        market_id: marketId,
        vendor_id: auth.user.id,
        vendor_categories: selectedVendorCategories,
        other_category: selectedVendorCategories.includes("Other") && otherCategory.trim() ? otherCategory.trim() : null,
        booth_value: ratings.value,
        foot_traffic: ratings.traffic,
        organization: ratings.organization,
        promotion: ratings.promotion,
        overall: ratings.overall,
        booth_cost: hasBoothCost ? parsedBoothCost : null,
        booth_duration: boothDuration || null,
        number_of_days: totalDays,
        experience: experience.trim(),
        would_return: wouldReturn,
      });
      if (insertError) {
        if (insertError.code === "23505") throw new Error("You already have a review for this market. Refresh to see its status.");
        if (insertError.code === "42501") throw new Error("You don't currently have permission to submit. Refresh and check your vendor verification status.");
        throw insertError;
      }
      setReviewStatus("pending");
      setSubmitted(true);
      setAccess("exists");
      setShowPreview(false);
      setExperience("");
    } catch (cause) {
      console.error("Unable to submit review:", cause);
      setError(cause instanceof Error ? cause.message : "We couldn't submit your review. Please try again.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  const displayVendorCategories =
    selectedVendorCategories.map((category) => {
      if (category === "Other" && otherCategory.trim()) {
        return `Other: ${otherCategory.trim()}`;
      }

      return category;
    });

  if (access !== "ready") {
    return (
      <section className="mt-10 border border-[#252521]/20 bg-[#F4F0E6] p-6 text-[#252521] sm:p-10">
        <h3 className="font-serif text-3xl font-bold">Share Your Experience</h3>
        <div className="mt-5 leading-relaxed text-[#55554E]" role="status">
          {access === "loading" && <p>Checking your review access...</p>}
          {access === "signin" && <><p>Sign in before sharing your vendor experience.</p><Link href="/login" className="mt-4 inline-block font-semibold text-[#AD573B] underline">Sign In / Create Account →</Link></>}
          {access === "verify" && <><p>Your vendor account must be approved before submitting reviews.</p><Link href="/verify" className="mt-4 inline-block font-semibold text-[#AD573B] underline">Apply or Check Verification →</Link></>}
          {access === "exists" && <><h4 className="font-serif text-2xl font-bold">{submitted ? "Review received!" : "You have reviewed this market."}</h4><p className="mt-4">{reviewStatus === "pending" ? "Your review is pending moderation and is not public." : reviewStatus === "approved" ? "Your review has been approved. Public review display is being connected next." : "Your review was not approved for publication. Editing and resubmission are not available yet."}</p></>}
        </div>
        {error && <p role="alert" className="mt-5 text-sm text-[#AD573B]">{error}</p>}
      </section>
    );
  }

  return (
    <section className="mt-10 overflow-hidden border border-[#252521]/20 bg-[#F4F0E6] text-[#252521]">
      {/* Header */}
      <div className="bg-[#252521] px-6 py-8 text-[#F4F0E6] sm:px-10">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#D9C6A3]">
          Behind the Booth / Vendor Field Notes
        </p>

        <h3 className="mt-3 font-serif text-3xl font-bold sm:text-4xl">
          Share Your Experience
        </h3>

        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#D9C6A3]">
          A thoughtful review of your market experience
          helps other vendors make informed decisions.
        </p>
      </div>

      <div className="px-5 py-7 sm:px-10">
        <fieldset disabled={busy} className="min-w-0 border-0 p-0">
        <legend className="sr-only">Your market review</legend>
        {/* Demo notice */}
        <div className="mb-8 border-l-2 border-[#AD573B] bg-[#EAE3D5] px-4 py-3">
          <p className="text-xs leading-relaxed text-[#55554E]">
            <strong>Private until approved:</strong> Submissions are saved for
            moderation before publication. Your account name and email will not
            appear publicly. Avoid including identifying details in your review
            if you want to remain anonymous.
          </p>
        </div>

        {/* Vendor categories */}
        <div className="mb-10">
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#AD573B]">
            About Your Business
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h4 className="font-serif text-2xl font-bold">
              What Do You Sell?
            </h4>

            <span className="border border-[#D9C6A3] px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-[#777C60]">
              Optional
            </span>
          </div>

          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#55554E]">
            Help other vendors understand your perspective.
            Select the categories that best describe your
            business. You can choose more than one or skip
            this section entirely.
          </p>

          <div className="mt-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {vendorCategories.map((category) => {
              const selected =
                selectedVendorCategories.includes(category);

              return (
                <label
                  key={category}
                  className={`flex cursor-pointer items-center gap-3 border px-4 py-3 text-sm transition ${
                    selected
                      ? "border-[#AD573B] bg-[#EAE3D5]"
                      : "border-[#D9C6A3] bg-[#FFFDF8] hover:border-[#AD573B]"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() =>
                      toggleVendorCategory(category)
                    }
                    className="h-4 w-4 shrink-0 accent-[#AD573B]"
                  />

                  <span
                    className={
                      selected
                        ? "font-semibold text-[#252521]"
                        : "text-[#55554E]"
                    }
                  >
                    {category}
                  </span>
                </label>
              );
            })}
          </div>

          {selectedVendorCategories.includes("Other") && (
            <div className="mt-5">
              <label
                htmlFor="other-category"
                className="block text-sm font-semibold"
              >
                Please describe your category
                <span className="ml-2 text-xs font-normal text-[#777C60]">
                  (Optional)
                </span>
              </label>

              <input
                id="other-category"
                type="text"
                maxLength={100}
                value={otherCategory}
                onChange={(event) => {
                  setOtherCategory(event.target.value);
                  setShowPreview(false);
                }}
                placeholder="e.g., Books, vintage collectibles..."
                className="mt-3 w-full border border-[#D9C6A3] bg-[#FFFDF8] px-4 py-3 text-sm outline-none focus:border-[#AD573B]"
              />
            </div>
          )}

          <p className="mt-4 text-xs text-[#777C60]">
            {selectedVendorCategories.length === 0
              ? "No categories selected. This section is optional."
              : `${selectedVendorCategories.length} ${
                  selectedVendorCategories.length === 1
                    ? "category"
                    : "categories"
                } selected.`}
          </p>
        </div>

        {/* Rating heading */}
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3 border-t border-[#252521]/15 pt-8">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#AD573B]">
              Market Evaluation
            </p>

            <h4 className="mt-1 font-serif text-xl font-bold">
              Rate Your Experience
            </h4>
          </div>

          <p className="text-xs text-[#777C60]">
            1 = Poor · 5 = Exceptional
          </p>
        </div>

        {/* Rating categories */}
        <div className="divide-y divide-[#252521]/15 border-y border-[#252521]/15">
          {categories.map((category, index) => {
            const selectedRating = ratings[category.key];

            return (
              <fieldset
                key={category.key}
                className="min-w-0 py-6"
              >
                <legend className="sr-only">
                  {category.label}
                </legend>

                <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] lg:items-center lg:gap-8">
                  {/* Category information */}
                  <div className="flex items-start gap-3">
                    <span className="pt-1 text-xs font-bold text-[#AD573B]">
                      {String(index + 1).padStart(2, "0")}
                    </span>

                    <div className="min-w-0">
                      <h5 className="font-serif text-xl font-bold">
                        {category.label}
                      </h5>

                      <p className="mt-2 text-sm font-medium text-[#252521]">
                        {category.description}
                      </p>

                      <p className="mt-2 max-w-sm text-xs leading-relaxed text-[#777C60]">
                        {category.guidance}
                      </p>

                      {/* Booth Cost and Duration */}
                      {category.key === "value" && (
                        <div className="mt-5 space-y-5">
                          {/* Booth Cost */}
                          <div>
                            <label
                              htmlFor="booth-cost"
                              className="block text-xs font-semibold text-[#252521]"
                            >
                              Booth Cost
                              <span className="ml-2 font-normal text-[#777C60]">
                                (Optional)
                              </span>
                            </label>

                            <div className="mt-2 flex max-w-[190px] items-center border border-[#D9C6A3] bg-[#FFFDF8]">
                              <span className="pl-3 text-sm text-[#777C60]">
                                $
                              </span>

                              <input
                                id="booth-cost"
                                type="number"
                                min="0"
                                step="0.01"
                                inputMode="decimal"
                                placeholder="150.00"
                                value={boothCost}
                                onChange={(event) => {
                                  setBoothCost(event.target.value);
                                  setShowPreview(false);
                                }}
                                className="w-full min-w-0 bg-transparent px-3 py-2 text-sm text-[#252521] outline-none"
                              />
                            </div>

                            <p className="mt-2 max-w-xs text-xs leading-relaxed text-[#777C60]">
                              Enter the total amount you paid
                              for your booth, if you&apos;d like
                              to share.
                            </p>
                          </div>

                          {/* Booth Duration */}
                          <div>
                            <p className="text-xs font-semibold text-[#252521]">
                              Booth Duration
                              <span className="ml-2 font-normal text-[#777C60]">
                                (Optional)
                              </span>
                            </p>

                            <p className="mt-2 text-xs leading-relaxed text-[#777C60]">
                              How many days did your booth
                              fee cover?
                            </p>

                            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-3">
                              <label className="flex cursor-pointer items-center gap-2">
                                <input
                                  type="radio"
                                  name="boothDuration"
                                  value="single"
                                  checked={
                                    boothDuration === "single"
                                  }
                                  onChange={() => {
                                    setBoothDuration("single");
                                    setNumberOfDays("");
                                    setShowPreview(false);
                                  }}
                                  className="h-4 w-4 accent-[#AD573B]"
                                />

                                <span className="text-xs font-medium">
                                  Single Day
                                </span>
                              </label>

                              <label className="flex cursor-pointer items-center gap-2">
                                <input
                                  type="radio"
                                  name="boothDuration"
                                  value="multi"
                                  checked={
                                    boothDuration === "multi"
                                  }
                                  onChange={() => {
                                    setBoothDuration("multi");
                                    setShowPreview(false);
                                  }}
                                  className="h-4 w-4 accent-[#AD573B]"
                                />

                                <span className="text-xs font-medium">
                                  Multi-Day
                                </span>
                              </label>
                            </div>

                            {boothDuration !== "" && (
                              <button
                                type="button"
                                onClick={() => {
                                  setBoothDuration("");
                                  setNumberOfDays("");
                                  setShowPreview(false);
                                }}
                                className="mt-3 text-xs text-[#AD573B] underline underline-offset-2 hover:text-[#8F452F]"
                              >
                                Clear duration selection
                              </button>
                            )}

                            {/* Multi-Day input */}
                            {boothDuration === "multi" && (
                              <div className="mt-4">
                                <label
                                  htmlFor="number-of-days"
                                  className="block text-xs font-semibold text-[#252521]"
                                >
                                  Number of Days
                                  <span className="ml-2 font-normal text-[#777C60]">
                                    (Optional)
                                  </span>
                                </label>

                                <input
                                  id="number-of-days"
                                  type="number"
                                  min="2"
                                  step="1"
                                  inputMode="numeric"
                                  placeholder="e.g., 3"
                                  value={numberOfDays}
                                  onChange={(event) => {
                                    setNumberOfDays(
                                      event.target.value
                                    );
                                    setShowPreview(false);
                                  }}
                                  className="mt-2 w-28 border border-[#D9C6A3] bg-[#FFFDF8] px-3 py-2 text-sm outline-none focus:border-[#AD573B]"
                                />
                              </div>
                            )}
                          </div>

                          {/* Daily cost calculation */}
                          {dailyBoothCost !== null && (
                            <div className="max-w-sm border-l-2 border-[#AD573B] bg-[#EAE3D5] px-4 py-3">
                              <p className="text-[10px] font-bold uppercase tracking-wider text-[#777C60]">
                                Estimated Booth Cost Per Day
                              </p>

                              <p className="mt-1 font-serif text-xl font-bold text-[#AD573B]">
                                {currencyFormatter.format(
                                  dailyBoothCost
                                )}
                              </p>

                              <p className="mt-1 text-xs text-[#55554E]">
                                Based on {totalDays}{" "}
                                {totalDays === 1
                                  ? "day"
                                  : "days"}{" "}
                                of participation.
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Rating buttons */}
                  <div>
                    <div className="grid grid-cols-5 gap-1.5 sm:gap-2">
                      {[1, 2, 3, 4, 5].map((score) => {
                        const selected =
                          selectedRating === score;

                        return (
                          <button
                            key={score}
                            type="button"
                            aria-label={`${category.label}: ${score} out of 5, ${ratingLabels[score - 1]}`}
                            aria-pressed={selected}
                            onClick={() => {
                              setRatings((previous) => ({
                                ...previous,
                                [category.key]: score,
                              }));
                              setShowPreview(false);
                            }}
                            className="flex min-w-0 flex-col items-center gap-1.5"
                          >
                            <span
                              className={`flex h-9 w-full items-center justify-center border text-sm font-semibold transition sm:h-10 ${
                                selected
                                  ? "border-[#AD573B] bg-[#AD573B] text-white"
                                  : "border-[#D9C6A3] bg-[#FFFDF8] text-[#252521] hover:border-[#AD573B]"
                              }`}
                            >
                              {score}
                            </span>

                            <span
                              className={`min-h-7 text-center text-[10px] leading-tight sm:text-[11px] ${
                                selected
                                  ? "font-bold text-[#AD573B]"
                                  : "text-[#55554E]"
                              }`}
                            >
                              {ratingLabels[score - 1]}
                            </span>
                          </button>
                        );
                      })}
                    </div>

                    {selectedRating !== undefined && (
                      <p
                        className="mt-2 text-right text-xs font-semibold text-[#AD573B]"
                        aria-live="polite"
                      >
                        Selected: {selectedRating}/5 —{" "}
                        {ratingLabels[selectedRating - 1]}
                      </p>
                    )}
                  </div>
                </div>
              </fieldset>
            );
          })}
        </div>

        {/* Written review */}
        <div className="mt-9">
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#AD573B]">
            Your Field Notes
          </p>

          <label
            htmlFor="experience"
            className="mt-2 block font-serif text-2xl font-bold"
          >
            Tell Us About Your Experience
          </label>

          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#55554E]">
            What went well? What could have been better?
            What should another vendor know before booking?
          </p>

          <textarea
            id="experience"
            rows={4}
            maxLength={2000}
            value={experience}
            onChange={(event) => {
              setExperience(event.target.value);
              setShowPreview(false);
            }}
            placeholder="Share your firsthand experience..."
            className="mt-4 w-full border border-[#D9C6A3] bg-[#FFFDF8] p-4 text-sm leading-relaxed text-[#252521] outline-none transition focus:border-[#AD573B]"
          />

          <p className="mt-1 text-right text-xs text-[#777C60]">
            {experience.length} / 2000 characters
          </p>
        </div>

        {/* Return preference */}
        <fieldset className="mt-7 border-t border-[#252521]/15 pt-7">
          <legend className="font-serif text-xl font-bold">
            Would You Participate Again?
          </legend>

          <p className="mt-2 text-sm text-[#55554E]">
            Based on your overall experience, would you
            return to this market?
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-x-8 gap-y-4">
            {["Yes", "No", "Maybe"].map((option) => (
              <label
                key={option}
                className="flex cursor-pointer items-center gap-2"
              >
                <input
                  type="radio"
                  name="wouldReturn"
                  value={option}
                  checked={wouldReturn === option}
                  onChange={() => {
                    setWouldReturn(option);
                    setShowPreview(false);
                  }}
                  className="h-4 w-4 accent-[#AD573B]"
                />

                <span className="text-sm font-semibold">
                  {option}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        {/* Preview button */}
        <div className="mt-8 flex flex-wrap items-center gap-5 border-t border-[#252521]/15 pt-7">
          <button
            type="button"
            onClick={handlePreview}
            className="heritage-button"
          >
            Preview My Review
          </button>

          <p className="text-xs text-[#777C60]">
            Preview your answers first. Nothing is saved until you submit.
          </p>
        </div>

        {/* Review preview */}
        {showPreview && (
          <div className="mt-10 border border-[#D9C6A3] bg-[#FFFDF8] p-5 sm:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#AD573B]">
              Review Preview — Not Submitted
            </p>

            <h4 className="mt-3 font-serif text-2xl font-bold">
              Your Vendor Field Report
            </h4>

            {/* Vendor category preview */}
            <div className="mt-6">
              <h5 className="font-serif text-lg font-bold">
                Vendor Category
              </h5>

              {displayVendorCategories.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {displayVendorCategories.map((category) => (
                    <span
                      key={category}
                      className="border border-[#D9C6A3] bg-[#EAE3D5] px-3 py-2 text-xs font-semibold text-[#55554E]"
                    >
                      {category}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm italic text-[#777C60]">
                  Not provided (optional).
                </p>
              )}
            </div>

            {/* Booth fee preview */}
            {(validBoothCost || boothDuration !== "") && (
              <div className="mt-7 border-t border-[#252521]/10 pt-6">
                <h5 className="font-serif text-lg font-bold">
                  Booth Fee Information
                </h5>

                {validBoothCost && (
                  <p className="mt-3 text-sm text-[#55554E]">
                    <strong>Booth Cost:</strong>{" "}
                    {currencyFormatter.format(
                      parsedBoothCost
                    )}
                  </p>
                )}

                {boothDuration !== "" && (
                  <p className="mt-2 text-sm text-[#55554E]">
                    <strong>Booth Duration:</strong>{" "}
                    {boothDuration === "single"
                      ? "Single Day"
                      : validMultiDay
                        ? `${parsedDays} Days`
                        : "Multi-Day Event"}
                  </p>
                )}

                {dailyBoothCost !== null && (
                  <p className="mt-2 text-sm font-semibold text-[#AD573B]">
                    Estimated Cost Per Day:{" "}
                    {currencyFormatter.format(
                      dailyBoothCost
                    )}
                  </p>
                )}
              </div>
            )}

            {/* Rating summary */}
            <div className="mt-7 divide-y divide-[#252521]/10 border-y border-[#252521]/10">
              {categories.map((category) => {
                const score = ratings[category.key];

                return (
                  <div
                    key={category.key}
                    className="flex flex-wrap items-center justify-between gap-2 py-3"
                  >
                    <span className="text-sm font-semibold">
                      {category.label}
                    </span>

                    <span className="text-sm font-bold text-[#AD573B]">
                      {score}/5 ·{" "}
                      {score !== undefined
                        ? ratingLabels[score - 1]
                        : ""}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Written review preview */}
            <div className="mt-6">
              <h5 className="font-serif text-lg font-bold">
                Your Experience
              </h5>

              <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[#55554E]">
                {experience}
              </p>

              <p className="mt-5 text-sm">
                <strong>Would participate again:</strong>{" "}
                {wouldReturn}
              </p>
            </div>

            <p className="mt-6 border-t border-[#252521]/10 pt-5 text-xs italic text-[#AD573B]">
              Nothing has been submitted yet. By submitting, you confirm this
              describes your firsthand vendor experience. Your review will be held
              for moderation. Editing after submission is not available yet.
            </p>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={busy}
              className="heritage-button mt-6 disabled:cursor-wait disabled:opacity-50"
            >
              {busy ? "Submitting..." : "Submit for Moderation"}
            </button>
          </div>
        )}
        </fieldset>
        {error && (
          <p role="alert" className="mt-6 border-l-2 border-[#AD573B] bg-[#EAE3D5] p-4 text-sm text-[#AD573B]">
            {error}
          </p>
        )}
      </div>
    </section>
  );
}

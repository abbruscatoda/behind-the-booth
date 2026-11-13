import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Community Guidelines",
  description: "How to share useful firsthand market reviews, protect your privacy, and participate in Behind the Booth.",
};

const guidelines = [
  {
    title: "Share your own experience.",
    text: "Review markets you have personally participated in as a vendor. Describe what you observed, and separate facts from opinions. Include relevant context without guessing about another person’s intentions. Do not submit invented experiences, copied reviews, or reviews on someone else’s behalf.",
  },
  {
    title: "Be specific. Be fair.",
    text: "Positive, mixed, and negative feedback are welcome. Explain your ratings with details about booth value, foot traffic, organization, promotion, and your overall experience. Sales and crowds can vary by date, weather, product, and booth location; your experience may differ from another vendor’s.",
  },
  {
    title: "Critique the experience respectfully.",
    text: "Focus on the event and how it was run. Harassment, threats, hate speech, personal attacks, and unsupported accusations are not appropriate. A low rating or a critical opinion alone is not a reason to reject a review.",
  },
  {
    title: "Protect your privacy and other people’s.",
    text: "Public reviews do not display your account name or email. However, your writing, product category, booth costs, or event details may identify you. Avoid names, phone numbers, private messages, order details, and other identifying information you do not want published. Vendor verification information is separate from the public review.",
  },
  {
    title: "Keep ratings independent.",
    text: "Do not review your own market or an event you organize, work for, or have a financial stake in beyond participating as a vendor. Do not offer or accept payment, gifts, or discounts in exchange for a review. Do not use extra accounts to influence ratings or submit duplicate reviews.",
  },
  {
    title: "Help keep the directory useful.",
    text: "Suggest real markets with an official event or organizer link when possible. Check the directory first to avoid duplicates. Keep descriptions factual and avoid unverified schedules, fees, or promotional claims. A suggestion is reviewed before it becomes a public listing.",
  },
];

export default function CommunityGuidelinesPage() {
  return (
    <main className="mx-auto w-full max-w-5xl px-6 py-14 md:py-20">
      <header className="max-w-3xl">
        <p className="heritage-label">Built on shared experience</p>
        <h1 className="heritage-heading mt-5 text-4xl md:text-6xl">Good information starts with a thoughtful community.</h1>
        <p className="mt-6 text-lg leading-relaxed text-[#55554E]">Behind the Booth helps vendors make informed decisions before booking a market. These guidelines keep reviews useful, independent, and respectful.</p>
      </header>

      <div className="mt-10 border-l-4 border-[#07472B] bg-[#E9E7DA] p-6">
        <p className="font-semibold text-[#07472B]">Honest feedback belongs here.</p>
        <p className="mt-2 leading-relaxed text-[#55554E]">You do not need to have loved an event to review it. Share what happened, explain your perspective, and give other vendors information they can use.</p>
      </div>

      <section aria-label="Review and participation guidelines" className="mt-10 grid gap-5 md:grid-cols-2">
        {guidelines.map((guideline, index) => (
          <article key={guideline.title} className="heritage-card">
            <p aria-hidden="true" className="text-sm font-bold tracking-widest text-[#07472B]">{String(index + 1).padStart(2, "0")}</p>
            <h2 className="mt-4 font-serif text-2xl font-bold">{guideline.title}</h2>
            <p className="mt-4 leading-relaxed text-[#55554E]">{guideline.text}</p>
          </article>
        ))}
      </section>

      <section aria-labelledby="moderation-heading" className="mt-12 border-t border-[#252521]/20 pt-10">
        <p className="heritage-label">Before a review goes live</p>
        <h2 id="moderation-heading" className="heritage-heading mt-4 text-3xl">How moderation works.</h2>
        <div className="mt-5 space-y-4 leading-relaxed text-[#55554E]">
          <p>Review submission requires an approved vendor account. Submitted reviews enter a moderation queue and appear publicly only after approval. Pending and rejected reviews are excluded from published rating summaries.</p>
          <p>We assess submissions against these guidelines. Verification and moderation help us evaluate submissions; they do not guarantee that every statement is accurate or that every vendor will have the same experience.</p>
          <p>Submissions that break these guidelines may be rejected. To question a moderation decision, flag a privacy concern, or request a correction, email us with the market link and a brief explanation. Please avoid sending sensitive documents in your initial message.</p>
        </div>
      </section>

      <section aria-labelledby="contact-heading" className="heritage-card mt-10">
        <h2 id="contact-heading" className="font-serif text-2xl font-bold">Something needs a closer look?</h2>
        <p className="mt-3 leading-relaxed text-[#55554E]">Contact Behind the Booth about a review, listing, or community concern.</p>
        <a href="mailto:behindtheboothhq@gmail.com" className="mt-4 inline-block break-all font-semibold text-[#07472B] underline underline-offset-4">behindtheboothhq@gmail.com</a>
      </section>

      <div className="mt-10 flex flex-wrap gap-6">
        <Link href="/markets" className="heritage-button">Explore Markets →</Link>
        <Link href="/verify" className="self-center font-semibold text-[#07472B] underline underline-offset-4">Learn about vendor verification</Link>
      </div>
    </main>
  );
}

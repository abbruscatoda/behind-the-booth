import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Contact",
  description: "Contact Behind the Booth about account support, market corrections, reviews, or privacy requests.",
};

const topics = [
  { title: "Account help", subject: "Account support", description: "Having trouble signing in or checking your vendor application? Tell us what happened and the error message you saw." },
  { title: "Market corrections", subject: "Market listing correction", description: "Send the listing link, the detail that needs changing, and an official source when available." },
  { title: "Review or moderation concerns", subject: "Review or moderation concern", description: "Include the market link and enough detail to identify the review or decision. Explain the concern without sharing private documents." },
  { title: "Privacy requests", subject: "Privacy request", description: "Request access, corrections, or deletion of your information. If possible, write from your account email so we can verify ownership." },
];

export default function ContactPage() {
  return (
    <main className="mx-auto w-full max-w-5xl px-6 py-14 md:py-20">
      <header className="max-w-3xl">
        <p className="heritage-label">Let’s keep the information useful</p>
        <h1 className="heritage-heading mt-5 text-4xl md:text-6xl">Get in touch.</h1>
        <p className="mt-6 text-lg leading-relaxed text-[#55554E]">Questions, corrections, and community concerns help us make Behind the Booth better for vendors across Raleigh and the Triangle.</p>
      </header>
      <div className="heritage-card mt-9">
        <h2 className="font-serif text-2xl font-bold">Email Behind the Booth</h2>
        <a href="mailto:behindtheboothhq@gmail.com" className="mt-4 inline-block break-all text-lg font-semibold text-[#07472B] underline underline-offset-4">behindtheboothhq@gmail.com</a>
        <p className="mt-4 leading-relaxed text-[#55554E]">The links below open your email app with a suggested subject. If no app opens, copy the address and send your message from Gmail or your preferred email service.</p>
      </div>
      <section aria-label="Contact topics" className="mt-6 grid gap-5 md:grid-cols-2">
        {topics.map(topic => (
          <article key={topic.subject} className="heritage-card flex flex-col">
            <h2 className="font-serif text-2xl font-bold">{topic.title}</h2>
            <p className="mt-4 flex-1 leading-relaxed text-[#55554E]">{topic.description}</p>
            <a href={`mailto:behindtheboothhq@gmail.com?subject=${encodeURIComponent(topic.subject)}`} className="mt-6 self-start font-semibold text-[#07472B] underline underline-offset-4">Email about this →</a>
          </article>
        ))}
      </section>
      <aside className="mt-8 border-l-4 border-[#07472B] bg-[#E9E7DA] p-6">
        <h2 className="font-semibold text-[#07472B]">A quick note about privacy</h2>
        <p className="mt-2 leading-relaxed text-[#55554E]">Never email passwords, confirmation or reset links, API keys, payment information, or sensitive identity documents. Crop or cover private details in screenshots before sending them.</p>
      </aside>
      <section aria-labelledby="suggest-heading" className="mt-10 border-t border-[#252521]/20 pt-8">
        <h2 id="suggest-heading" className="font-serif text-2xl font-bold">Know a market we’re missing?</h2>
        <p className="mt-3 leading-relaxed text-[#55554E]">Use the suggestion form to send a market to our moderation queue. You’ll need to sign in first.</p>
        <div className="mt-6 flex flex-wrap gap-6">
          <Link href="/suggest-market" className="heritage-button">Suggest a Market →</Link>
          <Link href="/privacy" className="self-center font-semibold text-[#07472B] underline underline-offset-4">Read our privacy notice</Link>
        </div>
      </section>
    </main>
  );
}

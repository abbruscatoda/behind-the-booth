import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Notice",
  description: "How Behind the Booth uses account information, vendor verification details, reviews, and essential sign-in cookies.",
};

export default function PrivacyPage() {
  return (
    <main className="mx-auto w-full max-w-4xl px-6 py-14 md:py-20">
      <header>
        <p className="heritage-label">Your information, explained</p>
        <h1 className="heritage-heading mt-5 text-4xl md:text-6xl">Privacy notice.</h1>
        <p className="mt-5 text-sm text-[#626C57]">Last updated November 12, 2026</p>
        <p className="mt-6 text-lg leading-relaxed text-[#55554E]">This notice describes how Behind the Booth uses information when you browse markets, create an account, apply for vendor verification, submit content, or contact us at www.behindtheboothhq.com.</p>
      </header>

      <aside className="mt-8 border-l-4 border-[#07472B] bg-[#E9E7DA] p-6">
        <h2 className="font-serif text-2xl font-bold">Private account. Thoughtful sharing.</h2>
        <p className="mt-3 leading-relaxed text-[#55554E]">Published reviews omit your account name and email, but they are linked to your account internally. Details you include in a review may identify you. Please share only what you are comfortable making available to others.</p>
      </aside>

      <div className="mt-10 space-y-9 text-[#55554E] [&_h2]:font-serif [&_h2]:text-2xl [&_h2]:font-bold [&_h2]:text-[#252521] [&_p]:mt-3 [&_p]:leading-relaxed [&_li]:leading-relaxed">
        <section aria-labelledby="collected"><h2 id="collected">1. Information we collect</h2>
          <ul className="mt-4 list-disc space-y-3 pl-5">
            <li><strong>Account information:</strong> your email address, account identifier, authentication records, and account status. Supabase Auth handles password authentication; please never send us your password by email.</li>
            <li><strong>Vendor applications:</strong> your business name, business link, verification notes, application status, and submission time.</li>
            <li><strong>Reviews:</strong> ratings, written experience, willingness to return, and optional product categories and booth cost or duration details, along with the market, submitting account, moderation status, and submission time.</li>
            <li><strong>Market suggestions:</strong> market name, location, website, optional notes, submitting account, submission time, and moderation status.</li>
            <li><strong>Messages:</strong> your email address and anything you choose to send when you contact us.</li>
            <li><strong>Technical information:</strong> hosting, authentication, and email providers may process IP addresses, browser or device information, request times, errors, and delivery or security logs to operate and protect the service.</li>
          </ul>
        </section>
        <section aria-labelledby="purpose"><h2 id="purpose">2. How we use information</h2>
          <p>We use information to operate accounts, verify vendors, moderate submissions, publish market information and approved reviews, calculate rating summaries, prevent abuse, troubleshoot problems, respond to requests, and send account-related emails and admin notifications.</p>
        </section>
        <section aria-labelledby="visibility"><h2 id="visibility">3. What other people can see</h2>
          <p>Market listings and summary ratings are available without an account. Signed-in members can access approved review details, including the text, ratings, submission date, and any optional category or booth details provided. These details may also contribute to aggregate reports.</p>
          <p>Account email addresses, private vendor application details, and private market suggestion notes are not included in published reviews or market listings. Site administrators can access submission and account information needed for verification, support, and moderation. Approved market suggestions become listings with public market details.</p>
          <p>Access restrictions cannot prevent someone who can view content from copying or sharing it. Avoid including personal contact details, private messages, or sensitive information in a review.</p>
        </section>
        <section aria-labelledby="providers"><h2 id="providers">4. Providers and other disclosures</h2>
          <p>We use Vercel to host the website, Supabase for authentication and database services, Resend for transactional email delivery, and Gmail for support messages and the admin notification inbox. They process information needed to provide those services. For example, account emails require your recipient address, and support messages are handled through Gmail.</p>
          <p>We may also disclose information when required by law or when necessary to investigate abuse, protect the service, or protect people’s rights or safety. Provider processing and storage may occur outside your state or country.</p>
        </section>
        <section aria-labelledby="cookies"><h2 id="cookies">5. Cookies and tracking</h2>
          <p>We use essential authentication cookies to keep you signed in and complete confirmation and password-reset flows. Blocking or deleting these cookies can interrupt those features. You can browse public market information without creating an account.</p>
          <p>We have not enabled advertising trackers, additional audience analytics, or email open/click tracking. Operational and security logs still exist. Links to market websites and other external services take you to sites with their own privacy practices.</p>
        </section>
        <section aria-labelledby="retention"><h2 id="retention">6. Storage and retention</h2>
          <p>Accounts and submitted content currently remain stored unless removed through an administrative process; the site does not have automatic account or submission expiry. Moderation records, support correspondence, and provider logs or backups may have different retention periods. We use these records to operate the service, address disputes, and investigate abuse.</p>
          <p>If you want information removed, contact us. We will review what can be deleted, what content is affected, and whether any records need to be retained for security or legal reasons. Deletion from active systems does not necessarily remove information immediately from provider backups or copies others have made.</p>
        </section>
        <section aria-labelledby="choices"><h2 id="choices">7. Questions, corrections, and deletion requests</h2>
          <p>Email <a href="mailto:behindtheboothhq@gmail.com?subject=Privacy%20request" className="break-all font-semibold text-[#07472B] underline underline-offset-4">behindtheboothhq@gmail.com</a> to request access to, correction of, or deletion of your information or account. When possible, write from the email associated with your account. We may need to verify ownership before acting.</p>
          <p>There is currently no self-service account deletion button. Please identify the affected account, review, or listing, but do not include passwords, reset links, government identification, or payment information in your initial message.</p>
        </section>
        <section aria-labelledby="security"><h2 id="security">8. Security</h2>
          <p>We use authenticated access and database permissions to restrict private information and moderation tools. No internet service can guarantee absolute security or anonymity. If you believe your account or information has been compromised, contact us without sharing login credentials.</p>
        </section>
        <section aria-labelledby="children"><h2 id="children">9. Children</h2>
          <p>Behind the Booth is a resource for vendors and is not directed to children under 13. If you believe a child under 13 has submitted personal information, contact us so we can investigate and address it.</p>
        </section>
        <section aria-labelledby="changes"><h2 id="changes">10. Changes to this notice</h2>
          <p>We will update this page and its date when our practices change. If a change requires additional notice or permission, we will provide it as appropriate.</p>
        </section>
      </div>
      <div className="mt-12 flex flex-wrap gap-6 border-t border-[#252521]/20 pt-8">
        <Link href="/contact" className="heritage-button">Contact Behind the Booth →</Link>
        <Link href="/community-guidelines" className="self-center font-semibold text-[#07472B] underline underline-offset-4">Community Guidelines</Link>
      </div>
    </main>
  );
}

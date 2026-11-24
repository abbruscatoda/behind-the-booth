import { pageMetadata } from "../lib/siteMetadata";
import Link from "next/link";
import Image from "next/image";
import marketPhoto from "../assets/photos/community-market.jpg";

export const metadata = pageMetadata(
  "Market reviews and vendor opportunities",
  "Read firsthand vendor reviews, rate markets you’ve attended, and find upcoming markets and events accepting vendor applications around Raleigh and the Triangle.",
  "/"
);

const features = [
  {
    number: "01",
    title: "Explore Markets",
    description:
      "Explore local markets, festivals, and pop-ups. Read vendor reviews about booth fees, foot traffic, organization, and the overall experience.",
    href: "/markets",
    linkLabel: "Explore the directory",
  },
  {
    number: "02",
    title: "Share Your Experience",
    description:
      "Rate and review markets you’ve attended. Help fellow vendors make informed decisions with firsthand insight from behind the booth.",
    href: "/markets",
    linkLabel: "Find a market to review",
  },
  {
    number: "03",
    title: "Find Vendor Opportunities",
    description:
      "Discover upcoming markets and special events accepting vendor applications. Check dates and fees, read past reviews, and apply directly with the organizer.",
    href: "/opportunities",
    linkLabel: "Find your next opportunity",
  },
];

export default function Home() {
  return (
    <main className="flex-1 bg-[#F4F0E6] text-[#252521]">
      {/* Hero */}
      <section className="brand-home-hero mx-auto max-w-6xl px-6">
        <div className="brand-hero-grid">
          <div>
            <div className="mb-5">
              <p className="brand-eyebrow">
                The Vendor&apos;s Field Guide
              </p>
            </div>

            <h1 className="heritage-heading brand-hero-title">
              Know the market.
              <br />
              <span className="brand-hero-emphasis">
                Before you book
              </span>
              <br />
              the booth.
            </h1>

            <div className="mt-6 max-w-xl">
              <p className="text-base leading-relaxed text-[#55554E] md:text-lg">
                Read firsthand vendor reviews, share what you&apos;ve learned,
                and find local markets accepting applications. Made for the
                Raleigh and Triangle vendor community.
              </p>
            </div>

            <p className="mt-4 text-sm font-medium leading-relaxed text-[#07472B]">Free to join. Verified vendors. Publicly anonymous reviews.</p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Link href="/markets" className="heritage-button">
                Explore Markets <span aria-hidden="true">→</span>
              </Link>

              <Link
                href="/opportunities"
                className="brand-secondary-button"
              >
                Find Vendor Opportunities
              </Link>
            </div>

            <a
              href="#about"
              className="mt-4 inline-flex min-h-11 items-center text-sm font-medium text-[#07472B] underline underline-offset-4"
            >
              Learn Our Story
            </a>
          </div>

          <figure>
            <Image
              src={marketPhoto}
              alt="Handmade goods displayed under white market tents, with shoppers and trees in the background."
              sizes="(max-width: 899px) 100vw, 520px"
              className="brand-hero-photo"
              preload
            />
            <figcaption className="brand-photo-credit">Market photography by <a href="https://www.pexels.com/photo/market-stall-tents-15807347/" target="_blank" rel="noopener noreferrer">Connor Scott McManus / Pexels<span className="sr-only"> (opens in a new tab)</span></a></figcaption>
          </figure>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-[#252521]/15 pt-4 text-xs text-[#626C57]">
          <span>Rooted in Raleigh, North Carolina</span>
          <span>Built for independent vendors</span>
        </div>
      </section>

      {/* Features */}
      <section className="brand-feature-section">
        <div className="mx-auto max-w-6xl">
          <h2 className="brand-feature-title">For your next market, and the one after that.</h2>

          <p className="mt-3 max-w-2xl text-base leading-relaxed text-[#55554E]">
            Learn from vendors who&apos;ve been there, share what
            you know, and discover where to set up next.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.number}
                className="brand-feature-card"
              >
                <span className="mb-4 text-xs font-medium text-[#626C57]">
                  {feature.number}
                </span>

                <h3 className="font-serif text-2xl text-[#07472B]">
                  {feature.title}
                </h3>

                <p className="mt-3 text-sm leading-relaxed text-[#55554E]">
                  {feature.description}
                </p>

                <div className="mt-auto pt-4">
                  <Link
                    href={feature.href}
                    className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[#07472B] underline underline-offset-4"
                  >
                    {feature.linkLabel}
                    <span aria-hidden="true">→</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Mission */}
      <section
        id="about"
        className="brand-mission mx-auto grid max-w-6xl gap-8 px-6 py-12 md:grid-cols-2 md:py-16"
      >
        <div>
          <p className="mb-4 heritage-label">
            Behind the Mission
          </p>

          <h2 className="brand-mission-title font-serif text-3xl leading-tight text-[#07472B] md:text-4xl">
            Because your time, money, and hard work matter.
          </h2>
        </div>

        <div className="flex flex-col justify-center">
          <p className="text-lg leading-relaxed text-[#55554E]">
            Choosing the right market shouldn&apos;t feel like a
            gamble. Behind the Booth gives independent vendors a
            place to share firsthand experiences, learn from one
            another, and make more informed decisions before
            paying for their next booth.
          </p>

          <p className="mt-6 text-lg leading-relaxed text-[#55554E]">
            Our vendor opportunity board helps you take the next
            step: discover upcoming markets and special events,
            explore application details, and apply directly with
            the organizer.
          </p>

          <p className="mt-6 text-lg leading-relaxed text-[#55554E]">
            Starting in Raleigh and the Triangle, our goal is to
            create a trusted community resource shaped by the
            people who know these markets best: the vendors.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-4">
            <Link
              href="/markets"
              className="border-b border-[#07472B] pb-2 text-sm font-bold text-[#07472B]"
            >
              Explore Markets →
            </Link>

            <Link
              href="/opportunities"
              className="border-b border-[#07472B] pb-2 text-sm font-bold text-[#07472B]"
            >
              Find Vendor Opportunities →
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

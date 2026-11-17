import { pageMetadata } from "../lib/siteMetadata";
import Link from "next/link";
import Image from "next/image";
import greenIcon from "../assets/brand/icon-green.png";

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
      <section className="brand-home-hero mx-auto max-w-6xl px-6 pb-14 pt-14 md:pb-20 md:pt-20">
        <div className="brand-hero-grid">
          <div>
            <div className="mb-7 flex items-center gap-4">
              <span className="h-px w-10 bg-[#AD573B]" />
              <p className="heritage-label">
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

            <div className="mt-7 max-w-xl border-l-2 border-[#AD573B] pl-5">
              <p className="text-base leading-relaxed text-[#55554E] md:text-lg">
                Every booth has a story. Read firsthand vendor reviews,
                rate markets you&apos;ve attended, and find your next
                place to sell. Discover upcoming markets and events
                accepting vendor applications around Raleigh and the
                Triangle.
              </p>
            </div>

            <p className="mt-5 text-sm font-semibold text-[#07472B]">Verified vendors. Publicly anonymous reviews.</p>

            <div className="mt-6 flex flex-wrap items-center gap-4">
              <Link href="/markets" className="heritage-button">
                Explore Markets <span aria-hidden="true">→</span>
              </Link>

              <Link
                href="/opportunities"
                className="inline-flex min-h-12 items-center justify-center gap-3 rounded-sm border border-[#07472B] px-6 py-4 text-center text-xs font-bold uppercase tracking-wider text-[#07472B] transition-colors hover:bg-[#E9E7DA]"
              >
                Find Vendor Opportunities
                <span aria-hidden="true">→</span>
              </Link>
            </div>

            <a
              href="#about"
              className="mt-5 inline-block border-b border-[#07472B] pb-1 text-xs font-bold uppercase tracking-wider text-[#07472B]"
            >
              Learn Our Story
            </a>
          </div>

          <div className="brand-emblem-panel" aria-hidden="true">
            <Image
              src={greenIcon}
              alt=""
              sizes="200px"
              className="brand-emblem"
              priority
            />
            <p className="brand-emblem-caption">Behind the Booth</p>
            <span className="brand-emblem-rule" />
            <p className="brand-emblem-text">
              Good markets start with shared experience.
            </p>
          </div>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-[#252521]/20 pt-5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#626C57] sm:text-xs">
          <span>Rooted in Raleigh, North Carolina</span>
          <span>Built for independent vendors</span>
        </div>
      </section>

      {/* Features */}
      <section className="border-y border-[#252521]/20 bg-[#E9E7DA] px-6 py-16 md:py-20">
        <div className="mx-auto max-w-6xl">
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.25em] text-[#07472B]">
            Your Next Market Starts Here
          </p>

          <h2 className="max-w-3xl font-serif text-4xl font-bold leading-tight md:text-5xl">
            Shared experience.
            <br />
            New opportunities.
          </h2>

          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[#55554E]">
            Learn from vendors who&apos;ve been there, share what
            you know, and discover where to set up next.
          </p>

          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.number}
                className="flex flex-col border border-[#252521]/20 bg-[#F4F0E6] p-8"
              >
                <span className="font-serif text-3xl italic text-[#07472B]">
                  {feature.number}
                </span>

                <div className="my-6 h-px bg-[#252521]/20" />

                <h3 className="font-serif text-2xl font-bold">
                  {feature.title}
                </h3>

                <p className="mt-4 leading-relaxed text-[#55554E]">
                  {feature.description}
                </p>

                <div className="mt-auto pt-6">
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
        className="mx-auto grid max-w-6xl gap-10 px-6 py-16 md:grid-cols-2 md:py-24"
      >
        <div>
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.25em] text-[#07472B]">
            Behind the Mission
          </p>

          <h2 className="font-serif text-4xl font-bold leading-tight md:text-5xl">
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
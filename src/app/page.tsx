import Link from "next/link";
import Image from "next/image";
import greenIcon from "../assets/brand/icon-green.png";

const features = [
  {
    number: "01",
    title: "Discover Markets",
    description:
      "Explore markets, festivals, and pop-ups around Raleigh and the Triangle.",
  },
  {
    number: "02",
    title: "Learn From Vendors",
    description:
      "Find firsthand insights about booth fees, foot traffic, organization, and event quality.",
  },
  {
    number: "03",
    title: "Make Better Decisions",
    description:
      "Spend less time guessing and more time finding opportunities worth your investment.",
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
              <p className="heritage-label">The Vendor&apos;s Field Guide</p>
            </div>
            <h1 className="heritage-heading brand-hero-title">
              Know the market.<br />
              <span className="brand-hero-emphasis">Before you book</span><br />
              the booth.
            </h1>
            <div className="mt-7 max-w-xl border-l-2 border-[#AD573B] pl-5">
              <p className="text-base leading-relaxed text-[#55554E] md:text-lg">Every booth has a story. Discover local markets, learn from fellow vendors, and make informed decisions before investing in your next event.</p>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-5">
              <Link href="/markets" className="heritage-button">Explore Markets <span aria-hidden="true">→</span></Link>
              <a href="#about" className="border-b border-[#07472B] pb-1 text-xs font-bold uppercase tracking-wider text-[#07472B]">Learn Our Story</a>
            </div>
          </div>
          <div className="brand-emblem-panel" aria-hidden="true">
            <Image src={greenIcon} alt="" sizes="200px" className="brand-emblem" priority />
            <p className="brand-emblem-caption">Behind the Booth</p>
            <span className="brand-emblem-rule" />
            <p className="brand-emblem-text">Good markets start with shared experience.</p>
          </div>
        </div>
        <div className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-[#252521]/20 pt-5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#626C57] sm:text-xs">
          <span>Rooted in Raleigh, North Carolina</span>
          <span>Built for independent vendors</span>
        </div>
      </section>

      {/* Feature section */}
      <section className="border-y border-[#252521]/20 bg-[#E9E7DA] px-6 py-16 md:py-20">
        <div className="mx-auto max-w-6xl">
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.25em] text-[#07472B]">
            What We&apos;re Building
          </p>

          <h2 className="max-w-3xl font-serif text-4xl font-bold leading-tight md:text-5xl">
            Better information.
            <br />
            Better markets.
          </h2>

          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.number}
                className="border border-[#252521]/20 bg-[#F4F0E6] p-8"
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
            gamble. Behind the Booth is being built to give
            independent vendors a place to share experiences,
            discover opportunities, and support one another.
          </p>

          <p className="mt-6 text-lg leading-relaxed text-[#55554E]">
            Starting in Raleigh and the Triangle, our goal is
            to create a trusted community resource shaped by
            the people who know these markets best: the vendors.
          </p>

          <Link
            href="/markets"
            className="mt-8 self-start border-b border-[#07472B] pb-2 text-sm font-bold uppercase tracking-wider text-[#07472B]"
          >
            Browse the Directory →
          </Link>
        </div>
      </section>

      
      
    </main>
  );
}
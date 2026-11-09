
import Link from "next/link";

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
    <main className="min-h-screen bg-[#F4F0E6] text-[#252521]">
      {/* Announcement bar */}
      <div className="bg-[#252521] px-5 py-3 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[#F4F0E6]">
        An independent resource for the vendor community
      </div>

      {/* Navigation */}
      <header className="border-b border-[#252521]/20">
        <nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-5 px-6 py-7">
          <Link
            href="/"
            className="font-serif text-2xl font-black tracking-tight md:text-3xl"
          >
            Behind the Booth<span className="text-[#AD573B]">.</span>
          </Link>

          <div className="flex items-center gap-7 text-sm font-semibold">
            <Link href="/markets" className="hover:text-[#AD573B]">
              Explore Markets
            </Link>
            <a href="#about" className="hover:text-[#AD573B]">
              Our Mission
            </a>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 pb-24 pt-20 md:pb-32 md:pt-28">
        <div className="mb-8 flex items-center gap-4">
          <span className="h-px w-12 bg-[#AD573B]" />
          <p className="text-xs font-bold uppercase tracking-[0.25em] text-[#AD573B]">
            The Vendor&apos;s Field Guide
          </p>
        </div>

        <h1 className="max-w-5xl font-serif text-5xl font-bold leading-[1.08] tracking-tight md:text-7xl lg:text-8xl">
          Know the market.
          <br />
          <span className="italic text-[#AD573B]">
            Before you book
          </span>
          <br />
          the booth.
        </h1>

        <div className="mt-10 max-w-2xl border-l-2 border-[#AD573B] pl-6">
          <p className="text-lg leading-relaxed text-[#55554E] md:text-xl">
            Every booth has a story. Discover local markets, learn
            from fellow vendors, and make informed decisions before
            investing in your next event.
          </p>
        </div>

        <div className="mt-12 flex flex-wrap items-center gap-6">
          <Link
            href="/markets"
            className="inline-flex items-center gap-3 rounded-sm bg-[#AD573B] px-8 py-4 text-sm font-bold uppercase tracking-wider text-white transition hover:bg-[#8D422C]"
          >
            Explore Markets <span aria-hidden="true">→</span>
          </Link>

          <a
            href="#about"
            className="border-b border-[#252521] pb-1 text-sm font-bold uppercase tracking-wider hover:text-[#AD573B]"
          >
            Learn Our Story
          </a>
        </div>

        <div className="mt-24 flex flex-wrap items-center justify-between gap-4 border-t border-[#252521]/25 pt-5 text-xs font-semibold uppercase tracking-[0.16em] text-[#777C60]">
          <span>Rooted in Raleigh, North Carolina</span>
          <span>Built for independent vendors</span>
        </div>
      </section>

      {/* Feature section */}
      <section className="border-y border-[#252521]/20 bg-[#EAE3D5] px-6 py-24">
        <div className="mx-auto max-w-6xl">
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.25em] text-[#AD573B]">
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
                <span className="font-serif text-3xl italic text-[#AD573B]">
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
        className="mx-auto grid max-w-6xl gap-12 px-6 py-24 md:grid-cols-2 md:py-32"
      >
        <div>
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.25em] text-[#AD573B]">
            Behind the Mission
          </p>

          <h2 className="font-serif text-4xl font-bold leading-tight md:text-5xl">
            Because your time,
            money, and hard work
            matter.
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
            className="mt-8 self-start border-b border-[#AD573B] pb-2 text-sm font-bold uppercase tracking-wider text-[#AD573B]"
          >
            Browse the Directory →
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#252521] px-6 py-12 text-[#F4F0E6]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6">
          <div>
            <p className="font-serif text-2xl font-bold">
              Behind the Booth.
            </p>
            <p className="mt-2 text-sm text-[#C7C0B3]">
              A better view from behind the booth.
            </p>
          </div>

          <div className="text-sm text-[#C7C0B3]">
            © 2026 Behind the Booth.
            <br />
            Raleigh, North Carolina
          </div>
        </div>
      </footer>
    </main>
  );
}

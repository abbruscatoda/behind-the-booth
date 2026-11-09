
export default function Home() {
  return (
    <main className="min-h-screen bg-[#111111] text-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="text-2xl font-black tracking-tight">
          BEHIND<span className="text-orange-400">THE</span>BOOTH.
        </div>
        <span className="text-sm text-gray-400">
          Built for vendors, by vendors.
        </span>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-28">
        <div className="mb-6 inline-block rounded-full border border-orange-400/40 px-4 py-2 text-sm text-orange-300">
          Coming soon to Raleigh &amp; the Triangle
        </div>

        <h1 className="max-w-4xl text-5xl font-black leading-tight tracking-tight md:text-7xl">
          Know the market.
          <br />
          <span className="text-orange-400">
            Before you book the booth.
          </span>
        </h1>

        <p className="mt-8 max-w-2xl text-xl leading-relaxed text-gray-400">
          Real experiences from real vendors. Discover local markets,
          read honest reviews, and make smarter decisions before
          spending money on your next event.
        </p>

        <div className="mt-10 flex flex-wrap gap-4">
          <a
            href="/markets"
            className="rounded-lg bg-orange-400 px-7 py-4 font-bold text-black transition hover:bg-orange-300"
          >
            Explore Markets
          </a>
          <a
            href="mailto:hello@example.com"
            className="rounded-lg border border-gray-600 px-7 py-4 font-bold transition hover:border-white"
          >
            Get in touch
          </a>
        </div>
      </section>

      <section
        id="how-it-works"
        className="border-t border-gray-800 bg-[#191919] px-6 py-20"
      >
        <div className="mx-auto max-w-6xl">
          <h2 className="mb-12 text-3xl font-bold">
            Your booth fee deserves better information.
          </h2>

          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                title: "Discover Markets",
                description:
                  "Find markets, festivals, and pop-ups around the Triangle.",
              },
              {
                title: "Read Vendor Reviews",
                description:
                  "Learn about foot traffic, organization, booth fees, and vendor experiences.",
              },
              {
                title: "Share Your Experience",
                description:
                  "Help other vendors make informed decisions through honest feedback.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="rounded-xl border border-gray-700 bg-[#222222] p-8"
              >
                <h3 className="mb-4 text-xl font-bold text-orange-400">
                  {item.title}
                </h3>
                <p className="leading-relaxed text-gray-400">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="px-6 py-10 text-center text-sm text-gray-500">
        © 2026 Behind the Booth.
        Made for the vendor community.
      </footer>
    </main>
  );
}

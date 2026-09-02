const domains = [
  "World and Geopolitics",
  "U.S. Economy and Policy",
  "Markets and Rates",
  "Companies and Earnings",
  "Housing and Real Estate",
  "Commodities and Energy",
  "Technology and AI",
  "Banking and Credit",
  "Consumer and Labor",
  "Regulation and Legal",
];

export default function Home() {
  return (
    <main className="min-h-screen bg-paper text-ink">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-10 px-6 py-10">
        <header className="flex flex-col gap-3 border-b border-ink/10 pb-6">
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-signal">
            Phase 2 Scaffold
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight">
            InvestorAgent market intelligence workspace
          </h1>
          <p className="max-w-3xl text-base leading-7 text-ink/70">
            The first scaffold is ready for the dashboard, source manager,
            watchlist, agent chat, and settings screens.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-ink/10 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Backend</h2>
            <p className="mt-2 text-sm leading-6 text-ink/70">
              FastAPI service with a health endpoint and configuration module.
            </p>
          </div>
          <div className="rounded-lg border border-ink/10 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Frontend</h2>
            <p className="mt-2 text-sm leading-6 text-ink/70">
              Next.js and TypeScript shell for the local dashboard experience.
            </p>
          </div>
          <div className="rounded-lg border border-ink/10 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Guardrails</h2>
            <p className="mt-2 text-sm leading-6 text-ink/70">
              Research-only framing remains a product requirement from day one.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold">V1 News Domains</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {domains.map((domain) => (
              <div
                key={domain}
                className="rounded-md border border-ink/10 bg-white px-4 py-3 text-sm font-medium shadow-sm"
              >
                {domain}
              </div>
            ))}
          </div>
        </section>

        <footer className="mt-auto border-t border-ink/10 pt-6 text-sm leading-6 text-ink/65">
          This is not financial advice. InvestorAgent is for research and
          educational purposes only.
        </footer>
      </section>
    </main>
  );
}

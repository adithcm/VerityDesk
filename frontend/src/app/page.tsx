"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const FINANCIAL_DISCLAIMER =
  "This is not financial advice. InvestorAgent is for research and educational purposes only. Investing involves risk.";

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

const navigation = [
  "Dashboard",
  "Daily Briefing",
  "Sources",
  "Watchlist",
  "Agent Chat",
  "Settings",
] as const;

type View = (typeof navigation)[number];

type SourceEntry = {
  id: string;
  name: string;
  base_url: string | null;
  domains: string[];
  access_method: string;
  requires_api_key: boolean;
  reliability_tier: "primary" | "standard" | "discovery";
  enabled_by_default: boolean;
  phase: "v1" | "optional_v1";
  status: string;
  update_cadence: string;
  notes: string;
};

type SourceCatalogResponse = {
  sources: SourceEntry[];
  total: number;
  enabled_by_default_count: number;
  optional_count: number;
};

type AgentResponse = {
  request_id: string;
  summary: string;
  agents_ran: string[];
  confidence: "low" | "medium" | "high";
  risks: string[];
  follow_up_questions: string[];
  guardrail: {
    status: "passed" | "needs_revision" | "blocked";
    disclaimer: string;
    issues: string[];
    banned_phrases_found: string[];
    required_sections: string[];
  };
  requires_guardrail_review: boolean;
};

const briefingRows = [
  { domain: "World", status: "Waiting for ingestion", signal: "No live articles yet" },
  { domain: "Markets", status: "Scaffold ready", signal: "Agent endpoint available" },
  { domain: "Housing", status: "Source catalog ready", signal: "FRED, Census, FHFA planned" },
];

const watchlistRows = [
  { symbol: "SPY", focus: "Broad market risk", state: "Monitor" },
  { symbol: "QQQ", focus: "Growth and AI exposure", state: "Monitor" },
  { symbol: "TLT", focus: "Rates sensitivity", state: "Monitor" },
];

export default function Home() {
  const [activeView, setActiveView] = useState<View>("Dashboard");
  const [sourceData, setSourceData] = useState<SourceCatalogResponse | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [agentQuery, setAgentQuery] = useState("What should I watch in markets today?");
  const [agentTicker, setAgentTicker] = useState("SPY");
  const [agentDomain, setAgentDomain] = useState("Markets and Rates");
  const [agentResponse, setAgentResponse] = useState<AgentResponse | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadSources() {
      setSourcesLoading(true);
      setSourceError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/sources`, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Source request failed with status ${response.status}`);
        }

        const payload = (await response.json()) as SourceCatalogResponse;

        if (isMounted) {
          setSourceData(payload);
        }
      } catch (error) {
        if (isMounted) {
          setSourceError(error instanceof Error ? error.message : "Could not load sources");
        }
      } finally {
        if (isMounted) {
          setSourcesLoading(false);
        }
      }
    }

    loadSources();

    return () => {
      isMounted = false;
    };
  }, []);

  const primarySources = useMemo(
    () => sourceData?.sources.filter((source) => source.reliability_tier === "primary") ?? [],
    [sourceData],
  );

  async function submitAgentQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAgentLoading(true);
    setAgentError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agents/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_query: agentQuery,
          intent: "market_research",
          domains: [agentDomain],
          tickers: agentTicker
            .split(",")
            .map((ticker) => ticker.trim().toUpperCase())
            .filter(Boolean),
        }),
      });

      if (!response.ok) {
        throw new Error(`Agent request failed with status ${response.status}`);
      }

      setAgentResponse((await response.json()) as AgentResponse);
    } catch (error) {
      setAgentError(error instanceof Error ? error.message : "Could not run agent query");
    } finally {
      setAgentLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f5f7f8] text-[#111827]">
      <div className="grid min-h-screen lg:grid-cols-[260px_1fr]">
        <aside className="border-b border-[#d7dee3] bg-[#ffffff] px-4 py-4 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between gap-3 lg:block">
            <div>
              <p className="text-xs font-semibold uppercase text-[#25636b]">InvestorAgent</p>
              <h1 className="mt-1 text-xl font-semibold">Market Workspace</h1>
            </div>
            <div className="rounded-md border border-[#d7dee3] px-2 py-1 text-xs font-medium text-[#4b5563]">
              Phase 2.6
            </div>
          </div>

          <nav className="mt-5 flex gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">
            {navigation.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setActiveView(item)}
                className={`min-h-10 rounded-md px-3 py-2 text-left text-sm font-medium transition ${
                  activeView === item
                    ? "bg-[#143642] text-white"
                    : "text-[#374151] hover:bg-[#eef3f5]"
                }`}
              >
                {item}
              </button>
            ))}
          </nav>

          <div className="mt-6 hidden border-t border-[#e5eaf0] pt-4 text-xs leading-5 text-[#5b6573] lg:block">
            {FINANCIAL_DISCLAIMER}
          </div>
        </aside>

        <section className="min-w-0 px-5 py-5 md:px-8">
          <AppHeader activeView={activeView} sourceData={sourceData} sourcesLoading={sourcesLoading} />

          <div className="mt-5">
            {activeView === "Dashboard" && (
              <DashboardView
                sourceData={sourceData}
                sourceError={sourceError}
                sourcesLoading={sourcesLoading}
                primarySources={primarySources}
              />
            )}
            {activeView === "Daily Briefing" && <DailyBriefingView />}
            {activeView === "Sources" && (
              <SourcesView
                sourceData={sourceData}
                sourceError={sourceError}
                sourcesLoading={sourcesLoading}
              />
            )}
            {activeView === "Watchlist" && <WatchlistView />}
            {activeView === "Agent Chat" && (
              <AgentChatView
                agentQuery={agentQuery}
                agentTicker={agentTicker}
                agentDomain={agentDomain}
                agentLoading={agentLoading}
                agentResponse={agentResponse}
                agentError={agentError}
                setAgentQuery={setAgentQuery}
                setAgentTicker={setAgentTicker}
                setAgentDomain={setAgentDomain}
                submitAgentQuery={submitAgentQuery}
              />
            )}
            {activeView === "Settings" && <SettingsView />}
          </div>
        </section>
      </div>
    </main>
  );
}

function AppHeader({
  activeView,
  sourceData,
  sourcesLoading,
}: {
  activeView: View;
  sourceData: SourceCatalogResponse | null;
  sourcesLoading: boolean;
}) {
  return (
    <header className="flex flex-col gap-3 border-b border-[#d7dee3] pb-5 md:flex-row md:items-end md:justify-between">
      <div>
        <p className="text-sm font-semibold text-[#25636b]">{activeView}</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-normal md:text-3xl">
          Local market intelligence
        </h2>
      </div>
      <div className="grid grid-cols-3 gap-2 text-sm">
        <Metric label="Sources" value={sourcesLoading ? "--" : String(sourceData?.total ?? 0)} />
        <Metric
          label="Default"
          value={sourcesLoading ? "--" : String(sourceData?.enabled_by_default_count ?? 0)}
        />
        <Metric label="Optional" value={sourcesLoading ? "--" : String(sourceData?.optional_count ?? 0)} />
      </div>
    </header>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-20 rounded-md border border-[#d7dee3] bg-white px-3 py-2">
      <p className="text-xs text-[#5b6573]">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function DashboardView({
  sourceData,
  sourceError,
  sourcesLoading,
  primarySources,
}: {
  sourceData: SourceCatalogResponse | null;
  sourceError: string | null;
  sourcesLoading: boolean;
  primarySources: SourceEntry[];
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">Today</h3>
          <span className="rounded-md bg-[#eef3f5] px-2 py-1 text-xs font-medium text-[#25636b]">
            Scaffold
          </span>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {briefingRows.map((row) => (
            <div key={row.domain} className="rounded-md border border-[#e5eaf0] p-3">
              <p className="text-sm font-semibold">{row.domain}</p>
              <p className="mt-2 text-sm text-[#5b6573]">{row.status}</p>
              <p className="mt-3 text-xs font-medium text-[#25636b]">{row.signal}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <h3 className="text-lg font-semibold">Source Health</h3>
        <StatusBlock loading={sourcesLoading} error={sourceError} />
        {!sourcesLoading && !sourceError && (
          <div className="mt-4 space-y-2">
            <p className="text-sm text-[#5b6573]">
              {sourceData?.enabled_by_default_count ?? 0} default sources configured.
            </p>
            <p className="text-sm text-[#5b6573]">{primarySources.length} primary sources ready for ingestion work.</p>
          </div>
        )}
      </section>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4 xl:col-span-2">
        <h3 className="text-lg font-semibold">News Domains</h3>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {domains.map((domain) => (
            <div key={domain} className="rounded-md border border-[#e5eaf0] px-3 py-2 text-sm font-medium">
              {domain}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function DailyBriefingView() {
  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <h3 className="text-lg font-semibold">Daily Briefing</h3>
        <span className="text-sm text-[#5b6573]">Pending Phase 3 ingestion</span>
      </div>
      <div className="mt-4 divide-y divide-[#e5eaf0]">
        {briefingRows.map((row) => (
          <div key={row.domain} className="grid gap-2 py-3 md:grid-cols-[180px_1fr_220px]">
            <p className="font-medium">{row.domain}</p>
            <p className="text-sm text-[#5b6573]">{row.status}</p>
            <p className="text-sm font-medium text-[#25636b]">{row.signal}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function SourcesView({
  sourceData,
  sourceError,
  sourcesLoading,
}: {
  sourceData: SourceCatalogResponse | null;
  sourceError: string | null;
  sourcesLoading: boolean;
}) {
  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <h3 className="text-lg font-semibold">Sources</h3>
        <span className="text-sm text-[#5b6573]">Connected to backend catalog</span>
      </div>
      <StatusBlock loading={sourcesLoading} error={sourceError} />
      {!sourcesLoading && !sourceError && (
        <div className="mt-4 overflow-hidden rounded-md border border-[#e5eaf0]">
          <div className="hidden grid-cols-[1.2fr_0.8fr_0.6fr_0.6fr] bg-[#eef3f5] px-3 py-2 text-xs font-semibold uppercase text-[#5b6573] md:grid">
            <span>Name</span>
            <span>Domains</span>
            <span>Access</span>
            <span>Tier</span>
          </div>
          <div className="divide-y divide-[#e5eaf0]">
            {sourceData?.sources.map((source) => (
              <div key={source.id} className="grid gap-2 px-3 py-3 md:grid-cols-[1.2fr_0.8fr_0.6fr_0.6fr]">
                <div>
                  <p className="font-medium">{source.name}</p>
                  <p className="mt-1 text-xs text-[#5b6573]">{source.update_cadence}</p>
                </div>
                <p className="text-sm text-[#374151]">{source.domains.join(", ")}</p>
                <p className="text-sm text-[#374151]">{source.access_method}</p>
                <p className="text-sm font-medium text-[#25636b]">{source.reliability_tier}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function WatchlistView() {
  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4">
      <h3 className="text-lg font-semibold">Watchlist</h3>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {watchlistRows.map((row) => (
          <div key={row.symbol} className="rounded-md border border-[#e5eaf0] p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-lg font-semibold">{row.symbol}</p>
              <span className="rounded-md bg-[#eef3f5] px-2 py-1 text-xs font-medium text-[#25636b]">
                {row.state}
              </span>
            </div>
            <p className="mt-3 text-sm text-[#5b6573]">{row.focus}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function AgentChatView({
  agentQuery,
  agentTicker,
  agentDomain,
  agentLoading,
  agentResponse,
  agentError,
  setAgentQuery,
  setAgentTicker,
  setAgentDomain,
  submitAgentQuery,
}: {
  agentQuery: string;
  agentTicker: string;
  agentDomain: string;
  agentLoading: boolean;
  agentResponse: AgentResponse | null;
  agentError: string | null;
  setAgentQuery: (value: string) => void;
  setAgentTicker: (value: string) => void;
  setAgentDomain: (value: string) => void;
  submitAgentQuery: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <form onSubmit={submitAgentQuery} className="rounded-md border border-[#d7dee3] bg-white p-4">
        <h3 className="text-lg font-semibold">Agent Query</h3>
        <label className="mt-4 block text-sm font-medium" htmlFor="agent-query">
          Query
        </label>
        <textarea
          id="agent-query"
          value={agentQuery}
          onChange={(event) => setAgentQuery(event.target.value)}
          className="mt-2 min-h-32 w-full rounded-md border border-[#cbd5dc] px-3 py-2 text-sm outline-none focus:border-[#25636b]"
        />

        <label className="mt-4 block text-sm font-medium" htmlFor="agent-ticker">
          Tickers
        </label>
        <input
          id="agent-ticker"
          value={agentTicker}
          onChange={(event) => setAgentTicker(event.target.value)}
          className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
        />

        <label className="mt-4 block text-sm font-medium" htmlFor="agent-domain">
          Domain
        </label>
        <select
          id="agent-domain"
          value={agentDomain}
          onChange={(event) => setAgentDomain(event.target.value)}
          className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] bg-white px-3 text-sm outline-none focus:border-[#25636b]"
        >
          {domains.map((domain) => (
            <option key={domain} value={domain}>
              {domain}
            </option>
          ))}
        </select>

        <button
          type="submit"
          disabled={agentLoading || !agentQuery.trim()}
          className="mt-5 min-h-10 w-full rounded-md bg-[#143642] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9aa8b2]"
        >
          {agentLoading ? "Running" : "Run Query"}
        </button>
      </form>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">Response</h3>
          {agentResponse && (
            <span className="rounded-md bg-[#eef3f5] px-2 py-1 text-xs font-medium text-[#25636b]">
              {agentResponse.guardrail.status}
            </span>
          )}
        </div>
        <p className="mt-3 rounded-md border border-[#d7dee3] bg-[#f8fafb] p-3 text-sm text-[#4b5563]">
          {FINANCIAL_DISCLAIMER}
        </p>
        {agentError && <p className="mt-4 rounded-md bg-[#fff1f0] p-3 text-sm text-[#b42318]">{agentError}</p>}
        {!agentResponse && !agentError && (
          <div className="mt-4 rounded-md border border-dashed border-[#cbd5dc] p-6 text-sm text-[#5b6573]">
            No response yet.
          </div>
        )}
        {agentResponse && (
          <div className="mt-4 space-y-4">
            <p className="whitespace-pre-line text-sm leading-6 text-[#374151]">{agentResponse.summary}</p>
            <div>
              <p className="text-sm font-semibold">Agents</p>
              <p className="mt-1 text-sm text-[#5b6573]">{agentResponse.agents_ran.join(", ")}</p>
            </div>
            <div>
              <p className="text-sm font-semibold">Risks</p>
              <ul className="mt-2 space-y-2">
                {agentResponse.risks.map((risk) => (
                  <li key={risk} className="rounded-md border border-[#e5eaf0] px-3 py-2 text-sm text-[#5b6573]">
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function SettingsView() {
  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4">
      <h3 className="text-lg font-semibold">Settings</h3>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <SettingRow label="Backend URL" value={API_BASE_URL} />
        <SettingRow label="Source Mode" value="Configured catalog" />
        <SettingRow label="Storage" value="Local SQLite" />
        <SettingRow label="Guardrails" value="Enabled" />
      </div>
    </section>
  );
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[#e5eaf0] px-3 py-3">
      <p className="text-xs font-semibold uppercase text-[#5b6573]">{label}</p>
      <p className="mt-1 text-sm font-medium">{value}</p>
    </div>
  );
}

function StatusBlock({ loading, error }: { loading: boolean; error: string | null }) {
  if (loading) {
    return <p className="mt-4 rounded-md bg-[#f8fafb] p-3 text-sm text-[#5b6573]">Loading sources.</p>;
  }

  if (error) {
    return <p className="mt-4 rounded-md bg-[#fff1f0] p-3 text-sm text-[#b42318]">{error}</p>;
  }

  return null;
}

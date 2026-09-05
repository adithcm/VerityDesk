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
type RunMode = "all" | "rss" | "official_api";
type FreshnessStatus = "fresh" | "stale" | "failed" | "skipped" | "not_configured";
type AgentIntent =
  | "daily_briefing"
  | "company_research"
  | "market_research"
  | "housing_macro_research"
  | "general_research";

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

type SourceHealthItem = {
  source_key: string;
  source_name: string | null;
  status: FreshnessStatus;
  stored_status: string | null;
  last_attempt_at: string | null;
  last_success_at: string | null;
  latest_item_published_at: string | null;
  latest_item_title: string | null;
  consecutive_failures: number;
  freshness_window_hours: number;
  stale_after: string | null;
  last_error: string | null;
};

type SourceHealthResponse = {
  sources: SourceHealthItem[];
  total: number;
  fresh_count: number;
  stale_count: number;
  failed_count: number;
  skipped_count: number;
  not_configured_count: number;
};

type IngestionRunRecord = {
  id: number;
  source_key: string;
  source_name: string | null;
  run_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  items_seen: number;
  items_inserted: number;
  items_updated: number;
  items_skipped: number;
  error: string | null;
};

type IngestionRunHistoryResponse = {
  runs: IngestionRunRecord[];
  total: number;
};

type LatestIngestedItem = {
  item_type: "article" | "economic_observation";
  source_key: string;
  source_name: string | null;
  series_id: string | null;
  title: string;
  url: string | null;
  published_at: string | null;
  retrieved_at: string | null;
  domains: string[];
  summary: string | null;
  value: number | null;
  unit: string | null;
  period: string | null;
};

type LatestItemsResponse = {
  items: LatestIngestedItem[];
  total: number;
};

type DailyScheduleConfig = {
  enabled: boolean;
  local_time: string;
  timezone: string;
  mode: RunMode;
};

type IngestionRunResponse = {
  request_id: string;
  mode: RunMode;
  status: "success" | "partial_success" | "failed" | "already_running";
  started_at: string;
  completed_at: string | null;
  results: Array<{
    source_key: string;
    source_type: string;
    status: string;
    items_seen: number;
    items_inserted: number;
    items_updated: number;
    items_skipped: number;
    error: string | null;
  }>;
  message: string;
};

type AgentResponse = {
  request_id: string;
  summary: string;
  agents_ran: string[];
  claims: Array<{
    claim: string;
    claim_type: string;
    source_ids: string[];
    confidence: "low" | "medium" | "high";
    as_of: string | null;
  }>;
  citations: Array<{
    source_id: string | null;
    title: string;
    url: string | null;
    publisher: string | null;
    published_at: string | null;
    retrieved_at: string | null;
    supports_claim: string;
  }>;
  confidence: "low" | "medium" | "high";
  risks: string[];
  follow_up_questions: string[];
  guardrail: {
    status: "passed" | "needs_revision" | "blocked";
    disclaimer: string;
    issues: string[];
    banned_phrases_found: string[];
    required_sections: string[];
    rewritten_text: string | null;
  };
  requires_guardrail_review: boolean;
};

type AgentRunRecord = {
  id: number;
  request_id: string;
  agent_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
};

type AgentRunHistoryResponse = {
  runs: AgentRunRecord[];
  total: number;
};

type ReportResponse = {
  id: number;
  report_type: string;
  status: string;
  title: string;
  summary: string | null;
  body: string;
  domains: string[];
  tickers: string[];
  companies: string[];
  as_of: string | null;
  confidence: "low" | "medium" | "high";
  disclaimer_version: string;
  guardrail_status: "passed" | "needs_revision" | "blocked";
  metadata: Record<string, unknown>;
  citations: AgentResponse["citations"];
  created_at: string;
  updated_at: string;
};

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
  const [healthData, setHealthData] = useState<SourceHealthResponse | null>(null);
  const [runsData, setRunsData] = useState<IngestionRunHistoryResponse | null>(null);
  const [latestItemsData, setLatestItemsData] = useState<LatestItemsResponse | null>(null);
  const [scheduleData, setScheduleData] = useState<DailyScheduleConfig | null>(null);
  const [ingestionError, setIngestionError] = useState<string | null>(null);
  const [ingestionLoading, setIngestionLoading] = useState(true);
  const [runMode, setRunMode] = useState<RunMode>("all");
  const [runLoading, setRunLoading] = useState(false);
  const [lastRunResponse, setLastRunResponse] = useState<IngestionRunResponse | null>(null);
  const [agentQuery, setAgentQuery] = useState("What should I watch in markets today?");
  const [agentIntent, setAgentIntent] = useState<AgentIntent>("market_research");
  const [agentTicker, setAgentTicker] = useState("SPY");
  const [agentDomain, setAgentDomain] = useState("Markets and Rates");
  const [agentRunsData, setAgentRunsData] = useState<AgentRunHistoryResponse | null>(null);
  const [agentRunsLoading, setAgentRunsLoading] = useState(true);
  const [agentResponse, setAgentResponse] = useState<AgentResponse | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [dailyBriefingReport, setDailyBriefingReport] = useState<ReportResponse | null>(null);
  const [dailyBriefingLoading, setDailyBriefingLoading] = useState(false);
  const [dailyBriefingError, setDailyBriefingError] = useState<string | null>(null);
  const [companyTicker, setCompanyTicker] = useState("AAPL");
  const [companyName, setCompanyName] = useState("Apple");
  const [companyReport, setCompanyReport] = useState<ReportResponse | null>(null);
  const [companyReportLoading, setCompanyReportLoading] = useState(false);
  const [companyReportError, setCompanyReportError] = useState<string | null>(null);

  async function loadSources() {
    setSourcesLoading(true);
    setSourceError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/sources`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Source request failed with status ${response.status}`);
      }
      setSourceData((await response.json()) as SourceCatalogResponse);
    } catch (error) {
      setSourceError(error instanceof Error ? error.message : "Could not load sources");
    } finally {
      setSourcesLoading(false);
    }
  }

  async function loadIngestionStatus() {
    setIngestionLoading(true);
    setIngestionError(null);

    try {
      const [healthResponse, runsResponse, latestItemsResponse, scheduleResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/ingestion/health`, { cache: "no-store" }),
        fetch(`${API_BASE_URL}/api/v1/ingestion/runs?limit=8`, { cache: "no-store" }),
        fetch(`${API_BASE_URL}/api/v1/ingestion/latest-items?limit=10`, { cache: "no-store" }),
        fetch(`${API_BASE_URL}/api/v1/ingestion/schedule`, { cache: "no-store" }),
      ]);

      if (!healthResponse.ok || !runsResponse.ok || !latestItemsResponse.ok || !scheduleResponse.ok) {
        throw new Error("Could not load ingestion status");
      }

      setHealthData((await healthResponse.json()) as SourceHealthResponse);
      setRunsData((await runsResponse.json()) as IngestionRunHistoryResponse);
      setLatestItemsData((await latestItemsResponse.json()) as LatestItemsResponse);
      setScheduleData((await scheduleResponse.json()) as DailyScheduleConfig);
    } catch (error) {
      setIngestionError(error instanceof Error ? error.message : "Could not load ingestion status");
    } finally {
      setIngestionLoading(false);
    }
  }

  useEffect(() => {
    loadSources();
    loadIngestionStatus();
    loadAgentRuns();
  }, []);

  const primarySources = useMemo(
    () => sourceData?.sources.filter((source) => source.reliability_tier === "primary") ?? [],
    [sourceData],
  );

  async function loadAgentRuns() {
    setAgentRunsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agents/runs?limit=12`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Agent run request failed with status ${response.status}`);
      }
      setAgentRunsData((await response.json()) as AgentRunHistoryResponse);
    } catch {
      setAgentRunsData(null);
    } finally {
      setAgentRunsLoading(false);
    }
  }

  async function triggerIngestionRun() {
    setRunLoading(true);
    setIngestionError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/ingestion/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: runMode, source_keys: [] }),
      });

      if (!response.ok) {
        throw new Error(`Ingestion run failed with status ${response.status}`);
      }

      setLastRunResponse((await response.json()) as IngestionRunResponse);
      await loadIngestionStatus();
    } catch (error) {
      setIngestionError(error instanceof Error ? error.message : "Could not run ingestion");
    } finally {
      setRunLoading(false);
    }
  }

  async function submitAgentQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAgentLoading(true);
    setAgentError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agents/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_query: agentQuery,
          intent: agentIntent,
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
      await loadAgentRuns();
    } catch (error) {
      setAgentError(error instanceof Error ? error.message : "Could not run agent query");
    } finally {
      setAgentLoading(false);
    }
  }

  async function generateDailyBriefing() {
    setDailyBriefingLoading(true);
    setDailyBriefingError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/daily-briefing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ time_window: "week" }),
      });

      if (!response.ok) {
        throw new Error(`Daily briefing request failed with status ${response.status}`);
      }

      setDailyBriefingReport((await response.json()) as ReportResponse);
      await loadAgentRuns();
    } catch (error) {
      setDailyBriefingError(error instanceof Error ? error.message : "Could not generate daily briefing");
    } finally {
      setDailyBriefingLoading(false);
    }
  }

  async function generateCompanyReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCompanyReportLoading(true);
    setCompanyReportError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/company-research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: companyTicker.trim() || null,
          company: companyName.trim() || null,
          time_window: "month",
        }),
      });

      if (!response.ok) {
        throw new Error(`Company report request failed with status ${response.status}`);
      }

      setCompanyReport((await response.json()) as ReportResponse);
      await loadAgentRuns();
    } catch (error) {
      setCompanyReportError(error instanceof Error ? error.message : "Could not generate company report");
    } finally {
      setCompanyReportLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f5f7f8] text-[#111827]">
      <div className="grid min-h-screen lg:grid-cols-[260px_1fr]">
        <aside className="border-b border-[#d7dee3] bg-white px-4 py-4 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between gap-3 lg:block">
            <div>
              <p className="text-xs font-semibold uppercase text-[#25636b]">InvestorAgent</p>
              <h1 className="mt-1 text-xl font-semibold">Market Workspace</h1>
            </div>
            <div className="rounded-md border border-[#d7dee3] px-2 py-1 text-xs font-medium text-[#4b5563]">
              Phase 5.3
            </div>
          </div>

          <nav className="mt-5 flex gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">
            {navigation.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setActiveView(item)}
                className={`min-h-10 rounded-md px-3 py-2 text-left text-sm font-medium transition ${
                  activeView === item ? "bg-[#143642] text-white" : "text-[#374151] hover:bg-[#eef3f5]"
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
          <AppHeader
            activeView={activeView}
            sourceData={sourceData}
            sourcesLoading={sourcesLoading}
            healthData={healthData}
            ingestionLoading={ingestionLoading}
          />

          <div className="mt-5">
            {activeView === "Dashboard" && (
              <DashboardView
                sourceData={sourceData}
                sourceError={sourceError}
                sourcesLoading={sourcesLoading}
                primarySources={primarySources}
                healthData={healthData}
                runsData={runsData}
                latestItemsData={latestItemsData}
                scheduleData={scheduleData}
                ingestionError={ingestionError}
                ingestionLoading={ingestionLoading}
                runMode={runMode}
                runLoading={runLoading}
                lastRunResponse={lastRunResponse}
                setRunMode={setRunMode}
                triggerIngestionRun={triggerIngestionRun}
              />
            )}
            {activeView === "Daily Briefing" && (
              <DailyBriefingView
                latestItemsData={latestItemsData}
                ingestionLoading={ingestionLoading}
                dailyBriefingReport={dailyBriefingReport}
                dailyBriefingLoading={dailyBriefingLoading}
                dailyBriefingError={dailyBriefingError}
                generateDailyBriefing={generateDailyBriefing}
              />
            )}
            {activeView === "Sources" && (
              <SourcesView
                sourceData={sourceData}
                sourceError={sourceError}
                sourcesLoading={sourcesLoading}
                healthData={healthData}
                ingestionError={ingestionError}
                ingestionLoading={ingestionLoading}
              />
            )}
            {activeView === "Watchlist" && (
              <WatchlistView
                companyTicker={companyTicker}
                companyName={companyName}
                companyReport={companyReport}
                companyReportLoading={companyReportLoading}
                companyReportError={companyReportError}
                setCompanyTicker={setCompanyTicker}
                setCompanyName={setCompanyName}
                generateCompanyReport={generateCompanyReport}
              />
            )}
            {activeView === "Agent Chat" && (
              <AgentChatView
                agentQuery={agentQuery}
                agentIntent={agentIntent}
                agentTicker={agentTicker}
                agentDomain={agentDomain}
                agentLoading={agentLoading}
                agentRunsData={agentRunsData}
                agentRunsLoading={agentRunsLoading}
                agentResponse={agentResponse}
                agentError={agentError}
                setAgentQuery={setAgentQuery}
                setAgentIntent={setAgentIntent}
                setAgentTicker={setAgentTicker}
                setAgentDomain={setAgentDomain}
                submitAgentQuery={submitAgentQuery}
              />
            )}
            {activeView === "Settings" && <SettingsView healthData={healthData} scheduleData={scheduleData} />}
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
  healthData,
  ingestionLoading,
}: {
  activeView: View;
  sourceData: SourceCatalogResponse | null;
  sourcesLoading: boolean;
  healthData: SourceHealthResponse | null;
  ingestionLoading: boolean;
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
        <Metric label="Fresh" value={ingestionLoading ? "--" : String(healthData?.fresh_count ?? 0)} />
        <Metric label="Needs Check" value={ingestionLoading ? "--" : String(needsCheckCount(healthData))} />
      </div>
    </header>
  );
}

function DashboardView({
  sourceData,
  sourceError,
  sourcesLoading,
  primarySources,
  healthData,
  runsData,
  latestItemsData,
  scheduleData,
  ingestionError,
  ingestionLoading,
  runMode,
  runLoading,
  lastRunResponse,
  setRunMode,
  triggerIngestionRun,
}: {
  sourceData: SourceCatalogResponse | null;
  sourceError: string | null;
  sourcesLoading: boolean;
  primarySources: SourceEntry[];
  healthData: SourceHealthResponse | null;
  runsData: IngestionRunHistoryResponse | null;
  latestItemsData: LatestItemsResponse | null;
  scheduleData: DailyScheduleConfig | null;
  ingestionError: string | null;
  ingestionLoading: boolean;
  runMode: RunMode;
  runLoading: boolean;
  lastRunResponse: IngestionRunResponse | null;
  setRunMode: (mode: RunMode) => void;
  triggerIngestionRun: () => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h3 className="text-lg font-semibold">Ingestion Health</h3>
          <IngestionRunControl
            runMode={runMode}
            runLoading={runLoading}
            setRunMode={setRunMode}
            triggerIngestionRun={triggerIngestionRun}
          />
        </div>
        <StatusBlock loading={ingestionLoading} error={ingestionError} />
        {healthData && (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <HealthMetric label="Fresh" value={healthData.fresh_count} status="fresh" />
            <HealthMetric label="Stale" value={healthData.stale_count} status="stale" />
            <HealthMetric label="Failed" value={healthData.failed_count} status="failed" />
            <HealthMetric label="Skipped" value={healthData.skipped_count} status="skipped" />
            <HealthMetric label="Not Configured" value={healthData.not_configured_count} status="not_configured" />
          </div>
        )}
        {lastRunResponse && (
          <p className="mt-4 rounded-md border border-[#d7dee3] bg-[#f8fafb] p-3 text-sm text-[#374151]">
            {lastRunResponse.message}
          </p>
        )}
      </section>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <h3 className="text-lg font-semibold">Source Coverage</h3>
        <StatusBlock loading={sourcesLoading} error={sourceError} />
        {!sourcesLoading && !sourceError && (
          <div className="mt-4 space-y-2">
            <p className="text-sm text-[#5b6573]">
              {sourceData?.enabled_by_default_count ?? 0} default sources configured.
            </p>
            <p className="text-sm text-[#5b6573]">{primarySources.length} primary sources ready for ingestion.</p>
          </div>
        )}
      </section>

      <SchedulerStatusCard scheduleData={scheduleData} runsData={runsData} loading={ingestionLoading} />

      <section className="rounded-md border border-[#d7dee3] bg-white p-4 xl:col-span-2">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">Latest Items</h3>
          <span className="text-sm text-[#5b6573]">{latestItemsData?.total ?? 0} shown</span>
        </div>
        <LatestItemsList latestItemsData={latestItemsData} loading={ingestionLoading} />
      </section>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4 xl:col-span-2">
        <h3 className="text-lg font-semibold">Recent Runs</h3>
        <RecentRunsTable runsData={runsData} loading={ingestionLoading} />
      </section>
    </div>
  );
}

function IngestionRunControl({
  runMode,
  runLoading,
  setRunMode,
  triggerIngestionRun,
}: {
  runMode: RunMode;
  runLoading: boolean;
  setRunMode: (mode: RunMode) => void;
  triggerIngestionRun: () => void;
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <select
        value={runMode}
        onChange={(event) => setRunMode(event.target.value as RunMode)}
        className="h-10 rounded-md border border-[#cbd5dc] bg-white px-3 text-sm outline-none focus:border-[#25636b]"
      >
        <option value="all">All sources</option>
        <option value="rss">RSS only</option>
        <option value="official_api">Official APIs only</option>
      </select>
      <button
        type="button"
        onClick={triggerIngestionRun}
        disabled={runLoading}
        className="min-h-10 rounded-md bg-[#143642] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9aa8b2]"
      >
        {runLoading ? "Running" : "Run Ingestion"}
      </button>
    </div>
  );
}

function SchedulerStatusCard({
  scheduleData,
  runsData,
  loading,
}: {
  scheduleData: DailyScheduleConfig | null;
  runsData: IngestionRunHistoryResponse | null;
  loading: boolean;
}) {
  const lastRun = runsData?.runs.find((run) => run.completed_at || run.started_at);

  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4 xl:col-span-2">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <h3 className="text-lg font-semibold">Daily Run</h3>
        <StatusBadge status={scheduleData?.enabled ? "enabled" : "off"} />
      </div>
      {loading ? (
        <p className="mt-4 rounded-md bg-[#f8fafb] p-3 text-sm text-[#5b6573]">Loading schedule.</p>
      ) : (
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <SettingRow label="Daily Run" value={scheduleData?.enabled ? "On" : "Off"} />
          <SettingRow label="Scheduled Time" value={formatScheduleTime(scheduleData)} />
          <SettingRow label="Run Mode" value={formatRunMode(scheduleData?.mode)} />
          <SettingRow label="Last Run" value={formatDateTime(lastRun?.completed_at ?? lastRun?.started_at)} />
        </div>
      )}
    </section>
  );
}

function DailyBriefingView({
  latestItemsData,
  ingestionLoading,
  dailyBriefingReport,
  dailyBriefingLoading,
  dailyBriefingError,
  generateDailyBriefing,
}: {
  latestItemsData: LatestItemsResponse | null;
  ingestionLoading: boolean;
  dailyBriefingReport: ReportResponse | null;
  dailyBriefingLoading: boolean;
  dailyBriefingError: string | null;
  generateDailyBriefing: () => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold">Daily Briefing</h3>
            <p className="mt-1 text-sm text-[#5b6573]">Generate a saved briefing from current ingested evidence.</p>
          </div>
          <button
            type="button"
            onClick={generateDailyBriefing}
            disabled={dailyBriefingLoading}
            className="min-h-10 rounded-md bg-[#143642] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9aa8b2]"
          >
            {dailyBriefingLoading ? "Generating" : "Generate Daily Briefing"}
          </button>
        </div>
        {dailyBriefingError && (
          <p className="mt-4 rounded-md bg-[#fff1f0] p-3 text-sm text-[#b42318]">{dailyBriefingError}</p>
        )}
        {!dailyBriefingReport && !dailyBriefingError && (
          <div className="mt-4 rounded-md border border-dashed border-[#cbd5dc] p-6 text-sm text-[#5b6573]">
            No briefing generated in this session yet.
          </div>
        )}
        {dailyBriefingReport && (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <SettingRow label="Status" value={dailyBriefingReport.status} />
              <SettingRow label="Confidence" value={dailyBriefingReport.confidence} />
              <SettingRow label="Sources" value={String(dailyBriefingReport.citations.length)} />
            </div>
            <div>
              <p className="text-sm font-semibold">{dailyBriefingReport.title}</p>
              <p className="mt-1 text-xs text-[#5b6573]">Generated At {formatDateTime(dailyBriefingReport.as_of)}</p>
              <p className="mt-3 whitespace-pre-line rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3 text-sm leading-6 text-[#374151]">
                {dailyBriefingReport.body}
              </p>
            </div>
            <CitationList citations={dailyBriefingReport.citations} />
          </div>
        )}
      </section>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h3 className="text-lg font-semibold">Briefing Inputs</h3>
          <span className="text-sm text-[#5b6573]">Latest ingested source material</span>
        </div>
        <LatestItemsList latestItemsData={latestItemsData} loading={ingestionLoading} />
      </section>
    </div>
  );
}

function SourcesView({
  sourceData,
  sourceError,
  sourcesLoading,
  healthData,
  ingestionError,
  ingestionLoading,
}: {
  sourceData: SourceCatalogResponse | null;
  sourceError: string | null;
  sourcesLoading: boolean;
  healthData: SourceHealthResponse | null;
  ingestionError: string | null;
  ingestionLoading: boolean;
}) {
  const healthBySourceKey = useMemo(
    () => new Map(healthData?.sources.map((source) => [source.source_key, source]) ?? []),
    [healthData],
  );

  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <h3 className="text-lg font-semibold">Sources</h3>
        <span className="text-sm text-[#5b6573]">Catalog plus freshness status</span>
      </div>
      <StatusBlock loading={sourcesLoading || ingestionLoading} error={sourceError || ingestionError} />
      {!sourcesLoading && !sourceError && (
        <div className="mt-4 overflow-hidden rounded-md border border-[#e5eaf0]">
          <div className="hidden grid-cols-[1.05fr_0.75fr_0.65fr_0.65fr_0.8fr] bg-[#eef3f5] px-3 py-2 text-xs font-semibold uppercase text-[#5b6573] md:grid">
            <span>Name</span>
            <span>Status</span>
            <span>Last Checked</span>
            <span>Last Success</span>
            <span>Latest Item</span>
          </div>
          <div className="divide-y divide-[#e5eaf0]">
            {sourceData?.sources.map((source) => {
              const health = healthBySourceKey.get(source.id);
              return (
                <div
                  key={source.id}
                  className="grid gap-2 px-3 py-3 md:grid-cols-[1.05fr_0.75fr_0.65fr_0.65fr_0.8fr]"
                >
                  <div>
                    <p className="font-medium">{source.name}</p>
                    <p className="mt-1 text-xs text-[#5b6573]">{source.access_method}</p>
                  </div>
                  <div>
                    <StatusBadge status={health?.status ?? "not_configured"} />
                    {health?.last_error && (
                      <p className="mt-1 text-xs leading-4 text-[#8a4b08]">{health.last_error}</p>
                    )}
                  </div>
                  <p className="text-sm text-[#374151]">{formatDateTime(health?.last_attempt_at)}</p>
                  <p className="text-sm text-[#374151]">{formatDateTime(health?.last_success_at)}</p>
                  <p className="text-sm text-[#374151]">{health?.latest_item_title ?? "--"}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

function WatchlistView({
  companyTicker,
  companyName,
  companyReport,
  companyReportLoading,
  companyReportError,
  setCompanyTicker,
  setCompanyName,
  generateCompanyReport,
}: {
  companyTicker: string;
  companyName: string;
  companyReport: ReportResponse | null;
  companyReportLoading: boolean;
  companyReportError: string | null;
  setCompanyTicker: (value: string) => void;
  setCompanyName: (value: string) => void;
  generateCompanyReport: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <h3 className="text-lg font-semibold">Watchlist</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-1">
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

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <form onSubmit={generateCompanyReport}>
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="text-lg font-semibold">Company Research</h3>
              <p className="mt-1 text-sm text-[#5b6573]">Generate a saved company report from filings, news, and market context.</p>
            </div>
            <button
              type="submit"
              disabled={companyReportLoading || (!companyTicker.trim() && !companyName.trim())}
              className="min-h-10 rounded-md bg-[#143642] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9aa8b2]"
            >
              {companyReportLoading ? "Generating" : "Generate Company Report"}
            </button>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="block text-sm font-medium" htmlFor="company-ticker">
              Ticker
              <input
                id="company-ticker"
                value={companyTicker}
                onChange={(event) => setCompanyTicker(event.target.value.toUpperCase())}
                className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
              />
            </label>
            <label className="block text-sm font-medium" htmlFor="company-name">
              Company
              <input
                id="company-name"
                value={companyName}
                onChange={(event) => setCompanyName(event.target.value)}
                className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
              />
            </label>
          </div>
        </form>

        {companyReportError && (
          <p className="mt-4 rounded-md bg-[#fff1f0] p-3 text-sm text-[#b42318]">{companyReportError}</p>
        )}
        {!companyReport && !companyReportError && (
          <div className="mt-4 rounded-md border border-dashed border-[#cbd5dc] p-6 text-sm text-[#5b6573]">
            No company report generated in this session yet.
          </div>
        )}
        {companyReport && (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <SettingRow label="Status" value={companyReport.status} />
              <SettingRow label="Confidence" value={companyReport.confidence} />
              <SettingRow label="Sources" value={String(companyReport.citations.length)} />
            </div>
            <div>
              <p className="text-sm font-semibold">{companyReport.title}</p>
              <p className="mt-1 text-xs text-[#5b6573]">Generated At {formatDateTime(companyReport.as_of)}</p>
              <p className="mt-3 whitespace-pre-line rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3 text-sm leading-6 text-[#374151]">
                {companyReport.body}
              </p>
            </div>
            <CitationList citations={companyReport.citations} />
          </div>
        )}
      </section>
    </div>
  );
}

function AgentChatView({
  agentQuery,
  agentIntent,
  agentTicker,
  agentDomain,
  agentLoading,
  agentRunsData,
  agentRunsLoading,
  agentResponse,
  agentError,
  setAgentQuery,
  setAgentIntent,
  setAgentTicker,
  setAgentDomain,
  submitAgentQuery,
}: {
  agentQuery: string;
  agentIntent: AgentIntent;
  agentTicker: string;
  agentDomain: string;
  agentLoading: boolean;
  agentRunsData: AgentRunHistoryResponse | null;
  agentRunsLoading: boolean;
  agentResponse: AgentResponse | null;
  agentError: string | null;
  setAgentQuery: (value: string) => void;
  setAgentIntent: (value: AgentIntent) => void;
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

        <label className="mt-4 block text-sm font-medium" htmlFor="agent-intent">
          Intent
        </label>
        <select
          id="agent-intent"
          value={agentIntent}
          onChange={(event) => setAgentIntent(event.target.value as AgentIntent)}
          className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] bg-white px-3 text-sm outline-none focus:border-[#25636b]"
        >
          <option value="market_research">Market research</option>
          <option value="company_research">Company research</option>
          <option value="housing_macro_research">Housing and macro</option>
          <option value="daily_briefing">Daily briefing</option>
          <option value="general_research">General research</option>
        </select>

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

        <section className="mt-5 border-t border-[#e5eaf0] pt-4">
          <h4 className="text-sm font-semibold">Recent Agent Runs</h4>
          <AgentRunsList agentRunsData={agentRunsData} loading={agentRunsLoading} />
        </section>
      </form>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">Answer</h3>
          {agentResponse && <StatusBadge status={agentResponse.guardrail.status} />}
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
            <div className="grid gap-3 sm:grid-cols-3">
              <SettingRow label="Confidence" value={agentResponse.confidence} />
              <SettingRow label="Sources" value={String(agentResponse.citations.length)} />
              <SettingRow label="Review Needed" value={agentResponse.requires_guardrail_review ? "Yes" : "No"} />
            </div>
            <div>
              <p className="text-sm font-semibold">Natural Language Response</p>
              <p className="mt-2 whitespace-pre-line rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3 text-sm leading-6 text-[#374151]">
                {agentResponse.summary}
              </p>
            </div>
            <InlineList title="Agents Run" values={agentResponse.agents_ran} />
            <ClaimsList claims={agentResponse.claims} />
            <CitationList citations={agentResponse.citations} />
            <InlineList title="Risks" values={agentResponse.risks} />
            <InlineList title="Follow-up Questions" values={agentResponse.follow_up_questions} />
            <GuardrailDetails response={agentResponse} />
          </div>
        )}
      </section>
    </div>
  );
}

function AgentRunsList({
  agentRunsData,
  loading,
}: {
  agentRunsData: AgentRunHistoryResponse | null;
  loading: boolean;
}) {
  if (loading) {
    return <p className="mt-3 rounded-md bg-[#f8fafb] p-3 text-sm text-[#5b6573]">Loading runs.</p>;
  }

  if (!agentRunsData || agentRunsData.runs.length === 0) {
    return (
      <div className="mt-3 rounded-md border border-dashed border-[#cbd5dc] p-3 text-sm text-[#5b6573]">
        No agent runs yet.
      </div>
    );
  }

  return (
    <div className="mt-3 space-y-2">
      {agentRunsData.runs.slice(0, 6).map((run) => (
        <div key={run.id} className="rounded-md border border-[#e5eaf0] px-3 py-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium">{run.agent_name}</p>
            <StatusBadge status={run.status} />
          </div>
          <p className="mt-1 text-xs text-[#5b6573]">{formatDateTime(run.completed_at ?? run.started_at)}</p>
          {run.error && <p className="mt-1 text-xs text-[#b42318]">{run.error}</p>}
        </div>
      ))}
    </div>
  );
}

function InlineList({ title, values }: { title: string; values: string[] }) {
  return (
    <div>
      <p className="text-sm font-semibold">{title}</p>
      {values.length === 0 ? (
        <p className="mt-2 text-sm text-[#5b6573]">None reported.</p>
      ) : (
        <div className="mt-2 flex flex-wrap gap-2">
          {values.map((value) => (
            <span key={value} className="rounded-md border border-[#e5eaf0] px-2 py-1 text-sm text-[#4b5563]">
              {value}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function ClaimsList({ claims }: { claims: AgentResponse["claims"] }) {
  return (
    <div>
      <p className="text-sm font-semibold">Claims</p>
      {claims.length === 0 ? (
        <p className="mt-2 text-sm text-[#5b6573]">No structured claims returned.</p>
      ) : (
        <div className="mt-2 space-y-2">
          {claims.map((claim, index) => (
            <div key={`${claim.claim}-${index}`} className="rounded-md border border-[#e5eaf0] p-3">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={claim.confidence} />
                <span className="rounded-md bg-[#eef3f5] px-2 py-1 text-xs font-medium text-[#4b5563]">
                  {claim.claim_type}
                </span>
              </div>
              <p className="mt-2 text-sm text-[#374151]">{claim.claim}</p>
              {claim.source_ids.length > 0 && (
                <p className="mt-2 text-xs text-[#5b6573]">Sources: {claim.source_ids.join(", ")}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CitationList({ citations }: { citations: AgentResponse["citations"] }) {
  return (
    <div>
      <p className="text-sm font-semibold">Citations</p>
      {citations.length === 0 ? (
        <p className="mt-2 rounded-md border border-dashed border-[#cbd5dc] p-3 text-sm text-[#5b6573]">
          No citations returned for this response.
        </p>
      ) : (
        <div className="mt-2 space-y-2">
          {citations.map((citation, index) => (
            <div key={`${citation.source_id}-${citation.title}-${index}`} className="rounded-md border border-[#e5eaf0] p-3">
              <p className="text-sm font-medium">
                {citation.url ? <a href={citation.url}>{citation.title}</a> : citation.title}
              </p>
              <p className="mt-1 text-xs text-[#5b6573]">
                {[citation.publisher, citation.source_id].filter(Boolean).join(" | ")}
              </p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <SettingRow label="Published" value={formatDateTime(citation.published_at)} />
                <SettingRow label="Retrieved" value={formatDateTime(citation.retrieved_at)} />
              </div>
              <p className="mt-2 text-sm text-[#5b6573]">{citation.supports_claim}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function GuardrailDetails({ response }: { response: AgentResponse }) {
  const issues = response.guardrail.issues;
  const bannedPhrases = response.guardrail.banned_phrases_found;

  return (
    <div>
      <p className="text-sm font-semibold">Guardrail Review</p>
      <div className="mt-2 rounded-md border border-[#e5eaf0] p-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={response.guardrail.status} />
          {response.requires_guardrail_review && (
            <span className="rounded-md bg-[#fff7e8] px-2 py-1 text-xs font-medium text-[#8a4b08]">
              Review needed
            </span>
          )}
        </div>
        {issues.length > 0 && <InlineList title="Issues" values={issues} />}
        {bannedPhrases.length > 0 && <InlineList title="Blocked Phrases" values={bannedPhrases} />}
        {response.guardrail.rewritten_text && (
          <p className="mt-3 rounded-md bg-[#f8fafb] p-3 text-sm text-[#5b6573]">
            Safer wording was applied to the final response.
          </p>
        )}
      </div>
    </div>
  );
}

function SettingsView({
  healthData,
  scheduleData,
}: {
  healthData: SourceHealthResponse | null;
  scheduleData: DailyScheduleConfig | null;
}) {
  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4">
      <h3 className="text-lg font-semibold">Settings</h3>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <SettingRow label="Backend URL" value={API_BASE_URL} />
        <SettingRow label="Source Mode" value="Catalog and ingestion status" />
        <SettingRow label="Storage" value="Local SQLite" />
        <SettingRow label="Tracked Sources" value={String(healthData?.total ?? 0)} />
        <SettingRow label="Daily Run" value={scheduleData?.enabled ? "On" : "Off"} />
        <SettingRow label="Scheduled Time" value={formatScheduleTime(scheduleData)} />
      </div>
    </section>
  );
}

function LatestItemsList({
  latestItemsData,
  loading,
}: {
  latestItemsData: LatestItemsResponse | null;
  loading: boolean;
}) {
  if (loading) {
    return <p className="mt-4 rounded-md bg-[#f8fafb] p-3 text-sm text-[#5b6573]">Loading latest items.</p>;
  }

  if (!latestItemsData || latestItemsData.items.length === 0) {
    return (
      <div className="mt-4 rounded-md border border-dashed border-[#cbd5dc] p-6 text-sm text-[#5b6573]">
        No ingested items yet.
      </div>
    );
  }

  return (
    <div className="mt-4 divide-y divide-[#e5eaf0]">
      {latestItemsData.items.map((item, index) => (
        <div key={`${item.source_key}-${item.title}-${index}`} className="grid gap-2 py-3 md:grid-cols-[1fr_160px_170px]">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium">{item.url ? <a href={item.url}>{item.title}</a> : item.title}</p>
              <span className="rounded-md bg-[#eef3f5] px-2 py-1 text-xs font-medium text-[#25636b]">
                {item.item_type === "article" ? "Article" : "Observation"}
              </span>
              {item.series_id && (
                <span className="rounded-md border border-[#d7dee3] px-2 py-1 text-xs font-medium text-[#5b6573]">
                  {item.series_id}
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-[#5b6573]">{item.summary ?? observationSummary(item)}</p>
          </div>
          <p className="text-sm text-[#374151]">{item.source_name ?? item.source_key}</p>
          <div>
            <p className="text-xs font-semibold uppercase text-[#5b6573]">{item.item_type === "article" ? "Published At" : "Released At"}</p>
            <p className="mt-1 text-sm text-[#5b6573]">{formatDateTime(item.published_at)}</p>
            <p className="text-xs font-semibold uppercase text-[#5b6573]">Retrieved At</p>
            <p className="mt-1 text-sm text-[#5b6573]">{formatDateTime(item.retrieved_at)}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function RecentRunsTable({
  runsData,
  loading,
}: {
  runsData: IngestionRunHistoryResponse | null;
  loading: boolean;
}) {
  if (loading) {
    return <p className="mt-4 rounded-md bg-[#f8fafb] p-3 text-sm text-[#5b6573]">Loading recent runs.</p>;
  }

  if (!runsData || runsData.runs.length === 0) {
    return (
      <div className="mt-4 rounded-md border border-dashed border-[#cbd5dc] p-6 text-sm text-[#5b6573]">
        No ingestion runs yet.
      </div>
    );
  }

  return (
    <div className="mt-4 overflow-hidden rounded-md border border-[#e5eaf0]">
      <div className="hidden grid-cols-[1fr_0.5fr_0.45fr_0.45fr_0.8fr] bg-[#eef3f5] px-3 py-2 text-xs font-semibold uppercase text-[#5b6573] md:grid">
        <span>Source</span>
        <span>Status</span>
        <span>Inserted</span>
        <span>Updated</span>
        <span>Completed At</span>
      </div>
      <div className="divide-y divide-[#e5eaf0]">
        {runsData.runs.map((run) => (
          <div key={run.id} className="grid gap-2 px-3 py-3 md:grid-cols-[1fr_0.5fr_0.45fr_0.45fr_0.8fr]">
            <div>
              <p className="font-medium">{run.source_name ?? run.source_key}</p>
              {run.error && <p className="mt-1 text-xs leading-4 text-[#8a4b08]">{run.error}</p>}
            </div>
            <StatusBadge status={run.status} />
            <p className="text-sm text-[#374151]">{run.items_inserted}</p>
            <p className="text-sm text-[#374151]">{run.items_updated}</p>
            <p className="text-sm text-[#5b6573]">{formatDateTime(run.completed_at)}</p>
          </div>
        ))}
      </div>
    </div>
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

function HealthMetric({ label, value, status }: { label: string; value: number; status: string }) {
  return (
    <div className="rounded-md border border-[#e5eaf0] p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-[#5b6573]">{label}</p>
        <StatusDot status={status} />
      </div>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
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
    return <p className="mt-4 rounded-md bg-[#f8fafb] p-3 text-sm text-[#5b6573]">Loading.</p>;
  }

  if (error) {
    return <p className="mt-4 rounded-md bg-[#fff1f0] p-3 text-sm text-[#b42318]">{error}</p>;
  }

  return null;
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex min-h-7 items-center rounded-md px-2 py-1 text-xs font-semibold ${badgeClass(status)}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}

function StatusDot({ status }: { status: string }) {
  return <span className={`h-2.5 w-2.5 rounded-full ${dotClass(status)}`} />;
}

function badgeClass(status: string) {
  if (status === "fresh" || status === "success" || status === "passed") {
    return "bg-[#e8f5ee] text-[#1f6f4a]";
  }
  if (status === "failed" || status === "blocked") {
    return "bg-[#fff1f0] text-[#b42318]";
  }
  if (status === "stale" || status === "skipped" || status === "needs_revision") {
    return "bg-[#fff7e8] text-[#8a4b08]";
  }
  return "bg-[#eef3f5] text-[#4b5563]";
}

function dotClass(status: string) {
  if (status === "fresh" || status === "success") {
    return "bg-[#2f7d57]";
  }
  if (status === "failed") {
    return "bg-[#b42318]";
  }
  if (status === "stale" || status === "skipped") {
    return "bg-[#b87514]";
  }
  return "bg-[#9aa8b2]";
}

function needsCheckCount(healthData: SourceHealthResponse | null) {
  if (!healthData) {
    return 0;
  }

  return healthData.stale_count + healthData.failed_count + healthData.skipped_count + healthData.not_configured_count;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "--";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatScheduleTime(scheduleData: DailyScheduleConfig | null) {
  if (!scheduleData) {
    return "--";
  }

  return `${formatClockTime(scheduleData.local_time)} ${scheduleData.timezone}`;
}

function formatClockTime(value: string) {
  const [hourPart, minutePart = "00"] = value.split(":");
  const hour = Number(hourPart);
  const minute = Number(minutePart);

  if (Number.isNaN(hour) || Number.isNaN(minute)) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(2026, 0, 1, hour, minute));
}

function formatRunMode(mode: RunMode | undefined) {
  if (mode === "rss") {
    return "RSS only";
  }

  if (mode === "official_api") {
    return "Official APIs only";
  }

  return "All sources";
}

function observationSummary(item: LatestIngestedItem) {
  if (item.value === null) {
    return "Structured observation";
  }

  const unit = item.unit ? ` ${item.unit}` : "";
  return `${item.period ?? "Latest period"}: ${item.value}${unit}`;
}

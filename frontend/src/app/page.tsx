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
  "Reports",
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
  generate_daily_briefing: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_status: string | null;
  last_message: string | null;
  last_report_id: number | null;
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

type ReportListResponse = {
  reports: ReportResponse[];
  total: number;
};

type ProactiveSuggestion = {
  id: string;
  kind: "question" | "report" | "evidence_gap";
  title: string;
  prompt: string;
  action:
    | "run_agent_query"
    | "generate_daily_briefing"
    | "generate_company_research"
    | "generate_market_strategy"
    | "generate_housing_report"
    | "generate_macro_report"
    | "review_sources";
  priority: number;
  domains: string[];
  tickers: string[];
  reasons: string[];
  guardrail_note: string;
};

type ProactiveSuggestionsResponse = {
  suggestions: ProactiveSuggestion[];
  total: number;
  generated_at: string;
};

type PersonalizationProfile = {
  location: string;
  watchlist: string;
  companies: string;
  priorityTopics: string[];
  housingInterests: string[];
  macroInterests: string[];
  ignoredTopics: string;
  briefingStyle: "quick" | "balanced" | "detailed";
  briefingTime: string;
};

type InferredAgentContext = {
  intent: AgentIntent;
  domain: string;
  tickers: string[];
  companies: string[];
  location: string | null;
  timeWindow: string;
  explanation: string;
};

const PERSONALIZATION_STORAGE_KEY = "investoragent.personalization.v1";

const topicOptions = [
  "World news",
  "U.S. economy",
  "Markets",
  "Company news",
  "Housing",
  "Mortgage rates",
  "AI and technology",
  "Energy",
  "Banks and credit",
  "Consumer trends",
];

const housingInterestOptions = [
  "Mortgage rates",
  "Affordability",
  "Inventory",
  "Rent trends",
  "Regional housing",
];

const macroInterestOptions = [
  "Inflation",
  "Interest rates",
  "Jobs",
  "Consumer spending",
  "Credit conditions",
  "Fed policy",
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
  const [healthData, setHealthData] = useState<SourceHealthResponse | null>(null);
  const [runsData, setRunsData] = useState<IngestionRunHistoryResponse | null>(null);
  const [latestItemsData, setLatestItemsData] = useState<LatestItemsResponse | null>(null);
  const [scheduleData, setScheduleData] = useState<DailyScheduleConfig | null>(null);
  const [ingestionError, setIngestionError] = useState<string | null>(null);
  const [ingestionLoading, setIngestionLoading] = useState(true);
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [runMode, setRunMode] = useState<RunMode>("all");
  const [runLoading, setRunLoading] = useState(false);
  const [lastRunResponse, setLastRunResponse] = useState<IngestionRunResponse | null>(null);
  const [agentQuery, setAgentQuery] = useState("What should I watch in markets today?");
  const [agentIntent, setAgentIntent] = useState<AgentIntent>("market_research");
  const [agentTicker, setAgentTicker] = useState("SPY");
  const [agentDomain, setAgentDomain] = useState("Markets and Rates");
  const [manualAgentContext, setManualAgentContext] = useState(false);
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
  const [marketReport, setMarketReport] = useState<ReportResponse | null>(null);
  const [marketReportLoading, setMarketReportLoading] = useState(false);
  const [marketReportError, setMarketReportError] = useState<string | null>(null);
  const [housingReport, setHousingReport] = useState<ReportResponse | null>(null);
  const [housingReportLoading, setHousingReportLoading] = useState(false);
  const [housingReportError, setHousingReportError] = useState<string | null>(null);
  const [macroReport, setMacroReport] = useState<ReportResponse | null>(null);
  const [macroReportLoading, setMacroReportLoading] = useState(false);
  const [macroReportError, setMacroReportError] = useState<string | null>(null);
  const [reportListData, setReportListData] = useState<ReportListResponse | null>(null);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [reportsError, setReportsError] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<ReportResponse | null>(null);
  const [reportActionLoading, setReportActionLoading] = useState<string | null>(null);
  const [suggestionsData, setSuggestionsData] = useState<ProactiveSuggestionsResponse | null>(null);
  const [suggestionsLoading, setSuggestionsLoading] = useState(true);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
  const [personalizationProfile, setPersonalizationProfile] = useState<PersonalizationProfile>(defaultPersonalizationProfile());
  const [profileSavedAt, setProfileSavedAt] = useState<string | null>(null);

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
    loadReports();
    loadSuggestions();
  }, []);

  useEffect(() => {
    const savedProfile = loadPersonalizationProfile();
    setPersonalizationProfile(savedProfile);
    setAgentTicker(savedProfile.watchlist);
    if (savedProfile.companies.trim()) {
      setCompanyName(firstListItem(savedProfile.companies));
    }
    if (savedProfile.watchlist.trim()) {
      setCompanyTicker(firstListItem(savedProfile.watchlist).toUpperCase());
    }
  }, []);

  function savePersonalizationProfile(nextProfile: PersonalizationProfile) {
    setPersonalizationProfile(nextProfile);
    localStorage.setItem(PERSONALIZATION_STORAGE_KEY, JSON.stringify(nextProfile));
    setProfileSavedAt(new Date().toISOString());
    if (nextProfile.watchlist.trim()) {
      setAgentTicker(nextProfile.watchlist);
      setCompanyTicker(firstListItem(nextProfile.watchlist).toUpperCase());
    }
    if (nextProfile.companies.trim()) {
      setCompanyName(firstListItem(nextProfile.companies));
    }
  }

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

  async function loadReports(selectedId?: number | null) {
    setReportsLoading(true);
    setReportsError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/reports?limit=50`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Report request failed with status ${response.status}`);
      }
      const data = (await response.json()) as ReportListResponse;
      setReportListData(data);
      setSelectedReport((current) => {
        if (selectedId === null) {
          return data.reports[0] ?? null;
        }
        const nextId = selectedId ?? current?.id;
        return data.reports.find((report) => report.id === nextId) ?? data.reports[0] ?? null;
      });
    } catch (error) {
      setReportsError(error instanceof Error ? error.message : "Could not load reports");
      setReportListData(null);
    } finally {
      setReportsLoading(false);
    }
  }

  async function loadSuggestions() {
    setSuggestionsLoading(true);
    setSuggestionsError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/suggestions/proactive?limit=7`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Suggestions request failed with status ${response.status}`);
      }
      setSuggestionsData((await response.json()) as ProactiveSuggestionsResponse);
    } catch (error) {
      setSuggestionsError(error instanceof Error ? error.message : "Could not load suggestions");
      setSuggestionsData(null);
    } finally {
      setSuggestionsLoading(false);
    }
  }

  function applySuggestion(suggestion: ProactiveSuggestion) {
    if (suggestion.action === "run_agent_query") {
      setAgentQuery(suggestion.prompt);
      setAgentIntent(suggestion.domains.some((domain) => domain.includes("Housing")) ? "housing_macro_research" : "market_research");
      setAgentDomain(suggestion.domains[0] ?? "Markets and Rates");
      setAgentTicker(suggestion.tickers.join(", "));
      setManualAgentContext(true);
      setActiveView("Agent Chat");
      return;
    }
    if (suggestion.action === "generate_daily_briefing") {
      generateDailyBriefing();
      setActiveView("Daily Briefing");
      return;
    }
    if (suggestion.action === "generate_market_strategy") {
      generateMarketStrategy();
      setActiveView("Dashboard");
      return;
    }
    if (suggestion.action === "generate_housing_report") {
      generateHousingReport();
      setActiveView("Dashboard");
      return;
    }
    if (suggestion.action === "generate_macro_report") {
      generateMacroReport();
      setActiveView("Dashboard");
      return;
    }
    if (suggestion.action === "review_sources") {
      setActiveView("Sources");
    }
  }

  async function openReport(reportId: number) {
    setReportActionLoading(`open-${reportId}`);
    setReportsError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/${reportId}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Report detail request failed with status ${response.status}`);
      }
      setSelectedReport((await response.json()) as ReportResponse);
    } catch (error) {
      setReportsError(error instanceof Error ? error.message : "Could not open report");
    } finally {
      setReportActionLoading(null);
    }
  }

  async function runReportAction(reportId: number, action: "regenerate" | "archive" | "delete") {
    setReportActionLoading(`${action}-${reportId}`);
    setReportsError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/reports/${reportId}${action === "delete" ? "" : `/${action}`}`,
        { method: action === "delete" ? "DELETE" : "POST" },
      );
      if (!response.ok) {
        throw new Error(`Report ${action} failed with status ${response.status}`);
      }
      const nextReport = action === "regenerate" ? ((await response.json()) as ReportResponse) : null;
      if (nextReport) {
        setSelectedReport(nextReport);
        await loadReports(nextReport.id);
      } else {
        await loadReports(null);
      }
    } catch (error) {
      setReportsError(error instanceof Error ? error.message : `Could not ${action} report`);
    } finally {
      setReportActionLoading(null);
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
      await loadSuggestions();
    } catch (error) {
      setIngestionError(error instanceof Error ? error.message : "Could not run ingestion");
    } finally {
      setRunLoading(false);
    }
  }

  async function saveSchedule(nextSchedule: DailyScheduleConfig) {
    setScheduleSaving(true);
    setScheduleError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/ingestion/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextSchedule),
      });
      if (!response.ok) {
        throw new Error(`Schedule update failed with status ${response.status}`);
      }
      setScheduleData((await response.json()) as DailyScheduleConfig);
      await loadIngestionStatus();
    } catch (error) {
      setScheduleError(error instanceof Error ? error.message : "Could not save schedule");
    } finally {
      setScheduleSaving(false);
    }
  }

  async function submitAgentQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAgentLoading(true);
    setAgentError(null);
    const inferredContext = inferAgentContext(agentQuery, personalizationProfile);
    const requestContext = manualAgentContext
      ? {
          ...inferredContext,
          intent: agentIntent,
          domain: agentDomain,
          tickers: splitList(agentTicker).map((ticker) => ticker.toUpperCase()),
          explanation: "Using your Advanced overrides for this request.",
        }
      : inferredContext;
    setAgentIntent(requestContext.intent);
    setAgentDomain(requestContext.domain);
    setAgentTicker(requestContext.tickers.join(", "));

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agents/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_query: agentQuery,
          intent: requestContext.intent,
          domains: [requestContext.domain],
          tickers: requestContext.tickers,
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
      await loadReports();
      await loadSuggestions();
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
      await loadReports();
      await loadSuggestions();
    } catch (error) {
      setCompanyReportError(error instanceof Error ? error.message : "Could not generate company report");
    } finally {
      setCompanyReportLoading(false);
    }
  }

  async function generateMarketStrategy() {
    setMarketReportLoading(true);
    setMarketReportError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/market-strategy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickers: ["SPY", "QQQ", "TLT"], time_window: "month" }),
      });

      if (!response.ok) {
        throw new Error(`Market strategy request failed with status ${response.status}`);
      }

      setMarketReport((await response.json()) as ReportResponse);
      await loadAgentRuns();
      await loadReports();
      await loadSuggestions();
    } catch (error) {
      setMarketReportError(error instanceof Error ? error.message : "Could not generate market strategy report");
    } finally {
      setMarketReportLoading(false);
    }
  }

  async function generateHousingReport() {
    setHousingReportLoading(true);
    setHousingReportError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/housing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ regions: ["US"], time_window: "quarter" }),
      });

      if (!response.ok) {
        throw new Error(`Housing report request failed with status ${response.status}`);
      }

      setHousingReport((await response.json()) as ReportResponse);
      await loadAgentRuns();
      await loadReports();
      await loadSuggestions();
    } catch (error) {
      setHousingReportError(error instanceof Error ? error.message : "Could not generate housing report");
    } finally {
      setHousingReportLoading(false);
    }
  }

  async function generateMacroReport() {
    setMacroReportLoading(true);
    setMacroReportError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/macro`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ regions: ["US"], time_window: "quarter" }),
      });

      if (!response.ok) {
        throw new Error(`Macro report request failed with status ${response.status}`);
      }

      setMacroReport((await response.json()) as ReportResponse);
      await loadAgentRuns();
      await loadReports();
      await loadSuggestions();
    } catch (error) {
      setMacroReportError(error instanceof Error ? error.message : "Could not generate macro report");
    } finally {
      setMacroReportLoading(false);
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
              Phase 5.6
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
                healthData={healthData}
                scheduleData={scheduleData}
                ingestionError={ingestionError}
                ingestionLoading={ingestionLoading}
                reportListData={reportListData}
                reportsLoading={reportsLoading}
                reportsError={reportsError}
                suggestionsData={suggestionsData}
                suggestionsLoading={suggestionsLoading}
                suggestionsError={suggestionsError}
                loadSuggestions={loadSuggestions}
                applySuggestion={applySuggestion}
                setActiveView={setActiveView}
                agentQuery={agentQuery}
                agentLoading={agentLoading}
                setAgentQuery={setAgentQuery}
                setManualAgentContext={setManualAgentContext}
                submitAgentQuery={submitAgentQuery}
                personalizationProfile={personalizationProfile}
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
            {activeView === "Reports" && (
              <ReportsView
                reportListData={reportListData}
                reportsLoading={reportsLoading}
                reportsError={reportsError}
                selectedReport={selectedReport}
                reportActionLoading={reportActionLoading}
                loadReports={loadReports}
                openReport={openReport}
                runReportAction={runReportAction}
              />
            )}
            {activeView === "Sources" && (
              <SourcesView
                sourceData={sourceData}
                sourceError={sourceError}
                sourcesLoading={sourcesLoading}
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
                personalizationProfile={personalizationProfile}
                manualAgentContext={manualAgentContext}
                setAgentQuery={setAgentQuery}
                setAgentIntent={setAgentIntent}
                setAgentTicker={setAgentTicker}
                setAgentDomain={setAgentDomain}
                setManualAgentContext={setManualAgentContext}
                submitAgentQuery={submitAgentQuery}
              />
            )}
            {activeView === "Settings" && (
              <SettingsView
                healthData={healthData}
                scheduleData={scheduleData}
                scheduleSaving={scheduleSaving}
                scheduleError={scheduleError}
                personalizationProfile={personalizationProfile}
                profileSavedAt={profileSavedAt}
                saveSchedule={saveSchedule}
                savePersonalizationProfile={savePersonalizationProfile}
              />
            )}
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
  healthData,
  scheduleData,
  ingestionError,
  ingestionLoading,
  reportListData,
  reportsLoading,
  reportsError,
  suggestionsData,
  suggestionsLoading,
  suggestionsError,
  loadSuggestions,
  applySuggestion,
  setActiveView,
  agentQuery,
  agentLoading,
  setAgentQuery,
  setManualAgentContext,
  submitAgentQuery,
  personalizationProfile,
}: {
  healthData: SourceHealthResponse | null;
  scheduleData: DailyScheduleConfig | null;
  ingestionError: string | null;
  ingestionLoading: boolean;
  reportListData: ReportListResponse | null;
  reportsLoading: boolean;
  reportsError: string | null;
  suggestionsData: ProactiveSuggestionsResponse | null;
  suggestionsLoading: boolean;
  suggestionsError: string | null;
  loadSuggestions: () => Promise<void>;
  applySuggestion: (suggestion: ProactiveSuggestion) => void;
  setActiveView: (view: View) => void;
  agentQuery: string;
  agentLoading: boolean;
  setAgentQuery: (value: string) => void;
  setManualAgentContext: (value: boolean) => void;
  submitAgentQuery: (event: FormEvent<HTMLFormElement>) => void;
  personalizationProfile: PersonalizationProfile;
}) {
  const latestReport = reportListData?.reports[0] ?? null;
  const dailyReport = reportListData?.reports.find((report) => report.report_type === "daily_briefing") ?? latestReport;
  const sourceStatusText = summarizeSourceStatus(healthData, ingestionLoading, ingestionError);
  const personalizedQuestions = buildPersonalizedQuestions(personalizationProfile);

  function askQuestion(question?: string) {
    if (question) {
      setAgentQuery(question);
    }
    setManualAgentContext(false);
    setActiveView("Agent Chat");
  }

  return (
    <div className="space-y-4">
      <section className="rounded-md border border-[#cbd5dc] bg-white p-5">
        <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
          <form
            onSubmit={(event) => {
              setActiveView("Agent Chat");
              submitAgentQuery(event);
            }}
          >
            <p className="text-sm font-semibold text-[#25636b]">Start here</p>
            <h3 className="mt-2 text-2xl font-semibold">Ask one question. InvestorAgent will handle the routing.</h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#5b6573]">
              Use plain language for market, company, housing, macro, or world news questions. Detailed controls stay out of the way unless you need them.
            </p>
            <label className="mt-4 block text-sm font-medium" htmlFor="dashboard-question">
              What do you want to know?
              <textarea
                id="dashboard-question"
                value={agentQuery}
                onChange={(event) => {
                  setAgentQuery(event.target.value);
                  setManualAgentContext(false);
                }}
                placeholder="Example: What are mortgage rates doing in Arizona and how could that affect housing?"
                className="mt-2 min-h-28 w-full rounded-md border border-[#cbd5dc] px-3 py-2 text-sm outline-none focus:border-[#25636b]"
              />
            </label>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <button
                type="submit"
                disabled={agentLoading || !agentQuery.trim()}
                className="min-h-11 rounded-md bg-[#143642] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9aa8b2]"
              >
                {agentLoading ? "Thinking" : "Ask InvestorAgent"}
              </button>
              <button
                type="button"
                onClick={() => setActiveView("Daily Briefing")}
                className="min-h-11 rounded-md border border-[#cbd5dc] px-4 py-2 text-sm font-semibold text-[#143642]"
              >
                Open Daily Briefing
              </button>
              <button
                type="button"
                onClick={() => setActiveView("Reports")}
                className="min-h-11 rounded-md border border-[#cbd5dc] px-4 py-2 text-sm font-semibold text-[#143642]"
              >
                View Saved Reports
              </button>
            </div>
          </form>
          <div className="rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-4">
            <p className="text-sm font-semibold">Today At A Glance</p>
            <div className="mt-3 space-y-3">
              <QuietStatusRow label="Sources" value={sourceStatusText} />
              <QuietStatusRow label="Daily run" value={scheduleData?.enabled ? "On" : "Off"} />
              <QuietStatusRow label="Next run" value={formatDateTime(scheduleData?.next_run_at)} />
              <QuietStatusRow label="Last run" value={formatDateTime(scheduleData?.last_run_at)} />
              <QuietStatusRow label="Location" value={personalizationProfile.location || "Not set"} />
              <QuietStatusRow label="Watchlist" value={compactListLabel(splitList(personalizationProfile.watchlist))} />
            </div>
            <button
              type="button"
              onClick={() => setActiveView("Settings")}
              className="mt-4 text-sm font-semibold text-[#25636b]"
            >
              Edit personalization
            </button>
          </div>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-md border border-[#d7dee3] bg-white p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="text-lg font-semibold">Latest Briefing</h3>
              <p className="mt-1 text-sm text-[#5b6573]">A short entry point into the most recent saved intelligence.</p>
            </div>
            <button
              type="button"
              onClick={() => setActiveView("Daily Briefing")}
              className="min-h-10 rounded-md border border-[#cbd5dc] px-3 py-2 text-sm font-semibold text-[#143642]"
            >
              Open
            </button>
          </div>
          <StatusBlock loading={reportsLoading} error={reportsError} />
          {!reportsLoading && !reportsError && !dailyReport && (
            <div className="mt-4 rounded-md border border-dashed border-[#cbd5dc] p-6 text-sm text-[#5b6573]">
              No briefing saved yet.
            </div>
          )}
          {dailyReport && (
            <div className="mt-4">
              <p className="text-sm font-semibold">{dailyReport.title}</p>
              <p className="mt-1 text-xs text-[#5b6573]">Retrieved At {formatDateTime(dailyReport.as_of ?? dailyReport.created_at)}</p>
              <p className="mt-3 line-clamp-5 text-sm leading-6 text-[#374151]">
                {dailyReport.summary ?? dailyReport.body}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <StatusBadge status={dailyReport.confidence} />
                <span className="rounded-md border border-[#e5eaf0] px-2 py-1 text-xs font-semibold text-[#5b6573]">
                  {dailyReport.citations.length} sources
                </span>
              </div>
            </div>
          )}
        </section>

        <section className="rounded-md border border-[#d7dee3] bg-white p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="text-lg font-semibold">Quick Questions</h3>
              <p className="mt-1 text-sm text-[#5b6573]">Useful starting points without changing dropdowns.</p>
            </div>
          </div>
          <div className="mt-4 grid gap-2">
            {personalizedQuestions.map((question) => (
              <button
                key={question}
                type="button"
                onClick={() => askQuestion(question)}
                className="min-h-10 rounded-md border border-[#e5eaf0] px-3 py-2 text-left text-sm font-medium text-[#143642] transition hover:border-[#b7c7ce] hover:bg-[#f8fafb]"
              >
                {question}
              </button>
            ))}
          </div>
        </section>
      </div>

      <ProactiveSuggestionsCard
        suggestionsData={suggestionsData}
        suggestionsLoading={suggestionsLoading}
        suggestionsError={suggestionsError}
        loadSuggestions={loadSuggestions}
        applySuggestion={applySuggestion}
      />
    </div>
  );
}

function ProactiveSuggestionsCard({
  suggestionsData,
  suggestionsLoading,
  suggestionsError,
  loadSuggestions,
  applySuggestion,
}: {
  suggestionsData: ProactiveSuggestionsResponse | null;
  suggestionsLoading: boolean;
  suggestionsError: string | null;
  loadSuggestions: () => Promise<void>;
  applySuggestion: (suggestion: ProactiveSuggestion) => void;
}) {
  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4 xl:col-span-2">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-lg font-semibold">Suggested Next Steps</h3>
          <p className="mt-1 text-sm text-[#5b6573]">
            Recommended questions and reports based on recent evidence and saved report history.
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadSuggestions()}
          disabled={suggestionsLoading}
          className="min-h-10 rounded-md border border-[#cbd5dc] px-3 py-2 text-sm font-semibold text-[#143642] disabled:cursor-not-allowed disabled:text-[#9aa8b2]"
        >
          {suggestionsLoading ? "Loading" : "Refresh"}
        </button>
      </div>
      <StatusBlock loading={suggestionsLoading} error={suggestionsError} />
      {!suggestionsLoading && !suggestionsError && (!suggestionsData || suggestionsData.suggestions.length === 0) && (
        <div className="mt-4 rounded-md border border-dashed border-[#cbd5dc] p-6 text-sm text-[#5b6573]">
          No suggestions available yet.
        </div>
      )}
      {suggestionsData && suggestionsData.suggestions.length > 0 && (
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {suggestionsData.suggestions.slice(0, 6).map((suggestion) => (
            <button
              key={suggestion.id}
              type="button"
              onClick={() => applySuggestion(suggestion)}
              className="rounded-md border border-[#e5eaf0] p-3 text-left transition hover:border-[#b7c7ce] hover:bg-[#f8fafb]"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-[#eef3f5] px-2 py-1 text-xs font-semibold uppercase text-[#25636b]">
                  {formatSuggestionKind(suggestion.kind)}
                </span>
                <span className="text-xs font-semibold text-[#5b6573]">Priority {suggestion.priority}</span>
              </div>
              <p className="mt-3 text-sm font-semibold">{suggestion.title}</p>
              <p className="mt-2 text-sm leading-5 text-[#374151]">{suggestion.prompt}</p>
              {suggestion.reasons.length > 0 && (
                <p className="mt-3 text-xs leading-5 text-[#5b6573]">{suggestion.reasons[0]}</p>
              )}
              <p className="mt-3 text-xs font-medium text-[#8a4b08]">{suggestion.guardrail_note}</p>
            </button>
          ))}
        </div>
      )}
      {suggestionsData && (
        <p className="mt-3 text-xs text-[#5b6573]">Updated {formatDateTime(suggestionsData.generated_at)}</p>
      )}
    </section>
  );
}

function MacroHousingReportsCard({
  housingReport,
  housingReportLoading,
  housingReportError,
  generateHousingReport,
  macroReport,
  macroReportLoading,
  macroReportError,
  generateMacroReport,
}: {
  housingReport: ReportResponse | null;
  housingReportLoading: boolean;
  housingReportError: string | null;
  generateHousingReport: () => void;
  macroReport: ReportResponse | null;
  macroReportLoading: boolean;
  macroReportError: string | null;
  generateMacroReport: () => void;
}) {
  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4 xl:col-span-2">
      <div>
        <h3 className="text-lg font-semibold">Housing And Macro</h3>
        <p className="mt-1 text-sm text-[#5b6573]">
          Generate research reports for housing conditions or broader macro context.
        </p>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <ReportGeneratorPanel
          title="Housing Report"
          description="Mortgage rates, affordability, supply, demand, and housing risks."
          buttonLabel="Generate Housing Report"
          loadingLabel="Generating"
          loading={housingReportLoading}
          error={housingReportError}
          report={housingReport}
          onGenerate={generateHousingReport}
        />
        <ReportGeneratorPanel
          title="Macro Report"
          description="Rates, labor, policy, credit, and broad economic risks."
          buttonLabel="Generate Macro Report"
          loadingLabel="Generating"
          loading={macroReportLoading}
          error={macroReportError}
          report={macroReport}
          onGenerate={generateMacroReport}
        />
      </div>
    </section>
  );
}

function ReportGeneratorPanel({
  title,
  description,
  buttonLabel,
  loadingLabel,
  loading,
  error,
  report,
  onGenerate,
}: {
  title: string;
  description: string;
  buttonLabel: string;
  loadingLabel: string;
  loading: boolean;
  error: string | null;
  report: ReportResponse | null;
  onGenerate: () => void;
}) {
  return (
    <div className="rounded-md border border-[#e5eaf0] p-3">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold">{title}</p>
          <p className="mt-1 text-sm text-[#5b6573]">{description}</p>
        </div>
        <button
          type="button"
          onClick={onGenerate}
          disabled={loading}
          className="min-h-10 rounded-md bg-[#143642] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9aa8b2]"
        >
          {loading ? loadingLabel : buttonLabel}
        </button>
      </div>
      {error && <p className="mt-4 rounded-md bg-[#fff1f0] p-3 text-sm text-[#b42318]">{error}</p>}
      {report && <CompactReportPreview report={report} />}
    </div>
  );
}

function CompactReportPreview({ report }: { report: ReportResponse }) {
  return (
    <div className="mt-4 space-y-3">
      <div className="grid gap-2 sm:grid-cols-3">
        <SettingRow label="Status" value={report.status} />
        <SettingRow label="Confidence" value={report.confidence} />
        <SettingRow label="Sources" value={String(report.citations.length)} />
      </div>
      <div>
        <p className="text-sm font-semibold">{report.title}</p>
        <p className="mt-1 text-xs text-[#5b6573]">Generated At {formatDateTime(report.as_of)}</p>
        <p className="mt-3 max-h-72 overflow-auto whitespace-pre-line rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3 text-sm leading-6 text-[#374151]">
          {report.body}
        </p>
      </div>
      <CitationList citations={report.citations} />
    </div>
  );
}

function MarketStrategyCard({
  marketReport,
  marketReportLoading,
  marketReportError,
  generateMarketStrategy,
}: {
  marketReport: ReportResponse | null;
  marketReportLoading: boolean;
  marketReportError: string | null;
  generateMarketStrategy: () => void;
}) {
  return (
    <section className="rounded-md border border-[#d7dee3] bg-white p-4 xl:col-span-2">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-lg font-semibold">Market Strategy</h3>
          <p className="mt-1 text-sm text-[#5b6573]">
            Generate a scenario-based market research note for broad watchlist context.
          </p>
        </div>
        <button
          type="button"
          onClick={generateMarketStrategy}
          disabled={marketReportLoading}
          className="min-h-10 rounded-md bg-[#143642] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9aa8b2]"
        >
          {marketReportLoading ? "Generating" : "Generate Market Strategy"}
        </button>
      </div>
      {marketReportError && (
        <p className="mt-4 rounded-md bg-[#fff1f0] p-3 text-sm text-[#b42318]">{marketReportError}</p>
      )}
      {marketReport && (
        <div className="mt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <SettingRow label="Status" value={marketReport.status} />
            <SettingRow label="Confidence" value={marketReport.confidence} />
            <SettingRow label="Sources" value={String(marketReport.citations.length)} />
          </div>
          <div>
            <p className="text-sm font-semibold">{marketReport.title}</p>
            <p className="mt-1 text-xs text-[#5b6573]">Generated At {formatDateTime(marketReport.as_of)}</p>
            <p className="mt-3 whitespace-pre-line rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3 text-sm leading-6 text-[#374151]">
              {marketReport.body}
            </p>
          </div>
          <CitationList citations={marketReport.citations} />
        </div>
      )}
    </section>
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
          <SettingRow label="Auto Briefing" value={scheduleData?.generate_daily_briefing ? "On" : "Off"} />
          <SettingRow label="Last Run" value={formatDateTime(scheduleData?.last_run_at ?? lastRun?.completed_at ?? lastRun?.started_at)} />
          <SettingRow label="Next Run" value={formatDateTime(scheduleData?.next_run_at)} />
          <SettingRow label="Last Status" value={scheduleData?.last_status ?? "--"} />
          <SettingRow label="Last Report" value={scheduleData?.last_report_id ? `#${scheduleData.last_report_id}` : "--"} />
        </div>
      )}
      {scheduleData?.last_message && (
        <p className="mt-4 rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3 text-sm text-[#5b6573]">
          {scheduleData.last_message}
        </p>
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
    <div className="space-y-4">
      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold">Daily Briefing</h3>
            <p className="mt-1 text-sm text-[#5b6573]">A readable summary built from the latest saved evidence.</p>
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
          <ReportReadingPanel report={dailyBriefingReport} variant="briefing" />
        )}
      </section>

      <details className="rounded-md border border-[#d7dee3] bg-white p-4">
        <summary className="cursor-pointer text-sm font-semibold text-[#143642]">Source material used for briefings</summary>
        <p className="mt-2 text-sm text-[#5b6573]">Latest retrieved items are available here when you want to inspect the raw inputs.</p>
        <LatestItemsList latestItemsData={latestItemsData} loading={ingestionLoading} />
      </details>
    </div>
  );
}

function ReportsView({
  reportListData,
  reportsLoading,
  reportsError,
  selectedReport,
  reportActionLoading,
  loadReports,
  openReport,
  runReportAction,
}: {
  reportListData: ReportListResponse | null;
  reportsLoading: boolean;
  reportsError: string | null;
  selectedReport: ReportResponse | null;
  reportActionLoading: string | null;
  loadReports: (selectedId?: number | null) => Promise<void>;
  openReport: (reportId: number) => Promise<void>;
  runReportAction: (reportId: number, action: "regenerate" | "archive" | "delete") => Promise<void>;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">Report Library</h3>
            <p className="mt-1 text-sm text-[#5b6573]">{reportListData?.total ?? 0} saved reports</p>
          </div>
          <button
            type="button"
            onClick={() => loadReports()}
            disabled={reportsLoading}
            className="min-h-10 rounded-md border border-[#cbd5dc] px-3 py-2 text-sm font-semibold text-[#143642] disabled:cursor-not-allowed disabled:text-[#9aa8b2]"
          >
            {reportsLoading ? "Loading" : "Refresh"}
          </button>
        </div>
        <StatusBlock loading={reportsLoading} error={reportsError} />
        {!reportsLoading && !reportsError && (!reportListData || reportListData.reports.length === 0) && (
          <div className="mt-4 rounded-md border border-dashed border-[#cbd5dc] p-6 text-sm text-[#5b6573]">
            No saved reports yet.
          </div>
        )}
        {reportListData && reportListData.reports.length > 0 && (
          <div className="mt-4 space-y-2">
            {reportListData.reports.map((report) => (
              <button
                key={report.id}
                type="button"
                onClick={() => openReport(report.id)}
                className={`w-full rounded-md border p-3 text-left transition ${
                  selectedReport?.id === report.id
                    ? "border-[#25636b] bg-[#eef7f7]"
                    : "border-[#e5eaf0] hover:border-[#b7c7ce]"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold uppercase text-[#25636b]">
                    {formatReportType(report.report_type)}
                  </span>
                  <span className="text-xs text-[#5b6573]">{formatDateTime(report.as_of ?? report.created_at)}</span>
                </div>
                <p className="mt-2 text-sm font-semibold">{report.title}</p>
                <p className="mt-2 line-clamp-2 text-sm text-[#5b6573]">{report.summary ?? report.body}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <StatusBadge status={report.confidence} />
                  <span className="rounded-md border border-[#e5eaf0] px-2 py-1 text-xs font-semibold text-[#5b6573]">
                    {report.citations.length} sources
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        {!selectedReport ? (
          <div className="rounded-md border border-dashed border-[#cbd5dc] p-6 text-sm text-[#5b6573]">
            Select a report to read it.
          </div>
        ) : (
          <ReportDetailPanel
            report={selectedReport}
            reportActionLoading={reportActionLoading}
            runReportAction={runReportAction}
          />
        )}
      </section>
    </div>
  );
}

function ReportDetailPanel({
  report,
  reportActionLoading,
  runReportAction,
}: {
  report: ReportResponse;
  reportActionLoading: string | null;
  runReportAction: (reportId: number, action: "regenerate" | "archive" | "delete") => Promise<void>;
}) {
  const isBusy = reportActionLoading?.endsWith(`-${report.id}`) ?? false;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase text-[#25636b]">{formatReportType(report.report_type)}</p>
          <h3 className="mt-1 text-xl font-semibold">{report.title}</h3>
          <p className="mt-2 text-sm text-[#5b6573]">{report.summary}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => runReportAction(report.id, "regenerate")}
            disabled={isBusy}
            className="min-h-10 rounded-md bg-[#143642] px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9aa8b2]"
          >
            {reportActionLoading === `regenerate-${report.id}` ? "Refreshing" : "Refresh Report"}
          </button>
          <button
            type="button"
            onClick={() => runReportAction(report.id, "archive")}
            disabled={isBusy}
            className="min-h-10 rounded-md border border-[#cbd5dc] px-3 py-2 text-sm font-semibold text-[#143642] disabled:cursor-not-allowed disabled:text-[#9aa8b2]"
          >
            {reportActionLoading === `archive-${report.id}` ? "Archiving" : "Archive"}
          </button>
          <button
            type="button"
            onClick={() => runReportAction(report.id, "delete")}
            disabled={isBusy}
            className="min-h-10 rounded-md border border-[#f0b8b1] px-3 py-2 text-sm font-semibold text-[#b42318] disabled:cursor-not-allowed disabled:text-[#9aa8b2]"
          >
            {reportActionLoading === `delete-${report.id}` ? "Deleting" : "Delete"}
          </button>
        </div>
      </div>

      <ReportReadingPanel report={report} variant="report" />

      {(report.domains.length > 0 || report.tickers.length > 0 || report.companies.length > 0) && (
        <details className="rounded-md border border-[#e5eaf0] p-3">
          <summary className="cursor-pointer text-sm font-semibold text-[#143642]">Report focus</summary>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <InlineList title="Domains" values={report.domains} />
            <InlineList title="Tickers" values={report.tickers} />
            <InlineList title="Companies" values={report.companies} />
          </div>
        </details>
      )}

      <details className="rounded-md border border-[#e5eaf0] p-3">
        <summary className="cursor-pointer text-sm font-semibold text-[#143642]">Report details</summary>
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          <SettingRow label="Status" value={report.status} />
          <SettingRow label="Guardrail" value={report.guardrail_status} />
          <SettingRow label="Created At" value={formatDateTime(report.created_at)} />
          <SettingRow label="Updated At" value={formatDateTime(report.updated_at)} />
          <SettingRow label="Disclaimer" value={report.disclaimer_version} />
        </div>
        <ReportMetadataPanel metadata={report.metadata} />
      </details>
    </div>
  );
}

function ReportReadingPanel({ report, variant }: { report: ReportResponse; variant: "briefing" | "report" }) {
  return (
    <div className="mt-4 space-y-4">
      <div className="flex flex-wrap gap-2">
        <StatusBadge status={report.confidence} />
        <span className="rounded-md border border-[#e5eaf0] px-2 py-1 text-xs font-semibold text-[#5b6573]">
          {report.citations.length} sources
        </span>
        <span className="rounded-md border border-[#e5eaf0] px-2 py-1 text-xs font-semibold text-[#5b6573]">
          Retrieved At {formatDateTime(report.as_of ?? report.created_at)}
        </span>
      </div>

      {variant === "briefing" && (
        <div>
          <p className="text-sm font-semibold">{report.title}</p>
          {report.summary && <p className="mt-2 text-sm leading-6 text-[#5b6573]">{report.summary}</p>}
        </div>
      )}

      <article className="whitespace-pre-line rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-4 text-sm leading-7 text-[#374151]">
        {report.body}
      </article>

      <p className="rounded-md border border-[#e5eaf0] bg-white p-3 text-xs leading-5 text-[#5b6573]">
        {FINANCIAL_DISCLAIMER}
      </p>

      <details className="rounded-md border border-[#e5eaf0] p-3">
        <summary className="cursor-pointer text-sm font-semibold text-[#143642]">Sources and citations</summary>
        <CitationList citations={report.citations} />
      </details>
    </div>
  );
}

function ReportMetadataPanel({ metadata }: { metadata: Record<string, unknown> }) {
  const rows = Object.entries(metadata).filter(([, value]) => value !== null && value !== undefined && value !== "");

  if (rows.length === 0) {
    return null;
  }

  return (
    <div>
      <p className="text-sm font-semibold">Report Context</p>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        {rows.slice(0, 10).map(([key, value]) => (
          <SettingRow key={key} label={formatMetadataKey(key)} value={formatMetadataValue(value)} />
        ))}
      </div>
    </div>
  );
}

function SourcesView({
  sourceData,
  sourceError,
  sourcesLoading,
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
  const healthBySourceKey = useMemo(
    () => new Map(healthData?.sources.map((source) => [source.source_key, source]) ?? []),
    [healthData],
  );

  return (
    <div className="space-y-4">
      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold">Source Status</h3>
            <p className="mt-1 text-sm text-[#5b6573]">Detailed source checks and manual refresh controls.</p>
          </div>
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

      <SchedulerStatusCard scheduleData={scheduleData} runsData={runsData} loading={ingestionLoading} />

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h3 className="text-lg font-semibold">Sources</h3>
          <span className="text-sm text-[#5b6573]">What is connected and what needs attention</span>
        </div>
        <StatusBlock loading={sourcesLoading || ingestionLoading} error={sourceError || ingestionError} />
        {!sourcesLoading && !sourceError && (
          <div className="mt-4 overflow-hidden rounded-md border border-[#e5eaf0]">
            <div className="hidden grid-cols-[1fr_0.85fr_1.05fr_0.75fr_0.85fr] bg-[#eef3f5] px-3 py-2 text-xs font-semibold uppercase text-[#5b6573] md:grid">
              <span>Source</span>
              <span>Status</span>
              <span>What it means</span>
              <span>Last Updated</span>
              <span>Latest Item</span>
            </div>
            <div className="divide-y divide-[#e5eaf0]">
              {sourceData?.sources.map((source) => {
                const health = healthBySourceKey.get(source.id);
                const sourceStatus = sourceStatusSummary(source, health);
                return (
                  <div
                    key={source.id}
                    className="grid gap-3 px-3 py-3 md:grid-cols-[1fr_0.85fr_1.05fr_0.75fr_0.85fr]"
                  >
                    <div>
                      <p className="font-medium">{source.name}</p>
                      <p className="mt-1 text-xs text-[#5b6573]">{formatAccessMethod(source.access_method)}</p>
                    </div>
                    <div>
                      <StatusBadge status={sourceStatus.label} />
                      <p className="mt-2 text-xs leading-4 text-[#5b6573]">{sourceStatus.nextStep}</p>
                    </div>
                    <div>
                      <p className="text-sm leading-5 text-[#374151]">{sourceStatus.description}</p>
                      {health?.last_error && (
                        <details className="mt-2">
                          <summary className="cursor-pointer text-xs font-semibold text-[#8a4b08]">Technical message</summary>
                          <p className="mt-1 text-xs leading-4 text-[#8a4b08]">{health.last_error}</p>
                        </details>
                      )}
                    </div>
                    <p className="text-sm text-[#374151]">{formatDateTime(health?.last_success_at ?? health?.last_attempt_at)}</p>
                    <p className="text-sm text-[#374151]">{health?.latest_item_title ?? "--"}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">Latest Items</h3>
          <span className="text-sm text-[#5b6573]">{latestItemsData?.total ?? 0} shown</span>
        </div>
        <LatestItemsList latestItemsData={latestItemsData} loading={ingestionLoading} />
      </section>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <h3 className="text-lg font-semibold">Recent Runs</h3>
        <RecentRunsTable runsData={runsData} loading={ingestionLoading} />
      </section>
    </div>
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
  personalizationProfile,
  manualAgentContext,
  setAgentQuery,
  setAgentIntent,
  setAgentTicker,
  setAgentDomain,
  setManualAgentContext,
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
  personalizationProfile: PersonalizationProfile;
  manualAgentContext: boolean;
  setAgentQuery: (value: string) => void;
  setAgentIntent: (value: AgentIntent) => void;
  setAgentTicker: (value: string) => void;
  setAgentDomain: (value: string) => void;
  setManualAgentContext: (value: boolean) => void;
  submitAgentQuery: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const inferredContext = inferAgentContext(agentQuery, personalizationProfile);
  const displayedContext = manualAgentContext
    ? {
        ...inferredContext,
        intent: agentIntent,
        domain: agentDomain,
        tickers: splitList(agentTicker).map((ticker) => ticker.toUpperCase()),
        explanation: "Using your Advanced overrides for this request.",
      }
    : inferredContext;

  return (
    <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <form onSubmit={submitAgentQuery} className="rounded-md border border-[#d7dee3] bg-white p-4">
        <h3 className="text-lg font-semibold">Ask InvestorAgent</h3>
        <label className="mt-4 block text-sm font-medium" htmlFor="agent-query">
          Question
        </label>
        <textarea
          id="agent-query"
          value={agentQuery}
          onChange={(event) => {
            setAgentQuery(event.target.value);
            setManualAgentContext(false);
          }}
          className="mt-2 min-h-32 w-full rounded-md border border-[#cbd5dc] px-3 py-2 text-sm outline-none focus:border-[#25636b]"
        />

        <InferredContextPanel inferredContext={displayedContext} manualAgentContext={manualAgentContext} />

        <details className="mt-4 rounded-md border border-[#e5eaf0] p-3">
          <summary className="cursor-pointer text-sm font-semibold text-[#143642]">Advanced</summary>
          <p className="mt-2 text-sm text-[#5b6573]">
            InvestorAgent fills these in automatically. Adjust them only when you want to override the default routing.
          </p>

          <label className="mt-4 block text-sm font-medium" htmlFor="agent-intent">
            Intent
          </label>
          <select
            id="agent-intent"
            value={agentIntent}
            onChange={(event) => {
              setAgentIntent(event.target.value as AgentIntent);
              setManualAgentContext(true);
            }}
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
            onChange={(event) => {
              setAgentTicker(event.target.value);
              setManualAgentContext(true);
            }}
            className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
          />

          <label className="mt-4 block text-sm font-medium" htmlFor="agent-domain">
            Domain
          </label>
          <select
            id="agent-domain"
            value={agentDomain}
            onChange={(event) => {
              setAgentDomain(event.target.value);
              setManualAgentContext(true);
            }}
            className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] bg-white px-3 text-sm outline-none focus:border-[#25636b]"
          >
            {domains.map((domain) => (
              <option key={domain} value={domain}>
                {domain}
              </option>
            ))}
          </select>
          {manualAgentContext && (
            <button
              type="button"
              onClick={() => setManualAgentContext(false)}
              className="mt-4 min-h-10 rounded-md border border-[#cbd5dc] px-3 py-2 text-sm font-semibold text-[#143642]"
            >
              Return To Auto
            </button>
          )}
        </details>

        <button
          type="submit"
          disabled={agentLoading || !agentQuery.trim()}
          className="mt-5 min-h-10 w-full rounded-md bg-[#143642] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9aa8b2]"
        >
          {agentLoading ? "Thinking" : "Ask InvestorAgent"}
        </button>

        <details className="mt-5 border-t border-[#e5eaf0] pt-4">
          <summary className="cursor-pointer text-sm font-semibold text-[#143642]">Recent agent runs</summary>
          <h4 className="text-sm font-semibold">Recent Agent Runs</h4>
          <AgentRunsList agentRunsData={agentRunsData} loading={agentRunsLoading} />
        </details>
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

function InferredContextPanel({
  inferredContext,
  manualAgentContext,
}: {
  inferredContext: InferredAgentContext;
  manualAgentContext: boolean;
}) {
  return (
    <section className="mt-4 rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold">InvestorAgent understood this as</p>
          <p className="mt-1 text-sm leading-5 text-[#5b6573]">{inferredContext.explanation}</p>
        </div>
        <StatusBadge status={manualAgentContext ? "manual" : "auto"} />
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <QuietStatusRow label="Topic" value={formatAgentIntent(inferredContext.intent)} />
        <QuietStatusRow label="Area" value={inferredContext.domain} />
        <QuietStatusRow label="Tickers" value={compactListLabel(inferredContext.tickers)} />
        <QuietStatusRow label="Location" value={inferredContext.location ?? "Not needed"} />
        <QuietStatusRow label="Time window" value={inferredContext.timeWindow} />
        <QuietStatusRow label="Companies" value={compactListLabel(inferredContext.companies)} />
      </div>
    </section>
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
  scheduleSaving,
  scheduleError,
  personalizationProfile,
  profileSavedAt,
  saveSchedule,
  savePersonalizationProfile,
}: {
  healthData: SourceHealthResponse | null;
  scheduleData: DailyScheduleConfig | null;
  scheduleSaving: boolean;
  scheduleError: string | null;
  personalizationProfile: PersonalizationProfile;
  profileSavedAt: string | null;
  saveSchedule: (nextSchedule: DailyScheduleConfig) => Promise<void>;
  savePersonalizationProfile: (nextProfile: PersonalizationProfile) => void;
}) {
  const schedule = scheduleData ?? defaultScheduleConfig();
  const [profileDraft, setProfileDraft] = useState<PersonalizationProfile>(personalizationProfile);

  useEffect(() => {
    setProfileDraft(personalizationProfile);
  }, [personalizationProfile]);

  function updateSchedule(patch: Partial<DailyScheduleConfig>) {
    saveSchedule({ ...schedule, ...patch });
  }

  function updateProfile(patch: Partial<PersonalizationProfile>) {
    setProfileDraft((current) => ({ ...current, ...patch }));
  }

  function toggleProfileOption(field: "priorityTopics" | "housingInterests" | "macroInterests", value: string) {
    setProfileDraft((current) => {
      const currentValues = current[field];
      const nextValues = currentValues.includes(value)
        ? currentValues.filter((item) => item !== value)
        : [...currentValues, value];
      return { ...current, [field]: nextValues };
    });
  }

  function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    savePersonalizationProfile(normalizePersonalizationProfile(profileDraft));
  }

  return (
    <div className="space-y-4">
      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <h3 className="text-lg font-semibold">App Settings</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <SettingRow label="Backend URL" value={API_BASE_URL} />
          <SettingRow label="Source Mode" value="Catalog and ingestion status" />
          <SettingRow label="Storage" value="Local SQLite" />
          <SettingRow label="Tracked Sources" value={String(healthData?.total ?? 0)} />
        </div>
      </section>

      <form onSubmit={submitProfile} className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className="text-lg font-semibold">Personalization</h3>
            <p className="mt-1 text-sm text-[#5b6573]">
              Tell InvestorAgent what matters to you once. Later milestones will use this to auto-select context.
            </p>
          </div>
          <button
            type="submit"
            className="min-h-10 rounded-md bg-[#143642] px-4 py-2 text-sm font-semibold text-white"
          >
            Save Personalization
          </button>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <label className="block text-sm font-medium" htmlFor="profile-location">
            Where are you based?
            <input
              id="profile-location"
              value={profileDraft.location}
              onChange={(event) => updateProfile({ location: event.target.value })}
              placeholder="Phoenix, AZ"
              className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
            />
          </label>

          <label className="block text-sm font-medium" htmlFor="profile-briefing-time">
            Preferred briefing time
            <input
              id="profile-briefing-time"
              type="time"
              value={profileDraft.briefingTime}
              onChange={(event) => updateProfile({ briefingTime: event.target.value })}
              className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
            />
          </label>

          <label className="block text-sm font-medium" htmlFor="profile-watchlist">
            What do you watch?
            <input
              id="profile-watchlist"
              value={profileDraft.watchlist}
              onChange={(event) => updateProfile({ watchlist: event.target.value.toUpperCase() })}
              placeholder="AAPL, MSFT, SPY, QQQ"
              className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
            />
          </label>

          <label className="block text-sm font-medium" htmlFor="profile-companies">
            What companies matter to you?
            <input
              id="profile-companies"
              value={profileDraft.companies}
              onChange={(event) => updateProfile({ companies: event.target.value })}
              placeholder="Apple, Nvidia, Tesla"
              className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
            />
          </label>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          <CheckboxGroup
            title="Topics to prioritize"
            options={topicOptions}
            values={profileDraft.priorityTopics}
            onToggle={(value) => toggleProfileOption("priorityTopics", value)}
          />
          <CheckboxGroup
            title="Housing interests"
            options={housingInterestOptions}
            values={profileDraft.housingInterests}
            onToggle={(value) => toggleProfileOption("housingInterests", value)}
          />
          <CheckboxGroup
            title="Macro interests"
            options={macroInterestOptions}
            values={profileDraft.macroInterests}
            onToggle={(value) => toggleProfileOption("macroInterests", value)}
          />
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_280px]">
          <label className="block text-sm font-medium" htmlFor="profile-ignore">
            What should InvestorAgent ignore?
            <input
              id="profile-ignore"
              value={profileDraft.ignoredTopics}
              onChange={(event) => updateProfile({ ignoredTopics: event.target.value })}
              placeholder="crypto, small caps, meme stocks"
              className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
            />
          </label>
          <label className="block text-sm font-medium" htmlFor="profile-briefing-style">
            Briefing style
            <select
              id="profile-briefing-style"
              value={profileDraft.briefingStyle}
              onChange={(event) => updateProfile({ briefingStyle: event.target.value as PersonalizationProfile["briefingStyle"] })}
              className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] bg-white px-3 text-sm outline-none focus:border-[#25636b]"
            >
              <option value="quick">Quick</option>
              <option value="balanced">Balanced</option>
              <option value="detailed">Detailed</option>
            </select>
          </label>
        </div>

        <div className="mt-4 rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3">
          <p className="text-sm font-semibold">Saved profile summary</p>
          <p className="mt-2 text-sm leading-6 text-[#5b6573]">{profileSummary(personalizationProfile)}</p>
          <p className="mt-1 text-xs text-[#5b6573]">Saved At {formatDateTime(profileSavedAt)}</p>
        </div>
      </form>

      <section className="rounded-md border border-[#d7dee3] bg-white p-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className="text-lg font-semibold">Daily Automation</h3>
            <p className="mt-1 text-sm text-[#5b6573]">
              Runs while the local backend is open. Schedule settings are saved locally.
            </p>
          </div>
          <StatusBadge status={schedule.enabled ? "enabled" : "off"} />
        </div>
        {scheduleError && <p className="mt-4 rounded-md bg-[#fff1f0] p-3 text-sm text-[#b42318]">{scheduleError}</p>}
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="flex items-center gap-3 rounded-md border border-[#e5eaf0] p-3 text-sm font-medium">
            <input
              type="checkbox"
              checked={schedule.enabled}
              disabled={scheduleSaving}
              onChange={(event) => updateSchedule({ enabled: event.target.checked })}
            />
            Daily run
          </label>
          <label className="flex items-center gap-3 rounded-md border border-[#e5eaf0] p-3 text-sm font-medium">
            <input
              type="checkbox"
              checked={schedule.generate_daily_briefing}
              disabled={scheduleSaving}
              onChange={(event) => updateSchedule({ generate_daily_briefing: event.target.checked })}
            />
            Generate daily briefing
          </label>
          <label className="block text-sm font-medium" htmlFor="schedule-time">
            Scheduled Time
            <input
              id="schedule-time"
              type="time"
              value={schedule.local_time}
              disabled={scheduleSaving}
              onChange={(event) => updateSchedule({ local_time: event.target.value })}
              className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] px-3 text-sm outline-none focus:border-[#25636b]"
            />
          </label>
          <label className="block text-sm font-medium" htmlFor="schedule-mode">
            Run Mode
            <select
              id="schedule-mode"
              value={schedule.mode}
              disabled={scheduleSaving}
              onChange={(event) => updateSchedule({ mode: event.target.value as RunMode })}
              className="mt-2 h-10 w-full rounded-md border border-[#cbd5dc] bg-white px-3 text-sm outline-none focus:border-[#25636b]"
            >
              <option value="all">All sources</option>
              <option value="rss">RSS only</option>
              <option value="official_api">Official APIs only</option>
            </select>
          </label>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <SettingRow label="Next Run" value={formatDateTime(schedule.next_run_at)} />
          <SettingRow label="Last Run" value={formatDateTime(schedule.last_run_at)} />
          <SettingRow label="Last Status" value={schedule.last_status ?? "--"} />
        </div>
        {scheduleSaving && <p className="mt-4 text-sm text-[#5b6573]">Saving schedule.</p>}
      </section>
    </div>
  );
}

function CheckboxGroup({
  title,
  options,
  values,
  onToggle,
}: {
  title: string;
  options: string[];
  values: string[];
  onToggle: (value: string) => void;
}) {
  return (
    <fieldset className="rounded-md border border-[#e5eaf0] p-3">
      <legend className="px-1 text-sm font-semibold">{title}</legend>
      <div className="mt-2 grid gap-2">
        {options.map((option) => (
          <label key={option} className="flex min-h-9 items-center gap-2 text-sm text-[#374151]">
            <input
              type="checkbox"
              checked={values.includes(option)}
              onChange={() => onToggle(option)}
            />
            {option}
          </label>
        ))}
      </div>
    </fieldset>
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

function sourceStatusSummary(source: SourceEntry, health: SourceHealthItem | undefined) {
  const errorText = health?.last_error?.toLowerCase() ?? "";

  if (health?.status === "fresh") {
    return {
      label: "Working",
      description: "This source has recent data available.",
      nextStep: "No action needed.",
    };
  }

  if (source.requires_api_key && (health?.status === "not_configured" || errorText.includes("api key"))) {
    return {
      label: "Missing API key",
      description: "This source needs an API key before it can retrieve data.",
      nextStep: "Add the key in your local environment file.",
    };
  }

  if (source.status === "optional" || source.phase === "optional_v1") {
    return {
      label: "Scaffolded only",
      description: "This provider is listed as an optional future connection.",
      nextStep: "Planned after core sources are stable.",
    };
  }

  if (source.access_method === "dataset_download" || errorText.includes("parser")) {
    return {
      label: "Parser not implemented",
      description: "The source is known, but its data parser still needs to be completed.",
      nextStep: "Planned for Phase 7.",
    };
  }

  if (health?.status === "stale") {
    return {
      label: "Stale",
      description: "This source worked before, but the latest saved data is old.",
      nextStep: "Try refreshing sources.",
    };
  }

  if (health?.status === "failed") {
    return {
      label: "Failed",
      description: "The latest retrieval attempt did not finish successfully.",
      nextStep: "Open the technical message or try refreshing.",
    };
  }

  if (health?.status === "skipped") {
    return {
      label: "Skipped",
      description: "InvestorAgent skipped this source during the latest run.",
      nextStep: "Check whether it is enabled for the selected run mode.",
    };
  }

  if (source.status === "planned") {
    return {
      label: "Scaffolded only",
      description: "This source is in the catalog, but full ingestion may still be incomplete.",
      nextStep: "Planned for Phase 7 if not already connected.",
    };
  }

  return {
    label: "Not checked",
    description: "InvestorAgent has not recorded a successful retrieval yet.",
    nextStep: "Run a source refresh.",
  };
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[#e5eaf0] px-3 py-3">
      <p className="text-xs font-semibold uppercase text-[#5b6573]">{label}</p>
      <p className="mt-1 text-sm font-medium">{value}</p>
    </div>
  );
}

function QuietStatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-[#e5eaf0] pb-2 last:border-b-0 last:pb-0">
      <p className="text-sm text-[#5b6573]">{label}</p>
      <p className="text-right text-sm font-semibold text-[#111827]">{value}</p>
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
  if (status === "fresh" || status === "success" || status === "passed" || status === "Working") {
    return "bg-[#e8f5ee] text-[#1f6f4a]";
  }
  if (status === "failed" || status === "blocked" || status === "Failed") {
    return "bg-[#fff1f0] text-[#b42318]";
  }
  if (
    status === "stale" ||
    status === "skipped" ||
    status === "needs_revision" ||
    status === "Missing API key" ||
    status === "Parser not implemented" ||
    status === "Stale" ||
    status === "Skipped"
  ) {
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

function summarizeSourceStatus(
  healthData: SourceHealthResponse | null,
  loading: boolean,
  error: string | null,
) {
  if (loading) {
    return "Checking";
  }

  if (error) {
    return "Needs attention";
  }

  if (!healthData) {
    return "Not checked";
  }

  const needsCheck = needsCheckCount(healthData);
  if (needsCheck === 0) {
    return `${healthData.fresh_count} working`;
  }

  return `${healthData.fresh_count} working, ${needsCheck} need check`;
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

function formatAccessMethod(accessMethod: string) {
  if (accessMethod === "rss") {
    return "News feed";
  }

  if (accessMethod === "api") {
    return "Direct API";
  }

  if (accessMethod === "dataset_download") {
    return "Dataset download";
  }

  if (accessMethod === "rss_or_webpage") {
    return "Feed or webpage";
  }

  return formatReportType(accessMethod);
}

function formatReportType(reportType: string) {
  return reportType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatSuggestionKind(kind: ProactiveSuggestion["kind"]) {
  if (kind === "evidence_gap") {
    return "Evidence Gap";
  }
  return kind.charAt(0).toUpperCase() + kind.slice(1);
}

function defaultScheduleConfig(): DailyScheduleConfig {
  return {
    enabled: false,
    local_time: "08:00",
    timezone: "local",
    mode: "all",
    generate_daily_briefing: false,
    last_run_at: null,
    next_run_at: null,
    last_status: null,
    last_message: null,
    last_report_id: null,
  };
}

function defaultPersonalizationProfile(): PersonalizationProfile {
  return {
    location: "",
    watchlist: "SPY, QQQ, TLT",
    companies: "",
    priorityTopics: ["Markets", "Housing", "U.S. economy"],
    housingInterests: ["Mortgage rates", "Affordability"],
    macroInterests: ["Inflation", "Interest rates", "Fed policy"],
    ignoredTopics: "",
    briefingStyle: "balanced",
    briefingTime: "08:00",
  };
}

function loadPersonalizationProfile() {
  if (typeof window === "undefined") {
    return defaultPersonalizationProfile();
  }

  const storedProfile = window.localStorage.getItem(PERSONALIZATION_STORAGE_KEY);
  if (!storedProfile) {
    return defaultPersonalizationProfile();
  }

  try {
    return normalizePersonalizationProfile({
      ...defaultPersonalizationProfile(),
      ...(JSON.parse(storedProfile) as Partial<PersonalizationProfile>),
    });
  } catch {
    return defaultPersonalizationProfile();
  }
}

function normalizePersonalizationProfile(profile: PersonalizationProfile): PersonalizationProfile {
  return {
    ...profile,
    location: profile.location.trim(),
    watchlist: normalizeListText(profile.watchlist).toUpperCase(),
    companies: normalizeListText(profile.companies),
    ignoredTopics: normalizeListText(profile.ignoredTopics),
    priorityTopics: uniqueList(profile.priorityTopics),
    housingInterests: uniqueList(profile.housingInterests),
    macroInterests: uniqueList(profile.macroInterests),
    briefingTime: profile.briefingTime || "08:00",
  };
}

function normalizeListText(value: string) {
  return splitList(value).join(", ");
}

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function uniqueList(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

function firstListItem(value: string) {
  return splitList(value)[0] ?? "";
}

function compactListLabel(values: string[]) {
  if (values.length === 0) {
    return "Not set";
  }

  if (values.length <= 3) {
    return values.join(", ");
  }

  return `${values.slice(0, 3).join(", ")} +${values.length - 3}`;
}

function buildPersonalizedQuestions(profile: PersonalizationProfile) {
  const location = profile.location || "my area";
  const watchlist = compactListLabel(splitList(profile.watchlist));
  const companies = compactListLabel(splitList(profile.companies));

  return [
    `What matters for ${watchlist === "Not set" ? "my watchlist" : watchlist} today?`,
    `What should I watch in markets this morning based on my interests?`,
    `How are rates affecting housing in ${location}?`,
    companies === "Not set" ? "What company news should I pay attention to?" : `What changed with ${companies} this week?`,
  ];
}

function inferAgentContext(query: string, profile: PersonalizationProfile): InferredAgentContext {
  const normalizedQuery = query.toLowerCase();
  const queryTickers = inferTickers(query);
  const profileTickers = splitList(profile.watchlist).map((ticker) => ticker.toUpperCase());
  const tickers = queryTickers.length > 0 ? queryTickers : profileTickers;
  const companies = inferCompanies(query, profile);
  const location = inferLocation(query, profile);
  const intent = inferIntent(normalizedQuery, queryTickers, companies);
  const domain = inferDomain(intent, normalizedQuery);
  const timeWindow = inferTimeWindow(normalizedQuery);
  const explanation = buildInferenceExplanation(intent, domain, tickers, companies, location, timeWindow);

  return {
    intent,
    domain,
    tickers,
    companies,
    location,
    timeWindow,
    explanation,
  };
}

function inferIntent(normalizedQuery: string, tickers: string[], companies: string[]): AgentIntent {
  if (containsAny(normalizedQuery, ["briefing", "summary", "today's update", "daily update"])) {
    return "daily_briefing";
  }

  if (containsAny(normalizedQuery, ["housing", "mortgage", "rent", "home price", "real estate", "inventory", "affordability"])) {
    return "housing_macro_research";
  }

  if (containsAny(normalizedQuery, ["inflation", "cpi", "jobs", "unemployment", "fed", "rates", "gdp", "recession", "yield"])) {
    return "market_research";
  }

  if (tickers.length > 0 || companies.length > 0 || containsAny(normalizedQuery, ["earnings", "company", "stock", "shares"])) {
    return "company_research";
  }

  if (containsAny(normalizedQuery, ["market", "portfolio", "watchlist", "stocks", "s&p", "nasdaq"])) {
    return "market_research";
  }

  return "general_research";
}

function inferDomain(intent: AgentIntent, normalizedQuery: string) {
  if (intent === "daily_briefing") {
    return "World and Geopolitics";
  }

  if (intent === "housing_macro_research") {
    return "Housing and Real Estate";
  }

  if (containsAny(normalizedQuery, ["inflation", "cpi", "jobs", "unemployment", "fed", "gdp", "recession"])) {
    return "U.S. Economy and Policy";
  }

  if (intent === "company_research") {
    return "Companies and Earnings";
  }

  if (containsAny(normalizedQuery, ["oil", "gas", "energy", "gold", "commodity", "commodities"])) {
    return "Commodities and Energy";
  }

  if (containsAny(normalizedQuery, ["ai", "chip", "semiconductor", "software", "technology", "tech"])) {
    return "Technology and AI";
  }

  if (containsAny(normalizedQuery, ["bank", "credit", "loan", "lending"])) {
    return "Banking and Credit";
  }

  if (containsAny(normalizedQuery, ["market", "rate", "yield", "stock", "watchlist", "portfolio"])) {
    return "Markets and Rates";
  }

  return "World and Geopolitics";
}

function inferTickers(query: string) {
  const matches = query.match(/\b[A-Z]{1,5}\b/g) ?? [];
  const ignoredWords = new Set(["I", "A", "US", "USA", "AZ", "CA", "NY", "UK", "EU", "AI", "GDP", "CPI"]);
  return uniqueList(matches.filter((match) => !ignoredWords.has(match)));
}

function inferCompanies(query: string, profile: PersonalizationProfile) {
  const normalizedQuery = query.toLowerCase();
  return splitList(profile.companies).filter((company) => normalizedQuery.includes(company.toLowerCase()));
}

function inferLocation(query: string, profile: PersonalizationProfile) {
  const stateMatches = query.match(/\b(AZ|CA|NY|TX|FL|WA|NV|CO|UT|IL|GA|NC|MA|NJ|PA)\b/i);
  if (stateMatches?.[0]) {
    return stateMatches[0].toUpperCase();
  }

  if (containsAny(query.toLowerCase(), ["near me", "my area", "my city", "my state", "local", "housing", "mortgage"])) {
    return profile.location || null;
  }

  return null;
}

function inferTimeWindow(normalizedQuery: string) {
  if (containsAny(normalizedQuery, ["today", "this morning", "daily", "now", "right now"])) {
    return "Today";
  }

  if (containsAny(normalizedQuery, ["this week", "weekly", "week"])) {
    return "This week";
  }

  if (containsAny(normalizedQuery, ["this month", "monthly", "month", "earnings"])) {
    return "This month";
  }

  if (containsAny(normalizedQuery, ["quarter", "q1", "q2", "q3", "q4"])) {
    return "This quarter";
  }

  return "Recent";
}

function buildInferenceExplanation(
  intent: AgentIntent,
  domain: string,
  tickers: string[],
  companies: string[],
  location: string | null,
  timeWindow: string,
) {
  const context = [
    `topic: ${formatAgentIntent(intent)}`,
    `area: ${domain}`,
    tickers.length > 0 ? `tickers: ${compactListLabel(tickers)}` : null,
    companies.length > 0 ? `companies: ${compactListLabel(companies)}` : null,
    location ? `location: ${location}` : null,
    `time: ${timeWindow.toLowerCase()}`,
  ].filter(Boolean);

  return `Auto-selected ${context.join(", ")}.`;
}

function containsAny(value: string, terms: string[]) {
  return terms.some((term) => value.includes(term));
}

function profileSummary(profile: PersonalizationProfile) {
  const location = profile.location || "no location yet";
  const watchlist = compactListLabel(splitList(profile.watchlist));
  const topics = compactListLabel(profile.priorityTopics);
  const ignoredTopics = compactListLabel(splitList(profile.ignoredTopics));

  return `Location: ${location}. Watchlist: ${watchlist}. Priority topics: ${topics}. Ignored topics: ${ignoredTopics}. Briefing style: ${profile.briefingStyle}.`;
}

function formatAgentIntent(intent: AgentIntent) {
  if (intent === "daily_briefing") {
    return "Daily briefing";
  }
  if (intent === "company_research") {
    return "Company research";
  }
  if (intent === "market_research") {
    return "Market research";
  }
  if (intent === "housing_macro_research") {
    return "Housing and macro";
  }
  return "General research";
}

function formatMetadataKey(key: string) {
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatMetadataValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length > 0 ? value.map(String).join(", ") : "--";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return value === null || value === undefined || value === "" ? "--" : String(value);
}

function observationSummary(item: LatestIngestedItem) {
  if (item.value === null) {
    return "Structured observation";
  }

  const unit = item.unit ? ` ${item.unit}` : "";
  return `${item.period ?? "Latest period"}: ${item.value}${unit}`;
}

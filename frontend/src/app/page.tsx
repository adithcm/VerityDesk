"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

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
  "Home",
  "Daily Brief",
  "Agent Chat",
  "Settings",
] as const;

type View = (typeof navigation)[number] | "Reports" | "Sources" | "Watchlist";
type ShellNavItem = {
  label: string;
  title: string;
  view: View;
};
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

type WatchAlertResponse = {
  id: number;
  watch_item_id: number;
  report_id: number | null;
  title: string;
  message: string;
  status: string;
  triggered_at: string;
  acknowledged_at: string | null;
  metadata: Record<string, unknown>;
};

type WatchItemResponse = {
  id: number;
  title: string;
  category: string;
  query: string;
  status: string;
  priority: string;
  enabled: boolean;
  last_checked_at: string | null;
  last_matched_at: string | null;
  last_summary: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  alerts: WatchAlertResponse[];
};

type WatchItemListResponse = {
  items: WatchItemResponse[];
  total: number;
};

type WatchEvaluationResponse = {
  checked: number;
  triggered: number;
  alerts: WatchAlertResponse[];
};

type ProactiveSuggestionsResponse = {
  suggestions: ProactiveSuggestion[];
  total: number;
  generated_at: string;
};

type PersonalizationProfile = {
  profileName: string;
  personalNote: string;
  location: string;
  housingMarkets: string;
  watchlist: string;
  companies: string;
  priorityTopics: string[];
  sectors: string;
  housingInterests: string[];
  macroInterests: string[];
  riskPreference: "conservative" | "balanced" | "aggressive";
  investingStyle: "long_term" | "medium_term" | "short_term" | "mixed";
  answerFormat: "brief" | "decision_memo" | "watchlist";
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

type HomeVisualModule = {
  id: "daily_read" | "housing" | "markets" | "companies" | "macro";
  title: string;
  value: string;
  label: string;
  summary: string;
  status: string;
  accent: "lime" | "cyan" | "pink" | "orange" | "violet";
  points: number[];
  updatedAt: string | null;
  stats: Array<{ label: string; value: string; detail: string | null }>;
  sources: Array<{ name: string; status: string; retrievedAt: string | null; description: string | null }>;
  relatedReportId: number | null;
  suggestedPrompt: string;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
};

type ChatSession = {
  id: string;
  title: string;
  summary: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
};

type VisualModulesApiResponse = {
  modules: Array<{
    id: HomeVisualModule["id"];
    title: string;
    summary: string;
    primary_value: string;
    primary_label: string;
    status: string;
    trend: string;
    updated_at: string | null;
    chart: {
      kind: "bar" | "line" | "spark";
      points: Array<{ label: string; value: number }>;
    };
    stats: Array<{ label: string; value: string; detail: string | null }>;
    sources: Array<{ name: string; status: string; retrieved_at: string | null; description: string | null }>;
    related_report_id: number | null;
    related_watch_item_ids: number[];
    suggested_prompt: string;
  }>;
  total: number;
  generated_at: string;
};

const PERSONALIZATION_STORAGE_KEY = "investoragent.personalization.v1";
const SETUP_COMPLETE_STORAGE_KEY = "investoragent.setupComplete.v1";
const LOCAL_SESSION_STORAGE_KEY = "investoragent.localSession.v1";
const CHAT_SESSIONS_STORAGE_KEY = "investoragent.chatSessions.v1";
const ACTIVE_CHAT_SESSION_STORAGE_KEY = "investoragent.activeChatSession.v1";

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

const shellNavigation: ShellNavItem[] = [
  { label: "Home", title: "Home", view: "Home" },
  { label: "Brief", title: "Daily Brief", view: "Daily Brief" },
  { label: "Chat", title: "Agent Chat", view: "Agent Chat" },
  { label: "Set", title: "Settings", view: "Settings" },
];

export default function Home() {
  const [activeView, setActiveView] = useState<View>("Home");
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
  const [visualModulesData, setVisualModulesData] = useState<VisualModulesApiResponse | null>(null);
  const [visualModulesLoading, setVisualModulesLoading] = useState(true);
  const [visualModulesError, setVisualModulesError] = useState<string | null>(null);
  const [watchItemsData, setWatchItemsData] = useState<WatchItemListResponse | null>(null);
  const [watchItemsLoading, setWatchItemsLoading] = useState(true);
  const [watchItemsError, setWatchItemsError] = useState<string | null>(null);
  const [watchEvaluationLoading, setWatchEvaluationLoading] = useState(false);
  const [newWatchTitle, setNewWatchTitle] = useState("");
  const [newWatchQuery, setNewWatchQuery] = useState("");
  const [newWatchCategory, setNewWatchCategory] = useState("custom");
  const [personalizationProfile, setPersonalizationProfile] = useState<PersonalizationProfile>(defaultPersonalizationProfile());
  const [profileSavedAt, setProfileSavedAt] = useState<string | null>(null);
  const [setupOpen, setSetupOpen] = useState(false);
  const [localSessionReady, setLocalSessionReady] = useState(false);
  const [entryLoaded, setEntryLoaded] = useState(false);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [activeChatSessionId, setActiveChatSessionId] = useState<string | null>(null);

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
    loadVisualModules();
    loadWatchItems();
  }, []);

  useEffect(() => {
    const savedProfile = loadPersonalizationProfile();
    const setupComplete = isSetupComplete(savedProfile);
    const savedChatSessions = loadChatSessions();
    const savedActiveChatId = loadActiveChatSessionId(savedChatSessions);
    setPersonalizationProfile(savedProfile);
    setLocalSessionReady(hasLocalSession());
    setSetupOpen(hasLocalSession() && !setupComplete);
    setChatSessions(savedChatSessions);
    setActiveChatSessionId(savedActiveChatId);
    setAgentTicker(savedProfile.watchlist);
    if (savedProfile.companies.trim()) {
      setCompanyName(firstListItem(savedProfile.companies));
    }
    if (savedProfile.watchlist.trim()) {
      setCompanyTicker(firstListItem(savedProfile.watchlist).toUpperCase());
    }
    setEntryLoaded(true);
  }, []);

  function savePersonalizationProfile(nextProfile: PersonalizationProfile) {
    setPersonalizationProfile(nextProfile);
    localStorage.setItem(PERSONALIZATION_STORAGE_KEY, JSON.stringify(nextProfile));
    localStorage.setItem(SETUP_COMPLETE_STORAGE_KEY, "true");
    setProfileSavedAt(new Date().toISOString());
    if (nextProfile.watchlist.trim()) {
      setAgentTicker(nextProfile.watchlist);
      setCompanyTicker(firstListItem(nextProfile.watchlist).toUpperCase());
    }
    if (nextProfile.companies.trim()) {
      setCompanyName(firstListItem(nextProfile.companies));
    }
  }

  function startLocalSession() {
    localStorage.setItem(LOCAL_SESSION_STORAGE_KEY, new Date().toISOString());
    setLocalSessionReady(true);
    setSetupOpen(!isSetupComplete(personalizationProfile));
    setActiveView("Home");
  }

  function persistChatSessions(nextSessions: ChatSession[], nextActiveId: string | null = activeChatSessionId) {
    setChatSessions(nextSessions);
    setActiveChatSessionId(nextActiveId);
    localStorage.setItem(CHAT_SESSIONS_STORAGE_KEY, JSON.stringify(nextSessions));
    if (nextActiveId) {
      localStorage.setItem(ACTIVE_CHAT_SESSION_STORAGE_KEY, nextActiveId);
    } else {
      localStorage.removeItem(ACTIVE_CHAT_SESSION_STORAGE_KEY);
    }
  }

  function createNewChatSession() {
    const nextSession = createChatSession();
    persistChatSessions([nextSession, ...chatSessions].slice(0, 20), nextSession.id);
    setAgentResponse(null);
    setAgentError(null);
    setAgentQuery("");
  }

  function selectChatSession(sessionId: string) {
    const session = chatSessions.find((item) => item.id === sessionId);
    if (!session) {
      return;
    }
    persistChatSessions(chatSessions, sessionId);
    const lastUserMessage = [...session.messages].reverse().find((message) => message.role === "user");
    setAgentQuery(lastUserMessage?.content ?? "");
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

  async function loadVisualModules() {
    setVisualModulesLoading(true);
    setVisualModulesError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/visuals/modules`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Visual module request failed with status ${response.status}`);
      }
      setVisualModulesData((await response.json()) as VisualModulesApiResponse);
    } catch (error) {
      setVisualModulesError(error instanceof Error ? error.message : "Could not load visual modules");
    } finally {
      setVisualModulesLoading(false);
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

  async function loadWatchItems() {
    setWatchItemsLoading(true);
    setWatchItemsError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watchlist/items`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Watch item request failed with status ${response.status}`);
      }
      setWatchItemsData((await response.json()) as WatchItemListResponse);
    } catch (error) {
      setWatchItemsError(error instanceof Error ? error.message : "Could not load watch items");
      setWatchItemsData(null);
    } finally {
      setWatchItemsLoading(false);
    }
  }

  async function createWatchItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newWatchTitle.trim() || !newWatchQuery.trim()) {
      return;
    }

    setWatchItemsError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watchlist/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: newWatchTitle.trim(),
          query: newWatchQuery.trim(),
          category: newWatchCategory,
          priority: "normal",
          enabled: true,
        }),
      });
      if (!response.ok) {
        throw new Error(`Watch item create failed with status ${response.status}`);
      }
      setNewWatchTitle("");
      setNewWatchQuery("");
      setNewWatchCategory("custom");
      await loadWatchItems();
    } catch (error) {
      setWatchItemsError(error instanceof Error ? error.message : "Could not create watch item");
    }
  }

  async function deleteWatchItem(watchItemId: number) {
    setWatchItemsError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watchlist/items/${watchItemId}`, { method: "DELETE" });
      if (!response.ok) {
        throw new Error(`Watch item delete failed with status ${response.status}`);
      }
      await loadWatchItems();
    } catch (error) {
      setWatchItemsError(error instanceof Error ? error.message : "Could not delete watch item");
    }
  }

  async function evaluateWatchItems() {
    setWatchEvaluationLoading(true);
    setWatchItemsError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watchlist/evaluate`, { method: "POST" });
      if (!response.ok) {
        throw new Error(`Watch item check failed with status ${response.status}`);
      }
      (await response.json()) as WatchEvaluationResponse;
      await loadWatchItems();
    } catch (error) {
      setWatchItemsError(error instanceof Error ? error.message : "Could not check watch items");
    } finally {
      setWatchEvaluationLoading(false);
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
      setActiveView("Daily Brief");
      return;
    }
    if (suggestion.action === "generate_market_strategy") {
      generateMarketStrategy();
      setActiveView("Home");
      return;
    }
    if (suggestion.action === "generate_housing_report") {
      generateHousingReport();
      setActiveView("Home");
      return;
    }
    if (suggestion.action === "generate_macro_report") {
      generateMacroReport();
      setActiveView("Home");
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
      await loadVisualModules();
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
    await runAgentQuery(agentQuery, manualAgentContext);
  }

  async function runAgentQuery(query: string, useManualContext: boolean) {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }

    setAgentLoading(true);
    setAgentError(null);
    const inferredContext = inferAgentContext(trimmedQuery, personalizationProfile);
    const requestContext = useManualContext
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
    setAgentQuery(trimmedQuery);
    setActiveView("Agent Chat");
    const sessionBeforeRun = ensureActiveChatSession(chatSessions, activeChatSessionId, trimmedQuery);
    const userMessage: ChatMessage = {
      id: createLocalId("msg"),
      role: "user",
      content: trimmedQuery,
      createdAt: new Date().toISOString(),
    };
    const sessionsWithUserMessage = upsertChatSession(chatSessions, {
      ...sessionBeforeRun,
      messages: [...sessionBeforeRun.messages, userMessage],
      title: sessionBeforeRun.title === "New chat" ? titleFromQuestion(trimmedQuery) : sessionBeforeRun.title,
      summary: summarizeChatMessages([...sessionBeforeRun.messages, userMessage]),
      updatedAt: userMessage.createdAt,
    });
    persistChatSessions(sessionsWithUserMessage, sessionBeforeRun.id);
    const queryWithMemory = buildQueryWithSessionMemory(trimmedQuery, sessionBeforeRun);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agents/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_query: queryWithMemory,
          intent: requestContext.intent,
          domains: [requestContext.domain],
          tickers: requestContext.tickers,
          companies: requestContext.companies,
          regions: requestContext.location ? [requestContext.location] : [],
          time_window: apiTimeWindow(requestContext.timeWindow),
        }),
      });

      if (!response.ok) {
        throw new Error(`Agent request failed with status ${response.status}`);
      }

      const nextAgentResponse = (await response.json()) as AgentResponse;
      setAgentResponse(nextAgentResponse);
      const assistantMessage: ChatMessage = {
        id: createLocalId("msg"),
        role: "assistant",
        content: nextAgentResponse.summary,
        createdAt: new Date().toISOString(),
      };
      const latestSession = sessionsWithUserMessage.find((session) => session.id === sessionBeforeRun.id) ?? sessionBeforeRun;
      persistChatSessions(
        upsertChatSession(sessionsWithUserMessage, {
          ...latestSession,
          messages: [...latestSession.messages, assistantMessage],
          summary: summarizeChatMessages([...latestSession.messages, assistantMessage]),
          updatedAt: assistantMessage.createdAt,
        }),
        sessionBeforeRun.id,
      );
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
      await loadVisualModules();
    } catch (error) {
      setDailyBriefingError(error instanceof Error ? error.message : "Could not generate daily briefing");
    } finally {
      setDailyBriefingLoading(false);
    }
  }

  async function generateCompanyReport(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
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
      await loadVisualModules();
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
      await loadVisualModules();
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
      await loadVisualModules();
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
      await loadVisualModules();
    } catch (error) {
      setMacroReportError(error instanceof Error ? error.message : "Could not generate macro report");
    } finally {
      setMacroReportLoading(false);
    }
  }

  function askFromShell(question?: string) {
    if (question) {
      setManualAgentContext(false);
      setAgentQuery(question);
      runAgentQuery(question, false);
      return;
    }
    setManualAgentContext(false);
    setActiveView("Home");
  }

  if (!entryLoaded) {
    return (
      <main className="min-h-screen bg-[#020617] text-[#f8fafc]">
        <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_72%_18%,rgba(34,211,238,0.18),transparent_30rem),radial-gradient(circle_at_18%_78%,rgba(163,230,53,0.12),transparent_30rem),#020617]" />
      </main>
    );
  }

  if (!localSessionReady) {
    return (
      <LoginEntryFlow
        profile={personalizationProfile}
        sourceStatusText={summarizeSourceStatus(healthData, ingestionLoading, ingestionError)}
        scheduleData={scheduleData}
        onContinue={startLocalSession}
        onSetup={() => {
          startLocalSession();
          setSetupOpen(true);
        }}
      />
    );
  }

  return (
    <main className="min-h-screen bg-[#020617] text-[#f8fafc]">
      <div className="fixed inset-0 -z-10 bg-[linear-gradient(rgba(34,211,238,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.035)_1px,transparent_1px),radial-gradient(circle_at_76%_10%,rgba(244,114,182,0.16),transparent_28rem),radial-gradient(circle_at_8%_68%,rgba(163,230,53,0.11),transparent_30rem),#020617] bg-[length:38px_38px,38px_38px,auto,auto,auto]" />
      {setupOpen && (
        <SetupProfileFlow
          profile={personalizationProfile}
          sourceStatusText={summarizeSourceStatus(healthData, ingestionLoading, ingestionError)}
          scheduleData={scheduleData}
          onSave={(nextProfile) => {
            savePersonalizationProfile(nextProfile);
            setSetupOpen(false);
            setActiveView("Home");
          }}
          onSkip={() => {
            localStorage.setItem(SETUP_COMPLETE_STORAGE_KEY, "true");
            setSetupOpen(false);
          }}
        />
      )}

      <header className="flex min-h-[70px] items-center justify-between gap-4 border-b border-cyan-300/20 px-5 md:px-7">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-[10px] border border-lime-300/60 bg-[#020617] font-mono text-sm font-black text-lime-300">
            V
          </div>
          <div>
            <p className="font-mono text-sm font-black uppercase text-lime-300">VerityDesk</p>
            <p className="text-xs font-semibold text-slate-400">Live web primary / APIs corroborate</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveView("Settings")}
            className="min-h-10 rounded-lg border border-[#1d3558] px-3 text-sm font-black text-slate-300 transition hover:border-cyan-300/50 hover:text-cyan-200"
          >
            Settings
          </button>
          <button
            type="button"
            onClick={triggerIngestionRun}
            disabled={runLoading}
            className="min-h-10 rounded-lg bg-lime-300 px-4 text-sm font-black text-[#102000] disabled:cursor-not-allowed disabled:bg-slate-500"
          >
            {runLoading ? "Refreshing" : "Refresh Sources"}
          </button>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] gap-4 p-4 lg:grid-cols-[82px_minmax(0,1fr)_390px] lg:gap-5 lg:p-6">
        <aside className="flex gap-2 rounded-[14px] border border-cyan-300/20 bg-[#07111f]/90 p-3 shadow-[0_24px_80px_rgba(0,0,0,0.32)] lg:min-h-[calc(100vh-118px)] lg:flex-col">
          {shellNavigation.map((item) => (
            <button
              key={item.label}
              type="button"
              title={item.title}
              onClick={() => setActiveView(item.view)}
              className={`h-[54px] w-[54px] rounded-[10px] border bg-[#020617] font-mono text-xs font-black transition ${
                activeView === item.view
                  ? "border-cyan-300 text-cyan-200 shadow-[0_0_28px_rgba(34,211,238,0.16)]"
                  : "border-[#1d3558] text-slate-400 hover:border-cyan-300/50 hover:text-cyan-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </aside>

        <section className="min-w-0 overflow-hidden rounded-[14px] border border-cyan-300/20 bg-[#07111f]/90 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
          <div className="flex min-h-11 items-center gap-2 border-b border-[#1d3558] bg-[#020617]/90 px-4">
            <span className="h-2.5 w-2.5 rounded-full bg-pink-400" />
            <span className="h-2.5 w-2.5 rounded-full bg-orange-400" />
            <span className="h-2.5 w-2.5 rounded-full bg-lime-300" />
            <span className="ml-2 font-mono text-xs font-bold text-slate-400">
              {activeView === "Home" ? "veritydesk home --visuals=api --ask=ready" : `veritydesk open --view=${activeView.toLowerCase().replaceAll(" ", "-")}`}
            </span>
          </div>

          <div className="p-5 md:p-7">
            {activeView === "Home" && (
              <OptionMHomeView
                healthData={healthData}
                scheduleData={scheduleData}
                ingestionError={ingestionError}
                ingestionLoading={ingestionLoading}
                reportListData={reportListData}
                reportsLoading={reportsLoading}
                reportsError={reportsError}
                visualModulesData={visualModulesData}
                visualModulesLoading={visualModulesLoading}
                visualModulesError={visualModulesError}
                agentQuery={agentQuery}
                agentLoading={agentLoading}
                agentResponse={agentResponse}
                agentError={agentError}
                personalizationProfile={personalizationProfile}
                setAgentQuery={setAgentQuery}
                setManualAgentContext={setManualAgentContext}
                submitAgentQuery={submitAgentQuery}
                openDailyBrief={() => setActiveView("Daily Brief")}
                openAgentChat={() => setActiveView("Agent Chat")}
              />
            )}
            {activeView === "Daily Brief" && (
              <DailyBriefingView
                latestItemsData={latestItemsData}
                ingestionLoading={ingestionLoading}
                reportListData={reportListData}
                reportsLoading={reportsLoading}
                reportsError={reportsError}
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
                watchItemsData={watchItemsData}
                watchItemsLoading={watchItemsLoading}
                watchItemsError={watchItemsError}
                watchEvaluationLoading={watchEvaluationLoading}
                newWatchTitle={newWatchTitle}
                newWatchQuery={newWatchQuery}
                newWatchCategory={newWatchCategory}
                companyTicker={companyTicker}
                companyName={companyName}
                companyReport={companyReport}
                companyReportLoading={companyReportLoading}
                companyReportError={companyReportError}
                setNewWatchTitle={setNewWatchTitle}
                setNewWatchQuery={setNewWatchQuery}
                setNewWatchCategory={setNewWatchCategory}
                setCompanyTicker={setCompanyTicker}
                setCompanyName={setCompanyName}
                createWatchItem={createWatchItem}
                deleteWatchItem={deleteWatchItem}
                evaluateWatchItems={evaluateWatchItems}
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
                chatSessions={chatSessions}
                activeChatSessionId={activeChatSessionId}
                setAgentQuery={setAgentQuery}
                setAgentIntent={setAgentIntent}
                setAgentTicker={setAgentTicker}
                setAgentDomain={setAgentDomain}
                setManualAgentContext={setManualAgentContext}
                submitAgentQuery={submitAgentQuery}
                createNewChatSession={createNewChatSession}
                selectChatSession={selectChatSession}
              />
            )}
            {activeView === "Settings" && (
              <SettingsView
                sourceData={sourceData}
                sourceError={sourceError}
                sourcesLoading={sourcesLoading}
                healthData={healthData}
                runsData={runsData}
                latestItemsData={latestItemsData}
                scheduleData={scheduleData}
                scheduleSaving={scheduleSaving}
                scheduleError={scheduleError}
                ingestionError={ingestionError}
                ingestionLoading={ingestionLoading}
                runMode={runMode}
                runLoading={runLoading}
                lastRunResponse={lastRunResponse}
                reportListData={reportListData}
                reportsLoading={reportsLoading}
                reportsError={reportsError}
                watchItemsData={watchItemsData}
                watchItemsLoading={watchItemsLoading}
                watchItemsError={watchItemsError}
                watchEvaluationLoading={watchEvaluationLoading}
                personalizationProfile={personalizationProfile}
                profileSavedAt={profileSavedAt}
                setRunMode={setRunMode}
                triggerIngestionRun={triggerIngestionRun}
                saveSchedule={saveSchedule}
                savePersonalizationProfile={savePersonalizationProfile}
                evaluateWatchItems={evaluateWatchItems}
                openSetup={() => setSetupOpen(true)}
              />
            )}
          </div>
        </section>

        {activeView === "Home" ? (
          <HomeProfileRail
            personalizationProfile={personalizationProfile}
            sourceStatusText={summarizeSourceStatus(healthData, ingestionLoading, ingestionError)}
            scheduleData={scheduleData}
            reportListData={reportListData}
            reportsLoading={reportsLoading}
            openSettings={() => setActiveView("Settings")}
          />
        ) : (
          <BriefingCardsPanel
            personalizationProfile={personalizationProfile}
            sourceStatusText={summarizeSourceStatus(healthData, ingestionLoading, ingestionError)}
            scheduleData={scheduleData}
            reportListData={reportListData}
            reportsLoading={reportsLoading}
            suggestionsData={suggestionsData}
            suggestionsLoading={suggestionsLoading}
            suggestionsError={suggestionsError}
            generateDailyBriefing={generateDailyBriefing}
            generateHousingReport={generateHousingReport}
            generateMarketStrategy={generateMarketStrategy}
            generateCompanyReport={generateCompanyReport}
            generateMacroReport={generateMacroReport}
            applySuggestion={applySuggestion}
            openSettings={() => setActiveView("Settings")}
          />
        )}
      </div>
    </main>
  );
}

function LoginEntryFlow({
  profile,
  sourceStatusText,
  scheduleData,
  onContinue,
  onSetup,
}: {
  profile: PersonalizationProfile;
  sourceStatusText: string;
  scheduleData: DailyScheduleConfig | null;
  onContinue: () => void;
  onSetup: () => void;
}) {
  const hasProfile = Boolean(profile.profileName || profile.location || profile.personalNote);

  return (
    <main className="min-h-screen overflow-hidden bg-[#020617] px-4 py-6 text-[#f8fafc] md:px-8">
      <div className="fixed inset-0 -z-10 bg-[linear-gradient(rgba(34,211,238,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.04)_1px,transparent_1px),radial-gradient(circle_at_78%_16%,rgba(34,211,238,0.22),transparent_30rem),radial-gradient(circle_at_18%_76%,rgba(163,230,53,0.13),transparent_28rem),#020617] bg-[length:42px_42px,42px_42px,auto,auto,auto]" />
      <section className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-6xl items-center gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(340px,0.95fr)]">
        <div>
          <div className="inline-flex items-center gap-3 rounded-full border border-cyan-300/25 bg-[#07111f]/80 px-4 py-2">
            <span className="h-2 w-2 rounded-full bg-lime-300 shadow-[0_0_18px_rgba(163,230,53,0.8)]" />
            <span className="font-mono text-xs font-black uppercase text-cyan-200">Local Intelligence Workspace</span>
          </div>
          <h1 className="mt-7 max-w-3xl text-5xl font-black leading-[0.95] text-white md:text-7xl">
            VerityDesk
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">
            Daily intelligence shaped around your location, watchlist, sources, and questions.
          </p>
          <div className="mt-8 grid max-w-2xl gap-3 sm:grid-cols-3">
            <LoginSignalCard label="Sources" value={sourceStatusText} />
            <LoginSignalCard label="Daily run" value={scheduleData?.enabled ? "On" : "Off"} />
            <LoginSignalCard label="Profile" value={hasProfile ? "Ready" : "Setup needed"} />
          </div>
        </div>

        <div className="rounded-[24px] border border-cyan-300/25 bg-[#07111f]/92 p-5 shadow-[0_30px_110px_rgba(0,0,0,0.45)] backdrop-blur">
          <div className="rounded-[18px] border border-[#1d3558] bg-[#020617]/82 p-5">
            <p className="font-mono text-xs font-black uppercase text-lime-300">Secure local entry</p>
            <h2 className="mt-3 text-3xl font-black text-white">
              {hasProfile ? `Welcome back${profile.profileName ? `, ${profile.profileName}` : ""}.` : "Set up your command center."}
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              This desktop build stores your profile on this Mac. Cloud login, database-backed profiles, and sync can plug into this same entry point during deployment.
            </p>

            <div className="mt-5 grid gap-3 rounded-xl border border-cyan-300/15 bg-[#07111f]/60 p-4">
              <SourceStripRow label="Location" value={profile.location || "Not set"} />
              <SourceStripRow label="Watchlist" value={compactListLabel(splitList(profile.watchlist))} />
              <SourceStripRow label="Briefing time" value={profile.briefingTime || "08:00"} />
            </div>

            <div className="mt-6 grid gap-3">
              <button
                type="button"
                onClick={hasProfile ? onContinue : onSetup}
                className="min-h-12 rounded-xl bg-lime-300 px-5 text-sm font-black text-[#102000] transition hover:bg-lime-200"
              >
                {hasProfile ? "Open VerityDesk" : "Start Setup"}
              </button>
              <button
                type="button"
                onClick={onSetup}
                className="min-h-12 rounded-xl border border-cyan-300/30 px-5 text-sm font-black text-cyan-200 transition hover:border-cyan-300/70"
              >
                {hasProfile ? "Review Setup" : "Continue Without Account"}
              </button>
            </div>

            <p className="mt-5 text-xs leading-5 text-slate-500">
              No investment advice. Research and educational use only.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

function LoginSignalCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-cyan-300/20 bg-[#07111f]/76 p-4">
      <p className="font-mono text-[11px] font-black uppercase text-slate-500">{label}</p>
      <p className="mt-2 truncate text-sm font-black text-cyan-100">{value}</p>
    </div>
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

function OptionMHomeView({
  healthData,
  scheduleData,
  ingestionError,
  ingestionLoading,
  reportListData,
  reportsLoading,
  reportsError,
  visualModulesData,
  visualModulesLoading,
  visualModulesError,
  agentQuery,
  agentLoading,
  agentResponse,
  agentError,
  personalizationProfile,
  setAgentQuery,
  setManualAgentContext,
  submitAgentQuery,
  openDailyBrief,
  openAgentChat,
}: {
  healthData: SourceHealthResponse | null;
  scheduleData: DailyScheduleConfig | null;
  ingestionError: string | null;
  ingestionLoading: boolean;
  reportListData: ReportListResponse | null;
  reportsLoading: boolean;
  reportsError: string | null;
  visualModulesData: VisualModulesApiResponse | null;
  visualModulesLoading: boolean;
  visualModulesError: string | null;
  agentQuery: string;
  agentLoading: boolean;
  agentResponse: AgentResponse | null;
  agentError: string | null;
  personalizationProfile: PersonalizationProfile;
  setAgentQuery: (value: string) => void;
  setManualAgentContext: (value: boolean) => void;
  submitAgentQuery: (event: FormEvent<HTMLFormElement>) => void;
  openDailyBrief: () => void;
  openAgentChat: () => void;
}) {
  const latestReport = reportListData?.reports[0] ?? null;
  const sourceStatusText = summarizeSourceStatus(healthData, ingestionLoading, ingestionError);
  const inferredContext = inferAgentContext(agentQuery, personalizationProfile);
  const fallbackModules = buildHomeVisualModules({
    profile: personalizationProfile,
    reports: reportListData?.reports ?? [],
    healthData,
    scheduleData,
  });
  const modules = visualModulesData?.modules.length ? visualModulesData.modules.map(mapVisualModuleFromApi) : fallbackModules;
  const [selectedModule, setSelectedModule] = useState<HomeVisualModule | null>(null);

  function askAboutModule(module: HomeVisualModule) {
    const contextLines = [
      module.suggestedPrompt,
      "",
      `Visual: ${module.title}`,
      `Status: ${module.status}`,
      `Primary signal: ${module.value} (${module.label})`,
      `Summary: ${module.summary}`,
      module.stats.length > 0 ? `Stats: ${module.stats.map((stat) => `${stat.label} ${stat.value}`).join("; ")}` : null,
      module.sources.length > 0 ? `Sources: ${module.sources.map((source) => `${source.name} (${source.status})`).join("; ")}` : null,
    ].filter(Boolean);

    setAgentQuery(contextLines.join("\n"));
    setManualAgentContext(false);
    openAgentChat();
  }

  return (
    <div className="grid gap-5">
      <section className="grid gap-5 xl:grid-cols-[minmax(0,0.92fr)_minmax(340px,0.55fr)]">
        <div className="rounded-[22px] border border-cyan-300/20 bg-[radial-gradient(circle_at_82%_18%,rgba(34,211,238,0.18),transparent_18rem),#020617]/90 p-5 md:p-6">
          <p className="font-mono text-xs font-black uppercase text-lime-300">Home / visual intelligence</p>
          <h1 className="mt-4 max-w-4xl text-[clamp(2.7rem,6vw,5rem)] font-black leading-[0.92] text-white">
            Read the signal. Ask the rest.
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-400">
            A cleaner daily surface powered by source refreshes, saved reports, and live web answers.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <NeonChip variant="live">{sourceStatusText}</NeonChip>
            <NeonChip>{scheduleData?.enabled ? "Daily run on" : "Daily run off"}</NeonChip>
            <NeonChip variant="search">{formatAgentIntent(inferredContext.intent)}</NeonChip>
          </div>
        </div>

        <div className="rounded-[22px] border border-lime-300/20 bg-[#061320]/90 p-5">
          <p className="font-mono text-xs font-black uppercase text-cyan-300">Today&apos;s brief</p>
          <h2 className="mt-3 text-2xl font-black text-white">
            {latestReport ? latestReport.title : "No saved brief yet"}
          </h2>
          <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-400">
            {cleanAnswerText(latestReport?.summary ?? latestReport?.body) ?? "Generate a daily brief or ask a question to start building today&apos;s intelligence layer."}
          </p>
          <button
            type="button"
            onClick={openDailyBrief}
            className="mt-5 min-h-10 rounded-lg border border-cyan-300/30 px-4 text-sm font-black text-cyan-200 transition hover:border-cyan-300/70"
          >
            Open Daily Brief
          </button>
        </div>
      </section>

      <form
        onSubmit={(event) => {
          openAgentChat();
          submitAgentQuery(event);
        }}
        className="rounded-xl border border-cyan-300/30 bg-[#020617] p-4 shadow-[inset_0_0_0_1px_rgba(163,230,53,0.04)]"
      >
        <label className="sr-only" htmlFor="console-question">
          Question
        </label>
        <textarea
          id="console-question"
          value={agentQuery}
          onChange={(event) => {
            setAgentQuery(event.target.value);
            setManualAgentContext(false);
          }}
          placeholder="Ask about markets, housing, companies, rates, world news, or what matters today."
          className="min-h-36 w-full resize-y border-0 bg-transparent text-xl leading-8 text-white outline-none placeholder:text-slate-600 md:text-2xl"
        />
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[#1d3558] pt-4">
          <div className="flex flex-wrap gap-2">
            <NeonChip variant="live">Tavily web search</NeonChip>
            <NeonChip variant="search">APIs verify</NeonChip>
            <NeonChip>{personalizationProfile.location ? `${personalizationProfile.location} context` : "Profile context"}</NeonChip>
          </div>
          <button
            type="submit"
            disabled={agentLoading || !agentQuery.trim()}
            className="min-h-11 rounded-lg bg-lime-300 px-5 text-sm font-black text-[#102000] disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
          >
            {agentLoading ? "Thinking" : "Ask"}
          </button>
        </div>
      </form>

      <section className="grid gap-4 xl:grid-cols-5">
        {visualModulesLoading && !visualModulesData && (
          <div className="rounded-[20px] border border-[#1d3558] bg-[#061320]/88 p-4 text-sm text-slate-400 xl:col-span-5">
            Loading visual modules.
          </div>
        )}
        {visualModulesError && (
          <div className="rounded-[20px] border border-orange-300/30 bg-orange-950/20 p-4 text-sm text-orange-100 xl:col-span-5">
            Using local fallback visuals. {visualModulesError}
          </div>
        )}
        {modules.map((module) => (
          <HomeVisualModuleCard key={module.id} module={module} onOpen={setSelectedModule} />
        ))}
      </section>

      {selectedModule && (
        <VisualDrillDownView
          module={selectedModule}
          onClose={() => setSelectedModule(null)}
          onAsk={() => askAboutModule(selectedModule)}
        />
      )}

      <section className="rounded-xl border border-[#1d3558] bg-[#0a1628]/75 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Answer</p>
            <h2 className="mt-1 text-2xl font-bold text-white">
              {agentResponse ? "Here is what VerityDesk found." : latestReport ? latestReport.title : "Ready when you are."}
            </h2>
          </div>
          {agentResponse && <NeonChip variant="live">Confidence: {agentResponse.confidence}</NeonChip>}
        </div>

        {agentError && <p className="mt-4 rounded-lg border border-red-300/30 bg-red-950/30 p-3 text-sm text-red-200">{agentError}</p>}
        {reportsError && !agentResponse && (
          <p className="mt-4 rounded-lg border border-red-300/30 bg-red-950/30 p-3 text-sm text-red-200">{reportsError}</p>
        )}
        {reportsLoading && !agentResponse && <p className="mt-4 text-sm text-slate-400">Loading the latest saved briefing.</p>}

        {!agentResponse && !agentError && !reportsLoading && (
          <div className="mt-4">
            <MarkdownAnswer
              text={cleanAnswerText(latestReport?.summary ?? latestReport?.body) ?? "Ask a question or click one of the briefing cards to start."}
            />
            {latestReport && (
              <div className="mt-4 flex flex-wrap gap-2">
                <NeonChip>Retrieved {formatDateTime(latestReport.as_of ?? latestReport.created_at)}</NeonChip>
                <NeonChip>{latestReport.citations.length} sources</NeonChip>
              </div>
            )}
          </div>
        )}

        {agentResponse && (
          <div className="mt-4 space-y-4">
            <MarkdownAnswer text={agentResponse.summary} />
            <p className="rounded-lg border border-[#1d3558] bg-[#020617]/70 p-3 text-xs leading-5 text-slate-400">
              {FINANCIAL_DISCLAIMER}
            </p>
            <EvidenceDrawer response={agentResponse} />
          </div>
        )}
      </section>
    </div>
  );
}

function HomeVisualModuleCard({ module, onOpen }: { module: HomeVisualModule; onOpen: (module: HomeVisualModule) => void }) {
  const accentClass = {
    lime: "border-lime-300/35 text-lime-300",
    cyan: "border-cyan-300/35 text-cyan-300",
    pink: "border-pink-300/35 text-pink-300",
    orange: "border-orange-300/35 text-orange-300",
    violet: "border-violet-300/35 text-violet-300",
  }[module.accent];
  const glowClass = {
    lime: "bg-lime-300 shadow-[0_0_24px_rgba(163,230,53,0.45)]",
    cyan: "bg-cyan-300 shadow-[0_0_24px_rgba(34,211,238,0.45)]",
    pink: "bg-pink-300 shadow-[0_0_24px_rgba(249,168,212,0.45)]",
    orange: "bg-orange-300 shadow-[0_0_24px_rgba(253,186,116,0.45)]",
    violet: "bg-violet-300 shadow-[0_0_24px_rgba(196,181,253,0.45)]",
  }[module.accent];

  return (
    <button
      type="button"
      onClick={() => onOpen(module)}
      className={`group min-h-[250px] rounded-[20px] border bg-[#061320]/88 p-4 text-left transition hover:-translate-y-0.5 hover:bg-[#08182a] ${accentClass}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] font-black uppercase text-slate-500">{module.status}</p>
          <h3 className="mt-2 text-xl font-black text-white">{module.title}</h3>
        </div>
        <span className={`h-2.5 w-2.5 rounded-full ${glowClass}`} />
      </div>
      <div className="mt-5">
        <p className="text-4xl font-black text-white">{module.value}</p>
        <p className="mt-1 text-xs font-bold uppercase tracking-normal text-slate-500">{module.label}</p>
      </div>
      <MiniBarChart points={module.points} accent={module.accent} />
      <p className="mt-4 line-clamp-3 text-sm leading-6 text-slate-400">{module.summary}</p>
      <p className="mt-4 font-mono text-[11px] font-black uppercase text-slate-500 group-hover:text-cyan-200">Open detail</p>
    </button>
  );
}

function VisualDrillDownView({
  module,
  onClose,
  onAsk,
}: {
  module: HomeVisualModule;
  onClose: () => void;
  onAsk: () => void;
}) {
  const accentClass = {
    lime: "border-lime-300/40 text-lime-300",
    cyan: "border-cyan-300/40 text-cyan-300",
    pink: "border-pink-300/40 text-pink-300",
    orange: "border-orange-300/40 text-orange-300",
    violet: "border-violet-300/40 text-violet-300",
  }[module.accent];

  return (
    <section className={`rounded-[24px] border bg-[#061320]/95 p-5 shadow-[0_28px_90px_rgba(0,0,0,0.38)] ${accentClass}`}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="font-mono text-xs font-black uppercase text-slate-500">Visual detail / {module.status}</p>
          <h2 className="mt-2 text-4xl font-black leading-none text-white">{module.title}</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">{module.summary}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onAsk}
            className="min-h-10 rounded-lg bg-lime-300 px-4 text-sm font-black text-[#102000]"
          >
            Ask About This
          </button>
          <button
            type="button"
            onClick={onClose}
            className="min-h-10 rounded-lg border border-[#1d3558] px-4 text-sm font-black text-slate-300 transition hover:border-cyan-300/60 hover:text-cyan-200"
          >
            Close
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <div className="rounded-[18px] border border-[#1d3558] bg-[#020617]/80 p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-5xl font-black text-white">{module.value}</p>
              <p className="mt-1 text-xs font-black uppercase text-slate-500">{module.label}</p>
            </div>
            <NeonChip>Updated {formatDateTime(module.updatedAt)}</NeonChip>
          </div>
          <LargeBarChart module={module} />
        </div>

        <div className="grid gap-4">
          <div className="rounded-[18px] border border-[#1d3558] bg-[#020617]/76 p-4">
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Key stats</p>
            <div className="mt-4 grid gap-3">
              {module.stats.length === 0 ? (
                <p className="text-sm text-slate-500">No structured stats yet.</p>
              ) : (
                module.stats.map((stat) => (
                  <div key={`${stat.label}-${stat.value}`} className="rounded-xl border border-[#1d3558] bg-[#061320]/70 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-bold text-slate-300">{stat.label}</span>
                      <span className="font-mono text-sm font-black text-white">{stat.value}</span>
                    </div>
                    {stat.detail && <p className="mt-1 text-xs leading-5 text-slate-500">{stat.detail}</p>}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      <details className="mt-4 rounded-[18px] border border-[#1d3558] bg-[#020617]/72 p-4">
        <summary className="cursor-pointer font-mono text-xs font-black uppercase text-cyan-300">View sources</summary>
        <div className="mt-4 grid gap-3">
          {module.sources.length === 0 ? (
            <p className="text-sm text-slate-500">No connected sources are attached to this visual yet.</p>
          ) : (
            module.sources.map((source) => (
              <div key={`${source.name}-${source.retrievedAt}`} className="rounded-xl border border-[#1d3558] bg-[#061320]/70 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-bold text-white">{source.name}</p>
                  <NeonChip>{titleCase(source.status.replaceAll("_", " "))}</NeonChip>
                </div>
                <p className="mt-1 text-xs text-slate-500">Retrieved {formatDateTime(source.retrievedAt)}</p>
                {source.description && <p className="mt-2 text-sm leading-5 text-slate-400">{source.description}</p>}
              </div>
            ))
          )}
        </div>
      </details>
    </section>
  );
}

function LargeBarChart({ module }: { module: HomeVisualModule }) {
  const maxPoint = Math.max(...module.points, 1);
  const barClass = {
    lime: "bg-lime-300",
    cyan: "bg-cyan-300",
    pink: "bg-pink-300",
    orange: "bg-orange-300",
    violet: "bg-violet-300",
  }[module.accent];

  return (
    <div className="mt-6 flex h-64 items-end gap-2 rounded-[18px] border border-[#1d3558] bg-[#061320]/70 px-4 py-4">
      {module.points.map((point, index) => (
        <div key={`${point}-${index}`} className="flex h-full flex-1 flex-col justify-end gap-2">
          <span
            className={`min-h-3 rounded-t-md opacity-90 ${barClass}`}
            style={{ height: `${Math.max(5, (point / maxPoint) * 100)}%` }}
          />
          <span className="text-center font-mono text-[10px] font-black text-slate-600">{index + 1}</span>
        </div>
      ))}
    </div>
  );
}

function MiniBarChart({ points, accent }: { points: number[]; accent: HomeVisualModule["accent"] }) {
  const maxPoint = Math.max(...points, 1);
  const barClass = {
    lime: "bg-lime-300",
    cyan: "bg-cyan-300",
    pink: "bg-pink-300",
    orange: "bg-orange-300",
    violet: "bg-violet-300",
  }[accent];

  return (
    <div className="mt-5 flex h-16 items-end gap-1.5 rounded-xl border border-[#1d3558] bg-[#020617]/76 px-3 py-2">
      {points.map((point, index) => (
        <span
          key={`${point}-${index}`}
          className={`w-full rounded-t-sm opacity-85 ${barClass}`}
          style={{ height: `${Math.max(12, (point / maxPoint) * 100)}%` }}
        />
      ))}
    </div>
  );
}

function HomeProfileRail({
  personalizationProfile,
  sourceStatusText,
  scheduleData,
  reportListData,
  reportsLoading,
  openSettings,
}: {
  personalizationProfile: PersonalizationProfile;
  sourceStatusText: string;
  scheduleData: DailyScheduleConfig | null;
  reportListData: ReportListResponse | null;
  reportsLoading: boolean;
  openSettings: () => void;
}) {
  const latestReport = reportListData?.reports[0] ?? null;

  return (
    <aside className="grid content-start gap-4 rounded-[14px] border border-cyan-300/20 bg-[#07111f]/90 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
      <section className="rounded-[18px] border border-cyan-300/20 bg-[#020617]/80 p-4">
        <p className="font-mono text-xs font-black uppercase text-lime-300">Profile</p>
        <h2 className="mt-3 text-2xl font-black text-white">{personalizationProfile.profileName || "My VerityDesk"}</h2>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          {personalizationProfile.personalNote || "Add a short note in Settings so answers and daily briefs know what matters to you."}
        </p>
        <button
          type="button"
          onClick={openSettings}
          className="mt-4 min-h-10 rounded-lg border border-cyan-300/30 px-4 text-sm font-black text-cyan-200 transition hover:border-cyan-300/70"
        >
          Tune Profile
        </button>
      </section>

      <section className="rounded-[18px] border border-[#1d3558] bg-[#020617]/70 p-4">
        <p className="font-mono text-xs font-black uppercase text-cyan-300">Status</p>
        <div className="mt-4 grid gap-3">
          <SourceStripRow label="Sources" value={sourceStatusText} />
          <SourceStripRow label="Daily run" value={scheduleData?.enabled ? "On" : "Off"} />
          <SourceStripRow label="Next" value={formatDateTime(scheduleData?.next_run_at)} />
          <SourceStripRow label="Location" value={personalizationProfile.location || "Not set"} />
          <SourceStripRow label="Watchlist" value={compactListLabel(splitList(personalizationProfile.watchlist))} />
        </div>
      </section>

      <section className="rounded-[18px] border border-[#1d3558] bg-[#020617]/70 p-4">
        <p className="font-mono text-xs font-black uppercase text-pink-300">Latest saved</p>
        <p className="mt-3 text-sm font-bold text-white">
          {reportsLoading ? "Loading..." : latestReport?.title ?? "No report yet"}
        </p>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          {latestReport ? `Retrieved ${formatDateTime(latestReport.as_of ?? latestReport.created_at)}` : "Daily cards will fill in after refreshes and brief generation."}
        </p>
      </section>
    </aside>
  );
}

function BriefingCardsPanel({
  personalizationProfile,
  sourceStatusText,
  scheduleData,
  reportListData,
  reportsLoading,
  suggestionsData,
  suggestionsLoading,
  suggestionsError,
  generateDailyBriefing,
  generateHousingReport,
  generateMarketStrategy,
  generateCompanyReport,
  generateMacroReport,
  applySuggestion,
  openSettings,
}: {
  personalizationProfile: PersonalizationProfile;
  sourceStatusText: string;
  scheduleData: DailyScheduleConfig | null;
  reportListData: ReportListResponse | null;
  reportsLoading: boolean;
  suggestionsData: ProactiveSuggestionsResponse | null;
  suggestionsLoading: boolean;
  suggestionsError: string | null;
  generateDailyBriefing: () => void;
  generateHousingReport: () => void;
  generateMarketStrategy: () => void;
  generateCompanyReport: () => void;
  generateMacroReport: () => void;
  applySuggestion: (suggestion: ProactiveSuggestion) => void;
  openSettings: () => void;
}) {
  const panels = buildDailyTopicPanels({
    profile: personalizationProfile,
    reports: reportListData?.reports ?? [],
    generateDailyBriefing,
    generateHousingReport,
    generateMarketStrategy,
    generateCompanyReport,
    generateMacroReport,
  });

  return (
    <aside className="grid content-start gap-4 rounded-[14px] border border-cyan-300/20 bg-[#07111f]/90 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white">Today&apos;s Panels</h2>
          <p className="mt-1 font-mono text-xs font-black uppercase text-slate-500">Saved daily intelligence</p>
        </div>
        <button type="button" onClick={openSettings} className="text-sm font-bold text-cyan-300">
          Tune
        </button>
      </div>

      {reportsLoading ? (
        <div className="rounded-xl border border-[#1d3558] bg-[#020617]/80 p-4 text-sm text-slate-400">
          Loading saved daily panels.
        </div>
      ) : (
        panels.map((panel) => <DailyTopicPanelCard key={panel.title} panel={panel} />)
      )}

      <div className="rounded-xl border border-[#1d3558] bg-[#020617]/80 p-4">
        <p className="font-mono text-xs font-black uppercase text-cyan-300">System</p>
        <div className="mt-3 grid gap-2">
          <SourceStripRow label="Sources" value={sourceStatusText} />
          <SourceStripRow label="Daily run" value={scheduleData?.enabled ? "On" : "Off"} />
          <SourceStripRow label="Next run" value={formatDateTime(scheduleData?.next_run_at)} />
          <SourceStripRow label="Location" value={personalizationProfile.location || "Set in Settings"} />
        </div>
      </div>

      <details className="rounded-xl border border-[#1d3558] bg-[#020617]/60 p-4">
        <summary className="cursor-pointer font-mono text-xs font-black uppercase text-slate-400">Suggested next questions</summary>
        {suggestionsLoading && <p className="mt-3 text-sm text-slate-400">Loading suggestions.</p>}
        {suggestionsError && <p className="mt-3 text-sm text-red-200">{suggestionsError}</p>}
        {!suggestionsLoading && !suggestionsError && (
          <div className="mt-3 grid gap-2">
            {(suggestionsData?.suggestions ?? []).slice(0, 3).map((suggestion) => (
              <button
                key={suggestion.id}
                type="button"
                onClick={() => applySuggestion(suggestion)}
                className="rounded-lg border border-[#1d3558] px-3 py-2 text-left text-sm leading-5 text-slate-300 hover:border-cyan-300/50"
              >
                {suggestion.title}
              </button>
            ))}
            {(!suggestionsData || suggestionsData.suggestions.length === 0) && (
              <p className="text-sm text-slate-400">No suggestions available yet.</p>
            )}
          </div>
        )}
      </details>
    </aside>
  );
}

type DailyTopicPanel = {
  title: string;
  description: string;
  report: ReportResponse | null;
  borderClass: string;
  dotClass: string;
  onRefresh: () => void;
};

function DailyTopicPanelCard({ panel }: { panel: DailyTopicPanel }) {
  const body = cleanAnswerText(panel.report?.summary ?? panel.report?.body);
  const signalLabel = reportMetadataText(panel.report, "signal_label") ?? (panel.report ? "Developing" : "No panel yet");
  const changeLabel = reportMetadataText(panel.report, "change_label") ?? "Waiting";

  return (
    <section className={`rounded-xl border bg-[#020617] p-4 ${panel.borderClass}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-lg font-bold text-white">{panel.title}</p>
          <p className="mt-1 text-xs font-semibold uppercase text-slate-500">
            {panel.report ? `Updated ${formatDateTime(panel.report.as_of ?? panel.report.created_at)}` : "Waiting for daily refresh"}
          </p>
        </div>
        <span className={`mt-2 h-2 w-2 rounded-full ${panel.dotClass}`} />
      </div>
      <p className="mt-3 text-sm leading-5 text-slate-400">
        {body ? compactText(body, 210) : panel.description}
      </p>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-2">
          <NeonChip variant={signalChipVariant(signalLabel)}>{signalLabel}</NeonChip>
          <NeonChip>{`Change: ${changeLabel}`}</NeonChip>
          {panel.report && <NeonChip>{panel.report.citations.length} sources</NeonChip>}
        </div>
        <button
          type="button"
          onClick={panel.onRefresh}
          className="min-h-9 rounded-lg border border-cyan-300/30 px-3 text-xs font-black text-cyan-200 transition hover:border-cyan-300/70"
        >
          Refresh
        </button>
      </div>
      {panel.report && (
        <div className="mt-3">
          <ReportEvidenceDrawer report={panel.report} />
        </div>
      )}
    </section>
  );
}

function reportMetadataText(report: ReportResponse | null | undefined, key: string) {
  const value = report?.metadata?.[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function signalChipVariant(signalLabel: string): "live" | "search" | undefined {
  if (signalLabel === "High Signal") {
    return "live";
  }
  if (signalLabel === "Developing") {
    return "search";
  }
  return undefined;
}

function ConsoleMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[#1d3558] bg-[#020617]/70 p-4">
      <p className="font-mono text-xs font-black uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-bold text-white">{value}</p>
    </div>
  );
}

function NeonChip({ children, variant }: { children: ReactNode; variant?: "live" | "search" }) {
  const className =
    variant === "live"
      ? "border-lime-300/45 text-lime-300"
      : variant === "search"
        ? "border-cyan-300/45 text-cyan-300"
        : "border-[#1d3558] text-slate-400";

  return (
    <span className={`inline-flex rounded-full border px-3 py-1.5 text-xs font-black ${className}`}>
      {children}
    </span>
  );
}

function SourceStripRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm font-semibold text-slate-400">{label}</span>
      <span className="text-right font-mono text-xs font-black text-lime-300">{value}</span>
    </div>
  );
}

function SetupProfileFlow({
  profile,
  sourceStatusText,
  scheduleData,
  onSave,
  onSkip,
}: {
  profile: PersonalizationProfile;
  sourceStatusText: string;
  scheduleData: DailyScheduleConfig | null;
  onSave: (profile: PersonalizationProfile) => void;
  onSkip: () => void;
}) {
  const [draft, setDraft] = useState<PersonalizationProfile>(profile);

  useEffect(() => {
    setDraft(profile);
  }, [profile]);

  function updateDraft(patch: Partial<PersonalizationProfile>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function toggleDraftOption(field: "priorityTopics" | "housingInterests" | "macroInterests", value: string) {
    setDraft((current) => {
      const currentValues = current[field];
      const nextValues = currentValues.includes(value)
        ? currentValues.filter((item) => item !== value)
        : [...currentValues, value];
      return { ...current, [field]: nextValues };
    });
  }

  function submitSetup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(normalizePersonalizationProfile(draft));
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#020617]/92 px-4 py-6 backdrop-blur-md">
      <form
        onSubmit={submitSetup}
        className="mx-auto grid max-w-5xl gap-5 rounded-2xl border border-cyan-300/25 bg-[#07111f] p-5 shadow-[0_30px_120px_rgba(0,0,0,0.55)] md:p-7"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-sm font-black uppercase text-lime-300">VerityDesk setup</p>
            <h1 className="mt-3 max-w-3xl text-4xl font-black leading-none text-white md:text-5xl">
              Tell it once. Let it brief you daily.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-400">
              Create a local profile so VerityDesk can personalize daily panels, chatbot answers, sources, and watch items without asking for the same context every time.
            </p>
          </div>
          <button
            type="button"
            onClick={onSkip}
            className="min-h-10 rounded-lg border border-[#1d3558] px-4 text-sm font-black text-slate-300 transition hover:border-cyan-300/50 hover:text-cyan-200"
          >
            Skip For Now
          </button>
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
          <section className="rounded-xl border border-cyan-300/20 bg-[#020617]/70 p-4">
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Profile</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <SettingsTextInput
                id="setup-profile-name"
                label="Profile name"
                value={draft.profileName}
                placeholder="Adith's briefing"
                onChange={(value) => updateDraft({ profileName: value })}
              />
              <SettingsTextInput
                id="setup-location"
                label="Primary location"
                value={draft.location}
                placeholder="Phoenix, AZ"
                onChange={(value) => updateDraft({ location: value })}
              />
              <SettingsTextInput
                id="setup-housing"
                label="Housing markets"
                value={draft.housingMarkets}
                placeholder="Phoenix, Scottsdale, Tucson"
                onChange={(value) => updateDraft({ housingMarkets: value })}
              />
              <SettingsTextInput
                id="setup-watchlist"
                label="Watchlist"
                value={draft.watchlist}
                placeholder="SPY, QQQ, TLT"
                onChange={(value) => updateDraft({ watchlist: value.toUpperCase() })}
              />
              <SettingsTextInput
                id="setup-companies"
                label="Companies"
                value={draft.companies}
                placeholder="Apple, Nvidia, Tesla"
                onChange={(value) => updateDraft({ companies: value })}
              />
              <SettingsTextInput
                id="setup-sectors"
                label="Sectors"
                value={draft.sectors}
                placeholder="AI, homebuilders, banks"
                onChange={(value) => updateDraft({ sectors: value })}
              />
            </div>
            <label className="mt-4 block text-sm font-bold text-slate-200" htmlFor="setup-note">
              What should VerityDesk know?
              <textarea
                id="setup-note"
                value={draft.personalNote}
                onChange={(event) => updateDraft({ personalNote: event.target.value })}
                placeholder="Example: Keep answers practical. I care about Arizona housing, mortgage rates, broad market risk, and long-term tech."
                className="mt-2 min-h-28 w-full resize-y rounded-xl border border-[#1d3558] bg-[#020617] px-4 py-3 text-sm leading-6 text-slate-300 outline-none focus:border-cyan-300"
              />
            </label>
          </section>

          <section className="grid gap-4">
            <div className="rounded-xl border border-lime-300/25 bg-[linear-gradient(135deg,rgba(163,230,53,0.12),transparent_42%),#020617] p-4">
              <p className="font-mono text-xs font-black uppercase text-lime-300">Local access</p>
              <h2 className="mt-2 text-xl font-bold text-white">Saved on this Mac</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                This setup creates a local profile for personalization. A simple local passcode or full account login can be added when cloud sync becomes necessary.
              </p>
            </div>
            <div className="rounded-xl border border-cyan-300/20 bg-[#020617]/70 p-4">
              <p className="font-mono text-xs font-black uppercase text-cyan-300">System check</p>
              <div className="mt-4 grid gap-2">
                <SourceStripRow label="Sources" value={sourceStatusText} />
                <SourceStripRow label="Daily run" value={scheduleData?.enabled ? "On" : "Off"} />
                <SourceStripRow label="Briefing time" value={formatScheduleTime(scheduleData)} />
              </div>
            </div>
            <div className="rounded-xl border border-[#1d3558] bg-[#020617]/70 p-4">
              <p className="font-mono text-xs font-black uppercase text-slate-500">Output style</p>
              <div className="mt-3 grid gap-3">
                <SettingsSelect
                  id="setup-briefing-style"
                  label="Briefing detail"
                  value={draft.briefingStyle}
                  onChange={(value) => updateDraft({ briefingStyle: value as PersonalizationProfile["briefingStyle"] })}
                  options={[
                    ["quick", "Quick"],
                    ["balanced", "Balanced"],
                    ["detailed", "Detailed"],
                  ]}
                />
                <SettingsTextInput
                  id="setup-briefing-time"
                  label="Preferred briefing time"
                  type="time"
                  value={draft.briefingTime}
                  onChange={(value) => updateDraft({ briefingTime: value })}
                />
              </div>
            </div>
          </section>
        </div>

        <section className="grid gap-4 lg:grid-cols-3">
          <CheckboxGroup
            title="Topics"
            options={topicOptions}
            values={draft.priorityTopics}
            onToggle={(value) => toggleDraftOption("priorityTopics", value)}
          />
          <CheckboxGroup
            title="Housing"
            options={housingInterestOptions}
            values={draft.housingInterests}
            onToggle={(value) => toggleDraftOption("housingInterests", value)}
          />
          <CheckboxGroup
            title="Macro"
            options={macroInterestOptions}
            values={draft.macroInterests}
            onToggle={(value) => toggleDraftOption("macroInterests", value)}
          />
        </section>

        <div className="flex flex-col gap-3 border-t border-[#1d3558] pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm leading-6 text-slate-400">
            You can change all of this later in Settings.
          </p>
          <button
            type="submit"
            className="min-h-11 rounded-lg bg-lime-300 px-5 text-sm font-black text-[#102000]"
          >
            Save And Start
          </button>
        </div>
      </form>
    </div>
  );
}

function buildBriefingCards(profile: PersonalizationProfile) {
  const location = profile.location || "my saved area";
  const housingMarkets = compactListLabel(splitList(profile.housingMarkets));
  const watchlist = compactListLabel(splitList(profile.watchlist));
  const marketFocus = compactListLabel(profile.priorityTopics);
  const sectors = compactListLabel(splitList(profile.sectors));
  const promptContext = cardPromptContext(profile);

  return [
    {
      title: "Local Housing Pulse",
      description: `Rates, affordability, inventory, and local housing signals for ${housingMarkets === "Not set" ? location : housingMarkets}.`,
      prompt: [
        `Give me a local housing pulse for ${housingMarkets === "Not set" ? location : housingMarkets}.`,
        "Use a simple structure: Bottom Line, Major Trends, What Changed Recently, Why It Matters To Me, What To Watch Next, and Uncertainty/Data Gaps.",
        "Cover trends in mortgage rates, affordability, inventory, prices, buyer/seller leverage, rent-vs-buy pressure, local demand, and local news.",
        "For each major trend, say whether it looks strengthening, weakening, mixed, or unclear.",
        "Use live web research first, then verify with housing and macro APIs where useful.",
        promptContext,
      ].join("\n"),
      borderClass: "border-cyan-300/30",
      dotClass: "bg-cyan-300 shadow-[0_0_24px_rgba(34,211,238,0.8)]",
    },
    {
      title: "Market Setup",
      description: `Indexes, rates, sector tone, volatility, and risks based on ${marketFocus}.`,
      prompt: [
        "Give me today's market setup.",
        `Focus on my priority topics (${marketFocus}) and sectors (${sectors}).`,
        "Use a simple structure: Bottom Line, Major Trends, What Changed Recently, Why It Matters To Me, What To Watch Next, and Uncertainty/Data Gaps.",
        "Cover trends in indexes, rates/yields, sector rotation, volatility, commodities, macro sentiment, liquidity, and risk appetite.",
        "For each major trend, say whether it looks strengthening, weakening, mixed, or unclear.",
        "Do not give direct buy, sell, or hold recommendations.",
        promptContext,
      ].join("\n"),
      borderClass: "border-lime-300/30",
      dotClass: "bg-lime-300 shadow-[0_0_24px_rgba(163,230,53,0.8)]",
    },
    {
      title: "Watchlist Moves",
      description: `News, filings, earnings, analyst signals, and catalysts for ${watchlist === "Not set" ? "my watchlist" : watchlist}.`,
      prompt: [
        `What changed for ${watchlist === "Not set" ? "the companies and tickers I follow" : watchlist} recently?`,
        "Use a simple structure: Bottom Line, Major Trends, What Changed Recently, Why It Matters To Me, What To Watch Next, and Uncertainty/Data Gaps.",
        "Cover trends in earnings expectations, guidance, filings, analyst revisions, product momentum, sentiment, sector pressure, and major catalysts.",
        "For each major trend, say whether it looks strengthening, weakening, mixed, or unclear.",
        "Explain why each item matters and what to monitor next without direct trading instructions.",
        promptContext,
      ].join("\n"),
      borderClass: "border-pink-300/30",
      dotClass: "bg-pink-300 shadow-[0_0_24px_rgba(244,114,182,0.8)]",
    },
    {
      title: "World Risk Radar",
      description: "Geopolitics, commodities, policy, regulation, and market spillovers.",
      prompt: [
        "Give me a world risk radar update.",
        "Use a simple structure: Bottom Line, Major Trends, What Changed Recently, Why It Matters To Me, What To Watch Next, and Uncertainty/Data Gaps.",
        "Cover trends in geopolitics, energy/commodities, regulation/policy, trade/tariffs, inflation pressure, capital flows, and investor sentiment.",
        "For each major trend, say whether it looks strengthening, weakening, mixed, or unclear.",
        `Prioritize what matters to my interests (${marketFocus}) and risk preference (${formatProfileChoice(profile.riskPreference)}).`,
        promptContext,
      ].join("\n"),
      borderClass: "border-orange-300/30",
      dotClass: "bg-orange-300 shadow-[0_0_24px_rgba(251,146,60,0.8)]",
    },
  ];
}

function buildDailyTopicPanels({
  profile,
  reports,
  generateDailyBriefing,
  generateHousingReport,
  generateMarketStrategy,
  generateCompanyReport,
  generateMacroReport,
}: {
  profile: PersonalizationProfile;
  reports: ReportResponse[];
  generateDailyBriefing: () => void;
  generateHousingReport: () => void;
  generateMarketStrategy: () => void;
  generateCompanyReport: () => void;
  generateMacroReport: () => void;
}): DailyTopicPanel[] {
  const latestByType = latestReportByType(reports);
  const location = profile.location || compactListLabel(splitList(profile.housingMarkets));
  const watchlist = compactListLabel(splitList(profile.watchlist));

  return [
    {
      title: "Daily Briefing",
      description: "Today's personal intelligence summary will appear here after the daily refresh runs.",
      report: latestByType.get("daily_briefing") ?? null,
      borderClass: "border-lime-300/35",
      dotClass: "bg-lime-300 shadow-[0_0_24px_rgba(163,230,53,0.8)]",
      onRefresh: generateDailyBriefing,
    },
    {
      title: "Local Housing Pulse",
      description: `Rates, affordability, inventory, and local housing signals for ${location === "Not set" ? "your saved area" : location}.`,
      report: latestByType.get("housing") ?? null,
      borderClass: "border-cyan-300/30",
      dotClass: "bg-cyan-300 shadow-[0_0_24px_rgba(34,211,238,0.8)]",
      onRefresh: generateHousingReport,
    },
    {
      title: "Market Setup",
      description: "Indexes, rates, sector tone, volatility, commodities, and macro risk.",
      report: latestByType.get("market_strategy") ?? null,
      borderClass: "border-pink-300/30",
      dotClass: "bg-pink-300 shadow-[0_0_24px_rgba(249,168,212,0.75)]",
      onRefresh: generateMarketStrategy,
    },
    {
      title: "Watchlist Moves",
      description: `Catalysts, filings, news, and risk signals for ${watchlist === "Not set" ? "your saved watchlist" : watchlist}.`,
      report: latestByType.get("company_research") ?? null,
      borderClass: "border-orange-300/30",
      dotClass: "bg-orange-300 shadow-[0_0_24px_rgba(253,186,116,0.75)]",
      onRefresh: generateCompanyReport,
    },
    {
      title: "Rates And Credit",
      description: "Rates, yields, inflation pressure, credit conditions, Fed policy, and consumer stress.",
      report: latestByType.get("macro") ?? null,
      borderClass: "border-violet-300/30",
      dotClass: "bg-violet-300 shadow-[0_0_24px_rgba(196,181,253,0.75)]",
      onRefresh: generateMacroReport,
    },
  ];
}

function buildHomeVisualModules({
  profile,
  reports,
  healthData,
  scheduleData,
}: {
  profile: PersonalizationProfile;
  reports: ReportResponse[];
  healthData: SourceHealthResponse | null;
  scheduleData: DailyScheduleConfig | null;
}): HomeVisualModule[] {
  const latestByType = latestReportByType(reports);
  const freshCount = healthData?.fresh_count ?? 0;
  const needsCheck = needsCheckCount(healthData);
  const totalSources = healthData?.total ?? 0;
  const location = profile.location || compactListLabel(splitList(profile.housingMarkets));
  const watchlist = compactListLabel(splitList(profile.watchlist));

  return [
    {
      id: "daily_read",
      title: "Daily Read",
      value: latestByType.has("daily_briefing") ? "Ready" : "Open",
      label: scheduleData?.enabled ? "Auto brief" : "Manual brief",
      summary: latestByType.get("daily_briefing")?.summary ?? "A personal briefing will appear after the daily refresh and brief generation run.",
      status: latestByType.has("daily_briefing") ? "Ready" : "Needs brief",
      accent: "lime",
      points: normalizeSparkPoints([freshCount, totalSources, reports.length, scheduleData?.enabled ? 8 : 3, needsCheck]),
      updatedAt: latestByType.get("daily_briefing")?.as_of ?? latestByType.get("daily_briefing")?.created_at ?? scheduleData?.last_run_at ?? null,
      stats: [
        { label: "Fresh sources", value: String(freshCount), detail: "Current source health" },
        { label: "Needs check", value: String(needsCheck), detail: "Sources stale, failed, or missing" },
      ],
      sources: [],
      relatedReportId: latestByType.get("daily_briefing")?.id ?? null,
      suggestedPrompt: "Explain today's daily read and what changed most since the last refresh.",
    },
    {
      id: "housing",
      title: "Housing",
      value: location === "Not set" ? "Set area" : "Local",
      label: location === "Not set" ? "Location needed" : location,
      summary: latestByType.get("housing")?.summary ?? "Tracks rates, affordability, housing markets, and local pressure points from your saved area.",
      status: latestByType.has("housing") ? "Ready" : "No local data",
      accent: "cyan",
      points: normalizeSparkPoints([2, profile.housingMarkets ? 7 : 3, freshCount, 5, needsCheck + 2]),
      updatedAt: latestByType.get("housing")?.as_of ?? latestByType.get("housing")?.created_at ?? null,
      stats: [
        { label: "Location", value: location === "Not set" ? "Not set" : location, detail: "Saved housing focus" },
        { label: "Fresh sources", value: String(freshCount), detail: "All connected source health" },
      ],
      sources: [],
      relatedReportId: latestByType.get("housing")?.id ?? null,
      suggestedPrompt: "Explain the housing visual using my saved location and call out affordability, rates, inventory, and data gaps.",
    },
    {
      id: "markets",
      title: "Markets",
      value: freshCount > 0 ? String(freshCount) : "--",
      label: "fresh sources",
      summary: latestByType.get("market_strategy")?.summary ?? "Shows broad risk, rates, volatility, commodities, and sector tone from connected feeds.",
      status: latestByType.has("market_strategy") ? "Ready" : "Needs refresh",
      accent: "pink",
      points: normalizeSparkPoints([freshCount, needsCheck + 1, totalSources, reports.length + 2, 6]),
      updatedAt: latestByType.get("market_strategy")?.as_of ?? latestByType.get("market_strategy")?.created_at ?? null,
      stats: [
        { label: "Fresh sources", value: String(freshCount), detail: "Current source health" },
        { label: "Reports", value: String(reports.length), detail: "Saved reports available" },
      ],
      sources: [],
      relatedReportId: latestByType.get("market_strategy")?.id ?? null,
      suggestedPrompt: "Explain the market setup using live web first and corroborate it with connected market APIs.",
    },
    {
      id: "companies",
      title: "Companies",
      value: watchlist === "Not set" ? "--" : String(splitList(profile.watchlist).length),
      label: watchlist === "Not set" ? "watchlist empty" : "tracked tickers",
      summary: latestByType.get("company_research")?.summary ?? "Surfaces news, filings, catalysts, and watchlist changes for saved companies.",
      status: watchlist === "Not set" ? "Needs setup" : latestByType.has("company_research") ? "Ready" : "Watching",
      accent: "orange",
      points: normalizeSparkPoints([splitList(profile.watchlist).length + 1, reports.length, freshCount, 3, needsCheck + 1]),
      updatedAt: latestByType.get("company_research")?.as_of ?? latestByType.get("company_research")?.created_at ?? null,
      stats: [
        { label: "Tickers", value: watchlist === "Not set" ? "0" : String(splitList(profile.watchlist).length), detail: "Saved watchlist" },
        { label: "Companies", value: String(splitList(profile.companies).length), detail: "Saved company names" },
      ],
      sources: [],
      relatedReportId: latestByType.get("company_research")?.id ?? null,
      suggestedPrompt: "Explain what changed for my saved companies and watchlist without giving buy or sell instructions.",
    },
    {
      id: "macro",
      title: "Macro",
      value: totalSources > 0 ? String(totalSources) : "--",
      label: "source map",
      summary: latestByType.get("macro")?.summary ?? "Connects inflation, rates, jobs, consumer, credit, and policy signals into one macro pulse.",
      status: latestByType.has("macro") ? "Ready" : "Quiet",
      accent: "violet",
      points: normalizeSparkPoints([totalSources, freshCount, needsCheck, profile.macroInterests.length + 2, reports.length + 1]),
      updatedAt: latestByType.get("macro")?.as_of ?? latestByType.get("macro")?.created_at ?? null,
      stats: [
        { label: "Macro interests", value: String(profile.macroInterests.length), detail: "Saved setup preferences" },
        { label: "Fresh sources", value: String(freshCount), detail: "Current source health" },
      ],
      sources: [],
      relatedReportId: latestByType.get("macro")?.id ?? null,
      suggestedPrompt: "Explain the macro visual and the main trends in rates, inflation, jobs, credit, and consumer conditions.",
    },
  ];
}

function mapVisualModuleFromApi(module: VisualModulesApiResponse["modules"][number]): HomeVisualModule {
  const accentById: Record<HomeVisualModule["id"], HomeVisualModule["accent"]> = {
    daily_read: "lime",
    housing: "cyan",
    markets: "pink",
    companies: "orange",
    macro: "violet",
  };

  return {
    id: module.id,
    title: module.title,
    value: module.primary_value,
    label: module.primary_label,
    summary: module.summary,
    status: titleCase(module.status.replaceAll("_", " ")),
    accent: accentById[module.id],
    points: normalizeSparkPoints(module.chart.points.map((point) => point.value)),
    updatedAt: module.updated_at,
    stats: module.stats,
    sources: module.sources.map((source) => ({
      name: source.name,
      status: source.status,
      retrievedAt: source.retrieved_at,
      description: source.description,
    })),
    relatedReportId: module.related_report_id,
    suggestedPrompt: module.suggested_prompt,
  };
}

function normalizeSparkPoints(points: number[]) {
  return points.map((point) => Math.max(1, Math.round(point)));
}

function latestReportByType(reports: ReportResponse[]) {
  const map = new Map<ReportResponse["report_type"], ReportResponse>();
  for (const report of reports) {
    if (!map.has(report.report_type)) {
      map.set(report.report_type, report);
    }
  }
  return map;
}

function buildDailyBriefingPrompt(profile: PersonalizationProfile) {
  const promptContext = cardPromptContext(profile);

  return [
    "Give me today's personalized briefing.",
    "Cover world news, market setup, rates and macro, local housing, watchlist companies, and major risks.",
    "Use a simple structure: Bottom Line, Major Trends, What Changed Recently, Why It Matters To Me, What To Watch Next, and Uncertainty/Data Gaps.",
    "Analyze cross-category trends in global risk, markets, rates/macro, housing, company/watchlist news, consumer/labor, credit, and commodities.",
    "For each major trend, say whether it looks strengthening, weakening, mixed, or unclear.",
    "Prioritize what matters to my saved profile and keep the answer easy to scan.",
    "Use live web research first, then use direct APIs and stored data to verify or add context.",
    "Do not give direct buy, sell, or hold recommendations.",
    promptContext,
  ].join("\n");
}

function cardPromptContext(profile: PersonalizationProfile) {
  const sections = [
    profile.profileName ? `Profile: ${profile.profileName}` : null,
    profile.personalNote ? `Personal note: ${profile.personalNote}` : null,
    profile.location ? `Primary location: ${profile.location}` : null,
    profile.housingMarkets ? `Housing markets to track: ${profile.housingMarkets}` : null,
    profile.watchlist ? `Watchlist tickers: ${profile.watchlist}` : null,
    profile.companies ? `Companies to track: ${profile.companies}` : null,
    profile.priorityTopics.length > 0 ? `Priority topics: ${profile.priorityTopics.join(", ")}` : null,
    profile.sectors ? `Sectors to watch: ${profile.sectors}` : null,
    profile.housingInterests.length > 0 ? `Housing interests: ${profile.housingInterests.join(", ")}` : null,
    profile.macroInterests.length > 0 ? `Macro interests: ${profile.macroInterests.join(", ")}` : null,
    `Risk preference: ${formatProfileChoice(profile.riskPreference)}`,
    `Investing style: ${formatProfileChoice(profile.investingStyle)}`,
    `Preferred answer format: ${formatProfileChoice(profile.answerFormat)}`,
    profile.ignoredTopics ? `Ignore or de-emphasize: ${profile.ignoredTopics}` : null,
  ].filter(Boolean);

  return `Use this saved user context:\n${sections.map((section) => `- ${section}`).join("\n")}`;
}

function formatProfileChoice(value: string) {
  return value.replaceAll("_", " ");
}

function titleCase(value: string) {
  return value
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
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
                onClick={() => setActiveView("Daily Brief")}
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
              onClick={() => setActiveView("Daily Brief")}
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
              <MarkdownAnswer text={cleanAnswerText(dailyReport.summary ?? dailyReport.body)} tone="light" compact />
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
        <div className="mt-3 max-h-72 overflow-auto rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3">
          <MarkdownAnswer text={cleanAnswerText(report.body)} tone="light" />
        </div>
      </div>
      <ReportEvidenceDrawer report={report} />
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
            <div className="mt-3 rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-3">
              <MarkdownAnswer text={cleanAnswerText(marketReport.body)} tone="light" />
            </div>
          </div>
          <ReportEvidenceDrawer report={marketReport} />
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
  reportListData,
  reportsLoading,
  reportsError,
  dailyBriefingReport,
  dailyBriefingLoading,
  dailyBriefingError,
  generateDailyBriefing,
}: {
  latestItemsData: LatestItemsResponse | null;
  ingestionLoading: boolean;
  reportListData: ReportListResponse | null;
  reportsLoading: boolean;
  reportsError: string | null;
  dailyBriefingReport: ReportResponse | null;
  dailyBriefingLoading: boolean;
  dailyBriefingError: string | null;
  generateDailyBriefing: () => void;
}) {
  const savedDailyBrief = reportListData?.reports.find((report) => report.report_type === "daily_briefing") ?? null;
  const activeBrief = dailyBriefingReport ?? savedDailyBrief;
  const briefText = cleanAnswerText(activeBrief?.body ?? activeBrief?.summary) ?? null;

  return (
    <div className="grid gap-5 text-slate-100">
      <section className="rounded-[24px] border border-cyan-300/20 bg-[radial-gradient(circle_at_86%_14%,rgba(34,211,238,0.16),transparent_22rem),#061320]/95 p-5 md:p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs font-black uppercase text-lime-300">Daily Brief</p>
            <h1 className="mt-3 text-4xl font-black leading-none text-white md:text-5xl">
              {activeBrief?.title ?? "Your daily intelligence brief"}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
              A concise AI briefing generated from your profile, live web research, connected APIs, watch items, and source freshness.
            </p>
          </div>
          <button
            type="button"
            onClick={generateDailyBriefing}
            disabled={dailyBriefingLoading}
            className="min-h-11 rounded-lg bg-lime-300 px-5 text-sm font-black text-[#102000] disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
          >
            {dailyBriefingLoading ? "Generating" : activeBrief ? "Regenerate Brief" : "Generate Brief"}
          </button>
        </div>
        {dailyBriefingError && (
          <p className="mt-4 rounded-lg border border-red-300/30 bg-red-950/30 p-3 text-sm text-red-200">{dailyBriefingError}</p>
        )}
        {reportsError && (
          <p className="mt-4 rounded-lg border border-red-300/30 bg-red-950/30 p-3 text-sm text-red-200">{reportsError}</p>
        )}

        <div className="mt-5 grid gap-3 sm:grid-cols-4">
          <ConsoleMetric label="Retrieved" value={formatDateTime(activeBrief?.as_of ?? activeBrief?.created_at)} />
          <ConsoleMetric label="Confidence" value={activeBrief?.confidence ?? "--"} />
          <ConsoleMetric label="Sources" value={String(activeBrief?.citations.length ?? 0)} />
          <ConsoleMetric label="Status" value={activeBrief?.guardrail_status ?? "waiting"} />
        </div>
      </section>

      <section className="rounded-[24px] border border-cyan-300/20 bg-[#07111f]/92 p-5 md:p-6">
        {reportsLoading && !activeBrief && (
          <p className="rounded-xl border border-[#1d3558] bg-[#020617]/70 p-4 text-sm text-slate-400">Loading saved briefing.</p>
        )}
        {!activeBrief && !dailyBriefingError && !reportsLoading && (
          <div className="rounded-[18px] border border-dashed border-cyan-300/25 bg-[#020617]/70 p-8 text-sm leading-6 text-slate-400">
            No daily brief is saved yet. Generate one to create the markdown briefing for today.
          </div>
        )}
        {activeBrief && (
          <div className="space-y-5">
            <MarkdownAnswer text={briefText} />
            <p className="rounded-lg border border-[#1d3558] bg-[#020617]/70 p-3 text-xs leading-5 text-slate-400">
              {FINANCIAL_DISCLAIMER}
            </p>
            <details className="rounded-[18px] border border-[#1d3558] bg-[#020617]/72 p-4">
              <summary className="cursor-pointer font-mono text-xs font-black uppercase text-cyan-300">
                View citations
              </summary>
              <div className="mt-4">
                <ReportEvidenceDrawer report={activeBrief} />
              </div>
            </details>
          </div>
        )}
      </section>

      <details className="rounded-[20px] border border-cyan-300/20 bg-[#07111f]/88 p-4">
        <summary className="cursor-pointer font-mono text-xs font-black uppercase text-cyan-300">Latest source material</summary>
        <p className="mt-2 text-sm text-slate-400">Raw retrieved items stay hidden unless you want to inspect the inputs.</p>
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
                <p className="mt-2 line-clamp-2 text-sm text-[#5b6573]">{cleanAnswerText(report.summary ?? report.body)}</p>
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
          <p className="mt-2 text-sm text-[#5b6573]">{cleanAnswerText(report.summary)}</p>
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
          {report.summary && <MarkdownAnswer text={cleanAnswerText(report.summary)} tone="light" compact />}
        </div>
      )}

      <article className="rounded-md border border-[#e5eaf0] bg-[#f8fafb] p-4">
        <MarkdownAnswer text={cleanAnswerText(report.body)} tone="light" />
      </article>

      <p className="rounded-md border border-[#e5eaf0] bg-white p-3 text-xs leading-5 text-[#5b6573]">
        {FINANCIAL_DISCLAIMER}
      </p>

      <ReportEvidenceDrawer report={report} />
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
  watchItemsData,
  watchItemsLoading,
  watchItemsError,
  watchEvaluationLoading,
  newWatchTitle,
  newWatchQuery,
  newWatchCategory,
  companyTicker,
  companyName,
  companyReport,
  companyReportLoading,
  companyReportError,
  setNewWatchTitle,
  setNewWatchQuery,
  setNewWatchCategory,
  setCompanyTicker,
  setCompanyName,
  createWatchItem,
  deleteWatchItem,
  evaluateWatchItems,
  generateCompanyReport,
}: {
  watchItemsData: WatchItemListResponse | null;
  watchItemsLoading: boolean;
  watchItemsError: string | null;
  watchEvaluationLoading: boolean;
  newWatchTitle: string;
  newWatchQuery: string;
  newWatchCategory: string;
  companyTicker: string;
  companyName: string;
  companyReport: ReportResponse | null;
  companyReportLoading: boolean;
  companyReportError: string | null;
  setNewWatchTitle: (value: string) => void;
  setNewWatchQuery: (value: string) => void;
  setNewWatchCategory: (value: string) => void;
  setCompanyTicker: (value: string) => void;
  setCompanyName: (value: string) => void;
  createWatchItem: (event: FormEvent<HTMLFormElement>) => void;
  deleteWatchItem: (watchItemId: number) => void;
  evaluateWatchItems: () => void;
  generateCompanyReport: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <div className="grid gap-4">
      <section className="rounded-xl border border-cyan-300/20 bg-[#020617] p-4 text-slate-100">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Watch Items</p>
            <h3 className="mt-1 text-xl font-bold text-white">Things VerityDesk should keep an eye on</h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Save plain-English signals. Daily refresh checks them against saved reports and flags anything that looks meaningful.
            </p>
          </div>
          <button
            type="button"
            onClick={evaluateWatchItems}
            disabled={watchEvaluationLoading}
            className="min-h-10 rounded-lg border border-lime-300/40 px-4 text-sm font-black text-lime-300 transition hover:border-lime-300 disabled:cursor-not-allowed disabled:text-slate-500"
          >
            {watchEvaluationLoading ? "Checking" : "Check Watch Items"}
          </button>
        </div>

        <form onSubmit={createWatchItem} className="mt-5 grid gap-3 rounded-xl border border-[#1d3558] bg-[#07111f] p-4 lg:grid-cols-[0.8fr_1.3fr_0.6fr_auto]">
          <label className="block text-sm font-bold text-slate-300" htmlFor="watch-title">
            Name
            <input
              id="watch-title"
              value={newWatchTitle}
              onChange={(event) => setNewWatchTitle(event.target.value)}
              placeholder="Mortgage rates below 6.5"
              className="mt-2 h-10 w-full rounded-lg border border-[#1d3558] bg-[#020617] px-3 text-sm text-white outline-none focus:border-cyan-300"
            />
          </label>
          <label className="block text-sm font-bold text-slate-300" htmlFor="watch-query">
            What To Watch
            <input
              id="watch-query"
              value={newWatchQuery}
              onChange={(event) => setNewWatchQuery(event.target.value)}
              placeholder="Tell me when Arizona affordability or mortgage rates meaningfully change"
              className="mt-2 h-10 w-full rounded-lg border border-[#1d3558] bg-[#020617] px-3 text-sm text-white outline-none focus:border-cyan-300"
            />
          </label>
          <label className="block text-sm font-bold text-slate-300" htmlFor="watch-category">
            Category
            <select
              id="watch-category"
              value={newWatchCategory}
              onChange={(event) => setNewWatchCategory(event.target.value)}
              className="mt-2 h-10 w-full rounded-lg border border-[#1d3558] bg-[#020617] px-3 text-sm text-white outline-none focus:border-cyan-300"
            >
              {["custom", "market", "company", "housing", "macro", "world"].map((category) => (
                <option key={category} value={category}>
                  {titleCase(category)}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={!newWatchTitle.trim() || !newWatchQuery.trim()}
            className="min-h-10 self-end rounded-lg bg-cyan-300 px-4 text-sm font-black text-[#04111f] disabled:cursor-not-allowed disabled:bg-slate-500"
          >
            Add
          </button>
        </form>

        {watchItemsError && <p className="mt-4 rounded-lg border border-red-300/30 bg-red-950/30 p-3 text-sm text-red-100">{watchItemsError}</p>}

        <div className="mt-5 grid gap-3">
          {watchItemsLoading && <div className="rounded-xl border border-[#1d3558] bg-[#07111f] p-4 text-sm text-slate-400">Loading watch items.</div>}
          {!watchItemsLoading && (watchItemsData?.items ?? []).length === 0 && (
            <div className="rounded-xl border border-dashed border-[#1d3558] bg-[#07111f] p-5 text-sm leading-6 text-slate-400">
              No watch items yet. Add one like "Phoenix inventory rising" or "Fed cut odds changing" and VerityDesk will check it during daily refresh.
            </div>
          )}
          {(watchItemsData?.items ?? []).map((item) => (
            <div key={item.id} className="rounded-xl border border-[#1d3558] bg-[#07111f] p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-lg font-bold text-white">{item.title}</p>
                    <NeonChip variant={item.status === "alert" ? "live" : item.status === "quiet" ? undefined : "search"}>
                      {titleCase(item.status)}
                    </NeonChip>
                    <NeonChip>{titleCase(item.category)}</NeonChip>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{item.query}</p>
                  <p className="mt-3 text-sm leading-6 text-slate-300">
                    {item.last_summary ?? "Waiting for the first check against saved daily reports."}
                  </p>
                  <p className="mt-2 font-mono text-xs font-bold uppercase text-slate-500">
                    Last checked {formatDateTime(item.last_checked_at)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => deleteWatchItem(item.id)}
                  className="min-h-9 rounded-lg border border-[#1d3558] px-3 text-xs font-black text-slate-400 transition hover:border-red-300/50 hover:text-red-200"
                >
                  Remove
                </button>
              </div>
              {item.alerts.length > 0 && (
                <details className="mt-3 rounded-lg border border-cyan-300/20 bg-[#020617] p-3">
                  <summary className="cursor-pointer font-mono text-xs font-black uppercase text-cyan-300">
                    Alerts ({item.alerts.length})
                  </summary>
                  <div className="mt-3 grid gap-2">
                    {item.alerts.slice(0, 3).map((alert) => (
                      <div key={alert.id} className="rounded-lg border border-[#1d3558] p-3 text-sm text-slate-300">
                        <p className="font-bold text-white">{alert.title}</p>
                        <p className="mt-1 leading-5">{alert.message}</p>
                        <p className="mt-2 font-mono text-xs font-bold uppercase text-slate-500">
                          {formatDateTime(alert.triggered_at)}
                        </p>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-cyan-300/20 bg-[#020617] p-4 text-slate-100">
        <form onSubmit={generateCompanyReport}>
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="font-mono text-xs font-black uppercase text-cyan-300">Company Deep Dive</p>
              <h3 className="mt-1 text-xl font-bold text-white">Generate a saved company report</h3>
              <p className="mt-2 text-sm text-slate-400">Use filings, news, market context, and live research for a company-specific read.</p>
            </div>
            <button
              type="submit"
              disabled={companyReportLoading || (!companyTicker.trim() && !companyName.trim())}
              className="min-h-10 rounded-lg bg-lime-300 px-4 py-2 text-sm font-black text-[#102000] disabled:cursor-not-allowed disabled:bg-slate-500"
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
                className="mt-2 h-10 w-full rounded-lg border border-[#1d3558] bg-[#07111f] px-3 text-sm text-white outline-none focus:border-cyan-300"
              />
            </label>
            <label className="block text-sm font-medium" htmlFor="company-name">
              Company
              <input
                id="company-name"
                value={companyName}
                onChange={(event) => setCompanyName(event.target.value)}
                className="mt-2 h-10 w-full rounded-lg border border-[#1d3558] bg-[#07111f] px-3 text-sm text-white outline-none focus:border-cyan-300"
              />
            </label>
          </div>
        </form>

        {companyReportError && (
          <p className="mt-4 rounded-lg border border-red-300/30 bg-red-950/30 p-3 text-sm text-red-100">{companyReportError}</p>
        )}
        {!companyReport && !companyReportError && (
          <div className="mt-4 rounded-xl border border-dashed border-[#1d3558] bg-[#07111f] p-6 text-sm text-slate-400">
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
              <p className="mt-1 text-xs text-slate-500">Generated At {formatDateTime(companyReport.as_of)}</p>
              <div className="mt-3 rounded-xl border border-[#1d3558] bg-[#07111f] p-3">
                <MarkdownAnswer text={cleanAnswerText(companyReport.body)} tone="dark" />
              </div>
            </div>
            <ReportEvidenceDrawer report={companyReport} />
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
  chatSessions,
  activeChatSessionId,
  setAgentQuery,
  setAgentIntent,
  setAgentTicker,
  setAgentDomain,
  setManualAgentContext,
  submitAgentQuery,
  createNewChatSession,
  selectChatSession,
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
  chatSessions: ChatSession[];
  activeChatSessionId: string | null;
  setAgentQuery: (value: string) => void;
  setAgentIntent: (value: AgentIntent) => void;
  setAgentTicker: (value: string) => void;
  setAgentDomain: (value: string) => void;
  setManualAgentContext: (value: boolean) => void;
  submitAgentQuery: (event: FormEvent<HTMLFormElement>) => void;
  createNewChatSession: () => void;
  selectChatSession: (sessionId: string) => void;
}) {
  const inferredContext = inferAgentContext(agentQuery, personalizationProfile);
  const activeSession = chatSessions.find((session) => session.id === activeChatSessionId) ?? null;
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
    <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="rounded-[20px] border border-cyan-300/20 bg-[#07111f]/88 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Chats</p>
            <p className="mt-1 text-xs text-slate-500">{chatSessions.length} saved locally</p>
          </div>
          <button
            type="button"
            onClick={createNewChatSession}
            className="min-h-9 rounded-lg bg-lime-300 px-3 text-xs font-black text-[#102000]"
          >
            New
          </button>
        </div>
        <div className="mt-4 grid gap-2">
          {chatSessions.length === 0 ? (
            <p className="rounded-xl border border-dashed border-[#1d3558] p-3 text-sm text-slate-500">No previous chats yet.</p>
          ) : (
            chatSessions.map((session) => (
              <button
                key={session.id}
                type="button"
                onClick={() => selectChatSession(session.id)}
                className={`rounded-xl border p-3 text-left transition ${
                  session.id === activeChatSessionId
                    ? "border-cyan-300/60 bg-cyan-300/10"
                    : "border-[#1d3558] bg-[#020617]/70 hover:border-cyan-300/40"
                }`}
              >
                <p className="line-clamp-1 text-sm font-black text-white">{session.title}</p>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{session.summary || "New chat"}</p>
                <p className="mt-2 font-mono text-[10px] font-black uppercase text-slate-600">{formatDateTime(session.updatedAt)}</p>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="rounded-[20px] border border-cyan-300/20 bg-[#07111f]/92 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs font-black uppercase text-lime-300">Agent Chat</p>
            <h1 className="mt-2 text-3xl font-black text-white">{activeSession?.title ?? "Ask VerityDesk"}</h1>
            <p className="mt-2 text-sm leading-6 text-slate-400">Session memory is saved locally and included as compact context for follow-up questions.</p>
          </div>
          {agentResponse && <NeonChip>Confidence: {agentResponse.confidence}</NeonChip>}
        </div>

        <div className="mt-5 grid gap-3">
          {activeSession?.messages.length ? (
            activeSession.messages.map((message) => (
              <ChatMessageBubble key={message.id} message={message} />
            ))
          ) : (
            <div className="rounded-[18px] border border-dashed border-[#1d3558] bg-[#020617]/70 p-6 text-sm text-slate-500">
              Start a question or use Ask About This from a visual.
            </div>
          )}
          {agentLoading && (
            <div className="rounded-[18px] border border-cyan-300/20 bg-[#020617]/70 p-4 text-sm text-cyan-200">Thinking...</div>
          )}
          {agentError && <p className="rounded-lg border border-red-300/30 bg-red-950/30 p-3 text-sm text-red-200">{agentError}</p>}
        </div>

        <form onSubmit={submitAgentQuery} className="mt-5 rounded-[18px] border border-cyan-300/25 bg-[#020617]/86 p-4">
          <label className="sr-only" htmlFor="agent-query">Question</label>
          <textarea
            id="agent-query"
            value={agentQuery}
            onChange={(event) => {
              setAgentQuery(event.target.value);
              setManualAgentContext(false);
            }}
            placeholder="Ask a follow-up or start a new question..."
            className="min-h-28 w-full resize-y border-0 bg-transparent text-base leading-7 text-white outline-none placeholder:text-slate-600"
          />
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[#1d3558] pt-4">
            <div className="flex flex-wrap gap-2">
              <NeonChip>{formatAgentIntent(displayedContext.intent)}</NeonChip>
              <NeonChip>{displayedContext.domain}</NeonChip>
              <NeonChip>{manualAgentContext ? "Manual route" : "Auto route"}</NeonChip>
            </div>
            <button
              type="submit"
              disabled={agentLoading || !agentQuery.trim()}
              className="min-h-10 rounded-lg bg-lime-300 px-4 text-sm font-black text-[#102000] disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
            >
              {agentLoading ? "Thinking" : "Send"}
            </button>
          </div>

          <details className="mt-4 rounded-xl border border-[#1d3558] bg-[#07111f]/75 p-3">
            <summary className="cursor-pointer font-mono text-xs font-black uppercase text-slate-400">Advanced routing</summary>
            <InferredContextPanel inferredContext={displayedContext} manualAgentContext={manualAgentContext} />
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <SettingsSelect
                id="agent-intent"
                label="Intent"
                value={agentIntent}
                onChange={(value) => {
                  setAgentIntent(value as AgentIntent);
                  setManualAgentContext(true);
                }}
                options={[
                  ["market_research", "Market research"],
                  ["company_research", "Company research"],
                  ["housing_macro_research", "Housing and macro"],
                  ["daily_briefing", "Daily briefing"],
                  ["general_research", "General research"],
                ]}
              />
              <SettingsTextInput
                id="agent-ticker"
                label="Tickers"
                value={agentTicker}
                onChange={(value) => {
                  setAgentTicker(value);
                  setManualAgentContext(true);
                }}
              />
              <SettingsSelect
                id="agent-domain"
                label="Domain"
                value={agentDomain}
                onChange={(value) => {
                  setAgentDomain(value);
                  setManualAgentContext(true);
                }}
                options={domains.map((domain): [string, string] => [domain, domain])}
              />
            </div>
            {manualAgentContext && (
              <button
                type="button"
                onClick={() => setManualAgentContext(false)}
                className="mt-4 min-h-10 rounded-lg border border-cyan-300/30 px-3 text-sm font-black text-cyan-200"
              >
                Return To Auto
              </button>
            )}
          </details>
        </form>

        {agentResponse && (
          <div className="mt-5">
            <EvidenceDrawer response={agentResponse} />
          </div>
        )}
        <details className="mt-5 rounded-xl border border-[#1d3558] bg-[#020617]/70 p-4">
          <summary className="cursor-pointer font-mono text-xs font-black uppercase text-cyan-300">Recent agent runs</summary>
          <AgentRunsList agentRunsData={agentRunsData} loading={agentRunsLoading} />
        </details>
      </section>
    </div>
  );
}

function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[86%] rounded-[18px] border p-4 ${
          isUser
            ? "border-lime-300/25 bg-lime-300/10 text-slate-100"
            : "border-cyan-300/20 bg-[#020617]/78 text-slate-300"
        }`}
      >
        <p className="font-mono text-[10px] font-black uppercase text-slate-500">{isUser ? "You" : "VerityDesk"} / {formatDateTime(message.createdAt)}</p>
        <div className="mt-2">
          <MarkdownAnswer text={message.content} />
        </div>
      </div>
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

function MarkdownAnswer({ text, tone = "dark", compact = false }: { text: string | null | undefined; tone?: "dark" | "light"; compact?: boolean }) {
  const lines = (text || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const textClass = tone === "dark" ? "text-slate-300" : "text-[#374151]";
  const mutedClass = tone === "dark" ? "text-slate-400" : "text-[#5b6573]";
  const headingClass = tone === "dark" ? "text-cyan-200" : "text-[#143642]";

  if (lines.length === 0) {
    return <p className={`text-sm leading-7 ${mutedClass}`}>No response available yet.</p>;
  }

  return (
    <div className={`${compact ? "space-y-2" : "space-y-3"} text-sm leading-7 ${textClass}`}>
      {lines.map((line, index) => {
        const heading = markdownHeadingText(line);
        if (heading) {
          return (
            <h3 key={`${line}-${index}`} className={`font-mono text-xs font-black uppercase tracking-normal ${headingClass}`}>
              {renderInlineMarkdown(heading)}
            </h3>
          );
        }

        const bullet = markdownBulletText(line);
        if (bullet) {
          return (
            <div key={`${line}-${index}`} className="flex gap-2">
              <span className={tone === "dark" ? "text-lime-300" : "text-[#25636b]"}>-</span>
              <p>{renderInlineMarkdown(bullet)}</p>
            </div>
          );
        }

        return <p key={`${line}-${index}`}>{renderInlineMarkdown(line)}</p>;
      })}
    </div>
  );
}

function markdownHeadingText(line: string) {
  if (line.startsWith("### ")) {
    return line.slice(4).trim();
  }
  if (line.startsWith("## ")) {
    return line.slice(3).trim();
  }

  const normalized = line.replace(/\*\*/g, "").trim();
  if (/^(bottom line|what changed|major trends|why it matters|why it matters to you|what to watch|what to watch next|confidence and gaps|uncertainty\/data gaps|uncertainty and data gaps):?$/i.test(normalized)) {
    return normalized.replace(/:$/, "");
  }

  return null;
}

function markdownBulletText(line: string) {
  if (line.startsWith("- ")) {
    return line.slice(2).trim();
  }
  if (line.startsWith("* ")) {
    return line.slice(2).trim();
  }
  return null;
}

function renderInlineMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`} className="font-black text-inherit">{part.slice(2, -2)}</strong>;
    }
    return <span key={`${part}-${index}`}>{part}</span>;
  });
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

function EvidenceDrawer({ response }: { response: AgentResponse }) {
  const latestRetrievedAt = latestCitationTimestamp(response.citations);

  return (
    <details className="rounded-xl border border-cyan-300/20 bg-[#020617]/80 p-4">
      <summary className="cursor-pointer list-none">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">View Sources</p>
            <p className="mt-1 text-sm text-slate-400">
              {response.citations.length} citations hidden by default
              {latestRetrievedAt ? ` · latest retrieved ${formatDateTime(latestRetrievedAt)}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <NeonChip>Confidence: {response.confidence}</NeonChip>
            <NeonChip>{response.requires_guardrail_review ? "Review needed" : "Guardrail passed"}</NeonChip>
          </div>
        </div>
      </summary>
      <div className="mt-4 grid gap-4">
        <EvidenceMetaGrid
          items={[
            ["Citations", String(response.citations.length)],
            ["Confidence", response.confidence],
            ["Retrieved At", formatDateTime(latestRetrievedAt)],
            ["Review Needed", response.requires_guardrail_review ? "Yes" : "No"],
          ]}
        />
        <CitationList citations={response.citations} />
        <details className="rounded-lg border border-[#1d3558] bg-[#07111f]/75 p-3">
          <summary className="cursor-pointer font-mono text-xs font-black uppercase text-slate-400">Analysis Details</summary>
          <div className="mt-4 grid gap-4">
            <InlineList title="Agents Run" values={response.agents_ran} />
            <ClaimsList claims={response.claims} />
            <InlineList title="Risks" values={response.risks} />
            <InlineList title="Follow-up Questions" values={response.follow_up_questions} />
            <GuardrailDetails response={response} />
          </div>
        </details>
      </div>
    </details>
  );
}

function ReportEvidenceDrawer({ report }: { report: ReportResponse }) {
  const latestRetrievedAt = latestCitationTimestamp(report.citations);

  return (
    <details className="rounded-xl border border-cyan-300/20 bg-[#020617]/80 p-4">
      <summary className="cursor-pointer list-none">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">View Sources</p>
            <p className="mt-1 text-sm text-slate-400">
              {report.citations.length} citations hidden by default
              {latestRetrievedAt ? ` · latest retrieved ${formatDateTime(latestRetrievedAt)}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <NeonChip>Confidence: {report.confidence}</NeonChip>
            <NeonChip>Retrieved {formatDateTime(report.as_of ?? report.created_at)}</NeonChip>
          </div>
        </div>
      </summary>
      <div className="mt-4 grid gap-4">
        <EvidenceMetaGrid
          items={[
            ["Citations", String(report.citations.length)],
            ["Confidence", report.confidence],
            ["Retrieved At", formatDateTime(latestRetrievedAt ?? report.as_of ?? report.created_at)],
            ["Guardrail", report.guardrail_status],
          ]}
        />
        <CitationList citations={report.citations} />
      </div>
    </details>
  );
}

function EvidenceMetaGrid({ items }: { items: Array<[string, string]> }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-lg border border-[#1d3558] bg-[#07111f]/75 p-3">
          <p className="font-mono text-[0.65rem] font-black uppercase text-slate-500">{label}</p>
          <p className="mt-1 text-sm font-bold text-slate-200">{value || "--"}</p>
        </div>
      ))}
    </div>
  );
}

function ClaimsList({ claims }: { claims: AgentResponse["claims"] }) {
  return (
    <div>
      <p className="text-sm font-semibold text-slate-200">Claims</p>
      {claims.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">No structured claims returned.</p>
      ) : (
        <div className="mt-2 space-y-2">
          {claims.map((claim, index) => (
            <div key={`${claim.claim}-${index}`} className="rounded-lg border border-[#1d3558] bg-[#07111f]/75 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={claim.confidence} />
                <span className="rounded-md border border-[#1d3558] px-2 py-1 text-xs font-medium text-slate-400">
                  {claim.claim_type}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-300">{claim.claim}</p>
              {claim.source_ids.length > 0 && (
                <p className="mt-2 text-xs text-slate-500">Sources: {claim.source_ids.join(", ")}</p>
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
      <p className="text-sm font-semibold text-slate-200">Citations</p>
      {citations.length === 0 ? (
        <p className="mt-2 rounded-lg border border-dashed border-[#1d3558] p-3 text-sm text-slate-500">
          No citations returned for this response.
        </p>
      ) : (
        <div className="mt-2 space-y-2">
          {citations.map((citation, index) => (
            <div key={`${citation.source_id}-${citation.title}-${index}`} className="rounded-lg border border-[#1d3558] bg-[#07111f]/75 p-3">
              <p className="text-sm font-medium text-slate-100">
                {citation.url ? (
                  <a className="text-cyan-300 underline-offset-4 hover:underline" href={citation.url}>
                    {citation.title}
                  </a>
                ) : (
                  citation.title
                )}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {[citation.publisher, citation.source_id].filter(Boolean).join(" | ")}
              </p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <SettingRow label="Published" value={formatDateTime(citation.published_at)} />
                <SettingRow label="Retrieved At" value={formatDateTime(citation.retrieved_at)} />
              </div>
              <p className="mt-2 text-sm text-slate-400">{citation.supports_claim}</p>
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
      <p className="text-sm font-semibold text-slate-200">Guardrail Review</p>
      <div className="mt-2 rounded-lg border border-[#1d3558] bg-[#07111f]/75 p-3">
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
          <p className="mt-3 rounded-lg border border-[#1d3558] bg-[#020617]/70 p-3 text-sm text-slate-400">
            Safer wording was applied to the final response.
          </p>
        )}
      </div>
    </div>
  );
}

function SettingsView({
  sourceData,
  sourceError,
  sourcesLoading,
  healthData,
  runsData,
  latestItemsData,
  scheduleData,
  scheduleSaving,
  scheduleError,
  ingestionError,
  ingestionLoading,
  runMode,
  runLoading,
  lastRunResponse,
  reportListData,
  reportsLoading,
  reportsError,
  watchItemsData,
  watchItemsLoading,
  watchItemsError,
  watchEvaluationLoading,
  personalizationProfile,
  profileSavedAt,
  setRunMode,
  triggerIngestionRun,
  saveSchedule,
  savePersonalizationProfile,
  evaluateWatchItems,
  openSetup,
}: {
  sourceData: SourceCatalogResponse | null;
  sourceError: string | null;
  sourcesLoading: boolean;
  healthData: SourceHealthResponse | null;
  runsData: IngestionRunHistoryResponse | null;
  latestItemsData: LatestItemsResponse | null;
  scheduleData: DailyScheduleConfig | null;
  scheduleSaving: boolean;
  scheduleError: string | null;
  ingestionError: string | null;
  ingestionLoading: boolean;
  runMode: RunMode;
  runLoading: boolean;
  lastRunResponse: IngestionRunResponse | null;
  reportListData: ReportListResponse | null;
  reportsLoading: boolean;
  reportsError: string | null;
  watchItemsData: WatchItemListResponse | null;
  watchItemsLoading: boolean;
  watchItemsError: string | null;
  watchEvaluationLoading: boolean;
  personalizationProfile: PersonalizationProfile;
  profileSavedAt: string | null;
  setRunMode: (mode: RunMode) => void;
  triggerIngestionRun: () => void;
  saveSchedule: (nextSchedule: DailyScheduleConfig) => Promise<void>;
  savePersonalizationProfile: (nextProfile: PersonalizationProfile) => void;
  evaluateWatchItems: () => void;
  openSetup: () => void;
}) {
  const schedule = scheduleData ?? defaultScheduleConfig();
  const [profileDraft, setProfileDraft] = useState<PersonalizationProfile>(personalizationProfile);
  const healthBySourceKey = useMemo(
    () => new Map(healthData?.sources.map((source) => [source.source_key, source]) ?? []),
    [healthData],
  );

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
    <div className="grid gap-5 text-slate-100">
      <section className="rounded-xl border border-cyan-300/20 bg-[#020617]/70 p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="font-mono text-sm font-black text-lime-300">veritydesk settings --profile --sources --automation</p>
            <h1 className="mt-3 text-4xl font-black leading-none text-white md:text-5xl">Control center.</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
              Settings holds the complexity so the home screen can stay simple. Save who you are, what you care about, when the app should refresh, and which sources are healthy.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <select
              value={runMode}
              onChange={(event) => setRunMode(event.target.value as RunMode)}
              className="h-10 rounded-lg border border-[#1d3558] bg-[#020617] px-3 text-sm font-semibold text-slate-200 outline-none focus:border-cyan-300"
            >
              <option value="all">All sources</option>
              <option value="rss">News feeds only</option>
              <option value="official_api">Official APIs only</option>
            </select>
            <button
              type="button"
              onClick={triggerIngestionRun}
              disabled={runLoading}
              className="min-h-10 rounded-lg bg-lime-300 px-4 text-sm font-black text-[#102000] disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
            >
              {runLoading ? "Refreshing" : "Refresh All Sources"}
            </button>
          </div>
        </div>
      </section>

      <form onSubmit={submitProfile} className="rounded-xl border border-cyan-300/20 bg-[#07111f]/88 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Personal context</p>
            <h2 className="mt-1 text-2xl font-bold text-white">Tell VerityDesk what matters once.</h2>
          </div>
          <button
            type="submit"
            className="min-h-10 rounded-lg bg-lime-300 px-4 text-sm font-black text-[#102000]"
          >
            Save Profile
          </button>
          <button
            type="button"
            onClick={openSetup}
            className="min-h-10 rounded-lg border border-cyan-300/30 px-4 text-sm font-black text-cyan-200 transition hover:border-cyan-300/70"
          >
            Run Setup
          </button>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
          <label className="block text-sm font-bold text-slate-200" htmlFor="profile-note">
            About you and your interests
            <textarea
              id="profile-note"
              value={profileDraft.personalNote}
              onChange={(event) => updateProfile({ personalNote: event.target.value })}
              placeholder="Example: I live in Arizona, care about housing affordability, mortgage rates, broad market risk, and long-term technology companies. Keep answers concise and practical."
              className="mt-2 min-h-36 w-full resize-y rounded-xl border border-[#1d3558] bg-[#020617] px-4 py-3 text-sm leading-6 text-slate-300 outline-none focus:border-cyan-300"
            />
          </label>

          <div className="grid gap-3">
            <SettingsTextInput
              id="profile-name"
              label="Profile name"
              value={profileDraft.profileName}
              placeholder="My VerityDesk"
              onChange={(value) => updateProfile({ profileName: value })}
            />
            <SettingsTextInput
              id="profile-location"
              label="Preferred location"
              value={profileDraft.location}
              placeholder="Phoenix, AZ"
              onChange={(value) => updateProfile({ location: value })}
            />
            <SettingsSelect
              id="profile-briefing-style"
              label="Answer style"
              value={profileDraft.briefingStyle}
              onChange={(value) => updateProfile({ briefingStyle: value as PersonalizationProfile["briefingStyle"] })}
              options={[
                ["quick", "Quick"],
                ["balanced", "Balanced"],
                ["detailed", "Detailed"],
              ]}
            />
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <SettingsTextInput
            id="profile-watchlist"
            label="Watchlist"
            value={profileDraft.watchlist}
            placeholder="AAPL, MSFT, SPY, QQQ"
            onChange={(value) => updateProfile({ watchlist: value.toUpperCase() })}
          />
          <SettingsTextInput
            id="profile-companies"
            label="Companies"
            value={profileDraft.companies}
            placeholder="Apple, Nvidia, Tesla"
            onChange={(value) => updateProfile({ companies: value })}
          />
          <SettingsTextInput
            id="profile-housing-markets"
            label="Housing markets"
            value={profileDraft.housingMarkets}
            placeholder="Phoenix, Scottsdale, Tucson"
            onChange={(value) => updateProfile({ housingMarkets: value })}
          />
          <SettingsTextInput
            id="profile-sectors"
            label="Sectors to watch"
            value={profileDraft.sectors}
            placeholder="AI, semiconductors, homebuilders, banks"
            onChange={(value) => updateProfile({ sectors: value })}
          />
          <SettingsTextInput
            id="profile-ignore"
            label="Ignore these topics"
            value={profileDraft.ignoredTopics}
            placeholder="crypto, small caps, meme stocks"
            onChange={(value) => updateProfile({ ignoredTopics: value })}
          />
          <SettingsTextInput
            id="profile-briefing-time"
            label="Preferred briefing time"
            value={profileDraft.briefingTime}
            type="time"
            onChange={(value) => updateProfile({ briefingTime: value })}
          />
          <SettingsSelect
            id="profile-risk"
            label="Risk preference"
            value={profileDraft.riskPreference}
            onChange={(value) => updateProfile({ riskPreference: value as PersonalizationProfile["riskPreference"] })}
            options={[
              ["conservative", "Conservative"],
              ["balanced", "Balanced"],
              ["aggressive", "Aggressive"],
            ]}
          />
          <SettingsSelect
            id="profile-investing-style"
            label="Investing style"
            value={profileDraft.investingStyle}
            onChange={(value) => updateProfile({ investingStyle: value as PersonalizationProfile["investingStyle"] })}
            options={[
              ["long_term", "Long-term"],
              ["medium_term", "Medium-term"],
              ["short_term", "Short-term"],
              ["mixed", "Mixed"],
            ]}
          />
          <SettingsSelect
            id="profile-answer-format"
            label="Preferred answer format"
            value={profileDraft.answerFormat}
            onChange={(value) => updateProfile({ answerFormat: value as PersonalizationProfile["answerFormat"] })}
            options={[
              ["brief", "Brief"],
              ["decision_memo", "Decision memo"],
              ["watchlist", "Watchlist"],
            ]}
          />
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-3 text-slate-200">
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

        <div className="mt-5 rounded-xl border border-[#1d3558] bg-[#020617]/70 p-4">
          <p className="font-mono text-xs font-black uppercase text-cyan-300">Saved profile</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">{profileSummary(personalizationProfile)}</p>
          <p className="mt-2 text-xs text-slate-500">Saved At {formatDateTime(profileSavedAt)}</p>
        </div>
      </form>

      <section className="rounded-xl border border-cyan-300/20 bg-[#07111f]/88 p-5">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Automation</p>
            <h2 className="mt-1 text-2xl font-bold text-white">Daily run</h2>
            <p className="mt-1 text-sm text-slate-400">
              Runs while the local backend is open. Schedule settings are saved locally.
            </p>
          </div>
          <StatusBadge status={schedule.enabled ? "enabled" : "off"} />
        </div>
        {scheduleError && <p className="mt-4 rounded-lg border border-red-300/30 bg-red-950/30 p-3 text-sm text-red-200">{scheduleError}</p>}
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="flex items-center gap-3 rounded-xl border border-[#1d3558] bg-[#020617]/70 p-3 text-sm font-bold text-slate-200">
            <input
              type="checkbox"
              checked={schedule.enabled}
              disabled={scheduleSaving}
              onChange={(event) => updateSchedule({ enabled: event.target.checked })}
            />
            Daily run
          </label>
          <label className="flex items-center gap-3 rounded-xl border border-[#1d3558] bg-[#020617]/70 p-3 text-sm font-bold text-slate-200">
            <input
              type="checkbox"
              checked={schedule.generate_daily_briefing}
              disabled={scheduleSaving}
              onChange={(event) => updateSchedule({ generate_daily_briefing: event.target.checked })}
            />
            Generate daily briefing
          </label>
          <SettingsTextInput
            id="schedule-time"
            label="Scheduled time"
            value={schedule.local_time}
            type="time"
            disabled={scheduleSaving}
            onChange={(value) => updateSchedule({ local_time: value })}
          />
          <SettingsSelect
            id="schedule-mode"
            label="Run mode"
            value={schedule.mode}
            disabled={scheduleSaving}
            onChange={(value) => updateSchedule({ mode: value as RunMode })}
            options={[
              ["all", "All sources"],
              ["rss", "News feeds only"],
              ["official_api", "Official APIs only"],
            ]}
          />
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <ConsoleMetric label="Next run" value={formatDateTime(schedule.next_run_at)} />
          <ConsoleMetric label="Last run" value={formatDateTime(schedule.last_run_at)} />
          <ConsoleMetric label="Last status" value={schedule.last_status ?? "--"} />
        </div>
        {scheduleSaving && <p className="mt-4 text-sm text-slate-400">Saving schedule.</p>}
      </section>

      <section className="rounded-xl border border-cyan-300/20 bg-[#07111f]/88 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Saved intelligence</p>
            <h2 className="mt-1 text-2xl font-bold text-white">Reports and brief history</h2>
            <p className="mt-1 text-sm leading-6 text-slate-400">
              Saved briefings and generated reports live here so Home can stay focused on the current signal.
            </p>
          </div>
          <StatusBadge status={reportsLoading ? "loading" : `${reportListData?.total ?? 0} reports`} />
        </div>
        <StatusBlock loading={reportsLoading} error={reportsError} />
        <div className="mt-4 grid gap-3 xl:grid-cols-2">
          {(reportListData?.reports ?? []).slice(0, 6).map((report) => (
            <article key={report.id} className="rounded-xl border border-[#1d3558] bg-[#020617]/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-bold text-white">{report.title}</p>
                <StatusBadge status={report.confidence} />
              </div>
              <p className="mt-2 text-xs text-slate-500">{titleCase(report.report_type)} / {formatDateTime(report.as_of ?? report.created_at)}</p>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-400">{cleanAnswerText(report.summary ?? report.body) ?? "No summary."}</p>
            </article>
          ))}
          {!reportsLoading && (reportListData?.reports ?? []).length === 0 && (
            <p className="rounded-xl border border-dashed border-[#1d3558] p-4 text-sm text-slate-500">No saved reports yet.</p>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-cyan-300/20 bg-[#07111f]/88 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Watch items</p>
            <h2 className="mt-1 text-2xl font-bold text-white">Signals to monitor</h2>
            <p className="mt-1 text-sm leading-6 text-slate-400">
              Plain-English monitoring rules used by the daily workflow and agent context.
            </p>
          </div>
          <button
            type="button"
            onClick={evaluateWatchItems}
            disabled={watchEvaluationLoading}
            className="min-h-10 rounded-lg border border-lime-300/40 px-4 text-sm font-black text-lime-300 transition hover:border-lime-300 disabled:cursor-not-allowed disabled:text-slate-500"
          >
            {watchEvaluationLoading ? "Checking" : "Check Watch Items"}
          </button>
        </div>
        <StatusBlock loading={watchItemsLoading} error={watchItemsError} />
        <div className="mt-4 grid gap-3 xl:grid-cols-2">
          {(watchItemsData?.items ?? []).slice(0, 6).map((item) => (
            <article key={item.id} className="rounded-xl border border-[#1d3558] bg-[#020617]/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-bold text-white">{item.title}</p>
                <StatusBadge status={item.enabled ? item.status : "off"} />
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-400">{item.query}</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <SourceStripRow label="Category" value={titleCase(item.category)} />
                <SourceStripRow label="Last checked" value={formatDateTime(item.last_checked_at)} />
              </div>
            </article>
          ))}
          {!watchItemsLoading && (watchItemsData?.items ?? []).length === 0 && (
            <p className="rounded-xl border border-dashed border-[#1d3558] p-4 text-sm text-slate-500">No watch items yet.</p>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-cyan-300/20 bg-[#07111f]/88 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs font-black uppercase text-cyan-300">Sources</p>
            <h2 className="mt-1 text-2xl font-bold text-white">Connected data</h2>
            <p className="mt-1 text-sm leading-6 text-slate-400">
              These sources support the assistant behind the scenes. Use one refresh for all sources, then inspect details only when something needs attention.
            </p>
          </div>
          <div className="grid min-w-44 gap-2">
            <SourceStripRow label="Working" value={String(healthData?.fresh_count ?? 0)} />
            <SourceStripRow label="Needs check" value={String(needsCheckCount(healthData))} />
          </div>
        </div>
        <StatusBlock loading={sourcesLoading || ingestionLoading} error={sourceError || ingestionError} />
        <div className="mt-5 grid gap-3 xl:grid-cols-2">
          {(sourceData?.sources ?? []).map((source) => {
            const health = healthBySourceKey.get(source.id);
            const sourceStatus = sourceStatusSummary(source, health);
            return (
              <SourceSettingsCard
                key={source.id}
                source={source}
                health={health}
                statusLabel={sourceStatus.label}
                description={sourceStatus.description}
                nextStep={sourceStatus.nextStep}
              />
            );
          })}
        </div>
        {lastRunResponse && (
          <p className="mt-4 rounded-xl border border-[#1d3558] bg-[#020617]/70 p-3 text-sm leading-6 text-slate-400">
            Latest refresh: {lastRunResponse.message}
          </p>
        )}
        <details className="mt-5 rounded-xl border border-[#1d3558] bg-[#020617]/70 p-4">
          <summary className="cursor-pointer font-mono text-xs font-black uppercase text-cyan-300">Recent runs and latest items</summary>
          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <div>
              <p className="text-sm font-bold text-white">Recent runs</p>
              <RecentRunsTable runsData={runsData} loading={ingestionLoading} />
            </div>
            <div>
              <p className="text-sm font-bold text-white">Latest retrieved items</p>
              <LatestItemsList latestItemsData={latestItemsData} loading={ingestionLoading} />
            </div>
          </div>
        </details>
      </section>

      <section className="rounded-xl border border-cyan-300/20 bg-[#07111f]/88 p-5">
        <p className="font-mono text-xs font-black uppercase text-cyan-300">Provider status</p>
        <h2 className="mt-1 text-2xl font-bold text-white">Models and live web</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <ConsoleMetric label="LLM provider" value="OpenAI via backend .env" />
          <ConsoleMetric label="Live web" value="Tavily via backend .env" />
          <ConsoleMetric label="Source keys" value="Managed locally" />
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          API keys stay in the backend environment and are not exposed in the browser. If an answer falls back or a source fails, check backend logs and source health above.
        </p>
      </section>
    </div>
  );
}

function SettingsTextInput({
  id,
  label,
  value,
  placeholder,
  type = "text",
  disabled = false,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  placeholder?: string;
  type?: "text" | "time";
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm font-bold text-slate-200" htmlFor={id}>
      {label}
      <input
        id={id}
        type={type}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-2 h-11 w-full rounded-xl border border-[#1d3558] bg-[#020617] px-4 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-300 disabled:cursor-not-allowed disabled:text-slate-500"
      />
    </label>
  );
}

function SettingsSelect({
  id,
  label,
  value,
  options,
  disabled = false,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: Array<[string, string]>;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm font-bold text-slate-200" htmlFor={id}>
      {label}
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 h-11 w-full rounded-xl border border-[#1d3558] bg-[#020617] px-4 text-sm text-slate-200 outline-none focus:border-cyan-300 disabled:cursor-not-allowed disabled:text-slate-500"
      >
        {options.map(([optionValue, labelText]) => (
          <option key={optionValue} value={optionValue}>
            {labelText}
          </option>
        ))}
      </select>
    </label>
  );
}

function SourceSettingsCard({
  source,
  health,
  statusLabel,
  description,
  nextStep,
}: {
  source: SourceEntry;
  health: SourceHealthItem | undefined;
  statusLabel: string;
  description: string;
  nextStep: string;
}) {
  return (
    <article className="rounded-xl border border-[#1d3558] bg-[#020617]/70 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-bold text-white">{source.name}</h3>
          <p className="mt-1 text-xs font-semibold text-slate-500">{formatAccessMethod(source.access_method)}</p>
        </div>
        <StatusBadge status={statusLabel} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-400">{description}</p>
      <div className="mt-4 grid gap-2 md:grid-cols-2">
        <SourceStripRow label="Last updated" value={formatDateTime(health?.last_success_at ?? health?.last_attempt_at)} />
        <SourceStripRow label="Next step" value={nextStep} />
      </div>
      {source.domains.length > 0 && (
        <p className="mt-3 text-xs leading-5 text-slate-500">Provides: {source.domains.slice(0, 4).join(", ")}</p>
      )}
      {health?.last_error && (
        <details className="mt-3 rounded-lg border border-orange-300/20 bg-orange-950/10 p-3">
          <summary className="cursor-pointer text-xs font-black uppercase text-orange-300">Technical message</summary>
          <p className="mt-2 text-xs leading-5 text-orange-200">{health.last_error}</p>
        </details>
      )}
    </article>
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
    <fieldset className="rounded-xl border border-[#1d3558] bg-[#020617]/70 p-3">
      <legend className="px-1 text-sm font-bold text-slate-200">{title}</legend>
      <div className="mt-2 grid gap-2">
        {options.map((option) => (
          <label key={option} className="flex min-h-9 items-center gap-2 text-sm text-slate-300">
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

  if (source.requires_api_key && source.phase === "optional_v1") {
    return {
      label: "Ready with key",
      description: "This optional provider is connected when its local key is available.",
      nextStep: "Run a source refresh.",
    };
  }

  if (source.status === "optional" || source.phase === "optional_v1") {
    return {
      label: "Available optional source",
      description: "This optional provider can be used during source refreshes.",
      nextStep: "Run a source refresh.",
    };
  }

  if (source.status !== "active" && (source.access_method === "dataset_download" || errorText.includes("parser"))) {
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

function cleanAnswerText(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  const cleaned = value
    .split("\n")
    .filter((line) => !line.trim().startsWith("Coordinator selected:"))
    .join("\n")
    .trim();

  return cleaned || null;
}

function compactText(value: string, maxLength: number) {
  const singleLine = value.replace(/\s+/g, " ").trim();
  if (singleLine.length <= maxLength) {
    return singleLine;
  }

  return `${singleLine.slice(0, maxLength).trim()}...`;
}

function latestCitationTimestamp(citations: AgentResponse["citations"]) {
  const timestamps = citations
    .map((citation) => citation.retrieved_at ?? citation.published_at)
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => new Date(right).getTime() - new Date(left).getTime());

  return timestamps[0] ?? null;
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
    profileName: "",
    personalNote: "",
    location: "",
    housingMarkets: "",
    watchlist: "SPY, QQQ, TLT",
    companies: "",
    priorityTopics: ["Markets", "Housing", "U.S. economy"],
    sectors: "",
    housingInterests: ["Mortgage rates", "Affordability"],
    macroInterests: ["Inflation", "Interest rates", "Fed policy"],
    riskPreference: "balanced",
    investingStyle: "long_term",
    answerFormat: "brief",
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

function isSetupComplete(profile: PersonalizationProfile) {
  if (typeof window === "undefined") {
    return true;
  }

  return window.localStorage.getItem(SETUP_COMPLETE_STORAGE_KEY) === "true" || Boolean(profile.profileName || profile.location || profile.personalNote);
}

function hasLocalSession() {
  if (typeof window === "undefined") {
    return false;
  }

  return window.localStorage.getItem(LOCAL_SESSION_STORAGE_KEY) === "ready" || Boolean(window.localStorage.getItem(LOCAL_SESSION_STORAGE_KEY));
}

function loadChatSessions(): ChatSession[] {
  if (typeof window === "undefined") {
    return [];
  }

  const storedSessions = window.localStorage.getItem(CHAT_SESSIONS_STORAGE_KEY);
  if (!storedSessions) {
    return [];
  }

  try {
    const parsed = JSON.parse(storedSessions) as ChatSession[];
    return parsed
      .filter((session) => session.id && Array.isArray(session.messages))
      .sort((first, second) => second.updatedAt.localeCompare(first.updatedAt))
      .slice(0, 20);
  } catch {
    return [];
  }
}

function loadActiveChatSessionId(sessions: ChatSession[]) {
  if (typeof window === "undefined") {
    return null;
  }

  const storedId = window.localStorage.getItem(ACTIVE_CHAT_SESSION_STORAGE_KEY);
  if (storedId && sessions.some((session) => session.id === storedId)) {
    return storedId;
  }
  return sessions[0]?.id ?? null;
}

function createChatSession(question?: string): ChatSession {
  const now = new Date().toISOString();
  return {
    id: createLocalId("chat"),
    title: question ? titleFromQuestion(question) : "New chat",
    summary: question ? question.slice(0, 160) : "",
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

function ensureActiveChatSession(sessions: ChatSession[], activeSessionId: string | null, question: string) {
  const activeSession = sessions.find((session) => session.id === activeSessionId);
  return activeSession ?? createChatSession(question);
}

function upsertChatSession(sessions: ChatSession[], nextSession: ChatSession) {
  const withoutSession = sessions.filter((session) => session.id !== nextSession.id);
  return [nextSession, ...withoutSession].sort((first, second) => second.updatedAt.localeCompare(first.updatedAt)).slice(0, 20);
}

function summarizeChatMessages(messages: ChatMessage[]) {
  const latest = messages.slice(-2).map((message) => `${message.role === "user" ? "Q" : "A"}: ${message.content.replace(/\s+/g, " ").slice(0, 120)}`);
  return latest.join(" / ");
}

function buildQueryWithSessionMemory(query: string, session: ChatSession) {
  const previousMessages = session.messages.slice(-6);
  if (previousMessages.length === 0) {
    return query;
  }

  const memory = previousMessages
    .map((message) => `${message.role === "user" ? "User" : "Assistant"}: ${message.content.replace(/\s+/g, " ").slice(0, 280)}`)
    .join("\n");
  const combined = `Use this recent chat context when helpful:\n${memory}\n\nCurrent user question:\n${query}`;
  return combined.slice(0, 3900);
}

function titleFromQuestion(question: string) {
  const compact = question.replace(/\s+/g, " ").trim();
  if (!compact) {
    return "New chat";
  }
  return compact.length > 54 ? `${compact.slice(0, 54)}...` : compact;
}

function createLocalId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function normalizePersonalizationProfile(profile: PersonalizationProfile): PersonalizationProfile {
  return {
    ...profile,
    profileName: profile.profileName.trim(),
    personalNote: profile.personalNote.trim(),
    location: profile.location.trim(),
    housingMarkets: normalizeListText(profile.housingMarkets),
    watchlist: normalizeListText(profile.watchlist).toUpperCase(),
    companies: normalizeListText(profile.companies),
    sectors: normalizeListText(profile.sectors),
    ignoredTopics: normalizeListText(profile.ignoredTopics),
    priorityTopics: uniqueList(profile.priorityTopics),
    housingInterests: uniqueList(profile.housingInterests),
    macroInterests: uniqueList(profile.macroInterests),
    riskPreference: profile.riskPreference || "balanced",
    investingStyle: profile.investingStyle || "long_term",
    answerFormat: profile.answerFormat || "brief",
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
  const location = compactListLabel(splitList(profile.housingMarkets)) === "Not set"
    ? profile.location || "my area"
    : compactListLabel(splitList(profile.housingMarkets));
  const watchlist = compactListLabel(splitList(profile.watchlist));
  const companies = compactListLabel(splitList(profile.companies));
  const sectors = compactListLabel(splitList(profile.sectors));

  return [
    `What matters for ${watchlist === "Not set" ? "my watchlist" : watchlist} today?`,
    `What should I watch in markets this morning based on ${sectors === "Not set" ? "my interests" : sectors}?`,
    `How are rates affecting housing in ${location}?`,
    companies === "Not set" ? "What company news should I pay attention to?" : `What changed with ${companies} this week?`,
  ];
}

function inferAgentContext(query: string, profile: PersonalizationProfile): InferredAgentContext {
  const normalizedQuery = query.toLowerCase();
  const queryTickers = inferTickers(query);
  const profileTickers = splitList(profile.watchlist).map((ticker) => ticker.toUpperCase());
  const companies = inferCompanies(query, profile);
  const location = inferLocation(query, profile);
  const intent = inferIntent(normalizedQuery, queryTickers, companies);
  const tickers =
    queryTickers.length > 0 || shouldUseProfileTickers(normalizedQuery, intent)
      ? queryTickers.length > 0
        ? queryTickers
        : profileTickers
      : [];
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

function shouldUseProfileTickers(normalizedQuery: string, intent: AgentIntent) {
  if (intent === "daily_briefing") {
    return true;
  }

  if (containsAny(normalizedQuery, ["watchlist", "portfolio", "my stocks", "tickers i follow", "companies i follow"])) {
    return true;
  }

  return intent === "company_research" && containsAny(normalizedQuery, ["stock", "stocks", "shares", "earnings", "company"]);
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
  const stateMatches = query.match(/\b(AL|AK|AZ|AR|CA|CO|CT|DE|DC|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b/i);
  if (stateMatches?.[0]) {
    return stateMatches[0].toUpperCase();
  }

  const cityMatches: Array<[string[], string]> = [
    [["phoenix"], "Phoenix"],
    [["austin"], "Austin"],
    [["dallas"], "Dallas"],
    [["houston"], "Houston"],
    [["seattle"], "Seattle"],
    [["denver"], "Denver"],
    [["las vegas"], "Las Vegas"],
    [["los angeles", "la housing"], "Los Angeles"],
    [["san francisco"], "San Francisco"],
    [["san diego"], "San Diego"],
    [["new york", "nyc"], "New York"],
    [["chicago"], "Chicago"],
    [["miami"], "Miami"],
    [["atlanta"], "Atlanta"],
    [["boston"], "Boston"],
    [["raleigh"], "Raleigh"],
    [["charlotte"], "Charlotte"],
    [["tampa"], "Tampa"],
    [["orlando"], "Orlando"],
    [["portland"], "Portland"],
    [["washington dc", "washington, dc"], "Washington DC"],
  ];
  const normalizedQuery = query.toLowerCase();
  const matchedCity = cityMatches.find(([aliases]) => aliases.some((alias) => normalizedQuery.includes(alias)));
  if (matchedCity) {
    return matchedCity[1];
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

function apiTimeWindow(label: string) {
  if (label === "Today") {
    return "today";
  }
  if (label === "This week") {
    return "week";
  }
  if (label === "This month") {
    return "month";
  }
  if (label === "This quarter") {
    return "quarter";
  }
  return "month";
}

function containsAny(value: string, terms: string[]) {
  return terms.some((term) => value.includes(term));
}

function profileSummary(profile: PersonalizationProfile) {
  const profileName = profile.profileName || "local profile";
  const location = profile.location || "no location yet";
  const housingMarkets = compactListLabel(splitList(profile.housingMarkets));
  const watchlist = compactListLabel(splitList(profile.watchlist));
  const sectors = compactListLabel(splitList(profile.sectors));
  const topics = compactListLabel(profile.priorityTopics);
  const ignoredTopics = compactListLabel(splitList(profile.ignoredTopics));

  const note = profile.personalNote ? `Note: ${profile.personalNote}. ` : "";
  return `${profileName}. ${note}Location: ${location}. Housing markets: ${housingMarkets}. Watchlist: ${watchlist}. Sectors: ${sectors}. Priority topics: ${topics}. Risk: ${formatProfileChoice(profile.riskPreference)}. Investing style: ${formatProfileChoice(profile.investingStyle)}. Answer format: ${formatProfileChoice(profile.answerFormat)}. Ignored topics: ${ignoredTopics}. Briefing style: ${profile.briefingStyle}.`;
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

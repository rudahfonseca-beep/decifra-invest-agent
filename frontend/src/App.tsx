import { useCallback, useEffect, useMemo, useState } from "react";
import { CatalystFeed } from "./components/CatalystFeed";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { CreditDetailView } from "./components/views/CreditDetailView";
import { CreditOverviewView } from "./components/views/CreditOverviewView";
import { CoverageView } from "./components/views/CoverageView";
import { DebtView } from "./components/views/DebtView";
import { IndustriesView } from "./components/views/IndustriesView";
import { ProfileView } from "./components/views/ProfileView";
import { ReportView } from "./components/views/ReportView";
import { ScreenerView } from "./components/views/ScreenerView";
import { TickersView } from "./components/views/TickersView";
import { ValuationView } from "./components/views/ValuationView";
import { WaterfallView } from "./components/views/WaterfallView";
import { fetchJson, qs } from "./lib/api";
import type {
  CatalystPayload,
  CompanyProfile,
  CreditDebtMatrix,
  CreditTablePayload,
  FilterState,
  IndustryItem,
  ScreenerPayload,
  TickerListItem,
  ValuationWaterfall,
  ViewId,
} from "./types";

const DEFAULT_FILTERS: FilterState = {
  industry: "All",
  cohort: "All",
  // Signal scan across the full universe is slow; opt-in via filter bar.
  includeSignals: false,
  showIncomplete: false,
};

export default function App() {
  const [view, setView] = useState<ViewId>("credit");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [selectedTicker, setSelectedTicker] = useState("PETR4");

  const [screener, setScreener] = useState<ScreenerPayload | null>(null);
  const [catalysts, setCatalysts] = useState<CatalystPayload | null>(null);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [debt, setDebt] = useState<CreditDebtMatrix | null>(null);
  const [waterfall, setWaterfall] = useState<ValuationWaterfall | null>(null);
  const [credit, setCredit] = useState<CreditTablePayload | null>(null);
  const [industries, setIndustries] = useState<IndustryItem[]>([]);
  const [tickers, setTickers] = useState<TickerListItem[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [loadingShell, setLoadingShell] = useState(true);
  const [loadingCredit, setLoadingCredit] = useState(true);
  const [feedSource, setFeedSource] = useState<"api" | "sample">("sample");

  const loadCredit = useCallback(
    (f: FilterState, refresh = false) => {
      setLoadingCredit(true);
      const q = qs({
        industry: f.industry,
        cohort: f.cohort,
        signals: f.includeSignals,
        incomplete: f.showIncomplete,
        refresh,
      });
      fetchJson<CreditTablePayload>([`/api/credit${q}`, `/sample/credit_table.json`])
        .then((d) => {
          setCredit(d);
          if (d.rows?.[0]?.ticker && !d.rows.find((r) => r.ticker === selectedTicker)) {
            // keep selected if still present; else first row
          }
        })
        .catch((e) => setError(String(e)))
        .finally(() => setLoadingCredit(false));
    },
    [selectedTicker]
  );

  useEffect(() => {
    Promise.all([
      fetchJson<ScreenerPayload>([
        "/api/screener?limit=12",
        "/sample/opportunity_screener.json",
      ]),
      fetchJson<CatalystPayload>([
        "/api/catalysts?limit=12",
        "/sample/catalyst_feed.json",
      ]),
      fetchJson<{ industries: IndustryItem[] }>([
        "/api/industries",
        "/sample/industries.json",
      ]),
      fetchJson<{ tickers: TickerListItem[] }>([
        "/api/tickers?incomplete=true",
        "/sample/tickers.json",
      ]),
      fetchJson<CompanyProfile>([
        `/api/profile/${selectedTicker}`,
        "/sample/company_profile.json",
      ]),
      fetchJson<CreditDebtMatrix>([
        `/api/debt/${selectedTicker}`,
        "/sample/credit_debt_matrix.json",
      ]),
      fetchJson<ValuationWaterfall>([
        `/api/waterfall/${selectedTicker}`,
        "/sample/valuation_waterfall.json",
      ]),
    ])
      .then(([s, c, ind, tix, p, d, w]) => {
        setScreener(s);
        setCatalysts(c);
        setIndustries(ind.industries || []);
        setTickers(tix.tickers || []);
        setProfile(p);
        setDebt(d);
        setWaterfall(w);
        setFeedSource(Array.isArray(ind.industries) && ind.industries.length > 3 ? "api" : "sample");
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoadingShell(false));
  }, [selectedTicker]);

  useEffect(() => {
    loadCredit(filters, false);
  }, [filters, loadCredit]);

  const filteredScreener = useMemo(() => {
    const rows = screener?.rows ?? [];
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (row) =>
        row.ticker.toLowerCase().includes(q) ||
        row.cnpj.includes(q.replace(/\D/g, "")) ||
        row.cnpj.toLowerCase().includes(q) ||
        row.isin.toLowerCase().includes(q) ||
        row.company_name.toLowerCase().includes(q)
    );
  }, [screener, query]);

  function goTicker(ticker: string) {
    setSelectedTicker(ticker);
    setView("detail");
  }

  function goIndustry(industry: string) {
    setFilters((f) => ({ ...f, industry }));
    setView("credit");
  }

  const showCatalyst =
    view === "screener" || view === "credit" || view === "industries" || view === "tickers";

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      <Sidebar active={view} onNavigate={setView} />

      <div className="flex min-w-0 flex-1 flex-col bg-[#0B1120]">
        <Header query={query} onQueryChange={setQuery} />

        <div className="flex min-h-0 flex-1">
          <main className="flex min-w-0 flex-1 flex-col px-4 py-4">
            {error && (
              <p className="mb-3 text-xs text-rose-400">Failed to load data: {error}</p>
            )}
            <p className="mb-2 text-[10px] text-slate-600">
              Feed: {feedSource === "api" ? "lake API" : "sample JSON"} · `decifra schemas serve`
            </p>

            {view === "screener" && (
              <ScreenerView rows={filteredScreener} loading={loadingShell} />
            )}
            {view === "industries" && (
              <IndustriesView
                items={industries}
                loading={loadingShell}
                onSelectIndustry={goIndustry}
              />
            )}
            {view === "tickers" && (
              <TickersView
                rows={tickers}
                loading={loadingShell}
                query={query}
                onSelectTicker={goTicker}
              />
            )}
            {view === "credit" && (
              <CreditOverviewView
                data={credit}
                filters={filters}
                loading={loadingCredit}
                onFilters={setFilters}
                onRefresh={() => loadCredit(filters, true)}
                onSelectTicker={goTicker}
              />
            )}
            {view === "detail" && (
              <CreditDetailView
                ticker={selectedTicker}
                tickers={tickers}
                filters={filters}
                onTickerChange={setSelectedTicker}
              />
            )}
            {view === "valuation" && <ValuationView initialTicker={selectedTicker} />}
            {view === "report" && <ReportView />}
            {view === "coverage" && <CoverageView onSelectTicker={goTicker} />}
            {view === "profile" && <ProfileView profile={profile} loading={loadingShell} />}
            {view === "debt" && <DebtView debt={debt} loading={loadingShell} />}
            {view === "waterfall" && (
              <WaterfallView waterfall={waterfall} loading={loadingShell} />
            )}
          </main>

          {showCatalyst && (
            <CatalystFeed items={catalysts?.items ?? []} loading={loadingShell} />
          )}
        </div>
      </div>
    </div>
  );
}

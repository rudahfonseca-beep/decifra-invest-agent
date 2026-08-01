import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
import { useDebounced } from "./lib/useDebounced";
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

const SCOPE = "core";

export default function App() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<ViewId>("credit");
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounced(query, 250);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [selectedTicker, setSelectedTicker] = useState("PETR4");

  const shellQuery = useQuery({
    queryKey: ["shell", SCOPE],
    queryFn: async () => {
      const [s, c, ind, tix] = await Promise.all([
        fetchJson<ScreenerPayload>([
          `/api/screener${qs({ limit: 12, scope: SCOPE })}`,
          "/sample/opportunity_screener.json",
        ]),
        fetchJson<CatalystPayload>([
          `/api/catalysts${qs({ limit: 12, scope: SCOPE })}`,
          "/sample/catalyst_feed.json",
        ]),
        fetchJson<{ industries: IndustryItem[] }>([
          `/api/industries${qs({ signals: false, scope: SCOPE })}`,
          "/sample/industries.json",
        ]),
        fetchJson<{ tickers: TickerListItem[] }>([
          `/api/tickers${qs({
            incomplete: true,
            signals: false,
            scope: SCOPE,
            q: undefined,
          })}`,
          "/sample/tickers.json",
        ]),
      ]);
      return { screener: s, catalysts: c, industries: ind.industries || [], tickers: tix.tickers || [] };
    },
  });

  const tickersSearchQuery = useQuery({
    queryKey: ["tickers", SCOPE, debouncedQuery],
    enabled: Boolean(debouncedQuery.trim()),
    placeholderData: (prev) => prev,
    queryFn: async () => {
      const tix = await fetchJson<{ tickers: TickerListItem[] }>([
        `/api/tickers${qs({
          incomplete: true,
          signals: false,
          scope: SCOPE,
          q: debouncedQuery.trim(),
          limit: 200,
        })}`,
        "/sample/tickers.json",
      ]);
      return tix.tickers || [];
    },
  });

  const creditQuery = useQuery({
    queryKey: ["credit", SCOPE, filters],
    placeholderData: (prev) => prev,
    queryFn: () =>
      fetchJson<CreditTablePayload>([
        `/api/credit${qs({
          industry: filters.industry,
          cohort: filters.cohort,
          signals: filters.includeSignals,
          incomplete: filters.showIncomplete,
          scope: SCOPE,
        })}`,
        "/sample/credit_table.json",
      ]),
  });

  const tickerDetailQuery = useQuery({
    queryKey: ["ticker", selectedTicker],
    placeholderData: (prev) => prev,
    queryFn: async () => {
      const [p, d, w] = await Promise.all([
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
      ]);
      return { profile: p, debt: d, waterfall: w };
    },
  });

  const screener = shellQuery.data?.screener ?? null;
  const catalysts = shellQuery.data?.catalysts ?? null;
  const industries = shellQuery.data?.industries ?? [];
  const tickers =
    debouncedQuery.trim() && tickersSearchQuery.data
      ? tickersSearchQuery.data
      : shellQuery.data?.tickers ?? [];
  const credit = creditQuery.data ?? null;
  const profile = tickerDetailQuery.data?.profile ?? null;
  const debt = tickerDetailQuery.data?.debt ?? null;
  const waterfall = tickerDetailQuery.data?.waterfall ?? null;

  const error =
    shellQuery.error || creditQuery.error || tickerDetailQuery.error
      ? String(shellQuery.error || creditQuery.error || tickerDetailQuery.error)
      : null;

  const feedSource: "api" | "sample" =
    industries.length > 3 ? "api" : "sample";

  const loadingShell = shellQuery.isLoading || shellQuery.isFetching;
  const loadingCredit = creditQuery.isLoading || creditQuery.isFetching;
  const loadingTicker = tickerDetailQuery.isLoading || tickerDetailQuery.isFetching;

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

  const shellBlocking = loadingShell && industries.length === 0 && !screener;
  const creditBlocking = loadingCredit && !credit;
  const tickerBlocking = loadingTicker && !profile;

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
              Feed: {feedSource === "api" ? "lake API" : "sample JSON"} · scope={SCOPE} ·{" "}
              `decifra schemas serve`
              {(loadingShell || loadingCredit || loadingTicker) && " · refreshing…"}
            </p>

            {view === "screener" && (
              <ScreenerView
                rows={filteredScreener}
                loading={shellBlocking}
                refreshing={loadingShell && !shellBlocking}
              />
            )}
            {view === "industries" && (
              <IndustriesView
                items={industries}
                loading={shellBlocking}
                refreshing={loadingShell && !shellBlocking}
                onSelectIndustry={goIndustry}
              />
            )}
            {view === "tickers" && (
              <TickersView
                rows={tickers}
                loading={shellBlocking && tickers.length === 0}
                refreshing={
                  (loadingShell || tickersSearchQuery.isFetching) && tickers.length > 0
                }
                query={query}
                onSelectTicker={goTicker}
              />
            )}
            {view === "credit" && (
              <CreditOverviewView
                data={credit}
                filters={filters}
                loading={creditBlocking}
                refreshing={loadingCredit && !creditBlocking}
                onFilters={setFilters}
                onRefresh={() =>
                  queryClient.invalidateQueries({ queryKey: ["credit", SCOPE, filters] })
                }
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
            {view === "profile" && (
              <ProfileView
                profile={profile}
                loading={tickerBlocking}
                refreshing={loadingTicker && !tickerBlocking}
              />
            )}
            {view === "debt" && (
              <DebtView
                debt={debt}
                loading={tickerBlocking}
                refreshing={loadingTicker && !tickerBlocking}
              />
            )}
            {view === "waterfall" && (
              <WaterfallView
                waterfall={waterfall}
                loading={tickerBlocking}
                refreshing={loadingTicker && !tickerBlocking}
              />
            )}
          </main>

          {showCatalyst && (
            <CatalystFeed
              items={catalysts?.items ?? []}
              loading={shellBlocking}
              refreshing={loadingShell && !shellBlocking}
            />
          )}
        </div>
      </div>
    </div>
  );
}

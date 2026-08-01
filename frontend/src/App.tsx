import { useEffect, useMemo, useState } from "react";
import { CatalystFeed } from "./components/CatalystFeed";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { DebtView } from "./components/views/DebtView";
import { ProfileView } from "./components/views/ProfileView";
import { ScreenerView } from "./components/views/ScreenerView";
import { WaterfallView } from "./components/views/WaterfallView";
import type {
  CatalystPayload,
  CompanyProfile,
  CreditDebtMatrix,
  ScreenerPayload,
  ValuationWaterfall,
  ViewId,
} from "./types";

async function fetchJson<T>(urls: string[]): Promise<T> {
  let lastError: unknown;
  for (const url of urls) {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`${url} -> ${r.status}`);
      return (await r.json()) as T;
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError ?? new Error("fetch failed");
}

export default function App() {
  const [view, setView] = useState<ViewId>("screener");
  const [query, setQuery] = useState("");
  const [screener, setScreener] = useState<ScreenerPayload | null>(null);
  const [catalysts, setCatalysts] = useState<CatalystPayload | null>(null);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [debt, setDebt] = useState<CreditDebtMatrix | null>(null);
  const [waterfall, setWaterfall] = useState<ValuationWaterfall | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedSource, setFeedSource] = useState<"api" | "sample">("sample");

  useEffect(() => {
    const detail = "PETR4";
    Promise.all([
      fetchJson<ScreenerPayload>([
        "/api/screener?limit=8",
        "/sample/opportunity_screener.json",
      ]),
      fetchJson<CatalystPayload>([
        "/api/catalysts?limit=8",
        "/sample/catalyst_feed.json",
      ]),
      fetchJson<CompanyProfile>([
        `/api/profile/${detail}`,
        "/sample/company_profile.json",
      ]),
      fetchJson<CreditDebtMatrix>([
        `/api/debt/${detail}`,
        "/sample/credit_debt_matrix.json",
      ]),
      fetchJson<ValuationWaterfall>([
        `/api/waterfall/${detail}`,
        "/sample/valuation_waterfall.json",
      ]),
    ])
      .then(([s, c, p, d, w]) => {
        setScreener(s);
        setCatalysts(c);
        setProfile(p);
        setDebt(d);
        setWaterfall(w);
        // Heuristic: live API rows usually have ISO as_of from assemblers
        setFeedSource(s.as_of?.includes("T") && !s.as_of.startsWith("2026-08-01T02") ? "api" : "sample");
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const filteredRows = useMemo(() => {
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
              Data feed: {feedSource === "api" ? "lake API /api/*" : "static sample JSON"}
              {" · "}
              run `decifra schemas serve` or `decifra schemas export-ui` for live lake
            </p>

            {view === "screener" && (
              <ScreenerView rows={filteredRows} loading={loading} />
            )}
            {view === "profile" && <ProfileView profile={profile} loading={loading} />}
            {view === "debt" && <DebtView debt={debt} loading={loading} />}
            {view === "waterfall" && (
              <WaterfallView waterfall={waterfall} loading={loading} />
            )}
          </main>

          <CatalystFeed items={catalysts?.items ?? []} loading={loading} />
        </div>
      </div>
    </div>
  );
}

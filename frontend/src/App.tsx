import { useEffect, useState } from "react";

type Tab = "profile" | "debt" | "waterfall";

type Metric = { value: number | string | null; lineage?: { source_doc?: string } };

export default function App() {
  const [tab, setTab] = useState<Tab>("profile");
  const [profile, setProfile] = useState<any>(null);
  const [debt, setDebt] = useState<any>(null);
  const [waterfall, setWaterfall] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/sample/company_profile.json").then((r) => r.json()),
      fetch("/sample/credit_debt_matrix.json").then((r) => r.json()),
      fetch("/sample/valuation_waterfall.json").then((r) => r.json()),
    ])
      .then(([p, d, w]) => {
        setProfile(p);
        setDebt(d);
        setWaterfall(w);
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <>
      <header>
        <h1>decifra</h1>
        <p>Dark-mode research UI (MVP) — Company Profile · Credit & Debt · Valuation Waterfall</p>
      </header>

      <nav className="tabs">
        {(
          [
            ["profile", "Company Profile"],
            ["debt", "Credit & Debt"],
            ["waterfall", "Valuation Waterfall"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            className={tab === id ? "active" : ""}
            onClick={() => setTab(id)}
            type="button"
          >
            {label}
          </button>
        ))}
      </nav>

      {error && <p className="empty">Failed to load samples: {error}</p>}

      {tab === "profile" && (
        <section className="panel">
          <h2>Company Profile</h2>
          {!profile ? (
            <p className="empty">Loading…</p>
          ) : (
            <>
              <div className="meta">
                {profile.ticker} · CNPJ {profile.cnpj || "—"} · {profile.currency}
              </div>
              <p>{profile.company_name || "—"}</p>
              <p className="lineage">ISINs: {(profile.isins || []).join(", ") || "—"}</p>
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Lineage</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(profile.metrics || {}).map(([k, m]) => {
                    const metric = m as Metric;
                    return (
                      <tr key={k}>
                        <td>{k}</td>
                        <td>{String(metric.value)}</td>
                        <td className="lineage">{metric.lineage?.source_doc}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </>
          )}
        </section>
      )}

      {tab === "debt" && (
        <section className="panel">
          <h2>Integrated Credit & Debt Matrix</h2>
          {!debt ? (
            <p className="empty">Loading…</p>
          ) : (
            <>
              <div className="meta">{debt.ticker}</div>
              <p>
                Capacity breach:{" "}
                <span
                  className={
                    debt.capacity?.any_breach ? "badge badge-breach" : "badge badge-ok"
                  }
                >
                  {String(debt.capacity?.any_breach)}
                </span>
              </p>
              <table>
                <thead>
                  <tr>
                    <th>Code/ISIN</th>
                    <th>Type</th>
                    <th>Indexer</th>
                    <th>Maturity</th>
                    <th>Lineage</th>
                  </tr>
                </thead>
                <tbody>
                  {(debt.facilities || []).map((f: any, i: number) => (
                    <tr key={i}>
                      <td>{f.isin_or_code}</td>
                      <td>{f.instrument_type}</td>
                      <td>{f.indexer}</td>
                      <td>{f.maturity}</td>
                      <td className="lineage">{f.lineage?.source_doc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>
      )}

      {tab === "waterfall" && (
        <section className="panel">
          <h2>Valuation Waterfall</h2>
          {!waterfall ? (
            <p className="empty">Loading…</p>
          ) : (
            <>
              <div className="meta">
                {waterfall.ticker} · {waterfall.method}
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Output</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(waterfall.outputs || {}).map(([k, v]) => (
                    <tr key={k}>
                      <td>{k}</td>
                      <td>{v == null ? "—" : String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="lineage">source: {waterfall.lineage?.source_doc}</p>
            </>
          )}
        </section>
      )}
    </>
  );
}

/** Group flat ticker rows into one row per issuer (CNPJ / company). */

export type CompanyGroupable = {
  ticker: string;
  company?: string;
  company_name?: string;
  cnpj?: string;
  has_financials?: boolean;
  credit_score?: number | null;
};

export type CompanyGroup<T extends CompanyGroupable> = {
  key: string;
  company: string;
  cnpj: string;
  tickers: string[];
  /** Preferred ticker for navigation / metrics. */
  primaryTicker: string;
  members: T[];
};

function companyLabel(r: CompanyGroupable): string {
  return (r.company || r.company_name || "").trim();
}

function groupKey(r: CompanyGroupable): string {
  const cnpj = (r.cnpj || "").replace(/\D/g, "");
  if (cnpj) return `cnpj:${cnpj}`;
  const name = companyLabel(r).toUpperCase();
  if (name) return `name:${name}`;
  return `ticker:${r.ticker.toUpperCase()}`;
}

function classRank(ticker: string): number {
  if (/4$/.test(ticker)) return 0;
  if (/3$/.test(ticker)) return 1;
  if (/11$/.test(ticker)) return 2;
  return 3;
}

/** Prefer liquid/common share class with financials and stronger credit. */
export function pickPrimaryTicker<T extends CompanyGroupable>(members: T[]): string {
  const sorted = [...members].sort((a, b) => {
    if (!!a.has_financials !== !!b.has_financials) return a.has_financials ? -1 : 1;
    const sa = a.credit_score ?? -1;
    const sb = b.credit_score ?? -1;
    if (sa !== sb) return sb - sa;
    const ra = classRank(a.ticker);
    const rb = classRank(b.ticker);
    if (ra !== rb) return ra - rb;
    return a.ticker.localeCompare(b.ticker);
  });
  return sorted[0]?.ticker ?? members[0].ticker;
}

export function groupByCompany<T extends CompanyGroupable>(rows: T[]): CompanyGroup<T>[] {
  const map = new Map<string, T[]>();
  for (const row of rows) {
    const k = groupKey(row);
    const list = map.get(k);
    if (list) list.push(row);
    else map.set(k, [row]);
  }

  const groups: CompanyGroup<T>[] = [];
  for (const [key, members] of map) {
    const tickers = [...new Set(members.map((m) => m.ticker))].sort((a, b) => {
      const ra = classRank(a);
      const rb = classRank(b);
      if (ra !== rb) return ra - rb;
      return a.localeCompare(b);
    });
    const head = members.find((m) => companyLabel(m)) || members[0];
    groups.push({
      key,
      company: companyLabel(head) || tickers[0],
      cnpj: (head.cnpj || "").replace(/\D/g, "") || head.cnpj || "",
      tickers,
      primaryTicker: pickPrimaryTicker(members),
      members,
    });
  }

  groups.sort((a, b) => a.company.localeCompare(b.company) || a.cnpj.localeCompare(b.cnpj));
  return groups;
}

export function formatCnpj(cnpj: string): string {
  const d = cnpj.replace(/\D/g, "");
  if (d.length !== 14) return cnpj || "—";
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}

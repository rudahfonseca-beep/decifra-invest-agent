export type ViewId = "screener" | "profile" | "debt" | "waterfall";

export type Signal = "safe" | "warning" | "distress";

export type Metric = {
  value: number | string | null;
  lineage?: { source_doc?: string };
};

export type ScreenerRow = {
  ticker: string;
  cnpj: string;
  isin: string;
  company_name: string;
  apv_discount_pct: number;
  ev_equity: number;
  net_debt_ebitda: number;
  dscr: number;
  merton_pd_pct: number;
  signal: Signal;
  lineage: {
    equity: string;
    credit: string;
  };
};

export type ScreenerPayload = {
  as_of: string;
  rows: ScreenerRow[];
};

export type CatalystItem = {
  id: string;
  source: string;
  ts_relative: string;
  title: string;
  impact: string;
  signal: Signal;
};

export type CatalystPayload = {
  items: CatalystItem[];
};

export type CompanyProfile = {
  ticker: string;
  cnpj?: string;
  cvm_code?: string;
  company_name?: string;
  isins?: string[];
  currency?: string;
  metrics?: Record<string, Metric>;
};

export type DebtFacility = {
  isin_or_code: string;
  instrument_type: string;
  indexer: string;
  yield_pct?: number;
  maturity: string;
  outstanding_brl?: number;
  covenant_text?: string;
  lineage?: { source_doc?: string };
};

export type CreditDebtMatrix = {
  ticker: string;
  as_of?: string;
  facilities?: DebtFacility[];
  capacity?: {
    net_debt_ebitda?: number | null;
    dscr?: number | null;
    any_breach?: boolean;
    lineage?: { source_doc?: string };
  };
};

export type ValuationWaterfall = {
  ticker: string;
  method: string;
  inputs?: Record<string, Metric>;
  outputs?: Record<string, number | null>;
  lineage?: { source_doc?: string };
};

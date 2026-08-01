export type ViewId =
  | "screener"
  | "industries"
  | "tickers"
  | "credit"
  | "detail"
  | "report"
  | "valuation"
  | "coverage"
  | "profile"
  | "debt"
  | "waterfall";

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
  apv_discount_pct: number | null;
  ev_equity: number | null;
  net_debt_ebitda: number | null;
  dscr: number | null;
  merton_pd_pct: number | null;
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

export type CreditRow = {
  ticker: string;
  company?: string;
  cnpj?: string;
  isins?: string[];
  industry_group?: string;
  sector?: string;
  cohort?: string;
  period?: string;
  has_financials?: boolean;
  credit_score?: number | null;
  fundamental_score?: number | null;
  qualitative_penalty?: number | null;
  debt_to_equity?: number | null;
  current_ratio?: number | null;
  interest_coverage?: number | null;
  net_margin?: number | null;
  equity_to_assets?: number | null;
  roe?: number | null;
  peer_benchmark?: boolean;
  signal_hits?: number | null;
};

export type CreditTablePayload = {
  industries: string[];
  cohorts: string[];
  filters: {
    industry: string;
    cohort: string;
    include_signals: boolean;
    show_incomplete: boolean;
  };
  summary: {
    companies: number;
    median_credit_score: number | null;
    mean_credit_score: number | null;
    with_peer_benchmark: number;
  };
  peer_medians: Record<string, number | null>;
  peer_median_labels: Record<string, string>;
  pct_kpis: string[];
  rows: CreditRow[];
};

export type IndustryItem = {
  industry_group: string;
  cohort?: string | null;
  companies: number;
  median_credit_score: number | null;
  mean_credit_score: number | null;
  tickers: string[];
};

export type TickerListItem = {
  ticker: string;
  company?: string;
  cnpj?: string;
  industry_group?: string;
  sector?: string;
  cohort?: string;
  period?: string;
  has_financials?: boolean;
  credit_score?: number | null;
  peer_benchmark?: boolean;
};

export type CreditDetail = {
  found: boolean;
  ticker: string;
  company?: string;
  industry_group?: string;
  sector?: string;
  cohort?: string;
  period?: string;
  cnpj?: string;
  isins?: string[];
  credit_score?: number | null;
  fundamental_score?: number | null;
  qualitative_penalty?: number | null;
  peer_benchmark?: boolean;
  has_financials?: boolean;
  ratios?: {
    key: string;
    label: string;
    company: number | null;
    peer_median: number | null;
    higher_better: boolean;
    pct: boolean;
  }[];
  signals?: {
    qualitative_penalty?: number;
    matched_keywords?: string[];
    signal_hits?: {
      source?: string;
      date?: string;
      title?: string;
      keywords?: string[];
      path?: string;
      url?: string;
    }[];
  } | null;
  error?: string;
};

export type FilterState = {
  industry: string;
  cohort: string;
  includeSignals: boolean;
  showIncomplete: boolean;
};

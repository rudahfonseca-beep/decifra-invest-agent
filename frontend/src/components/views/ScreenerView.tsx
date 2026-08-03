import { OpportunityScreener } from "../OpportunityScreener";
import type { ScreenerRow } from "../../types";

type Props = {
  rows: ScreenerRow[];
  loading?: boolean;
  refreshing?: boolean;
  query?: string;
};

export function ScreenerView({ rows, loading, refreshing, query }: Props) {
  return (
    <OpportunityScreener rows={rows} loading={loading} refreshing={refreshing} query={query} />
  );
}

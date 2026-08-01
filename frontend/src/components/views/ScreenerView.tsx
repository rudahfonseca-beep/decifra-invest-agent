import { OpportunityScreener } from "../OpportunityScreener";
import type { ScreenerRow } from "../../types";

type Props = {
  rows: ScreenerRow[];
  loading?: boolean;
  refreshing?: boolean;
};

export function ScreenerView({ rows, loading, refreshing }: Props) {
  return <OpportunityScreener rows={rows} loading={loading} refreshing={refreshing} />;
}

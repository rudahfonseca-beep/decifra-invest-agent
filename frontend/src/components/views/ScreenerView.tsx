import { OpportunityScreener } from "../OpportunityScreener";
import type { ScreenerRow } from "../../types";

type Props = {
  rows: ScreenerRow[];
  loading?: boolean;
};

export function ScreenerView({ rows, loading }: Props) {
  return <OpportunityScreener rows={rows} loading={loading} />;
}

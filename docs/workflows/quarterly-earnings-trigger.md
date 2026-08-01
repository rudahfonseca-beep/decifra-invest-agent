# Workflow: Quarterly earnings trigger (stub)

**Status:** Planned — not implemented. Tracked as `AUTO-009`.  
**Roadmap:** Phase 1 (ingest) + Phase 3 (models) + Phase 5 (schemas).

## Purpose

Event-driven refresh when a new **ITR** or **DFP** filing is detected on CVM Dados Abertos:

1. Update 3-statement CSVs for affected CNPJ/tickers
2. Recompute credit KPIs / capacity flags (when Phase 3 exists)
3. Refresh valuation defaults that depend on latest statements
4. Emit/update Company Profile + Credit & Debt Matrix + Valuation Waterfall artifacts (Phase 5)

## Intended detection

- Poll or diff CVM DFP/ITR zip inventories / `DT_REFER`+`VERSAO` vs lake
- Or hook after `decifra sync financials` coverage delta shows new periods

## Intended CLI (future)

```bash
.\.venv\Scripts\python.exe -m decifra sync financials --ticker PETR4
.\.venv\Scripts\python.exe -m decifra pipeline refresh --ticker PETR4 --reason itr_dfp
```

## Closeout

Document trigger reason, tickers touched, and model refresh status in an automation AAR; refresh session dashboard.

## Related

- Current sync: `docs/workflows/sync-pilot.md`
- Auditor: `docs/prompts/unified-pipeline-auditor.md`

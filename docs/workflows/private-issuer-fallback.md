# Workflow: Private issuer fallback

**Status:** Implemented (CLI + resolver) — rating agency scrapers still stub. Tracked as `AUTO-010` / IMP-024.  
**Roadmap:** Phase 2.

## Purpose

When a CNPJ query returns **no Category A** CVM equity filings (companhia fechada / unlisted issuer), run the fallback chain instead of failing silently.

## Fallback order (strict)

1. **ANBIMA** prospectuses / fixed-income issuer docs (`data/cache/anbima/`)  
2. **B3 Balcão** bond registrations  
3. **Credit rating agency** public press releases (Adjusted Net Debt / Adjusted EBITDA) — stub until parsers land

Hierarchy of Truth still applies for conflicting figures: **CVM > ANBIMA > Rating Agency > Web screeners**.

## CLI

```bash
.\.venv\Scripts\python.exe -m decifra entities sync
.\.venv\Scripts\python.exe -m decifra entities resolve --ticker PETR4
.\.venv\Scripts\python.exe -m decifra entities resolve --cnpj 33000167000101
.\.venv\Scripts\python.exe -m decifra entities private-issuer --cnpj 33000167000101
```

## Artifacts

- `data/universe/entities.json` — canonical CNPJ ↔ CVM ↔ ticker ↔ ISIN
- Debt extracts under `data/companies/{TICKER}/debt/`
- Lineage tags on fallback steps (`lineage.source_doc`)

## Do not

- Invent Category A DFP rows for private issuers
- Skip ANBIMA/Balcão and jump straight to screeners

# Workflow: Private issuer fallback (stub)

**Status:** Planned — not implemented. Tracked as `AUTO-010` / `IMP-024`.  
**Roadmap:** Phase 2.

## Purpose

When a CNPJ query returns **no Category A** CVM equity filings (companhia fechada / unlisted issuer), run the fallback chain instead of failing silently.

## Fallback order (strict)

1. **ANBIMA** prospectuses / fixed-income issuer docs  
2. **B3 Balcão** bond registrations  
3. **Credit rating agency** public press releases (Adjusted Net Debt / Adjusted EBITDA)

Hierarchy of Truth still applies for conflicting figures: CVM > ANBIMA > Rating Agency > Web screeners.

## Intended CLI (future)

```bash
.\.venv\Scripts\python.exe -m decifra entities resolve --cnpj 00000000000191
.\.venv\Scripts\python.exe -m decifra sync private-issuer --cnpj 00000000000191
```

## Artifacts

- Entity record under `data/universe/entities.json` (or per-issuer folder when designed)
- Debt / prospectus extracts under a non-ticker path if no B3 equity ticker exists
- Lineage tags on every scraped metric

## Do not

- Invent Category A DFP rows for private issuers
- Skip ANBIMA/Balcão and jump straight to screeners

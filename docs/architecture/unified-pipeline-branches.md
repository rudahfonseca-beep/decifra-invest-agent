# Unified Pipeline — Branch & Commit Structure

**Epic:** `feat/unified-pipeline` (merge target for phases; PR to `main` later)  
**Do not push** until explicitly approved.

## Branch map

| Branch | Scope | IMP IDs | Merges into |
|--------|-------|---------|-------------|
| `feat/unified-pipeline` | Progress JSON, Pipeline dashboard tab, end-state viz, phase merges | — | `main` |
| `feat/pipeline-phase-1` | FRE, ANBIMA, B3 shares/Balcão | IMP-020..022 | epic |
| `feat/pipeline-phase-2` | Entity graph + Hierarchy + private fallback | IMP-023..024 | epic |
| `feat/pipeline-phase-3` | APV, Merton, capacity, FCFE waterfall | IMP-025..028 | epic |
| `feat/pipeline-phase-4` | CVM funds + EDGAR | IMP-029..030 | epic |
| `feat/pipeline-phase-5` | Schemas, ITR–debt align, React MVP | IMP-031..033 | epic |

```text
main
 └─ feat/unified-pipeline
     ├─ feat/pipeline-phase-1  (merged locally)
     ├─ feat/pipeline-phase-2
     ├─ feat/pipeline-phase-3
     ├─ feat/pipeline-phase-4
     └─ feat/pipeline-phase-5
```

## Commit convention

1. Epic bootstrap: `docs: pipeline progress tracker + dashboard Pipeline tab`
2. Per deliverable: `feat(<area>): …` (one IMP-focused commit when practical)
3. Phase closeout: `docs(aar): Phase N unified pipeline AAR` (+ progress/gap/LOG updates)
4. After phase: merge phase branch → `feat/unified-pipeline` locally

## Progress source of truth

[`pipeline-progress.json`](pipeline-progress.json) drives the HTML **Pipeline** tab via `scripts/update_session_dashboard.py`.
Update deliverable `status` (`todo` | `in_progress` | `done` | `blocked`) as work lands.

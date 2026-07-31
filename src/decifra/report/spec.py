"""ReportSpec model and validation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from decifra.report.catalog import (
    ALL_KPIS,
    ReportMode,
    default_kpis,
    known_industry_groups,
)
from decifra.store.folders import list_tickers


@dataclass
class EntitySelection:
    companies: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.companies and not self.industries


@dataclass
class ReportSpec:
    mode: ReportMode = "credit"
    title: str = ""
    subjects: EntitySelection = field(default_factory=EntitySelection)
    comparatives: EntitySelection = field(default_factory=EntitySelection)
    kpis: list[str] = field(default_factory=list)
    include_signals: bool = True
    language: str = "pt"

    def resolved_kpis(self) -> list[str]:
        if self.kpis:
            return list(self.kpis)
        return default_kpis(self.mode)

    def default_title(self) -> str:
        if self.title.strip():
            return self.title.strip()
        parts: list[str] = []
        if self.subjects.companies:
            parts.append(", ".join(self.subjects.companies))
        if self.subjects.industries:
            parts.append(", ".join(self.subjects.industries))
        focus = " · ".join(parts) if parts else "custom"
        label = "Credit" if self.mode == "credit" else "Equity"
        return f"{label} report — {focus}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReportSpec:
        subjects = data.get("subjects") or {}
        comparatives = data.get("comparatives") or {}
        mode = str(data.get("mode") or "credit").lower().strip()
        if mode not in {"credit", "equity"}:
            raise ValueError(f"Invalid mode '{mode}'; expected 'credit' or 'equity'")
        lang = str(data.get("language") or "pt").lower().strip()
        if lang not in {"pt", "en"}:
            raise ValueError(f"Invalid language '{lang}'; expected 'pt' or 'en'")
        return cls(
            mode=mode,  # type: ignore[arg-type]
            title=str(data.get("title") or ""),
            subjects=EntitySelection(
                companies=[str(c).upper() for c in (subjects.get("companies") or [])],
                industries=[str(i) for i in (subjects.get("industries") or [])],
            ),
            comparatives=EntitySelection(
                companies=[str(c).upper() for c in (comparatives.get("companies") or [])],
                industries=[str(i) for i in (comparatives.get("industries") or [])],
            ),
            kpis=[str(k) for k in (data.get("kpis") or [])],
            include_signals=bool(data.get("include_signals", True)),
            language=lang,
        )


class SpecValidationError(ValueError):
    """Raised when a report spec fails validation."""


def load_spec(path: str | Path) -> ReportSpec:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SpecValidationError("Spec file must contain a JSON object")
    try:
        spec = ReportSpec.from_dict(raw)
    except ValueError as exc:
        raise SpecValidationError(str(exc)) from exc
    return validate_spec(spec)


def validate_spec(
    spec: ReportSpec,
    *,
    known_tickers: list[str] | None = None,
    known_industries: list[str] | None = None,
) -> ReportSpec:
    """Validate and normalize a ReportSpec. Returns the same instance after checks."""
    if spec.mode not in {"credit", "equity"}:
        raise SpecValidationError(f"Invalid mode '{spec.mode}'")

    if spec.subjects.is_empty():
        raise SpecValidationError(
            "Subjects must include at least one company or industry"
        )

    tickers = {t.upper() for t in (known_tickers if known_tickers is not None else list_tickers())}
    industries = {
        i.lower(): i
        for i in (known_industries if known_industries is not None else known_industry_groups())
    }

    def _check_companies(label: str, companies: list[str]) -> list[str]:
        out: list[str] = []
        for c in companies:
            t = c.upper().strip()
            if not t:
                continue
            if tickers and t not in tickers:
                raise SpecValidationError(f"Unknown ticker in {label}: {t}")
            out.append(t)
        return out

    def _check_industries(label: str, names: list[str]) -> list[str]:
        out: list[str] = []
        for name in names:
            key = name.strip()
            if not key:
                continue
            match = industries.get(key.lower())
            if match is None:
                # Allow exact casing from credit table even if not in static map
                # (e.g. dynamic "Other") — still reject totally unknown when map set
                known_exact = {v.lower(): v for v in industries.values()}
                match = known_exact.get(key.lower())
            if match is None:
                raise SpecValidationError(f"Unknown industry in {label}: {name}")
            out.append(match)
        return out

    spec.subjects.companies = _check_companies("subjects", spec.subjects.companies)
    spec.subjects.industries = _check_industries("subjects", spec.subjects.industries)
    spec.comparatives.companies = _check_companies(
        "comparatives", spec.comparatives.companies
    )
    spec.comparatives.industries = _check_industries(
        "comparatives", spec.comparatives.industries
    )

    # Re-check after normalization (empty strings stripped)
    if spec.subjects.is_empty():
        raise SpecValidationError(
            "Subjects must include at least one company or industry"
        )

    if spec.kpis:
        unknown = [k for k in spec.kpis if k not in ALL_KPIS]
        if unknown:
            raise SpecValidationError(
                f"Unknown KPI(s): {', '.join(unknown)}. "
                f"Known: {', '.join(ALL_KPIS)}"
            )

    if spec.language not in {"pt", "en"}:
        raise SpecValidationError(f"Invalid language '{spec.language}'")

    return spec

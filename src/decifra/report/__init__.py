"""Shared credit/equity report builder: spec → context → LLM prompt / HTML."""

from decifra.report.assemble import assemble_context
from decifra.report.generate import build_report_artifacts
from decifra.report.spec import ReportSpec, load_spec, validate_spec

__all__ = [
    "ReportSpec",
    "assemble_context",
    "build_report_artifacts",
    "load_spec",
    "validate_spec",
]

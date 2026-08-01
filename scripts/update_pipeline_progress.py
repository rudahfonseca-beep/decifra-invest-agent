#!/usr/bin/env python3
"""Update docs/architecture/pipeline-progress.json deliverable/phase statuses."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "docs" / "architecture" / "pipeline-progress.json"

VALID = {"todo", "in_progress", "done", "blocked"}


def load() -> dict:
    return json.loads(PROGRESS.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    data["updated"] = date.today().isoformat()
    PROGRESS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def set_deliverable(imp_id: str, status: str, *, aar: str | None = None) -> None:
    if status not in VALID:
        raise SystemExit(f"status must be one of {sorted(VALID)}")
    data = load()
    found = False
    for phase in data["phases"]:
        for d in phase["deliverables"]:
            if d["id"] == imp_id:
                d["status"] = status
                found = True
        statuses = {d["status"] for d in phase["deliverables"]}
        if statuses == {"done"}:
            phase["status"] = "done"
        elif "in_progress" in statuses or "done" in statuses:
            phase["status"] = "in_progress"
        elif "blocked" in statuses and statuses <= {"blocked", "todo"}:
            phase["status"] = "blocked"
        else:
            phase["status"] = "todo"
        if aar and found and any(d["id"] == imp_id for d in phase["deliverables"]):
            # set aar on phase when closing any deliverable with --aar
            if status == "done":
                phase["aar"] = aar
    if not found:
        raise SystemExit(f"Unknown deliverable id: {imp_id}")
    # Recompute overall
    all_d = [d for p in data["phases"] for d in p["deliverables"]]
    if all(d["status"] == "done" for d in all_d):
        data["overall_status"] = "done"
    elif any(d["status"] in ("in_progress", "done") for d in all_d):
        data["overall_status"] = "in_progress"
    else:
        data["overall_status"] = "todo"
    save(data)
    print(f"Updated {imp_id} -> {status}")


def set_pillar(pillar: str, grade: str) -> None:
    data = load()
    if pillar not in data["pillars"]:
        raise SystemExit(f"Unknown pillar: {pillar}")
    data["pillars"][pillar]["grade"] = grade
    save(data)
    print(f"Updated pillar {pillar} -> {grade}")


def set_phase_aar(phase_id: int, aar: str) -> None:
    data = load()
    for phase in data["phases"]:
        if phase["id"] == phase_id:
            phase["aar"] = aar
            save(data)
            print(f"Phase {phase_id} aar -> {aar}")
            return
    raise SystemExit(f"Unknown phase: {phase_id}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("deliverable", help="Set IMP-* status")
    d.add_argument("id")
    d.add_argument("status", choices=sorted(VALID))
    d.add_argument("--aar", default=None)

    pl = sub.add_parser("pillar", help="Set pillar grade")
    pl.add_argument("pillar")
    pl.add_argument("grade")

    pa = sub.add_parser("phase-aar", help="Attach AAR path to a phase")
    pa.add_argument("phase", type=int)
    pa.add_argument("aar")

    args = p.parse_args()
    if args.cmd == "deliverable":
        set_deliverable(args.id, args.status, aar=args.aar)
    elif args.cmd == "pillar":
        set_pillar(args.pillar, args.grade)
    elif args.cmd == "phase-aar":
        set_phase_aar(args.phase, args.aar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

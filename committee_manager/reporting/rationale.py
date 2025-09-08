"""Utilities for exporting allocation rationales and committee health.

This module provides functions to transform an
:class:`~committee_manager.engine.allocator.AllocationResult` into
structures suitable for YAML or CSV output.  Seat rationales are grouped
by committee and person, and health metrics summarize overall committee
status.
"""
from __future__ import annotations

import csv
from typing import Dict, Tuple

import yaml

from ..engine.allocator import AllocationResult


def format_seat_rationales(result: AllocationResult) -> Dict[str, Dict[str, str]]:
    """Return seat rationales grouped by committee and person.

    Parameters
    ----------
    result:
        Allocation result containing rationales keyed by ``(committee, person)``.

    Returns
    -------
    dict[str, dict[str, str]]
        Mapping of committee name -> person name -> rationale string.
    """
    grouped: Dict[str, Dict[str, str]] = {}
    for (committee, person), rationale in sorted(result.rationales.items()):
        grouped.setdefault(committee, {})[person] = rationale
    return grouped


def export_yaml(result: AllocationResult, allocation_file: str, rationale_file: str) -> None:
    """Write allocation and rationale data to YAML files.

    The allocation file maps each committee to a list of member names. The
    rationale file contains per-seat rationales and committee health metrics.

    Parameters
    ----------
    result:
        Allocation package produced by the allocator.
    allocation_file:
        Path to write committee membership YAML.
    rationale_file:
        Path to write rationales + health YAML.
    """
    allocations = {
        committee.name: [person.name for person in sorted(committee.members, key=lambda p: p.name)]
        for committee in sorted(result.committees, key=lambda c: c.name)
    }
    rationales = {
        "seats": format_seat_rationales(result),
        "committee_health": result.committee_health,
    }
    with open(allocation_file, "w", encoding="utf8") as handle:
        yaml.safe_dump(allocations, handle, sort_keys=True)
    with open(rationale_file, "w", encoding="utf8") as handle:
        yaml.safe_dump(rationales, handle, sort_keys=True)


def export_csv(result: AllocationResult, allocation_file: str, rationale_file: str) -> None:
    """Write allocation and rationale data to CSV files.

    The allocation CSV has columns ``committee`` and ``person``. The
    rationale CSV first lists seat rationales with columns ``committee``,
    ``person`` and ``rationale``. After a blank row a second header is
    written containing committee health metrics.
    """
    allocation_rows = []
    for committee in sorted(result.committees, key=lambda c: c.name):
        for person in sorted(committee.members, key=lambda p: p.name):
            allocation_rows.append({"committee": committee.name, "person": person.name})
    with open(allocation_file, "w", newline="", encoding="utf8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["committee", "person"])
        writer.writeheader()
        writer.writerows(allocation_rows)

    seat_rationales = format_seat_rationales(result)
    with open(rationale_file, "w", newline="", encoding="utf8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["committee", "person", "rationale"])
        for committee in sorted(seat_rationales):
            people = seat_rationales[committee]
            for person in sorted(people):
                writer.writerow([committee, person, people[person]])
        writer.writerow([])
        writer.writerow(["committee", "size", "min_size", "max_size", "missing_competencies"])
        for committee in sorted(result.committee_health):
            metrics = result.committee_health[committee]
            missing = ";".join(sorted(metrics.get("missing_competencies", [])))
            writer.writerow(
                [
                    committee,
                    metrics.get("size"),
                    metrics.get("min_size"),
                    metrics.get("max_size"),
                    missing,
                ]
            )

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from ..models.committee import Committee
from ..models.person import Person


@dataclass
class AllocationResult:
    """Final allocation package."""

    committees: List[Committee]
    rationales: Dict[Tuple[str, str], str] = field(default_factory=dict)
    committee_health: Dict[str, Dict[str, object]] = field(default_factory=dict)


class Allocator:
    """Allocate people to committees using simple heuristics.

    Inputs are sorted by name before processing so that operations remain
    deterministic without relying on randomness. The algorithm proceeds in
    four stages:
    1. feasibility pre-check
    2. greedy seat filling
    3. local improvements
    4. final packaging
    """

    @staticmethod
    def precheck_feasibility(committees: List[Committee], people: List[Person]) -> None:
        """Validate that each committee can be feasibly populated."""
        committees_sorted = sorted(committees, key=lambda c: c.name)
        people_sorted = sorted(people, key=lambda p: p.name)
        for committee in committees_sorted:
            available = [
                p
                for p in people_sorted
                if p.is_available() and p not in committee.exclusions
            ]
            if len(available) < committee.min_size:
                raise ValueError(
                    f"Not enough available people for committee {committee.name}"
                )
            for comp in sorted(committee.required_competencies):
                if not any(p.has_competency(comp) for p in available):
                    raise ValueError(
                        f"No available person with competency {comp} for {committee.name}"
                    )

    @staticmethod
    def greedy_fill(
        committees: List[Committee],
        people: List[Person],
        rationales: Dict[Tuple[str, str], str],
    ) -> None:
        """Greedily assign people to committees to satisfy minimum sizes and competencies."""
        committees_sorted = sorted(committees, key=lambda c: c.name)
        people_sorted = sorted(people, key=lambda p: p.name)
        for committee in committees_sorted:
            available = [
                p
                for p in people_sorted
                if p.is_available() and p not in committee.exclusions
            ]
            # Fill required competencies first
            for comp in sorted(committee.required_competencies):
                if committee.needs_competency(comp):
                    for person in available:
                        if person.has_competency(comp):
                            committee.add_member(person)
                            rationales[(committee.name, person.name)] = (
                                f"Provides required competency {comp}"
                            )
                            available.remove(person)
                            break
            # Fill remaining seats to reach minimum size
            for person in list(available):
                if not committee.has_openings():
                    break
                if len(committee.members) >= committee.min_size:
                    break
                committee.add_member(person)
                rationales[(committee.name, person.name)] = "Fills remaining slot"
                available.remove(person)

    @staticmethod
    def local_improvements(
        committees: List[Committee],
        people: List[Person],
        rationales: Dict[Tuple[str, str], str],
    ) -> None:
        """Attempt to cover unmet competencies with remaining people."""
        committees_sorted = sorted(committees, key=lambda c: c.name)
        people_sorted = sorted(people, key=lambda p: p.name)
        for committee in committees_sorted:
            for comp in sorted(committee.required_competencies):
                if committee.needs_competency(comp) and committee.has_openings():
                    for person in people_sorted:
                        if (
                            person.is_available()
                            and person not in committee.exclusions
                            and person.has_competency(comp)
                        ):
                            committee.add_member(person)
                            rationales[(committee.name, person.name)] = (
                                f"Added to improve coverage of {comp}"
                            )
                            break

    @staticmethod
    def package_result(
        committees: List[Committee], rationales: Dict[Tuple[str, str], str]
    ) -> AllocationResult:
        """Create final allocation package with health summaries."""
        health: Dict[str, Dict[str, object]] = {}
        for committee in sorted(committees, key=lambda c: c.name):
            missing = sorted(
                [
                    comp
                    for comp in committee.required_competencies
                    if committee.needs_competency(comp)
                ]
            )
            health[committee.name] = {
                "size": len(committee.members),
                "min_size": committee.min_size,
                "max_size": committee.max_size,
                "missing_competencies": missing,
            }
        return AllocationResult(
            committees=committees, rationales=dict(rationales), committee_health=health
        )

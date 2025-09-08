from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set

from .person import Person


@dataclass
class Committee:
    """Represents a committee with membership requirements."""

    name: str
    min_size: int
    max_size: int
    required_competencies: Set[str] = field(default_factory=set)
    exclusions: Set[Person] = field(default_factory=set)
    diversity_targets: Dict[str, int] = field(default_factory=dict)
    members: Set[Person] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.min_size < 0 or self.max_size < 0:
            raise ValueError("Committee sizes must be non-negative")
        if self.max_size < self.min_size:
            raise ValueError("max_size cannot be less than min_size")

    def has_openings(self) -> bool:
        """Return True if the committee can accept additional members."""
        return len(self.members) < self.max_size

    def add_member(self, person: Person) -> None:
        if person in self.exclusions:
            raise ValueError(f"{person.name} is excluded from this committee")
        if not self.has_openings():
            raise ValueError("Committee is already at maximum size")
        if person in self.members:
            raise ValueError(f"{person.name} is already a member")
        if not person.is_available():
            raise ValueError(f"{person.name} is not available")
        self.members.add(person)
        person.assignments.add(self.name)

    def current_coverage(self) -> Set[str]:
        """Return the set of competencies covered by current members."""
        coverage: Set[str] = set()
        for member in self.members:
            coverage.update(member.competencies)
        return coverage

    def needs_competency(self, competency: str) -> bool:
        """Return True if the committee lacks a required competency."""
        return (
            competency in self.required_competencies
            and competency not in self.current_coverage()
        )

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Set


@dataclass(eq=False)
class Person:
    """Represents an individual available for committee service."""

    name: str
    service_cap: int = 0
    age: int = 0
    sex: str = ""
    family_branch: str = ""
    competencies: Set[str] = field(default_factory=set)
    interests: Set[str] = field(default_factory=set)
    assignments: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.service_cap < 0:
            raise ValueError("service_cap must be non-negative")
        if self.age < 0:
            raise ValueError("age must be non-negative")
        self.sex = self.sex.strip().lower()
        self.family_branch = self.family_branch.strip().lower()

    def workload(self) -> int:
        """Return the number of committees this person currently serves on."""
        return len(self.assignments)

    def has_competency(self, competency: str) -> bool:
        """Return whether the person possesses a given competency."""
        return competency in self.competencies

    def is_available(self) -> bool:
        """Return True if the person can accept additional assignments."""
        return self.workload() < self.service_cap

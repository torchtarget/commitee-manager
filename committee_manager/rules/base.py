from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Sequence, Tuple

from committee_manager.models.committee import Committee
from committee_manager.models.person import Person


@dataclass
class Rule(ABC):
    """Base class for all business rules."""

    name: str
    priority: int
    applies_to: Sequence[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    explain_exclude: str | None = None
    explain_score: str | None = None

    def applies(self, committee: Committee) -> bool:
        """Return ``True`` if this rule applies to the given committee."""
        return not self.applies_to or committee.name in self.applies_to

    @abstractmethod
    def evaluate(
        self, person: Person, committee: Committee
    ) -> Tuple[Any, str]:
        """Evaluate the rule for a person/committee pair."""


@dataclass
class HardRule(Rule):
    """Rule that determines eligibility."""

    def evaluate(self, person: Person, committee: Committee) -> Tuple[bool, str]:
        eligible = self.check(person, committee)
        rationale = ""
        if not eligible:
            template = (
                self.explain_exclude
                or f"{person.name} excluded by {self.name}"
            )
            rationale = template.format(
                person=person, committee=committee, params=self.params
            )
        return eligible, rationale

    @abstractmethod
    def check(self, person: Person, committee: Committee) -> bool:
        """Return ``True`` if the person is eligible for the committee."""


@dataclass
class SoftRule(Rule):
    """Rule that contributes a score."""

    weight: float = 1.0

    def evaluate(self, person: Person, committee: Committee) -> Tuple[float, str]:
        base = self.score(person, committee)
        score = base * self.weight
        template = self.explain_score or f"{self.name} score {score:.2f}"
        rationale = template.format(
            person=person,
            committee=committee,
            score=score,
            params=self.params,
        )
        return score, rationale

    @abstractmethod
    def score(self, person: Person, committee: Committee) -> float:
        """Return a base score for the person/committee pair."""

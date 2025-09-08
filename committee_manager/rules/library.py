from __future__ import annotations

from dataclasses import dataclass

from committee_manager.models.committee import Committee
from committee_manager.models.person import Person

from .base import HardRule, SoftRule


@dataclass
class ServiceCapRule(HardRule):
    """Disallow assignments beyond a person's service cap."""

    slug = "service_cap"

    def check(self, person: Person, committee: Committee) -> bool:
        return person.is_available()


@dataclass
class HasCompetencyRule(SoftRule):
    """Award points if the person possesses a given competency."""

    slug = "has_competency"

    def score(self, person: Person, committee: Committee) -> float:
        competency = self.params.get("competency")
        if competency and person.has_competency(competency):
            return 1.0
        return 0.0

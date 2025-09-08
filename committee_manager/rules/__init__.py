"""Business rules for committee_manager."""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Type

from .base import HardRule, Rule, SoftRule
from .library import HasCompetencyRule, ServiceCapRule

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from committee_manager.io.rule_loader import RuleDefinition


RULE_REGISTRY: Dict[str, Type[Rule]] = {
    ServiceCapRule.slug: ServiceCapRule,
    HasCompetencyRule.slug: HasCompetencyRule,
}


def create_rule(defn: "RuleDefinition") -> Rule:
    """Instantiate a concrete :class:`Rule` from a :class:`RuleDefinition`."""
    cls = RULE_REGISTRY.get(defn.name)
    if cls is None:
        raise KeyError(f"Unknown rule: {defn.name}")

    kwargs = {
        "name": defn.name,
        "priority": defn.priority,
        "applies_to": defn.applies_to,
        "params": defn.params,
        "explain_exclude": defn.explain_exclude,
        "explain_score": defn.explain_score,
    }
    if issubclass(cls, SoftRule):
        kwargs["weight"] = defn.weight if defn.weight is not None else 1.0
    rule = cls(**kwargs)  # type: ignore[arg-type]
    return rule


def build_rules(definitions: List["RuleDefinition"]) -> List[Rule]:
    """Build and sort rule objects from definitions."""
    rules = [create_rule(d) for d in definitions]
    return sorted(rules, key=lambda r: r.priority)


__all__ = [
    "Rule",
    "HardRule",
    "SoftRule",
    "ServiceCapRule",
    "HasCompetencyRule",
    "create_rule",
    "build_rules",
]

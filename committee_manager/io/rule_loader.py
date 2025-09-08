"""Load and validate rule definitions from YAML files."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

import yaml


@dataclass
class RuleDefinition:
    """Data representation of a rule definition."""

    name: str
    kind: Literal["hard", "soft"]
    priority: int
    applies_to: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    weight: Optional[float] = None
    explain_exclude: Optional[str] = None
    explain_score: Optional[str] = None


def _validate_rule(index: int, data: Dict[str, Any]) -> RuleDefinition:
    required = {"name", "kind", "priority", "params"}
    missing = required - data.keys()
    if missing:
        raise ValueError(
            f"Rule {index}: missing required fields: {', '.join(sorted(missing))}"
        )

    name = data["name"]
    kind = data["kind"]
    if kind not in {"hard", "soft"}:
        raise ValueError(f"Rule {index}: kind must be 'hard' or 'soft'")

    priority = data["priority"]
    if not isinstance(priority, int):
        raise ValueError(f"Rule {index}: priority must be an integer")

    params = data["params"]
    if not isinstance(params, dict):
        raise ValueError(f"Rule {index}: params must be a mapping")

    applies_to = data.get("applies_to") or []
    if not isinstance(applies_to, list):
        raise ValueError(f"Rule {index}: applies_to must be a list if provided")

    weight = data.get("weight")
    if kind == "soft" and weight is None:
        raise ValueError(f"Rule {index}: soft rules require a weight")
    if weight is not None and not isinstance(weight, (int, float)):
        raise ValueError(f"Rule {index}: weight must be a number if provided")

    return RuleDefinition(
        name=name,
        kind=kind,
        priority=priority,
        applies_to=applies_to,
        params=params,
        weight=float(weight) if weight is not None else None,
        explain_exclude=data.get("explain_exclude"),
        explain_score=data.get("explain_score"),
    )


def load_rules(path: str) -> List[RuleDefinition]:
    """Parse a YAML file into :class:`RuleDefinition` objects."""
    with open(path, "r", encoding="utf8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, list):
        raise ValueError("Rule file must contain a list of rule definitions")

    rules: List[RuleDefinition] = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Rule {idx}: expected mapping but found {type(item).__name__}"
            )
        rules.append(_validate_rule(idx, item))

    return rules

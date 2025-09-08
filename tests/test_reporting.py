import csv
import sys
from pathlib import Path

import yaml

sys.path.append(str(Path(__file__).resolve().parents[1]))

from committee_manager.engine.allocator import AllocationResult
from committee_manager.models.person import Person
from committee_manager.models.committee import Committee
from committee_manager.rules.base import HardRule, SoftRule
from committee_manager.reporting import export_yaml, export_csv

Person.__hash__ = object.__hash__


class CapacityRule(HardRule):
    def check(self, person: Person, committee: Committee) -> bool:  # pragma: no cover - simple pass-through
        return person.is_available()


class CompetencyRule(SoftRule):
    def score(self, person: Person, committee: Committee) -> float:  # pragma: no cover - simple pass-through
        return 1.0 if self.params["competency"] in person.competencies else 0.0


def test_export_yaml_and_csv(tmp_path):
    alice = Person(name="Alice", service_cap=2, competencies={"finance"})
    bob = Person(name="Bob", service_cap=1)
    bob.assignments.add("Existing")  # at capacity

    committee = Committee(name="Finance", min_size=1, max_size=5)
    committee.add_member(alice)

    hard = CapacityRule(name="service_cap", priority=1, explain_exclude="{person.name} is at capacity")
    soft = CompetencyRule(
        name="has_competency",
        priority=2,
        weight=1.5,
        params={"competency": "finance"},
        explain_score="{person.name} adds {params[competency]} skill",
    )

    _, exclude_rationale = hard.evaluate(bob, committee)
    _, include_rationale = soft.evaluate(alice, committee)

    result = AllocationResult(
        committees=[committee],
        rationales={
            (committee.name, alice.name): include_rationale,
            (committee.name, bob.name): exclude_rationale,
        },
        committee_health={
            committee.name: {
                "size": 1,
                "min_size": 1,
                "max_size": 5,
                "missing_competencies": [],
            }
        },
    )

    alloc_yaml = tmp_path / "alloc.yaml"
    rat_yaml = tmp_path / "rationale.yaml"
    export_yaml(result, str(alloc_yaml), str(rat_yaml))

    allocations = yaml.safe_load(alloc_yaml.read_text())
    assert allocations == {"Finance": ["Alice"]}

    rationale_data = yaml.safe_load(rat_yaml.read_text())
    assert rationale_data["seats"]["Finance"]["Alice"] == include_rationale
    assert rationale_data["seats"]["Finance"]["Bob"] == exclude_rationale
    assert rationale_data["committee_health"]["Finance"]["size"] == 1

    alloc_csv = tmp_path / "alloc.csv"
    rat_csv = tmp_path / "rationale.csv"
    export_csv(result, str(alloc_csv), str(rat_csv))

    with open(alloc_csv, newline="", encoding="utf8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"committee": "Finance", "person": "Alice"}]

    with open(rat_csv, newline="", encoding="utf8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["committee", "person", "rationale"]
    assert ["Finance", "Alice", include_rationale] in rows
    assert ["Finance", "Bob", exclude_rationale] in rows
    header_idx = rows.index(["committee", "size", "min_size", "max_size", "missing_competencies"])
    assert rows[header_idx + 1][:4] == ["Finance", "1", "1", "5"]

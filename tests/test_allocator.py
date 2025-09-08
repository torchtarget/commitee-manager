import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from committee_manager.engine.allocator import Allocator
from committee_manager.models.person import Person
from committee_manager.models.committee import Committee

# Ensure hashability for set operations
Person.__hash__ = object.__hash__


def test_precheck_feasibility_errors():
    alice = Person(name="Alice", service_cap=0)
    committee = Committee(name="Finance", min_size=1, max_size=1)
    with pytest.raises(ValueError):
        Allocator.precheck_feasibility([committee], [alice])

    bob = Person(name="Bob", service_cap=1)
    committee2 = Committee(
        name="Audit", min_size=1, max_size=1, required_competencies={"finance"}
    )
    with pytest.raises(ValueError):
        Allocator.precheck_feasibility([committee2], [bob])


def test_allocation_flow_and_packaging():
    alice = Person(name="Alice", service_cap=1, competencies={"finance"})
    bob = Person(name="Bob", service_cap=1)
    committee = Committee(
        name="Finance", min_size=2, max_size=2, required_competencies={"finance"}
    )

    committees = [committee]
    people = [alice, bob]
    rationales = {}

    Allocator.precheck_feasibility(committees, people)
    Allocator.greedy_fill(committees, people, rationales)
    Allocator.local_improvements(committees, people, rationales)
    result = Allocator.package_result(committees, rationales)

    assert committee.members == {alice, bob}
    assert result.committee_health["Finance"]["missing_competencies"] == []
    assert result.committee_health["Finance"]["size"] == 2
    assert (
        rationales[(committee.name, alice.name)]
        == "Provides required competency finance"
    )
    assert rationales[(committee.name, bob.name)] == "Fills remaining slot"


def test_local_improvements_adds_skill():
    committee = Committee(
        name="Finance", min_size=0, max_size=1, required_competencies={"finance"}
    )
    alice = Person(name="Alice", service_cap=1, competencies={"finance"})
    rationales = {}
    Allocator.local_improvements([committee], [alice], rationales)
    assert alice in committee.members
    assert (
        rationales[(committee.name, alice.name)]
        == "Added to improve coverage of finance"
    )

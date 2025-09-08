import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from committee_manager.models.person import Person
from committee_manager.models.committee import Committee


def test_person_service_cap_validation():
    with pytest.raises(ValueError):
        Person(name="Alice", service_cap=-1)


def test_committee_size_validation():
    with pytest.raises(ValueError):
        Committee(name="Test", min_size=2, max_size=1)


def test_committee_add_member_validations():
    alice = Person(name="Alice", service_cap=1)
    bob = Person(name="Bob", service_cap=0)
    committee = Committee(name="Finance", min_size=0, max_size=1, exclusions={alice})

    # Excluded member
    with pytest.raises(ValueError):
        committee.add_member(alice)

    committee.exclusions.clear()

    # Person at capacity
    with pytest.raises(ValueError):
        committee.add_member(bob)

    # Valid addition
    committee.add_member(alice)

    # No remaining openings
    with pytest.raises(ValueError):
        committee.add_member(Person(name="Carol", service_cap=1))


def test_committee_add_member_without_hash_patch():
    """Regression test ensuring Person is hashable by default."""
    alice = Person(name="Alice", service_cap=1)
    committee = Committee(name="Finance", min_size=0, max_size=1)
    committee.add_member(alice)
    assert committee.members == {alice}
    assert alice.assignments == {"Finance"}

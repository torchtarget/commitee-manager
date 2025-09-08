from __future__ import annotations

import argparse
import os
from typing import Dict, List

import yaml

from ..engine.allocator import Allocator
from ..io.committee_loader import load_committees
from ..io.people_loader import load_people
from ..io.rule_loader import load_rule_objects
from ..reporting.rationale import export_csv, export_yaml
from ..rules import SoftRule


# ---------------------------------------------------------------------------
# Scenario utilities
# ---------------------------------------------------------------------------

def _load_scenario(path: str | None) -> Dict:
    """Load a scenario configuration from ``path`` if it exists."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def _save_scenario(path: str, data: Dict) -> None:
    """Persist ``data`` to ``path`` as YAML."""
    with open(path, "w", encoding="utf8") as handle:
        yaml.safe_dump(data, handle, sort_keys=True)


def _apply_locks(committees: Dict[str, object], people: Dict[str, object], locks: Dict[str, List[str]]) -> None:
    """Apply locked members to committees prior to allocation."""
    for committee_name, members in locks.items():
        committee = committees.get(committee_name)
        if committee is None:
            raise ValueError(f"Unknown committee in locks: {committee_name}")
        for person_name in members:
            person = people.get(person_name)
            if person is None:
                raise ValueError(f"Unknown person in locks: {person_name}")
            if person not in committee.members:
                committee.add_member(person)


def _apply_weights(rules: List, weights: Dict[str, float]) -> None:
    """Override weights for soft rules using the scenario data."""
    for rule in rules:
        if isinstance(rule, SoftRule) and rule.name in weights:
            rule.weight = float(weights[rule.name])


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def cmd_allocate(args: argparse.Namespace) -> None:
    people = load_people(args.people)
    committees = load_committees(args.committees, people)

    rules = []
    if args.rules:
        rules = load_rule_objects(args.rules)

    scenario = _load_scenario(args.scenario)
    _apply_locks(committees, people, scenario.get("locks", {}))
    _apply_weights(rules, scenario.get("weights", {}))

    committees_list = list(committees.values())
    people_list = list(people.values())
    rationales = {}

    Allocator.precheck_feasibility(committees_list, people_list)
    Allocator.greedy_fill(committees_list, people_list, rationales)
    Allocator.local_improvements(committees_list, people_list, rationales)
    result = Allocator.package_result(committees_list, rationales)

    os.makedirs(args.output, exist_ok=True)
    if args.format == "csv":
        allocation_file = os.path.join(args.output, "allocation.csv")
        rationale_file = os.path.join(args.output, "rationale.csv")
        export_csv(result, allocation_file, rationale_file)
    else:
        allocation_file = os.path.join(args.output, "allocation.yaml")
        rationale_file = os.path.join(args.output, "rationale.yaml")
        export_yaml(result, allocation_file, rationale_file)

    print(f"Wrote allocation to {allocation_file} and rationale to {rationale_file}")


def cmd_lock_member(args: argparse.Namespace) -> None:
    scenario = _load_scenario(args.scenario)
    locks = scenario.setdefault("locks", {})
    members = locks.setdefault(args.committee, [])
    if args.person not in members:
        members.append(args.person)
    _save_scenario(args.scenario, scenario)


def cmd_set_weight(args: argparse.Namespace) -> None:
    scenario = _load_scenario(args.scenario)
    weights = scenario.setdefault("weights", {})
    weights[args.rule] = float(args.weight)
    _save_scenario(args.scenario, scenario)


def cmd_compare(args: argparse.Namespace) -> None:
    def _load_alloc(directory: str) -> Dict[str, List[str]]:
        path = os.path.join(directory, "allocation.yaml")
        with open(path, "r", encoding="utf8") as handle:
            return yaml.safe_load(handle) or {}

    alloc1 = _load_alloc(args.dir1)
    alloc2 = _load_alloc(args.dir2)

    committees = sorted(set(alloc1) | set(alloc2))
    for committee in committees:
        members1 = set(alloc1.get(committee, []))
        members2 = set(alloc2.get(committee, []))
        added = sorted(members2 - members1)
        removed = sorted(members1 - members2)
        if added or removed:
            print(f"{committee}:")
            if added:
                print(f"  + {'; '.join(added)}")
            if removed:
                print(f"  - {'; '.join(removed)}")


# ---------------------------------------------------------------------------
# Argument parser setup
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="committee-manager")
    sub = parser.add_subparsers(dest="command", required=True)

    # allocate
    p_alloc = sub.add_parser("allocate", help="Run allocation")
    p_alloc.add_argument("--people", required=True, help="People CSV path")
    p_alloc.add_argument("--committees", required=True, help="Committees CSV path")
    p_alloc.add_argument("--rules", help="Rules YAML path")
    p_alloc.add_argument("--scenario", help="Scenario YAML path")
    p_alloc.add_argument("--output", required=True, help="Output directory")
    p_alloc.add_argument(
        "--format",
        choices=["yaml", "csv"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    p_alloc.set_defaults(func=cmd_allocate)

    # lock-member
    p_lock = sub.add_parser("lock-member", help="Lock a person to a committee")
    p_lock.add_argument("scenario", help="Scenario YAML path")
    p_lock.add_argument("committee", help="Committee name")
    p_lock.add_argument("person", help="Person name")
    p_lock.set_defaults(func=cmd_lock_member)

    # set-weight
    p_weight = sub.add_parser("set-weight", help="Override a rule weight in the scenario")
    p_weight.add_argument("scenario", help="Scenario YAML path")
    p_weight.add_argument("rule", help="Rule name")
    p_weight.add_argument("weight", type=float, help="New weight value")
    p_weight.set_defaults(func=cmd_set_weight)

    # compare
    p_compare = sub.add_parser("compare", help="Compare two allocation directories")
    p_compare.add_argument("dir1", help="First allocation directory")
    p_compare.add_argument("dir2", help="Second allocation directory")
    p_compare.set_defaults(func=cmd_compare)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from committee_manager.io.rule_loader import load_rules


def test_load_rules_valid(tmp_path):
    rule_file = tmp_path / "rules.yaml"
    rule_file.write_text(
        """
- name: service_cap
  kind: hard
  priority: 1
  params: {}
""",
        encoding="utf8",
    )
    rules = load_rules(str(rule_file))
    assert len(rules) == 1
    rule = rules[0]
    assert rule.name == "service_cap"
    assert rule.kind == "hard"
    assert rule.priority == 1
    assert rule.params == {}


def test_load_rules_validation_errors(tmp_path):
    rule_file = tmp_path / "bad_rules.yaml"
    rule_file.write_text(
        """
- name: missing_weight
  kind: soft
  priority: 1
  params: {}
""",
        encoding="utf8",
    )
    with pytest.raises(ValueError):
        load_rules(str(rule_file))

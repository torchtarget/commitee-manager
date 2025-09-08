import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from committee_manager.io import load_rule_objects
from committee_manager.models.committee import Committee
from committee_manager.models.person import Person
from committee_manager.rules import HardRule, SoftRule


def test_rule_evaluation(tmp_path):
    rule_file = tmp_path / "rules.yaml"
    rule_file.write_text(
        """
- name: service_cap
  kind: hard
  priority: 1
  params: {}
  explain_exclude: "{person.name} is at capacity"
- name: has_competency
  kind: soft
  priority: 2
  weight: 1.5
  params:
    competency: finance
  explain_score: "{person.name} adds {params[competency]} skill"
""",
        encoding="utf8",
    )

    rules = load_rule_objects(str(rule_file))
    assert len(rules) == 2
    assert [r.priority for r in rules] == [1, 2]

    person = Person(name="Alice", service_cap=1, competencies={"finance"})
    committee = Committee(name="Finance", min_size=1, max_size=5)

    person.assignments.add("Existing")
    hard = next(r for r in rules if isinstance(r, HardRule))
    eligible, rationale = hard.evaluate(person, committee)
    assert not eligible
    assert "capacity" in rationale

    soft = next(r for r in rules if isinstance(r, SoftRule))
    score, rationale = soft.evaluate(person, committee)
    assert score == 1.5
    assert "finance" in rationale

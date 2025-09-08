"""Minimal Flask application exposing the allocator via a web form."""
from __future__ import annotations

import csv
import os
from io import StringIO
from pathlib import Path
from typing import Dict, List

from flask import Flask, render_template_string, request

from ..engine.allocator import Allocator
from ..io.committee_loader import load_committees
from ..io.people_loader import load_people
from ..io.rule_loader import load_rule_objects

app = Flask(__name__)

INPUT_DIR = Path(__file__).resolve().parents[2] / "inputs"


def _ensure_inputs_populated() -> None:
    """Create inputs dir and populate with examples if empty."""
    example_dir = Path(__file__).resolve().parents[2] / "examples"
    INPUT_DIR.mkdir(exist_ok=True)
    if not any(INPUT_DIR.iterdir()) and example_dir.exists():
        for name in example_dir.iterdir():
            if name.is_file():
                (INPUT_DIR / name.name).write_text(name.read_text(encoding="utf8"), encoding="utf8")

EDIT_TEMPLATE = """
<!doctype html>
<title>Edit Inputs</title>
<style>
  table { border-collapse: collapse; }
  th, td { padding: 4px; }
  input { width: 100%; box-sizing: border-box; }
</style>
<form method=post onsubmit="prepareData()">
  <input type=hidden name="people_path" value="{{ people_path }}">
  <input type=hidden name="committees_path" value="{{ committees_path }}">
  <input type=hidden name="rules_path" value="{{ rules_path }}">

  <h1>Edit People</h1>
  <table id="people_table" border="1">
    <thead>
      <tr>
        {% for head in people_header %}<th>{{ head }}</th>{% endfor %}
      </tr>
    </thead>
    <tbody>
      {% for row in people_rows %}
      <tr>
        {% for cell in row %}
        <td><input type="text" value="{{ cell }}"></td>
        {% endfor %}
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <button type="button" onclick="addRow('people_table')">Add Row</button>

  <h1>Edit Committees</h1>
  <table id="committees_table" border="1">
    <thead>
      <tr>
        {% for head in committees_header %}<th>{{ head }}</th>{% endfor %}
      </tr>
    </thead>
    <tbody>
      {% for row in committees_rows %}
      <tr>
        {% for cell in row %}
        <td><input type="text" value="{{ cell }}"></td>
        {% endfor %}
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <button type="button" onclick="addRow('committees_table')">Add Row</button>

  <input type=hidden name="people_content" id="people_content">
  <input type=hidden name="committees_content" id="committees_content">
  <p><input type=submit value="Allocate"></p>
</form>

<script>
function addRow(id) {
  const table = document.getElementById(id);
  const cols = table.tHead.rows[0].cells.length;
  const row = table.tBodies[0].insertRow();
  for (let i = 0; i < cols; i++) {
    const cell = row.insertCell();
    cell.innerHTML = '<input type="text">';
  }
}

function tableToCSV(id) {
  const table = document.getElementById(id);
  const rows = Array.from(table.rows);
  const lines = [];
  for (const r of rows) {
    const cells = Array.from(r.cells).map(c => {
      const input = c.querySelector('input');
      return input ? input.value : c.textContent;
    });
    if (r.rowIndex === 0 || cells.some(v => v.trim() !== '')) {
      lines.push(cells.join(','));
    }
  }
  return lines.join('\n');
}

function prepareData() {
  document.getElementById('people_content').value = tableToCSV('people_table');
  document.getElementById('committees_content').value = tableToCSV('committees_table');
}
</script>
"""

RESULT_TEMPLATE = """
<!doctype html>
<title>Allocation Result</title>
<h1>Allocation</h1>
<table border="1">
  <tr><th>Committee</th><th>Member</th><th>Rationale</th></tr>
  {% for committee in result.committees %}
    {% for member in committee.members %}
      <tr>
        <td>{{ committee.name }}</td>
        <td>{{ member.name }}</td>
        <td>{{ rationales.get((committee.name, member.name), '') }}</td>
      </tr>
    {% endfor %}
  {% endfor %}
</table>

<h1>Committee Health</h1>
<table border="1">
  <tr><th>Committee</th><th>Size</th><th>Min</th><th>Max</th><th>Missing Competencies</th></tr>
  {% for name, health in result.committee_health.items() %}
    <tr>
      <td>{{ name }}</td>
      <td>{{ health['size'] }}</td>
      <td>{{ health['min_size'] }}</td>
      <td>{{ health['max_size'] }}</td>
      <td>{{ ', '.join(health['missing_competencies']) }}</td>
    </tr>
  {% endfor %}
</table>

<p><a href="/">Back</a></p>
"""


@app.route("/", methods=["GET", "POST"])
def allocate() -> str:
    """Render edit form or process allocation request."""
    _ensure_inputs_populated()

    if request.method == "POST" and "people_path" in request.form:
        people_path = request.form["people_path"]
        committees_path = request.form["committees_path"]
        rules_path = request.form.get("rules_path") or None

        people_content = request.form.get("people_content", "")
        committees_content = request.form.get("committees_content", "")
        with open(people_path, "w", encoding="utf8") as handle:
            handle.write(people_content.strip() + "\n")
        with open(committees_path, "w", encoding="utf8") as handle:
            handle.write(committees_content.strip() + "\n")

        people = load_people(people_path)
        committees = load_committees(committees_path, people)
        rules = load_rule_objects(rules_path) if rules_path else []

        committees_list: List = list(committees.values())
        people_list: List = list(people.values())
        rationales: Dict = {}

        Allocator.precheck_feasibility(committees_list, people_list)
        Allocator.greedy_fill(committees_list, people_list, rationales)
        Allocator.local_improvements(committees_list, people_list, rationales)
        result = Allocator.package_result(committees_list, rationales)

        return render_template_string(
            RESULT_TEMPLATE, result=result, rationales=rationales
        )

    people_path = INPUT_DIR / "people.csv"
    committees_path = INPUT_DIR / "committees.csv"
    rules_path = INPUT_DIR / "rules.yaml"
    people_text = people_path.read_text(encoding="utf8") if people_path.exists() else ""
    committees_text = (
        committees_path.read_text(encoding="utf8") if committees_path.exists() else ""
    )

    if people_text:
        people_data = list(csv.reader(StringIO(people_text)))
        people_header = people_data[0] if people_data else []
        people_rows = people_data[1:] if len(people_data) > 1 else []
    else:
        people_header = ["name", "service_cap", "competencies"]
        people_rows = [[]]
    if not people_rows or not people_rows[0]:
        people_rows = [["" for _ in people_header]]

    if committees_text:
        committee_data = list(csv.reader(StringIO(committees_text)))
        committees_header = committee_data[0] if committee_data else []
        committees_rows = committee_data[1:] if len(committee_data) > 1 else []
    else:
        committees_header = [
            "name",
            "min_size",
            "max_size",
            "required_competencies",
            "exclusions",
            "diversity_targets",
        ]
        committees_rows = [[]]
    if not committees_rows or not committees_rows[0]:
        committees_rows = [["" for _ in committees_header]]

    return render_template_string(
        EDIT_TEMPLATE,
        people_header=people_header,
        people_rows=people_rows,
        committees_header=committees_header,
        committees_rows=committees_rows,
        people_path=str(people_path),
        committees_path=str(committees_path),
        rules_path=str(rules_path) if rules_path.exists() else "",
    )


def create_app() -> Flask:
    """Return the Flask application instance."""
    return app


if __name__ == "__main__":
    # Bind to all interfaces to allow remote access when running the app directly.
    app.run(debug=True, host="0.0.0.0")

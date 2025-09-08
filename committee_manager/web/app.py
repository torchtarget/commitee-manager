"""Minimal Flask application exposing the allocator via a web form."""
from __future__ import annotations

import os
import tempfile
from typing import Dict, List

from flask import Flask, render_template_string, request

from ..engine.allocator import Allocator
from ..io.committee_loader import load_committees
from ..io.people_loader import load_people
from ..io.rule_loader import load_rule_objects
from ..reporting.rationale import export_yaml

app = Flask(__name__)

FORM_TEMPLATE = """
<!doctype html>
<title>Committee Manager</title>
<h1>Upload allocation inputs</h1>
<form method=post enctype=multipart/form-data>
  <label>People CSV: <input type=file name=people required></label><br>
  <label>Committees CSV: <input type=file name=committees required></label><br>
  <label>Rules YAML: <input type=file name=rules></label><br>
  <input type=submit value="Allocate">
</form>
"""

RESULT_TEMPLATE = """
<!doctype html>
<title>Allocation Result</title>
<h1>Allocation</h1>
<pre>{{ allocation }}</pre>
<h1>Rationale</h1>
<pre>{{ rationale }}</pre>
<p><a href="/">Back</a></p>
"""


@app.route("/", methods=["GET", "POST"])
def allocate() -> str:
    """Render upload form or process allocation request."""
    if request.method == "POST":
        people_file = request.files.get("people")
        committees_file = request.files.get("committees")
        rules_file = request.files.get("rules")
        if not people_file or not committees_file:
            return "People and committees files are required", 400

        with tempfile.TemporaryDirectory() as tmpdir:
            people_path = os.path.join(tmpdir, "people.csv")
            committees_path = os.path.join(tmpdir, "committees.csv")
            rules_path = os.path.join(tmpdir, "rules.yaml")
            people_file.save(people_path)
            committees_file.save(committees_path)
            if rules_file and rules_file.filename:
                rules_file.save(rules_path)
            else:
                rules_path = None

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

            allocation_file = os.path.join(tmpdir, "allocation.yaml")
            rationale_file = os.path.join(tmpdir, "rationale.yaml")
            export_yaml(result, allocation_file, rationale_file)

            with open(allocation_file, "r", encoding="utf8") as handle:
                allocation = handle.read()
            with open(rationale_file, "r", encoding="utf8") as handle:
                rationale = handle.read()

        return render_template_string(
            RESULT_TEMPLATE, allocation=allocation, rationale=rationale
        )

    return FORM_TEMPLATE


def create_app() -> Flask:
    """Return the Flask application instance."""
    return app


if __name__ == "__main__":
    # Bind to all interfaces to allow remote access when running the app directly.
    app.run(debug=True, host="0.0.0.0")

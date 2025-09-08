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
  <input type=submit value="Upload">
</form>
"""

EDIT_TEMPLATE = """
<!doctype html>
<title>Edit Inputs</title>
<h1>Edit People</h1>
<form method=post>
  <input type=hidden name="people_path" value="{{ people_path }}">
  <input type=hidden name="committees_path" value="{{ committees_path }}">
  <input type=hidden name="rules_path" value="{{ rules_path }}">
  <textarea name=people_content rows=10 cols=80>{{ people }}</textarea>
  <h1>Edit Committees</h1>
  <textarea name=committees_content rows=10 cols=80>{{ committees }}</textarea><br>
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
    """Render upload form, edit data, or process allocation request."""
    if request.method == "POST":
        # Allocation submission after editing
        if "people_path" in request.form:
            people_path = request.form["people_path"]
            committees_path = request.form["committees_path"]
            rules_path = request.form.get("rules_path") or None

            # Persist edited contents back to their files
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

            tmpdir = os.path.dirname(people_path)
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

        # Initial upload of files
        people_file = request.files.get("people")
        committees_file = request.files.get("committees")
        rules_file = request.files.get("rules")
        if not people_file or not committees_file:
            return "People and committees files are required", 400

        tmpdir = tempfile.mkdtemp()
        people_path = os.path.join(tmpdir, "people.csv")
        committees_path = os.path.join(tmpdir, "committees.csv")
        rules_path = os.path.join(tmpdir, "rules.yaml")
        people_file.save(people_path)
        committees_file.save(committees_path)
        if rules_file and rules_file.filename:
            rules_file.save(rules_path)
        else:
            rules_path = None

        with open(people_path, "r", encoding="utf8") as handle:
            people_text = handle.read()
        with open(committees_path, "r", encoding="utf8") as handle:
            committees_text = handle.read()

        return render_template_string(
            EDIT_TEMPLATE,
            people=people_text,
            committees=committees_text,
            people_path=people_path,
            committees_path=committees_path,
            rules_path=rules_path or "",
        )

    return FORM_TEMPLATE


def create_app() -> Flask:
    """Return the Flask application instance."""
    return app


if __name__ == "__main__":
    # Bind to all interfaces to allow remote access when running the app directly.
    app.run(debug=True, host="0.0.0.0")

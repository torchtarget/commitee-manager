from __future__ import annotations

from committee_manager.web import create_app


def test_web_allocation(tmp_path):
    app = create_app()
    client = app.test_client()

    # Ensure GET works
    resp = client.get("/")
    assert resp.status_code == 200

    people_path = tmp_path / "people.csv"
    committees_path = tmp_path / "committees.csv"
    rules_path = tmp_path / "rules.yaml"

    people_path.write_text(
        "name,service_cap,competencies\nAlice,2,finance;strategy\nBob,1,\n"
    )
    committees_path.write_text(
        "name,min_size,max_size,required_competencies\nFinance,1,2,finance\n"
    )
    rules_path.write_text(
        (
            "- name: has_competency\n  kind: soft\n  priority: 1\n  weight: 1\n  params:\n"
            "    competency: finance\n  explain_score: '{person.name} has finance competency'\n"
        )
    )

    data = {
        "people": (people_path.open("rb"), "people.csv"),
        "committees": (committees_path.open("rb"), "committees.csv"),
        "rules": (rules_path.open("rb"), "rules.yaml"),
    }
    resp = client.post("/", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert b"Finance" in resp.data
    assert b"Alice" in resp.data

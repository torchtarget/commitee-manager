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

    upload_data = {
        "people": (people_path.open("rb"), "people.csv"),
        "committees": (committees_path.open("rb"), "committees.csv"),
        "rules": (rules_path.open("rb"), "rules.yaml"),
    }
    resp = client.post("/", data=upload_data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert b"Edit People" in resp.data

    import re

    people_path_val = re.search(
        b'name="people_path" value="([^"]+)"', resp.data
    ).group(1).decode()
    committees_path_val = re.search(
        b'name="committees_path" value="([^"]+)"', resp.data
    ).group(1).decode()
    rules_path_val = re.search(
        b'name="rules_path" value="([^"]*)"', resp.data
    ).group(1).decode()

    people_content = (
        "name,service_cap,competencies\n"
        "Alice,2,finance;strategy\n"
        "Bob,1,\n"
        "Carol,1,finance\n"
    )
    committees_content = (
        "name,min_size,max_size,required_competencies\n"
        "Finance,1,2,finance\n"
    )

    resp = client.post(
        "/",
        data={
            "people_path": people_path_val,
            "committees_path": committees_path_val,
            "rules_path": rules_path_val,
            "people_content": people_content,
            "committees_content": committees_content,
        },
    )
    assert resp.status_code == 200
    assert b"Finance" in resp.data
    assert b"Alice" in resp.data

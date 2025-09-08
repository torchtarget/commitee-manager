"""Utilities for loading :class:`~committee_manager.models.person.Person` objects from CSV files."""
from __future__ import annotations

import csv
from typing import Dict

from ..models.person import Person


def load_people(path: str) -> Dict[str, Person]:
    """Load people from a CSV file.

    The CSV is expected to contain at least a ``name`` column. Optional columns
    are ``service_cap`` and ``competencies``. Competencies should be provided as
    a semicolon-delimited string.

    Parameters
    ----------
    path:
        Path to the CSV file.

    Returns
    -------
    dict[str, Person]
        Mapping of person name to :class:`Person` instances.

    Raises
    ------
    ValueError
        If required columns are missing or data is invalid.
    """

    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        required = {"name"}
        missing = required - set(fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        people: Dict[str, Person] = {}
        for lineno, row in enumerate(reader, start=2):
            name = row.get("name", "").strip()
            if not name:
                raise ValueError(f"Row {lineno}: 'name' is required")

            service_cap_raw = row.get("service_cap", "0").strip() or "0"
            try:
                service_cap = int(service_cap_raw)
            except ValueError as exc:
                raise ValueError(
                    f"Row {lineno}: service_cap must be an integer"
                ) from exc
            if service_cap < 0:
                raise ValueError(f"Row {lineno}: service_cap must be non-negative")

            comp_field = row.get("competencies", "").strip()
            competencies = {c.strip() for c in comp_field.split(";") if c.strip()}

            people[name] = Person(
                name=name, service_cap=service_cap, competencies=competencies
            )

    return people

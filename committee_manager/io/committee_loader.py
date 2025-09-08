"""Utilities for loading :class:`~committee_manager.models.committee.Committee` objects from CSV files."""
from __future__ import annotations

import csv
import json
from typing import Dict, Set

from ..models.committee import Committee
from ..models.person import Person


def load_committees(path: str, people: Dict[str, Person] | None = None) -> Dict[str, Committee]:
    """Load committees from a CSV file.

    The CSV must include ``name``, ``min_size`` and ``max_size`` columns. Optional
    columns are ``required_competencies``, ``exclusions`` and ``diversity_targets``.
    Competencies and exclusions should be semicolon-delimited strings. Diversity
    targets can either be a JSON object or a semicolon-separated list of
    ``key=value`` pairs.

    Parameters
    ----------
    path:
        Path to the CSV file.
    people:
        Optional mapping of person names to :class:`Person` instances. Required if
        the ``exclusions`` column is used.

    Returns
    -------
    dict[str, Committee]
        Mapping of committee name to :class:`Committee` instances.

    Raises
    ------
    ValueError
        If required columns are missing, referenced people are unknown or data is
        otherwise invalid.
    """

    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        required = {"name", "min_size", "max_size"}
        missing = required - set(fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        committees: Dict[str, Committee] = {}
        for lineno, row in enumerate(reader, start=2):
            name = row.get("name", "").strip()
            if not name:
                raise ValueError(f"Row {lineno}: 'name' is required")

            try:
                min_size = int(row.get("min_size", ""))
                max_size = int(row.get("max_size", ""))
            except ValueError as exc:
                raise ValueError(
                    f"Row {lineno}: min_size and max_size must be integers"
                ) from exc
            if min_size < 0 or max_size < 0:
                raise ValueError(f"Row {lineno}: sizes must be non-negative")
            if max_size < min_size:
                raise ValueError(
                    f"Row {lineno}: max_size cannot be less than min_size"
                )

            rc_field = row.get("required_competencies", "").strip()
            required_competencies = {c.strip() for c in rc_field.split(";") if c.strip()}

            exclusions_field = row.get("exclusions", "").strip()
            exclusions: Set[Person] = set()
            if exclusions_field:
                if people is None:
                    raise ValueError(
                        f"Row {lineno}: exclusions specified but no people mapping provided"
                    )
                for pname in exclusions_field.split(";"):
                    pname = pname.strip()
                    if not pname:
                        continue
                    person = people.get(pname)
                    if person is None:
                        raise ValueError(
                            f"Row {lineno}: exclusion '{pname}' not found in people list"
                        )
                    exclusions.add(person)

            div_field = row.get("diversity_targets", "").strip()
            diversity_targets: Dict[str, int] = {}
            if div_field:
                parsed = False
                # First try JSON
                try:
                    data = json.loads(div_field)
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if not isinstance(v, int):
                                raise ValueError
                        diversity_targets = data
                        parsed = True
                except (ValueError, json.JSONDecodeError):
                    pass
                if not parsed:
                    pairs = [p for p in div_field.split(";") if p.strip()]
                    for p in pairs:
                        if "=" not in p:
                            raise ValueError(
                                f"Row {lineno}: diversity_targets entry '{p}' missing '='"
                            )
                        k, v = p.split("=", 1)
                        k = k.strip()
                        try:
                            diversity_targets[k] = int(v)
                        except ValueError as exc:
                            raise ValueError(
                                f"Row {lineno}: diversity_targets value '{v}' for key '{k}' must be int"
                            ) from exc

            committees[name] = Committee(
                name=name,
                min_size=min_size,
                max_size=max_size,
                required_competencies=required_competencies,
                exclusions=exclusions,
                diversity_targets=diversity_targets,
            )

    return committees

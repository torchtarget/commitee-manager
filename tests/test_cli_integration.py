import sys
from pathlib import Path
import argparse

sys.path.append(str(Path(__file__).resolve().parents[1]))

from committee_manager.cli.main import cmd_allocate


def test_allocate_examples(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "out"
    args = argparse.Namespace(
        people=root / "examples/people.csv",
        committees=root / "examples/committees.csv",
        rules=root / "examples/rules.yaml",
        scenario=None,
        output=str(output_dir),
        format="yaml",
    )
    cmd_allocate(args)
    assert (output_dir / "allocation.yaml").exists()
    assert (output_dir / "rationale.yaml").exists()

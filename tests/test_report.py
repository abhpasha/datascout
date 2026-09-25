import json
from pathlib import Path

import pandas as pd
import pytest

from datascout import scan
from datascout.cli import main


@pytest.fixture
def messy_csv(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {"id": [1, 2, 2, 4], "email": ["a@x.com", "b@x.com", "b@x.com", "d@x.com"], "note": [None] * 4}
    )
    path = tmp_path / "messy.csv"
    df.to_csv(path, index=False)
    return path


def test_scan_file(messy_csv):
    report = scan(messy_csv)
    assert report.source == "messy.csv"
    assert report.summary["rows"] == 4
    assert 0 <= report.score < 100


@pytest.mark.parametrize("ext", [".html", ".md", ".json", ".txt"])
def test_save_formats(messy_csv, tmp_path, ext):
    out = scan(messy_csv).save(tmp_path / f"report{ext}")
    assert out.read_text().strip()


def test_json_is_valid(messy_csv):
    data = json.loads(scan(messy_csv).to_json())
    assert {"score", "issues", "summary"} <= data.keys()


def test_cli_fail_under(messy_csv):
    assert main([str(messy_csv), "--quiet", "--fail-under", "100"]) == 1
    assert main([str(messy_csv), "--quiet", "--fail-under", "0"]) == 0


def test_cli_missing_file():
    assert main(["does_not_exist.csv", "--quiet"]) == 2

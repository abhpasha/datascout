import numpy as np
import pandas as pd

from datascout.checks import (
    check_constant_columns,
    check_dates_stored_as_text,
    check_duplicate_rows,
    check_id_uniqueness,
    check_missing,
    check_numbers_stored_as_text,
    check_outliers,
    check_pii,
    check_whitespace_and_case,
    health_score,
    run_checks,
)


def test_clean_frame_has_no_issues():
    df = pd.DataFrame({"a": range(20), "b": [f"x{i}" for i in range(20)]})
    assert run_checks(df) == []
    assert health_score([]) == 100


def test_missing_severity_levels():
    df = pd.DataFrame({"empty": [None] * 10, "half": [1, None] * 5, "few": [1] * 9 + [None]})
    sev = {i.column: i.severity for i in check_missing(df)}
    assert sev == {"empty": "high", "half": "high", "few": "medium"}


def test_duplicate_rows():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    [issue] = check_duplicate_rows(df)
    assert issue.details["count"] == 1


def test_duplicate_ids_only_on_key_like_columns():
    df = pd.DataFrame({"order_id": [1, 2, 3, 4, 4], "qty": [1, 1, 1, 1, 1]})
    issues = check_id_uniqueness(df)
    assert [i.column for i in issues] == ["order_id"]


def test_constant_column():
    df = pd.DataFrame({"c": ["same"] * 5, "v": range(5)})
    assert [i.column for i in check_constant_columns(df)] == ["c"]


def test_outliers_detected():
    values = list(np.random.default_rng(0).normal(50, 5, 100)) + [5000]
    issues = check_outliers(pd.DataFrame({"x": values}))
    assert issues and issues[0].details["count"] == 1


def test_numbers_and_dates_as_text():
    df = pd.DataFrame({"price": ["$1,200", "$30", "$5"] * 4, "day": ["2024-01-02", "2024-02-03", "2024-03-04"] * 4})
    assert [i.column for i in check_numbers_stored_as_text(df)] == ["price"]
    assert [i.column for i in check_dates_stored_as_text(df)] == ["day"]


def test_whitespace_and_case():
    df = pd.DataFrame({"city": ["Toronto", "toronto", "Ottawa ", "Ottawa"]})
    kinds = {i.check for i in check_whitespace_and_case(df)}
    assert kinds == {"whitespace", "inconsistent_case"}


def test_pii_email():
    df = pd.DataFrame({"contact": ["a@b.com", "c@d.org", "e@f.io"]})
    assert check_pii(df)[0].column == "contact"


def test_skip():
    df = pd.DataFrame({"a": [1, 1], "b": [2, 2]})
    assert not any(i.check == "duplicate_rows" for i in run_checks(df, skip=["duplicate_rows"]))


def test_pii_phone_but_not_dates():
    phones = pd.DataFrame({"phone": ["+1 (416) 555-0199", "416-555-0123", "647.555.0101"]})
    dates = pd.DataFrame({"d": ["2024-01-01", "2024-02-01", "2024-03-01"]})
    assert check_pii(phones)[0].message.endswith("phone numbers")
    assert check_pii(dates) == []

"""Data quality checks. Each check takes a DataFrame and returns a list of Issues.

Adding a new check is one function plus one entry in ``ALL_CHECKS``.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Callable

import pandas as pd

SEVERITY_WEIGHT = {"high": 15, "medium": 6, "low": 2}

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
PHONE_RE = re.compile(r"^\+?[\d\s().-]{7,}$")
DATE_HINT_RE = re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}")


@dataclass
class Issue:
    check: str
    severity: str  # "high" | "medium" | "low"
    message: str
    column: str | None = None
    suggestion: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _text_columns(df: pd.DataFrame):
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
            non_null = s.dropna()
            if len(non_null):
                yield col, non_null.astype(str)


# ---------------------------------------------------------------- checks


def check_missing(df: pd.DataFrame, high: float = 50.0, medium: float = 10.0) -> list[Issue]:
    issues = []
    if not len(df):
        return issues
    for col in df.columns:
        pct = 100 * df[col].isna().mean()
        if pct == 0:
            continue
        if pct == 100:
            sev, msg = "high", "Column is completely empty"
            tip = "Drop the column or fix the upstream source."
        elif pct >= high:
            sev, msg = "high", f"{pct:.1f}% of values are missing"
            tip = "Consider dropping, or check why the source stops populating it."
        elif pct >= medium:
            sev, msg = "medium", f"{pct:.1f}% of values are missing"
            tip = "Decide on an imputation strategy or flag rows downstream."
        else:
            sev, msg = "low", f"{pct:.1f}% of values are missing"
            tip = "Usually fine; make sure downstream code handles nulls."
        issues.append(Issue("missing_values", sev, msg, str(col), tip, {"missing_pct": round(pct, 2)}))
    return issues


def check_duplicate_rows(df: pd.DataFrame) -> list[Issue]:
    n = int(df.duplicated().sum())
    if n == 0:
        return []
    pct = 100 * n / len(df)
    sev = "high" if pct >= 5 else "medium"
    return [
        Issue(
            "duplicate_rows",
            sev,
            f"{n:,} fully duplicated rows ({pct:.1f}%)",
            None,
            "Use df.drop_duplicates() or add a unique key constraint upstream.",
            {"count": n},
        )
    ]


def check_constant_columns(df: pd.DataFrame) -> list[Issue]:
    issues = []
    for col in df.columns:
        non_null = df[col].dropna()
        if len(non_null) and non_null.nunique() == 1:
            issues.append(
                Issue(
                    "constant_column",
                    "low",
                    f"Only one distinct value: '{non_null.iloc[0]}'",
                    str(col),
                    "Carries no information for modelling; consider dropping.",
                )
            )
    return issues


def check_outliers(df: pd.DataFrame, k: float = 3.0) -> list[Issue]:
    """Flag numeric columns with values outside k * IQR (default 3, i.e. extreme outliers)."""
    issues = []
    for col in df.select_dtypes("number").columns:
        s = df[col].dropna()
        if len(s) < 10 or pd.api.types.is_bool_dtype(s):
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        lo, hi = q1 - k * iqr, q3 + k * iqr
        mask = (s < lo) | (s > hi)
        n = int(mask.sum())
        if n:
            pct = 100 * n / len(s)
            examples = s[mask].head(3).tolist()
            issues.append(
                Issue(
                    "outliers",
                    "medium" if pct >= 1 else "low",
                    f"{n} extreme outlier(s) outside [{lo:,.2f}, {hi:,.2f}], e.g. {examples}",
                    str(col),
                    "Verify these are real values and not unit or entry errors.",
                    {"count": n, "lower": lo, "upper": hi},
                )
            )
    return issues


def check_numbers_stored_as_text(df: pd.DataFrame, threshold: float = 0.9) -> list[Issue]:
    issues = []
    for col, s in _text_columns(df):
        cleaned = s.str.replace(r"[,$€£%\s]", "", regex=True)
        parsed = pd.to_numeric(cleaned, errors="coerce")
        ratio = parsed.notna().mean()
        if ratio >= threshold:
            bad = s[parsed.isna()].head(3).tolist()
            detail = f"; non-numeric examples: {bad}" if bad else ""
            issues.append(
                Issue(
                    "numeric_as_text",
                    "medium",
                    f"{ratio:.0%} of values look numeric but column is stored as text{detail}",
                    str(col),
                    "Strip symbols and cast with pd.to_numeric(..., errors='coerce').",
                )
            )
    return issues


def check_dates_stored_as_text(df: pd.DataFrame, threshold: float = 0.9) -> list[Issue]:
    issues = []
    for col, s in _text_columns(df):
        if s.str.match(DATE_HINT_RE).mean() < threshold:
            continue
        parsed = pd.to_datetime(s, errors="coerce", format="mixed")
        if parsed.notna().mean() >= threshold:
            issues.append(
                Issue(
                    "date_as_text",
                    "low",
                    "Values look like dates but column is stored as text",
                    str(col),
                    "Parse with pd.to_datetime() so you can sort, filter and resample.",
                )
            )
    return issues


def check_whitespace_and_case(df: pd.DataFrame) -> list[Issue]:
    issues = []
    for col, s in _text_columns(df):
        padded = int((s != s.str.strip()).sum())
        if padded:
            issues.append(
                Issue(
                    "whitespace",
                    "low",
                    f"{padded} value(s) have leading/trailing spaces",
                    str(col),
                    "Apply .str.strip(); padded keys silently break joins.",
                    {"count": padded},
                )
            )
        stripped = s.str.strip()
        if stripped.nunique() <= 50:
            groups = stripped.groupby(stripped.str.lower()).nunique()
            clashes = groups[groups > 1]
            if len(clashes):
                variants = [
                    sorted(stripped[stripped.str.lower() == key].unique().tolist())
                    for key in clashes.index[:3]
                ]
                issues.append(
                    Issue(
                        "inconsistent_case",
                        "medium",
                        f"Same category written differently: {variants}",
                        str(col),
                        "Normalise with .str.strip().str.lower() or a mapping dict.",
                    )
                )
    return issues


def _looks_like_phone(s: pd.Series) -> pd.Series:
    digits = s.str.count(r"\d")
    return s.str.match(PHONE_RE) & ~s.str.match(DATE_HINT_RE) & digits.between(9, 15)


def check_pii(df: pd.DataFrame, threshold: float = 0.5) -> list[Issue]:
    issues = []
    for col, s in _text_columns(df):
        sample = s.head(1000)
        if sample.str.match(EMAIL_RE).mean() >= threshold:
            kind = "email addresses"
        elif _looks_like_phone(sample).mean() >= threshold:
            kind = "phone numbers"
        else:
            continue
        issues.append(
            Issue(
                "possible_pii",
                "medium",
                f"Column appears to contain {kind}",
                str(col),
                "Mask, hash or drop before sharing this dataset.",
            )
        )
    return issues


def check_id_uniqueness(df: pd.DataFrame) -> list[Issue]:
    issues = []
    for col in df.columns:
        name = str(col)
        is_key_name = name.lower() in {"id", "uuid", "guid"} or name.lower().endswith("_id") or name.endswith("Id")
        if not is_key_name:
            continue
        s = df[col].dropna()
        dupes = int(s.duplicated().sum())
        # Only flag when the column is *mostly* unique: a true key with a few collisions.
        if dupes and s.nunique() / max(len(s), 1) >= 0.8:
            issues.append(
                Issue(
                    "duplicate_ids",
                    "high",
                    f"Looks like a key column but has {dupes} duplicated value(s)",
                    str(col),
                    "Investigate before joining; duplicate keys multiply rows.",
                    {"count": dupes},
                )
            )
    return issues


ALL_CHECKS: dict[str, Callable[[pd.DataFrame], list[Issue]]] = {
    "missing_values": check_missing,
    "duplicate_rows": check_duplicate_rows,
    "duplicate_ids": check_id_uniqueness,
    "constant_column": check_constant_columns,
    "outliers": check_outliers,
    "numeric_as_text": check_numbers_stored_as_text,
    "date_as_text": check_dates_stored_as_text,
    "whitespace_and_case": check_whitespace_and_case,
    "possible_pii": check_pii,
}


def run_checks(df: pd.DataFrame, skip: list[str] | None = None) -> list[Issue]:
    """Run every registered check (minus any in ``skip``) and return issues sorted by severity."""
    skip = set(skip or [])
    issues: list[Issue] = []
    for name, fn in ALL_CHECKS.items():
        if name not in skip:
            issues.extend(fn(df))
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(issues, key=lambda i: (order[i.severity], i.column or ""))


def health_score(issues: list[Issue]) -> int:
    """A simple 0-100 score. Each issue deducts points by severity."""
    penalty = sum(SEVERITY_WEIGHT[i.severity] for i in issues)
    return max(0, 100 - penalty)

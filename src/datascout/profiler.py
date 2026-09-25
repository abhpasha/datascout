"""Column-level profiling: types, completeness, cardinality and basic stats."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _semantic_type(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    if pd.api.types.is_numeric_dtype(s):
        return "numeric"
    return "text"


def profile_column(s: pd.Series) -> dict[str, Any]:
    n = len(s)
    non_null = s.dropna()
    stype = _semantic_type(s)
    info: dict[str, Any] = {
        "name": str(s.name),
        "dtype": str(s.dtype),
        "type": stype,
        "missing": int(n - len(non_null)),
        "missing_pct": round(100 * (n - len(non_null)) / n, 2) if n else 0.0,
        "unique": int(non_null.nunique()),
        "unique_pct": round(100 * non_null.nunique() / len(non_null), 2) if len(non_null) else 0.0,
        "sample": [str(v) for v in non_null.drop_duplicates().head(3).tolist()],
    }

    if stype == "numeric" and len(non_null):
        values = non_null.astype(float)
        info["stats"] = {
            "min": float(values.min()),
            "max": float(values.max()),
            "mean": round(float(values.mean()), 4),
            "median": float(values.median()),
            "std": round(float(values.std()), 4) if len(values) > 1 else 0.0,
        }
    elif stype == "datetime" and len(non_null):
        info["stats"] = {"min": str(non_null.min()), "max": str(non_null.max())}
    elif stype == "text" and len(non_null):
        as_str = non_null.astype(str)
        lengths = as_str.str.len()
        top = as_str.value_counts().head(1)
        info["stats"] = {
            "min_length": int(lengths.min()),
            "max_length": int(lengths.max()),
            "most_common": str(top.index[0]),
            "most_common_count": int(top.iloc[0]),
        }
    return info


def profile(df: pd.DataFrame) -> dict[str, Any]:
    """Return a dataset-level summary plus a profile for every column."""
    return {
        "rows": len(df),
        "columns": int(df.shape[1]),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 3),
        "duplicate_rows": int(df.duplicated().sum()),
        "total_missing_cells": int(df.isna().sum().sum()),
        "column_profiles": [profile_column(df[c]) for c in df.columns],
    }

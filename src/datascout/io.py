"""Load tabular files into a pandas DataFrame based on extension."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SUPPORTED = {".csv", ".tsv", ".txt", ".parquet", ".pq", ".json", ".jsonl", ".xlsx", ".xls"}


def load(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read a CSV, TSV, Parquet, JSON/JSONL or Excel file into a DataFrame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED))}"
        )

    if ext in {".csv", ".txt"}:
        return pd.read_csv(path, **kwargs)
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t", **kwargs)
    if ext in {".parquet", ".pq"}:
        return pd.read_parquet(path, **kwargs)
    if ext == ".jsonl":
        return pd.read_json(path, lines=True, **kwargs)
    if ext == ".json":
        return pd.read_json(path, **kwargs)
    return pd.read_excel(path, **kwargs)

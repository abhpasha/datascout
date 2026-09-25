"""Generate examples/messy_customers.csv: a small dataset with realistic, deliberate problems."""

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 500

df = pd.DataFrame(
    {
        "customer_id": np.arange(1000, 1000 + n),
        "email": [f"user{i}@example.com" for i in range(n)],
        "country": rng.choice(["Canada", "canada", "USA", "usa ", "India", "UK"], n),
        "signup_date": pd.date_range("2024-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
        "age": rng.integers(18, 75, n).astype(float),
        "annual_spend": [f"${v:,.2f}" for v in rng.gamma(2, 400, n)],
        "orders": rng.poisson(6, n),
        "plan": ["standard"] * n,
        "referral_code": [None] * 420 + [f"REF{i}" for i in range(80)],
    }
)

df.loc[rng.choice(n, 40, replace=False), "age"] = np.nan   # missing values
df.loc[[10, 20, 30], "orders"] = [480, 950, 1200]          # extreme outliers
df.loc[[5, 6], "customer_id"] = [1001, 1002]               # duplicate keys
df = pd.concat([df, df.iloc[:8]], ignore_index=True)        # duplicate rows

out = Path(__file__).with_name("messy_customers.csv")
df.to_csv(out, index=False)
print(f"Wrote {out} ({len(df)} rows)")

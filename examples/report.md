# Data quality report: `messy_customers.csv`

Generated 2026-09-25 22:00 UTC by [datascout](https://github.com/YOUR-USERNAME/datascout).

**Health score: 36/100 (Poor)**

| Rows | Columns | Duplicate rows | Missing cells | Memory |
|---:|---:|---:|---:|---:|
| 508 | 9 | 8 | 469 | 0.171 MB |

## Issues (2 high, 4 medium, 5 low)

| Severity | Column | Issue | Suggested fix |
|---|---|---|---|
| high | customer_id | Looks like a key column but has 10 duplicated value(s) | Investigate before joining; duplicate keys multiply rows. |
| high | referral_code | 84.3% of values are missing | Consider dropping, or check why the source stops populating it. |
| medium | (table) | 8 fully duplicated rows (1.6%) | Use df.drop_duplicates() or add a unique key constraint upstream. |
| medium | annual_spend | 100% of values look numeric but column is stored as text | Strip symbols and cast with pd.to_numeric(..., errors='coerce'). |
| medium | country | Same category written differently: [['Canada', 'canada'], ['USA', 'usa']] | Normalise with .str.strip().str.lower() or a mapping dict. |
| medium | email | Column appears to contain email addresses | Mask, hash or drop before sharing this dataset. |
| low | age | 8.1% of values are missing | Usually fine; make sure downstream code handles nulls. |
| low | country | 78 value(s) have leading/trailing spaces | Apply .str.strip(); padded keys silently break joins. |
| low | orders | 3 extreme outlier(s) outside [-5.00, 16.00], e.g. [480, 950, 1200] | Verify these are real values and not unit or entry errors. |
| low | plan | Only one distinct value: 'standard' | Carries no information for modelling; consider dropping. |
| low | signup_date | Values look like dates but column is stored as text | Parse with pd.to_datetime() so you can sort, filter and resample. |

## Column profiles

| Column | Type | Missing % | Unique | Sample values |
|---|---|---:|---:|---|
| customer_id | numeric | 0.0 | 498 | 1000, 1001, 1002 |
| email | text | 0.0 | 500 | user0@example.com, user1@example.com, user2@example.com |
| country | text | 0.0 | 6 | Canada, India, usa  |
| signup_date | text | 0.0 | 500 | 2024-01-01, 2024-01-02, 2024-01-03 |
| age | numeric | 8.07 | 57 | 24.0, 55.0, 72.0 |
| annual_spend | text | 0.0 | 500 | $1,714.44, $1,013.80, $582.48 |
| orders | numeric | 0.0 | 19 | 7, 5, 8 |
| plan | text | 0.0 | 1 | standard |
| referral_code | text | 84.25 | 80 | REF0, REF1, REF2 |

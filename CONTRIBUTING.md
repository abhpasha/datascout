# Contributing to datascout

Thanks for your interest! Bug reports, new checks and documentation fixes are all welcome.

## Getting set up

```bash
git clone https://github.com/YOUR-USERNAME/datascout.git
cd datascout
pip install -e ".[dev]"
pytest
```

## Proposing a new check

1. Open an issue describing the problem the check catches and a small example of bad data.
2. Add the function to `src/datascout/checks.py` and register it in `ALL_CHECKS`.
3. Add at least one test showing it fires on bad data and stays quiet on clean data.
4. Add a row to the "What it checks" table in the README.

Good checks are **specific** (low false-positive rate) and **actionable** (the suggestion tells
someone what to do next).

## Pull requests

- Keep PRs focused on one change.
- Make sure `pytest` and `ruff check .` pass.
- Describe what changed and why in the PR description.

"""datascout: fast, zero-config data quality checks for tabular data."""

from datascout.checks import Issue, run_checks
from datascout.profiler import profile
from datascout.report import Report, scan

__all__ = ["Issue", "Report", "profile", "run_checks", "scan"]
__version__ = "0.1.0"

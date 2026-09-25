"""Command-line interface: `datascout data.csv --html report.html --fail-under 80`."""

from __future__ import annotations

import argparse
import sys

from datascout import __version__
from datascout.checks import ALL_CHECKS
from datascout.report import scan


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="datascout",
        description="Scan a tabular data file for quality issues and get suggested fixes.",
    )
    p.add_argument("path", help="CSV, TSV, Parquet, JSON/JSONL or Excel file")
    p.add_argument("--html", metavar="FILE", help="write an HTML report")
    p.add_argument("--md", metavar="FILE", help="write a Markdown report")
    p.add_argument("--json", metavar="FILE", help="write a JSON report (for pipelines)")
    p.add_argument(
        "--skip", nargs="+", default=[], choices=sorted(ALL_CHECKS), metavar="CHECK",
        help=f"checks to skip; one or more of: {', '.join(sorted(ALL_CHECKS))}",
    )
    p.add_argument(
        "--fail-under", type=int, metavar="SCORE",
        help="exit with code 1 if the health score is below SCORE (useful in CI)",
    )
    p.add_argument("-q", "--quiet", action="store_true", help="don't print the summary")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = scan(args.path, skip=args.skip)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(report.to_text())
    for target in (args.html, args.md, args.json):
        if target:
            report.save(target)
            if not args.quiet:
                print(f"\nSaved {target}")

    if args.fail_under is not None and report.score < args.fail_under:
        print(f"\nHealth score {report.score} is below --fail-under {args.fail_under}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Tie profiling and checks together and render results as text, Markdown, HTML or JSON."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from datascout.checks import Issue, health_score, run_checks
from datascout.io import load
from datascout.profiler import profile


@dataclass
class Report:
    source: str
    summary: dict
    issues: list[Issue]
    score: int
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )

    # ------------------------------------------------------------ helpers
    def counts(self) -> dict[str, int]:
        c = {"high": 0, "medium": 0, "low": 0}
        for i in self.issues:
            c[i.severity] += 1
        return c

    @property
    def grade(self) -> str:
        if self.score >= 90:
            return "Excellent"
        if self.score >= 75:
            return "Good"
        if self.score >= 50:
            return "Needs attention"
        return "Poor"

    # ------------------------------------------------------------ outputs
    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "generated_at": self.generated_at,
            "score": self.score,
            "grade": self.grade,
            "issue_counts": self.counts(),
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_text(self) -> str:
        s, c = self.summary, self.counts()
        lines = [
            f"datascout report for {self.source}",
            f"{s['rows']:,} rows x {s['columns']} columns | {s['memory_mb']} MB",
            f"Health score: {self.score}/100 ({self.grade})",
            f"Issues: {c['high']} high, {c['medium']} medium, {c['low']} low",
            "",
        ]
        if not self.issues:
            lines.append("No issues found.")
        for i in self.issues:
            where = f"[{i.column}] " if i.column else ""
            lines.append(f"  {i.severity.upper():<6} {where}{i.message}")
            if i.suggestion:
                lines.append(f"         fix: {i.suggestion}")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        s, c = self.summary, self.counts()
        out = [
            f"# Data quality report: `{self.source}`",
            "",
            f"Generated {self.generated_at} by [datascout](https://github.com/YOUR-USERNAME/datascout).",
            "",
            f"**Health score: {self.score}/100 ({self.grade})**",
            "",
            "| Rows | Columns | Duplicate rows | Missing cells | Memory |",
            "|---:|---:|---:|---:|---:|",
            (
                f"| {s['rows']:,} | {s['columns']} | {s['duplicate_rows']:,} | "
                f"{s['total_missing_cells']:,} | {s['memory_mb']} MB |"
            ),
            "",
            f"## Issues ({c['high']} high, {c['medium']} medium, {c['low']} low)",
            "",
        ]
        if self.issues:
            out += ["| Severity | Column | Issue | Suggested fix |", "|---|---|---|---|"]
            for i in self.issues:
                msg = i.message.replace("|", "\\|")
                out.append(f"| {i.severity} | {i.column or '(table)'} | {msg} | {i.suggestion} |")
        else:
            out.append("No issues found.")
        out += [
            "",
            "## Column profiles",
            "",
            "| Column | Type | Missing % | Unique | Sample values |",
            "|---|---|---:|---:|---|",
        ]
        for p in s["column_profiles"]:
            sample = ", ".join(p["sample"]).replace("|", "\\|")
            out.append(f"| {p['name']} | {p['type']} | {p['missing_pct']} | {p['unique']:,} | {sample} |")
        return "\n".join(out) + "\n"

    def to_html(self) -> str:
        s, c = self.summary, self.counts()
        e = html.escape
        total = max(len(self.issues), 1)

        issue_rows = "".join(
            f"<tr class='sev-{i.severity}'><td><span class='pill'>{i.severity}</span></td>"
            f"<td>{e(i.column or '(whole table)')}</td><td>{e(i.message)}</td>"
            f"<td class='fix'>{e(i.suggestion)}</td></tr>"
            for i in self.issues
        ) or "<tr><td colspan='4' class='empty'>No issues found. This dataset looks clean.</td></tr>"

        col_rows = "".join(
            f"<tr><td class='mono'>{e(p['name'])}</td><td>{p['type']}</td>"
            f"<td><div class='bar'><span style='width:{p['missing_pct']}%'></span></div>"
            f"<small>{p['missing_pct']}%</small></td>"
            f"<td class='num'>{p['unique']:,}</td>"
            f"<td class='sample'>{e(', '.join(p['sample']))}</td></tr>"
            for p in s["column_profiles"]
        )

        segs = "".join(
            f"<span class='seg-{k}' style='flex:{c[k] / total}'></span>" for k in ("high", "medium", "low") if c[k]
        )

        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>datascout: {e(self.source)}</title>
<style>
:root {{ --ink:#18263B; --muted:#5B6878; --paper:#FFFFFF; --field:#F2F4F7; --line:#DDE2E8;
        --high:#B8322A; --medium:#A86B12; --low:#3A68A0; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --ink:#E6EAF0; --muted:#9AA6B5; --paper:#131A24; --field:#1C2531; --line:#2C3746;
          --high:#F07068; --medium:#E3A64A; --low:#7EA9DB; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink);
       font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:1080px; margin:0 auto; padding:40px 24px 64px; }}
h1 {{ font-size:1.7rem; margin:0 0 4px; letter-spacing:-.01em; }}
h2 {{ font-size:1.15rem; margin:40px 0 12px; }}
.meta {{ color:var(--muted); margin:0 0 28px; }}
.mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.9em; }}
.score {{ display:grid; grid-template-columns:auto 1fr; gap:28px; align-items:center;
         background:var(--field); border-radius:10px; padding:22px 26px; }}
.score b {{ font-size:3rem; line-height:1; }}
.score b small {{ font-size:1rem; color:var(--muted); font-weight:500; }}
.stack {{ display:flex; height:10px; border-radius:5px; overflow:hidden; background:var(--line); margin:10px 0 8px; }}
.seg-high {{ background:var(--high); }} .seg-medium {{ background:var(--medium); }} .seg-low {{ background:var(--low); }}
.legend span {{ margin-right:18px; color:var(--muted); }}
.legend i {{ display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:6px; }}
dl {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:1px; background:var(--line);
     border:1px solid var(--line); border-radius:10px; overflow:hidden; margin:20px 0 0; }}
dl div {{ background:var(--paper); padding:14px 18px; }}
dt {{ color:var(--muted); font-size:.85rem; }} dd {{ margin:2px 0 0; font-size:1.25rem; font-weight:600; }}
.scroll {{ overflow-x:auto; border:1px solid var(--line); border-radius:10px; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ text-align:left; padding:10px 14px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ font-size:.85rem; color:var(--muted); font-weight:600; background:var(--field); }}
tr:last-child td {{ border-bottom:0; }}
.pill {{ font-size:.8rem; font-weight:600; padding:2px 8px; border-radius:999px; border:1px solid currentColor; }}
.sev-high .pill {{ color:var(--high); }} .sev-medium .pill {{ color:var(--medium); }} .sev-low .pill {{ color:var(--low); }}
.fix {{ color:var(--muted); }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.bar {{ display:inline-block; width:80px; height:6px; background:var(--line); border-radius:3px; margin-right:8px; vertical-align:middle; }}
.bar span {{ display:block; height:100%; background:var(--medium); border-radius:3px; }}
.sample {{ color:var(--muted); max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.empty {{ color:var(--muted); padding:24px; }}
footer {{ margin-top:48px; color:var(--muted); font-size:.85rem; }}
@media (max-width:600px) {{ .score {{ grid-template-columns:1fr; }} }}
</style></head><body><main>
<h1>Data quality report</h1>
<p class="meta"><span class="mono">{e(self.source)}</span>, generated {self.generated_at}</p>

<section class="score">
  <b>{self.score}<small>/100</small></b>
  <div><strong>{self.grade}</strong>: {len(self.issues)} issue(s) found
    <div class="stack">{segs}</div>
    <div class="legend"><span><i style="background:var(--high)"></i>{c['high']} high</span>
      <span><i style="background:var(--medium)"></i>{c['medium']} medium</span>
      <span><i style="background:var(--low)"></i>{c['low']} low</span></div></div>
</section>

<dl>
  <div><dt>Rows</dt><dd>{s['rows']:,}</dd></div>
  <div><dt>Columns</dt><dd>{s['columns']}</dd></div>
  <div><dt>Duplicate rows</dt><dd>{s['duplicate_rows']:,}</dd></div>
  <div><dt>Missing cells</dt><dd>{s['total_missing_cells']:,}</dd></div>
  <div><dt>Memory</dt><dd>{s['memory_mb']} MB</dd></div>
</dl>

<h2>Issues and suggested fixes</h2>
<div class="scroll"><table><thead><tr><th>Severity</th><th>Column</th><th>Issue</th><th>Suggested fix</th></tr></thead>
<tbody>{issue_rows}</tbody></table></div>

<h2>Column profiles</h2>
<div class="scroll"><table><thead><tr><th>Column</th><th>Type</th><th>Missing</th><th class="num">Unique</th><th>Sample values</th></tr></thead>
<tbody>{col_rows}</tbody></table></div>

<footer>Generated by datascout. Scores are heuristic: use them to prioritise, not to certify.</footer>
</main></body></html>
"""

    def save(self, path: str | Path) -> Path:
        """Save the report; format is chosen from the extension (.html, .md, .json, .txt)."""
        path = Path(path)
        renderers = {".html": self.to_html, ".md": self.to_markdown, ".json": self.to_json, ".txt": self.to_text}
        if path.suffix.lower() not in renderers:
            raise ValueError("Report path must end in .html, .md, .json or .txt")
        path.write_text(renderers[path.suffix.lower()](), encoding="utf-8")
        return path


def scan(data: pd.DataFrame | str | Path, skip: list[str] | None = None, name: str | None = None) -> Report:
    """Profile and check a DataFrame or a file path. This is the main entry point."""
    if isinstance(data, pd.DataFrame):
        df, source = data, name or "DataFrame"
    else:
        df, source = load(data), name or Path(data).name
    issues = run_checks(df, skip=skip)
    return Report(source=source, summary=profile(df), issues=issues, score=health_score(issues))

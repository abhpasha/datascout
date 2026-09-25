"""Use datascout from Python instead of the command line."""

import pandas as pd

import datascout

df = pd.read_csv("examples/messy_customers.csv")

report = datascout.scan(df, name="messy_customers.csv")
print(report.to_text())

# Work with issues programmatically, e.g. fail a pipeline step on high-severity problems.
high = [i for i in report.issues if i.severity == "high"]
if high:
    print(f"\n{len(high)} high-severity issue(s) need attention before loading to the warehouse.")

report.save("examples/report.html")
report.save("examples/report.md")

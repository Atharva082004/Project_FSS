# loc_monthly.py -- Q5: average NLOC per month of src/flask/app.py
# Produces two versions of the plot:
#   "all"          : every commit reachable from the checked-out commit (task definition)
#   "first_parent" : only the first-parent line (robustness check, see report)
import os
import subprocess
from datetime import datetime, timezone

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pydriller import Repository

REPO = "flask"
TARGET = "src/flask/app.py"
SINCE = datetime(2021, 1, 1, tzinfo=timezone.utc)
UNTIL = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
SPLIT = "0ec7f713d679ceed2c605e62ac5d38d579f29fa0"   # "Split the App and Blueprint ..."
os.makedirs("figures", exist_ok=True)

# Commits on the first-parent line of HEAD (excludes commits that only entered the
# history through merges of other branches, e.g. maintenance branches).
first_parent = set(subprocess.check_output(
    ["git", "-C", REPO, "rev-list", "--first-parent", "HEAD"], text=True).split())

# --- 1. NLOC of the target file after every commit that modified it ----------
rows = []
for c in Repository(REPO, since=SINCE, to=UNTIL).traverse_commits():
    for m in c.modified_files:
        if m.new_path == TARGET:
            rows.append(dict(hash=c.hash, date=c.committer_date,
                             change=m.change_type.name, nloc=m.nloc,
                             msg=c.msg.splitlines()[0],
                             on_first_parent=c.hash in first_parent))

all_df = pd.DataFrame(rows)
all_df["date"] = pd.to_datetime(all_df["date"], utc=True)      # months bucketed in UTC
all_df = all_df.sort_values("date", kind="stable").reset_index(drop=True)
all_df.to_csv("figures/q5_commits_for_target.csv", index=False)

print("commits touching", TARGET, ":", len(all_df))
print("  on first-parent line:", int(all_df["on_first_parent"].sum()))
print(all_df["change"].value_counts().to_string())
print("rows with nloc missing:", int(all_df["nloc"].isna().sum()))


# --- 2. Monthly average + plot (months without modifications are NOT plotted) -
def analyse(d, tag, subtitle):
    d = d.dropna(subset=["nloc"]).copy()
    d["month"] = d["date"].dt.strftime("%Y-%m")
    monthly = d.groupby("month")["nloc"].agg(mean="mean", n="count")
    monthly.to_csv(f"figures/q5_monthly_avg_nloc_{tag}.csv")

    fig, ax = plt.subplots(figsize=(14, 6))
    bars = ax.bar(monthly.index, monthly["mean"], color="#1f77b4")
    for b, n in zip(bars, monthly["n"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{n}",
                ha="center", va="bottom", fontsize=7)
    ax.set_xlabel("Month (only months in which the file was modified)")
    ax.set_ylabel("Average NLOC after modification")
    ax.set_title(f"{TARGET}: average LOC per month, 2021-01 to 2024-12\n"
                 f"{subtitle}; number above bar = commits in that month")
    plt.setp(ax.get_xticklabels(), rotation=90, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"figures/q5_monthly_loc_{tag}.png", dpi=200)
    plt.close(fig)

    # largest consecutive size changes (for manual investigation)
    d["delta_nloc"] = d["nloc"].diff()
    big = d.loc[d["delta_nloc"].abs().nlargest(10).index]
    print(f"\n=== largest size changes [{tag}] ===")
    print(big[["hash", "date", "change", "nloc", "delta_nloc", "msg"]].to_string())


analyse(all_df, "all", "all commits reachable from HEAD")
analyse(all_df[all_df["on_first_parent"]], "first_parent", "first-parent history only")

# --- 3. What did the split commit do? (code moved, or code deleted?) ---------
print("\n=== split commit", SPLIT[:7], "===")
for c in Repository(REPO, single=SPLIT).traverse_commits():
    for m in c.modified_files:
        if m.new_path in ("src/flask/app.py", "src/flask/sansio/app.py"):
            print(f"{m.new_path:28s} {m.change_type.name:8s} old_path={m.old_path}  nloc={m.nloc}")
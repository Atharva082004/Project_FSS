# change_frequency.py -- Q3: most frequently changed files
# Usage:
#   python change_frequency.py            -> path-based ranking (primary)
#   python change_frequency.py lineage    -> renames merged (robustness check)
# Requires files.csv from analysis.py (columns: hash, date, path, old_path, change, added, deleted)
import os
import sys

import pandas as pd
import matplotlib
matplotlib.use("Agg")                      # no GUI needed, just save files
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

MERGE_RENAMES = len(sys.argv) > 1 and sys.argv[1] == "lineage"
EXCLUDE_PURE_RENAMES = True   # a pure move (0 lines added/deleted) is not a content change
TOP_N = 20
suffix = "lineage" if MERGE_RENAMES else "path"
os.makedirs("figures", exist_ok=True)

f = pd.read_csv("files.csv")

# Row order = PyDriller traversal order (oldest commit first). Do NOT re-sort by date.
order = {h: i for i, h in enumerate(f["hash"].drop_duplicates())}
f["ord"] = f["hash"].map(order)

# --- 1. Canonical path ------------------------------------------------------
if MERGE_RENAMES:
    # Time-aware: a path is redirected only for commits made BEFORE its rename,
    # so a new file that reuses an old path (e.g. app.py after the sansio split)
    # is not folded into the renamed file.
    events = {}   # old_path -> list of (commit_order, new_path)
    ren = f[f["change"] == "RENAME"]
    for old, new, o in zip(ren["old_path"], ren["path"], ren["ord"]):
        events.setdefault(old, []).append((o, new))

    def canonical(path, o):
        for _ in range(20):                          # guard against cycles
            later = [(ro, new) for ro, new in events.get(path, []) if ro > o]
            if not later:
                break
            o, path = min(later)                     # earliest later rename
        return path

    f["canonical_path"] = [canonical(p, o) for p, o in zip(f["path"], f["ord"])]
    leftover = [p for p in f["canonical_path"].unique() if p.startswith("flask/")]
    if leftover:
        print("WARNING: old-layout paths not merged:", leftover[:10])
else:
    f["canonical_path"] = f["path"]

# --- 2. Optionally drop pure renames (moves without content change) ----------
if EXCLUDE_PURE_RENAMES:
    pure = (f["change"] == "RENAME") & (f["added"] == 0) & (f["deleted"] == 0)
    print("pure renames excluded:", int(pure.sum()))
    f = f[~pure]

# --- 3. Change frequency = number of distinct commits touching each file -----
counts = (f.groupby("canonical_path")["hash"].nunique()
            .sort_values(ascending=False))
counts.rename("n_commits").to_csv(f"figures/change_frequency_all_files_{suffix}.csv")

top = counts.head(TOP_N)
print(f"mode: {suffix}")
print(top.to_string())
print("commits touching any file:", f["hash"].nunique())

# --- 4. Colour bars by file category ----------------------------------------
def categorize(path):
    p = path.lower()
    if p.startswith("src/flask/") and p.endswith(".py"):
        return "Production code (src/flask)"
    if p.startswith("tests/"):
        return "Tests"
    if p.startswith("docs/") or p.endswith((".rst", ".md")):
        return "Docs / changelog"
    if (p.startswith((".github/", "requirements/"))
            or p.endswith((".toml", ".txt", ".cfg", ".ini", ".yaml", ".yml", ".in"))):
        return "Config / dependencies / CI"
    return "Other"

COLORS = {
    "Production code (src/flask)": "#1f77b4",
    "Tests": "#2ca02c",
    "Docs / changelog": "#ff7f0e",
    "Config / dependencies / CI": "#9467bd",
    "Other": "#7f7f7f",
}

plot_df = top.iloc[::-1]                    # reverse so the largest bar is on top
cats = [categorize(p) for p in plot_df.index]

fig, ax = plt.subplots(figsize=(11, 8))
bars = ax.barh(plot_df.index, plot_df.values, color=[COLORS[c] for c in cats])
ax.bar_label(bars, padding=3, fontsize=9)
ax.set_xlim(0, plot_df.max() * 1.1)
ax.set_xlabel("Number of commits that modified the file")
note = "renames merged" if MERGE_RENAMES else "path-based"
ax.set_title(f"Top {TOP_N} most frequently changed files in Flask ({note})\n"
             "(2021-01-01 to 2024-12-31)")
used = [c for c in COLORS if c in set(cats)]
ax.legend(handles=[Patch(color=COLORS[c], label=c) for c in used],
          loc="lower right", title="File type")
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
out = f"figures/q3_change_frequency_{suffix}.png"
fig.savefig(out, dpi=200)
print("saved", out)
# q1_q2.py (v2) -- Q1 (commit count) and Q2 (commits with the fewest modified files)
# Requires commits.csv and files.csv from analysis.py
import os
import subprocess

import pandas as pd

os.makedirs("figures", exist_ok=True)
c = pd.read_csv("commits.csv")
c["msg"] = c["msg"].fillna("")
f = pd.read_csv("files.csv")
WINDOW = ["--since=2021-01-01T00:00:00Z", "--until=2024-12-31T23:59:59Z"]


def git(*args):
    return subprocess.check_output(["git", "-C", "flask", *args], text=True)


# ------------------------------------------------------------------ Q1 -------
total = len(c)
merges = int(c["merge"].sum())
print("=== Q1 ===")
print(f"commits (PyDriller):          {total}")
print(f"  merge commits:              {merges}")
print(f"  non-merge commits:          {total - merges}")
print(f"git rev-list --count:         {int(git('rev-list', '--count', *WINDOW, 'HEAD'))}")
print(f"git rev-list --merges --count:{int(git('rev-list', '--merges', '--count', *WINDOW, 'HEAD'))}")

# ------------------------------------------------------------------ Q2 -------
print("\n=== Q2 ===")
zero = c[c["n_files"] == 0]
print(f"commits with 0 modified files: {len(zero)} "
      f"(merge: {int(zero['merge'].sum())}, non-merge: {int((~zero['merge']).sum())})")
print("non-merge commit(s) with 0 files:")
print(zero[~zero["merge"]][["hash", "date", "msg"]].to_string(index=False))

nm = c[~c["merge"]]
pos = nm[nm["n_files"] >= 1]
mn = int(pos["n_files"].min())
small = pos[pos["n_files"] == mn].copy()
print(f"\nnon-merge commits with >= 1 file, minimum = {mn}: {len(small)} commits "
      f"({len(small) / len(nm) * 100:.1f}% of non-merge commits)")


# Categorise by WHICH file the commit touched (more reliable than keywords in the message)
def path_category(p):
    q = p.lower()
    if q.startswith("tests/"):
        return "tests"
    if q.startswith("src/flask/") and q.endswith(".py"):
        return "production code"
    if q == "changes.rst":
        return "changelog"
    if q.startswith("docs/") or q.endswith((".rst", ".md")):
        return "documentation / project docs"
    if (q.startswith((".github/", "requirements/")) or q.startswith(".pre-commit")
            or q.endswith((".toml", ".txt", ".cfg", ".ini", ".yaml", ".yml", ".in"))):
        return "config / CI / dependencies"
    return "other"


def is_bot(msg):
    m = msg.lower()
    return m.startswith("bump ") or "[pre-commit.ci]" in m


single = f[f["hash"].isin(small["hash"])].drop_duplicates("hash")[["hash", "path"]]
small = small.merge(single, on="hash", how="left")
small["category"] = small["path"].fillna("").map(path_category)
small["bot"] = small["msg"].map(is_bot)

print("\ncategory of the single modified file:")
print(small["category"].value_counts().to_string())
print(f"\nbot-style messages (Bump ... / [pre-commit.ci]): {int(small['bot'].sum())}")
print("\nmost frequently modified files among single-file commits:")
print(small["path"].value_counts().head(15).to_string())

small.to_csv("figures/q2_smallest_commits.csv", index=False)
sample = small.sample(min(25, len(small)), random_state=42).sort_values("date")
sample.to_csv("figures/q2_manual_sample.csv", index=False)
print("\nsample for manual inspection (git -C flask show <hash>):")
print(sample[["hash", "date", "path", "msg"]].to_string(index=False))
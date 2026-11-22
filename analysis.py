# analysis.py
from datetime import datetime, timezone
import pandas as pd
from pydriller import Repository

REPO = "flask"
SINCE = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
UNTIL = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

commits, files = [], []
for c in Repository(REPO, since=SINCE, to=UNTIL).traverse_commits():
    mods = c.modified_files
    commits.append(dict(hash=c.hash, date=c.committer_date, merge=c.merge,
                        n_files=len(mods), msg=c.msg.splitlines()[0]))
    for m in mods:
        files.append(dict(hash=c.hash, date=c.committer_date,
                  path=m.new_path or m.old_path,
                  old_path=m.old_path,
                  change=m.change_type.name,
                  added=m.added_lines, deleted=m.deleted_lines))

pd.DataFrame(commits).to_csv("commits.csv", index=False)
pd.DataFrame(files).to_csv("files.csv", index=False)
print("commits:", len(commits))
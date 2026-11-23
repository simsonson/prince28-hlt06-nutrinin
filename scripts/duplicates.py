import json
from collections import defaultdict
from pathlib import Path

groups = defaultdict(list)
for line in Path("data/manifest.jsonl").read_text(encoding="utf-8").splitlines():
    record = json.loads(line)
    if record.get("status") == "downloaded":
        groups[record["sha256"]].append(record["url"])
for digest, urls in groups.items():
    if len(urls) > 1:
        print(digest, *urls, sep="\n")

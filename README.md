# CTF writeups

Writeups for CTF challenges. Each entry walks through the analysis, the underlying vulnerability, and the steps that reproduce the solution. Flags are intentionally left out.

## FortID CTF 2026

### Web

| Challenge | Technique |
|---|---|
| [Do You Know Lika?](FortID/Web/01-do-you-know-lika/README.md) | Server-side template injection in Handlebars via prototype pollution |
| [Ultimative PHP](FortID/Web/02-ultimative-php/README.md) | Chained PHP quirks: parameter name mangling, the `Array` collision, a magic hash, and object injection |
| [Doctor Bye Bye](FortID/Web/03-doctor-bye-bye/README.md) | Blind SQL injection through `ORDER BY` using a boolean oracle |

### Cryptography

| Challenge | Technique |
|---|---|
| [DESBox](FortID/Cryptography/01-desbox/README.md) | 3DES complementation property used to bypass the key checks |

### OSINT

| Challenge | Technique |
|---|---|
| [Baby OSINT](FortID/OSINT/01-baby-osint/README.md) | Recovering the event from a photograph with cross-source pivoting |

## Repository layout

Each writeup lives under `FortID/<category>/<challenge>/`. Inside a folder you will find:

- `README.md` - the writeup itself, with the reasoning and the steps;
- the challenge source, when it helps explain the vulnerability;
- a ready-to-run solve script, where one is needed.

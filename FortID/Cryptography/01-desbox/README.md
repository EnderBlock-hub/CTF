# DESBox

| Field | Value |
|---|---|
| Platform | FortID CTF |
| Category | Cryptography |
| Challenge file | [`DESBox.py`](DESBox.py) |
| Status | Solved |
| Flag | Omitted |

## Challenge overview

DESBox is a small MS-DOS style shell. The `DIR` listing shows three files, `KEYB.COM`, `README.TXT` and `FLAG.BIN`, but `TYPE FLAG.BIN` only answers `Access denied`, so the flag never leaves the box on its own.

The only command that touches the flag is `KEYB`. It asks for two 24-byte 3DES keys written as hex, prints `FLAG.BIN` encrypted under the first key, and then decrypts one attacker-chosen blob under the second key as a "debug" feature:

```python
print("\nC:\\FLAG.BIN encrypted under Key A:")
print(DES3.new(key_a, DES3.MODE_ECB).encrypt(FLAG).hex())

ct = bytes.fromhex(input("\nDebug ciphertext> ").strip())
print("Debug output:")
print(DES3.new(key_b, DES3.MODE_ECB).decrypt(ct).hex())
```

So the service hands us two things at once:

- `C = E_Ka(FLAG)` in 3DES-ECB;
- a decryption oracle `D_Kb(ct)` for any `ct` we send.

Ka and Kb are keys that we influence but do not fully control.

## What the keys actually are

A submitted key does not go into 3DES unchanged. Each one is run through `load_key`:

```python
def load_key(user_key):
    key = xor(permute(user_key), MASK)
    return DES3.adjust_key_parity(key)
```

Three things happen to our input:

1. `permute` shuffles the 24 bytes with a fresh random permutation, created separately for each key;
2. the result is XORed with a fixed secret table `MASK` that we never get to see;
3. `adjust_key_parity` fixes the low bit of every byte so the key has valid DES parity.

On top of that, `read_keys` rejects "obvious" key pairs with four guards:

```python
if key_a == key_b: ...                                      # identical
if effective_bytes(key_a) == effective_bytes(key_b): ...    # equal ignoring parity
if sorted(effective_bytes(key_a)) == sorted(effective_bytes(key_b)): ...  # same byte multiset
if is_effective_complement(key_a, key_b): ...               # one is the complement of the other
```

`effective_bytes` drops the parity bit from every byte (`b & 0xFE`), because DES ignores it anyway.

## The idea: DES complementation

DES has a well known complementation property. Flip every bit of the key and every bit of the plaintext, and the ciphertext flips too:

```
E(~K, ~P) = ~E(K, P)
```

The same holds for 3DES in EDE mode: complementing all three subkeys and the input complements the output of each stage in turn. Written for decryption, this becomes:

```
D(~K, ~C) = ~P
```

That is exactly the shape of our oracle. If Kb is the bitwise complement of Ka, then sending the complement of `C` into the decrypt oracle gives us the complement of the flag:

```
D(Kb, ~C) = D(~Ka, ~E(Ka, FLAG)) = ~FLAG
```

and flipping the bits back recovers `FLAG`.

One subtlety makes this easier. DES ignores the parity bit of each key byte, so "complement of the key" only has to hold on the top seven bits of every byte. XORing a byte with `0xFF` flips those seven bits (plus the ignored parity bit), which is precisely what the property needs.

## Getting past the guards and the secret MASK

We cannot set Ka and Kb directly. After our input is permuted and XORed with the same secret `MASK`, we need the two loaded keys to come out as complements on their effective bits. The key observation is that `MASK` is the same for both keys, so it cancels out of the comparison: only the relationship between the two permuted inputs matters.

If `permute(A)` and `permute(B)` end up as complements position by position, then `permute(A) ^ MASK` and `permute(B) ^ MASK` are complements too, because XORing both sides with the same `MASK` preserves their difference. After parity adjustment the two DES keys are effective complements, and the oracle returns `~FLAG`.

So we want two inputs that stay complements of each other no matter how they are shuffled. The trick is to pick complement multisets with a single odd byte:

```python
A = bytes([0x00] * 23 + [0x02])
B = bytes([0xFD] + [0xFF] * 23)
```

Byte for byte, `0x00` complements to `0xFF` and `0x02` complements to `0xFD`, so B is the complement of A as a multiset. Now look at the two independent shuffles:

- every position where both keys hold a common byte gives `0x00 ^ 0xFF = 0xFF`, a clean complement;
- the single odd byte (`0x02` in A, `0xFD` in B) is also a complement, but only if it lands in the same position in both shuffles.

The two permutations are independent, so the odd bytes line up with probability `1/24`. When they do, the loaded keys are exact effective complements and the attack fires. When they do not, two positions are wrong and the output is garbage, so we simply try again. About 24 attempts on average.

The same A and B slip past all four guards:

- they are not equal;
- their effective bytes differ;
- their effective multisets differ (A holds twenty-three `0x00`, B holds twenty-three `0xFE`);
- `is_effective_complement` compares the two inputs as ordered lists, and because the odd byte sits at opposite ends of A and B, the ordered lists are not complements, so the check passes. The complement relationship only appears after the server's own shuffle, which that guard never accounts for.

That gap is the whole challenge: the checks look at the raw input in a fixed order, while the actual key derivation permutes the bytes afterwards.

## Solve script

One connection is enough, because our keys always pass the guards, so `KEYB` can be repeated in a loop until the odd bytes line up. The full script is in [`solve.py`](solve.py):

```python
from pwn import *

A = bytes([0x00] * 23 + [0x02])
B = bytes([0xFD] + [0xFF] * 23)

def flip(data):
    return bytes(b ^ 0xFF for b in data)

# the FortID instance speaks TLS, so wrap the socket
io = remote("HOST", 1337, ssl=True)

for attempt in range(1, 500):
    io.sendlineafter(b"C:\\> ", b"KEYB")
    io.sendlineafter(b"KEY A> ", A.hex().encode())
    io.sendlineafter(b"KEY B> ", B.hex().encode())

    io.recvuntil(b"under Key A:\n")
    enc_flag = bytes.fromhex(io.recvline().strip().decode())

    io.sendlineafter(b"Debug ciphertext> ", flip(enc_flag).hex().encode())
    io.recvuntil(b"Debug output:\n")
    out = bytes.fromhex(io.recvline().strip().decode())

    guess = flip(out)
    if b"FortID{" in guess:
        log.success(f"recovered after {attempt} tries")
        print(guess.decode(errors="replace"))
        break
```

## Running it

Pass the instance host and port on the command line (the socket is wrapped in TLS). Most of the time it finishes well inside the service's 2-minute limit:

```
python solve.py desbox-<id>.inst<n>.ctf.fortid.com 1337

[+] Opening connection to desbox-<id>.inst<n>.ctf.fortid.com on port 1337: Done
[+] recovered after 19 tries
FortID{...}
```

If an attempt does not align within two minutes, the server closes the socket on its own timer. Just reconnect and run again, since every fresh connection starts the timer over.

## Takeaways

- The DES complementation property is still a real attack surface whenever an interface exposes an encryption result and a decryption oracle under related keys.
- Ignored parity bits mean "complement" only has to hold on seven bits per byte, which is trivial to arrange.
- The guards tried to forbid complement keys, but they inspected the raw input in a fixed order while the server itself permuted the bytes before use. The validation and the real key derivation disagreed, and that disagreement is the vulnerability.

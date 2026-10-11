#!/usr/bin/env python3
# DESBox - FortID CTF
#
# The service prints  C = E(Ka, FLAG)  and then decrypts anything we send
# under a second key Kb. 3DES has the complementation property, so if Kb is
# the bitwise complement of Ka then
#
#     D(Kb, ~C) = ~FLAG
#
# We cannot set the keys directly: the server permutes our input, XORs it
# with a secret mask and fixes the parity. So we hand it two inputs that are
# complements of each other as a multiset, with a single "odd" byte. When
# the server's two independent shuffles happen to put that odd byte in the
# same slot (about 1 in 24), the loaded keys are exact complements and the
# decrypt oracle returns ~FLAG.

from pwn import *

# complement multisets: 0x00 <-> 0xFF and the odd pair 0x02 <-> 0xFD
A = bytes([0x00] * 23 + [0x02])
B = bytes([0xFD] + [0xFF] * 23)


def flip(data):
    return bytes(b ^ 0xFF for b in data)


io = remote("HOST", PORT)

for attempt in range(1, 500):
    io.sendlineafter(b"C:\\> ", b"KEYB")
    io.sendlineafter(b"KEY A> ", A.hex().encode())
    io.sendlineafter(b"KEY B> ", B.hex().encode())

    io.recvuntil(b"under Key A:\n")
    enc_flag = bytes.fromhex(io.recvline().strip().decode())

    # feed the complement of the ciphertext back into the decrypt oracle
    io.sendlineafter(b"Debug ciphertext> ", flip(enc_flag).hex().encode())
    io.recvuntil(b"Debug output:\n")
    out = bytes.fromhex(io.recvline().strip().decode())

    guess = flip(out)
    if b"FortID{" in guess:
        log.success(f"recovered after {attempt} tries")
        print(guess.decode(errors="replace"))
        break
else:
    log.failure("no alignment yet, reconnect and run again")

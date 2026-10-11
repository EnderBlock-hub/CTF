<?php

declare(strict_types=1);

final class MigratedProfile
{
    public $displayName = 'guest';

    public function __toString(): string
    {
        return (string) $this->displayName;
    }
}

final class LegacyTemplate
{
    public $template = 'welcome.txt';

    public function __toString(): string
    {
        if (strpos($this->template, '../')) {
            return '[invalid template]';
        }

        $path = __DIR__ . '/templates/' . $this->template;
        $contents = file_get_contents($path);

        return $contents === false ? '[missing template]' : $contents;
    }
}

function page_start(string $title): void
{
    $safeTitle = htmlspecialchars($title, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    echo '<!doctype html><html lang="en"><head><meta charset="utf-8">';
    echo '<meta name="viewport" content="width=device-width,initial-scale=1">';
    echo "<title>{$safeTitle}</title><link rel=\"stylesheet\" href=\"/style.css\">";
    echo '</head><body><main>';
}

function page_end(): void
{
    echo '</main></body></html>';
}

function fail_request(string $message, array $details = []): never
{
    http_response_code(403);
    page_start('Migration rejected');
    echo '<section class="result"><p class="eyebrow">Verification failure</p>';
    echo '<h2>Migration rejected</h2>';
    echo '<p class="error">' . htmlspecialchars($message, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . '</p>';

    foreach ($details as $label => $value) {
        echo '<p><code>' . htmlspecialchars((string) $label, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
        echo ': ' . htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . '</code></p>';
    }

    echo '<a class="button secondary" href="/">Start over</a></section>';
    page_end();
    exit;
}

function decode_base64url(string $input): string|false
{
    $input = strtr($input, '-_', '+/');
    $remainder = strlen($input) % 4;

    if ($remainder === 1) {
        return false;
    }

    if ($remainder !== 0) {
        $input .= str_repeat('=', 4 - $remainder);
    }

    return base64_decode($input, true);
}

if (isset($_GET['manual'])) {
    $manual = $_GET['manual'];

    if (!is_string($manual)) {
        fail_request('Invalid manual name');
    }

    if (str_contains($manual, 'php://') || str_contains($manual, '../')) {
        fail_request('Invalid manual name');
    }

    $manual = rawurldecode($manual);

    if (!str_ends_with($manual, '.php')) {
        fail_request('Only PHP manual pages can be loaded');
    }

    page_start('Operations manual');
    include $manual;
    page_end();
    exit;
}

if ($_GET === []) {
    page_start('Ultimative PHP migration');
    ?>
    <section class="shell">
        <p class="eyebrow">Ultimative Identity Platform · final migration</p>
        <h1>One request.<br>Zero exceptions.</h1>
        <p class="lead">
            Submit every legacy proof together. The gateway rejects partial
            migrations and preserves no state between attempts.
        </p>
        <div class="status-grid">
            <div><span>Legacy digest</span><strong>MD5 compatibility</strong></div>
            <div><span>Modern digest</span><strong>SHA-256 enabled</strong></div>
            <div><span>Profile format</span><strong>PHP portable object</strong></div>
            <div><span>Gateway mode</span><strong>Strict verification</strong></div>
        </div>
        <a class="button" href="/?manual=manual/operations.php">Read operations manual</a>
    </section>
    <?php
    page_end();
    exit;
}

$rawQuery = $_SERVER['QUERY_STRING'] ?? '';

if (str_contains(rawurldecode($rawQuery), 'access_level')) {
    fail_request('The access_level parameter is protected');
}

if (($_GET['access_level'] ?? '') !== 'administrator') {
    fail_request('Administrator access required');
}

$primary = $_GET['primary'] ?? null;
$backup = $_GET['backup'] ?? null;

if ($primary === null || $backup === null) {
    fail_request('Both recovery answers are required');
}

if (get_debug_type($primary) !== get_debug_type($backup)) {
    fail_request('Recovery answers must use the same format');
}

if ($primary === $backup) {
    fail_request('Recovery answers must be different');
}

$primaryMaterial = 'legacy-recovery:v1:' . $primary;
$backupMaterial = 'legacy-recovery:v1:' . $backup;

$primaryHash = hash('sha256', $primaryMaterial);
$backupHash = hash('sha256', $backupMaterial);

if (!hash_equals($primaryHash, $backupHash)) {
    fail_request('Recovery fingerprints do not match');
}

$code = $_GET['code'] ?? '';

if (!is_string($code) || strlen($code) > 64) {
    fail_request('Invalid migration code');
}

$material = 'ULTIMATIVE-PHP-2026:' . $code;
$legacyDigest = substr(hash('md5', $material), 0, 9);
$modernDigest = substr(hash('sha256', $material), 0, 9);

if (!($legacyDigest !== $modernDigest && $legacyDigest == $modernDigest)) {
    fail_request('The compatibility code was rejected', [
        'legacy' => $legacyDigest,
        'modern' => $modernDigest,
    ]);
}

$encodedProfile = $_GET['profile'] ?? '';

if (!is_string($encodedProfile)) {
    fail_request('Invalid profile encoding');
}

$serializedProfile = decode_base64url($encodedProfile);

if ($serializedProfile === false) {
    fail_request('Invalid profile encoding');
}

$profile = @unserialize($serializedProfile, [
    'allowed_classes' => [MigratedProfile::class, LegacyTemplate::class],
]);

if (!$profile instanceof MigratedProfile) {
    fail_request('Unsupported profile type');
}

page_start('Migration completed');
echo '<section class="result"><p class="eyebrow">Verification complete</p>';
echo '<h2>Profile imported</h2><p class="lead">Welcome to the modern identity platform.</p>';
echo '<p class="flag">' . htmlspecialchars((string) $profile, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . '</p>';
echo '</section>';
page_end();


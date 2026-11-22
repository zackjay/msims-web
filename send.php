<?php
declare(strict_types=1);

/*
 * Penghantar borang pertanyaan laman MSIMS.
 * Menerima POST dari borang di laman yang sama dan menghantar e-mel ke TO.
 */

const TO = 'inquiry@msims.tech';
const FROM = 'inquiry@msims.tech';
const MAX_PER_IP_PER_HOUR = 5;
const MAX_TOTAL_PER_HOUR = 60;

const SECTORS = [
    'Agriculture', 'Fisheries', 'Oil palm and commodities',
    'Maritime and ports', 'Construction', 'Off-road driving',
];
const TYPES = [
    'Simulator demo', 'System purchase', 'Exhibition rental',
    'Custom software development',
];

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

function out(int $code, array $body): void
{
    http_response_code($code);
    echo json_encode($body);
    exit;
}

/** Satu baris teks: buang aksara kawalan dan baris baharu, potong panjang. */
function line(string $key, int $max): string
{
    $v = (string)($_POST[$key] ?? '');
    $v = preg_replace('/[\x00-\x1F\x7F]+/u', ' ', $v) ?? '';
    return mb_substr(trim($v), 0, $max);
}

/** Teks berbilang baris: kekalkan baris baharu, buang aksara kawalan lain. */
function text(string $key, int $max): string
{
    $v = (string)($_POST[$key] ?? '');
    $v = str_replace(["\r\n", "\r"], "\n", $v);
    $v = preg_replace('/[\x00-\x09\x0B-\x1F\x7F]+/u', ' ', $v) ?? '';
    return mb_substr(trim($v), 0, $max);
}

/** Had kadar ringkas berasaskan fail. Pulangkan false jika had dilepasi. */
function allow(string $bucket, int $max): bool
{
    $file = sys_get_temp_dir() . '/msims_rl_' . hash('sha256', $bucket);
    $now = time();
    $fh = @fopen($file, 'c+');
    if ($fh === false) {
        return true;
    }
    flock($fh, LOCK_EX);
    $raw = stream_get_contents($fh);
    $hits = array_values(array_filter(
        array_map('intval', $raw === '' || $raw === false ? [] : explode(',', $raw)),
        static fn (int $t): bool => $t > $now - 3600
    ));
    $ok = count($hits) < $max;
    if ($ok) {
        $hits[] = $now;
    }
    ftruncate($fh, 0);
    rewind($fh);
    fwrite($fh, implode(',', $hits));
    flock($fh, LOCK_UN);
    fclose($fh);
    return $ok;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    out(405, ['ok' => false, 'error' => 'method']);
}

// Hanya terima dari laman ini sendiri.
$host = strtolower(preg_replace('/:\d+$/', '', (string)($_SERVER['HTTP_HOST'] ?? '')) ?? '');
$source = (string)($_SERVER['HTTP_ORIGIN'] ?? ($_SERVER['HTTP_REFERER'] ?? ''));
$sourceHost = strtolower((string)parse_url($source, PHP_URL_HOST));
if ($host === '' || $sourceHost === '' || $sourceHost !== $host) {
    out(403, ['ok' => false, 'error' => 'origin']);
}

// Tapis bot ringkas: skrip laman menghantar masa isian borang (ms).
// Permintaan tanpa nilai ini, atau yang terlalu pantas, ditolak.
$elapsed = (string)($_POST['elapsed'] ?? '');
if (!ctype_digit($elapsed) || (int)$elapsed < 1500) {
    out(422, ['ok' => false, 'error' => 'invalid']);
}

$name = line('name', 100);
$org = line('org', 140);
$email = line('email', 160);
$phone = line('phone', 40);
$sector = line('sector', 60);
$type = line('type', 60);
$lang = line('lang', 2) === 'ms' ? 'ms' : 'en';
$message = text('message', 3000);

if ($name === '' || filter_var($email, FILTER_VALIDATE_EMAIL) === false
    || !in_array($sector, SECTORS, true) || !in_array($type, TYPES, true)) {
    out(422, ['ok' => false, 'error' => 'invalid']);
}

$ip = (string)($_SERVER['REMOTE_ADDR'] ?? 'unknown');
if (!allow('ip:' . $ip, MAX_PER_IP_PER_HOUR) || !allow('all', MAX_TOTAL_PER_HOUR)) {
    header('Retry-After: 3600');
    out(429, ['ok' => false, 'error' => 'rate']);
}

$subject = '[msims.tech] ' . $type . ' · ' . $sector . ($org !== '' ? ' · ' . $org : '');
$body = implode("\n", [
    'New enquiry from the MSIMS website',
    '',
    'Name         : ' . $name,
    'Organisation : ' . ($org !== '' ? $org : '-'),
    'Email        : ' . $email,
    'Phone        : ' . ($phone !== '' ? $phone : '-'),
    'Sector       : ' . $sector,
    'Enquiry type : ' . $type,
    'Site language: ' . ($lang === 'ms' ? 'Bahasa Melayu' : 'English'),
    '',
    'Message:',
    $message !== '' ? $message : '-',
    '',
    '--',
    'Sent from ' . $host . ' on ' . gmdate('Y-m-d H:i') . ' UTC',
    'Reply to this email to answer ' . $name . ' directly.',
]);

$headers = implode("\r\n", [
    'From: MSIMS Website <' . FROM . '>',
    'Reply-To: ' . $email,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
]);

$sent = @mail(TO, mb_encode_mimeheader($subject, 'UTF-8', 'B', "\r\n"), $body, $headers, '-f' . FROM);

if (!$sent) {
    out(500, ['ok' => false, 'error' => 'send']);
}
out(200, ['ok' => true]);

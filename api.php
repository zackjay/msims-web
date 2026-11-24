<?php
// MSIMS - API penjana lesen (license.msims.tech).
// Pelayan TIDAK menyimpan kunci rahsia dalam bentuk terbuka dan tidak boleh menandatangani lesen:
// ia hanya menyimpan salinan kunci yang disulitkan dengan kata laluan pemilik, serta daftar lesen.
declare(strict_types=1);

const KUNCI_AWAM = '30cd0721020cb24125bde8673a55d446e196197ac124e8a88f581788cbaa1af5';
const HOS_DIBENAR = 'license.msims.tech';
const SESI_MAKS = 43200;          // 12 jam
const PENGAWAL = "<?php http_response_code(404); exit; ?>\n";
const AB32 = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const HASH_MULA = 'd09eba48ab9b9690a7de61053d49790eb7f20518f939455c50bc51eb022be7ad';   // SHA-256 token sekali guna untuk akaun sementara pertama

function hantar(int $kod, array $d): void
{
    http_response_code($kod);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    header('X-Robots-Tag: noindex, nofollow, noarchive, nosnippet');
    echo json_encode($d, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

// ---------- permintaan ----------
$hos = strtolower((string)($_SERVER['HTTP_HOST'] ?? ''));
$setempat = preg_match('/^(localhost|127\.0\.0\.1)(:\d+)?$/', $hos) === 1 && getenv('MSIMS_LESEN_UJI') === '1';
$https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');
if (!$setempat && $hos !== HOS_DIBENAR) hantar(400, ['ralat' => 'hos']);
if (!$setempat && !$https) hantar(400, ['ralat' => 'https']);
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') hantar(405, ['ralat' => 'kaedah']);
if (($_SERVER['HTTP_X_REQUESTED_WITH'] ?? '') !== 'msims-lesen') hantar(403, ['ralat' => 'asal']);
$asal = (string)($_SERVER['HTTP_ORIGIN'] ?? '');
if ($asal !== '' && $asal !== ($https ? 'https' : 'http') . '://' . $hos) hantar(403, ['ralat' => 'asal']);
if (!function_exists('sodium_crypto_sign_verify_detached')) hantar(500, ['ralat' => 'sodium']);

$mentah = file_get_contents('php://input', false, null, 0, 4 * 1024 * 1024);
$masuk = json_decode($mentah === false || $mentah === '' ? '{}' : $mentah, true);
if (!is_array($masuk)) hantar(400, ['ralat' => 'json']);
$aksi = (string)($_GET['a'] ?? '');

// ---------- storan (di luar public_html; setiap fail berpengawal supaya tidak boleh dibaca melalui web) ----------
function dir_data(): string
{
    static $d = null;
    if ($d !== null) return $d;
    $uji = getenv('MSIMS_LESEN_DATA');
    $akar = rtrim((string)($_SERVER['DOCUMENT_ROOT'] ?? __DIR__), '/');
    $calon = $uji ? [$uji] : [dirname($akar) . '/msims_lesen_data', __DIR__ . '/_data'];
    foreach ($calon as $c) {
        if ((is_dir($c) || @mkdir($c, 0700, true)) && is_writable($c)) {
            if (!is_file("$c/.htaccess")) @file_put_contents("$c/.htaccess", "<IfModule mod_authz_core.c>\nRequire all denied\n</IfModule>\n<IfModule !mod_authz_core.c>\nDeny from all\n</IfModule>\n");
            if (!is_dir("$c/sesi")) @mkdir("$c/sesi", 0700);
            return $d = $c;
        }
    }
    hantar(500, ['ralat' => 'storan']);
    return '';
}
function baca(string $n, $lalai)
{
    $p = dir_data() . "/$n.php";
    if (!is_file($p)) return $lalai;
    $s = @file_get_contents($p);
    if ($s === false || strlen($s) < strlen(PENGAWAL)) return $lalai;
    $j = json_decode(substr($s, strlen(PENGAWAL)), true);
    return is_array($j) ? $j : $lalai;
}
function tulis(string $n, array $d): void
{
    $p = dir_data() . "/$n.php";
    $t = dir_data() . "/$n." . bin2hex(random_bytes(6)) . '.tmp.php';
    if (@file_put_contents($t, PENGAWAL . json_encode($d, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), LOCK_EX) === false || !@rename($t, $p)) {
        @unlink($t);
        hantar(500, ['ralat' => 'storan']);
    }
}
function dengan_kunci(callable $f)
{
    $fp = fopen(dir_data() . '/kunci.lock', 'c');
    if ($fp === false) hantar(500, ['ralat' => 'storan']);
    flock($fp, LOCK_EX);
    try { return $f(); } finally { flock($fp, LOCK_UN); fclose($fp); }
}

// ---------- had cubaan ----------
function ip(): string { return substr((string)($_SERVER['REMOTE_ADDR'] ?? '?'), 0, 64); }
function had_semak(): void
{
    $h = baca('had', []); $kini = time();
    foreach ([ip(), '*'] as $k) {
        $hingga = (int)($h[$k]['kunci'] ?? 0);
        if ($hingga > $kini) hantar(429, ['ralat' => 'had', 'tunggu' => $hingga - $kini]);
    }
}
function had_gagal(): void
{
    dengan_kunci(function () {
        $h = baca('had', []); $kini = time();
        foreach ([[ip(), 8, 900], ['*', 40, 3600]] as $x) {
            $e = $h[$x[0]] ?? ['n' => 0, 't' => $kini, 'kunci' => 0];
            if ($kini - (int)$e['t'] > $x[2]) $e = ['n' => 0, 't' => $kini, 'kunci' => 0];
            $e['n']++;
            if ($e['n'] >= $x[1]) $e = ['n' => 0, 't' => $kini, 'kunci' => $kini + 900];
            $h[$x[0]] = $e;
        }
        foreach ($h as $k => $e) if ($k !== '*' && $kini - (int)$e['t'] > 7200 && (int)$e['kunci'] < $kini) unset($h[$k]);
        tulis('had', $h);
    });
}
function had_berjaya(): void
{
    dengan_kunci(function () { $h = baca('had', []); if (isset($h[ip()])) { unset($h[ip()]); tulis('had', $h); } });
}

// ---------- sesi ----------
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
ini_set('session.gc_maxlifetime', (string)SESI_MAKS);
session_save_path(dir_data() . '/sesi');
session_name('msimslesen');
session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'secure' => !$setempat, 'httponly' => true, 'samesite' => 'Strict']);
session_start();
function sudah_log(): bool { return isset($_SESSION['log']) && time() - (int)$_SESSION['log'] < SESI_MAKS; }
function wajib_log(): void { if (!sudah_log()) hantar(401, ['ralat' => 'sesi']); }

// ---------- pengesahan ----------
function b64($s) { $b = is_string($s) ? base64_decode($s, true) : false; return $b === false ? '' : $b; }
function blob_bersih($o)
{
    if (!is_array($o) || ($o['format'] ?? '') !== 'MSIMS-KUNCI-1' || isset($o['rahsia'])) return null;
    $awam = strtolower((string)($o['awam'] ?? ''));
    $e = $o['enc'] ?? null;
    if ($awam !== KUNCI_AWAM || !is_array($e)) return null;
    $iter = $e['iter'] ?? 0;
    if (!is_int($iter) || $iter < 100000 || $iter > 5000000) return null;
    if (strlen(b64($e['garam'] ?? '')) < 8 || strlen(b64($e['iv'] ?? '')) !== 12) return null;
    $data = b64($e['data'] ?? '');
    if (strlen($data) < 32 || strlen($data) > 128) return null;
    return ['format' => 'MSIMS-KUNCI-1', 'awam' => $awam,
        'enc' => ['garam' => (string)$e['garam'], 'iv' => (string)$e['iv'], 'iter' => $iter, 'data' => (string)$e['data']],
        'dicipta' => substr((string)($o['dicipta'] ?? ''), 0, 40)];
}
function b32_nyahkod(string $s): string
{
    $s = strtr(strtoupper($s), ['O' => '0', 'I' => '1', 'L' => '1', '-' => '', ' ' => '', "\r" => '', "\n" => '', "\t" => '']);
    $out = ''; $buf = 0; $bit = 0;
    for ($i = 0, $n = strlen($s); $i < $n; $i++) {
        $v = strpos(AB32, $s[$i]);
        if ($v === false) return '';
        $buf = (($buf << 5) | $v) & 0xFFFF; $bit += 5;
        if ($bit >= 8) { $out .= chr(($buf >> ($bit - 8)) & 0xFF); $bit -= 8; }
    }
    return $out;
}
function lesen_sah(string $kunci, string $id): bool
{
    if (strlen($kunci) > 260 || stripos($kunci, 'MSIMS-') !== 0) return false;
    $b = b32_nyahkod(substr($kunci, 6));
    if (strlen($b) < 89) return false;
    $d = substr($b, 0, 25); $tt = substr($b, 25, 64);
    if (strtoupper(bin2hex(substr($d, 13, 4))) !== $id) return false;
    return sodium_crypto_sign_verify_detached($tt, $d, hex2bin(KUNCI_AWAM));
}
function teks($v, int $n): string
{
    if (!is_scalar($v)) return '';
    $s = trim(preg_replace('/[\x00-\x1F\x7F]/u', ' ', (string)$v) ?? '');
    return function_exists('mb_substr') ? mb_substr($s, 0, $n) : substr($s, 0, $n);
}
function rekod_bersih($r)
{
    if (!is_array($r)) return null;
    $id = strtoupper(teks($r['id'] ?? '', 8));
    $kunci = strtoupper(teks($r['kunci'] ?? '', 260));
    if (!preg_match('/^[0-9A-F]{8}$/', $id) || !lesen_sah($kunci, $id)) return null;
    $jenis = strtoupper(teks($r['jenis'] ?? '', 12));
    return ['dijana' => teks($r['dijana'] ?? '', 40), 'produk' => strtoupper(teks($r['produk'] ?? '', 24)),
        'jenis' => in_array($jenis, ['KEKAL', 'TEMPOH', 'PERCUBAAN', 'TERSUAI'], true) ? $jenis : null,
        'pelanggan' => teks($r['pelanggan'] ?? '', 120), 'idMesin' => teks($r['idMesin'] ?? '', 24), 'tamat' => teks($r['tamat'] ?? '', 12),
        'had' => teks($r['had'] ?? '', 16), 'id' => $id, 'catatan' => teks($r['catatan'] ?? '', 200), 'kunci' => $kunci];
}

function nama_bersih($v)
{
    $n = strtolower(trim(is_string($v) ? $v : ''));
    return preg_match('/^[a-z0-9._-]{3,32}$/', $n) ? $n : null;
}
function rahsia_pelayan(): string   // untuk garam olok-olok, supaya nama pengguna tidak boleh diteka melalui API
{
    return dengan_kunci(function () {
        $r = baca('rahsia', null);
        if (!is_array($r) || strlen(b64($r['k'] ?? '')) !== 32) { $r = ['k' => base64_encode(random_bytes(32))]; tulis('rahsia', $r); }
        return b64($r['k']);
    });
}

// ---------- tindakan ----------
if ($aksi === 'status') {
    hantar(200, ['ok' => true, 'log' => sudah_log()]);
}
if ($aksi === 'pra') {      // garam pengesahan bagi nama pengguna (garam olok-olok yang tetap jika nama tidak wujud)
    had_semak();
    $nama = nama_bersih($masuk['nama'] ?? null);
    if ($nama === null) hantar(422, ['ralat' => 'nama']);
    $a = baca('akaun', null);
    $garam = (is_array($a) && hash_equals((string)($a['nama'] ?? ''), $nama))
        ? (string)$a['garam']
        : base64_encode(substr(hash_hmac('sha256', 'garam|' . $nama, rahsia_pelayan(), true), 0, 16));
    hantar(200, ['ok' => true, 'garam' => $garam]);
}
if ($aksi === 'mula') {     // akaun sementara pertama: hanya apabila belum ada akaun, dan hanya dengan token sekali guna
    had_semak();
    $nama = nama_bersih($masuk['nama'] ?? null); $auth = (string)($masuk['auth'] ?? ''); $garam = (string)($masuk['garam'] ?? '');
    if (!hash_equals(HASH_MULA, hash('sha256', (string)($masuk['token'] ?? '')))) { had_gagal(); hantar(403, ['ralat' => 'token']); }
    if ($nama === null || !preg_match('/^[0-9a-f]{64}$/', $auth) || strlen(b64($garam)) !== 16) hantar(422, ['ralat' => 'data']);
    $ok = dengan_kunci(function () use ($nama, $garam, $auth) {
        if (baca('akaun', null) !== null) return false;
        tulis('akaun', ['v' => 2, 'nama' => $nama, 'garam' => $garam, 'hash' => password_hash($auth, PASSWORD_DEFAULT), 'blob' => null, 'sementara' => true, 'dikemas' => gmdate('c')]);
        return true;
    });
    if (!$ok) hantar(409, ['ralat' => 'sudah']);
    hantar(200, ['ok' => true]);
}
if ($aksi === 'cabaran') {
    had_semak();
    $n = base64_encode(random_bytes(32));
    $_SESSION['cabaran'] = ['n' => $n, 't' => time()];
    hantar(200, ['ok' => true, 'nonce' => $n]);
}
if ($aksi === 'sedia') {   // tetapkan / tukar nama pengguna & kata laluan: hanya pemegang kunci rahsia boleh (tandatangan cabaran)
    had_semak();
    $c = $_SESSION['cabaran'] ?? null; unset($_SESSION['cabaran']);
    $nonce = (string)($masuk['nonce'] ?? ''); $auth = (string)($masuk['auth'] ?? ''); $garam = (string)($masuk['garam'] ?? '');
    $nama = nama_bersih($masuk['nama'] ?? null);
    $blob = blob_bersih($masuk['blob'] ?? null); $tt = b64($masuk['tandatangan'] ?? '');
    if (!is_array($c) || !hash_equals((string)$c['n'], $nonce) || time() - (int)$c['t'] > 300) hantar(400, ['ralat' => 'cabaran']);
    if ($nama === null) hantar(422, ['ralat' => 'nama']);
    if ($blob === null || !preg_match('/^[0-9a-f]{64}$/', $auth) || strlen(b64($garam)) !== 16 || strlen($tt) !== 64) hantar(422, ['ralat' => 'data']);
    $mesej = "MSIMS-LESEN-SEDIA\n$nonce\n$nama\n$auth\n" . $blob['enc']['data'];
    if (!sodium_crypto_sign_verify_detached($tt, $mesej, hex2bin(KUNCI_AWAM))) { had_gagal(); hantar(403, ['ralat' => 'tandatangan']); }
    dengan_kunci(function () use ($nama, $garam, $auth, $blob) {
        tulis('akaun', ['v' => 2, 'nama' => $nama, 'garam' => $garam, 'hash' => password_hash($auth, PASSWORD_DEFAULT), 'blob' => $blob, 'sementara' => false, 'dikemas' => gmdate('c')]);
    });
    had_berjaya();
    session_regenerate_id(true);
    $_SESSION['log'] = time();
    hantar(200, ['ok' => true]);
}
if ($aksi === 'masuk') {
    had_semak();
    $a = baca('akaun', null);
    $nama = nama_bersih($masuk['nama'] ?? null); $auth = (string)($masuk['auth'] ?? '');
    $sah = is_array($a) && $nama !== null && preg_match('/^[0-9a-f]{64}$/', $auth) === 1;
    $namaOk = $sah && hash_equals((string)($a['nama'] ?? ''), $nama);
    // sentiasa jalankan semakan hash supaya masa jawapan tidak mendedahkan sama ada nama pengguna wujud
    $laluanOk = password_verify($sah ? $auth : 'x', is_array($a) ? (string)$a['hash'] : '$2y$10$abcdefghijklmnopqrstuuJ8Gq0s2iZQ9o1b8XvG0rXqkq7p0V1y2');
    if (!$namaOk || !$laluanOk) { had_gagal(); hantar(401, ['ralat' => 'laluan']); }
    had_berjaya();
    session_regenerate_id(true);
    $_SESSION['log'] = time();
    hantar(200, ['ok' => true, 'nama' => $a['nama'], 'blob' => $a['blob'] ?? null, 'sementara' => !empty($a['sementara'])]);
}
if ($aksi === 'keluar') {
    $_SESSION = [];
    session_destroy();
    hantar(200, ['ok' => true]);
}
if ($aksi === 'daftar') {
    wajib_log();
    hantar(200, ['ok' => true, 'rekod' => array_values(baca('daftar', []))]);
}
if ($aksi === 'tambah') {   // satu rekod atau beberapa (pulih sandaran); hanya lesen bertandatangan sah diterima
    wajib_log();
    $senarai = $masuk['rekod'] ?? null;
    if (is_array($senarai) && isset($senarai['id'])) $senarai = [$senarai];
    if (!is_array($senarai) || count($senarai) > 5000) hantar(422, ['ralat' => 'data']);
    $baru = [];
    foreach ($senarai as $r) { $b = rekod_bersih($r); if ($b !== null) $baru[$b['id']] = $b; }
    if (!$baru) hantar(422, ['ralat' => 'data']);
    $tambah = dengan_kunci(function () use ($baru) {
        $d = baca('daftar', []); $ada = []; $n = 0;
        foreach ($d as $r) $ada[$r['id']] = true;
        foreach ($baru as $id => $r) if (!isset($ada[$id])) { array_unshift($d, $r); $n++; }
        if ($n) tulis('daftar', array_slice($d, 0, 50000));
        return $n;
    });
    hantar(200, ['ok' => true, 'tambah' => $tambah, 'diterima' => count($baru)]);
}
hantar(404, ['ralat' => 'aksi']);

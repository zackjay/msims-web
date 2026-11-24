/*! noble-ed25519 - MIT License (c) 2019 Paul Miller (paulmillr.com) */
/**
 * 4KB JS implementation of ed25519 EdDSA signatures.
 * Compliant with RFC8032, FIPS 186-5 & ZIP215.
 * @module
 * @example
 * ```js
import * as ed from '@noble/ed25519';
(async () => {
  const privKey = ed.utils.randomPrivateKey();
  const message = Uint8Array.from([0xab, 0xbc, 0xcd, 0xde]);
  const pubKey = await ed.getPublicKeyAsync(privKey); // Sync methods are also present
  const signature = await ed.signAsync(message, privKey);
  const isValid = await ed.verifyAsync(signature, message, pubKey);
})();
```
 */
/**
 * Curve params. ed25519 is twisted edwards curve. Equation is −x² + y² = -a + dx²y².
 * * P = `2n**255n - 19n` // field over which calculations are done
 * * N = `2n**252n + 27742317777372353535851937790883648493n` // group order, amount of curve points
 * * h = 8 // cofactor
 * * a = `Fp.create(BigInt(-1))` // equation param
 * * d = -121665/121666 a.k.a. `Fp.neg(121665 * Fp.inv(121666))` // equation param
 * * Gx, Gy are coordinates of Generator / base point
 */
const ed25519_CURVE = {
    p: 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffedn,
    n: 0x1000000000000000000000000000000014def9dea2f79cd65812631a5cf5d3edn,
    h: 8n,
    a: 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffecn,
    d: 0x52036cee2b6ffe738cc740797779e89800700a4d4141d8ab75eb4dca135978a3n,
    Gx: 0x216936d3cd6e53fec0a4e231fdd6dc5c692cc7609525a7b2c9562d608f25d51an,
    Gy: 0x6666666666666666666666666666666666666666666666666666666666666658n,
};
const { p: P, n: N, Gx, Gy, a: _a, d: _d } = ed25519_CURVE;
const h = 8n; // cofactor
const L = 32; // field / group byte length
const L2 = 64;
// Helpers and Precomputes sections are reused between libraries
// ## Helpers
// ----------
// error helper, messes-up stack trace
const err = (m = '') => {
    throw new Error(m);
};
const isBig = (n) => typeof n === 'bigint'; // is big integer
const isStr = (s) => typeof s === 'string'; // is string
const isBytes = (a) => a instanceof Uint8Array || (ArrayBuffer.isView(a) && a.constructor.name === 'Uint8Array');
/** assert is Uint8Array (of specific length) */
const abytes = (a, l) => !isBytes(a) || (typeof l === 'number' && l > 0 && a.length !== l)
    ? err('Uint8Array expected')
    : a;
/** create Uint8Array */
const u8n = (len) => new Uint8Array(len);
const u8fr = (buf) => Uint8Array.from(buf);
const padh = (n, pad) => n.toString(16).padStart(pad, '0');
const bytesToHex = (b) => Array.from(abytes(b))
    .map((e) => padh(e, 2))
    .join('');
const C = { _0: 48, _9: 57, A: 65, F: 70, a: 97, f: 102 }; // ASCII characters
const _ch = (ch) => {
    if (ch >= C._0 && ch <= C._9)
        return ch - C._0; // '2' => 50-48
    if (ch >= C.A && ch <= C.F)
        return ch - (C.A - 10); // 'B' => 66-(65-10)
    if (ch >= C.a && ch <= C.f)
        return ch - (C.a - 10); // 'b' => 98-(97-10)
    return;
};
const hexToBytes = (hex) => {
    const e = 'hex invalid';
    if (!isStr(hex))
        return err(e);
    const hl = hex.length;
    const al = hl / 2;
    if (hl % 2)
        return err(e);
    const array = u8n(al);
    for (let ai = 0, hi = 0; ai < al; ai++, hi += 2) {
        // treat each char as ASCII
        const n1 = _ch(hex.charCodeAt(hi)); // parse first char, multiply it by 16
        const n2 = _ch(hex.charCodeAt(hi + 1)); // parse second char
        if (n1 === undefined || n2 === undefined)
            return err(e);
        array[ai] = n1 * 16 + n2; // example: 'A9' => 10*16 + 9
    }
    return array;
};
/** normalize hex or ui8a to ui8a */
const toU8 = (a, len) => abytes(isStr(a) ? hexToBytes(a) : u8fr(abytes(a)), len);
const cr = () => globalThis?.crypto; // WebCrypto is available in all modern environments
const subtle = () => cr()?.subtle ?? err('crypto.subtle must be defined');
// prettier-ignore
const concatBytes = (...arrs) => {
    const r = u8n(arrs.reduce((sum, a) => sum + abytes(a).length, 0)); // create u8a of summed length
    let pad = 0; // walk through each array,
    arrs.forEach(a => { r.set(a, pad); pad += a.length; }); // ensure they have proper type
    return r;
};
/** WebCrypto OS-level CSPRNG (random number generator). Will throw when not available. */
const randomBytes = (len = L) => {
    const c = cr();
    return c.getRandomValues(u8n(len));
};
const big = BigInt;
const arange = (n, min, max, msg = 'bad number: out of range') => isBig(n) && min <= n && n < max ? n : err(msg);
/** modular division */
const M = (a, b = P) => {
    const r = a % b;
    return r >= 0n ? r : b + r;
};
const modN = (a) => M(a, N);
/** Modular inversion using eucledian GCD (non-CT). No negative exponent for now. */
// prettier-ignore
const invert = (num, md) => {
    if (num === 0n || md <= 0n)
        err('no inverse n=' + num + ' mod=' + md);
    let a = M(num, md), b = md, x = 0n, y = 1n, u = 1n, v = 0n;
    while (a !== 0n) {
        const q = b / a, r = b % a;
        const m = x - u * q, n = y - v * q;
        b = a, a = r, x = u, y = v, u = m, v = n;
    }
    return b === 1n ? M(x, md) : err('no inverse'); // b is gcd at this point
};
const callHash = (name) => {
    // @ts-ignore
    const fn = etc[name];
    if (typeof fn !== 'function')
        err('hashes.' + name + ' not set');
    return fn;
};
const apoint = (p) => (p instanceof Point ? p : err('Point expected'));
// ## End of Helpers
// -----------------
const B256 = 2n ** 256n;
/** Point in XYZT extended coordinates. */
class Point {
    static BASE;
    static ZERO;
    ex;
    ey;
    ez;
    et;
    constructor(ex, ey, ez, et) {
        const max = B256;
        this.ex = arange(ex, 0n, max);
        this.ey = arange(ey, 0n, max);
        this.ez = arange(ez, 1n, max);
        this.et = arange(et, 0n, max);
        Object.freeze(this);
    }
    static fromAffine(p) {
        return new Point(p.x, p.y, 1n, M(p.x * p.y));
    }
    /** RFC8032 5.1.3: Uint8Array to Point. */
    static fromBytes(hex, zip215 = false) {
        const d = _d;
        // Copy array to not mess it up.
        const normed = u8fr(abytes(hex, L));
        // adjust first LE byte = last BE byte
        const lastByte = hex[31];
        normed[31] = lastByte & ~0x80;
        const y = bytesToNumLE(normed);
        // zip215=true:           0 <= y < 2^256
        // zip215=false, RFC8032: 0 <= y < 2^255-19
        const max = zip215 ? B256 : P;
        arange(y, 0n, max);
        const y2 = M(y * y); // y²
        const u = M(y2 - 1n); // u=y²-1
        const v = M(d * y2 + 1n); // v=dy²+1
        let { isValid, value: x } = uvRatio(u, v); // (uv³)(uv⁷)^(p-5)/8; square root
        if (!isValid)
            err('bad point: y not sqrt'); // not square root: bad point
        const isXOdd = (x & 1n) === 1n; // adjust sign of x coordinate
        const isLastByteOdd = (lastByte & 0x80) !== 0; // x_0, last bit
        if (!zip215 && x === 0n && isLastByteOdd)
            err('bad point: x==0, isLastByteOdd'); // x=0, x_0=1
        if (isLastByteOdd !== isXOdd)
            x = M(-x);
        return new Point(x, y, 1n, M(x * y)); // Z=1, T=xy
    }
    /** Checks if the point is valid and on-curve. */
    assertValidity() {
        const a = _a;
        const d = _d;
        const p = this;
        if (p.is0())
            throw new Error('bad point: ZERO'); // TODO: optimize, with vars below?
        // Equation in affine coordinates: ax² + y² = 1 + dx²y²
        // Equation in projective coordinates (X/Z, Y/Z, Z):  (aX² + Y²)Z² = Z⁴ + dX²Y²
        const { ex: X, ey: Y, ez: Z, et: T } = p;
        const X2 = M(X * X); // X²
        const Y2 = M(Y * Y); // Y²
        const Z2 = M(Z * Z); // Z²
        const Z4 = M(Z2 * Z2); // Z⁴
        const aX2 = M(X2 * a); // aX²
        const left = M(Z2 * M(aX2 + Y2)); // (aX² + Y²)Z²
        const right = M(Z4 + M(d * M(X2 * Y2))); // Z⁴ + dX²Y²
        if (left !== right)
            throw new Error('bad point: equation left != right (1)');
        // In Extended coordinates we also have T, which is x*y=T/Z: check X*Y == Z*T
        const XY = M(X * Y);
        const ZT = M(Z * T);
        if (XY !== ZT)
            throw new Error('bad point: equation left != right (2)');
        return this;
    }
    /** Equality check: compare points P&Q. */
    equals(other) {
        const { ex: X1, ey: Y1, ez: Z1 } = this;
        const { ex: X2, ey: Y2, ez: Z2 } = apoint(other); // checks class equality
        const X1Z2 = M(X1 * Z2);
        const X2Z1 = M(X2 * Z1);
        const Y1Z2 = M(Y1 * Z2);
        const Y2Z1 = M(Y2 * Z1);
        return X1Z2 === X2Z1 && Y1Z2 === Y2Z1;
    }
    is0() {
        return this.equals(I);
    }
    /** Flip point over y coordinate. */
    negate() {
        return new Point(M(-this.ex), this.ey, this.ez, M(-this.et));
    }
    /** Point doubling. Complete formula. Cost: `4M + 4S + 1*a + 6add + 1*2`. */
    double() {
        const { ex: X1, ey: Y1, ez: Z1 } = this;
        const a = _a;
        // https://hyperelliptic.org/EFD/g1p/auto-twisted-extended.html#doubling-dbl-2008-hwcd
        const A = M(X1 * X1);
        const B = M(Y1 * Y1);
        const C = M(2n * M(Z1 * Z1));
        const D = M(a * A);
        const x1y1 = X1 + Y1;
        const E = M(M(x1y1 * x1y1) - A - B);
        const G = D + B;
        const F = G - C;
        const H = D - B;
        const X3 = M(E * F);
        const Y3 = M(G * H);
        const T3 = M(E * H);
        const Z3 = M(F * G);
        return new Point(X3, Y3, Z3, T3);
    }
    /** Point addition. Complete formula. Cost: `8M + 1*k + 8add + 1*2`. */
    add(other) {
        const { ex: X1, ey: Y1, ez: Z1, et: T1 } = this;
        const { ex: X2, ey: Y2, ez: Z2, et: T2 } = apoint(other); // doesn't check if other on-curve
        const a = _a;
        const d = _d;
        // https://hyperelliptic.org/EFD/g1p/auto-twisted-extended-1.html#addition-add-2008-hwcd-3
        const A = M(X1 * X2);
        const B = M(Y1 * Y2);
        const C = M(T1 * d * T2);
        const D = M(Z1 * Z2);
        const E = M((X1 + Y1) * (X2 + Y2) - A - B);
        const F = M(D - C);
        const G = M(D + C);
        const H = M(B - a * A);
        const X3 = M(E * F);
        const Y3 = M(G * H);
        const T3 = M(E * H);
        const Z3 = M(F * G);
        return new Point(X3, Y3, Z3, T3);
    }
    /**
     * Point-by-scalar multiplication. Scalar must be in range 1 <= n < CURVE.n.
     * Uses {@link wNAF} for base point.
     * Uses fake point to mitigate side-channel leakage.
     * @param n scalar by which point is multiplied
     * @param safe safe mode guards against timing attacks; unsafe mode is faster
     */
    multiply(n, safe = true) {
        if (!safe && (n === 0n || this.is0()))
            return I;
        arange(n, 1n, N);
        if (n === 1n)
            return this;
        if (this.equals(G))
            return wNAF(n).p;
        // init result point & fake point
        let p = I;
        let f = G;
        for (let d = this; n > 0n; d = d.double(), n >>= 1n) {
            // if bit is present, add to point
            // if not present, add to fake, for timing safety
            if (n & 1n)
                p = p.add(d);
            else if (safe)
                f = f.add(d);
        }
        return p;
    }
    /** Convert point to 2d xy affine point. (X, Y, Z) ∋ (x=X/Z, y=Y/Z) */
    toAffine() {
        const { ex: x, ey: y, ez: z } = this;
        // fast-paths for ZERO point OR Z=1
        if (this.equals(I))
            return { x: 0n, y: 1n };
        const iz = invert(z, P);
        // (Z * Z^-1) must be 1, otherwise bad math
        if (M(z * iz) !== 1n)
            err('invalid inverse');
        // x = X*Z^-1; y = Y*Z^-1
        return { x: M(x * iz), y: M(y * iz) };
    }
    toBytes() {
        const { x, y } = this.assertValidity().toAffine();
        const b = numTo32bLE(y);
        // store sign in first LE byte
        b[31] |= x & 1n ? 0x80 : 0;
        return b;
    }
    toHex() {
        return bytesToHex(this.toBytes());
    } // encode to hex string
    clearCofactor() {
        return this.multiply(big(h), false);
    }
    isSmallOrder() {
        return this.clearCofactor().is0();
    }
    isTorsionFree() {
        // multiply by big number CURVE.n
        let p = this.multiply(N / 2n, false).double(); // ensures the point is not "bad".
        if (N % 2n)
            p = p.add(this); // P^(N+1) // P*N == (P*(N/2))*2+P
        return p.is0();
    }
    static fromHex(hex, zip215) {
        return Point.fromBytes(toU8(hex), zip215);
    }
    get x() {
        return this.toAffine().x;
    }
    get y() {
        return this.toAffine().y;
    }
    toRawBytes() {
        return this.toBytes();
    }
}
/** Generator / base point */
const G = new Point(Gx, Gy, 1n, M(Gx * Gy));
/** Identity / zero point */
const I = new Point(0n, 1n, 1n, 0n);
// Static aliases
Point.BASE = G;
Point.ZERO = I;
const numTo32bLE = (num) => hexToBytes(padh(arange(num, 0n, B256), L2)).reverse();
const bytesToNumLE = (b) => big('0x' + bytesToHex(u8fr(abytes(b)).reverse()));
const pow2 = (x, power) => {
    // pow2(x, 4) == x^(2^4)
    let r = x;
    while (power-- > 0n) {
        r *= r;
        r %= P;
    }
    return r;
};
// prettier-ignore
const pow_2_252_3 = (x) => {
    const x2 = (x * x) % P; // x^2,       bits 1
    const b2 = (x2 * x) % P; // x^3,       bits 11
    const b4 = (pow2(b2, 2n) * b2) % P; // x^(2^4-1), bits 1111
    const b5 = (pow2(b4, 1n) * x) % P; // x^(2^5-1), bits 11111
    const b10 = (pow2(b5, 5n) * b5) % P; // x^(2^10)
    const b20 = (pow2(b10, 10n) * b10) % P; // x^(2^20)
    const b40 = (pow2(b20, 20n) * b20) % P; // x^(2^40)
    const b80 = (pow2(b40, 40n) * b40) % P; // x^(2^80)
    const b160 = (pow2(b80, 80n) * b80) % P; // x^(2^160)
    const b240 = (pow2(b160, 80n) * b80) % P; // x^(2^240)
    const b250 = (pow2(b240, 10n) * b10) % P; // x^(2^250)
    const pow_p_5_8 = (pow2(b250, 2n) * x) % P; // < To pow to (p+3)/8, multiply it by x.
    return { pow_p_5_8, b2 };
};
const RM1 = 0x2b8324804fc1df0b2b4d00993dfbd7a72f431806ad2fe478c4ee1b274a0ea0b0n; // √-1
// for sqrt comp
// prettier-ignore
const uvRatio = (u, v) => {
    const v3 = M(v * v * v); // v³
    const v7 = M(v3 * v3 * v); // v⁷
    const pow = pow_2_252_3(u * v7).pow_p_5_8; // (uv⁷)^(p-5)/8
    let x = M(u * v3 * pow); // (uv³)(uv⁷)^(p-5)/8
    const vx2 = M(v * x * x); // vx²
    const root1 = x; // First root candidate
    const root2 = M(x * RM1); // Second root candidate; RM1 is √-1
    const useRoot1 = vx2 === u; // If vx² = u (mod p), x is a square root
    const useRoot2 = vx2 === M(-u); // If vx² = -u, set x <-- x * 2^((p-1)/4)
    const noRoot = vx2 === M(-u * RM1); // There is no valid root, vx² = -u√-1
    if (useRoot1)
        x = root1;
    if (useRoot2 || noRoot)
        x = root2; // We return root2 anyway, for const-time
    if ((M(x) & 1n) === 1n)
        x = M(-x); // edIsNegative
    return { isValid: useRoot1 || useRoot2, value: x };
};
// N == L, just weird naming
const modL_LE = (hash) => modN(bytesToNumLE(hash)); // modulo L; but little-endian
const sha512a = (...m) => etc.sha512Async(...m); // Async SHA512
const sha512s = (...m) => callHash('sha512Sync')(...m);
// RFC8032 5.1.5
const hash2extK = (hashed) => {
    // slice creates a copy, unlike subarray
    const head = hashed.slice(0, L);
    head[0] &= 248; // Clamp bits: 0b1111_1000
    head[31] &= 127; // 0b0111_1111
    head[31] |= 64; // 0b0100_0000
    const prefix = hashed.slice(L, L2); // private key "prefix"
    const scalar = modL_LE(head); // modular division over curve order
    const point = G.multiply(scalar); // public key point
    const pointBytes = point.toBytes(); // point serialized to Uint8Array
    return { head, prefix, scalar, point, pointBytes };
};
// RFC8032 5.1.5; getPublicKey async, sync. Hash priv key and extract point.
const getExtendedPublicKeyAsync = (priv) => sha512a(toU8(priv, L)).then(hash2extK);
const getExtendedPublicKey = (priv) => hash2extK(sha512s(toU8(priv, L)));
/** Creates 32-byte ed25519 public key from 32-byte private key. Async. */
const getPublicKeyAsync = (priv) => getExtendedPublicKeyAsync(priv).then((p) => p.pointBytes);
/** Creates 32-byte ed25519 public key from 32-byte private key. To use, set `etc.sha512Sync` first. */
const getPublicKey = (priv) => getExtendedPublicKey(priv).pointBytes;
const hashFinishA = (res) => sha512a(res.hashable).then(res.finish);
const hashFinishS = (res) => res.finish(sha512s(res.hashable));
const _sign = (e, rBytes, msg) => {
    // sign() shared code
    const { pointBytes: P, scalar: s } = e;
    const r = modL_LE(rBytes); // r was created outside, reduce it modulo L
    const R = G.multiply(r).toBytes(); // R = [r]B
    const hashable = concatBytes(R, P, msg); // dom2(F, C) || R || A || PH(M)
    const finish = (hashed) => {
        // k = SHA512(dom2(F, C) || R || A || PH(M))
        const S = modN(r + modL_LE(hashed) * s); // S = (r + k * s) mod L; 0 <= s < l
        return abytes(concatBytes(R, numTo32bLE(S)), L2); // 64-byte sig: 32b R.x + 32b LE(S)
    };
    return { hashable, finish };
};
/**
 * Signs message (NOT message hash) using private key. Async.
 * Follows RFC8032 5.1.6.
 */
const signAsync = async (msg, privKey) => {
    const m = toU8(msg);
    const e = await getExtendedPublicKeyAsync(privKey);
    const rBytes = await sha512a(e.prefix, m); // r = SHA512(dom2(F, C) || prefix || PH(M))
    return hashFinishA(_sign(e, rBytes, m)); // gen R, k, S, then 64-byte signature
};
/**
 * Signs message (NOT message hash) using private key. To use, set `hashes.sha512` first.
 * Follows RFC8032 5.1.6.
 */
const sign = (msg, privKey) => {
    const m = toU8(msg);
    const e = getExtendedPublicKey(privKey);
    const rBytes = sha512s(e.prefix, m); // r = SHA512(dom2(F, C) || prefix || PH(M))
    return hashFinishS(_sign(e, rBytes, m)); // gen R, k, S, then 64-byte signature
};
const veriOpts = { zip215: true };
const _verify = (sig, msg, pub, opts = veriOpts) => {
    sig = toU8(sig, L2); // Signature hex str/Bytes, must be 64 bytes
    msg = toU8(msg); // Message hex str/Bytes
    pub = toU8(pub, L);
    const { zip215 } = opts; // switch between zip215 and rfc8032 verif
    let A;
    let R;
    let s;
    let SB;
    let hashable = Uint8Array.of();
    try {
        A = Point.fromHex(pub, zip215); // public key A decoded
        R = Point.fromHex(sig.slice(0, L), zip215); // 0 <= R < 2^256: ZIP215 R can be >= P
        s = bytesToNumLE(sig.slice(L, L2)); // Decode second half as an integer S
        SB = G.multiply(s, false); // in the range 0 <= s < L
        hashable = concatBytes(R.toBytes(), A.toBytes(), msg); // dom2(F, C) || R || A || PH(M)
    }
    catch (error) { }
    const finish = (hashed) => {
        // k = SHA512(dom2(F, C) || R || A || PH(M))
        if (SB == null)
            return false; // false if try-catch catched an error
        if (!zip215 && A.isSmallOrder())
            return false; // false for SBS: Strongly Binding Signature
        const k = modL_LE(hashed); // decode in little-endian, modulo L
        const RkA = R.add(A.multiply(k, false)); // [8]R + [8][k]A'
        return RkA.add(SB.negate()).clearCofactor().is0(); // [8][S]B = [8]R + [8][k]A'
    };
    return { hashable, finish };
};
/** Verifies signature on message and public key. Async. Follows RFC8032 5.1.7. */
const verifyAsync = async (s, m, p, opts = veriOpts) => hashFinishA(_verify(s, m, p, opts));
/** Verifies signature on message and public key. To use, set `hashes.sha512` first. Follows RFC8032 5.1.7. */
const verify = (s, m, p, opts = veriOpts) => hashFinishS(_verify(s, m, p, opts));
/** Math, hex, byte helpers. Not in `utils` because utils share API with noble-curves. */
const etc = {
    sha512Async: async (...messages) => {
        const s = subtle();
        const m = concatBytes(...messages);
        return u8n(await s.digest('SHA-512', m.buffer));
    },
    sha512Sync: undefined,
    bytesToHex: bytesToHex,
    hexToBytes: hexToBytes,
    concatBytes: concatBytes,
    mod: M,
    invert: invert,
    randomBytes: randomBytes,
};
/** ed25519-specific key utilities. */
const utils = {
    getExtendedPublicKeyAsync: getExtendedPublicKeyAsync,
    getExtendedPublicKey: getExtendedPublicKey,
    randomPrivateKey: () => randomBytes(L),
    precompute: (w = 8, p = G) => {
        p.multiply(3n);
        w;
        return p;
    }, // no-op
};
// ## Precomputes
// --------------
const W = 8; // W is window size
const scalarBits = 256;
const pwindows = Math.ceil(scalarBits / W) + 1; // 33 for W=8
const pwindowSize = 2 ** (W - 1); // 128 for W=8
const precompute = () => {
    const points = [];
    let p = G;
    let b = p;
    for (let w = 0; w < pwindows; w++) {
        b = p;
        points.push(b);
        for (let i = 1; i < pwindowSize; i++) {
            b = b.add(p);
            points.push(b);
        } // i=1, bc we skip 0
        p = b.double();
    }
    return points;
};
let Gpows = undefined; // precomputes for base point G
// const-time negate
const ctneg = (cnd, p) => {
    const n = p.negate();
    return cnd ? n : p;
};
/**
 * Precomputes give 12x faster getPublicKey(), 10x sign(), 2x verify() by
 * caching multiples of G (base point). Cache is stored in 32MB of RAM.
 * Any time `G.multiply` is done, precomputes are used.
 * Not used for getSharedSecret, which instead multiplies random pubkey `P.multiply`.
 *
 * w-ary non-adjacent form (wNAF) precomputation method is 10% slower than windowed method,
 * but takes 2x less RAM. RAM reduction is possible by utilizing `.subtract`.
 *
 * !! Precomputes can be disabled by commenting-out call of the wNAF() inside Point#multiply().
 */
const wNAF = (n) => {
    const comp = Gpows || (Gpows = precompute());
    let p = I;
    let f = G; // f must be G, or could become I in the end
    const pow_2_w = 2 ** W; // 256 for W=8
    const maxNum = pow_2_w; // 256 for W=8
    const mask = big(pow_2_w - 1); // 255 for W=8 == mask 0b11111111
    const shiftBy = big(W); // 8 for W=8
    for (let w = 0; w < pwindows; w++) {
        let wbits = Number(n & mask); // extract W bits.
        n >>= shiftBy; // shift number by W bits.
        if (wbits > pwindowSize) {
            wbits -= maxNum;
            n += 1n;
        } // split if bits > max: +224 => 256-32
        const off = w * pwindowSize;
        const offF = off; // offsets, evaluate both
        const offP = off + Math.abs(wbits) - 1;
        const isEven = w % 2 !== 0; // conditions, evaluate both
        const isNeg = wbits < 0;
        if (wbits === 0) {
            // off == I: can't add it. Adding random offF instead.
            f = f.add(ctneg(isEven, comp[offF])); // bits are 0: add garbage to fake point
        }
        else {
            p = p.add(ctneg(isNeg, comp[offP])); // bits are 1: add to result point
        }
    }
    return { p, f }; // return both real and fake points for JIT
};
// !! Remove the export to easily use in REPL / browser console

const ed = { getPublicKeyAsync, signAsync, verifyAsync, utils };

// ===================== Penjana Lesen MSIMS =====================
const $ = id => document.getElementById(id);
const AB = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const HARI_EPOCH = 19723;                 // 2024-01-01 dalam hari Unix (sama dengan LesenTeras.h)
const TIADA_TAMAT = 0xFFFF;
const BENDERA_KEKAL = 0x01;
const ITER_BAHARU = 600000;               // PBKDF2-SHA256 untuk fail kunci baharu
const KUNCI_AWAM_SIM = '30cd0721020cb24125bde8673a55d446e196197ac124e8a88f581788cbaa1af5';
const LS_TUNGGAK = 'msims_lesen_tertunggak_v1';
const MIN_LALUAN = 12;
const MASA_KUNCI_AUTO = 15 * 60 * 1000;
const PRODUK = [
  ['SAWIT', 'SIM-SAWIT ANGKUT', 'Simulator'], ['JENGKAUT', 'SIM-JENGKAUT', 'Simulator'], ['FORKLIF', 'SIM-FORKLIF', 'Simulator'],
  ['EKSKAVATOR', 'SIM-EKSKAVATOR', 'Simulator'], ['KRENSTS', 'SIM Kren Gantri STS', 'Simulator'], ['DRON', 'SIM-DRON Pertanian', 'Simulator'],
  ['PUKAT', 'SIM-PUKAT', 'Simulator'], ['TANI', 'SIM-TANI', 'Simulator'], ['APMM', 'SIM-APMM', 'Simulator'],
  ['HARVESTER', 'SimHarvester', 'Simulator'], ['PANDULASAK', 'Sim Pandu Lasak', 'Simulator'],
  ['VRJERUT', 'VR Krew Pukat Jerut', 'VR'], ['VRTUNDA', 'VR Krew Pukat Tunda', 'VR'], ['VRPENYELAM', 'VR Penyelam Konservasi', 'VR'],
];
const LABEL_JENIS = { KEKAL: 'Kekal', TEMPOH: 'Tempoh', PERCUBAAN: 'Percubaan', TERSUAI: 'Tersuai', LAMA: 'Lesen' };
const namaProduk = kod => (PRODUK.find(p => p[0] === kod) || [kod, kod])[1];

const te = new TextEncoder();
const hex = b => [...b].map(x => x.toString(16).padStart(2, '0')).join('');
const unhex = h => new Uint8Array(h.match(/../g).map(x => parseInt(x, 16)));
const b64 = b => btoa(String.fromCharCode(...b));
const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
async function sha256(b) { return new Uint8Array(await crypto.subtle.digest('SHA-256', b)); }
function b32enc(b) { let s = '', buf = 0, bit = 0; for (const x of b) { buf = (buf << 8) | x; bit += 8; while (bit >= 5) { s += AB[(buf >>> (bit - 5)) & 31]; bit -= 5; } buf &= 0xff; }
  if (bit > 0) s += AB[(buf << (5 - bit)) & 31]; return s; }
function b32dec(s) { const out = []; let buf = 0, bit = 0;
  for (let c of s.toUpperCase()) { if ('- \r\n\t'.includes(c)) continue; if (c === 'O') c = '0'; if (c === 'I' || c === 'L') c = '1';
    const v = AB.indexOf(c); if (v < 0) return null; buf = (buf << 5) | v; bit += 5; if (bit >= 8) { out.push((buf >>> (bit - 8)) & 255); bit -= 8; } buf &= 0xff; }
  return new Uint8Array(out); }
async function idProduk(kod) { const h = await sha256(te.encode('MSIMS-PRODUK:' + kod.toUpperCase())); return (h[0] << 8) | h[1]; }
async function nyahkodIdMesin(s) {
  const t = s.toUpperCase().replace(/[^0-9A-Z]/g, '').replace(/O/g, '0').replace(/[IL]/g, '1');
  if (t.length !== 17) return { ralat: 'ID Mesin mesti 17 aksara (XXXX-XXXX-XXXX-XXXX-X).' };
  const b = b32dec(t.slice(0, 16)); if (!b || b.length !== 10) return { ralat: 'ID Mesin mengandungi aksara tidak sah.' };
  const h = await sha256(b); if (AB[h[0] & 31] !== t[16]) return { ralat: 'ID Mesin salah taip (aksara semak tidak sepadan). Minta pelanggan salin semula.' };
  return { bait: b, papar: t.slice(0, 4) + '-' + t.slice(4, 8) + '-' + t.slice(8, 12) + '-' + t.slice(12, 16) + '-' + t[16] };
}
const hariKini = () => Math.floor(Date.now() / 86400000) - HARI_EPOCH;
const hariDari = tarikh => { const [y, m, d] = tarikh.split('-').map(Number); return Math.floor(Date.UTC(y, m - 1, d) / 86400000) - HARI_EPOCH; };
const tarikhDari = h => new Date((h + HARI_EPOCH) * 86400000).toISOString().slice(0, 10).split('-').reverse().join('/');
const isoTambahBulan = n => { const d = new Date(); d.setMonth(d.getMonth() + n); return d.toISOString().slice(0, 10); };
function mesej(id, teks, kelas) { const e = $(id); e.textContent = teks || ''; e.className = 'mesej ' + (kelas || ''); }

// ---------- simpanan pelayar (boleh gagal: tetingkap peribadi, pratonton) ----------
function lsBaca(k) { try { return localStorage.getItem(k); } catch { return null; } }
function lsTulis(k, v) { try { localStorage.setItem(k, v); return true; } catch { return false; } }
function lsBuang(k) { try { localStorage.removeItem(k); } catch {} }

// ---------- fail & papan klip ----------
function simpanFail(nama, teks, mimeJenis) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([teks], { type: mimeJenis || 'text/plain' }));
  a.download = nama; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 800);
  return { ok: true };
}
async function salin(teks, idMesej) {
  try { await navigator.clipboard.writeText(teks); mesej(idMesej, 'Disalin ke papan klip.', 'ok'); return true; }
  catch { mesej(idMesej, 'Papan klip tidak dibenarkan di sini. Pilih teks kunci dan salin secara manual.', 'ralat'); return false; }
}

// ---------- API pelayan ----------
// Pelayan hanya menerima kunci pengesahan (terbitan kata laluan) dan salinan kunci yang SUDAH disulitkan.
// Kata laluan dan kunci rahsia terbuka tidak pernah dihantar.
async function api(aksi, data) {
  let r;
  try { r = await fetch('api.php?a=' + aksi, { method: 'POST', credentials: 'same-origin', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'msims-lesen' }, body: JSON.stringify(data || {}) }); }
  catch { throw { kod: 'rangkaian' }; }
  let j = null; try { j = await r.json(); } catch {}
  if (!r.ok || !j || !j.ok) throw { kod: (j && j.ralat) || 'pelayan', status: r.status, tunggu: j && j.tunggu };
  return j;
}
function ralatApi(e) {
  const k = e && e.kod;
  if (k === 'rangkaian') return 'Tiada sambungan ke pelayan. Semak internet dan cuba lagi.';
  if (k === 'laluan') return 'Nama pengguna atau kata laluan salah.';
  if (k === 'nama') return 'Nama pengguna tidak sah.';
  if (k === 'had') return `Terlalu banyak cubaan. Cuba lagi dalam ${Math.max(1, Math.ceil((e.tunggu || 60) / 60))} minit.`;
  if (k === 'sesi') return 'Sesi tamat. Log masuk semula.';
  if (k === 'tandatangan' || k === 'data') return 'Pelayan menolak fail kunci ini: ia bukan kunci lesen MSIMS semasa.';
  if (k === 'cabaran') return 'Permintaan tamat tempoh. Cuba sekali lagi.';
  if (k === 'storan' || k === 'sodium') return 'Pelayan tidak dapat menyimpan data (' + k + '). Hubungi pentadbir hosting.';
  return 'Ralat pelayan (' + (k || 'tidak diketahui') + '). Cuba lagi.';
}

// ===================== log masuk & kunci rahsia =====================
// Satu nama pengguna + kata laluan: kata laluan mengesahkan anda di pelayan DAN membuka kunci rahsia di dalam pelayar.
let KUNCI = null;            // { awam: Uint8Array, rahsia: Uint8Array } - dalam memori sahaja, hilang apabila halaman ditutup
let OBJ_SEMASA = null;       // salinan dilindungi (bersulit) bagi kunci yang sedang dibuka
let FAIL_DIPILIH = null;     // objek JSON fail kunci yang dipilih
let NAMA = '';               // nama pengguna semasa
let MOD = 'log';             // 'log' | 'sementara' (baru log masuk dengan akaun sementara) | 'lupa' (set semula dengan fail kunci)
let AKTIVITI = Date.now();
const POLA_NAMA = /^[a-z0-9._-]{3,32}$/;
const TEKS_NAMA = 'Nama pengguna: 3 hingga 32 aksara (huruf kecil, nombor, titik atau sengkang).';

async function terbitKunciAes(laluan, garam, iter) {
  const k = await crypto.subtle.importKey('raw', te.encode(laluan), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey({ name: 'PBKDF2', salt: garam, iterations: iter, hash: 'SHA-256' }, k, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}
async function terbitAuth(laluan, garam) {   // kunci pengesahan: garam berasingan, jadi tidak mendedahkan kunci penyulitan
  const k = await crypto.subtle.importKey('raw', te.encode(laluan), 'PBKDF2', false, ['deriveBits']);
  return hex(new Uint8Array(await crypto.subtle.deriveBits({ name: 'PBKDF2', salt: garam, iterations: ITER_BAHARU, hash: 'SHA-256' }, k, 256)));
}
async function lindungi(k, laluan) {
  const garam = crypto.getRandomValues(new Uint8Array(16)), iv = crypto.getRandomValues(new Uint8Array(12));
  const ka = await terbitKunciAes(laluan, garam, ITER_BAHARU);
  const data = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, ka, k.rahsia));
  return { format: 'MSIMS-KUNCI-1', awam: hex(k.awam), enc: { garam: b64(garam), iv: b64(iv), iter: ITER_BAHARU, data: b64(data) }, dicipta: new Date().toISOString() };
}
async function bukaFail(o, laluan) {
  let rahsia;
  if (o.rahsia) rahsia = unhex(o.rahsia);
  else {
    const e = o.enc, ka = await terbitKunciAes(laluan || '', unb64(e.garam), e.iter);
    rahsia = new Uint8Array(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(e.iv) }, ka, unb64(e.data)));
  }
  const awam = await ed.getPublicKeyAsync(rahsia);
  if (hex(awam) !== String(o.awam).toLowerCase()) throw new Error('padanan');
  return { awam, rahsia };
}
function semakLaluanBaru(a, b) {
  if (a.length < MIN_LALUAN) return `Kata laluan minimum ${MIN_LALUAN} aksara.`;
  if (a !== b) return 'Kata laluan tidak sepadan.';
  return null;
}
// Tetapkan nama pengguna + kata laluan di pelayan. Pelayan hanya menerima jika cabaran ditandatangani dengan kunci rahsia lesen.
async function daftarAkaun(k, nama, laluan) {
  const obj = await lindungi(k, laluan);
  const garam = crypto.getRandomValues(new Uint8Array(16));
  const auth = await terbitAuth(laluan, garam);
  const { nonce } = await api('cabaran');
  const tt = await ed.signAsync(te.encode(`MSIMS-LESEN-SEDIA\n${nonce}\n${nama}\n${auth}\n${obj.enc.data}`), k.rahsia);
  await api('sedia', { nonce, nama, auth, garam: b64(garam), blob: obj, tandatangan: b64(tt) });
  return obj;
}

function papar() {
  $('skrinLog').hidden = !!KUNCI; $('skrinApp').hidden = !KUNCI;
  $('panelLog').hidden = MOD !== 'log'; $('panelSedia').hidden = MOD === 'log';
  $('tajukPintu').textContent = MOD === 'log' ? 'Log masuk' : (MOD === 'sementara' ? 'Tetapkan kata laluan anda' : 'Tetapkan semula kata laluan');
  $('subSedia').textContent = MOD === 'sementara'
    ? 'Anda log masuk dengan kata laluan sementara. Tetapkan nama pengguna dan kata laluan anda sendiri, dan pilih fail kunci rahsia lesen. Selepas ini hanya nama pengguna dan kata laluan diperlukan pada mana-mana peranti.'
    : 'Pilih fail kunci rahsia lesen anda untuk menetapkan nama pengguna dan kata laluan baharu. Hanya pemegang fail kunci boleh melakukannya.';
  $('namaLog').textContent = NAMA;
  $('btnTukar').disabled = !KUNCI; $('btnSandarKunci').disabled = !OBJ_SEMASA;
}
function kosongkanBorang() {
  for (const id of ['laluan', 'laluan1', 'laluan2', 'laluanFail', 'namaBaru']) $(id).value = '';
  $('failKunci').value = ''; $('sediaLama').hidden = true; FAIL_DIPILIH = null;
  mesej('mesejLog', ''); mesej('sediaMesej', '');
}
async function logKeluar(sebab) {
  if (KUNCI) KUNCI.rahsia.fill(0);
  KUNCI = null; OBJ_SEMASA = null; DAFTAR = []; HASIL = null; MOD = 'log';
  $('hasil').hidden = true;
  kosongkanBorang(); papar(); lukisDaftar();
  mesej('mesejLog', sebab || '', 'samar');
  try { await api('keluar'); } catch {}
}
async function selepasBuka(k, obj, nota) {
  KUNCI = k; OBJ_SEMASA = obj; MOD = 'log'; AKTIVITI = Date.now();
  kosongkanBorang(); $('namaE').value = NAMA;
  papar(); mesej('mesejApp', nota || '', 'ok');
  await hantarTunggak();
  await muatDaftar();
  $('permintaan').focus();
}
async function logMasuk() {
  const nama = $('nama').value.trim().toLowerCase(), laluan = $('laluan').value;
  if (!POLA_NAMA.test(nama) || !laluan) return mesej('mesejLog', 'Masukkan nama pengguna dan kata laluan.', 'ralat');
  const btn = $('btnMasuk'); btn.disabled = true; btn.textContent = 'Menyemak…'; mesej('mesejLog', '');
  try {
    const { garam } = await api('pra', { nama });
    const auth = await terbitAuth(laluan, unb64(garam));
    const j = await api('masuk', { nama, auth });
    NAMA = j.nama;
    if (!j.blob) { MOD = 'sementara'; kosongkanBorang(); papar(); $('namaBaru').focus(); return; }
    let k; try { k = await bukaFail(j.blob, laluan); } catch { throw { teks: 'Kunci di pelayan tidak dapat dibuka dengan kata laluan ini. Tetapkan semula dengan fail kunci.' }; }
    await selepasBuka(k, j.blob, '');
  } catch (e) { mesej('mesejLog', e && e.teks ? e.teks : ralatApi(e), 'ralat'); $('laluan').select(); }
  finally { btn.disabled = false; btn.textContent = 'Log masuk'; }
}
$('borangLog').addEventListener('submit', e => { e.preventDefault(); logMasuk(); });
$('btnLupa').addEventListener('click', () => { MOD = 'lupa'; kosongkanBorang(); papar(); $('namaBaru').focus(); });
$('btnBatalSedia').addEventListener('click', () => logKeluar(''));
$('btnLogKeluar').addEventListener('click', () => logKeluar(''));

$('failKunci').addEventListener('change', async e => {
  const f = e.target.files[0]; FAIL_DIPILIH = null; $('sediaLama').hidden = true; mesej('sediaMesej', '');
  if (!f) return;
  try { const o = JSON.parse(await f.text()); if (!o || o.format !== 'MSIMS-KUNCI-1' || !o.awam || !(o.rahsia || o.enc)) throw 0; FAIL_DIPILIH = o; }
  catch { return mesej('sediaMesej', 'Fail ini bukan fail kunci MSIMS. Pilih MSIMS-KunciRahsia-ASAL.json atau MSIMS-KunciRahsia-dilindungi.json.', 'ralat'); }
  if (String(FAIL_DIPILIH.awam).toLowerCase() !== KUNCI_AWAM_SIM) { FAIL_DIPILIH = null; return mesej('sediaMesej', 'Fail kunci ini bukan pasangan kunci yang terbina dalam simulator MSIMS semasa.', 'ralat'); }
  $('sediaLama').hidden = !FAIL_DIPILIH.enc;
  mesej('sediaMesej', FAIL_DIPILIH.enc ? 'Fail kunci dilindungi: masukkan juga kata laluan fail itu.' : 'Fail kunci diterima.', 'samar');
});
$('borangSedia').addEventListener('submit', async e => {
  e.preventDefault();
  const nama = $('namaBaru').value.trim().toLowerCase();
  if (!POLA_NAMA.test(nama)) return mesej('sediaMesej', TEKS_NAMA, 'ralat');
  const r = semakLaluanBaru($('laluan1').value, $('laluan2').value); if (r) return mesej('sediaMesej', r, 'ralat');
  if (!FAIL_DIPILIH) return mesej('sediaMesej', 'Pilih fail kunci rahsia dahulu.', 'ralat');
  const btn = $('btnSedia'); btn.disabled = true; btn.textContent = 'Memproses…';
  try {
    let k;
    try { k = await bukaFail(FAIL_DIPILIH, $('laluanFail').value); } catch { throw { teks: FAIL_DIPILIH.enc ? 'Kata laluan fail kunci salah, atau fail rosak.' : 'Fail kunci rosak.' }; }
    const dariAsal = !!FAIL_DIPILIH.rahsia;
    const obj = await daftarAkaun(k, nama, $('laluan1').value);
    NAMA = nama;
    await selepasBuka(k, obj, 'Nama pengguna dan kata laluan ditetapkan. Mana-mana peranti kini hanya perlu log masuk.' + (dariAsal ? ' Muat turun sandaran kunci di bahagian Lanjutan, kemudian PADAM fail ASAL.' : ''));
  } catch (err) {
    mesej('sediaMesej', err && err.teks ? err.teks : ralatApi(err), 'ralat');
  } finally { btn.disabled = false; btn.textContent = 'Simpan & masuk'; }
});
for (const ev of ['pointerdown', 'keydown']) addEventListener(ev, () => { AKTIVITI = Date.now(); }, { passive: true });
setInterval(() => { if (KUNCI && Date.now() - AKTIVITI > MASA_KUNCI_AUTO) logKeluar('Log keluar automatik selepas 15 minit tanpa aktiviti.'); }, 20000);

// ===================== borang jana =====================
function isiProduk() {
  const s = $('produk');
  for (const [kumpulan, label] of [['Simulator', 'Simulator'], ['VR', 'VR (Quest 3)']]) {
    const g = document.createElement('optgroup'); g.label = label;
    for (const [kod, nama, k] of PRODUK) if (k === kumpulan) { const o = document.createElement('option'); o.value = kod; o.textContent = `${nama} · ${kod}`; g.appendChild(o); }
    s.appendChild(g);
  }
  const o = document.createElement('option'); o.value = 'LAIN'; o.textContent = 'Kod lain…'; s.appendChild(o);
  s.value = 'SAWIT';
}
const kodProduk = () => $('produk').value === 'LAIN' ? $('produkLain').value.trim().toUpperCase() : $('produk').value;
const jenisDipilih = () => document.querySelector('input[name=jenis]:checked').value;
function pilihProduk(kod) {
  if (PRODUK.some(p => p[0] === kod)) { $('produk').value = kod; $('bungkusLain').hidden = true; }
  else { $('produk').value = 'LAIN'; $('produkLain').value = kod; $('bungkusLain').hidden = false; }
}

let ID_MESIN = null, giliranKesan = 0;
async function kesanPermintaan() {
  const g = ++giliranKesan;
  const teks = $('permintaan').value, el = $('kesan');
  ID_MESIN = null;
  if (!teks.trim()) { el.className = 'kesan samar'; el.textContent = 'Contoh di atas. ID Mesin dipaparkan pada skrin Pengaktifan Lesen simulator.'; ringkas(); return; }
  const T = teks.toUpperCase();
  const calon = [...T.matchAll(/[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]/g)].map(m => m[0]);
  const padat = T.replace(/[\s-]/g, '');
  if (/^[0-9A-Z]{17}$/.test(padat)) calon.push(padat);
  let jumpa = null, ralat = null;
  for (const c of calon) { const r = await nyahkodIdMesin(c); if (!r.ralat) { jumpa = r; break; } ralat = r.ralat; }
  if (g !== giliranKesan) return;
  const mp = T.match(/PRODUK\s*:[^\n(]*\(([A-Z0-9_]{2,24})\)/);
  if (mp) pilihProduk(mp[1]);
  if (jumpa) {
    ID_MESIN = jumpa; el.className = 'kesan ok';
    el.textContent = `✓ ID Mesin ${jumpa.papar}` + (mp ? ` · produk ${mp[1]} dikesan` : '');
  } else {
    el.className = 'kesan ralat';
    el.textContent = ralat || 'ID Mesin tidak ditemui. Format: XXXX-XXXX-XXXX-XXXX-X (17 aksara).';
  }
  ringkas();
}
let tKesan = 0;
$('permintaan').addEventListener('input', () => { clearTimeout(tKesan); tKesan = setTimeout(kesanPermintaan, 150); });
$('produk').addEventListener('change', () => { $('bungkusLain').hidden = $('produk').value !== 'LAIN'; ringkas(); });
$('produkLain').addEventListener('input', ringkas);

function tukarJenis() {
  const j = jenisDipilih();
  for (const k of ['KEKAL', 'TEMPOH', 'PERCUBAAN', 'TERSUAI']) $('p' + k).hidden = k !== j;
  ringkas();
}
for (const r of document.querySelectorAll('input[name=jenis]')) r.addEventListener('change', tukarJenis);
$('cipanBulan').addEventListener('click', e => {
  const b = e.target.closest('button[data-bulan]'); if (!b) return;
  for (const x of $('cipanBulan').children) x.setAttribute('aria-pressed', x === b ? 'true' : 'false');
  $('tamatTempoh').value = isoTambahBulan(+b.dataset.bulan); ringkas();
});
$('tamatTempoh').addEventListener('input', () => { for (const x of $('cipanBulan').children) x.setAttribute('aria-pressed', 'false'); ringkas(); });
for (const id of ['hariCuba', 'hadCuba', 'tamatSuai', 'hadSuai', 'pelanggan']) $(id).addEventListener('input', ringkas);
$('tiadaTamat').addEventListener('change', e => { $('tamatSuai').disabled = e.target.checked; ringkas(); });
$('tiadaHad').addEventListener('change', e => { $('hadSuai').disabled = e.target.checked; ringkas(); });

function parameter() {
  const j = jenisDipilih(), kini = hariKini();
  const nomborDalam = (id, min, max) => { const n = Number($(id).value); return Number.isInteger(n) && n >= min && n <= max ? n : null; };
  let tamat = TIADA_TAMAT, had = 0, bendera = 0;
  if (j === 'KEKAL') bendera = BENDERA_KEKAL;
  else if (j === 'TEMPOH') { if (!$('tamatTempoh').value) return { ralat: 'Pilih tarikh tamat.' }; tamat = hariDari($('tamatTempoh').value); }
  else if (j === 'PERCUBAAN') {
    const h = nomborDalam('hariCuba', 1, 365); if (h === null) return { ralat: 'Tempoh percubaan mesti 1 hingga 365 hari.' };
    had = nomborDalam('hadCuba', 1, 16777215); if (had === null) return { ralat: 'Had dibuka mesti sekurang-kurangnya 1 kali.' };
    tamat = kini + h;
  } else {
    if (!$('tiadaTamat').checked) { if (!$('tamatSuai').value) return { ralat: 'Pilih tarikh tamat atau tandakan "Tiada tarikh tamat".' }; tamat = hariDari($('tamatSuai').value); }
    if (!$('tiadaHad').checked) { had = nomborDalam('hadSuai', 1, 16777215); if (had === null) return { ralat: 'Had dibuka mesti 1 hingga 16,777,215 (atau tandakan "Tanpa had").' }; }
  }
  if (tamat !== TIADA_TAMAT && tamat < kini) return { ralat: 'Tarikh tamat sudah lepas.' };
  if (tamat !== TIADA_TAMAT && tamat >= TIADA_TAMAT) return { ralat: 'Tarikh tamat terlalu jauh.' };
  return { jenis: j, tamat, had, bendera };
}
const teksSyarat = (tamat, had) => [tamat === 'Tiada' ? 'tiada tarikh tamat' : 'tamat ' + tamat, had === 'Tanpa had' ? 'tanpa had penggunaan' : had + ' kali dibuka'].join(', ');
function ringkas() {
  const p = parameter(), kod = kodProduk() || '—', el = $('ringkasan');
  if (p.ralat) { el.innerHTML = ''; el.append(Object.assign(document.createElement('span'), { className: 'ralat', textContent: p.ralat })); return; }
  const syarat = teksSyarat(p.tamat === TIADA_TAMAT ? 'Tiada' : tarikhDari(p.tamat), p.had || 'Tanpa had');
  el.innerHTML = '';
  const cap = Object.assign(document.createElement('span'), { className: 'cap ' + p.jenis, textContent: LABEL_JENIS[p.jenis] });
  el.append(cap, ' ', Object.assign(document.createElement('b'), { textContent: kod }), ` · ${syarat} · untuk PC ${ID_MESIN ? ID_MESIN.papar : '(ID Mesin belum ditampal)'}`);
}

let HASIL = null;
$('btnJana').addEventListener('click', async () => {
  if (!KUNCI) return;
  mesej('mesejJana', '');
  const kod = kodProduk();
  if (!/^[A-Z0-9_]{2,24}$/.test(kod)) return mesej('mesejJana', 'Kod produk tidak sah (2 hingga 24 huruf/nombor).', 'ralat');
  if (!ID_MESIN) await kesanPermintaan();
  if (!ID_MESIN) return mesej('mesejJana', 'Tampal ID Mesin pelanggan dahulu.', 'ralat');
  const p = parameter(); if (p.ralat) return mesej('mesejJana', p.ralat, 'ralat');
  const btn = $('btnJana'); btn.disabled = true;
  try {
    const id = crypto.getRandomValues(new Uint32Array(1))[0];
    const pr = await idProduk(kod);
    const d = new Uint8Array(25);
    d[0] = 1; d[1] = pr >> 8; d[2] = pr & 255; d.set(ID_MESIN.bait, 3);
    d[13] = id >>> 24; d[14] = (id >>> 16) & 255; d[15] = (id >>> 8) & 255; d[16] = id & 255;
    const mula = Math.max(0, hariKini() - 1);
    d[17] = mula >> 8; d[18] = mula & 255; d[19] = p.tamat >> 8; d[20] = p.tamat & 255;
    d[21] = (p.had >>> 16) & 255; d[22] = (p.had >>> 8) & 255; d[23] = p.had & 255; d[24] = p.bendera;
    const sig = await ed.signAsync(d, KUNCI.rahsia);
    const semua = new Uint8Array(89); semua.set(d); semua.set(sig, 25);
    const r = {
      dijana: new Date().toISOString(), produk: kod, jenis: p.jenis, pelanggan: $('pelanggan').value.trim(), idMesin: ID_MESIN.papar,
      tamat: p.tamat === TIADA_TAMAT ? 'Tiada' : tarikhDari(p.tamat), had: p.had || 'Tanpa had',
      id: id.toString(16).toUpperCase().padStart(8, '0'), catatan: $('catatan').value.trim(),
      kunci: 'MSIMS-' + b32enc(semua).match(/.{1,5}/g).join('-'),
    };
    HASIL = r; paparHasil(r);
    await tambahRekod(r);
  } catch (e) { mesej('mesejJana', 'Ralat: ' + e.message, 'ralat'); }
  finally { btn.disabled = !KUNCI; }
});

const jenisRekod = r => r.jenis || 'LAMA';
function mesejPelanggan(r) {
  return `*Lesen MSIMS — ${namaProduk(r.produk)}*\nJenis: ${LABEL_JENIS[jenisRekod(r)].toUpperCase()} (${teksSyarat(r.tamat, r.had)})\nID Mesin: ${r.idMesin}\nID Lesen: ${r.id}\n\nKunci lesen:\n${r.kunci}\n\nCara aktifkan: buka simulator, tampal kunci pada skrin Pengaktifan Lesen, tekan AKTIFKAN.\nLesen ini sah pada komputer dengan ID Mesin di atas sahaja.`;
}
const pautanWa = r => 'https://wa.me/?text=' + encodeURIComponent(mesejPelanggan(r));
function paparHasil(r) {
  $('capHasil').className = 'cap ' + jenisRekod(r); $('capHasil').textContent = LABEL_JENIS[jenisRekod(r)];
  $('hasilTajuk').textContent = `${namaProduk(r.produk)}${r.pelanggan ? ' · ' + r.pelanggan : ''}`;
  $('hasilButir').textContent = `ID Lesen ${r.id} · ID Mesin ${r.idMesin} · ${teksSyarat(r.tamat, r.had)}`;
  $('hasilKunci').textContent = r.kunci; $('lnkWa').href = pautanWa(r);
  $('hasil').hidden = false; mesej('mesejHasil', '');
  $('hasil').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' });
}
$('btnSalinKunci').addEventListener('click', () => HASIL && salin(HASIL.kunci, 'mesejHasil'));
$('btnSalinMesej').addEventListener('click', () => HASIL && salin(mesejPelanggan(HASIL), 'mesejHasil'));
$('btnTxt').addEventListener('click', async () => {
  if (!HASIL) return; const r = HASIL;
  const t = `LESEN PERISIAN MSIMS\r\n====================\r\nProduk      : ${namaProduk(r.produk)} (${r.produk})\r\nJenis       : ${LABEL_JENIS[jenisRekod(r)].toUpperCase()}\r\nPelanggan   : ${r.pelanggan || '-'}\r\nID Mesin    : ${r.idMesin}\r\nTarikh tamat: ${r.tamat}\r\nHad guna    : ${r.had}\r\nID lesen    : ${r.id}\r\n\r\nKUNCI LESEN (salin keseluruhan baris di bawah):\r\n${r.kunci}\r\n\r\nCara mengaktifkan: buka simulator, tampal kunci lesen pada skrin "Pengaktifan Lesen", tekan AKTIFKAN.\r\nLesen ini hanya sah pada komputer dengan ID Mesin di atas.\r\n`;
  const m = await simpanFail(`Lesen-${r.produk}-${(r.pelanggan || r.id).replace(/[^A-Za-z0-9]+/g, '_')}.txt`, t, 'text/plain');
  mesej('mesejHasil', m.ok ? 'Fail .txt dimuat turun.' : m.sebab, m.ok ? 'ok' : 'ralat');
});

// ===================== daftar lesen (disimpan di pelayan; sama di semua peranti) =====================
let DAFTAR = [];
const rekodSah = r => r && typeof r === 'object' && typeof r.id === 'string' && /^[0-9A-F]{8}$/.test(r.id) && typeof r.kunci === 'string';
const senaraiDaftar = () => DAFTAR;
// rekod yang belum sampai ke pelayan (rangkaian putus / sesi tamat) disimpan di pelayar dan dihantar semula kemudian
const tunggak = () => { try { const a = JSON.parse(lsBaca(LS_TUNGGAK) || '[]'); return Array.isArray(a) ? a.filter(rekodSah) : []; } catch { return []; } };
const simpanTunggak = a => { if (a.length) lsTulis(LS_TUNGGAK, JSON.stringify(a)); else lsBuang(LS_TUNGGAK); };
async function hantarTunggak() {
  const a = tunggak(); if (!a.length) return;
  try { await api('tambah', { rekod: a }); simpanTunggak([]); } catch {}
}
async function muatDaftar() {
  try { const j = await api('daftar'); DAFTAR = (j.rekod || []).filter(rekodSah); mesej('mesejDaftar', ''); }
  catch (e) { mesej('mesejDaftar', ralatApi(e), 'ralat'); }
  lukisDaftar();
}
async function tambahRekod(r) {
  DAFTAR = [r, ...DAFTAR.filter(x => x.id !== r.id)]; lukisDaftar();
  try { await api('tambah', { rekod: r }); mesej('mesejDaftar', ''); }
  catch (e) {
    simpanTunggak([r, ...tunggak().filter(x => x.id !== r.id)]);
    mesej('mesejDaftar', 'Lesen ini sah dan boleh dihantar, tetapi rekodnya belum disimpan di pelayan (' + ralatApi(e) + ') Ia akan dihantar semula apabila anda log masuk lagi.', 'ralat');
  }
}
function lukisDaftar() {
  const q = $('cari').value.trim().toLowerCase();
  const semua = senaraiDaftar().filter(rekodSah).slice().sort((a, b) => String(b.dijana).localeCompare(String(a.dijana)));
  const tapis = q ? semua.filter(r => [r.produk, namaProduk(r.produk), r.pelanggan, r.idMesin, r.id, r.catatan, LABEL_JENIS[jenisRekod(r)]].join(' ').toLowerCase().includes(q)) : semua;
  $('bilDaftar').textContent = semua.length ? `${semua.length} lesen` : '';
  const ul = $('senaraiDaftar'); ul.innerHTML = '';
  if (!tapis.length) {
    const li = document.createElement('li'); li.className = 'kosong';
    li.textContent = (semua.length ? 'Tiada padanan untuk carian ini.' : 'Belum ada lesen. Setiap lesen yang anda jana disenaraikan di sini, dengan butang untuk salin semula atau hantar WhatsApp.');
    ul.appendChild(li); return;
  }
  const el = (tag, kelas, teks) => { const e = document.createElement(tag); if (kelas) e.className = kelas; if (teks != null) e.textContent = teks; return e; };
  for (const r of tapis.slice(0, 300)) {
    const li = document.createElement('li');
    const r1 = el('div', 'r1'); r1.append(el('span', 'cap ' + jenisRekod(r), LABEL_JENIS[jenisRekod(r)] || 'Lesen'), el('span', 'prod', r.produk), el('span', '', String(r.dijana).slice(0, 10).split('-').reverse().join('/')));
    const r2 = el('div', 'r2', r.pelanggan || '(tiada nama pelanggan)');
    const r3 = el('div', 'r3'); r3.append(el('span', 'mono', r.idMesin), ` · ${teksSyarat(r.tamat, r.had)} · ID ${r.id}`);
    li.append(r1, r2, r3);
    if (r.catatan) li.append(el('div', 'r3', r.catatan));
    const r4 = el('div', 'r4');
    const bS = el('button', '', 'Salin kunci'); bS.dataset.id = r.id; bS.dataset.aksi = 'salin';
    const aW = el('a', 'btn', 'WhatsApp'); aW.href = pautanWa(r); aW.target = '_blank'; aW.rel = 'noopener';
    r4.append(bS, aW); li.append(r4); ul.appendChild(li);
  }
}
$('senaraiDaftar').addEventListener('click', e => {
  const b = e.target.closest('button[data-aksi=salin]'); if (!b) return;
  const r = senaraiDaftar().find(x => x.id === b.dataset.id); if (r) salin(r.kunci, 'mesejDaftar');
});
$('cari').addEventListener('input', lukisDaftar);
$('btnCsv').addEventListener('click', () => {
  if (!DAFTAR.length) return mesej('mesejDaftar', 'Tiada rekod untuk dieksport.', 'samar');
  const k = ['dijana', 'produk', 'jenis', 'pelanggan', 'idMesin', 'tamat', 'had', 'id', 'catatan', 'kunci'];
  const q = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  simpanFail('MSIMS-daftar-lesen.csv', '\uFEFF' + [k.join(','), ...DAFTAR.map(r => k.map(x => q(x === 'jenis' ? jenisRekod(r) : r[x])).join(','))].join('\r\n'), 'text/csv');
  mesej('mesejDaftar', 'CSV dimuat turun.', 'ok');
});
$('btnSandar').addEventListener('click', () => {
  if (!DAFTAR.length) return mesej('mesejDaftar', 'Tiada rekod untuk disandarkan.', 'samar');
  simpanFail('MSIMS-daftar-lesen-sandaran.json', JSON.stringify(DAFTAR, null, 1), 'application/json'); mesej('mesejDaftar', 'Sandaran dimuat turun.', 'ok');
});
$('btnPulih').addEventListener('click', () => { $('failPulih').click(); });
$('failPulih').addEventListener('change', async e => {
  const f = e.target.files[0]; e.target.value = ''; if (!f) return;
  let a; try { a = JSON.parse(await f.text()); if (!Array.isArray(a)) throw 0; } catch { return mesej('mesejDaftar', 'Fail sandaran tidak sah.', 'ralat'); }
  const masuk = a.filter(rekodSah);
  if (!masuk.length) return mesej('mesejDaftar', 'Tiada rekod lesen dalam fail itu.', 'ralat');
  try { const j = await api('tambah', { rekod: masuk }); await muatDaftar(); mesej('mesejDaftar', `${j.tambah} rekod baharu dipulihkan (${masuk.length} dalam fail, ${j.diterima} bertandatangan sah).`, 'ok'); }
  catch (err) { mesej('mesejDaftar', err && err.kod === 'data' ? 'Tiada rekod dalam fail itu yang ditandatangani dengan kunci MSIMS semasa.' : ralatApi(err), 'ralat'); }
});

// ===================== lanjutan =====================
$('btnSemak').addEventListener('click', async () => {
  const el = $('hasilSemak');
  try {
    const m = $('semakTeks').value.toUpperCase().match(/MSIMS-[0-9A-Z-]{60,}/);
    let t = (m ? m[0] : $('semakTeks').value).replace(/\s/g, ''); if (/^msims-/i.test(t)) t = t.slice(6);
    const b = b32dec(t); if (!b || b.length < 89) throw new Error('Format kunci tidak sah.');
    const d = b.slice(0, 25), sig = b.slice(25, 89);
    const sahSim = await verifyAsync(sig, d, unhex(KUNCI_AWAM_SIM));
    const sahBuka = KUNCI && hex(KUNCI.awam) !== KUNCI_AWAM_SIM ? await verifyAsync(sig, d, KUNCI.awam) : null;
    const p = (d[1] << 8) | d[2]; let nama = `tidak dikenali (0x${p.toString(16)})`;
    for (const [kod] of PRODUK) if (await idProduk(kod) === p) nama = `${namaProduk(kod)} · ${kod}`;
    const tamat = (d[19] << 8) | d[20], had = (d[21] << 16) | (d[22] << 8) | d[23], kekal = (d[24] & BENDERA_KEKAL) !== 0;
    const h = await sha256(d.slice(3, 13)), s = b32enc(d.slice(3, 13));
    const id = ((d[13] << 24) >>> 0) + (d[14] << 16) + (d[15] << 8) + d[16];
    el.textContent = '';
    const baris = [
      `Tandatangan: ${sahSim ? 'SAH (kunci simulator semasa)' : 'TIDAK SAH untuk simulator semasa'}${sahBuka === null ? '' : sahBuka ? ' · sah untuk kunci yang dibuka' : ''}`,
      `Jenis: ${kekal ? 'KEKAL' : 'biasa'} · Produk: ${nama}`,
      `ID Mesin: ${s.slice(0, 4)}-${s.slice(4, 8)}-${s.slice(8, 12)}-${s.slice(12, 16)}-${AB[h[0] & 31]}`,
      `ID lesen: ${id.toString(16).toUpperCase().padStart(8, '0')} · Mula: ${tarikhDari((d[17] << 8) | d[18])} · Tamat: ${tamat === TIADA_TAMAT ? 'Tiada' : tarikhDari(tamat)} · Had: ${had || 'Tanpa had'}`,
    ];
    baris.forEach((x, i) => { if (i) el.append(document.createElement('br')); el.append(x); });
    el.className = 'mesej ' + (sahSim || sahBuka ? 'ok' : 'ralat');
  } catch (e) { el.textContent = e.message; el.className = 'mesej ralat'; }
});
$('btnTukar').addEventListener('click', async () => {
  if (!KUNCI) return;
  const nama = $('namaE').value.trim().toLowerCase();
  if (!POLA_NAMA.test(nama)) return mesej('mesejEksport', TEKS_NAMA, 'ralat');
  const r = semakLaluanBaru($('laluanE1').value, $('laluanE2').value); if (r) return mesej('mesejEksport', r, 'ralat');
  const btn = $('btnTukar'); btn.disabled = true; btn.textContent = 'Menukar…';
  try { OBJ_SEMASA = await daftarAkaun(KUNCI, nama, $('laluanE1').value); NAMA = nama; $('laluanE1').value = ''; $('laluanE2').value = ''; mesej('mesejEksport', 'Nama pengguna dan kata laluan ditukar. Semua peranti kini menggunakan yang baharu.', 'ok'); }
  catch (e) { mesej('mesejEksport', ralatApi(e), 'ralat'); }
  finally { btn.textContent = 'Simpan nama pengguna & kata laluan'; papar(); }
});
$('btnSandarKunci').addEventListener('click', () => {
  if (!OBJ_SEMASA) return;
  simpanFail('MSIMS-KunciRahsia-dilindungi.json', JSON.stringify(OBJ_SEMASA, null, 1), 'application/json');
  mesej('mesejSandarKunci', 'Fail kunci dilindungi dimuat turun. Simpan di pendrive dan Drive peribadi; ia dibuka dengan kata laluan semasa anda.', 'ok');
});

// ===================== mula =====================
$('awamHex').textContent = KUNCI_AWAM_SIM;
isiProduk();
$('tamatTempoh').value = isoTambahBulan(3);
{ const d = new Date(); d.setMonth(d.getMonth() + 12); $('tamatSuai').value = d.toISOString().slice(0, 10); }
tukarJenis();
papar();
lukisDaftar();
$('nama').focus();

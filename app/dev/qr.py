"""DEV ONLY: a small QR code encoder (ISO/IEC 18004, byte mode, versions 1-40, levels L/M/Q/H, automatic mask) with an
SVG writer: black square modules on white, 4-module quiet zone. Pure Python, no dependencies; follows the structure of
Project Nayuki's public QR Code generator. make_integration.py uses it for app/img/qr-repo.svg.
Usage: python3 app/dev/qr.py TEXT [out.svg]    Self-test: python3 app/dev/qr.py --test"""
import sys

# per version 0..40 (index 0 unused): error-correction codewords per block, and number of blocks
ECC_PER_BLOCK = {
    "L": [-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    "M": [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
    "Q": [-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    "H": [-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
}
NUM_BLOCKS = {
    "L": [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25],
    "M": [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49],
    "Q": [-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68],
    "H": [-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81],
}
FORMAT_BITS = {"L": 1, "M": 0, "Q": 3, "H": 2}
MASKS = [
    lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0, lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0, lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0, lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
]


def raw_modules(ver):  # data + ECC modules after all function patterns
    n = (16 * ver + 128) * ver + 64
    if ver >= 2:
        a = ver // 7 + 2
        n -= (25 * a - 10) * a - 55
        if ver >= 7:
            n -= 36
    return n


def data_codewords(ver, ecl):
    return raw_modules(ver) // 8 - ECC_PER_BLOCK[ecl][ver] * NUM_BLOCKS[ecl][ver]


def gf_mul(x, y):  # GF(2^8) mod x^8 + x^4 + x^3 + x^2 + 1
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def rs_divisor(deg):
    res = [0] * (deg - 1) + [1]
    root = 1
    for _ in range(deg):
        for j in range(deg):
            res[j] = gf_mul(res[j], root)
            if j + 1 < deg:
                res[j] ^= res[j + 1]
        root = gf_mul(root, 0x02)
    return res


def rs_remainder(data, div):
    res = [0] * len(div)
    for b in data:
        f = b ^ res.pop(0)
        res.append(0)
        for i, c in enumerate(div):
            res[i] ^= gf_mul(c, f)
    return res


def align_positions(ver):
    if ver == 1:
        return []
    a = ver // 7 + 2
    step = (ver * 8 + a * 3 + 5) // (a * 4 - 4) * 2
    size = ver * 4 + 17
    res = [6]
    pos = size - 7
    while len(res) < a:
        res.insert(1, pos)
        pos -= step
    return res


def encode(text, ecl="M", mask=None):
    """Returns the module matrix (list of rows, True = dark) for `text` (UTF-8, byte mode) at the smallest version."""
    data = text.encode("utf-8")
    for ver in range(1, 41):
        cc = 8 if ver <= 9 else 16
        if 4 + cc + 8 * len(data) <= data_codewords(ver, ecl) * 8:
            break
    else:
        raise ValueError("text too long")
    bits = []
    put = lambda v, n: bits.extend((v >> i) & 1 for i in reversed(range(n)))
    put(0b0100, 4); put(len(data), cc)
    for b in data:
        put(b, 8)
    cap = data_codewords(ver, ecl) * 8
    put(0, min(4, cap - len(bits)))
    put(0, (-len(bits)) % 8)
    pad = 0xEC
    while len(bits) < cap:
        put(pad, 8); pad ^= 0xEC ^ 0x11
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    # split into blocks, append ECC, interleave
    nb, el = NUM_BLOCKS[ecl][ver], ECC_PER_BLOCK[ecl][ver]
    raw = raw_modules(ver) // 8
    nshort, slen = nb - raw % nb, raw // nb
    div, blocks, k = rs_divisor(el), [], 0
    for i in range(nb):
        dat = words[k:k + slen - el + (0 if i < nshort else 1)]
        k += len(dat)
        ecc = rs_remainder(dat, div)
        if i < nshort:
            dat = dat + [0]
        blocks.append(dat + ecc)
    cw = [blk[i] for i in range(len(blocks[0])) for j, blk in enumerate(blocks) if i != slen - el or j >= nshort]
    assert len(cw) == raw
    # function patterns
    size = ver * 4 + 17
    M = [[False] * size for _ in range(size)]
    F = [[False] * size for _ in range(size)]

    def fn(x, y, dark):
        M[y][x] = dark; F[y][x] = True

    for i in range(size):
        fn(6, i, i % 2 == 0); fn(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < size and 0 <= y < size:
                    fn(x, y, max(abs(dx), abs(dy)) not in (2, 4))
    al = align_positions(ver)
    for i, ay in enumerate(al):
        for j, ax in enumerate(al):
            if (i == 0 and j == 0) or (i == 0 and j == len(al) - 1) or (i == len(al) - 1 and j == 0):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    fn(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)

    def format_bits(m):
        d = FORMAT_BITS[ecl] << 3 | m
        r = d
        for _ in range(10):
            r = (r << 1) ^ ((r >> 9) * 0x537)
        b = (d << 10 | r) ^ 0x5412
        g = lambda i: (b >> i) & 1 == 1
        for i in range(6):
            fn(8, i, g(i))
        fn(8, 7, g(6)); fn(8, 8, g(7)); fn(7, 8, g(8))
        for i in range(9, 15):
            fn(14 - i, 8, g(i))
        for i in range(8):
            fn(size - 1 - i, 8, g(i))
        for i in range(8, 15):
            fn(8, size - 15 + i, g(i))
        fn(8, size - 8, True)  # the dark module

    format_bits(0)  # reserves the format areas
    if ver >= 7:
        r = ver
        for _ in range(12):
            r = (r << 1) ^ ((r >> 11) * 0x1F25)
        b = ver << 12 | r
        for i in range(18):
            d = (b >> i) & 1 == 1
            a, c = size - 11 + i % 3, i // 3
            fn(a, c, d); fn(c, a, d)
    # codewords, in the two-column zigzag
    i, right = 0, size - 1
    while right >= 1:
        if right == 6:
            right = 5
        for vert in range(size):
            for j in range(2):
                x = right - j
                y = size - 1 - vert if ((right + 1) & 2) == 0 else vert
                if not F[y][x] and i < len(cw) * 8:
                    M[y][x] = (cw[i >> 3] >> (7 - (i & 7))) & 1 == 1
                    i += 1
        right -= 2

    def apply(m):
        f = MASKS[m]
        for y in range(size):
            for x in range(size):
                if not F[y][x] and f(x, y):
                    M[y][x] = not M[y][x]

    if mask is None:
        best = None
        for m in range(8):
            apply(m); format_bits(m)
            p = penalty(M)
            if best is None or p < best[0]:
                best = (p, m)
            apply(m)
        mask = best[1]
    apply(mask); format_bits(mask)
    return M


def penalty(M):
    n, res = len(M), 0
    lines = [row for row in M] + [[M[y][x] for y in range(n)] for x in range(n)]
    finder = ([True, False, True, True, True, False, True, False, False, False, False],
              [False, False, False, False, True, False, True, True, True, False, True])
    for ln in lines:
        run = 1
        for k in range(1, n + 1):
            if k < n and ln[k] == ln[k - 1]:
                run += 1
            else:
                if run >= 5:
                    res += 3 + run - 5
                run = 1
        for k in range(n - 10):
            if ln[k:k + 11] in finder:
                res += 40
    for y in range(n - 1):
        for x in range(n - 1):
            if M[y][x] == M[y][x + 1] == M[y + 1][x] == M[y + 1][x + 1]:
                res += 3
    dark, tot = sum(map(sum, M)), n * n
    res += ((abs(dark * 20 - tot * 10) + tot - 1) // tot - 1) * 10
    return res


def svg(M, quiet=4):
    n = len(M) + 2 * quiet
    d = "".join(f"M{x + quiet},{y + quiet}h1v1h-1z" for y, row in enumerate(M) for x, v in enumerate(row) if v)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
            f'<rect width="{n}" height="{n}" fill="#fff"/><path fill="#000" d="{d}"/></svg>\n')


def _test():
    # known vector: the GF(256) generator polynomial for 10 ECC codewords (ISO/IEC 18004 Annex A, alpha exponents
    # 251 67 46 61 118 70 64 94 32 45), and the format string for M / mask 5 (100000011001110, ISO Table C.1)
    exp = [1]
    for _ in range(254):
        exp.append(gf_mul(exp[-1], 2))
    assert rs_divisor(10) == [exp[e] for e in (251, 67, 46, 61, 118, 70, 64, 94, 32, 45)], "generator polynomial"
    d = 0 << 3 | 5
    r = d
    for _ in range(10):
        r = (r << 1) ^ ((r >> 9) * 0x537)
    assert (d << 10 | r) ^ 0x5412 == 0b100000011001110, "format bits"
    # ISO/IEC 18004 Annex I: "01234567" at 1-M yields these 16 data + 10 ECC codewords (numeric mode there, so we check
    # the RS step on the given data codewords)
    data = [0x10, 0x20, 0x0C, 0x56, 0x61, 0x80, 0xEC, 0x11, 0xEC, 0x11, 0xEC, 0x11, 0xEC, 0x11, 0xEC, 0x11]
    assert rs_remainder(data, rs_divisor(10)) == [0xA5, 0x24, 0xD4, 0xC1, 0xED, 0x36, 0xC7, 0x87, 0x2C, 0x55], "ECC"
    print("ok: generator polynomial, format bits, Annex I ECC codewords")


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        _test()
    else:
        s = svg(encode(sys.argv[1]))
        if len(sys.argv) > 2:
            open(sys.argv[2], "w").write(s)
        else:
            sys.stdout.write(s)

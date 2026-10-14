"""Display rules for every number the Prüfstand shows (shared by build_pruefstand.py and render_pruefstand.py).
Point values are truncated toward zero, never rounded up; interval bounds are rounded outward (lower bound down, upper bound
up), never inward. Values are taken exactly as stored in the source file (shortest repr of the float)."""
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR

MINUS = "−"


def q(v, d, mode=ROUND_DOWN):
    """Decimal of v quantised to d decimals with the given rounding mode."""
    return Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-d), rounding=mode)


def _s(x, d, sep=","):
    s = f"{abs(x):,.{d}f}" if sep else f"{abs(x):.{d}f}"
    if sep and sep != ",": s = s.replace(",", sep)
    return (MINUS if x < 0 else "") + s


def t(v, d=3, sep=","):
    """point value: truncated toward zero to d decimals (thousands separator for |v| ≥ 1,000)."""
    if isinstance(v, int) and not isinstance(v, bool): return _s(Decimal(v), 0, sep)
    x = q(v, d, ROUND_DOWN)
    if x == 0: x = abs(x)
    return _s(x, d, sep)


def lo(v, d=3, sep=","):
    """lower interval bound, rounded down."""
    if isinstance(v, int): return _s(Decimal(v), 0, sep)
    return _s(q(v, d, ROUND_FLOOR), d, sep)


def hi(v, d=3, sep=","):
    """upper interval bound, rounded up."""
    if isinstance(v, int): return _s(Decimal(v), 0, sep)
    return _s(q(v, d, ROUND_CEILING), d, sep)


def signed(s):
    return s if s.startswith(MINUS) or s.lstrip("0.,") == "" else "+" + s


def pct(v, d=1):
    """share as a percentage, truncated."""
    x = (Decimal(repr(float(v))) * 100).quantize(Decimal(1).scaleb(-d), rounding=ROUND_DOWN)
    return f"{x:.{d}f}%"

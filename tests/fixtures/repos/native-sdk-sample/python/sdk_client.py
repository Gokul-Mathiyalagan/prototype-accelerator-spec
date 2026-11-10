"""Call the vendored native libraries through ctypes."""

import ctypes
import sys
from pathlib import Path

VENDOR = Path(__file__).resolve().parent.parent / "vendor"
SUFFIX = ".dylib" if sys.platform == "darwin" else ".so"


def load(name: str) -> ctypes.CDLL:
    return ctypes.CDLL(str(VENDOR / name / "lib" / f"lib{name}{SUFFIX}"))


tinymath = load("tinymath")
tinymath.tm_add.argtypes = [ctypes.c_int, ctypes.c_int]
tinymath.tm_clamp.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
tinymath.tm_version.restype = ctypes.c_char_p

secretsauce = load("secretsauce")
secretsauce.ss_score.argtypes = [ctypes.c_char_p, ctypes.c_int]
secretsauce.ss_version.restype = ctypes.c_char_p


def weighted_score(segment: str, weight: int) -> int:
    """Score a segment with the vendor library, clamped to 0..10000."""
    raw = secretsauce.ss_score(segment.encode(), weight)
    return tinymath.tm_clamp(raw, 0, 10000)


if __name__ == "__main__":
    print(tinymath.tm_version().decode(), secretsauce.ss_version().decode())
    print("enterprise:", weighted_score("enterprise", 3))

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

import sdk_client  # noqa: E402


def test_tinymath_adds():
    assert sdk_client.tinymath.tm_add(2, 3) == 5


def test_weighted_score_is_clamped():
    assert 0 <= sdk_client.weighted_score("enterprise", 3) <= 10000
    assert sdk_client.weighted_score("", 0) == 0  # -1 from the vendor, clamped to 0

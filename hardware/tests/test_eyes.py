import math

from flybridge.config import Config
from flybridge.eyes import looming_angle


def test_angle_grows_as_object_approaches():
    cfg = Config()
    angles = [looming_angle(d, cfg) for d in (200, 100, 50, 20, 10, 5)]
    assert angles == sorted(angles)


def test_nothing_in_range_is_zero():
    cfg = Config()
    assert looming_angle(None, cfg) == 0.0
    assert looming_angle(cfg.max_range_cm, cfg) == 0.0


def test_angle_at_threshold():
    cfg = Config(object_size_cm=20, near_cm=20)
    assert math.isclose(looming_angle(20, cfg), 2 * math.atan(0.5))

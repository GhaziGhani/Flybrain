"""Sensor -> eyes: one ultrasonic distance becomes a looming stimulus.

An object of size S at distance d fills an angle 2*atan(S / 2d) of the visual field.
Flies avoid collisions with looming-sensitive visual projection neurons (LPLC2, LC4),
which respond both to how big a dark object looks and to how fast it grows. The
ultrasonic sensor only measures distance, so we turn that distance into the angle an
obstacle of `object_size_cm` would subtend, and drive those neurons with it.

The sensor looks straight ahead, so both eyes (L and R populations) get the same drive.
"""
from __future__ import annotations

import math

import numpy as np

from .config import Config


def looming_angle(distance_cm: float | None, cfg: Config) -> float:
    """Angle in radians an obstacle subtends; 0 when nothing is in range."""
    if distance_cm is None or distance_cm <= 0 or distance_cm >= cfg.max_range_cm:
        return 0.0
    d = max(distance_cm, 1.0)
    return 2.0 * math.atan(cfg.object_size_cm / (2.0 * d))


class UltrasonicEyes:
    def __init__(self, brain, cfg: Config):
        self.cfg = cfg
        self.lplc2 = np.concatenate([brain.cells(["LPLC2"], "L"), brain.cells(["LPLC2"], "R")])
        self.lc4 = np.concatenate([brain.cells(["LC4"], "L"), brain.cells(["LC4"], "R")])
        if len(self.lplc2) == 0 or len(self.lc4) == 0:
            raise RuntimeError("this brain has no LPLC2/LC4 looming neurons to use as eyes")
        self.previous_angle: float | None = None
        self.last_drive = 0.0

    def drive(self, distance_cm: float | None) -> float:
        angle = looming_angle(distance_cm, self.cfg)
        growth = 0.0 if self.previous_angle is None else max(0.0, angle - self.previous_angle)
        self.previous_angle = angle
        size_term = self.cfg.loom_gain * angle / (math.pi / 2)
        self.last_drive = float(np.clip(size_term + self.cfg.growth_gain * growth, 0.0, self.cfg.drive_cap))
        return self.last_drive

    def inject(self, distance_cm: float | None) -> list:
        amount = self.drive(distance_cm)
        if amount <= 0:
            return []
        return [(self.lplc2, amount), (self.lc4, amount)]

    def reset(self) -> None:
        self.previous_angle = None
        self.last_drive = 0.0

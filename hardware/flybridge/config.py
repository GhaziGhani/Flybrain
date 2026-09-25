from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Config:
    near_cm: float = 20.0
    margin_cm: float = 2.0
    object_size_cm: float = 20.0
    max_range_cm: float = 400.0

    sample_ms: int = 80
    steps_per_reading: int = 4
    loom_gain: float = 0.9
    growth_gain: float = 4.0
    drive_cap: float = 0.8

    readout: str = "vnc_motor"
    components: int = 80
    trace_tau: float = 0.25
    calibration_readings: int = 300

    learning_rate: float = 0.3
    temperature: float = 0.25
    exploration: float = 0.05
    baseline_rate: float = 0.05
    reward_correct: float = 1.0
    punish_crash: float = -1.0
    punish_false_alarm: float = -0.5

    inject_dopamine: bool = True
    dopamine_drive: float = 0.6

    seed: int = 64

    def to_dict(self) -> dict:
        return asdict(self)

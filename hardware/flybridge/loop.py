"""The closed loop, one sensor reading at a time:

  Arduino sensor -> link -> median filter -> eyes (LPLC2/LC4 looming drive)
    -> the real connectome, stepped 20 ms at a time
    -> motor neuron activity -> readout -> LED decision -> link -> Arduino LED
    -> judge (was that right?) -> dopamine (PAM reward / PPL1 punishment) -> learning

Modes:
  train   explores, learns from every judged decision
  run     uses what it learned, greedily, with no further learning
  innate  no readout at all: the LED follows the DNp01 giant fiber, the fly's own
          hard-wired escape command. Shows what the untrained connectome already does.
"""
from __future__ import annotations

import csv
import threading
import time
from collections import deque

import numpy as np

from .config import Config
from .eyes import UltrasonicEyes
from .learning import DopamineNeurons, DopaminePolicy, MotorReadout, judge
from .link import MedianFilter

MODES = ("train", "run", "innate")
LOG_FIELDS = ["millis", "raw_cm", "cm", "loom_drive", "eye_spikes", "giant_fiber_spikes", "motor_spikes",
              "p_avoid", "led", "pwm", "verdict", "reward", "dopamine", "pam_spikes", "ppl1_spikes",
              "phase", "accuracy", "near_cm"]


class FlyLoop:
    def __init__(self, brain, link, cfg: Config, mode: str = "train", policy: DopaminePolicy | None = None,
                 log_path=None, heatmap_neurons: int = 48, heatmap_length: int = 120):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.brain, self.link, self.cfg, self.mode = brain, link, cfg, mode
        self.eyes = UltrasonicEyes(brain, cfg)
        self.readout = MotorReadout(brain, cfg)
        self.dopamine = DopamineNeurons(brain, cfg)
        self.filter = MedianFilter(cfg.max_range_cm)
        self.policy = policy or DopaminePolicy(cfg, seed=cfg.seed)
        if mode == "run" and not self.policy.ready:
            raise ValueError("run mode needs a trained model; train first or pass --model")
        self.calibration: list | None = None if (self.policy.ready or mode == "innate") else []

        n = brain.n
        self.eye_mask = np.zeros(n, bool)
        self.eye_mask[np.concatenate([self.eyes.lplc2, self.eyes.lc4])] = True
        self.giant_fiber_mask = np.zeros(n, bool)
        self.giant_fiber_mask[brain.cells(["DNp01"])] = True
        self.motor_mask = np.zeros(n, bool)
        self.motor_mask[self.readout.idx] = True

        self.lock = threading.Lock()
        self.history: deque = deque(maxlen=400)
        self.activity: deque = deque(maxlen=heatmap_length)
        self.heatmap_neurons = heatmap_neurons
        self.judged = {True: deque(maxlen=60), False: deque(maxlen=60)}
        self.totals = {"readings": 0, "avoided": 0, "clear": 0, "crash": 0, "false alarm": 0}
        self.started = time.monotonic()

        self.log_file = open(log_path, "w", newline="") if log_path else None
        self.log = csv.DictWriter(self.log_file, LOG_FIELDS) if self.log_file else None
        if self.log:
            self.log.writeheader()

    @property
    def phase(self) -> str:
        if self.mode == "innate":
            return "innate reflex"
        if self.calibration is not None:
            return "calibrating"
        return "learning" if self.mode == "train" else "running"

    @property
    def accuracy(self) -> float | None:
        """Balanced accuracy over recent decisions: the mean of 'avoided when near' and
        'stayed off when far', so a fly that never switches on can't score well just
        because obstacles are usually far away."""
        rates = [np.mean(v) for v in self.judged.values() if v]
        return float(np.mean(rates)) if len(rates) == 2 else None

    @property
    def hit_rates(self) -> dict:
        return {"near": float(np.mean(self.judged[True])) if self.judged[True] else None,
                "far": float(np.mean(self.judged[False])) if self.judged[False] else None}

    def cycle(self) -> dict | None:
        reading = self.link.read()
        if reading is None:
            return None
        cm = self.filter(reading.cm)
        inject = self.eyes.inject(cm)

        eye = giant = motor = 0
        x = None
        for _ in range(self.cfg.steps_per_reading):
            fired = self.brain.step(inject=inject)
            x = self.readout.observe(fired)
            eye += int(self.eye_mask[fired].sum())
            giant += int(self.giant_fiber_mask[fired].sum())
            motor += int(self.motor_mask[fired].sum())

        z = None
        if self.mode == "innate":
            led, p = giant > 0, min(1.0, giant / self.cfg.steps_per_reading)
        elif self.calibration is not None:
            led, p = False, 0.0
            self.calibration.append(x)
            if len(self.calibration) >= self.cfg.calibration_readings:
                self.policy.fit_basis(np.stack(self.calibration))
                self.calibration = None
        else:
            z = self.policy.features(x)
            led, p = self.policy.act(z, explore=self.mode == "train")
        pwm = int(round(255 * p)) if led else 0
        self.link.send(led, pwm)

        phase = self.phase
        reward, verdict = judge(cm, led, self.cfg)
        dopamine, pam, ppl1 = 0.0, 0, 0
        if self.mode == "train" and z is not None and reward != 0:
            dopamine = self.policy.learn(z, led, reward)
            fired = self.brain.step(inject=self.dopamine.inject(dopamine))
            self.readout.observe(fired)
            pam, ppl1 = self.dopamine.count(fired)

        if phase != "calibrating" and reward != 0:
            self.judged[cm < self.cfg.near_cm].append(1.0 if reward > 0 else 0.0)
            self.totals[verdict] += 1
        self.totals["readings"] += 1

        record = {
            "millis": reading.millis, "raw_cm": reading.cm, "cm": round(cm, 1),
            "loom_drive": round(self.eyes.last_drive, 3), "eye_spikes": eye,
            "giant_fiber_spikes": giant, "motor_spikes": motor, "p_avoid": round(p, 3),
            "led": int(led), "pwm": pwm, "verdict": verdict, "reward": reward,
            "dopamine": round(dopamine, 3), "pam_spikes": pam, "ppl1_spikes": ppl1,
            "phase": phase, "accuracy": None if self.accuracy is None else round(self.accuracy, 3),
            "near_cm": self.cfg.near_cm,
        }
        with self.lock:
            self.history.append(record)
            self.activity.append(np.asarray(x, np.float32))
        if self.log:
            self.log.writerow(record)
        return record

    def snapshot(self) -> dict:
        """Everything the dashboard shows, safe to call from another thread."""
        with self.lock:
            history = list(self.history)
            activity = np.stack(self.activity) if self.activity else None
        heatmap = None
        if activity is not None and len(activity) > 2:
            top = np.argsort(activity.var(0))[::-1][:self.heatmap_neurons]
            block = activity[:, top].T
            lo, hi = block.min(1, keepdims=True), block.max(1, keepdims=True)
            heatmap = ((block - lo) / (hi - lo + 1e-6)).round(3).tolist()
        return {
            "mode": self.mode, "phase": self.phase, "readout": self.cfg.readout,
            "near_cm": self.cfg.near_cm, "margin_cm": self.cfg.margin_cm,
            "port": getattr(self.link, "port", "?"), "arduino": getattr(self.link, "version", None),
            "totals": dict(self.totals), "accuracy": self.accuracy, "hit_rates": self.hit_rates,
            "calibration": None if self.calibration is None else [len(self.calibration), self.cfg.calibration_readings],
            "updates": self.policy.updates, "expected_reward": round(self.policy.expected_reward, 3),
            "uptime": round(time.monotonic() - self.started, 1),
            "history": history, "heatmap": heatmap,
        }

    def close(self) -> None:
        if self.log_file:
            self.log_file.close()

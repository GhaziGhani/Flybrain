"""Motor neurons -> decision, and dopamine -> learning.

The connectome itself is never changed: flybrain wires it exactly as electron microscopy
found it. What learns is a set of output synapses from a motor population (by default
the 708 real VNC motor neurons) onto two competing output neurons, AVOID (LED on) and
CRUISE (LED off). This mirrors the fly's mushroom body, where approach and avoidance
output neurons (MBONs) compete, and dopamine rewrites the Kenyon cell -> MBON synapses
of whichever compartment was active.

Each output neuron's activity is its learned value for acting now. Whichever is higher
wins (with a little behavioural variability while training). After the judge scores
the action, dopamine is the reward prediction error for the neuron that acted:

    dopamine = reward - value(chosen)
    dw(chosen) = learning_rate * dopamine * activity / (1 + |activity|^2)

Positive dopamine (the PAM cluster in flies) strengthens the synapses that produced a
good action; negative dopamine (the PPL1 cluster, the fly's "don't do that" signal)
weakens the ones that produced a bad one. Because each action keeps its own value,
a crash teaches the brain directly that cruising was wrong there, even when it was
confident, which a single-output rule can't do.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from flybrain import Trace

from .config import Config

POPULATIONS = {
    "vnc_motor": "the 708 VNC motor neurons that drive the fly's muscles",
    "descending": "the 1,314 descending neurons, the brain's commands to the body",
    "escape": "the escape descending neurons DNp01 (giant fiber), DNp02, DNp04, DNp11",
}


def population(brain, name: str) -> np.ndarray:
    superclass = brain.superclass.astype(str)
    if name == "vnc_motor":
        idx = np.flatnonzero(superclass == "vnc_motor")
    elif name == "descending":
        idx = np.flatnonzero(superclass == "descending_neuron")
    elif name == "escape":
        idx = brain.cells(["DNp01", "DNp02", "DNp04", "DNp11"])
    else:
        raise ValueError(f"readout must be one of {sorted(POPULATIONS)}, not {name!r}")
    if len(idx) == 0:
        raise RuntimeError(f"no {name} neurons in this brain")
    return idx


def cell_types_starting(brain, prefix: str) -> np.ndarray:
    return np.flatnonzero(np.char.startswith(brain.cell_type.astype(str), prefix))


class MotorReadout:
    def __init__(self, brain, cfg: Config):
        self.idx = population(brain, cfg.readout)
        self.trace = Trace(brain, idx=self.idx, tau=cfg.trace_tau)

    def observe(self, fired) -> np.ndarray:
        return self.trace.observe(fired)


def judge(distance_cm: float | None, led_on: bool, cfg: Config) -> tuple[float, str]:
    """The world's verdict on one decision. Too close with the LED off is a crash."""
    if distance_cm is None:
        return 0.0, "no reading"
    if abs(distance_cm - cfg.near_cm) <= cfg.margin_cm:
        return 0.0, "borderline"
    near = distance_cm < cfg.near_cm
    if near and led_on:
        return cfg.reward_correct, "avoided"
    if near:
        return cfg.punish_crash, "crash"
    if led_on:
        return cfg.punish_false_alarm, "false alarm"
    return cfg.reward_correct, "clear"


CRUISE, AVOID = 0, 1


class DopaminePolicy:
    """Two competing output neurons (CRUISE, AVOID) over PCA-compressed motor activity."""

    def __init__(self, cfg: Config, seed: int = 0):
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        self.mu = self.P = self.sd = None
        self.W = None
        self.b = np.zeros(2)
        self.expected_reward = 0.0
        self.updates = 0

    @property
    def ready(self) -> bool:
        return self.P is not None

    def fit_basis(self, X: np.ndarray) -> None:
        """Called once, after calibration: which directions of motor activity vary most."""
        X = np.asarray(X, np.float64)
        self.mu = X.mean(0)
        vt = np.linalg.svd(X - self.mu, full_matrices=False)[2]
        k = min(self.cfg.components, len(vt))
        self.P = vt[:k].T
        self.sd = ((X - self.mu) @ self.P).std(0) + 1e-6
        self.W = np.zeros((2, k))
        self.b = np.zeros(2)

    def features(self, x: np.ndarray) -> np.ndarray:
        return ((np.asarray(x, np.float64) - self.mu) @ self.P) / self.sd

    def values(self, z: np.ndarray) -> np.ndarray:
        return self.W @ z + self.b

    def p_avoid(self, z: np.ndarray) -> float:
        q = self.values(z)
        return float(1.0 / (1.0 + np.exp(-np.clip((q[AVOID] - q[CRUISE]) / self.cfg.temperature, -30, 30))))

    def act(self, z: np.ndarray, explore: bool) -> tuple[bool, float]:
        p = self.p_avoid(z)
        if not explore:
            return p >= 0.5, p
        eps = self.cfg.exploration
        return bool(self.rng.random() < eps / 2 + (1 - eps) * p), p

    def learn(self, z: np.ndarray, action: bool, reward: float) -> float:
        """Apply one dopamine signal to the output neuron that acted. Returns the dopamine
        level: the reward prediction error, positive = better than expected."""
        a = AVOID if action else CRUISE
        dopamine = reward - (self.W[a] @ z + self.b[a])
        step = self.cfg.learning_rate * dopamine / (1.0 + z @ z)
        self.W[a] += step * z
        self.b[a] += step
        self.expected_reward += self.cfg.baseline_rate * (reward - self.expected_reward)
        self.updates += 1
        return float(dopamine)

    def save(self, path: str | Path) -> None:
        np.savez(path, mu=self.mu, P=self.P, sd=self.sd, W=self.W, b=self.b,
                 expected_reward=self.expected_reward, updates=self.updates,
                 readout=self.cfg.readout)

    def load(self, path: str | Path) -> None:
        d = np.load(path, allow_pickle=False)
        if str(d["readout"]) != self.cfg.readout:
            raise ValueError(f"{path} was trained on the {d['readout']} readout, not {self.cfg.readout}")
        self.mu, self.P, self.sd, self.W, self.b = d["mu"], d["P"], d["sd"], d["W"], d["b"]
        self.expected_reward = float(d["expected_reward"])
        self.updates = int(d["updates"])


class DopamineNeurons:
    """The fly's real dopaminergic neurons, fired inside the connectome as the teaching signal:
    PAM cluster for reward, PPL1 cluster for punishment."""

    def __init__(self, brain, cfg: Config):
        self.cfg = cfg
        self.pam = cell_types_starting(brain, "PAM")
        self.ppl1 = cell_types_starting(brain, "PPL1")
        self.pam_mask = np.zeros(brain.n, bool)
        self.pam_mask[self.pam] = True
        self.ppl1_mask = np.zeros(brain.n, bool)
        self.ppl1_mask[self.ppl1] = True

    def inject(self, dopamine: float) -> list:
        if not self.cfg.inject_dopamine or dopamine == 0:
            return []
        amount = float(np.clip(abs(dopamine), 0, 1)) * self.cfg.dopamine_drive
        return [(self.pam if dopamine > 0 else self.ppl1, amount)]

    def count(self, fired) -> tuple[int, int]:
        return int(self.pam_mask[fired].sum()), int(self.ppl1_mask[fired].sum())

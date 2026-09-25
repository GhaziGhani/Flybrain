"""Plot a FlyBridge session log as one image.

    python tools/plot_session.py logs/train-20260925-181500.csv [out.png]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"
ORANGE, RED, AQUA, MAGENTA, GREEN, BLUE, YELLOW = ("#eb6834", "#e34948", "#1baf7a", "#d55181",
                                                   "#0ca30c", "#2a78d6", "#c98500")


def load(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    num = lambda k: np.array([float(r[k]) if r[k] not in ("", "None") else np.nan for r in rows])  # noqa: E731
    return rows, num


def main() -> None:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".png")
    rows, num = load(src)
    t = np.arange(len(rows))
    cm, led = num("cm"), num("led")
    crash = np.array([r["verdict"] == "crash" for r in rows])
    calibrating = np.array([r["phase"] == "calibrating" for r in rows])
    dopamine, acc = num("dopamine"), num("accuracy")

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, ax = plt.subplots(5, 1, figsize=(11, 10), sharex=True,
                           gridspec_kw={"height_ratios": [2.2, 1, 1, 1.4, 1.4]}, facecolor="#fcfcfb")
    for a in ax:
        a.set_facecolor("#fcfcfb")
        a.grid(axis="y", color=GRID, lw=0.6)
        if calibrating.any():
            a.axvspan(0, np.flatnonzero(calibrating)[-1], color="#f0efec", lw=0)

    ax[0].fill_between(t, 0, np.nanmax(cm[cm < 300]) * 1.05, where=led > 0, color=ORANGE, alpha=0.22, lw=0,
                       step="mid", label="LED on (brain's decision)")
    ax[0].plot(t, np.minimum(cm, 200), color=INK, lw=0.9, label="distance")
    near = float(rows[0].get("near_cm") or 20.0)
    ax[0].axhline(near, color=YELLOW, ls="--", lw=1, label=f"near threshold ({near:g} cm)")
    ax[0].scatter(t[crash], np.zeros(crash.sum()), marker="|", s=80, color=RED, label="crash")
    ax[0].set_ylabel("distance (cm)")
    ax[0].set_ylim(bottom=0)
    ax[0].legend(loc="upper right", ncol=4, frameon=False)
    ax[0].set_title(f"{src.name}: {len(rows)} readings   (grey = calibration)", loc="left", color=INK)

    ax[1].plot(t, num("giant_fiber_spikes"), color=AQUA, lw=0.8)
    ax[1].set_ylabel("giant fiber\nspikes")
    ax[2].plot(t, num("motor_spikes"), color=MAGENTA, lw=0.8)
    ax[2].set_ylabel("motor neuron\nspikes")

    ax[3].bar(t, np.where(dopamine > 0, dopamine, 0), width=1, color=GREEN, label="PAM: reward")
    ax[3].bar(t, np.where(dopamine < 0, dopamine, 0), width=1, color=RED, label="PPL1: punishment")
    ax[3].axhline(0, color=MUTED, lw=0.6)
    ax[3].set_ylabel("dopamine\n(prediction error)")
    ax[3].legend(loc="upper right", ncol=2, frameon=False)

    ax[4].plot(t, acc, color=BLUE, lw=1.4)
    ax[4].set_ylim(0, 1.02)
    ax[4].set_ylabel("balanced\naccuracy")
    ax[4].set_xlabel("sensor reading")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print(out)


if __name__ == "__main__":
    main()

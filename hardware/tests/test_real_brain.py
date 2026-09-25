"""Runs the loop on the real MaleCNS connectome. Skipped if the brain files aren't downloaded."""
import numpy as np
import pytest

flybrain = pytest.importorskip("flybrain")
pytestmark = pytest.mark.skipif(not flybrain.has_data(), reason="run `flybrain download` first")

from flybridge import Config, FlyLoop, SimArduino  # noqa: E402
from flybridge.link import Reading  # noqa: E402


class Scripted(SimArduino):
    """Holds the obstacle at a fixed distance."""

    def __init__(self, cm):
        super().__init__()
        self.cm = cm

    def read(self, timeout=1.0):
        self.millis += 80
        return Reading(self.millis, self.cm)


@pytest.fixture(scope="module")
def brain():
    return flybrain.FlyBrain(device="cpu", sensory_input=False, seed=64)


def test_looming_near_object_drives_the_escape_pathway_harder(brain):
    cfg = Config()
    spikes = {}
    for cm in (120, 8):
        brain.reset(64)
        loop = FlyLoop(brain, Scripted(cm), cfg, mode="innate")
        spikes[cm] = sum(loop.cycle()["giant_fiber_spikes"] for _ in range(30))
    assert spikes[8] > spikes[120]


def test_training_loop_calibrates_learns_and_releases_dopamine(brain):
    brain.reset(64)
    cfg = Config(calibration_readings=40, components=10)
    loop = FlyLoop(brain, SimArduino(cfg.near_cm, seed=5), cfg, mode="train")
    records = [loop.cycle() for _ in range(160)]
    assert loop.phase == "learning" and loop.policy.updates > 50
    rewarded = [r for r in records if r["dopamine"] > 0]
    punished = [r for r in records if r["dopamine"] < 0]
    assert rewarded and punished
    assert np.mean([r["ppl1_spikes"] for r in punished]) > np.mean([r["ppl1_spikes"] for r in rewarded])

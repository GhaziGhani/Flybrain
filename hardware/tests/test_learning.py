import numpy as np

from flybridge.config import Config
from flybridge.learning import DopaminePolicy, judge


def test_judge_verdicts():
    cfg = Config(near_cm=20, margin_cm=2)
    assert judge(10, True, cfg) == (cfg.reward_correct, "avoided")
    assert judge(10, False, cfg) == (cfg.punish_crash, "crash")
    assert judge(80, True, cfg) == (cfg.punish_false_alarm, "false alarm")
    assert judge(80, False, cfg) == (cfg.reward_correct, "clear")
    assert judge(21, True, cfg) == (0.0, "borderline")
    assert judge(None, True, cfg)[0] == 0.0


def synthetic_activity(distance, rng, n=60):
    """Stand-in for motor-neuron activity: a few neurons respond more the closer the object is."""
    x = rng.normal(0, 0.3, n)
    x[:8] += 3.0 / (1 + distance / 15)
    return x


def test_dopamine_learns_to_avoid_from_reward_alone():
    cfg = Config(components=10)
    rng = np.random.default_rng(0)
    policy = DopaminePolicy(cfg, seed=0)
    distances = rng.uniform(4, 90, 3000)
    policy.fit_basis(np.stack([synthetic_activity(d, rng) for d in distances[:300]]))
    for d in distances[300:]:
        z = policy.features(synthetic_activity(d, rng))
        led, _ = policy.act(z, explore=True)
        reward, _ = judge(d, led, cfg)
        if reward:
            policy.learn(z, led, reward)
    correct = []
    for d in rng.uniform(4, 90, 500):
        reward, _ = judge(d, policy.act(policy.features(synthetic_activity(d, rng)), explore=False)[0], cfg)
        if reward:
            correct.append(reward > 0)
    assert np.mean(correct) > 0.9


def test_crash_teaches_even_a_confident_policy():
    cfg = Config(components=4)
    policy = DopaminePolicy(cfg, seed=0)
    policy.fit_basis(np.random.default_rng(1).normal(size=(50, 4)))
    z = np.ones(4)
    policy.b[:] = [2.0, -2.0]
    before = policy.p_avoid(z)
    for _ in range(20):
        policy.learn(z, action=False, reward=cfg.punish_crash)
    assert policy.p_avoid(z) > before


def test_save_and_load_roundtrip(tmp_path):
    cfg = Config(components=4)
    policy = DopaminePolicy(cfg)
    policy.fit_basis(np.random.default_rng(2).normal(size=(40, 6)))
    policy.learn(np.ones(4), True, 1.0)
    policy.save(tmp_path / "m.npz")
    other = DopaminePolicy(cfg)
    other.load(tmp_path / "m.npz")
    assert np.allclose(other.W, policy.W) and other.updates == 1

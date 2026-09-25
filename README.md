# FlyBrain Reservoir

An interactive reservoir computer modeled on the topology of the fly connectome. The same circuit can be
given different jobs: paste in a real sequence of numbers and it learns the trend and predicts what comes
next, it learns to balance a bicycle from scratch through trial and reward, or it can interpolate arbitrary
functions from sparse, noisy samples and get benchmarked live against classical methods.

Live artifact: https://claude.ai/artifact/LDCQSH9521hbgqkHoBJRip

## What this is

In 2024, [FlyWire and an international consortium published the first complete connectome of an adult
brain](https://research.google/blog/a-connectomics-milestone-mapping-the-complete-male-fruit-fly-brain/):
every one of the ~140,000 neurons and ~50 million synapses in a male fruit fly, reconstructed from
electron microscopy. [Janelia FlyEM, the MRC Laboratory of Molecular Biology, the University of Cambridge
and Google Research have since extended that map into the male CNS
connectome](https://www.janelia.org/project-team/flyem/male-cns-connectome) — the brain *and* the ventral
nerve cord, seamlessly wired together: roughly 166,000 neurons in total, about 23,000 of them in the nerve
cord alone. `index.html` is a single-page, self-contained simulation inspired by both milestones — not a
download of either actual dataset (which requires authenticated access to tens of millions of individual
synapses), but a statistically faithful stand-in built from their published architecture: regional neuron
proportions, feedforward sensory pathways (optic lobes, antennal lobe), recurrent hubs (central complex,
mushroom body), and a distinct nerve-cord module fed by descending neurons — generated at a scale a
browser can simulate in real time.

## The idea

The generated connectome is used as the fixed, signed (Dale's-law) recurrent weight matrix of an
[echo-state-network-style reservoir computer](https://en.wikipedia.org/wiki/Reservoir_computing). Sensory
input is injected into the optic lobes and antennal lobe and left to ripple through the recurrent
circuitry. Central-complex and other central-brain neurons — the fly's real locomotor/steering hub —
project descending into a modeled ventral nerve cord, and it's that nerve cord's own small, trainable
population of motor neurons that produces the final output. Only those nerve-cord synapses ever change;
everything upstream of them stays fixed.

The app currently offers three tasks built on that same substrate:

- **Forecast a trend** (the flagship task, and the only one that runs on data you bring): paste any ordered
  sequence of real numbers — sales, prices, sensor readings, anything evenly spaced. Each value feeds into
  the reservoir one step at a time alongside a normalized time index (so both trend and seasonality are
  learnable, since the time index is always known even for future steps), and a ridge-regression readout
  learns to predict the next value. In "Validate accuracy" mode it holds back the last stretch of your data
  and grades its forecast against what actually happened (RMSE / MAE / MAPE); in "Predict what's next" it
  trains on everything and forecasts new points past the end, feeding its own predictions back in as it
  goes. It's benchmarked against three classical forecasting baselines — persistence, linear-trend
  extrapolation, and Holt's linear exponential smoothing — and genuinely loses to them on cleanly linear
  data and wins on noisy/nonlinear series, which is the honest result.
- **Ride a bicycle** (the one that learns *over time*): a simplified lean-and-steer bicycle model that
  falls over unless something actively corrects it. The brain feels the lean angle and lean rate and
  outputs a single steering torque via its nerve-cord motor neurons. Those readout weights are trained
  across many attempts with an OpenAI-ES-style evolution strategy — each generation perturbs the weights
  several ways, runs one episode per perturbation, and moves the weights toward whichever variants survived
  longest and stayed most upright. A live learning-curve chart plots survival time per generation so you
  can watch it improve from a few seconds to a full, uncrashed run.
- **Interpolate a function**: the original task. A scalar input — think of it as a position swept across
  the fly's compound eye — drives the reservoir once, and a ridge-regression readout is trained on a
  handful of labeled, noisy moments from that sweep to reconstruct the target function everywhere else.
  It's compared against five classical interpolation/regression methods on the same sparse samples, ranked
  by RMSE / MAE / R² against the true (held-out) function, with an "edge of chaos" explorer that rescales
  the brain's connection strengths across a range of spectral radii — reproducing reservoir computing's
  signature result that performance peaks at the boundary between ordered and chaotic dynamics.

Brain size, spectral radius, leak rate and input gain are shared across all three tasks — it's genuinely
the same circuit doing three different jobs, not three separate simulations.

## Running it

It's a single static HTML file with no build step and no external dependencies beyond two Google Fonts
links — open `index.html` directly in a browser, or serve the directory with any static file server.

## Hardware: a real fly brain driving an Arduino

[`hardware/`](hardware/README.md) takes this off the screen. An Arduino streams an ultrasonic
sensor to the PC, where the complete MaleCNS connectome (166,700 real neurons, via the
[`flybrain`](https://pypi.org/project/flybrain/) library) sees the reading as a looming stimulus on
its LPLC2/LC4 looming detectors. A readout from its 708 real VNC motor neurons decides whether to
switch an LED on, and the brain learns what its motor output should mean from dopamine: its own
PAM neurons for reward, PPL1 neurons for punishment. See [hardware/README.md](hardware/README.md)
for wiring, setup, measured results and the serial protocol.

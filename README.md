# FlyBrain Reservoir

An interactive reservoir computer modeled on the topology of the fly connectome. The same circuit can be
given different jobs: it now learns to balance a bicycle from scratch through trial and reward, or it can
interpolate arbitrary functions from sparse, noisy samples and get benchmarked live against classical
interpolation methods (linear, cubic spline, polynomial, Gaussian RBF, k-NN).

Live artifact: https://claude.ai/artifact/LDCQSH9521hbgqkHoBJRip

## What this is

In 2024, [FlyWire and an international consortium published the first complete connectome of an adult
brain](https://research.google/blog/a-connectomics-milestone-mapping-the-complete-male-fruit-fly-brain/):
every one of the ~140,000 neurons and ~50 million synapses in a male fruit fly, reconstructed from
electron microscopy. `index.html` is a single-page, self-contained simulation inspired by that
milestone — not a download of the actual FlyWire dataset (which requires authenticated access to the
raw synapse table), but a statistically faithful stand-in built from the same architectural facts:
regional neuron proportions, feedforward sensory pathways (optic lobes, antennal lobe), and recurrent
hubs (central complex, mushroom body), generated at a scale a browser can simulate in real time.

## The idea

The generated connectome is used as the fixed, signed (Dale's-law) recurrent weight matrix of an
[echo-state-network-style reservoir computer](https://en.wikipedia.org/wiki/Reservoir_computing). Sensory
input is injected into the optic lobes and antennal lobe and left to ripple through the recurrent
circuitry; everything downstream of that fixed reservoir is read out by a small, trainable population of
"descending" neurons drawn mostly from the central complex — the fly's real locomotor/steering hub.

The app currently offers two tasks built on that same substrate:

- **Ride a bicycle** (the flagship task, and the one that learns *over time*): a simplified lean-and-steer
  bicycle model that falls over unless something actively corrects it. The brain feels the lean angle and
  lean rate and outputs a single steering torque. Its descending-neuron readout weights are trained across
  many attempts with an OpenAI-ES-style evolution strategy — each generation perturbs the weights several
  ways, runs one episode per perturbation, and moves the weights toward whichever variants survived
  longest and stayed most upright. A live learning-curve chart plots survival time per generation so you
  can watch it improve from a few seconds to a full, uncrashed run.
- **Interpolate a function**: the original task. A scalar input — think of it as a position swept across
  the fly's compound eye — drives the reservoir once, and a ridge-regression readout is trained on a
  handful of labeled, noisy moments from that sweep to reconstruct the target function everywhere else.
  It's compared against five classical interpolation/regression methods on the same sparse samples, ranked
  by RMSE / MAE / R² against the true (held-out) function, with an "edge of chaos" explorer that rescales
  the brain's connection strengths across a range of spectral radii — reproducing reservoir computing's
  signature result that performance peaks at the boundary between ordered and chaotic dynamics.

Brain size, spectral radius, leak rate and input gain are shared across both tasks — it's genuinely the
same circuit doing two different jobs, not two separate simulations.

## Running it

It's a single static HTML file with no build step and no external dependencies beyond two Google Fonts
links — open `index.html` directly in a browser, or serve the directory with any static file server.

# FlyBrain Reservoir

An interactive reservoir computer modeled on the topology of the fly connectome, used to interpolate
arbitrary functions from sparse, noisy samples and benchmarked live against classical interpolation
methods (linear, cubic spline, polynomial, Gaussian RBF, k-NN).

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
[echo-state-network-style reservoir computer](https://en.wikipedia.org/wiki/Reservoir_computing). A
scalar input — think of it as a position swept across the fly's compound eye — is injected into the
sensory neuropils and left to ripple through the recurrent circuitry. A simple ridge-regression readout
is then trained on a handful of labeled, noisy moments from that sweep, and used to reconstruct the
target function everywhere else.

The page compares that reconstruction against five classical interpolation/regression methods on the
same sparse samples, ranks them by RMSE / MAE / R² against the true (held-out) function, and includes an
"edge of chaos" explorer that rescales the same brain's connection strengths across a range of spectral
radii — reproducing reservoir computing's signature result that performance peaks at the boundary
between ordered and chaotic dynamics.

## Running it

It's a single static HTML file with no build step and no external dependencies beyond two Google Fonts
links — open `index.html` directly in a browser, or serve the directory with any static file server.

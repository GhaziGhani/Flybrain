# FlyBridge: a real fly brain in the loop with an Arduino

An ultrasonic obstacle-avoidance robot where the Arduino does **no thinking**. It measures
distance and drives an LED; every decision in between is made by the complete male fruit fly
central nervous system — the [MaleCNS v1.0 connectome](https://www.janelia.org/project-team/flyem/male-cns-connectome),
166,700 real neurons and 25.6 million real connections, simulated with the
[`flybrain`](https://pypi.org/project/flybrain/) library. The brain learns what its own motor
output should mean through dopamine: rewarded when it avoids, punished when it "crashes".

```
 HC-SR04 ──► Arduino ──serial──► PC                                            ┌──► judge: right or wrong?
  sensor      (senses only)      │                                             │        │
                                 ▼                                             │        ▼
                        median filter ─► EYES ─► MaleCNS connectome ─► MOTOR ─► decision   DOPAMINE
                                         LPLC2    (frozen, 20 ms steps)  NEURONS  AVOID vs  PAM = reward
                                         LC4      166,700 neurons         708 VNC  CRUISE    PPL1 = "don't"
                                         looming                                   │          │
                                         detectors                                 │  rewires the readout
 LED ◄── Arduino ◄──serial── C,led,pwm ◄──────────────────────────────────────────┘  synapses (only these)
```

## How each layer maps to the fly

| Layer | In this project | In a real fly |
|---|---|---|
| Sensor | HC-SR04 distance, streamed every 80 ms | compound eye |
| Eyes | distance → the angle an obstacle would fill → voltage into **LPLC2** and **LC4** (185 + 126 neurons, both eyes) | LPLC2/LC4 are the fly's looming detectors, the cells that fire when something is about to hit it |
| Brain | the full MaleCNS connectome, 4 × 20 ms steps per reading, **never modified** | the same wiring |
| Output | spike traces of the **708 VNC motor neurons** (or the 1,314 descending neurons, `--readout descending`) | motor neurons drive the muscles; descending neurons carry the brain's commands to them |
| Decision | two competing output units, **AVOID** and **CRUISE**; the higher-valued one wins | approach vs avoidance mushroom body output neurons (MBONs) |
| Teaching signal | dopamine = reward − expected reward, fired into the connectome's own **PAM** (reward, 316 neurons) or **PPL1** (punishment, 16 neurons) cells | PAM and PPL1 dopaminergic clusters |
| Learning | three-factor rule on the output synapses: `Δw = rate × dopamine × activity` | dopamine-gated plasticity at Kenyon cell → MBON synapses |

**The "pain / don't do it" neurons** you were looking for are the **PPL1** dopaminergic neurons.
Flies don't have a single pain centre, but aversive learning — "that hurt, don't do it again" —
is taught by PPL1 dopamine, while PAM dopamine teaches reward. Both are in this connectome, and
the loop actually fires them: after each punished decision you can see PPL1 spike inside the
brain (and in the dashboard).

**What learns, honestly:** `flybrain` keeps the connectome's 25.6 million synapses fixed (it's
the real wiring; that's the point). What dopamine changes is the set of synapses from the output
population onto the AVOID/CRUISE units — the same division of labour as reservoir computing, and
the same place a fly's dopamine acts (the mushroom body output synapses).

## Measured results

All measured on the real connectome in this repo's simulator, then **tested with learning switched
off on an obstacle path the brain never trained on** (600 readings). "Balanced" averages the
near-object and far-object scores, so a brain that never turns on can't look good by default.

| Output population | Near: avoided | Far: stayed off | Balanced |
|---|---|---|---|
| **Innate** DNp01 giant fiber, no training | 100% | 0.7% | 0.50 |
| 708 VNC motor neurons, trained (default settings) | 96.5% | 92.0% | **0.943** |
| 1,314 descending neurons, trained | 99.3% | 96.2% | **0.978** |
| 8 escape descending neurons (DNp01/02/04/11), trained | 97.9% | 98.1% | **0.980** |

The untrained brain already sees the obstacle — its giant fiber fires for anything in range,
so it never crashes but raises constant false alarms. Dopamine training teaches it where
"too near" actually is. Motor neurons learn slightly worse than descending neurons because by
the time the looming signal reaches the nerve cord it's mixed with the cord's own ongoing activity;
that's why the motor readout defaults to 80 principal components and 80 ms of integration.

**Full hardware-path rehearsal.** The same thing run exactly as it would be with a board: the CLI,
the real `SerialLink`, and `tools/fake_arduino.py` speaking the Arduino protocol over a virtual
serial port, in real time (80 ms per reading). Default VNC motor readout, trained for 2,400 readings
(~3 minutes, 2,015 dopamine updates), then 900 readings with learning off:

| | Near: avoided | Far: stayed off | Balanced | Crashes |
|---|---|---|---|---|
| Real time, over the serial link, learning off | 93.3% | 83.8% | **0.885** | 15 of 223 near decisions |

Its remaining mistakes are mostly false alarms, not crashes. That follows from the rewards: a crash
costs −1 and a false alarm only −0.5, so the brain learned that caution is cheaper. Set
`punish_false_alarm = -1.0` in `config.py` if you want it less jumpy, and train longer for both.

## Parts and wiring

* Arduino Uno or Nano (any 5 V AVR board), USB cable
* HC-SR04 ultrasonic sensor
* One LED and a 220 Ω resistor (later: a motor driver, see below)

```
HC-SR04          Arduino               LED
  VCC  ───────── 5V
  GND  ───────── GND ─────────────────── cathode (short leg)
  TRIG ───────── D9
  ECHO ───────── D10
                 D6 ─── 220 Ω ───────── anode (long leg)
```

On a 3.3 V board, put a voltage divider on ECHO (it outputs 5 V).

## Setup

**1. Arduino.** Open `arduino/fly_bridge/fly_bridge.ino` in the Arduino IDE, pick your board and
port, and upload. Open the Serial Monitor at **115200** baud: you should see `HELLO,FlyBridge,1`
and a stream of `D,<millis>,<cm>` lines that change as you move your hand. **Close the Serial
Monitor afterwards** — only one program can hold the port, and Python needs it.

**2. Python** (3.10 or newer):

```sh
cd hardware
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python -m flybrain download      # the brain: ~260 MB, once, checksum-verified
```

**3. VS Code.** Open the `hardware` folder (File → Open Folder). The Run and Debug panel has
ready-made launch configurations: simulated Arduino, real Arduino (train), real Arduino (run
what it learned), innate reflex, and list ports. Select the `.venv` interpreter when prompted.

## Running it

Try it without hardware first:

```sh
python -m flybridge --sim
```

Open **http://127.0.0.1:8765** to watch it live: the distance and the brain's LED decisions,
spikes in the eyes, giant fiber and motor neurons, every dopamine burst, the motor population
as a neurons × time matrix, and the learning curve.

Then with the Arduino:

```sh
python -m flybridge --list-ports          # find it: COM5, /dev/ttyACM0, /dev/cu.usbmodem...
python -m flybridge --port COM5           # learn
```

**Training it.** For the first 300 readings (~25 s) it only watches, calibrating which patterns
of motor activity vary. Then it starts deciding. Move your hand (or a book) toward the sensor
past 20 cm and away again, at different speeds, for a few minutes, spending about as long near
as far. Wrong answers are punished, so early on the LED will be erratic; that is the fly learning.
Stop with Ctrl+C. The learned synapses are saved to `flybridge_model.npz` and **the next session
continues from them**, so it keeps improving across sessions.

```sh
python -m flybridge --port COM5 --mode run      # use what it learned; no more learning
python -m flybridge --port COM5 --mode innate   # compare: the untrained giant-fiber reflex
python -m flybridge --port COM5 --near 30       # a different "too near" distance
python -m flybridge --port COM5 --readout descending --model descending.npz
```

Every session writes a CSV to `logs/`. Turn one into a picture with
`python tools/plot_session.py logs/<file>.csv`.

## Serial protocol

115200 baud, one message per line:

| Direction | Message | Meaning |
|---|---|---|
| Arduino → PC | `HELLO,FlyBridge,1` | on boot and in reply to `?` |
| Arduino → PC | `D,<millis>,<cm>` | one reading every 80 ms; `-1.0` = no echo |
| PC → Arduino | `C,<led 0/1>,<pwm 0-255>` | the brain's decision; pwm = how strongly it wants to avoid |
| PC → Arduino | `?` | identify yourself |

If the Arduino hears no command for 600 ms it switches the LED off itself and blinks its onboard
LED, so a stopped or crashed brain never leaves an actuator running. The PC always reads the
newest reading and skips any backlog, so the brain works on the present even if it runs slower
than the sensor.

## From an LED to motors

The `pwm` value is already the brain's avoidance drive (0–255). To steer a small robot:

* Replace the LED on D6 with a motor driver (L298N, TB6612) input; map `pwm` to a turn or a stop.
* For left/right steering, add a second HC-SR04 and drive `LPLC2`/`LC4` on the **L** and **R**
  sides separately in `flybridge/eyes.py` (the populations are already split by side). The fly's
  looming responses are side-specific, so the brain can then tell which way to turn.
* In `flybridge/learning.py`, add output units for the new actions (e.g. TURN_LEFT, TURN_RIGHT);
  the judge in `judge()` decides what earns dopamine.

## Tuning knobs (`flybridge/config.py`)

| Setting | Default | What it does |
|---|---|---|
| `near_cm` | 20 | "too near" threshold (`--near`) |
| `object_size_cm` | 20 | assumed obstacle size, which sets the looming angle |
| `steps_per_reading` | 4 | 20 ms brain steps per reading; keep × 20 ms ≈ `sample_ms` for real time |
| `components` | 80 | principal components of motor activity the readout learns on |
| `learning_rate` | 0.3 | step size of each dopamine update |
| `punish_crash` / `punish_false_alarm` | −1 / −0.5 | how bad each mistake is; their ratio sets how cautious it becomes |
| `exploration` | 0.05 | how often it tries the other action while training |
| `calibration_readings` | 300 | readings watched before learning starts |

## Development

```sh
python -m pytest tests                          # 19 tests; the real-brain ones need `flybrain download`
python tools/fake_arduino.py                    # a virtual Arduino on a pty (Linux/macOS)
python -m flybridge --port /dev/pts/N           # ...then drive it exactly like real hardware
tools/check_sketch.sh /path/to/ArduinoCore-avr  # compile the sketch with avr-gcc, no IDE needed
```

## Limits worth knowing

* One ultrasonic sensor has no left or right, so both eyes get the same stimulus.
* The eye interface drives the looming neurons directly. `flybrain` notes that photoreceptor
  input fades at the lamina in a spiking model, so, like other embodied fly models, the visual
  front end is a model and everything downstream is the connectome.
* A step costs ~6 ms on 4 CPU cores here (~85 ms per reading including learning, against an
  80 ms sensor). A much slower PC will skip readings rather than fall behind; `--device cuda`
  with `pip install "flybrain[gpu]"` is ~10× faster on an NVIDIA GPU.

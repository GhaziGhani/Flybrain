"""python -m flybridge --sim                    simulated Arduino, learning (a good first run)
python -m flybridge --port COM5              real Arduino, learning; resumes from the saved model
python -m flybridge --port COM5 --mode run   use what it learned, no more learning
python -m flybridge --sim --mode innate      no training: LED follows the giant fiber reflex
python -m flybridge --list-ports             find your Arduino's port
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import Config
from .learning import POPULATIONS, DopaminePolicy
from .link import SerialLink, SimArduino
from .loop import MODES, FlyLoop


def list_ports() -> None:
    from serial.tools import list_ports as lp
    ports = list(lp.comports())
    if not ports:
        print("no serial ports found; is the Arduino plugged in?")
    for p in ports:
        print(f"{p.device:<16} {p.description}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="flybridge", description="A real fruit fly connectome driving an Arduino.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--port", help="Arduino serial port, e.g. COM5 or /dev/ttyACM0")
    src.add_argument("--sim", action="store_true", help="use a simulated Arduino and obstacle instead of hardware")
    src.add_argument("--list-ports", action="store_true", help="list serial ports and exit")
    ap.add_argument("--mode", choices=MODES, default="train")
    ap.add_argument("--model", type=Path, default=Path("flybridge_model.npz"),
                    help="where learned synapses are saved and resumed from (default %(default)s)")
    ap.add_argument("--readings", type=int, default=0, help="stop after this many readings (0 = until Ctrl+C)")
    ap.add_argument("--near", type=float, default=Config.near_cm, help="'too near' threshold in cm (default %(default)s)")
    ap.add_argument("--readout", choices=sorted(POPULATIONS), default=Config.readout,
                    help="which neurons the decision is read from (default %(default)s)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--fast", action="store_true", help="simulation only: run as fast as possible, not at sensor speed")
    ap.add_argument("--no-dopamine-neurons", action="store_true",
                    help="learn without also firing the real PAM/PPL1 neurons inside the connectome")
    ap.add_argument("--dashboard-port", type=int, default=8765)
    ap.add_argument("--no-dashboard", action="store_true")
    ap.add_argument("--log", type=Path, help="CSV log of every reading (default logs/<mode>-<time>.csv)")
    ap.add_argument("--device", default="cpu", help="flybrain device: cpu, cuda or auto")
    ap.add_argument("--seed", type=int, default=Config.seed)
    args = ap.parse_args(argv)

    if args.list_ports:
        list_ports()
        return 0
    if not args.port and not args.sim:
        ap.error("pass --port PORT for a real Arduino, or --sim (see --list-ports)")

    cfg = Config(near_cm=args.near, readout=args.readout, seed=args.seed,
                 inject_dopamine=not args.no_dopamine_neurons)

    policy = DopaminePolicy(cfg, seed=cfg.seed)
    if args.mode != "innate" and args.model.exists():
        policy.load(args.model)
        print(f"loaded {args.model}: {policy.updates} dopamine updates so far")
    elif args.mode == "run":
        print(f"no model at {args.model}; train first (--mode train)", file=sys.stderr)
        return 2

    print("loading the MaleCNS connectome (first run downloads ~260 MB to ~/fly-data)...")
    from flybrain import FlyBrain
    brain = FlyBrain(device=args.device, sensory_input=False, seed=cfg.seed)
    print(f"brain ready: {brain.n:,} neurons")

    if args.sim:
        link = SimArduino(cfg.near_cm, seed=cfg.seed, period_ms=cfg.sample_ms, realtime=not args.fast)
    else:
        link = SerialLink(args.port, args.baud)
        if link.version is None:
            print(f"warning: no HELLO from {args.port}; is fly_bridge.ino uploaded? continuing anyway")
        else:
            print(f"arduino on {args.port}: FlyBridge protocol {link.version}")

    log = args.log or Path("logs") / f"{args.mode}-{time.strftime('%Y%m%d-%H%M%S')}.csv"
    log.parent.mkdir(parents=True, exist_ok=True)
    loop = FlyLoop(brain, link, cfg, mode=args.mode, policy=policy, log_path=log)

    dashboard = None
    if not args.no_dashboard:
        from .dashboard import Dashboard
        dashboard = Dashboard(loop, port=args.dashboard_port)
        dashboard.start()
        print(f"dashboard: {dashboard.url}")
    print(f"mode {args.mode}, readout {cfg.readout}, near < {cfg.near_cm} cm, logging to {log}")
    print("Ctrl+C to stop" + (" (learned synapses are saved on exit)" if args.mode == "train" else ""))

    def save():
        if args.mode == "train" and policy.ready:
            policy.save(args.model)

    interactive = sys.stdout.isatty()
    n, t0, last_print = 0, time.monotonic(), 0.0
    try:
        while not args.readings or n < args.readings:
            rec = loop.cycle()
            if rec is None:
                print("\nno reading from the Arduino for 1 s; check wiring and port", file=sys.stderr)
                continue
            n += 1
            if args.mode == "train" and n % 200 == 0:
                save()
            now = time.monotonic()
            if now - last_print > 1.0 or (args.readings and n == args.readings):
                last_print = now
                acc = loop.accuracy
                t = loop.totals
                line = (f"[{loop.phase:>13}] {rec['cm']:6.1f} cm  LED {'ON ' if rec['led'] else 'off'}  "
                        f"p={rec['p_avoid']:.2f}  acc={'  - ' if acc is None else f'{acc:4.0%}'}  "
                        f"avoided {t['avoided']} crash {t['crash']} false alarm {t['false alarm']}  "
                        f"{(now - t0) / n * 1000:4.0f} ms/reading")
                print(("\r" + line) if interactive else line, end="" if interactive else "\n", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        print()
        save()
        link.close()
        loop.close()
        if dashboard:
            dashboard.stop()
        if args.mode == "train" and policy.ready:
            print(f"saved {args.model} ({policy.updates} dopamine updates)")
        print(f"log: {log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""A stand-in Arduino that speaks the exact FlyBridge serial protocol over a virtual serial
port, for testing the real serial path without hardware (Linux and macOS).

    python tools/fake_arduino.py
    # prints a port like /dev/pts/5; in another terminal:
    python -m flybridge --port /dev/pts/5

It behaves like fly_bridge.ino: streams D lines every 80 ms from a simulated obstacle,
obeys C lines, answers "?", and turns its virtual LED off after 600 ms without commands.
"""
from __future__ import annotations

import os
import select
import sys
import threading
import time
import tty
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flybridge.link import PROTOCOL_VERSION, ObstacleWorld  # noqa: E402


class FakeArduino:
    def __init__(self, fd: int, near_cm: float = 20.0, seed: int = 0, period_ms: int = 80, failsafe_ms: int = 600):
        self.fd = fd
        self.world = ObstacleWorld(near_cm, seed)
        self.period = period_ms / 1000
        self.failsafe = failsafe_ms / 1000
        self.led = False
        self.pwm = 0
        self.commands = 0
        self.failsafe_trips = 0
        self.last_command = None
        self.started = time.monotonic()
        self._buffer = b""

    def _write(self, text: str) -> None:
        os.write(self.fd, text.encode("ascii"))

    def _handle(self, line: str) -> None:
        if line == "?":
            self._write(f"HELLO,FlyBridge,{PROTOCOL_VERSION}\n")
        elif line.startswith("C,"):
            try:
                led, pwm = (int(v) for v in line[2:].split(","))
            except ValueError:
                return
            self.led, self.pwm = bool(led), max(0, min(255, pwm))
            self.commands += 1
            self.last_command = time.monotonic()

    def run(self, stop: threading.Event) -> None:
        self._write(f"HELLO,FlyBridge,{PROTOCOL_VERSION}\n")
        next_sample = time.monotonic()
        while not stop.is_set():
            timeout = max(0.0, next_sample - time.monotonic())
            ready, _, _ = select.select([self.fd], [], [], timeout)
            if ready:
                try:
                    self._buffer += os.read(self.fd, 256)
                except OSError:
                    return
                while b"\n" in self._buffer:
                    raw, self._buffer = self._buffer.split(b"\n", 1)
                    self._handle(raw.decode("ascii", "replace").strip())
            now = time.monotonic()
            if now >= next_sample:
                next_sample += self.period
                cm = self.world.advance(self.period)
                millis = int((now - self.started) * 1000)
                self._write(f"D,{millis},{cm:.1f}\n")
            if self.led and self.last_command and now - self.last_command > self.failsafe:
                self.led, self.pwm = False, 0
                self.failsafe_trips += 1


def open_virtual_port():
    """(master fd for the fake Arduino, slave path for the PC side)."""
    master, slave = os.openpty()
    tty.setraw(slave)
    return master, slave, os.ttyname(slave)


def main() -> None:
    master, slave, path = open_virtual_port()
    arduino = FakeArduino(master)
    stop = threading.Event()
    print(f"virtual Arduino on {path}\n  run: python -m flybridge --port {path}\nCtrl+C to stop", flush=True)
    thread = threading.Thread(target=arduino.run, args=(stop,), daemon=True)
    thread.start()
    try:
        while True:
            time.sleep(1)
            state = "ON " if arduino.led else "off"
            print(f"\robstacle {arduino.world.distance:6.1f} cm   LED {state} pwm {arduino.pwm:3d}   "
                  f"commands {arduino.commands}", end="", flush=True)
    except KeyboardInterrupt:
        stop.set()
        print()


if __name__ == "__main__":
    main()

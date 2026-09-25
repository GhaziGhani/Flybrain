"""PC <-> Arduino interface.

Line protocol, 115200 baud, one message per line:

  Arduino -> PC   HELLO,FlyBridge,<version>     on boot, and in reply to "?"
                  D,<millis>,<cm>               one ultrasonic reading; cm = -1.0 means no echo
  PC -> Arduino   C,<led 0|1>,<pwm 0-255>       what the brain decided; pwm = how strongly
                  ?                             ask the Arduino to identify itself

The Arduino never decides anything. If it hears no C line for 600 ms it turns the
LED off by itself, so a crashed or paused brain can't leave an actuator running.

SimArduino speaks the same interface without hardware: a virtual HC-SR04 watching an
obstacle that drifts toward and away from the fly, with sensor noise and dropouts.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass

import numpy as np

PROTOCOL_VERSION = 1


@dataclass
class Reading:
    millis: int
    cm: float | None


def parse_line(line: str):
    """('D', Reading) | ('HELLO', version) | (None, raw) for anything unrecognised."""
    line = line.strip()
    parts = line.split(",")
    if parts[0] == "D" and len(parts) == 3:
        try:
            millis = int(parts[1])
            cm = float(parts[2])
        except ValueError:
            return None, line
        return "D", Reading(millis, cm if cm > 0 else None)
    if parts[0] == "HELLO" and len(parts) >= 3:
        return "HELLO", parts[2]
    return None, line


def format_command(led: bool, pwm: int) -> str:
    return f"C,{1 if led else 0},{int(np.clip(pwm, 0, 255))}\n"


class MedianFilter:
    """HC-SR04s throw the occasional wild reading; a 3-sample median removes single spikes.
    Missing echoes count as 'nothing in front' (max range)."""

    def __init__(self, max_range_cm: float, size: int = 3):
        self.max_range = max_range_cm
        self.window: deque = deque(maxlen=size)

    def __call__(self, cm: float | None) -> float:
        self.window.append(self.max_range if cm is None else min(cm, self.max_range))
        return float(np.median(self.window))


class SerialLink:
    def __init__(self, port: str, baud: int = 115200, reset_wait: float = 2.0, handshake: bool = True):
        import serial
        self.serial = serial.Serial(port, baud, timeout=0.05)
        self.port = port
        self.version = None
        self.led = False
        self.pwm = 0
        self._buffer = b""
        if reset_wait:
            time.sleep(reset_wait)   # opening the port resets most Arduinos; give the bootloader time
        self.serial.reset_input_buffer()
        if handshake:
            self.serial.write(b"?\n")
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and self.version is None:
                for line in self._lines():
                    kind, value = parse_line(line)
                    if kind == "HELLO":
                        self.version = value

    def _lines(self):
        """Complete lines received so far; a half-received line waits in the buffer."""
        chunk = self.serial.read(self.serial.in_waiting or 1)
        if chunk:
            self._buffer += chunk
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            yield line.decode("ascii", "replace")

    def read(self, timeout: float = 1.0) -> Reading | None:
        """The newest reading. Older queued readings are skipped so the brain always
        works on the present, never on a backlog."""
        deadline = time.monotonic() + timeout
        latest = None
        while True:
            for line in self._lines():
                kind, value = parse_line(line)
                if kind == "D":
                    latest = value
                elif kind == "HELLO":
                    self.version = value
            if latest is not None and self.serial.in_waiting == 0 and b"\n" not in self._buffer:
                return latest
            if time.monotonic() > deadline:
                return latest

    def send(self, led: bool, pwm: int) -> None:
        self.led, self.pwm = bool(led), int(pwm)
        self.serial.write(format_command(led, pwm).encode("ascii"))

    def close(self) -> None:
        try:
            self.send(False, 0)
        finally:
            self.serial.close()


class ObstacleWorld:
    """An obstacle drifting toward and away from the sensor at 5-40 cm/s, spending
    about as much time closer than `near_cm` as farther, so both outcomes get practised."""

    def __init__(self, near_cm: float = 20.0, seed: int = 0):
        self.rng = np.random.default_rng(seed)
        self.near = near_cm
        self.distance = 80.0
        self._new_target()

    def _new_target(self) -> None:
        if self.rng.random() < 0.5:
            self.target = self.rng.uniform(4.0, self.near * 0.85)
        else:
            self.target = self.rng.uniform(self.near * 1.15, self.near * 4.5)
        self.speed = self.rng.uniform(5.0, 40.0)
        self.hold = self.rng.uniform(0.0, 1.5)

    def advance(self, seconds: float) -> float:
        gap = self.target - self.distance
        step = self.speed * seconds
        if abs(gap) <= step:
            self.distance = self.target
            self.hold -= seconds
            if self.hold <= 0:
                self._new_target()
        else:
            self.distance += math.copysign(step, gap)
        return self.distance


class SimArduino:
    """Same interface as SerialLink: read() returns one sensor reading, send() drives the LED."""

    def __init__(self, near_cm: float = 20.0, seed: int = 0, period_ms: int = 80, realtime: bool = False):
        self.world = ObstacleWorld(near_cm, seed)
        self.rng = np.random.default_rng(seed + 1)
        self.period_ms = period_ms
        self.realtime = realtime
        self.millis = 0
        self.version = f"sim-{PROTOCOL_VERSION}"
        self.port = "simulated"
        self.led = False
        self.pwm = 0
        self._next = time.monotonic()

    @property
    def true_distance(self) -> float:
        return self.world.distance

    def read(self, timeout: float = 1.0) -> Reading:
        if self.realtime:
            self._next += self.period_ms / 1000
            delay = self._next - time.monotonic()
            if delay > 0:
                time.sleep(delay)
        self.millis += self.period_ms
        d = self.world.advance(self.period_ms / 1000)
        roll = self.rng.random()
        if roll < 0.02:
            return Reading(self.millis, None)
        if roll < 0.03:
            return Reading(self.millis, float(self.rng.uniform(2, 300)))
        return Reading(self.millis, round(max(2.0, d + self.rng.normal(0, 0.8)), 1))

    def send(self, led: bool, pwm: int) -> None:
        self.led, self.pwm = bool(led), int(pwm)

    def close(self) -> None:
        self.send(False, 0)

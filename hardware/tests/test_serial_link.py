"""The real SerialLink talking to a fake Arduino over a virtual serial port (pty)."""
import os
import sys
import threading
import time

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="needs a pty")

from fake_arduino import FakeArduino, open_virtual_port  # noqa: E402
from flybridge.link import SerialLink  # noqa: E402


@pytest.fixture
def arduino():
    master, slave, path = open_virtual_port()
    fake = FakeArduino(master, seed=3, period_ms=40, failsafe_ms=300)
    stop = threading.Event()
    thread = threading.Thread(target=fake.run, args=(stop,), daemon=True)
    thread.start()
    yield fake, path
    stop.set()
    thread.join(1)
    os.close(master)
    os.close(slave)


def test_handshake_readings_and_commands(arduino):
    fake, path = arduino
    link = SerialLink(path, reset_wait=0)
    assert link.version == "1"
    readings = [link.read(timeout=1.0) for _ in range(5)]
    assert all(r is not None and r.cm is not None for r in readings)
    assert readings[-1].millis > readings[0].millis
    link.send(True, 200)
    time.sleep(0.15)
    assert fake.led and fake.pwm == 200 and fake.commands >= 1
    link.send(False, 0)
    time.sleep(0.15)
    assert not fake.led
    link.serial.close()


def test_arduino_failsafe_turns_led_off_when_brain_goes_quiet(arduino):
    fake, path = arduino
    link = SerialLink(path, reset_wait=0)
    link.send(True, 255)
    time.sleep(0.1)
    assert fake.led
    time.sleep(0.5)
    assert not fake.led and fake.failsafe_trips == 1
    link.serial.close()


def test_read_skips_backlog_to_stay_current(arduino):
    fake, path = arduino
    link = SerialLink(path, reset_wait=0)
    time.sleep(0.5)
    reading = link.read(timeout=1.0)
    newest_possible = int((time.monotonic() - fake.started) * 1000)
    assert newest_possible - reading.millis < 150
    link.serial.close()

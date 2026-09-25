from flybridge.link import MedianFilter, Reading, format_command, parse_line


def test_parse_distance():
    assert parse_line("D,1234,17.5\r\n") == ("D", Reading(1234, 17.5))


def test_parse_no_echo_is_none():
    assert parse_line("D,80,-1.0") == ("D", Reading(80, None))


def test_parse_hello():
    assert parse_line("HELLO,FlyBridge,1") == ("HELLO", "1")


def test_parse_garbage_is_ignored():
    assert parse_line("D,abc,1")[0] is None
    assert parse_line("D,1")[0] is None
    assert parse_line("")[0] is None


def test_format_command_clamps():
    assert format_command(True, 300) == "C,1,255\n"
    assert format_command(False, -5) == "C,0,0\n"


def test_median_filter_removes_a_single_spike():
    f = MedianFilter(max_range_cm=400)
    assert f(30.0) == 30.0
    assert f(31.0) == 30.5
    assert f(250.0) == 31.0
    assert f(32.0) == 32.0


def test_median_filter_treats_missing_echo_as_max_range():
    f = MedianFilter(max_range_cm=400)
    for _ in range(3):
        value = f(None)
    assert value == 400.0

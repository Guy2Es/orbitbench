# tests/test_epoch.py
"""UTCGregorian epochs as integer milliseconds."""
import pytest

from orbitbench.epoch import add_seconds, format_epoch, parse_epoch


def test_round_trip():
    for text in ("01 Jan 2026 00:00:00.000", "29 Feb 2028 23:59:59.999", "31 Dec 2099 12:34:56.789"):
        assert format_epoch(parse_epoch(text)) == text


def test_fraction_is_optional_and_padded():
    assert parse_epoch("01 Jan 2026 00:00:00") == parse_epoch("01 Jan 2026 00:00:00.000")
    assert parse_epoch("01 Jan 2026 00:00:00.5") == parse_epoch("01 Jan 2026 00:00:00.500")


def test_add_seconds_rounds_to_the_millisecond():
    assert add_seconds("01 Jan 2026 00:00:00.000", 19048.4826) == "01 Jan 2026 05:17:28.483"


def test_add_seconds_crosses_a_day():
    assert add_seconds("01 Jan 2026 23:59:59.500", 1.0) == "02 Jan 2026 00:00:00.500"


@pytest.mark.parametrize("text", ["31 Feb 2026 00:00:00.000", "01 Foo 2026 00:00:00.000", "1 Jan 2026 00:00:00",
                                  "01 Jan 2026 25:00:00.000", "2026-01-01T00:00:00", ""])
def test_malformed_or_impossible_epochs_are_rejected(text):
    with pytest.raises(ValueError):
        parse_epoch(text)

# src/orbitbench/reference/tle.py
"""Synthetic two-line element sets with valid checksums, and the SGP4 state read from them."""
from sgp4.api import Satrec


def checksum(line: str) -> int:
    """Modulo-10 sum of the digits of the first 68 columns, each '-' counting 1."""
    return sum(int(c) if c.isdigit() else 1 if c == "-" else 0 for c in line[:68]) % 10


def _bstar_field(mantissa: int, exponent: int) -> str:
    """The 8-column implied-decimal field: 0.<mantissa> x 10^exponent."""
    return f" {mantissa:05d}{'-' if exponent < 0 else '+'}{abs(exponent)}"


def build_tle(*, satnum: int, year: int, day: float, bstar_mantissa: int, bstar_exponent: int, element_set: int,
              inc_deg: float, raan_deg: float, ecc: float, aop_deg: float, mean_anomaly_deg: float,
              mean_motion_rev_day: float, rev_number: int) -> tuple:
    """Two 69-column lines. `day` is the day of the year with its fraction, 1.0 being 1 January 00:00."""
    line1 = (f"1 {satnum:05d}U 26001A   {year % 100:02d}{day:012.8f}  .00000000  00000-0 "
             f"{_bstar_field(bstar_mantissa, bstar_exponent)} 0 {element_set:4d}")
    line2 = (f"2 {satnum:05d} {inc_deg:8.4f} {raan_deg:8.4f} {round(ecc * 1e7):07d} {aop_deg:8.4f} "
             f"{mean_anomaly_deg:8.4f} {mean_motion_rev_day:11.8f}{rev_number:5d}")
    return line1 + str(checksum(line1)), line2 + str(checksum(line2))


def sgp4_state(line1: str, line2: str, minutes_after_epoch: float) -> tuple:
    """Position (km) and velocity (km/s) in the TEME frame, `minutes_after_epoch` after the TLE epoch."""
    sat = Satrec.twoline2rv(line1, line2)
    err, pos, vel = sat.sgp4(sat.jdsatepoch, sat.jdsatepochF + minutes_after_epoch / 1440.0)
    if err != 0:
        raise ValueError(f"SGP4 failed with code {err}")
    return tuple(pos), tuple(vel)

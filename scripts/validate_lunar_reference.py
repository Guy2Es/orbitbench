"""Independent check of the lunar_impact table (amendment of 8 November 2026 in docs/lunar_baseline_rule.md).
Usage: python scripts/validate_lunar_reference.py --data DIR [--variants base,me_plus,me_minus] [--seeds 0-14]
DIR holds grgm900c.cof, DE405AllPlanets.bsp, de421.bsp and SPICELunaCurrentKernel.bpc (copy them from /opt/gmat/data of the
orbitbench-gmat image). Needs numpy, scipy, numba, jplephem, pyyaml. No GMAT code is used."""
import math
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from numba import njit
from jplephem.pck import PCK
from jplephem.spk import SPK
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline

HERE = Path(".")   # set from --data in work()
TT_MINUS_UTC = 69.184          # s, 2026
PCK_SHIFT_S = 59.75            # empirical shift that matches GMAT's rotation to 0.6 arcsec (see moonrot.py / pa.py)
MU_LUNA_DE = 4902.8005821478   # km^3/s^2, Luna.Mu in GMAT
MU_EARTH = 398600.4415
MU_SUN = 132712440017.99
R_MOON = 1737.4


def read_cof(path, nmax):
    gm = rad = None
    C = np.zeros((nmax + 2, nmax + 2)); S = np.zeros((nmax + 2, nmax + 2)); C[0, 0] = 1.0
    for line in open(path):
        p = line.split()
        if line.startswith("POTFIELD"):
            gm, rad = float(p[2]) / 1e9, float(p[3]) / 1e3        # km^3/s^2, km
        elif line.startswith("RECOEF"):
            n, m = int(line[6:11]), int(line[11:14])          # fixed columns: "RECOEF  100100" is n=100, m=100
            cs, ss = (float(x) for x in re.findall(r"[-+]?\d\.\d+e[-+]\d+", line[14:]))
            if n <= nmax and m <= nmax:
                f = math.exp(0.5 * (math.log(2 - (m == 0)) + math.log(2 * n + 1) + math.lgamma(n - m + 1) - math.lgamma(n + m + 1)))
                C[n, m] = cs * f; S[n, m] = ss * f      # un-normalise
    return gm, rad, C, S


@njit(cache=True)
def grav_acc(x, y, z, C, S, nmax, mu, R):
    """Acceleration (km/s^2) of the harmonic field in the body-fixed frame (Montenbruck & Gill 3.3)."""
    r2 = x * x + y * y + z * z
    rho = R * R / r2
    x0 = R * x / r2; y0 = R * y / r2; z0 = R * z / r2
    V = np.zeros((nmax + 3, nmax + 3)); W = np.zeros((nmax + 3, nmax + 3))
    V[0, 0] = R / math.sqrt(r2)
    for m in range(nmax + 2):
        if m > 0:
            V[m, m] = (2 * m - 1) * (x0 * V[m - 1, m - 1] - y0 * W[m - 1, m - 1])
            W[m, m] = (2 * m - 1) * (x0 * W[m - 1, m - 1] + y0 * V[m - 1, m - 1])
        if m <= nmax + 1:
            V[m + 1, m] = (2 * m + 1) * z0 * V[m, m]
            W[m + 1, m] = (2 * m + 1) * z0 * W[m, m]
        for n in range(m + 2, nmax + 2):
            V[n, m] = ((2 * n - 1) * z0 * V[n - 1, m] - (n + m - 1) * rho * V[n - 2, m]) / (n - m)
            W[n, m] = ((2 * n - 1) * z0 * W[n - 1, m] - (n + m - 1) * rho * W[n - 2, m]) / (n - m)
    ax = ay = az = 0.0
    for n in range(nmax + 1):
        for m in range(n + 1):
            if m == 0:
                ax -= C[n, 0] * V[n + 1, 1]
                ay -= C[n, 0] * W[n + 1, 1]
                az -= (n + 1) * C[n, 0] * V[n + 1, 0]
            else:
                f = 0.5 * (n - m + 1) * (n - m + 2)
                ax += 0.5 * (-C[n, m] * V[n + 1, m + 1] - S[n, m] * W[n + 1, m + 1]) + f * (C[n, m] * V[n + 1, m - 1] + S[n, m] * W[n + 1, m - 1])
                ay += 0.5 * (-C[n, m] * W[n + 1, m + 1] + S[n, m] * V[n + 1, m + 1]) + f * (-C[n, m] * W[n + 1, m - 1] + S[n, m] * V[n + 1, m - 1])
                az += (n - m + 1) * (-C[n, m] * V[n + 1, m] - S[n, m] * W[n + 1, m])
    k = mu / (R * R)
    return ax * k, ay * k, az * k


def jd_utc(s):
    t = datetime.strptime(s, "%d %b %Y %H:%M:%S.%f")
    a = (14 - t.month) // 12; y = t.year + 4800 - a; m = t.month + 12 * a - 3
    jdn = t.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn - 0.5 + (t.hour + t.minute / 60 + t.second / 3600) / 24


def Rz(t): c, s = np.cos(t), np.sin(t); return np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
def Rx(t): c, s = np.cos(t), np.sin(t); return np.array([[1, 0, 0], [0, c, s], [0, -s, c]])


def kep2cart(el, mu):
    a, e, i, raan, aop, ta = el[0], el[1], *[math.radians(v) for v in el[2:]]
    p = a * (1 - e * e); r = p / (1 + e * math.cos(ta))
    rp = np.array([r * math.cos(ta), r * math.sin(ta), 0.0])
    vp = np.array([-math.sqrt(mu / p) * math.sin(ta), math.sqrt(mu / p) * (e + math.cos(ta)), 0.0])
    Q = Rz(-raan) @ Rx(-i) @ Rz(-aop)      # perifocal -> inertial
    return Q @ rp, Q @ vp


class Model:
    def __init__(self, nmax=50, ephem="DE405AllPlanets.bsp", pa_offset=None, mu_field="file", mu_elem="de",
                 horizon_days=61.0, grid_min=10.0):
        self.nmax = nmax
        gm, rad, self.C, self.S = read_cof(HERE / "grgm900c.cof", nmax)
        self.R = rad
        self.mu_field = gm if mu_field == "file" else MU_LUNA_DE
        self.mu_elem = MU_LUNA_DE if mu_elem == "de" else gm
        self.spk = SPK.open(str(HERE / ephem))
        self.pck = PCK.open(str(HERE / "SPICELunaCurrentKernel.bpc")).segments[0]
        self.pa_offset = np.eye(3) if pa_offset is None else pa_offset   # applied after the PA rotation (e.g. PA -> ME)
        self.horizon = horizon_days; self.grid_min = grid_min

    def setup(self, epoch):
        self.jd0 = jd_utc(epoch) + TT_MINUS_UTC / 86400
        n = int(self.horizon * 1440 / self.grid_min) + 3
        t = np.arange(n) * self.grid_min * 60.0
        jd = self.jd0 + t / 86400
        k = self.spk
        moon_emb = k[3, 301].compute(jd)               # (3, n)
        earth_emb = k[3, 399].compute(jd)
        sun_ssb = k[0, 10].compute(jd)
        emb_ssb = k[0, 3].compute(jd)
        earth_rel = earth_emb - moon_emb
        sun_rel = sun_ssb - (emb_ssb + moon_emb)
        rots = np.empty((n, 9))
        for j in range(n):
            ang = self.pck.compute(self.jd0 - TT_MINUS_UTC / 86400 + PCK_SHIFT_S / 86400 + t[j] / 86400, 0.0)[0]
            R = self.pa_offset @ (Rz(ang[2]) @ Rx(ang[1]) @ Rz(ang[0]))
            rots[j] = R.ravel()
        self.t_grid = t
        self.s_earth = CubicSpline(t, earth_rel.T); self.s_sun = CubicSpline(t, sun_rel.T); self.s_rot = CubicSpline(t, rots)

    def rhs(self, t, y):
        r = y[:3]; v = y[3:]
        Rm = self.s_rot(t).reshape(3, 3)
        rf = Rm @ r
        ax, ay, az = grav_acc(rf[0], rf[1], rf[2], self.C, self.S, self.nmax, self.mu_field, self.R)
        a = Rm.T @ np.array([ax, ay, az])
        for mu_b, rb in ((MU_EARTH, self.s_earth(t)), (MU_SUN, self.s_sun(t))):
            d = rb - r
            a += mu_b * (d / np.linalg.norm(d) ** 3 - rb / np.linalg.norm(rb) ** 3)
        return np.concatenate([v, a])

    def periapsis_radius(self, y, mu):
        r = y[:3]; v = y[3:]
        rn = np.linalg.norm(r)
        h = np.cross(r, v)
        ev = np.cross(v, h) / mu - r / rn
        e = np.linalg.norm(ev)
        p = h @ h / mu
        return p / (1 + e)

    def impact_days(self, params, rtol=1e-12, atol=1e-10, max_days=60.0):
        self.setup(params["epoch"])
        el = [params[k] for k in ("sma_km", "ecc", "inc_deg", "raan_deg", "aop_deg", "ta_deg")]
        r0, v0 = kep2cart(el, self.mu_elem)
        mu_p = self.mu_elem
        ev = lambda t, y: self.periapsis_radius(y, mu_p) - R_MOON
        ev.terminal = True; ev.direction = -1
        sol = solve_ivp(self.rhs, (0.0, max_days * 86400.0), np.concatenate([r0, v0]), method="DOP853", rtol=rtol,
                        atol=atol, events=ev, first_step=30.0, max_step=300.0)
        if sol.t_events[0].size:
            return float(sol.t_events[0][0] / 86400.0)
        return None


def parse_seeds(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def offset(sign):
    """Small rotation from the principal-axes frame to the mean-Earth frame (NAIF moon_080317.tf, DE421), either sign."""
    w = sign * np.radians(np.array([0.30, 78.56, 67.92]) / 3600)
    K = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
    return np.eye(3) - K


VARIANTS = {"base": {}, "de421": {"ephem": "de421.bsp"}, "me_plus": {"pa_offset": offset(+1)},
            "me_minus": {"pa_offset": offset(-1)}}


def work(args):
    data, name, seed, params = args
    global HERE
    HERE = Path(data)
    return name, seed, Model(**VARIANTS[name]).impact_days(params)


def main():
    import argparse
    from multiprocessing import Pool
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--variants", default="base,me_plus,me_minus")
    ap.add_argument("--seeds", default="all", help="e.g. 0-14, or all (every seed of the table)")
    ap.add_argument("--table", default=None, help="table to check (default: the public table of the development seeds)")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    path = Path(args.table) if args.table else (Path(__file__).resolve().parent.parent / "src" / "orbitbench" / "families"
                                                / "templates" / "lunar_impact_table.yaml")
    table = yaml.safe_load(path.read_text(encoding="utf-8"))
    seeds = sorted(table) if args.seeds == "all" else [s for s in parse_seeds(args.seeds) if s in table]
    names = args.variants.split(",")
    jobs = [(args.data, n, s, table[s]["params"]) for n in names for s in seeds]
    with Pool(args.workers) as pool:
        res = {(n, s): d for n, s, d in pool.map(work, jobs, chunksize=1)}
    worst = 0.0
    bad = []
    for s in seeds:
        g = table[s]["impact_days"]
        cells = []
        for n in names:
            d = res[(n, s)]
            cells.append(f"{n} {'none' if d is None else '%.4f' % d}")
            if n == "base":
                worst = float("inf") if d is None else max(worst, abs(d - g))
        base = res.get(("base", s))
        for n in names:
            if n.startswith("me_") and (res[(n, s)] is None or base is None or abs(res[(n, s)] - base) >= 0.3):
                bad.append(s)
                break
        print(f"seed {s:>8}  GMAT {g:8.4f}  " + "  ".join(cells))
    print(f"largest difference of the base variant to GMAT: {worst:.4f} day")
    if bad:
        print("seeds that move by 0.3 day or more under the orientation offset (to redo): " + ",".join(map(str, sorted(set(bad)))))


if __name__ == "__main__":
    main()

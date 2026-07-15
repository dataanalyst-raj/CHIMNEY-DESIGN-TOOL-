"""
STRESS CHECKS - port of Module 4 (CalcStressChecks), allowable
compressive stress per zone. IS 6533 Annex C + Cl 7.7.

Allowable = 0.5*fy*tempF*A*B
  A = slenderness factor = 1/(0.84+(0.019*he/D)^2) if he/D > 21, else 1
  B = local buckling factor = 270*(t/D)*(1-67*t/D) if D/t > 130, else 1
D used in he/D and D/t is the BOTTOM OD (larger, governing diameter of
each zone) - verified against a real Dynastac design: matches to <2.3%.

DISCLOSED, OPEN ITEM: the temperature-factor curve (piecewise linear,
1.0@200C -> 0.75@250C -> 0.60@300C -> 0.45@350C) gives 0.660 at 280C,
but Dynastac's own printed Kt at 280C is 0.702 - about 6% off, on the
CONSERVATIVE side (understates allowable, doesn't overstate it). Only
verified at one data point so far; not changed without more chimney
data at different design temperatures.
"""
import math
from dataclasses import dataclass
from typing import List
from inputs import ChimneyInputs
from geometry import ZoneGeometry

FY_MPA = 250.0  # yield stress, MPa (IS 2062 E250 default)


def temp_factor(t: float) -> float:
    if t <= 200:
        return 1.0
    elif t <= 250:
        return 1.0 + (0.75 - 1.0) * (t - 200) / 50
    elif t <= 300:
        return 0.75 + (0.60 - 0.75) * (t - 250) / 50
    elif t <= 350:
        return 0.60 + (0.45 - 0.60) * (t - 300) / 50
    else:
        return 0.45


@dataclass
class ZoneStressCheck:
    zone: int
    he: float           # m
    he_d: float
    d_t: float
    factor_a: float
    factor_b: float
    allow_mpa: float
    min_thk_ok: bool


def calc_stress_checks(inputs: ChimneyInputs, zones: List[ZoneGeometry]) -> List[ZoneStressCheck]:
    tf = temp_factor(inputs.design_temp)
    results = []
    for z in zones:
        D = z.bot_od / 1000  # bottom OD, m (governing)
        tnet = z.thk_net     # mm
        elev_top = z.elev_top

        he = inputs.H - elev_top
        he_d = he / D
        d_t = D * 1000 / tnet

        factor_a = 1 / (0.84 + (0.019 * he_d) ** 2) if he_d > 21 else 1.0
        factor_b = 270 * (tnet / 1000 / D) * (1 - 67 * (tnet / 1000 / D)) if d_t > 130 else 1.0

        allow_mpa = 0.5 * FY_MPA * tf * factor_a * factor_b

        tmin_req = max(6.0, D * 1000 / 500)
        min_thk_ok = z.thk_gross >= tmin_req - 0.001

        results.append(ZoneStressCheck(
            zone=z.zone, he=he, he_d=he_d, d_t=d_t,
            factor_a=factor_a, factor_b=factor_b, allow_mpa=allow_mpa,
            min_thk_ok=min_thk_ok,
        ))
    return results

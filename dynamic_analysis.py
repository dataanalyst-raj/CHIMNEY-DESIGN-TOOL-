"""
DYNAMIC ANALYSIS - port of Module 8 (CalcDynamicAnalysis), Mode-1
modal dynamic wind load. IS 6533 Cl 8.3.

  P_dyn,j = M_j * eta_j * nu           <- FIXED: was M_j*xi*eta_j*nu
  eta_j   = y_j * SUM(y_k.Pstat_k.m_k) / SUM(y_k^2.M_k)

FIXED (14 Jul 2026): `xi` was being double-counted in the final load
formula. Verified by feeding a real design's own printed period/mass/
mode-shape/static-load values into this exact formula: WITH xi gave
~2.7x too high on every zone (a suspiciously constant ratio matching
xi itself); WITHOUT xi matched to within 0.3-2.7% on every zone. `xi`
is still computed and shown for reference (matches the real design's
printed value) but no longer multiplied into the load.

Cl 8.3.6: mode 1 alone is sufficient for chimneys < 80m.
"""
import math
from dataclasses import dataclass
from typing import List
from inputs import ChimneyInputs
from wind_loads import ZoneWindLoad
from natural_frequency import NaturalFrequencyResult

# Table 5: dynamic coefficient xi (e -> xi), lined/unlined
_T5_E = [0, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2]
_T5_XI_UNLINED = [1.3, 2.5, 3.1, 3.5, 3.75, 4.1, 4.3, 4.5, 4.7]
_T5_XI_LINED = [1.2, 1.7, 1.9, 2.1, 2.3, 2.45, 2.6, 2.7, 2.75]
# Table 6: pulsation coefficient m (height -> m), terrain A/B
_T6_H = [10, 20, 40, 60, 100, 200, 350]
_T6_M_A = [0.6, 0.6, 0.55, 0.48, 0.46, 0.42, 0.38]
_T6_M_B = [0.83, 0.83, 0.75, 0.65, 0.6, 0.54, 0.46]
# Table 7: space correlation nu (e -> nu)
_T7_E = [0.05, 0.1, 0.2]
_T7_NU = [0.7, 0.75, 0.75]


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])
    return ys[-1]


@dataclass
class DynamicAnalysisResult:
    e: float
    xi: float       # reference only, NOT multiplied into the load (see header)
    nu: float
    dyn_load: List[float]     # kg, per zone
    dyn_total: List[float]    # static + dynamic, kg, per zone


def calc_dynamic_analysis(inputs: ChimneyInputs, nf: NaturalFrequencyResult,
                           wind_loads: List[ZoneWindLoad], lining: str = "None",
                           terrain_type: str = "A") -> DynamicAnalysisResult:
    n = len(nf.mass)
    T1 = nf.nat_period
    e = T1 * inputs.vb / 1200
    is_lined = lining not in ("None", "")

    xi = _interp(e, _T5_E, _T5_XI_LINED if is_lined else _T5_XI_UNLINED)
    nu = _interp(max(0.05, min(0.2, e)), _T7_E, _T7_NU)

    eta_num = 0.0
    eta_den = 0.0
    for i in range(n):
        Mj = nf.mass[i]
        yj = nf.defl[i]
        pstat_k = wind_loads[i].force_kg
        hk = max(10.0, nf.elev_mid_cm[i] / 100)  # cm -> m
        mk = _interp(hk, _T6_H, _T6_M_B if terrain_type.upper() == "B" else _T6_M_A)
        eta_num += yj * pstat_k * mk
        eta_den += yj ** 2 * Mj

    dyn_load = []
    dyn_total = []
    for i in range(n):
        yj = nf.defl[i]
        Mj = nf.mass[i]
        eta_j = yj * eta_num / eta_den if eta_den > 0 else 0.0
        dl = Mj * eta_j * nu   # FIXED: no xi
        dyn_load.append(dl)
        dyn_total.append(wind_loads[i].force_kg + dl)

    return DynamicAnalysisResult(e=e, xi=xi, nu=nu, dyn_load=dyn_load, dyn_total=dyn_total)

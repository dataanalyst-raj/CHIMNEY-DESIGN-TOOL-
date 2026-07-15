"""
GOVERNING LOADS - port of the CORRECTED Module 9 (CalcWindEQLoads).
IS 6533 Cl 8 + IS 1893. Produces the governing design bending moment.

FIXED (14 Jul 2026), matching Dynastac's own documented methodology
("the highest of the B.M.s caused by Wind loads calculated by three
methods viz. 3 sec peak Gust, H.M.W. static+Dynamic Inertia and G.E.F.
Method, have been considered for stress analysis"):
  (a) 3-sec peak gust, STATIC alone (wind_loads.py)
  (b) Hourly-mean-wind STATIC + Dynamic Inertia, SUMMED (not separate)
  (c) GEF Method = hourly-mean-wind force * Gust Factor G
Earthquake is a SEPARATE design check, not folded into this max -
confirmed from Dynastac's own combined-stress table, which only
compares the 3 wind methods above.

Also FIXED: `gamma` was being double-counted in the seismic ah formula
(ah = Beta.I.Z.gamma.Sa/g). Verified: WITH gamma gave ~1.92x too low
vs a real design's own printed ah; WITHOUT gamma matched to 0.2%.

DISCLOSED, OPEN ITEMS (not fixed):
  - The Sa/g(T) power-law fit (0.2099*T^-1.3562) does not hold well
    outside the period range it was fitted on - found up to 8x off on
    a real design's mode 2/3 periods. ah will be wrong until this gets
    a proper piecewise refit (or the real IS 1893/6533 curve shape).
  - Hourly-mean wind K2 still uses the same flat ratio approximation
    as gust_factor.py's Vh (same disclosed gap).

Also includes the Module 9 vortex-shedding check (Cl 8.4) - note this
is a SEPARATE, simpler check from gust_factor.py's strakes check
(IS Cl A-3); both exist in the source tool and are ported faithfully.
"""
import math
from dataclasses import dataclass
from typing import List
from inputs import ChimneyInputs
from geometry import ZoneGeometry
from wind_loads import ZoneWindLoad
from dynamic_analysis import DynamicAnalysisResult

STROUHAL = 0.2


@dataclass
class Module9VortexResult:
    vcr: float
    resonance: str


def calc_module9_vortex(inputs: ChimneyInputs, nat_freq: float, top_od_mm: float) -> Module9VortexResult:
    d_top = top_od_mm / 1000
    vcr = nat_freq * d_top / STROUHAL
    vd = inputs.vb
    resonance = "RESONANCE - check across-wind" if 0.33 * vd <= vcr <= 0.8 * vd else "OK - no resonance"
    return Module9VortexResult(vcr=vcr, resonance=resonance)


def _hmw_k2_ratio(h_mid: float) -> float:
    """Ratio of hourly-mean-wind k2 to static (3-sec peak gust) k2,
    height-dependent. Fitted from a real design, terrain cat 3 - DISCLOSED
    as needing validation on more chimneys/terrains (see module header)."""
    h_use = max(3.0, h_mid)
    r = 0.4638 + 0.04122 * math.log(h_use)
    return max(0.55, min(0.65, r))


def calc_seismic_ah(nat_period: float, beta_soil: float, importance_i: float, z_seismic: float) -> float:
    """ah = Beta.I.Z.(Sa/g) - gamma removed (was double-counted, see header).
    DISCLOSED: Sa/g power-law fit doesn't hold well outside its fitted range."""
    sa_g = 0.2099 * nat_period ** (-1.3562)
    return beta_soil * importance_i * z_seismic * sa_g


@dataclass
class GoverningLoadsResult:
    f_3smw: List[float]          # (a) 3-sec static alone
    f_hmw_inertia: List[float]   # (b) HMW static + inertia, summed
    f_gef: List[float]           # (c) GEF method
    gov_force: List[float]
    eq_shear: List[float]        # separate check, not in gov_force
    gov_bm: List[float]
    gov_base_moment: float


def calc_governing_loads(inputs: ChimneyInputs, zones: List[ZoneGeometry],
                          wind_loads: List[ZoneWindLoad], dyn: DynamicAnalysisResult,
                          nf_mass: List[float], gust_g: float, eq_ah: float,
                          proj_dia_mm: List[float]) -> GoverningLoadsResult:
    n = len(zones)

    f_3smw = [w.force_kg for w in wind_loads]

    hmw_force = []
    for z, pdia, w in zip(zones, proj_dia_mm, wind_loads):
        k2_hmw = w.k2 * _hmw_k2_ratio(w.z_mid)
        vz_hmw = inputs.vb * inputs.k1 * k2_hmw * inputs.k3 * inputs.ki
        press_hmw = 0.6 * vz_hmw ** 2
        if inputs.insulation not in ("None", ""):
            mean_od_m = z.mean_od / 1000 + 2 * inputs.insul_thk / 1000
        else:
            mean_od_m = z.mean_od / 1000
        force_n = (inputs.shape_cyl * press_hmw * z.length * mean_od_m
                   + inputs.shape_ladder * press_hmw * z.length * (pdia / 1000))
        hmw_force.append(force_n / 9.80665)

    f_hmw_inertia = [hmw_force[i] + dyn.dyn_load[i] for i in range(n)]
    f_gef = [hmw_force[i] * gust_g for i in range(n)]

    gov_force = [max(f_3smw[i], f_hmw_inertia[i], f_gef[i]) for i in range(n)]
    eq_shear = [eq_ah * nf_mass[i] for i in range(n)]

    gov_bm = [0.0] * n
    for i in range(n):
        zone_base_elev = zones[i].elev_top - zones[i].length
        bm_sum = 0.0
        for j in range(i + 1):
            lever_arm = (zones[j].elev_top - zones[j].length / 2) - zone_base_elev
            if lever_arm > 0:
                bm_sum += gov_force[j] * lever_arm
        gov_bm[i] = bm_sum

    return GoverningLoadsResult(
        f_3smw=f_3smw, f_hmw_inertia=f_hmw_inertia, f_gef=f_gef,
        gov_force=gov_force, eq_shear=eq_shear, gov_bm=gov_bm,
        gov_base_moment=gov_bm[-1],
    )

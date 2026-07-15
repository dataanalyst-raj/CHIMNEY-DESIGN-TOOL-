"""
BASE FOUNDATION - port of Module 11 (CalcBaseFoundation + CalcBYbaseChair).
Base plate, concrete bearing, and anchor bolt design.

PCD & bolt count are AUTO-COMPUTED (PCD = shell base OD + 270mm, a
7-chimney-survey constant; bolt count iterates until safe), OR you can
type an override directly (matches the Excel tool's D11/D12 override
cells) to check the downstream B&Y stress formulas against a known
real design's actual PCD/N.

DISCLOSED, OPEN ITEM: the +270mm PCD offset does NOT hold for every
chimney (one real design needed +154mm instead) - flagged, not fixed,
needs more chimney data. Even feeding a real design's EXACT exact
PCD/N/moment/weight into the B&Y k-solve below does not reproduce its
own printed k/fs/fc - narrowed to an unexplained ~40%-of-expected
"effective bolt area" gap. The k-solve formula itself WAS verified
against the Brownell & Young textbook's own worked example (reproduces
it almost exactly) - so the formula is faithful to the source, the gap
is something else not yet identified.
"""
import math
from dataclasses import dataclass
from typing import Optional
from inputs import ChimneyInputs

PI = 3.14159265358979
FDN_OVERHANG = 215.0        # base plate overhang Db->OD, mm
FDN_WIDTH = 300.0           # base plate radial width, mm
FDN_LEVER = 70.0            # bolt-to-gusset lever arm, mm
FDN_PCD_CLEARANCE = 270.0   # PCD = shell base OD + 270mm (disclosed gap, see header)
FDN_BOLT_AREA_CM2 = 5.72    # typical M30 anchor bolt root area, cm2

# B&Y base-chair coefficient table (k -> Cc, Ct, z, j)
_KS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
_CCS = [0.6, 0.852, 1.049, 1.218, 1.37, 1.51, 1.64, 1.765, 1.884, 2.0, 2.113, 2.224]
_CTS = [3.008, 2.887, 2.772, 2.661, 2.551, 2.442, 2.333, 2.224, 2.113, 2.0, 1.884, 1.765]
_ZS = [0.49, 0.48, 0.469, 0.459, 0.448, 0.438, 0.427, 0.416, 0.404, 0.393, 0.381, 0.369]
_JS = [0.76, 0.766, 0.771, 0.776, 0.779, 0.781, 0.783, 0.784, 0.785, 0.785, 0.785, 0.784]


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
class BYSolveResult:
    k: float
    fc: float       # concrete bearing stress, kg/cm2
    fs: float       # bolt/steel stress, kg/cm2
    cc: float
    ct: float
    t1: float        # equiv steel shell thickness, cm
    t2: float        # concrete bearing width, cm
    wdw: float       # base dead weight used in the solve, kg


def calc_by_base_chair(pcd_mm: float, n_bolts: int, base_moment_kgm: float,
                        base_dead_kg: float, modular_ratio: float = 12.0) -> BYSolveResult:
    bc_d = pcd_mm / 10  # cm
    as_tot = n_bolts * FDN_BOLT_AREA_CM2
    t1 = as_tot / (PI * bc_d)
    t2 = (FDN_WIDTH / 10) - t1
    mw = base_moment_kgm * 100  # kg-cm
    wdw = base_dead_kg

    k = 0.25
    cc = ct = fs = fc = 0.0
    for _ in range(8):
        cc = _interp(k, _KS, _CCS)
        ct = _interp(k, _KS, _CTS)
        z = _interp(k, _KS, _ZS)
        j = _interp(k, _KS, _JS)
        ft = (mw - wdw * z * bc_d) / (j * bc_d)
        fs = ft / (t1 * (bc_d / 2) * ct)
        fc_load = ft + wdw
        fc = fc_load / ((t2 + modular_ratio * t1) * (bc_d / 2) * cc)
        if fs > 0 and fc > 0:
            k = 1 / (1 + fs / (modular_ratio * fc))

    return BYSolveResult(k=k, fc=fc, fs=fs, cc=cc, ct=ct, t1=t1, t2=t2, wdw=wdw)


@dataclass
class BaseFoundationResult:
    pcd: float
    n_bolts: int
    bearing_pressure: float   # kg/cm2
    bearing_ok: bool
    bolt_tension: float        # kg
    plate_thk_req: float       # mm
    plate_thk_used: float      # mm
    plate_ok: bool
    status: str
    by: BYSolveResult


def calc_base_foundation(inputs: ChimneyInputs, base_od_mm: float,
                          base_moment_kgm: float, base_dead_kg: float,
                          allow_base_plate: float, allow_concrete: float,
                          allow_fdn_bolt_t: float, modular_ratio: float,
                          base_plate_my_coef_fn,
                          pcd_override: Optional[float] = None,
                          n_override: Optional[int] = None) -> BaseFoundationResult:
    """base_plate_my_coef_fn: function(l_over_b) -> My coefficient, from
    base_chair_stress.get_base_plate_my_coef (Table 10.3)."""
    m_knm = base_moment_kgm * 9.80665 / 1000
    w_kn = base_dead_kg * 9.80665 / 1000

    if pcd_override and pcd_override > 0:
        pcd = pcd_override
    else:
        pcd = max(600.0, base_od_mm + FDN_PCD_CLEARANCE)

    if n_override and n_override > 0:
        n_bolts = int(n_override)
    else:
        n_bolts = 16
        while n_bolts <= 48:
            pb_trial = 4 * m_knm / (n_bolts * pcd / 1000) - w_kn / n_bolts
            pb_trial = max(0.0, pb_trial * 1000 / 9.80665)
            stress_trial = pb_trial / FDN_BOLT_AREA_CM2
            if stress_trial <= allow_fdn_bolt_t:
                break
            n_bolts += 4

    # PART 1: concrete bearing
    od = pcd + 2 * FDN_OVERHANG
    ring_id = pcd - 2 * FDN_WIDTH
    area_ring = PI / 4 * ((od / 1000) ** 2 - (ring_id / 1000) ** 2)
    z_ring = PI / 32 * ((od / 1000) ** 4 - (ring_id / 1000) ** 4) / (od / 1000)
    bearing_pressure = (w_kn / area_ring + m_knm / z_ring) / 98.0665
    bearing_ok = bearing_pressure <= allow_concrete

    # PART 2: anchor bolt tension
    bolt_tension = (4 * m_knm / (n_bolts * pcd / 1000) - w_kn / n_bolts) * 1000 / 9.80665
    bolt_tension = max(0.0, bolt_tension)

    # B&Y solve (needed for base plate sizing path b)
    by = calc_by_base_chair(pcd, n_bolts, base_moment_kgm, base_dead_kg, modular_ratio)

    # PART 3: base plate thickness - governing of TWO bending modes
    gusset_spacing = PI * pcd / n_bolts
    bm_plate_a = bolt_tension * FDN_LEVER / gusset_spacing
    t_req_a = math.sqrt(6 * bm_plate_a / (allow_base_plate / 100))

    l_overhang_cm = FDN_OVERHANG / 10
    b_spacing_cm = PI * pcd / 10 / n_bolts
    bl_ratio_b = l_overhang_cm / b_spacing_cm
    my_coef_b = base_plate_my_coef_fn(bl_ratio_b)
    bm_plate_b = abs(my_coef_b * by.fc * l_overhang_cm ** 2 * 0.91)
    t_req_b = math.sqrt(6 * bm_plate_b / allow_base_plate) * 10

    plate_thk_req = max(t_req_a, t_req_b)
    plate_thk_used = math.ceil(plate_thk_req + inputs.ca_ext)
    plate_ok = plate_thk_used >= plate_thk_req

    status = "OK" if (bearing_ok and plate_ok) else "CHECK"

    return BaseFoundationResult(
        pcd=pcd, n_bolts=n_bolts, bearing_pressure=bearing_pressure, bearing_ok=bearing_ok,
        bolt_tension=bolt_tension, plate_thk_req=plate_thk_req, plate_thk_used=plate_thk_used,
        plate_ok=plate_ok, status=status, by=by,
    )

"""
FLANGE DESIGN - port of Module 13 (CalcFlangeDesign), inter-zone
flanges & bolts. IS 6533 Cl 8.6.

PART 1: flange detail per JOINT between adjacent zones (N-1 flanges
for N shell zones - the base of the last zone connects to the base
plate/foundation, not a flange).
PART 2: flange-plate stress at the governing flange - two bending
paths, governing = MAX of the two:
  (a) bolt-force bending (B&Y eq 10.40)
  (b) compressive-load bending on the flange sector

DISCLOSED, OPEN ITEM: the bolt-force formula P=4M/(N.PCD)-W/N is the
same family that showed an unresolved ~40%-of-expected "effective bolt
area" gap in base_foundation.py's B&Y k-solve - confirmed to propagate
here too on a real design (bolt force came out ~14% low, feeding
through to under-sized flange thickness at the higher-moment joints).
Same root cause, not a separate bug.
"""
import math
from dataclasses import dataclass
from typing import List
from inputs import ChimneyInputs
from geometry import ZoneGeometry
from combined_stress import ZoneCombinedStress

PI = 3.14159265358979
FL_ID_CLEAR = 2.0       # flange ID = shell OD + 2mm
FL_PCD_ALLOW = 82.0     # PCD = ID + bolt allowance
FL_OD_EDGE = 86.0       # OD = PCD + edge
FL_BOLT_DIA = 24        # M24
MU_STEEL = 0.3

_T106_BL = [1, 1.2, 1.4, 1.6, 1.8, 2, 10]
_T106_G1 = [0.565, 0.35, 0.211, 0.125, 0.073, 0.042, 0]

_STD_T = [12, 14, 16, 18, 20, 22, 25, 28, 32, 36, 40]


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
class FlangeJoint:
    joint: int
    od: float
    id_: float
    pcd: float
    n_bolts: int
    thk: float


@dataclass
class FlangeDesignResult:
    joints: List[FlangeJoint]
    bolt_force: float
    my_a: float
    my_b: float
    my_governing: float
    stress: float
    stress_ok: bool


def calc_flange_design(inputs: ChimneyInputs, zones: List[ZoneGeometry],
                        combined_stress: List[ZoneCombinedStress],
                        flange_min_thk: float, allow_flange_pl: float) -> FlangeDesignResult:
    n = len(zones)
    n_joints = n - 1

    joints = []
    for i in range(n_joints):
        fl_id = zones[i].bot_od + FL_ID_CLEAR
        fl_pcd = fl_id + FL_PCD_ALLOW
        fl_od = fl_pcd + FL_OD_EDGE
        fl_n = max(20, round(PI * fl_pcd / 130 / 4) * 4)
        fl_thk = max(flange_min_thk, 12)
        joints.append(FlangeJoint(joint=i + 1, od=fl_od, id_=fl_id, pcd=fl_pcd,
                                    n_bolts=fl_n, thk=fl_thk))

    # governing joint = max moment among the N-1 joints
    gov_zone = 0
    gov_max_bm = 0.0
    for i in range(n_joints):
        if combined_stress[i].bm > gov_max_bm:
            gov_max_bm = combined_stress[i].bm
            gov_zone = i

    m_kgm = combined_stress[gov_zone].bm
    w_kg = combined_stress[gov_zone].dead_imp
    gov_joint = joints[gov_zone]

    p = 4 * m_kgm / (gov_joint.n_bolts * gov_joint.pcd / 1000) - w_kg / gov_joint.n_bolts
    p = max(0.0, p)

    l = 8.0    # flange overhang lever, cm (calibrated)
    e = 2.08   # half across-flats of M24 nut, cm
    b = PI * gov_joint.pcd / 10 / gov_joint.n_bolts
    bl = b / l
    g1 = _interp(bl, _T106_BL, _T106_G1)

    my_a = p / (4 * PI) * ((1 + MU_STEEL) * math.log(2 * l / (PI * e)) + (1 - g1))

    comp_load = p
    comp_pressure = comp_load / (l * b)
    ab_ratio = l / b
    q_factor = 0.0959 * ab_ratio + 0.0187
    my_b = q_factor * comp_pressure * b ** 2

    my_gov = max(my_a, my_b)

    t_req = math.sqrt(6 * my_gov / allow_flange_pl) * 10 + 1.5
    t_used = max(flange_min_thk, _STD_T[0])
    for std in _STD_T:
        if std >= t_req - 0.001:
            t_used = std
            break
    else:
        t_used = _STD_T[-1]

    for jt in joints:
        if jt.thk < t_used:
            jt.thk = t_used

    tcorr = t_used / 10 - 0.15
    if tcorr < 0.5:
        tcorr = t_used / 10
    stress = 6 * my_gov / tcorr ** 2
    stress_ok = stress <= allow_flange_pl * 1.0001

    return FlangeDesignResult(
        joints=joints, bolt_force=p, my_a=my_a, my_b=my_b, my_governing=my_gov,
        stress=stress, stress_ok=stress_ok,
    )

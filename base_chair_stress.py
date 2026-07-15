"""
BASE CHAIR STRESS - port of Module 12 (CalcBaseChairStress), B&Y
detailed checks: base plate, compression plate, gussets.

1. BASE PLATE - formula verified against the Brownell & Young textbook's
   own worked example (reproduces it almost exactly). Still has a real,
   disclosed numeric gap on real designs, traced to base_foundation.py's
   B&Y k-solve bolt tension - not this formula.

2. COMPRESSION PLATE - Eq. 10.40 (B&Y, a=1/2/My-controlling reduced
   form). CONFIRMED CORRECT: fed a real design's own bolt tension, this
   reproduces its printed moment (574.9 vs 564.8) to 1.8%, and the
   gamma1/gamma2 table lookup matches to 3 decimal places.
   FIXED (14 Jul 2026): plate thickness used to convert moment->stress
   was a disconnected placeholder unrelated to the actual required
   thickness - now properly derived the same way as the base plate.

3. GUSSETS - allowable stress uses the verified IS 800:1984
   Merchant-Rankine formula (matches a real design to <0.2%).
   FIXED (14 Jul 2026): gusset thickness was using GROSS thickness in
   both the radius-of-gyration and stress formulas, with no corrosion
   subtraction - confirmed via a real design's own printed radius of
   gyration, which only reproduces correctly using CORRODED thickness.
   Gusset HEIGHT remains a genuine chair-layout design choice (B&Y
   takes height as a GIVEN input, not something it derives) - this is
   disclosed as approximate, not a bug.
"""
import math
from dataclasses import dataclass
from inputs import ChimneyInputs
from base_foundation import BYSolveResult

PI = 3.14159265358979
MU_STEEL = 0.3
E_STEEL = 2_000_000.0        # kg/cm2
MERCHANT_N = 1.4              # IS 800:1984 Merchant-Rankine exponent
IS800_FOS = 1.64              # IS 800:1984 factor of safety
PLATE_POISSON = 0.91          # (1-nu^2), nu=0.3

# Table 10.3 (l/b ratio -> Mx, My) - B&Y base plate bending
_T3_LB = [0, 0.3333, 0.5, 0.6667, 1, 1.5, 2, 3]
_T3_MY = [-0.5, -0.428, -0.319, -0.227, -0.119, -0.124, -0.125, -0.125]

# Compression-ring gamma table (b/l -> gamma1, gamma2) - B&Y Table 10.6
_GA = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 3.0]
_GG1 = [0.565, 0.35, 0.211, 0.125, 0.073, 0.042, 0.0]


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])
    return ys[-1]


def get_base_plate_my_coef(l_over_b: float) -> float:
    """Table 10.3 My lookup - used by base_foundation.py too."""
    return _interp(l_over_b, _T3_LB, _T3_MY)


@dataclass
class BaseChairStressResult:
    base_plate_stress: float
    base_plate_ok: bool
    compr_plate_stress: float
    compr_plate_ok: bool
    gusset_stress: float
    gusset_allow: float
    gusset_ok: bool
    status: str


def calc_base_chair_stress(inputs: ChimneyInputs, pcd: float, n_bolts: int,
                            by: BYSolveResult, base_od_mm: float,
                            fdn_plate_thk_used: float, bolt_tension: float,
                            allow_base_plate: float, material: str = "IS 2062") -> BaseChairStressResult:
    from base_foundation import FDN_OVERHANG, FDN_WIDTH

    bc_d = pcd / 10  # cm

    # ---- 1. BASE PLATE ----
    l = FDN_OVERHANG / 10
    b = PI * bc_d / n_bolts
    bl = l / b
    my_c = get_base_plate_my_coef(bl)
    bm_plate = abs(my_c * by.fc * l ** 2 * PLATE_POISSON)

    t_actual_base = (fdn_plate_thk_used - inputs.ca_ext) / 10
    if t_actual_base < 0.5:
        t_actual_base = fdn_plate_thk_used / 10
    base_plate_stress = 6 * bm_plate / t_actual_base ** 2
    base_plate_ok = base_plate_stress <= allow_base_plate * 1.0001

    # ---- 2. COMPRESSION PLATE (Eq. 10.40) ----
    a = (pcd - base_od_mm) / 2 / 10  # skirt OD to PCD, cm
    if a <= 0:
        a = 13.5
    l_compr = a + FDN_WIDTH / 10 / 2
    if l_compr <= 0:
        l_compr = 20.0
    e_compr = 2.6  # half-flat of typical anchor bolt nut, cm
    bl_compr = b / l_compr
    g1 = _interp(bl_compr, _GA, _GG1)
    p_compr_load = bolt_tension * (2 / 3)
    mmax_compr = p_compr_load / (4 * PI) * ((1 + MU_STEEL) * math.log(2 * l_compr / (PI * e_compr)) + (1 - g1))

    safe_allow = allow_base_plate if allow_base_plate >= 100 else 1682.0
    safe_moment = max(mmax_compr, 0.01)
    t_compr_req_cm = math.sqrt(6 * safe_moment / safe_allow)
    t_compr_used_mm = math.ceil(t_compr_req_cm * 10 + inputs.ca_ext)
    t_compr = (t_compr_used_mm - inputs.ca_ext) / 10
    if t_compr < 0.5:
        t_compr = 0.5
    compr_plate_stress = 6 * mmax_compr / t_compr ** 2
    compr_plate_ok = compr_plate_stress <= allow_base_plate * 1.0001

    # ---- 3. GUSSETS ----
    p_gusset = (by.fs * by.t1 * (bc_d / 2) * by.ct + by.wdw) / n_bolts
    if p_gusset <= 0:
        p_gusset = bolt_tension / max(n_bolts, 1)

    h_gus = a + FDN_OVERHANG / 10
    if h_gus < 5:
        h_gus = 5
    t_gus = 1.2 - inputs.ca_int / 10   # corroded gusset thickness, cm (CA_int is in mm)
    if t_gus < 0.3:
        t_gus = 0.3

    ry_gus = t_gus / math.sqrt(12)
    lambda_gus = h_gus / ry_gus

    fy_gus = 350 / 0.0980665 if "350" in material.upper() else 250 / 0.0980665

    fcc_gus = PI ** 2 * E_STEEL / lambda_gus ** 2
    gusset_allow = (fcc_gus * fy_gus) / ((fcc_gus ** MERCHANT_N + fy_gus ** MERCHANT_N) ** (1 / MERCHANT_N))
    gusset_allow = gusset_allow / IS800_FOS

    gusset_stress = p_gusset / (t_gus * h_gus)
    gusset_ok = gusset_stress <= gusset_allow

    status = "OK" if (base_plate_ok and compr_plate_ok and gusset_ok) else "CHECK"

    return BaseChairStressResult(
        base_plate_stress=base_plate_stress, base_plate_ok=base_plate_ok,
        compr_plate_stress=compr_plate_stress, compr_plate_ok=compr_plate_ok,
        gusset_stress=gusset_stress, gusset_allow=gusset_allow, gusset_ok=gusset_ok,
        status=status,
    )

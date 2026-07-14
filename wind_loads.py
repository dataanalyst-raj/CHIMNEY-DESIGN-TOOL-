"""
STATIC WIND LOADS - port of the Excel tool's Module3 (CalcWindLoads),
carrying forward the fix validated against Kurkumbh on 14 Jul 2026:

  Ladder/platform projected width is now a PER-ZONE value (from the
  editable zone table's "Proj Dia (mm)" column), not one flat constant
  applied to every zone. Dynastac's own design shows real per-zone
  widths (500/300/300/350/150/300mm) - much larger at the zones that
  actually contain a platform. Matched Dynastac's static wind loads to
  <0.1% on all 6 zones once per-zone width was used (vs up to 33% error
  before, worst at the platform zones).

IS 875 Part 3 Table 2 (k2 by height & terrain category), IS 6533 Cl 8.2.
"""
import math
from dataclasses import dataclass
from typing import List
from inputs import ChimneyInputs
from geometry import ZoneGeometry

PI = math.pi

# k2 table: height (m) -> k2, by terrain category 1-4
_K2_HEIGHTS = [10, 15, 20, 30, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
_K2_CAT = {
    1: [1.05, 1.09, 1.12, 1.15, 1.2, 1.26, 1.3, 1.32, 1.34, 1.35, 1.35, 1.35, 1.35, 1.35],
    2: [1.00, 1.05, 1.07, 1.12, 1.17, 1.24, 1.28, 1.3, 1.32, 1.34, 1.35, 1.35, 1.35, 1.35],
    3: [0.91, 0.97, 1.01, 1.06, 1.12, 1.2, 1.24, 1.27, 1.29, 1.31, 1.32, 1.34, 1.35, 1.35],
    4: [0.80, 0.80, 0.80, 0.97, 1.1, 1.2, 1.24, 1.27, 1.28, 1.3, 1.31, 1.32, 1.33, 1.34],
}


def _interp(x: float, xs: List[float], ys: List[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])
    return ys[-1]


def get_k2(height_m: float, terrain_cat: int) -> float:
    col = _K2_CAT.get(terrain_cat, _K2_CAT[1])
    return _interp(max(height_m, _K2_HEIGHTS[0]), _K2_HEIGHTS, col)


@dataclass
class ZoneWindLoad:
    zone: int
    z_mid: float            # m (above ground, includes base elevation)
    k2: float
    vz: float                # m/s
    press: float              # N/m2
    force_n: float
    force_kg: float
    arm: float                # m (to base)
    moment_nm: float


def calc_wind_loads(inputs: ChimneyInputs, zones: List[ZoneGeometry],
                     proj_dia_mm: List[float]) -> List[ZoneWindLoad]:
    """
    proj_dia_mm: per-zone ladder/platform projected width (mm), same
    order as `zones` (zone 1 = top). Pass 300.0 for a plain default if
    the user hasn't customised it.
    """
    results = []
    for z, pdia in zip(zones, proj_dia_mm):
        z_mid = inputs.base_elev + z.elev_mid
        k2 = get_k2(z_mid, inputs.terrain_cat)
        vz = inputs.vb * inputs.k1 * k2 * inputs.k3 * inputs.ki
        press = 0.6 * vz ** 2   # N/m2

        if inputs.insulation not in ("None", ""):
            mean_od_m = z.mean_od / 1000 + 2 * inputs.insul_thk / 1000
        else:
            mean_od_m = z.mean_od / 1000

        force_n = (inputs.shape_cyl * press * z.length * mean_od_m
                   + inputs.shape_ladder * press * z.length * (pdia / 1000))
        force_kg = force_n / 9.80665
        arm = z_mid
        moment = force_n * arm

        results.append(ZoneWindLoad(
            zone=z.zone, z_mid=z_mid, k2=k2, vz=vz, press=press,
            force_n=force_n, force_kg=force_kg, arm=arm, moment_nm=moment,
        ))
    return results


def total_base_shear_kg(loads: List[ZoneWindLoad]) -> float:
    return sum(l.force_kg for l in loads)


def total_base_moment_kgm(loads: List[ZoneWindLoad]) -> float:
    return sum(l.moment_nm for l in loads) / 9.80665

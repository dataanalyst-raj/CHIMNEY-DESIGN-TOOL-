"""
COMBINED STRESS - port of Module 5 (CalcCombinedStress), the central
shell stress table. IS 6533 Cl 7.7.

Cumulative (top -> each section): shear, dead+imposed load, bending
moment, then compressive + bending stress, total, vs allowable.
Uses the GOVERNING moment (max of the 3 real wind methods, from
governing_loads.py) - confirmed correct by Dynastac's own documented
methodology.

Platform weight contributes starting at its OWN elevation, carrying
through every zone below it (dead+imposed load is a running total, so
a platform's weight structurally loads every section beneath it - this
is different from the natural-frequency mass model, which places each
platform's mass only at its own physical location).
"""
from dataclasses import dataclass
from typing import List
from inputs import ChimneyInputs
from geometry import ZoneGeometry
from wind_loads import ZoneWindLoad
from stress_checks import ZoneStressCheck
from natural_frequency import get_local_od

PI = 3.14159265358979


@dataclass
class ZoneCombinedStress:
    zone: int
    shear: float          # kg
    dead_imp: float        # kg
    bm: float               # kg-m (governing)
    compr_st: float         # kg/cm2
    bend_st: float          # kg/cm2
    total_st: float         # kg/cm2
    allow_st: float         # kg/cm2
    check_ok: bool


def calc_combined_stress(inputs: ChimneyInputs, zones: List[ZoneGeometry],
                          wind_loads: List[ZoneWindLoad], stress_checks: List[ZoneStressCheck],
                          gov_bm: List[float],
                          platform_elev: List[float], platform_width: List[float],
                          platform_sweep: List[float]) -> List[ZoneCombinedStress]:
    n = len(zones)
    results = []
    for i in range(n):
        cum_shell_wt = sum(zones[j].weight for j in range(i + 1))
        cum_len = sum(zones[j].length for j in range(i + 1))

        zone_base_elev = zones[i].elev_top - zones[i].length

        plat_above_wt = 0.0
        for pe, pw, psw in zip(platform_elev, platform_width, platform_sweep):
            if pe > zone_base_elev:
                od_local = get_local_od(pe, zones) / 1000
                ri = od_local / 2
                ro = ri + pw / 1000
                ring_area = (psw / 360) * PI * (ro ** 2 - ri ** 2)
                plat_above_wt += inputs.plat_weight * ring_area + inputs.plat_imposed * ring_area

        dead_imp = cum_shell_wt + inputs.ladder_weight * cum_len + plat_above_wt
        if i == n - 1:
            dead_imp += inputs.misc_weight + inputs.contingency_wt

        shear = sum(wind_loads[j].force_kg for j in range(i + 1))

        bm = gov_bm[i]

        area_cm2 = _zone_area_cm2(zones[i])
        z_cm3 = _zone_zmod_cm3(zones[i])

        compr_st = dead_imp / area_cm2
        bend_st = (bm * 100) / z_cm3
        total_st = compr_st + bend_st

        allow_st = stress_checks[i].allow_mpa * 10.197  # MPa -> kg/cm2
        check_ok = total_st <= allow_st

        results.append(ZoneCombinedStress(
            zone=i + 1, shear=shear, dead_imp=dead_imp, bm=bm,
            compr_st=compr_st, bend_st=bend_st, total_st=total_st,
            allow_st=allow_st, check_ok=check_ok,
        ))
    return results


def _zone_area_cm2(z: ZoneGeometry) -> float:
    dm_cm = (z.mean_od - z.thk_net) / 10
    tcm = z.thk_net / 10
    return PI * dm_cm * tcm


def _zone_zmod_cm3(z: ZoneGeometry) -> float:
    dm_cm = (z.mean_od - z.thk_net) / 10
    tcm = z.thk_net / 10
    return PI / 4 * dm_cm ** 2 * tcm

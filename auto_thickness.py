"""
AUTO-SIZE THICKNESS - port of the Excel tool's AutoSizeThickness
(inside Module 16/17's CalculateChimney iterative pass loop).
IS 6533 Cl 7.3.1: t = MAX(stress-required-net + corrosion, 6.0mm, OD/500)

Runs the FULL load pipeline (geometry -> wind -> natural frequency ->
gust -> dynamic -> governing moment -> allowable stress -> static
deflection) once per pass, computes the required thickness per zone
from the governing moment and allowable stress, applies the deflection
governor if the top deflection exceeds H/200, checks convergence,
repeats up to 15 passes (matching the VBA), then rounds each zone UP
to a standard plate size.

DEFLECTION GOVERNOR (ported 16 Jul 2026, matches VBA exactly):
  if top deflection > H/200 allowable:
      scale = max(1, top_deflection / (0.95 * allowable))
      every zone's thickness is scaled up by that factor, then the
      final thickness = MAX(stress-required, deflection-scaled, OD/500)
"""
import math
from typing import List
from inputs import ChimneyInputs
from geometry import calc_shell_geometry
from wind_loads import calc_wind_loads
from natural_frequency import calc_natural_frequency
from gust_factor import calc_gust_factor
from stress_checks import calc_stress_checks
from dynamic_analysis import calc_dynamic_analysis
from governing_loads import calc_seismic_ah, calc_governing_loads
from static_deflection import calc_static_deflection

PI = 3.14159265358979
STD_PLATES = [6, 8, 10, 12, 14, 16, 18, 20, 22, 25]


def _round_up_to_plate(t: float) -> float:
    for std in STD_PLATES:
        if std >= t - 0.001:
            return float(std)
    return float(STD_PLATES[-1])


def calc_auto_thickness(inputs: ChimneyInputs, portions: List[str], lengths: List[float],
                         proj_dia: List[float], plat_elev: List[float], plat_width: List[float],
                         plat_sweep: List[float], max_pass: int = 15) -> List[float]:
    """Returns converged, standard-plate-rounded gross thickness per zone
    (same order as `portions`/`lengths`, top zone first)."""
    n = len(lengths)
    thk = [6.0] * n   # start at the IS 6533 minimum

    for _ in range(max_pass):
        zone_table = [{"Zone": i + 1, "Portion": portions[i], "Length (m)": lengths[i],
                       "Thk gross (mm)": thk[i]} for i in range(n)]
        zones = calc_shell_geometry(inputs, zone_table)
        wind_loads = calc_wind_loads(inputs, zones, proj_dia)
        nf = calc_natural_frequency(inputs, zones, plat_elev, plat_width, plat_sweep)
        gust = calc_gust_factor(inputs, nf.nat_freq, wind_loads[0].vz, zones[0].mean_od)
        sc = calc_stress_checks(inputs, zones)
        dyn = calc_dynamic_analysis(inputs, nf, wind_loads, lining=inputs.lining,
                                     terrain_type=inputs.terrain_type)
        eq_ah = calc_seismic_ah(nf.nat_period, inputs.beta_soil, inputs.importance_i, inputs.z_seismic)
        gov = calc_governing_loads(inputs, zones, wind_loads, dyn, nf.mass, gust.G, eq_ah, proj_dia)
        defl = calc_static_deflection(inputs, zones, wind_loads)

        # deflection governor - scale every zone's thickness up if the top
        # deflection exceeds the H/200 allowable (matches VBA exactly)
        defl_scale = 1.0
        if defl.defl_allow > 0 and defl.top_deflection > defl.defl_allow:
            defl_scale = defl.top_deflection / (0.95 * defl.defl_allow)
            if defl_scale < 1.0:
                defl_scale = 1.0

        new_thk = [0.0] * n
        for i in range(n):
            D_cm = zones[i].mean_od / 10
            M_kgcm = gov.gov_bm[i] * 100
            allow_kgcm2 = sc[i].allow_mpa * 10.197  # MPa -> kg/cm2

            if allow_kgcm2 > 0 and D_cm > 0:
                treq_net = M_kgcm / (allow_kgcm2 * PI / 4 * D_cm ** 2)
            else:
                treq_net = 0.6

            t_structural = max(treq_net * 10, 6.0)  # cm->mm, IS 6mm floor
            t_is = t_structural + inputs.ca_int + inputs.ca_ext

            t_defl = thk[i] * defl_scale  # deflection-scaled thickness
            t_is = max(t_is, t_defl, zones[i].mean_od / 500)  # governing of all three
            new_thk[i] = t_is

        converged = all(abs(new_thk[i] - thk[i]) <= 0.01 for i in range(n))
        thk = new_thk
        if converged:
            break

    return [_round_up_to_plate(t) for t in thk]

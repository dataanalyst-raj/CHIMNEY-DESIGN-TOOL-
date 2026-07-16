"""
STATIC DEFLECTION - port of Module 10 (CalcStaticDeflection),
moment-area method, IS 6533 Cl 7.4.

Top deflection = sum over zones of segment contributions:
    defl_i = M_i * (H - z_i) * L_i / (E . I_i)
  where M_i = bending moment at zone i from wind forces above it
        z_i = mid-elevation of zone i
        L_i = zone length, I_i = GROSS section moment of inertia
        E   = temperature-reduced modulus (1,836,000 kg/cm2)
Allowable: H/200 (IS 6533 Cl 7.4).

Uses plain STATIC wind force (Module 3's WforceKg), matching the VBA
exactly - not the governing (max of 3 methods) force from Module 9.
This is a direct, faithful 1:1 port; not independently re-validated
against Dynastac beyond a ballpark sanity check (their own report shows
9.15cm actual vs 16.00cm allowable for the Kurkumbh reference - exact
match not expected since this inherits the same already-disclosed
upstream gaps as everything else, e.g. static wind force's k2 issue).
"""
from dataclasses import dataclass
from typing import List
from inputs import ChimneyInputs
from geometry import ZoneGeometry
from wind_loads import ZoneWindLoad

PI = 3.14159265358979
E_DEFL = 1_836_000.0   # kg/cm2, temperature-reduced modulus


@dataclass
class StaticDeflectionResult:
    top_deflection: float      # cm
    defl_allow: float           # cm, H/200
    defl_ok: bool
    zone_defl: List[float]      # cm, per-zone contribution


def calc_static_deflection(inputs: ChimneyInputs, zones: List[ZoneGeometry],
                            wind_loads: List[ZoneWindLoad]) -> StaticDeflectionResult:
    n = len(zones)
    zone_defl = [0.0] * n
    defl_sum = 0.0

    for i in range(n):
        z_mid = zones[i].elev_top - zones[i].length / 2

        # moment at zone i from wind forces ABOVE it (kg-m)
        m_i = 0.0
        for k in range(n):
            z_mid_k = zones[k].elev_top - zones[k].length / 2
            if z_mid_k > z_mid:
                m_i += wind_loads[k].force_kg * (z_mid_k - z_mid)

        # gross section moment of inertia at this zone (cm4)
        dm_cm = (zones[i].mean_od - zones[i].thk_gross) / 10
        t_cm = zones[i].thk_gross / 10
        i_gross = PI / 8 * dm_cm ** 3 * t_cm

        # segment deflection contribution (cm)
        zone_defl[i] = (m_i * 100) * ((inputs.H - z_mid) * 100) * (zones[i].length * 100) / (E_DEFL * i_gross)
        defl_sum += zone_defl[i]

    top_deflection = defl_sum
    defl_allow = inputs.H * 100 / 200
    defl_ok = top_deflection <= defl_allow

    return StaticDeflectionResult(
        top_deflection=top_deflection, defl_allow=defl_allow, defl_ok=defl_ok, zone_defl=zone_defl,
    )

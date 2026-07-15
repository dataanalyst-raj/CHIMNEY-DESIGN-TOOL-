"""
NATURAL FREQUENCY - port of Module 6 (CalcNaturalFrequency), Rayleigh
method, IS 6533 Cl 8.3.1.

Carries forward the fixes validated against Kurkumbh on 14 Jul 2026:
  - Platform mass uses the real ring-area formula (same as combined
    stress), not a flat estimate - matches Dynastac's own platform
    weights to <1%.

DISCLOSED, OPEN ITEM (not fixed - flagged honestly, same as the Excel
tool): even with the platform-mass fix, a consistent ~217kg/zone
residual gap remains vs Dynastac's own printed zone masses on every
zone. Flange weight was tested and ruled out as the cause. Root cause
still unknown - natural frequency will read HIGH vs the true design
until this is resolved. Treat this module's output with that caveat.
"""
import math
from dataclasses import dataclass
from typing import List
from inputs import ChimneyInputs
from geometry import ZoneGeometry

PI = math.pi
E_STEEL = 2_040_000.0     # kg/cm2
G_CM = 981.0               # cm/s2
VIB_CORR = 0.3             # cm, vibration-calc corrosion on wall


def get_local_od(elev_m: float, zones: List[ZoneGeometry]) -> float:
    """Chimney OD (mm) at a given elevation, interpolated within its zone."""
    for z in zones:
        z_top = z.elev_top
        z_bot = z_top - z.length
        if z_bot <= elev_m <= z_top:
            frac = (z_top - elev_m) / z.length if z.length > 0 else 0
            return z.top_od + (z.bot_od - z.top_od) * frac
    return zones[0].mean_od  # fallback


@dataclass
class NaturalFrequencyResult:
    nat_freq: float            # Hz
    nat_period: float          # s
    mass: List[float]          # kg, per zone
    defl: List[float]          # cm, per zone
    elev_mid_cm: List[float]   # cm, per zone


def calc_natural_frequency(inputs: ChimneyInputs, zones: List[ZoneGeometry],
                            platform_elev: List[float], platform_width: List[float],
                            platform_sweep: List[float]) -> NaturalFrequencyResult:
    n = len(zones)
    misc_mass = inputs.misc_weight + inputs.contingency_wt

    # ---- STEP 1: per-zone vibrating mass ----
    mass = [0.0] * n
    elev_mid_cm = [0.0] * n
    for i, z in enumerate(zones):
        elev_top = z.elev_top
        elev_bot = elev_top - z.length
        elev_mid_m = elev_top - z.length / 2
        elev_mid_cm[i] = elev_mid_m * 100

        # shell + ladder
        mass[i] = z.weight + inputs.ladder_weight * z.length

        # platforms whose elevation falls within this zone - real ring area
        plat_mass = 0.0
        for pe, pw, psw in zip(platform_elev, platform_width, platform_sweep):
            if pe > elev_bot and pe <= elev_top:
                od_local = get_local_od(pe, zones) / 1000  # m
                ri = od_local / 2
                ro = ri + pw / 1000
                ring_area = (psw / 360) * PI * (ro ** 2 - ri ** 2)
                plat_mass += inputs.plat_weight * ring_area
        mass[i] += plat_mass

        # misc + contingency lumped at the base zone (last zone)
        if i == n - 1:
            mass[i] += misc_mass

    # ---- STEP 2: self-weight deflection (forward-march, base->top) ----
    phi_arr = [0.0] * n
    for i, z in enumerate(zones):
        dm_cm = (z.mean_od - VIB_CORR * 10) / 10
        if dm_cm < 1:
            dm_cm = z.mean_od / 10
        tcorr_cm = max(0.1, (z.thk_gross - VIB_CORR * 10) / 10)
        i_corr = PI / 8 * dm_cm ** 3 * tcorr_cm  # cm4

        m_seg = 0.0
        for k in range(n):
            if elev_mid_cm[k] > elev_mid_cm[i]:
                m_seg += mass[k] * (elev_mid_cm[k] - elev_mid_cm[i])
        phi_arr[i] = m_seg / (E_STEEL * i_corr)

    # integrate curvature base -> top (zones list is top(0)->base(n-1),
    # so march in REVERSED order: base first)
    defl = [0.0] * n
    slope = 0.0
    d = 0.0
    for idx in reversed(range(n)):
        l_cm = zones[idx].length * 100
        d = d + slope * l_cm + 0.5 * phi_arr[idx] * l_cm ** 2
        slope = slope + phi_arr[idx] * l_cm
        defl[idx] = d

    # ---- STEP 3: Rayleigh quotient ----
    sum_wy = sum(mass[i] * defl[i] for i in range(n))
    sum_wy2 = sum(mass[i] * defl[i] ** 2 for i in range(n))

    nat_freq = (1 / (2 * PI)) * math.sqrt(G_CM * sum_wy / sum_wy2) if sum_wy2 > 0 else 0.0
    nat_period = 1 / nat_freq if nat_freq > 0 else 0.0

    return NaturalFrequencyResult(
        nat_freq=nat_freq, nat_period=nat_period,
        mass=mass, defl=defl, elev_mid_cm=elev_mid_cm,
    )

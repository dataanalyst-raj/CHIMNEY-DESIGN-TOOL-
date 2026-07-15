"""
GUST FACTOR - port of Module 7 (CalcGustFactor + CalcStrakesCheck),
IS 875 Part 3 Gust Factor Method Cl 8.3.

G = 1 + gfr * sqrt( B*(1+phi)^2 + S.E/beta )

Includes the (1+phi)^2 resonance-amplification term (verified against
a real design's own printed intermediate value). L(h) and turbulence
intensity Ih are height-dependent (fitted from 6 real chimney designs,
+/-7%, most within +/-2.5%).

DISCLOSED, OPEN ITEMS (not fixed - flagged honestly, same as Excel):
  - `gfr` was found to be off by ~18% on Kurkumbh specifically (outside
    the established +/-7% tolerance) - the Ih(H) fit may not generalise
    to every terrain/height combination yet.
  - `Vh` (hourly-mean wind speed) uses a flat conversion factor
    (sqrt(0.605)) applied to the peak-gust speed, rather than a genuine
    separate hourly-mean K2 table. Real hourly-mean K2 values vary more
    steeply with height than this flat ratio captures - found to run
    Vh about 27% high on Kurkumbh. A proper fix needs a real IS 875
    hourly-mean K2 table, which hasn't been implemented yet.
  - These two errors happened to substantially cancel in the final G
    for Kurkumbh (~1.2% off) - that is NOT guaranteed to hold for a
    different height/terrain. Don't over-trust a close G here.
"""
import math
from dataclasses import dataclass
from inputs import ChimneyInputs

PI = math.pi
CZ = 12.0   # longitudinal correlation constant
CY = 10.0   # lateral correlation constant

_IH_REF30 = {1: 0.113, 2: 0.15, 3: 0.186, 4: 0.22}


@dataclass
class GustFactorResult:
    gfr: float
    lh: float
    vh: float
    background_b: float
    size_reduction_s: float
    energy_e: float
    phi: float
    resonant_measure: float
    G: float


def calc_gust_factor(inputs: ChimneyInputs, nat_freq: float, vz_top: float,
                      mean_od_top_mm: float) -> GustFactorResult:
    H = inputs.H
    fo = nat_freq
    b_top = mean_od_top_mm / 1000  # breadth normal to wind, top zone (m)

    # Hourly-mean wind speed at top - flat conversion (DISCLOSED open item)
    vh = vz_top * math.sqrt(0.605)

    # Turbulence length scale L(h) - height-dependent (verified fit)
    lh = 299.83 * H ** 0.3442

    czh_l = CZ * H / lh
    foh_vh = fo * H / vh
    fob_vh = fo * b_top / vh
    x_lh = fo * lh / vh

    # Peak factor
    gf = math.sqrt(2 * math.log(3600 * fo))

    # Turbulence intensity Ih - height-dependent (verified fit, DISCLOSED
    # ~18% gap possible outside the originally-fitted range)
    ih_ref30 = _IH_REF30.get(inputs.terrain_cat, 0.15)
    ih = ih_ref30 * (H / 30) ** (-0.654)

    gfr = gf * 2 * ih

    background_b = 1 / (1 + 0.85 * czh_l)
    size_reduction_s = 1 / ((1 + 3.5 * foh_vh) * (1 + 4 * fob_vh))
    energy_e = 0.525 * x_lh ** (-2 / 3)

    phi = gfr * math.sqrt(background_b) / 4
    beta = inputs.gust_damp_frac
    resonant_measure = size_reduction_s * energy_e / beta

    G = 1 + gfr * math.sqrt(background_b * (1 + phi) ** 2 + size_reduction_s * energy_e / beta)

    return GustFactorResult(
        gfr=gfr, lh=lh, vh=vh, background_b=background_b,
        size_reduction_s=size_reduction_s, energy_e=energy_e,
        phi=phi, resonant_measure=resonant_measure, G=G,
    )


@dataclass
class StrakesResult:
    vcr: float
    range_lo: float
    range_hi: float
    needed: bool


def calc_strakes_check(inputs: ChimneyInputs, nat_freq: float, vh: float,
                        zones, dt_top_third_mm: float) -> StrakesResult:
    """dt_top_third_mm: length-weighted mean OD (mm) over the top 1/3 of H
    (pass zones and compute upstream, or pass a pre-computed value)."""
    vcr = 5 * (dt_top_third_mm / 1000) * nat_freq
    range_lo = 0.33 * vh
    range_hi = 0.8 * vh
    needed = range_lo <= vcr <= range_hi
    return StrakesResult(vcr=vcr, range_lo=range_lo, range_hi=range_hi, needed=needed)


def top_third_mean_od(inputs: ChimneyInputs, zones) -> float:
    """Length-weighted mean OD over the top third of the chimney height."""
    top_third = inputs.H / 3
    acc_len = 0.0
    acc_od = 0.0
    for z in zones:
        z_top = z.elev_top
        z_bot = z_top - z.length
        if z_top > (inputs.H - top_third):
            lo = max(z_bot, inputs.H - top_third)
            use_len = z_top - lo
            if use_len > 0:
                acc_len += use_len
                acc_od += use_len * z.mean_od
    if acc_len > 0:
        return acc_od / acc_len
    return zones[0].mean_od

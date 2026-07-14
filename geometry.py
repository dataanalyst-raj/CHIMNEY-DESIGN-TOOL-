"""
SHELL GEOMETRY - port of the Excel tool's Module2 (CalcShellGeometry),
carrying forward the two fixes validated against Kurkumbh on 14 Jul 2026:

  1. Zone lengths come directly from the editable zone table (no more
     forced equal-split - that was the length-order/auto-split bug).
  2. Conical OD taper is LINEAR PER METRE OF HEIGHT (cumulative-length
     weighted), not divided equally across zone COUNT - that was the
     bug that gave wrong Bottom OD whenever conical zones had unequal
     lengths (invisible before because all zones happened to be equal
     length).

Validated against Kurkumbh 32m to <0.03% on total shell weight and
exact match on OD progression (820->1195->1507.5->1820mm).
"""
import math
from dataclasses import dataclass
from typing import List
from inputs import ChimneyInputs

PI = math.pi


@dataclass
class ZoneGeometry:
    zone: int
    portion: str
    length: float          # m
    thk_gross: float       # mm
    thk_net: float         # mm
    top_od: float          # mm
    bot_od: float          # mm
    mean_od: float         # mm
    weight: float          # kg
    elev_top: float        # m (from base of shell)
    elev_mid: float        # m


def calc_shell_geometry(inputs: ChimneyInputs, zone_table: List[dict]) -> List[ZoneGeometry]:
    """
    zone_table: list of dicts with keys "Zone","Portion","Length (m)",
    "Thk gross (mm)" (as produced/edited via the Streamlit data editor).
    Returns a list of ZoneGeometry, ordered top (zone 1) to base (zone N).
    """
    n = len(zone_table)
    lengths = [row["Length (m)"] for row in zone_table]
    thks = [row["Thk gross (mm)"] for row in zone_table]
    portions = [row["Portion"] for row in zone_table]

    n_cyl = sum(1 for p in portions if p == "Cylindrical")

    zones: List[ZoneGeometry] = []

    # --- cylindrical zones: constant OD = id_top + 2*thickness ---
    prev_bot_od = None
    for i in range(n_cyl):
        thk = thks[i]
        od = inputs.id_top + 2 * thk
        length = lengths[i]
        thk_net = thk - inputs.ca_int - inputs.ca_ext
        weight = PI * ((od - thk) / 1000) * (thk / 1000) * length * (inputs.density * 1000)
        zones.append(ZoneGeometry(
            zone=i + 1, portion="Cylindrical", length=length,
            thk_gross=thk, thk_net=thk_net, top_od=od, bot_od=od, mean_od=od,
            weight=weight, elev_top=0, elev_mid=0,   # filled in later
        ))
        prev_bot_od = od

    # --- conical zones: OD tapers linearly per metre of cumulative height ---
    cone_top_od = prev_bot_od if prev_bot_od is not None else inputs.id_top
    cone_portion_total = sum(lengths[n_cyl:])
    cum_len = 0.0
    for j in range(n_cyl, n):
        thk = thks[j]
        length = lengths[j]
        top_od = cone_top_od + (inputs.flare_bot_od - cone_top_od) * (cum_len / cone_portion_total)
        cum_len += length
        bot_od = cone_top_od + (inputs.flare_bot_od - cone_top_od) * (cum_len / cone_portion_total)
        mean_od = (top_od + bot_od) / 2
        thk_net = thk - inputs.ca_int - inputs.ca_ext
        weight = PI * ((mean_od - thk) / 1000) * (thk / 1000) * length * (inputs.density * 1000)
        zones.append(ZoneGeometry(
            zone=j + 1, portion="Conical", length=length,
            thk_gross=thk, thk_net=thk_net, top_od=top_od, bot_od=bot_od, mean_od=mean_od,
            weight=weight, elev_top=0, elev_mid=0,
        ))

    # --- cumulative elevation, base (last zone) at ground ---
    cum = 0.0
    for z in reversed(zones):
        cum += z.length
        z.elev_top = cum
        z.elev_mid = cum - z.length / 2

    return zones


def total_shell_weight(zones: List[ZoneGeometry]) -> float:
    return sum(z.weight for z in zones)

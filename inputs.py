"""
IS 6533 Steel Chimney Design Tool - Web Edition
Inputs data model.

Mirrors the Excel/VBA tool's Inputs sheet, with the same field set
validated against the Kurkumbh 32m chimney. Zone-level overrides
(length, thickness, projected width) are handled as an editable table
in the UI rather than magic sheet cells - a cleaner pattern than the
Excel version's "type in D11, blank=auto" convention.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class ChimneyInputs:
    # --- Geometry ---
    H: float = 32.0                    # total height, m
    id_top: float = 800.0              # nominal internal dia (top, cylindrical), mm
    base_elev: float = 0.5             # elevation of base above ground, m
    lining: str = "None"
    insulation: str = "None"
    insul_thk: float = 0.0             # mm

    # --- Flare ---
    flare_h: float = 16.0              # flare height, m
    flare_bot_od: float = 1820.0       # flare bottom OD, mm (NOT the ID Dynastac
                                        # sometimes prints - convert ID->OD first!)

    # --- Shell material ---
    material: str = "IS 2062"
    density: float = 8.0               # gm/cc
    design_temp: float = 280.0         # deg C
    ca_int: float = 3.0                # corrosion allowance internal, mm
    ca_ext: float = 0.0                # corrosion allowance external, mm

    # --- Location & wind ---
    location: str = "Kurkumbh"
    vb: float = 39.0                   # basic wind speed, m/s
    seismic_zone: int = 3
    z_seismic: float = 0.20
    k1: float = 0.92
    terrain_cat: int = 3
    k3: float = 1.0
    ki: float = 1.0

    # --- Wind shape/attachment factors ---
    shape_cyl: float = 0.7             # Cf, shell shape factor
    shape_ladder: float = 1.2          # ladder/platform shape factor
    ladder_weight: float = 45.0        # kg/m

    # --- Platforms (up to 6) ---
    num_platforms: int = 2
    plat_elev: List[float] = field(default_factory=lambda: [30.5, 15.0, 0, 0, 0, 0])
    plat_width: List[float] = field(default_factory=lambda: [900, 900, 900, 900, 900, 900])   # mm
    plat_sweep: List[float] = field(default_factory=lambda: [360, 360, 360, 360, 360, 360])   # deg
    plat_weight: float = 160.0         # kg/m2 (dead)
    plat_imposed: float = 300.0        # kg/m2 (imposed/live)

    # --- Misc weights ---
    misc_weight: float = 960.0         # kg
    contingency_wt: float = 669.0      # kg

    # --- Zone discretisation ---
    max_zone_len: float = 6.0          # auto-split target, m (used only if no override table)


def default_zone_table(inputs: ChimneyInputs):
    """
    Build a default zone table (length, thickness, proj. dia) using the
    same auto-split logic as the VBA CalcZoneCounts, as a starting point
    for the editable table in the UI. Thickness defaults to the IS 6533
    Cl 7.3.1 minimum (6mm); proj. dia defaults to a flat ladder-width
    estimate (300mm) - both are meant to be edited by the user.
    """
    import math

    cyl_portion = inputs.H - inputs.flare_h
    cone_portion = inputs.flare_h
    max_z = min(max(inputs.max_zone_len, 0.1), 10.0)

    n_cyl = min(8, max(1, math.ceil(cyl_portion / max_z - 1e-9)))
    n_cone = min(6, max(1, math.ceil(cone_portion / max_z - 1e-9)))
    while (n_cyl + n_cone) < 3:
        if n_cone < 6:
            n_cone += 1
        else:
            n_cyl += 1

    rows = []
    for i in range(n_cyl):
        rows.append({
            "Zone": i + 1, "Portion": "Cylindrical",
            "Length (m)": round(cyl_portion / n_cyl, 3),
            "Thk gross (mm)": 6.0,
            "Proj Dia (mm)": 300.0,
        })
    for i in range(n_cone):
        rows.append({
            "Zone": n_cyl + i + 1, "Portion": "Conical",
            "Length (m)": round(cone_portion / n_cone, 3),
            "Thk gross (mm)": 6.0,
            "Proj Dia (mm)": 300.0,
        })
    return rows

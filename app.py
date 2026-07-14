"""
IS 6533 Steel Chimney Design Tool - Web Edition (v1)
Veda Engineering internal tool.

Ported from the Excel/VBA tool, carrying forward every fix validated
against the Kurkumbh 32m chimney on 14 Jul 2026:
  - Shell geometry: real per-zone lengths (editable table), correct
    linear-per-metre conical taper.
  - Wind loads: per-zone ladder/platform projected width.

v1 scope: Inputs, Shell Geometry, Static Wind Loads. Natural Frequency,
Gust Factor, Dynamic Analysis, Seismic, Combined Stress, Base
Foundation/Chair, and Flange Design are not yet ported - see the
roadmap note at the bottom of the page.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from modules.inputs import ChimneyInputs, default_zone_table
from modules.geometry import calc_shell_geometry, total_shell_weight
from modules.wind_loads import calc_wind_loads, total_base_shear_kg, total_base_moment_kgm

st.set_page_config(page_title="Chimney Design Tool | Veda Engineering", layout="wide")

st.title("🏭 IS 6533 Steel Chimney Design Tool")
st.caption("Veda Engineering · Web Edition v1 · Shell Geometry & Static Wind Loads")

# ---------------------------------------------------------------------
# SIDEBAR: INPUTS
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("Inputs")

    with st.expander("Geometry", expanded=True):
        H = st.number_input("Total height, H (m)", value=32.0, step=0.5)
        id_top = st.number_input("Top internal dia (mm)", value=800.0, step=10.0)
        base_elev = st.number_input("Base elevation above ground (m)", value=0.5, step=0.1)
        flare_h = st.number_input("Flare height (m)", value=16.0, step=0.5)
        flare_bot_od = st.number_input(
            "Flare bottom OD (mm)", value=1820.0, step=10.0,
            help="This is OUTER diameter. If your source report gives an ID, "
                 "add 2x the base zone thickness before entering it here.")

    with st.expander("Material & corrosion", expanded=False):
        density = st.number_input("Density (gm/cc)", value=8.0, step=0.05)
        design_temp = st.number_input("Design temperature (deg C)", value=280.0, step=10.0)
        ca_int = st.number_input("Corrosion allowance - internal (mm)", value=3.0, step=0.5)
        ca_ext = st.number_input("Corrosion allowance - external (mm)", value=0.0, step=0.5)
        insulation = st.selectbox("External insulation", ["None", "Present"], index=0)
        insul_thk = st.number_input("Insulation thickness (mm)", value=0.0, step=5.0,
                                     disabled=(insulation == "None"))

    with st.expander("Wind", expanded=False):
        vb = st.number_input("Basic wind speed, Vb (m/s)", value=39.0, step=0.5)
        k1 = st.number_input("Risk coefficient, K1", value=0.92, step=0.01)
        terrain_cat = st.selectbox("Terrain category", [1, 2, 3, 4], index=2)
        k3 = st.number_input("Topography factor, K3", value=1.0, step=0.01)
        ki = st.number_input("Interference factor, Ki", value=1.0, step=0.01)
        shape_cyl = st.number_input("Shape factor - cylinder, Cf", value=0.7, step=0.05)
        shape_ladder = st.number_input("Shape factor - ladder/platform", value=1.2, step=0.05)

    with st.expander("Zone auto-split (starting point)", expanded=False):
        max_zone_len = st.number_input("Max zone height for auto-split (m)", value=6.0, step=0.5)

inputs = ChimneyInputs(
    H=H, id_top=id_top, base_elev=base_elev, flare_h=flare_h, flare_bot_od=flare_bot_od,
    density=density, design_temp=design_temp, ca_int=ca_int, ca_ext=ca_ext,
    insulation=insulation, insul_thk=insul_thk,
    vb=vb, k1=k1, terrain_cat=terrain_cat, k3=k3, ki=ki,
    shape_cyl=shape_cyl, shape_ladder=shape_ladder,
    max_zone_len=max_zone_len,
)

# ---------------------------------------------------------------------
# MAIN: EDITABLE ZONE TABLE
# ---------------------------------------------------------------------
st.subheader("1. Zone Table")
st.caption(
    "Edit Length, Thickness, and Proj. Dia directly — no auto/manual toggle needed. "
    "'Proj Dia' is the ladder+platform projected width for that zone (mm); use a "
    "larger value at any zone that contains a platform (typically 300-500mm)."
)

if "zone_table" not in st.session_state or st.session_state.get("_last_h") != (H, flare_h, max_zone_len):
    st.session_state.zone_table = pd.DataFrame(default_zone_table(inputs))
    st.session_state["_last_h"] = (H, flare_h, max_zone_len)

edited = st.data_editor(
    st.session_state.zone_table,
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "Zone": st.column_config.NumberColumn(disabled=True),
        "Portion": st.column_config.SelectboxColumn(options=["Cylindrical", "Conical"], disabled=True),
        "Length (m)": st.column_config.NumberColumn(format="%.3f", min_value=0.1),
        "Thk gross (mm)": st.column_config.NumberColumn(format="%.1f", min_value=3.0),
        "Proj Dia (mm)": st.column_config.NumberColumn(format="%.0f", min_value=0.0),
    },
    key="zone_editor",
)
st.session_state.zone_table = edited
zone_rows = edited.to_dict("records")

total_len = sum(r["Length (m)"] for r in zone_rows)
col1, col2 = st.columns(2)
col1.metric("Total zone length", f"{total_len:.2f} m", delta=f"{total_len - H:+.2f} m vs H")
if abs(total_len - H) > 0.01:
    st.warning(f"Zone lengths sum to {total_len:.2f}m but H = {H:.2f}m — adjust lengths to match.")

# ---------------------------------------------------------------------
# SHELL GEOMETRY
# ---------------------------------------------------------------------
st.subheader("2. Shell Geometry")

zones = calc_shell_geometry(inputs, zone_rows)
geo_df = pd.DataFrame([{
    "Zone": z.zone, "Portion": z.portion, "Length (m)": round(z.length, 3),
    "Thk gross (mm)": z.thk_gross, "Thk net (mm)": round(z.thk_net, 2),
    "Top OD (mm)": round(z.top_od, 1), "Bottom OD (mm)": round(z.bot_od, 1),
    "Mean OD (mm)": round(z.mean_od, 1), "Shell Wt (kg)": round(z.weight, 1),
    "Elev top (m)": round(z.elev_top, 3),
} for z in zones])

st.dataframe(geo_df, use_container_width=True, hide_index=True)

total_wt = total_shell_weight(zones)
c1, c2, c3 = st.columns(3)
c1.metric("Total shell weight", f"{total_wt:,.1f} kg")
c2.metric("Base OD", f"{zones[-1].bot_od:,.1f} mm")
c3.metric("Top OD", f"{zones[0].top_od:,.1f} mm")

# OD profile chart
fig = go.Figure()
xs, ys = [], []
elev = 0.0
for z in reversed(zones):  # base to top
    xs += [-z.bot_od / 2, -z.top_od / 2]
    ys += [elev, elev + z.length]
    elev += z.length
fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#1f4e78", width=2), name="Left OD"))
fig.add_trace(go.Scatter(x=[-x for x in xs], y=ys, mode="lines", line=dict(color="#1f4e78", width=2),
                          name="Right OD", showlegend=False))
fig.update_layout(title="Shell profile (OD)", xaxis_title="mm", yaxis_title="Elevation (m)",
                   height=420, showlegend=False, xaxis=dict(scaleanchor="y"))
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------
# STATIC WIND LOADS
# ---------------------------------------------------------------------
st.subheader("3. Static Wind Loads (IS 875 Part 3 & IS 6533 Cl 8.2)")

proj_dia = [r["Proj Dia (mm)"] for r in zone_rows]
wind_loads = calc_wind_loads(inputs, zones, proj_dia)

wind_df = pd.DataFrame([{
    "Zone": w.zone, "Length (m)": round(zones[i].length, 3), "z_mid (m)": round(w.z_mid, 2),
    "k2": round(w.k2, 4), "Vz (m/s)": round(w.vz, 2), "Press (N/m2)": round(w.press, 1),
    "Force (N)": round(w.force_n, 1), "Force (kg)": round(w.force_kg, 1),
    "Arm (m)": round(w.arm, 2), "Moment (N.m)": round(w.moment_nm, 1),
} for i, w in enumerate(wind_loads)])

st.dataframe(wind_df, use_container_width=True, hide_index=True)

c1, c2 = st.columns(2)
c1.metric("Total base shear", f"{total_base_shear_kg(wind_loads):,.1f} kg")
c2.metric("Total base moment", f"{total_base_moment_kgm(wind_loads):,.1f} kg·m")

st.divider()
st.info(
    "**Roadmap:** Natural Frequency, Gust Factor, Dynamic Analysis, Seismic, "
    "Combined Stress, Base Foundation/Chair, and Flange Design are not yet "
    "ported to this web version. Ask to continue the port for any of these "
    "modules once you're happy with this slice."
)

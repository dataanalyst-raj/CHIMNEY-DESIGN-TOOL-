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

from inputs import ChimneyInputs, default_zone_table
from geometry import calc_shell_geometry, total_shell_weight
from wind_loads import calc_wind_loads, total_base_shear_kg, total_base_moment_kgm
from assets import VEDA_LOGO_B64

st.set_page_config(page_title="Chimney Design Tool | Veda Engineering",
                    page_icon="🏭", layout="wide")

# ═══════════════════════════════════════════════════════════════════
# STYLE — Veda brand palette (red #D8242D sampled from the logo mark),
# IBM Plex Sans for headers/body, IBM Plex Mono for all numeric/data
# output (a technical, spec-sheet register that fits an engineering
# calc tool rather than a generic system font).
# ═══════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {{
    --veda-red: #D8242D;
    --veda-red-dark: #A81820;
    --ink: #1A1A1A;
    --steel: #4A5568;
    --steel-light: #718096;
    --hairline: #E2E2E4;
    --panel: #F7F7F8;
}}

html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', -apple-system, sans-serif;
}}

/* FORCE LIGHT THEME regardless of the visitor's system/browser dark-mode
   setting - the brand palette above assumes a white page background, so
   Streamlit's auto dark-mode would otherwise make headers/text unreadable. */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
section.main, .main .block-container {{
    background-color: #FFFFFF !important;
}}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {{
    background-color: var(--panel) !important;
}}
[data-testid="stSidebar"] * {{
    color: var(--ink) !important;
}}
.stApp p, .stApp span, .stApp label, .stApp div, h1, h2, h3 {{
    color: var(--ink);
}}
[data-testid="stExpander"] {{
    background-color: #FFFFFF !important;
    border: 1px solid var(--hairline) !important;
}}

/* kill default streamlit chrome for a cleaner, branded feel */
#MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
.block-container {{ padding-top: 1rem; max-width: 1200px; }}

/* numeric output reads as monospace, like a spec sheet */
[data-testid="stDataFrame"] * , [data-testid="stMetricValue"], .stNumberInput input {{
    font-family: 'IBM Plex Mono', monospace !important;
}}

/* ---------- masthead ---------- */
.veda-masthead {{
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 18px 0 16px 0;
    border-bottom: 3px solid var(--veda-red);
    margin-bottom: 28px;
}}
.veda-masthead img {{ height: 56px; width: 56px; object-fit: contain; }}
.veda-masthead .title-block {{ line-height: 1.15; }}
.veda-masthead .company {{
    font-size: 12px; font-weight: 600; letter-spacing: 0.14em;
    color: var(--veda-red); text-transform: uppercase; margin: 0 0 2px 0;
}}
.veda-masthead .tool-name {{
    font-size: 26px; font-weight: 700; color: var(--ink); margin: 0;
}}
.veda-masthead .tool-sub {{
    font-size: 13px; color: var(--steel-light); margin: 2px 0 0 0;
}}

/* ---------- step rail: reflects the real calc pipeline ---------- */
.step-header {{
    display: flex; align-items: center; gap: 14px;
    margin: 8px 0 4px 0;
}}
.step-badge {{
    flex-shrink: 0; width: 30px; height: 30px; border-radius: 50%;
    background: var(--veda-red); color: white; font-family: 'IBM Plex Mono', monospace;
    font-weight: 600; font-size: 14px; display: flex; align-items: center;
    justify-content: center;
}}
.step-title {{ font-size: 19px; font-weight: 700; color: var(--ink); margin: 0; }}
.step-caption {{ font-size: 13px; color: var(--steel-light); margin: 2px 0 18px 44px; }}
.step-rail {{
    border-left: 2px solid var(--hairline); margin-left: 14px; padding-left: 30px;
    margin-bottom: 6px;
}}

/* ---------- stat cards (replace default st.metric look) ---------- */
.stat-row {{ display: flex; gap: 14px; margin: 4px 0 22px 0; flex-wrap: wrap; }}
.stat-card {{
    background: var(--panel); border: 1px solid var(--hairline); border-radius: 6px;
    padding: 14px 18px; flex: 1; min-width: 160px;
}}
.stat-card .label {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.06em; color: var(--steel-light);
    text-transform: uppercase; margin: 0 0 4px 0;
}}
.stat-card .value {{
    font-family: 'IBM Plex Mono', monospace; font-size: 22px; font-weight: 600;
    color: var(--ink); margin: 0;
}}
.stat-card .delta {{ font-size: 12px; color: var(--steel-light); margin-top: 2px; }}
.stat-card.accent {{ border-left: 3px solid var(--veda-red); }}

/* section spacing */
.section-gap {{ margin-top: 38px; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# MASTHEAD
# ---------------------------------------------------------------------
st.markdown(f"""
<div class="veda-masthead">
    <img src="data:image/png;base64,{VEDA_LOGO_B64}" alt="Veda Engineering">
    <div class="title-block">
        <p class="company">Veda Engineering</p>
        <p class="tool-name">Steel Chimney Design Tool</p>
        <p class="tool-sub">IS 6533 (Part 2) &middot; Self-Supporting Steel Chimneys &middot; Web Edition v1</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# SIDEBAR: INPUTS
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Inputs")

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

    st.markdown("---")
    st.caption("Veda Engineering · Internal Tool · v1")

inputs = ChimneyInputs(
    H=H, id_top=id_top, base_elev=base_elev, flare_h=flare_h, flare_bot_od=flare_bot_od,
    density=density, design_temp=design_temp, ca_int=ca_int, ca_ext=ca_ext,
    insulation=insulation, insul_thk=insul_thk,
    vb=vb, k1=k1, terrain_cat=terrain_cat, k3=k3, ki=ki,
    shape_cyl=shape_cyl, shape_ladder=shape_ladder,
    max_zone_len=max_zone_len,
)


def stat_card(label, value, delta=None, accent=False):
    accent_cls = " accent" if accent else ""
    delta_html = f'<div class="delta">{delta}</div>' if delta else ""
    return f"""<div class="stat-card{accent_cls}">
        <p class="label">{label}</p>
        <p class="value">{value}</p>
        {delta_html}
    </div>"""


def step_header(number, title, caption):
    st.markdown(f"""
    <div class="section-gap">
    <div class="step-header">
        <div class="step-badge">{number}</div>
        <p class="step-title">{title}</p>
    </div>
    <p class="step-caption">{caption}</p>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# STEP 1 — ZONE TABLE
# ---------------------------------------------------------------------
step_header(1, "Zone Table",
             "Edit Length, Thickness, and Proj. Dia directly. 'Proj Dia' is the "
             "ladder+platform projected width for that zone (mm) — use a larger "
             "value at any zone that contains a platform, typically 300-500mm.")

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
delta_txt = f"{total_len - H:+.2f} m vs H = {H:.2f} m"
st.markdown(f'<div class="stat-row">{stat_card("Total zone length", f"{total_len:.2f} m", delta_txt, accent=abs(total_len-H)>0.01)}</div>',
            unsafe_allow_html=True)
if abs(total_len - H) > 0.01:
    st.warning(f"Zone lengths sum to {total_len:.2f}m but H = {H:.2f}m — adjust lengths to match.")

# ---------------------------------------------------------------------
# STEP 2 — SHELL GEOMETRY
# ---------------------------------------------------------------------
step_header(2, "Shell Geometry",
             "Zone-by-zone weight and OD profile, computed from the table above.")

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
st.markdown(f"""<div class="stat-row">
    {stat_card("Total shell weight", f"{total_wt:,.1f} kg", accent=True)}
    {stat_card("Base OD", f"{zones[-1].bot_od:,.1f} mm")}
    {stat_card("Top OD", f"{zones[0].top_od:,.1f} mm")}
</div>""", unsafe_allow_html=True)

# OD profile chart
fig = go.Figure()
xs, ys = [], []
elev = 0.0
for z in reversed(zones):  # base to top
    xs += [-z.bot_od / 2, -z.top_od / 2]
    ys += [elev, elev + z.length]
    elev += z.length
fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#D8242D", width=2.5), name="Left OD"))
fig.add_trace(go.Scatter(x=[-x for x in xs], y=ys, mode="lines", line=dict(color="#D8242D", width=2.5),
                          name="Right OD", showlegend=False))
fig.update_layout(
    title=dict(text="Shell Profile (OD)", font=dict(family="IBM Plex Sans", size=15, color="#1A1A1A")),
    xaxis_title="mm", yaxis_title="Elevation (m)",
    height=420, showlegend=False, xaxis=dict(scaleanchor="y"),
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    font=dict(family="IBM Plex Mono", size=11, color="#4A5568"),
    margin=dict(t=50, l=10, r=10, b=10),
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------
# STEP 3 — STATIC WIND LOADS
# ---------------------------------------------------------------------
step_header(3, "Static Wind Loads",
             "IS 875 Part 3 &amp; IS 6533 Cl 8.2 — per-zone design wind pressure and force.")

proj_dia = [r["Proj Dia (mm)"] for r in zone_rows]
wind_loads = calc_wind_loads(inputs, zones, proj_dia)

wind_df = pd.DataFrame([{
    "Zone": w.zone, "Length (m)": round(zones[i].length, 3), "z_mid (m)": round(w.z_mid, 2),
    "k2": round(w.k2, 4), "Vz (m/s)": round(w.vz, 2), "Press (N/m2)": round(w.press, 1),
    "Force (N)": round(w.force_n, 1), "Force (kg)": round(w.force_kg, 1),
    "Arm (m)": round(w.arm, 2), "Moment (N.m)": round(w.moment_nm, 1),
} for i, w in enumerate(wind_loads)])

st.dataframe(wind_df, use_container_width=True, hide_index=True)

st.markdown(f"""<div class="stat-row">
    {stat_card("Total base shear", f"{total_base_shear_kg(wind_loads):,.1f} kg", accent=True)}
    {stat_card("Total base moment", f"{total_base_moment_kgm(wind_loads):,.1f} kg&middot;m", accent=True)}
</div>""", unsafe_allow_html=True)

st.markdown("---")
st.info(
    "**Roadmap:** Natural Frequency, Gust Factor, Dynamic Analysis, Seismic, "
    "Combined Stress, Base Foundation/Chair, and Flange Design are not yet "
    "ported to this web version. Ask to continue the port for any of these "
    "modules once you're happy with this slice."
)
st.caption("Veda Engineering · Internal Tool · Validated against Kurkumbh 32m chimney design (Dynastac reference, 08/01/2025)")

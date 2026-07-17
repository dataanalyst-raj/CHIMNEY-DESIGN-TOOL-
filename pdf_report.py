"""
PDF REPORT GENERATOR - builds a downloadable design report from
everything the app has already computed. Doesn't recompute anything,
just formats the existing results.
"""
import base64
import io
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                 PageBreak, Image, HRFlowable)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from assets import VEDA_LOGO_B64

VEDA_RED = colors.HexColor("#D8242D")
INK = colors.HexColor("#1A1A1A")
STEEL = colors.HexColor("#4A5568")
PANEL = colors.HexColor("#F7F7F8")
HAIRLINE = colors.HexColor("#E2E2E4")

_styles = getSampleStyleSheet()
_styles.add(ParagraphStyle("VedaTitle", parent=_styles["Title"], textColor=INK, fontSize=20, spaceAfter=2))
_styles.add(ParagraphStyle("VedaCompany", parent=_styles["Normal"], textColor=VEDA_RED,
                            fontSize=10, fontName="Helvetica-Bold", spaceAfter=2))
_styles.add(ParagraphStyle("VedaSub", parent=_styles["Normal"], textColor=STEEL, fontSize=9))
_styles.add(ParagraphStyle("SectionHead", parent=_styles["Heading2"], textColor=INK,
                            fontSize=13, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold"))
_styles.add(ParagraphStyle("Caption", parent=_styles["Normal"], textColor=STEEL, fontSize=8,
                            spaceAfter=8))
_styles.add(ParagraphStyle("Disclosed", parent=_styles["Normal"], textColor=colors.HexColor("#A85C00"),
                            fontSize=8, spaceAfter=4, leftIndent=8))


def _section(title, caption=None):
    flow = [Paragraph(title, _styles["SectionHead"])]
    if caption:
        flow.append(Paragraph(caption, _styles["Caption"]))
    return flow


def _data_table(headers, rows, col_widths=None):
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9D9D9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, HAIRLINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
    ]))
    return t


def _stat_line(pairs):
    """pairs: list of (label, value) tuples -> a compact 2-col-per-item table."""
    row = []
    for label, value in pairs:
        row.append(Paragraph(f"<b>{label}:</b> {value}", _styles["Normal"]))
    t = Table([row], colWidths=[None] * len(row))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def generate_pdf_report(inputs, zones, zone_rows, wind_loads, defl, nf, gust, strakes,
                         sc, dyn, vortex, eq_ah, gov, cs, bf, bcs, fd) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm,
                             leftMargin=15 * mm, rightMargin=15 * mm)
    story = []

    # ---- Header ----
    logo_bytes = base64.b64decode(VEDA_LOGO_B64)
    logo = Image(io.BytesIO(logo_bytes), width=16 * mm, height=16 * mm)
    header_tbl = Table([[logo, Paragraph(
        "VEDA ENGINEERING<br/><b>Steel Chimney Design Report</b><br/>"
        f"<font size=9 color='#4A5568'>IS 6533 (Part 2) &middot; Self-Supporting Steel Chimneys &middot; "
        f"Generated {date.today().strftime('%d %b %Y')}</font>", _styles["Normal"])]],
        colWidths=[20 * mm, None])
    header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(header_tbl)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2, color=VEDA_RED))
    story.append(Spacer(1, 10))

    # ---- Key inputs summary ----
    story += _section("Design Summary")
    story.append(_stat_line([
        ("Location", inputs.location), ("Height H", f"{inputs.H:.1f} m"),
        ("Top ID", f"{inputs.id_top:.0f} mm"), ("Flare height", f"{inputs.flare_h:.1f} m"),
    ]))
    story.append(_stat_line([
        ("Basic wind speed", f"{inputs.vb:.0f} m/s"), ("Seismic Z", f"{inputs.z_seismic:.2f}"),
        ("Terrain category", f"{inputs.terrain_cat}"), ("Design temp", f"{inputs.design_temp:.0f} degC"),
    ]))
    story.append(Spacer(1, 4))

    headline_rows = [
        ["Total shell weight", f"{sum(z.weight for z in zones):,.0f} kg"],
        ["Governing base moment", f"{gov.gov_base_moment:,.0f} kg-m"],
        ["Base shear", f"{cs[-1].shear:,.0f} kg"],
        ["Natural frequency", f"{nf.nat_freq:.4f} Hz"],
        ["Top deflection / allowable", f"{defl.top_deflection:.2f} / {defl.defl_allow:.2f} cm ({'OK' if defl.defl_ok else 'EXCEEDS'})"],
        ["Base chair status", bcs.status],
        ["Flange design status", "OK" if fd.stress_ok else "CHECK"],
    ]
    story.append(_data_table(["Headline result", "Value"], headline_rows, col_widths=[80 * mm, 90 * mm]))
    story.append(PageBreak())

    # ---- Zone Table / Shell Geometry ----
    story += _section("Shell Geometry", "Zone-by-zone weight and OD profile.")
    geo_rows = [[z.zone, z.portion, f"{z.length:.3f}", f"{z.thk_gross:.1f}", f"{z.thk_net:.2f}",
                 f"{z.top_od:.0f}", f"{z.bot_od:.0f}", f"{z.mean_od:.0f}", f"{z.weight:.1f}"]
                for z in zones]
    story.append(_data_table(
        ["Zone", "Portion", "Len (m)", "Thk gr (mm)", "Thk net (mm)", "Top OD", "Bot OD", "Mean OD", "Wt (kg)"],
        geo_rows))
    story.append(Spacer(1, 10))

    # ---- Static Wind Loads ----
    story += _section("Static Wind Loads", "IS 875 Part 3 &amp; IS 6533 Cl 8.2.")
    wl_rows = [[w.zone, f"{w.z_mid:.2f}", f"{w.k2:.4f}", f"{w.vz:.2f}", f"{w.press:.1f}",
                f"{w.force_kg:.1f}"] for w in wind_loads]
    story.append(_data_table(["Zone", "z_mid (m)", "k2", "Vz (m/s)", "Press (N/m2)", "Force (kg)"], wl_rows))
    story.append(Spacer(1, 10))

    # ---- Static Deflection ----
    story += _section("Static Deflection", "IS 6533 Cl 7.4, moment-area method.")
    story.append(_stat_line([
        ("Top deflection", f"{defl.top_deflection:.2f} cm"), ("Allowable H/200", f"{defl.defl_allow:.2f} cm"),
        ("Check", "OK" if defl.defl_ok else "EXCEEDS LIMIT"),
    ]))
    story.append(PageBreak())

    # ---- Natural Frequency ----
    story += _section("Natural Frequency", "Rayleigh method, IS 6533 Cl 8.3.1.")
    story.append(_stat_line([("Natural frequency", f"{nf.nat_freq:.4f} Hz"), ("Period", f"{nf.nat_period:.4f} s")]))
    story.append(Paragraph(
        "Disclosed open item: a consistent ~217kg/zone mass residual vs a reference design remains "
        "unexplained - natural frequency may read somewhat high vs the true design.", _styles["Disclosed"]))
    story.append(Spacer(1, 10))

    # ---- Gust Factor & Across-Wind ----
    story += _section("Gust Factor &amp; Across-Wind Check", "IS 875 Part 3 Gust Factor Method Cl 8.3.")
    story.append(_stat_line([
        ("gfr", f"{gust.gfr:.4f}"), ("L(h)", f"{gust.lh:.1f} m"), ("Vh", f"{gust.vh:.2f} m/s"),
        ("Gust Factor G", f"{gust.G:.4f}"),
    ]))
    story.append(_stat_line([
        ("Critical Vcr", f"{strakes.vcr:.3f} m/s"),
        ("Helical strakes", "REQUIRED" if strakes.needed else "Not required"),
    ]))
    story.append(Paragraph(
        "Disclosed open item: gfr and Vh each carry independent gaps that happened to cancel in the "
        "final G on the validated reference - not guaranteed to hold for every height/terrain.",
        _styles["Disclosed"]))
    story.append(Spacer(1, 10))

    # ---- Allowable Stress ----
    story += _section("Allowable Stress", "IS 6533 Annex C &amp; Cl 7.3.1.")
    sc_rows = [[s.zone, f"{s.he:.2f}", f"{s.he_d:.3f}", f"{s.d_t:.1f}", f"{s.factor_a:.4f}",
                f"{s.factor_b:.4f}", f"{s.allow_mpa:.2f}"] for s in sc]
    story.append(_data_table(["Zone", "he (m)", "he/D", "D/t", "Factor A", "Factor B", "Allow (MPa)"], sc_rows))
    story.append(PageBreak())

    # ---- Dynamic Analysis ----
    story += _section("Dynamic Analysis (Mode 1)", "IS 6533 Cl 8.3 modal wind load.")
    dyn_rows = [[i + 1, f"{nf.mass[i]:.1f}", f"{nf.defl[i]:.3f}", f"{wind_loads[i].force_kg:.1f}",
                 f"{dyn.dyn_load[i]:.1f}"] for i in range(len(zones))]
    story.append(_data_table(["Zone", "Mass (kg)", "Mode y (cm)", "Pstat (kg)", "Dyn Load (kg)"], dyn_rows))
    story.append(Spacer(1, 10))

    # ---- Governing Loads ----
    story += _section("Governing Design Moment", "IS 6533 + IS 1893. Governing = MAX of 3 wind methods.")
    story.append(_stat_line([
        ("Vortex Vcr (Cl 8.4)", f"{vortex.vcr:.3f} m/s ({vortex.resonance})"),
        ("Seismic coeff ah", f"{eq_ah:.5f}"), ("Governing base moment", f"{gov.gov_base_moment:,.1f} kg-m"),
    ]))
    gov_rows = [[i + 1, f"{gov.f_3smw[i]:.1f}", f"{gov.f_hmw_inertia[i]:.1f}", f"{gov.f_gef[i]:.1f}",
                 f"{gov.gov_force[i]:.1f}", f"{gov.gov_bm[i]:.1f}"] for i in range(len(zones))]
    story.append(_data_table(["Zone", "3-sec Static", "HMW+Inertia", "GEF", "Gov Force", "Gov BM"], gov_rows))
    story.append(Paragraph(
        "Disclosed open item: the seismic Sa/g curve doesn't hold well outside its originally-fitted "
        "period range.", _styles["Disclosed"]))
    story.append(PageBreak())

    # ---- Combined Stress ----
    story += _section("Combined Stress", "IS 6533 Cl 7.7 - cumulative shell stress table.")
    cs_rows = [[c.zone, f"{c.shear:.1f}", f"{c.dead_imp:.1f}", f"{c.bm:.1f}", f"{c.compr_st:.2f}",
                f"{c.bend_st:.2f}", f"{c.total_st:.2f}", f"{c.allow_st:.1f}", "OK" if c.check_ok else "FAIL"]
               for c in cs]
    story.append(_data_table(
        ["Sect", "Shear", "Dead+Imp", "BM", "Compr", "Bend", "Total", "Allow", "Chk"], cs_rows))
    story.append(Spacer(1, 10))

    # ---- Base Foundation & Chair Stress ----
    story += _section("Base Foundation &amp; Chair Stress", "B&amp;Y detailed checks.")
    story.append(_stat_line([
        ("PCD", f"{bf.pcd:,.0f} mm"), ("Bolt count N", f"{bf.n_bolts}"),
        ("Bearing pressure", f"{bf.bearing_pressure:.2f} kg/cm2"), ("Bolt tension", f"{bf.bolt_tension:,.0f} kg"),
    ]))
    story.append(_stat_line([
        ("Base plate stress", f"{bcs.base_plate_stress:.1f} kg/cm2"),
        ("Compression plate stress", f"{bcs.compr_plate_stress:.1f} kg/cm2"),
        ("Gusset stress/allow", f"{bcs.gusset_stress:.1f} / {bcs.gusset_allow:.1f} kg/cm2"),
        ("Status", bcs.status),
    ]))
    story.append(Paragraph(
        "Disclosed open item: an unexplained ~40%-of-expected effective bolt area gap remains in the "
        "B&amp;Y k-solve, even though the formula itself was verified faithful to the Brownell &amp; Young "
        "textbook's own worked example.", _styles["Disclosed"]))
    story.append(Spacer(1, 10))

    # ---- Flange Design ----
    story += _section("Flange Design", "IS 6533 Cl 8.6 - inter-zone flanges &amp; bolts.")
    fd_rows = [[j.joint, f"{j.od:.0f}", f"{j.id_:.0f}", f"{j.pcd:.0f}", "M24", j.n_bolts, j.thk]
               for j in fd.joints]
    story.append(_data_table(["Joint", "OD", "ID", "PCD", "Bolt", "Qty", "Thk (mm)"], fd_rows))
    story.append(_stat_line([
        ("Governing bolt force", f"{fd.bolt_force:,.0f} kg"), ("Induced stress", f"{fd.stress:.0f} kg/cm2"),
        ("Status", "OK" if fd.stress_ok else "CHECK"),
    ]))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=HAIRLINE))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Veda Engineering &middot; Internal Tool &middot; Web Edition &middot; "
        "All disclosed open items above are documented in the tool's own source code comments.",
        _styles["Caption"]))

    doc.build(story)
    buf.seek(0)
    return buf.read()

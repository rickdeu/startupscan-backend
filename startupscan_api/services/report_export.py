import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String


# ── Typography ───────────────────────────────────────────────────────────────
# DejaVu Sans ships inside matplotlib (a pinned dependency of this project),
# so it is always available on the deployment host without bundling extra
# font assets. It gives a more distinctive, editorial look than the bare
# Helvetica base-14 font and has broad glyph coverage for the symbols used
# throughout the report (✔ ✘ ▸ ● ★ ✦).
def _register_report_fonts():
    try:
        import matplotlib

        base = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
        pdfmetrics.registerFont(TTFont("DejaVuSans", os.path.join(base, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(base, "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Oblique", os.path.join(base, "DejaVuSans-Oblique.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVuSans-BoldOblique", os.path.join(base, "DejaVuSans-BoldOblique.ttf")))
        pdfmetrics.registerFontFamily(
            "DejaVuSans",
            normal="DejaVuSans",
            bold="DejaVuSans-Bold",
            italic="DejaVuSans-Oblique",
            boldItalic="DejaVuSans-BoldOblique",
        )
        return "DejaVuSans", "DejaVuSans-Bold", "DejaVuSans-Oblique", "DejaVuSans-BoldOblique"
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique"


F_REG, F_BOLD, F_ITALIC, F_BOLDITALIC = _register_report_fonts()


# ── Color palette ───────────────────────────────────────────────────────────
C_NAVY    = colors.HexColor("#14161a")
C_BLUE    = colors.HexColor("#f5580d")
C_BLUE_LT = colors.HexColor("#ffede0")
C_BLUE_MD = colors.HexColor("#ffd9bc")
C_SLATE   = colors.HexColor("#475569")
C_SLATE_LT = colors.HexColor("#f8fafc")
C_BORDER  = colors.HexColor("#e2e8f0")
C_GREEN   = colors.HexColor("#16a34a")
C_GREEN_LT = colors.HexColor("#dcfce7")
C_RED     = colors.HexColor("#dc2626")
C_RED_LT  = colors.HexColor("#fee2e2")
C_AMBER   = colors.HexColor("#d97706")
C_AMBER_LT = colors.HexColor("#fef3c7")
C_VIOLET  = colors.HexColor("#b8720a")
C_VIOLET_LT = colors.HexColor("#fbf0dc")
C_VIOLET_MD = colors.HexColor("#f0d8a8")
C_WHITE   = colors.white
C_KICKER  = colors.HexColor("#ffb27a")

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static", "img", "icon.png")


def _logo_flowable(height: float = 20):
    """Returns a proportionally-scaled logo Image flowable, or None if the asset is missing."""
    if not os.path.exists(LOGO_PATH):
        return None
    try:
        from PIL import Image as PILImage
        with PILImage.open(LOGO_PATH) as im:
            ratio = im.width / im.height
    except Exception:
        ratio = 0.75
    return Image(LOGO_PATH, width=height * ratio, height=height)


# ── Styles ───────────────────────────────────────────────────────────────────
def _build_styles():
    base = getSampleStyleSheet()

    def s(name, **kw):
        kw.setdefault("fontName", F_REG)
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "cover_meta":  s("cover_meta",  fontSize=9,  textColor=colors.HexColor("#cbd5e1"),
                         leading=14),
        "section_h":   s("section_h",   fontSize=13, textColor=C_NAVY,
                         fontName=F_BOLD, spaceBefore=14, spaceAfter=6),
        "sub_h":       s("sub_h",       fontSize=10, textColor=C_BLUE,
                         fontName=F_BOLD, spaceBefore=8, spaceAfter=4),
        "body":        s("body",        fontSize=9,  textColor=C_NAVY,
                         leading=14, spaceAfter=4),
        "bullet":      s("bullet",      fontSize=9,  textColor=C_NAVY,
                         leading=14, leftIndent=12, spaceAfter=3),
        "small":       s("small",       fontSize=8,  textColor=C_SLATE,
                         leading=12),
        "caption":     s("caption",     fontSize=8.3, textColor=C_SLATE,
                         leading=12, spaceAfter=6, fontName=F_ITALIC),
        "kpi_value":   s("kpi_value",   fontSize=16, textColor=C_NAVY,
                         fontName=F_BOLD, alignment=TA_CENTER),
        "kpi_label":   s("kpi_label",   fontSize=7,  textColor=C_SLATE,
                         alignment=TA_CENTER),
        "kpi_icon":    s("kpi_icon",    fontSize=10, textColor=C_BLUE,
                         alignment=TA_CENTER),
        "tag_green":   s("tag_green",   fontSize=8,  textColor=C_GREEN,
                         fontName=F_BOLD),
        "tag_amber":   s("tag_amber",   fontSize=8,  textColor=C_AMBER,
                         fontName=F_BOLD),
        "tag_red":     s("tag_red",     fontSize=8,  textColor=C_RED,
                         fontName=F_BOLD),
        "footer":      s("footer",      fontSize=7,  textColor=C_SLATE,
                         alignment=TA_CENTER),
        "canvas_block_title": s("canvas_block_title", fontSize=8.5, textColor=C_VIOLET,
                                fontName=F_BOLD, leading=11, spaceAfter=3),
        "canvas_item": s("canvas_item", fontSize=7.3, textColor=C_NAVY,
                         leading=10, spaceAfter=2),
        "canvas_intro": s("canvas_intro", fontSize=9, textColor=C_SLATE,
                          leading=13, spaceAfter=8, fontName=F_ITALIC),
        "pill_text":   s("pill_text",   fontSize=7.6, fontName=F_BOLD,
                         alignment=TA_CENTER),
        "card_title":  s("card_title",  fontSize=9,  textColor=C_NAVY,
                         fontName=F_BOLD, leading=12, spaceAfter=4),
        "card_item":   s("card_item",   fontSize=7.6, textColor=C_NAVY,
                         leading=11, spaceAfter=2),
        "card_item_lg": s("card_item_lg", fontSize=8.7, textColor=C_NAVY,
                          leading=13, spaceAfter=3),
        "callout_body": s("callout_body", fontSize=9, textColor=C_NAVY,
                          leading=14),
    }


def _hr(color=None, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness,
                      color=color or C_BORDER, spaceAfter=8, spaceBefore=4)


def _score_color(score: float):
    if score >= 7.5:
        return C_GREEN, C_GREEN_LT
    if score >= 5.0:
        return C_AMBER, C_AMBER_LT
    return C_RED, C_RED_LT


def _score_tier_label(score: float, t: dict) -> str:
    if score >= 8:
        return t.get("report_pdf_score_excellent", "Excelente")
    if score >= 6.5:
        return t.get("report_pdf_score_good", "Bom")
    if score >= 5:
        return t.get("report_pdf_score_regular", "Regular")
    return t.get("report_pdf_rating_weak", "Fraco")


def _tracked_label(text: str, font_name: str, font_size: float, color, tracking: float = 1.6):
    """
    Letter-spaced "eyebrow" label rendered as individually-placed glyphs.
    ReportLab's Paragraph line-breaker tokenizes on any whitespace
    (including thin/em-space tricks) and re-flows every gap to the font's
    plain space width, so inserting Unicode spacing characters into a
    Paragraph string can't produce real letter-tracking. Drawing each
    character at a manually advanced x position sidesteps that entirely.
    """
    x = 0.0
    positions = []
    for ch in text.upper():
        positions.append((ch, x))
        x += stringWidth(ch, font_name, font_size) + tracking
    total_width = max(1.0, x - tracking)
    height = font_size * 1.3
    d = Drawing(total_width, height)
    baseline = height * 0.26
    for ch, cx in positions:
        d.add(String(cx, baseline, ch, fontName=font_name, fontSize=font_size, fillColor=color))
    return d


def _truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _hexval(color) -> str:
    return color.hexval()[2:] if hasattr(color, "hexval") else "0f172a"


def _pill(text: str, fg, bg):
    """Small rounded chip used for badges/tags (score tier, industry, id...)."""
    style = ParagraphStyle("pill", fontSize=7.6, fontName=F_BOLD,
                            textColor=fg, alignment=TA_CENTER, leading=10)
    tbl = Table([[Paragraph(text, style)]])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), bg),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))
    return tbl


def _chip_row(chips: list):
    if not chips:
        return None
    row = Table([chips])
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]
    for i in range(len(chips) - 1):
        style.append(("RIGHTPADDING", (i, 0), (i, 0), 6))
    row.setStyle(TableStyle(style))
    return row


# ── Score gauge (donut) ──────────────────────────────────────────────────────
def _build_score_gauge(score: float, fg_color, size: float = 98):
    d = Drawing(size, size)
    pie = Pie()
    pie.x = 0
    pie.y = 0
    pie.width = size
    pie.height = size
    pie.data = [max(0.05, score), max(0.05, 10.0 - score)]
    pie.slices.strokeWidth = 0
    pie.slices.label_visible = 0
    pie.slices[0].fillColor = fg_color
    pie.slices[1].fillColor = C_BORDER
    pie.startAngle = 90
    pie.direction = "clockwise"
    d.add(pie)

    hole_r = size * 0.34
    cx = cy = size / 2.0
    d.add(Circle(cx, cy, hole_r, fillColor=C_WHITE, strokeColor=None))
    d.add(String(cx, cy + size * 0.01, f"{score:.1f}", textAnchor="middle",
                 fontName=F_BOLD, fontSize=size * 0.24, fillColor=C_NAVY))
    d.add(String(cx, cy - size * 0.20, "/ 10", textAnchor="middle",
                 fontName=F_REG, fontSize=size * 0.09, fillColor=C_SLATE))
    return d


# ── Mini inline progress bar (used in the category table) ──────────────────
def _mini_bar(value: float, color, max_value: float = 10.0, width: float = 62, height: float = 7):
    d = Drawing(width, height)
    r = height / 2.0
    d.add(Rect(0, 0, width, height, rx=r, ry=r, fillColor=C_BORDER, strokeColor=None))
    filled_w = max(height, width * max(0.0, min(1.0, value / max_value)))
    d.add(Rect(0, 0, filled_w, height, rx=r, ry=r, fillColor=color, strokeColor=None))
    return d


# ── Native bar chart ─────────────────────────────────────────────────────────
def _build_category_chart(categories: dict, t: dict, category_labels: dict | None = None):
    from reportlab.graphics.charts.barcharts import VerticalBarChart

    category_labels = category_labels or {}
    labels = [category_labels.get(k) or k.replace("_", " ").title() for k in categories.keys()]
    values_list = [float(v) for v in categories.values()]
    average = sum(values_list) / len(values_list) if values_list else 0.0

    d = Drawing(460, 212)
    chart = VerticalBarChart()
    chart.x = 60
    chart.y = 48
    chart.width = 380
    chart.height = 128
    chart.data = [values_list]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.angle = 28
    chart.categoryAxis.labels.dy = -14
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fontName = F_REG
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 10
    chart.valueAxis.valueStep = 2
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontName = F_REG
    chart.bars.strokeColor = None
    chart.barLabelFormat = "%0.1f"
    chart.barLabels.nudge = 7
    chart.barLabels.fontName = F_BOLD
    chart.barLabels.fontSize = 7
    chart.barLabels.boxAnchor = "n"
    for i, v in enumerate(values_list):
        fg, _bg = _score_color(v)
        chart.bars[(0, i)].fillColor = fg
    d.add(chart)

    title = String(230, 198, t.get("report_pdf_category_score_chart_title", "Pontuação por Categoria (0–10)"),
                   textAnchor="middle", fontName=F_BOLD, fontSize=8.5, fillColor=C_NAVY)
    d.add(title)

    if values_list:
        avg_y = chart.y + (average / 10.0) * chart.height
        d.add(Line(chart.x, avg_y, chart.x + chart.width, avg_y,
                    strokeColor=C_SLATE, strokeWidth=0.6, strokeDashArray=(2, 2)))
        d.add(String(chart.x + chart.width + 4, avg_y - 3,
                      f"{t.get('report_pdf_average_label', 'Average')} {average:.1f}",
                      fontName=F_REG, fontSize=6.3, fillColor=C_SLATE))

    legend_items = [
        (t.get("report_pdf_rating_strong", "Strong"), C_GREEN),
        (t.get("report_pdf_rating_moderate", "Moderate"), C_AMBER),
        (t.get("report_pdf_rating_weak", "Weak"), C_RED),
    ]
    lx = chart.x
    for label_text, c in legend_items:
        d.add(Rect(lx, 8, 7, 7, fillColor=c, strokeColor=None))
        d.add(String(lx + 10, 8, label_text, fontName=F_REG, fontSize=6.3, fillColor=C_SLATE))
        lx += 10 + stringWidth(label_text, F_REG, 6.3) + 16
    return d


# ── Financial KPI table ──────────────────────────────────────────────────────
def _build_kpi_table(analysis, styles, t: dict):
    score = float(analysis.success_score or 0)
    fg, bg = _score_color(score)

    kpi_data = [
        [
            Paragraph("★", styles["kpi_icon"]),
            Paragraph("AOA", styles["kpi_icon"]),
            Paragraph("▲", styles["kpi_icon"]),
            Paragraph("◆", styles["kpi_icon"]),
        ],
        [
            Paragraph(f"{score:.1f}/10", styles["kpi_value"]),
            Paragraph(f"{float(analysis.revenue or 0):,.0f}", styles["kpi_value"]),
            Paragraph(f"{float(analysis.growth_rate or 0):.1f}%", styles["kpi_value"]),
            Paragraph(f"{float(analysis.profit_margin or 0):.1f}%", styles["kpi_value"]),
        ],
        [
            Paragraph(t.get("report_pdf_final_score", "Score Final"), styles["kpi_label"]),
            Paragraph(t.get("revenue", "Receita"), styles["kpi_label"]),
            Paragraph(t.get("growth", "Crescimento"), styles["kpi_label"]),
            Paragraph(t.get("report_pdf_profit_margin", "Margem de Lucro"), styles["kpi_label"]),
        ],
    ]
    col_w = (PAGE_W - 2 * MARGIN) / 4
    tbl = Table(kpi_data, colWidths=[col_w] * 4, rowHeights=[16, 26, 16])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, 1), bg),
        ("BACKGROUND",  (1, 0), (-1, 1), C_SLATE_LT),
        ("BACKGROUND",  (0, 2), (-1, 2), C_BORDER),
        ("GRID",        (0, 0), (-1, -1), 0.4, C_BORDER),
        ("ROUNDEDCORNERS", [4]),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


# ── Category score table ─────────────────────────────────────────────────────
def _build_category_table(categories: dict, styles, t: dict, category_labels: dict | None = None):
    category_labels = category_labels or {}
    rows = [
        [
            Paragraph(f"<b>{t.get('category', 'Categoria')}</b>", styles["small"]),
            Paragraph(f"<b>{t.get('report_pdf_grade', 'Nota')}</b>", styles["small"]),
            "",
            Paragraph(f"<b>{t.get('report_pdf_rating', 'Avaliação')}</b>", styles["small"]),
        ]
    ]
    for key, val in categories.items():
        v = float(val)
        label = category_labels.get(key) or key.replace("_", " ").title()
        fg, _bg = _score_color(v)
        if v >= 7.5:
            rating = Paragraph(f"● {t.get('report_pdf_rating_strong', 'Forte')}", styles["tag_green"])
        elif v >= 5.0:
            rating = Paragraph(f"● {t.get('report_pdf_rating_moderate', 'Moderado')}", styles["tag_amber"])
        else:
            rating = Paragraph(f"● {t.get('report_pdf_rating_weak', 'Fraco')}", styles["tag_red"])
        rows.append([
            Paragraph(label, styles["body"]),
            Paragraph(f"{v:.1f}", styles["body"]),
            _mini_bar(v, fg),
            rating,
        ])

    avail_w = PAGE_W - 2 * MARGIN
    tbl = Table(rows, colWidths=[avail_w * 0.38, avail_w * 0.10, avail_w * 0.24, avail_w * 0.28])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), C_BLUE_LT),
        ("GRID",        (0, 0), (-1, -1), 0.4, C_BLUE_MD),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_SLATE_LT]),
        ("PADDING",     (0, 0), (-1, -1), 5),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",       (2, 1), (2, -1), "CENTER"),
    ]))
    return tbl


# ── Investor thesis table ────────────────────────────────────────────────────
def _build_investor_table(investor_pitch: dict, styles, t: dict):
    fields = [
        (t.get("report_pdf_investment_thesis", "Tese de Investimento"),   investor_pitch.get("investment_thesis", "N/A")),
        (t.get("report_pdf_funding_readiness", "Prontidão para Captação"), investor_pitch.get("funding_readiness", "N/A")),
        (t.get("suggested_ticket", "Ticket Sugerido"),         investor_pitch.get("suggested_ticket", "N/A")),
        (t.get("report_pdf_key_risks_investor", "Riscos para o Investidor"), investor_pitch.get("key_risks_for_investor", "N/A")),
        (t.get("report_pdf_expected_return_profile", "Perfil de Retorno Esperado"), investor_pitch.get("expected_return_profile", "N/A")),
    ]
    rows = []
    for label, value in fields:
        if not value or value == "N/A":
            continue
        rows.append([
            Paragraph(f"<b>{label}</b>", styles["small"]),
            Paragraph(str(value), styles["body"]),
        ])
    if not rows:
        return None

    avail_w = PAGE_W - 2 * MARGIN
    tbl = Table(rows, colWidths=[avail_w * 0.28, avail_w * 0.72])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), C_BLUE_LT),
        ("GRID",        (0, 0), (-1, -1), 0.4, C_BLUE_MD),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [C_WHITE, C_SLATE_LT]),
        ("PADDING",     (0, 0), (-1, -1), 6),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
    ]))
    return tbl


# ── Capital use / risk mitigation / investor fit cards ──────────────────────
def _build_extra_investor_cards(investor_pitch: dict, styles, t: dict):
    candidates = [
        (t.get("report_pdf_capital_use_plan", "Capital Use Plan"), investor_pitch.get("capital_use_plan") or [], C_BLUE_LT, C_BLUE),
        (t.get("report_pdf_risk_mitigation", "Risk Mitigation"), investor_pitch.get("risk_mitigation") or [], C_AMBER_LT, C_VIOLET),
        (t.get("report_pdf_investor_fit", "Investor Fit"), investor_pitch.get("investor_fit") or [], C_VIOLET_LT, C_VIOLET),
    ]
    cards = [c for c in candidates if c[1]]
    if not cards:
        return None

    avail_w = PAGE_W - 2 * MARGIN
    col_w = avail_w / len(cards)
    cells = []
    for title, items, _bg, accent in cards:
        flow = [Paragraph(f'<font color="#{_hexval(accent)}"><b>{title}</b></font>', styles["card_title"])]
        for item in items[:4]:
            flow.append(Paragraph(f"▸ {item}", styles["card_item"]))
        cells.append(flow)

    tbl = Table([cells], colWidths=[col_w] * len(cards))
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]
    for i, (_title, _items, bg, _accent) in enumerate(cards):
        style.append(("BACKGROUND", (i, 0), (i, 0), bg))
    if len(cards) > 1:
        style.append(("GRID", (0, 0), (-1, -1), 0.4, C_BORDER))
    tbl.setStyle(TableStyle(style))
    return tbl


# ── Strengths / risks side-by-side panel ─────────────────────────────────────
def _build_strengths_risks_panel(strengths: list, weaknesses: list, styles, t: dict):
    if not strengths and not weaknesses:
        return None

    avail_w = PAGE_W - 2 * MARGIN
    left = [Paragraph(f'<font color="#{_hexval(C_GREEN)}"><b>{t.get("strengths", "Pontos Fortes")}</b></font>', styles["card_title"])]
    for item in strengths:
        left.append(Paragraph(f"✔ {item}", styles["card_item"]))
    if not strengths:
        left.append(Paragraph("—", styles["card_item"]))

    right = [Paragraph(f'<font color="#{_hexval(C_RED)}"><b>{t.get("report_pdf_weaknesses", "Riscos e Pontos a Melhorar")}</b></font>', styles["card_title"])]
    for item in weaknesses:
        right.append(Paragraph(f"✘ {item}", styles["card_item"]))
    if not weaknesses:
        right.append(Paragraph("—", styles["card_item"]))

    tbl = Table([[left, right]], colWidths=[avail_w * 0.5, avail_w * 0.5])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), C_GREEN_LT),
        ("BACKGROUND", (1, 0), (1, 0), C_RED_LT),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("PADDING",    (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (1, 0), (1, 0), 14),
    ]))
    return tbl


# ── Highlighted "unique narrative angle" callout ─────────────────────────────
def _build_callout(kicker: str, text: str, accent, bg):
    style = ParagraphStyle("callout", fontSize=9, fontName=F_REG, textColor=C_NAVY, leading=14)
    body = Paragraph(f'<font color="#{_hexval(accent)}"><b>✦ {kicker}</b></font><br/>{text}', style)
    tbl = Table([[body]], colWidths=[PAGE_W - 2 * MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), bg),
        ("LINEBEFORE",  (0, 0), (0, 0), 3, accent),
        ("PADDING",     (0, 0), (-1, -1), 10),
    ]))
    return tbl


# ── Business Model Canvas (Pro tier) ─────────────────────────────────────────
_CANVAS_BLOCK_FILLS = {
    "key_partners": C_VIOLET_LT,
    "key_activities": C_BLUE_LT,
    "key_resources": C_BLUE_LT,
    "value_propositions": C_AMBER_LT,
    "customer_relationships": C_GREEN_LT,
    "channels": C_GREEN_LT,
    "customer_segments": C_VIOLET_LT,
    "cost_structure": C_SLATE_LT,
    "revenue_streams": C_SLATE_LT,
}
_CANVAS_BLOCK_ICONS = {
    "key_partners": "●",
    "key_activities": "▸",
    "value_propositions": "★",
    "key_resources": "■",
    "customer_relationships": "◆",
    "customer_segments": "▲",
    "channels": "▸",
    "cost_structure": "●",
    "revenue_streams": "★",
}


def _canvas_cell(key: str, block: dict, styles, max_items: int = 2):
    icon = _CANVAS_BLOCK_ICONS.get(key, "●")
    flow = [Paragraph(f'<font color="#{_hexval(C_VIOLET)}">{icon}</font> {block["title"]}', styles["canvas_block_title"])]
    for item in (block.get("items") or [])[:max_items]:
        flow.append(Paragraph(f"• {item}", styles["canvas_item"]))
    return flow


def _build_business_canvas(canvas: dict, styles):
    """
    Renders the 9 Business Model Canvas blocks as a plain 3x3 grid.
    Deliberately avoids ReportLab row-spanning: Platypus's automatic
    row-height calculation does not reliably account for cells that span
    multiple rows, which caused real overlapping/garbled text with the
    previous "classic diamond" layout. A uniform grid with no spans lets
    every row auto-size correctly to its tallest cell, with no overlap.
    """
    b = canvas["blocks"]
    avail_w = PAGE_W - 2 * MARGIN
    col_w = [avail_w / 3.0] * 3

    order = [
        ("key_partners", "key_activities", "value_propositions"),
        ("key_resources", "customer_relationships", "customer_segments"),
        ("channels", "cost_structure", "revenue_streams"),
    ]
    data = [[_canvas_cell(key, b[key], styles) for key in row] for row in order]

    table = Table(data, colWidths=col_w)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.6, C_VIOLET_MD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]
    for row_idx, row_keys in enumerate(order):
        for col_idx, key in enumerate(row_keys):
            style.append(("BACKGROUND", (col_idx, row_idx), (col_idx, row_idx), _CANVAS_BLOCK_FILLS[key]))
    table.setStyle(TableStyle(style))
    return table


# ── Cover / highlights ───────────────────────────────────────────────────────
def _build_highlight_lines(report: dict, t: dict) -> list:
    lines = []
    strengths = report.get("strengths") or []
    if strengths:
        lines.append(str(strengths[0]))

    category_scores = report.get("category_scores") or {}
    if category_scores:
        category_labels = report.get("category_labels") or {}
        top_key = max(category_scores, key=lambda k: category_scores[k])
        top_label = category_labels.get(top_key) or top_key.replace("_", " ").title()
        lines.append(f"{top_label}: {float(category_scores[top_key]):.1f}/10")

    investor_pitch = report.get("investor_pitch") or {}
    thesis = investor_pitch.get("investment_thesis")
    if thesis:
        lines.append(_truncate(str(thesis), 150))

    return lines[:3]


def _build_cover_page(analysis, styles, t: dict, report: dict):
    story = []
    metadata = analysis.metadata or {}
    startup_name = str(metadata.get("startup_name", "") or "").strip()
    industry = str(metadata.get("industry", "") or "").strip()
    score = float(analysis.success_score or 0)
    fg, bg = _score_color(score)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    avail_w = PAGE_W - 2 * MARGIN

    # Banner: kicker (real glyph tracking, see _tracked_label) + title, with the
    # platform logo docked to the right so every report carries the brand mark.
    kicker = _tracked_label(
        t.get("report_pdf_kicker_report", "AI-POWERED PITCH INTELLIGENCE"),
        F_BOLD, 7.5, C_KICKER, tracking=1.8,
    )
    title_style = ParagraphStyle("ch", fontName=F_BOLD, fontSize=17, textColor=C_WHITE, leading=20)
    title_p = Paragraph(t.get("report_pdf_cover_title", "StartupScan — Relatório de Avaliação de Pitch"), title_style)
    logo_img = _logo_flowable(26)
    if logo_img:
        header_t = Table(
            [[kicker, logo_img], [title_p, ""]],
            colWidths=[avail_w - 50, 50], rowHeights=[16, 38],
        )
    else:
        header_t = Table([[kicker], [title_p]], colWidths=[avail_w], rowHeights=[16, 38])
    header_style = [
        ("BACKGROUND", (0, 0), (-1, -1), C_NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
        ("TOPPADDING", (0, 1), (0, 1), 2),
        ("BOTTOMPADDING", (0, 1), (0, 1), 10),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",      (1, 0), (1, -1), "CENTER"),
        ("TOPPADDING",    (1, 0), (1, 1), 0),
        ("BOTTOMPADDING", (1, 0), (1, 1), 0),
    ]
    if logo_img:
        header_style.append(("SPAN", (1, 0), (1, 1)))
    header_t.setStyle(TableStyle(header_style))
    story.append(header_t)
    story.append(Spacer(1, 0.35 * cm))

    # Metadata line
    meta_parts = [f"<b>{t.get('report_pdf_analysis_number_prefix', 'Análise')} #{analysis.id}</b>"]
    if startup_name:
        meta_parts.append(f"{t.get('startup_label', 'Startup')}: <b>{startup_name}</b>")
    meta_parts.append(f"{t.get('generated_at', 'Gerado em')}: {now_str}")
    story.append(Paragraph("  |  ".join(meta_parts), styles["small"]))
    story.append(_hr(C_BLUE, thickness=1.2))
    story.append(Spacer(1, 0.3 * cm))

    # Score gauge + tag chips
    gauge = _build_score_gauge(score, fg, size=98)
    chips = [_pill(_score_tier_label(score, t), fg, bg)]
    if industry:
        chips.append(_pill(f"{t.get('report_pdf_industry_label', 'Setor')}: {industry}", C_NAVY, C_SLATE_LT))
    uniqueness_key = report.get("narrative_uniqueness_key")
    if uniqueness_key:
        chips.append(_pill(f"#{uniqueness_key}", C_VIOLET, C_VIOLET_LT))
    right_col = [_chip_row(chips)]
    combo = Table([[gauge, right_col]], colWidths=[avail_w * 0.24, avail_w * 0.76])
    combo.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, 0), 16),
    ]))
    story.append(combo)
    story.append(Spacer(1, 0.4 * cm))

    # Highlights box
    highlight_lines = _build_highlight_lines(report, t)
    if highlight_lines:
        flow = [Paragraph(f'<font color="#{_hexval(C_BLUE)}"><b>{t.get("report_pdf_snapshot_label", "Destaques")}</b></font>', styles["card_title"])]
        for line in highlight_lines:
            flow.append(Paragraph(f"▸ {line}", styles["card_item_lg"]))
        hl_tbl = Table([[flow]], colWidths=[avail_w])
        hl_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_SLATE_LT),
            ("LINEBEFORE", (0, 0), (0, 0), 3, C_BLUE),
            ("PADDING",    (0, 0), (-1, -1), 10),
        ]))
        story.append(hl_tbl)
        story.append(Spacer(1, 0.4 * cm))

    return story


# ── Main export ─────────────────────────────────────────────────────────────
def export_analysis_pdf(analysis, output_path: str, language: str = "en", include_business_canvas: bool = False):
    from startupscan_api.i18n import build_ui_text

    t = build_ui_text(language)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    styles = _build_styles()
    story = []

    report = analysis.report or {}
    metadata = analysis.metadata or {}

    # The local engine's narrative is a deterministic function of
    # (score, metadata) plus language, so a report generated in one
    # language can be safely and losslessly regenerated in another at
    # export time — this avoids ever mixing the (translated) PDF chrome
    # with a stale, differently-languaged stored narrative.
    if report.get("status") == "local_report" and report.get("language") != language:
        from startupscan_api.utils.report import generate_interpretable_report
        report = generate_interpretable_report(analysis.success_score, metadata, language=language)

    category_scores = report.get("category_scores", {})
    category_labels = report.get("category_labels", {})
    startup_name = str(metadata.get("startup_name", "") or "").strip() or t.get("startup_label", "Startup")

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.extend(_build_cover_page(analysis, styles, t, report))

    # ── Financial KPIs ────────────────────────────────────────────────────────
    story.append(Paragraph(f"<b>{t.get('financial_indicators', 'Indicadores Financeiros')}</b>", styles["section_h"]))
    story.append(_build_kpi_table(analysis, styles, t))
    story.append(Paragraph(
        t.get("report_pdf_financial_indicators_caption",
              "Principais sinais financeiros informados na submissão do pitch, utilizados como entradas diretas do modelo de pontuação."),
        styles["caption"],
    ))
    story.append(Spacer(1, 0.3 * cm))

    # ── Executive summary ─────────────────────────────────────────────────────
    story.append(_hr())
    story.append(Paragraph(f"<b>{t.get('executive_summary', 'Resumo Executivo')}</b>", styles["section_h"]))
    summary = report.get("summary", t.get("report_pdf_summary_unavailable", "Resumo não disponível."))
    for para in str(summary).split("\n\n"):
        para = para.strip()
        if para:
            story.append(Paragraph(para, styles["body"]))
    story.append(Spacer(1, 0.4 * cm))

    # ── Market opportunity ────────────────────────────────────────────────────
    market_opp = report.get("market_opportunity", "")
    if market_opp:
        story.append(_hr())
        story.append(Paragraph(f"<b>{t.get('report_pdf_market_opportunity', 'Oportunidade de Mercado')}</b>", styles["section_h"]))
        story.append(Paragraph(str(market_opp), styles["body"]))
        story.append(Spacer(1, 0.3 * cm))

    # ── Competitive positioning ───────────────────────────────────────────────
    comp_pos = report.get("competitive_position", "")
    if comp_pos:
        story.append(Paragraph(f"<b>{t.get('report_pdf_competitive_position', 'Posicionamento Competitivo')}</b>", styles["section_h"]))
        story.append(Paragraph(str(comp_pos), styles["body"]))
        story.append(Spacer(1, 0.3 * cm))

    # ── Category assessment ───────────────────────────────────────────────────
    if category_scores:
        story.append(_hr())
        story.append(Paragraph(f"<b>{t.get('report_pdf_category_assessment', 'Avaliação Detalhada por Categoria')}</b>", styles["section_h"]))
        story.append(Paragraph(
            t.get("report_pdf_category_assessment_intro",
                  "Cada dimensão abaixo é avaliada numa escala de 0 a 10, combinando sinais quantitativos com a estrutura qualitativa do pitch."),
            styles["caption"],
        ))
        story.append(_build_category_table(category_scores, styles, t, category_labels))
        story.append(Spacer(1, 0.35 * cm))
        story.append(_build_category_chart(category_scores, t, category_labels))
        story.append(Spacer(1, 0.4 * cm))

    # ── Strengths / risks / recommendations ──────────────────────────────────
    strengths = report.get("strengths", [])
    weaknesses = report.get("weaknesses", [])
    recommendations = report.get("recommendations", [])
    narrative_key = report.get("narrative_uniqueness_key")

    if strengths or weaknesses or recommendations:
        story.append(_hr())
        story.append(Paragraph(f"<b>{t.get('report_pdf_qualitative_analysis', 'Análise Qualitativa')}</b>", styles["section_h"]))

    panel = _build_strengths_risks_panel(strengths, weaknesses, styles, t)
    if panel:
        story.append(panel)
        story.append(Spacer(1, 0.35 * cm))

    remaining_recommendations = recommendations
    if narrative_key and recommendations:
        story.append(_build_callout(
            t.get("report_pdf_narrative_signature_label", "Ângulo Narrativo Único"),
            str(recommendations[0]), C_BLUE, C_BLUE_LT,
        ))
        story.append(Spacer(1, 0.3 * cm))
        remaining_recommendations = recommendations[1:]

    if remaining_recommendations:
        story.append(Paragraph(f"<b>{t.get('report_pdf_recommendations', 'Recomendações Acionáveis')}</b>", styles["sub_h"]))
        for i, item in enumerate(remaining_recommendations, 1):
            story.append(Paragraph(f"{i}. {item}", styles["bullet"]))
        story.append(Spacer(1, 0.4 * cm))

    # ── Investor thesis ───────────────────────────────────────────────────────
    investor_pitch = report.get("investor_pitch", {})
    if investor_pitch:
        story.append(_hr(C_BLUE, 0.8))
        story.append(Paragraph(f"<b>{t.get('report_pdf_investor_perspective', 'Perspectiva para Investidores')}</b>", styles["section_h"]))

        thesis = investor_pitch.get("investment_thesis", "")
        if thesis:
            story.append(Paragraph(f"<b>{t.get('report_pdf_investment_thesis', 'Tese de Investimento')}</b>", styles["sub_h"]))
            story.append(Paragraph(str(thesis), styles["body"]))
            story.append(Spacer(1, 0.3 * cm))

        inv_table = _build_investor_table(investor_pitch, styles, t)
        if inv_table:
            story.append(inv_table)
            story.append(Spacer(1, 0.35 * cm))

        extra_cards = _build_extra_investor_cards(investor_pitch, styles, t)
        if extra_cards:
            story.append(extra_cards)
            story.append(Spacer(1, 0.4 * cm))

    # ── Legacy (fallback: old investor_pitch without rich fields) ────────────
    elif report.get("investor_pitch") and isinstance(report["investor_pitch"], dict):
        old = report["investor_pitch"]
        if old.get("investment_thesis"):
            story.append(Paragraph(f"<b>{t.get('report_pdf_investor_thesis_legacy', 'Tese para Investidores')}</b>", styles["section_h"]))
            story.append(Paragraph(old.get("investment_thesis", ""), styles["body"]))
            story.append(Paragraph(f"<b>{t.get('readiness_label', 'Prontidão')}:</b> {old.get('funding_readiness', 'N/A')}", styles["body"]))
            story.append(Paragraph(f"<b>{t.get('suggested_ticket', 'Ticket sugerido')}:</b> {old.get('suggested_ticket', 'N/A')}", styles["body"]))

    # ── Business Model Canvas (Pro tier only) ─────────────────────────────────
    if include_business_canvas:
        from startupscan_api.utils.business_canvas import generate_business_model_canvas
        canvas = generate_business_model_canvas(analysis, language=language)
        story.append(PageBreak())
        story.append(Paragraph(
            f'<font color="#{_hexval(C_VIOLET)}">★</font> '
            f"<b>{canvas['section_title']}</b> "
            f'<font size="7" color="#{_hexval(C_VIOLET)}">PRO</font>',
            styles["section_h"],
        ))
        story.append(_hr(C_VIOLET, 0.8))
        story.append(Paragraph(canvas["intro"], styles["canvas_intro"]))
        story.append(_build_business_canvas(canvas, styles))
        story.append(Spacer(1, 0.4 * cm))

    # ── Metadata footer ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(_hr())
    engine_used = metadata.get("analysis_engine_used", "local")
    engine_req  = metadata.get("analysis_engine_requested", "local")
    story.append(
        Paragraph(
            f"{t.get('report_pdf_engine_used', 'Motor utilizado')}: <b>{engine_used}</b> | "
            f"{t.get('report_pdf_engine_requested', 'Solicitado')}: {engine_req} | "
            f"{t.get('startup_label', 'Startup')}: {startup_name} | "
            f"{t.get('generated_at', 'Gerado em')}: {datetime.now().strftime('%d/%m/%Y %H:%M')} | StartupScanAI",
            styles["footer"],
        )
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN + 0.35 * cm,
        bottomMargin=MARGIN + 0.6 * cm,
    )
    startup_short = (startup_name or "StartupScan")[:40]

    def _decorate_page(canvas_obj, doc_obj):
        canvas_obj.saveState()
        # Top accent strip
        canvas_obj.setFillColor(C_BLUE)
        canvas_obj.rect(0, PAGE_H - 0.14 * cm, PAGE_W, 0.14 * cm, stroke=0, fill=1)
        # Running footer
        canvas_obj.setStrokeColor(C_BORDER)
        canvas_obj.setLineWidth(0.4)
        canvas_obj.line(MARGIN, MARGIN * 0.55, PAGE_W - MARGIN, MARGIN * 0.55)
        canvas_obj.setFont(F_REG, 7.5)
        canvas_obj.setFillColor(C_SLATE)
        canvas_obj.drawString(MARGIN, MARGIN * 0.32, f"StartupScanAI  •  {startup_short}")
        canvas_obj.drawRightString(
            PAGE_W - MARGIN, MARGIN * 0.32,
            f"{t.get('report_pdf_page_label', 'Page')} {doc_obj.page}",
        )
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=_decorate_page, onLaterPages=_decorate_page)
    return output_path

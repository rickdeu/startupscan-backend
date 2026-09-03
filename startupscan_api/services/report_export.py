import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Color palette ───────────────────────────────────────────────────────────
C_NAVY    = colors.HexColor("#0f172a")
C_BLUE    = colors.HexColor("#2563eb")
C_BLUE_LT = colors.HexColor("#dbeafe")
C_BLUE_MD = colors.HexColor("#bfdbfe")
C_SLATE   = colors.HexColor("#475569")
C_SLATE_LT = colors.HexColor("#f8fafc")
C_BORDER  = colors.HexColor("#e2e8f0")
C_GREEN   = colors.HexColor("#16a34a")
C_GREEN_LT = colors.HexColor("#dcfce7")
C_RED     = colors.HexColor("#dc2626")
C_RED_LT  = colors.HexColor("#fee2e2")
C_AMBER   = colors.HexColor("#d97706")
C_AMBER_LT = colors.HexColor("#fef3c7")
C_VIOLET  = colors.HexColor("#7c3aed")
C_VIOLET_LT = colors.HexColor("#ede9fe")
C_VIOLET_MD = colors.HexColor("#c4b5fd")
C_WHITE   = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm


# ── Styles ───────────────────────────────────────────────────────────────────
def _build_styles():
    base = getSampleStyleSheet()

    def s(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "cover_title": s("cover_title", fontSize=26, textColor=C_WHITE,
                         fontName="Helvetica-Bold", leading=32, spaceAfter=6),
        "cover_sub":   s("cover_sub",   fontSize=13, textColor=colors.HexColor("#cbd5e1"),
                         leading=18, spaceAfter=4),
        "cover_meta":  s("cover_meta",  fontSize=9,  textColor=colors.HexColor("#94a3b8"),
                         leading=14),
        "section_h":   s("section_h",   fontSize=13, textColor=C_NAVY,
                         fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6),
        "sub_h":       s("sub_h",       fontSize=10, textColor=C_BLUE,
                         fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4),
        "body":        s("body",        fontSize=9,  textColor=C_NAVY,
                         leading=14, spaceAfter=4),
        "bullet":      s("bullet",      fontSize=9,  textColor=C_NAVY,
                         leading=14, leftIndent=12, spaceAfter=3),
        "small":       s("small",       fontSize=8,  textColor=C_SLATE,
                         leading=12),
        "score_big":   s("score_big",   fontSize=36, textColor=C_BLUE,
                         fontName="Helvetica-Bold", alignment=TA_CENTER),
        "label_center": s("label_center", fontSize=8, textColor=C_SLATE,
                          alignment=TA_CENTER),
        "kpi_value":   s("kpi_value",   fontSize=16, textColor=C_NAVY,
                         fontName="Helvetica-Bold", alignment=TA_CENTER),
        "kpi_label":   s("kpi_label",   fontSize=7,  textColor=C_SLATE,
                         alignment=TA_CENTER),
        "tag_green":   s("tag_green",   fontSize=8,  textColor=C_GREEN,
                         fontName="Helvetica-Bold"),
        "tag_amber":   s("tag_amber",   fontSize=8,  textColor=C_AMBER,
                         fontName="Helvetica-Bold"),
        "tag_red":     s("tag_red",     fontSize=8,  textColor=C_RED,
                         fontName="Helvetica-Bold"),
        "footer":      s("footer",      fontSize=7,  textColor=C_SLATE,
                         alignment=TA_CENTER),
        "canvas_block_title": s("canvas_block_title", fontSize=8.5, textColor=C_VIOLET,
                                fontName="Helvetica-Bold", leading=11, spaceAfter=3),
        "canvas_item": s("canvas_item", fontSize=7.3, textColor=C_NAVY,
                         leading=10, spaceAfter=2),
        "canvas_intro": s("canvas_intro", fontSize=9, textColor=C_SLATE,
                          leading=13, spaceAfter=8, fontName="Helvetica-Oblique"),
        "pro_badge": s("pro_badge", fontSize=7, textColor=C_WHITE,
                       fontName="Helvetica-Bold", alignment=TA_CENTER),
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


def _readiness_style(text: str, styles):
    t = (text or "").lower()
    if "strong" in t:
        return styles["tag_green"]
    if "ready" in t:
        return styles["tag_amber"]
    return styles["tag_red"]


# ── Native bar chart ─────────────────────────────────────────────────────────
def _build_category_chart(categories: dict, t: dict, category_labels: dict | None = None):
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing, String

    category_labels = category_labels or {}
    labels = [category_labels.get(k) or k.replace("_", " ").title() for k in categories.keys()]
    values = [[float(v) for v in categories.values()]]

    d = Drawing(460, 190)
    chart = VerticalBarChart()
    chart.x = 60
    chart.y = 40
    chart.width = 380
    chart.height = 130
    chart.data = values
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.angle = 28
    chart.categoryAxis.labels.dy = -14
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 10
    chart.valueAxis.valueStep = 2
    chart.bars[0].fillColor = C_BLUE
    chart.bars[0].strokeColor = colors.HexColor("#1d4ed8")
    chart.bars[0].strokeWidth = 0.4

    title = String(230, 184, t.get("report_pdf_category_score_chart_title", "Pontuação por Categoria (0–10)"),
                   textAnchor="middle", fontSize=8.5, fillColor=C_NAVY)
    d.add(chart)
    d.add(title)
    return d


# ── Financial KPI table ──────────────────────────────────────────────────────
def _build_kpi_table(analysis, styles, t: dict):
    score = float(analysis.success_score or 0)
    fg, bg = _score_color(score)

    kpi_data = [
        [
            Paragraph(f"{score:.1f}/10", styles["kpi_value"]),
            Paragraph(f"AOA {float(analysis.revenue or 0):,.0f}", styles["kpi_value"]),
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
    t = Table(kpi_data, colWidths=[col_w] * 4, rowHeights=[28, 16])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, 0), bg),
        ("BACKGROUND",  (1, 0), (-1, 0), C_SLATE_LT),
        ("BACKGROUND",  (0, 1), (-1, 1), C_BORDER),
        ("GRID",        (0, 0), (-1, -1), 0.4, C_BORDER),
        ("ROUNDEDCORNERS", [4]),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ── Category score table ─────────────────────────────────────────────────────
def _build_category_table(categories: dict, styles, t: dict, category_labels: dict | None = None):
    category_labels = category_labels or {}
    rows = [
        [
            Paragraph(f"<b>{t.get('category', 'Categoria')}</b>", styles["small"]),
            Paragraph(f"<b>{t.get('report_pdf_grade', 'Nota')}</b>", styles["small"]),
            Paragraph(f"<b>{t.get('report_pdf_rating', 'Avaliação')}</b>", styles["small"]),
        ]
    ]
    for key, val in categories.items():
        v = float(val)
        label = category_labels.get(key) or key.replace("_", " ").title()
        if v >= 7.5:
            rating = Paragraph(f"● {t.get('report_pdf_rating_strong', 'Forte')}", styles["tag_green"])
        elif v >= 5.0:
            rating = Paragraph(f"● {t.get('report_pdf_rating_moderate', 'Moderado')}", styles["tag_amber"])
        else:
            rating = Paragraph(f"● {t.get('report_pdf_rating_weak', 'Fraco')}", styles["tag_red"])
        rows.append([
            Paragraph(label, styles["body"]),
            Paragraph(f"{v:.1f}", styles["body"]),
            rating,
        ])

    avail_w = PAGE_W - 2 * MARGIN
    t = Table(rows, colWidths=[avail_w * 0.55, avail_w * 0.12, avail_w * 0.33])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), C_BLUE_LT),
        ("GRID",        (0, 0), (-1, -1), 0.4, C_BLUE_MD),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_SLATE_LT]),
        ("PADDING",     (0, 0), (-1, -1), 5),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


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
    t = Table(rows, colWidths=[avail_w * 0.28, avail_w * 0.72])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), C_BLUE_LT),
        ("GRID",        (0, 0), (-1, -1), 0.4, C_BLUE_MD),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [C_WHITE, C_SLATE_LT]),
        ("PADDING",     (0, 0), (-1, -1), 6),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
    ]))
    return t


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


def _canvas_cell(block: dict, styles, max_items: int = 2):
    flow = [Paragraph(block["title"], styles["canvas_block_title"])]
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
    data = [[_canvas_cell(b[key], styles) for key in row] for row in order]

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


# ── Section with colored bullet list ─────────────────────────────────────────
def _bullet_section(title: str, items: list, story, styles,
                    bullet_char="▸", color=C_NAVY):
    if not items:
        return
    story.append(Paragraph(f"<b>{title}</b>", styles["sub_h"]))
    for item in items:
        txt = str(item).strip()
        if not txt:
            continue
        story.append(
            Paragraph(f'<font color="#{color.hexval()[2:] if hasattr(color, "hexval") else "0f172a"}">{bullet_char}</font> {txt}',
                      styles["bullet"])
        )
    story.append(Spacer(1, 0.2 * cm))


def _bullet_section_simple(title: str, items: list, story, styles, prefix="●"):
    if not items:
        return
    story.append(Paragraph(f"<b>{title}</b>", styles["sub_h"]))
    for item in items:
        txt = str(item).strip()
        if not txt:
            continue
        story.append(Paragraph(f"{prefix} {txt}", styles["bullet"]))
    story.append(Spacer(1, 0.2 * cm))


# ── Inline cover (no canvas) ────────────────────────────────────────────────
def _build_cover_block(analysis, styles, t: dict):
    story = []
    startup_name = (analysis.metadata or {}).get("startup_name", "") if analysis.metadata else ""
    score = float(analysis.success_score or 0)
    fg, bg = _score_color(score)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Blue header rendered as a background table
    header_data = [[
        Paragraph(
            f"<b>{t.get('report_pdf_cover_title', 'StartupScan — Relatório de Avaliação de Pitch')}</b>",
            ParagraphStyle("ch", fontSize=16, textColor=C_WHITE,
                           fontName="Helvetica-Bold", leading=22),
        )
    ]]
    avail_w = PAGE_W - 2 * MARGIN
    header_t = Table(header_data, colWidths=[avail_w], rowHeights=[48])
    header_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
        ("PADDING",       (0, 0), (-1, -1), 14),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header_t)
    story.append(Spacer(1, 0.4 * cm))

    # Metadata line
    meta_parts = [f"<b>{t.get('report_pdf_analysis_number_prefix', 'Análise')} #{analysis.id}</b>"]
    if startup_name:
        meta_parts.append(f"{t.get('startup_label', 'Startup')}: <b>{startup_name}</b>")
    meta_parts.append(f"{t.get('generated_at', 'Gerado em')}: {now_str}")
    story.append(Paragraph("  |  ".join(meta_parts), styles["small"]))
    story.append(_hr(C_BLUE, thickness=1.2))
    story.append(Spacer(1, 0.3 * cm))

    # Highlighted score
    score_label = (
        t.get("report_pdf_score_excellent", "Excelente") if score >= 8
        else (t.get("report_pdf_score_good", "Bom") if score >= 6.5
        else (t.get("report_pdf_score_regular", "Regular") if score >= 5
        else t.get("report_pdf_rating_weak", "Fraco"))))
    score_data = [[
        Paragraph(f"{score:.1f}", ParagraphStyle("sv", fontSize=40, textColor=fg,
                                                  fontName="Helvetica-Bold", alignment=TA_CENTER)),
        Paragraph(f"<b>/ 10</b><br/>{score_label}",
                  ParagraphStyle("sl", fontSize=12, textColor=C_SLATE,
                                  leading=18, alignment=TA_LEFT)),
    ]]
    score_t = Table(score_data, colWidths=[avail_w * 0.20, avail_w * 0.80], rowHeights=[52])
    score_t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), bg),
        ("PADDING",     (0, 0), (-1, -1), 10),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",        (0, 0), (-1, -1), 0, C_WHITE),
    ]))
    story.append(score_t)
    story.append(Spacer(1, 0.5 * cm))
    return story


# ── Main export ─────────────────────────────────────────────────────────────
def export_analysis_pdf(analysis, output_path: str, language: str = "en", include_business_canvas: bool = False):
    from startupscan_api.i18n import build_ui_text

    t = build_ui_text(language)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    styles = _build_styles()
    story = []

    # ── Cover / header ────────────────────────────────────────────────────────
    story.extend(_build_cover_block(analysis, styles, t))

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

    # ── Financial KPIs ────────────────────────────────────────────────────────
    story.append(Paragraph(f"<b>{t.get('financial_indicators', 'Indicadores Financeiros')}</b>", styles["section_h"]))
    story.append(_build_kpi_table(analysis, styles, t))
    story.append(Spacer(1, 0.5 * cm))

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
        story.append(PageBreak())
        story.append(Paragraph(f"<b>{t.get('report_pdf_category_assessment', 'Avaliação Detalhada por Categoria')}</b>", styles["section_h"]))
        story.append(_build_category_table(category_scores, styles, t, category_labels))
        story.append(Spacer(1, 0.4 * cm))
        story.append(_build_category_chart(category_scores, t, category_labels))
        story.append(Spacer(1, 0.5 * cm))

    # ── Strengths ─────────────────────────────────────────────────────────────
    strengths = report.get("strengths", [])
    weaknesses = report.get("weaknesses", [])
    recommendations = report.get("recommendations", [])

    if strengths or weaknesses or recommendations:
        story.append(_hr())
        story.append(Paragraph(f"<b>{t.get('report_pdf_qualitative_analysis', 'Análise Qualitativa')}</b>", styles["section_h"]))

    if strengths:
        story.append(Paragraph(f"<b>{t.get('strengths', 'Pontos Fortes')}</b>", styles["sub_h"]))
        for item in strengths:
            story.append(Paragraph(f"✔ {item}", styles["bullet"]))
        story.append(Spacer(1, 0.3 * cm))

    if weaknesses:
        story.append(Paragraph(f"<b>{t.get('report_pdf_weaknesses', 'Riscos e Pontos a Melhorar')}</b>", styles["sub_h"]))
        for item in weaknesses:
            story.append(Paragraph(f"✘ {item}", styles["bullet"]))
        story.append(Spacer(1, 0.3 * cm))

    if recommendations:
        story.append(Paragraph(f"<b>{t.get('report_pdf_recommendations', 'Recomendações Acionáveis')}</b>", styles["sub_h"]))
        for i, item in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {item}", styles["bullet"]))
        story.append(Spacer(1, 0.4 * cm))

    # ── Investor thesis ───────────────────────────────────────────────────────
    investor_pitch = report.get("investor_pitch", {})
    if investor_pitch:
        story.append(PageBreak())
        story.append(Paragraph(f"<b>{t.get('report_pdf_investor_perspective', 'Perspectiva para Investidores')}</b>", styles["section_h"]))
        story.append(_hr(C_BLUE, 0.8))

        thesis = investor_pitch.get("investment_thesis", "")
        if thesis:
            story.append(Paragraph(f"<b>{t.get('report_pdf_investment_thesis', 'Tese de Investimento')}</b>", styles["sub_h"]))
            story.append(Paragraph(str(thesis), styles["body"]))
            story.append(Spacer(1, 0.3 * cm))

        inv_table = _build_investor_table(investor_pitch, styles, t)
        if inv_table:
            story.append(inv_table)
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
            f'<font color="#{C_VIOLET.hexval()[2:]}">★</font> '
            f"<b>{canvas['section_title']}</b> "
            f'<font size="7" color="#{C_VIOLET.hexval()[2:]}">PRO</font>',
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
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(C_SLATE)
        canvas_obj.drawString(MARGIN, MARGIN * 0.32, f"StartupScanAI  •  {startup_short}")
        canvas_obj.drawRightString(
            PAGE_W - MARGIN, MARGIN * 0.32,
            f"{t.get('report_pdf_page_label', 'Page')} {doc_obj.page}",
        )
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=_decorate_page, onLaterPages=_decorate_page)
    return output_path

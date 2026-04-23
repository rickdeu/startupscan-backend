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

# ── Paleta de cores ──────────────────────────────────────────────────────────
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
C_WHITE   = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm


# ── Estilos ──────────────────────────────────────────────────────────────────
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


# ── Gráfico de barras nativo ─────────────────────────────────────────────────
def _build_category_chart(categories: dict):
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing, String

    labels = [k.replace("_", " ").title() for k in categories.keys()]
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

    title = String(230, 184, "Pontuação por Categoria (0–10)",
                   textAnchor="middle", fontSize=8.5, fillColor=C_NAVY)
    d.add(chart)
    d.add(title)
    return d


# ── Tabela de KPIs financeiros ───────────────────────────────────────────────
def _build_kpi_table(analysis, styles):
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
            Paragraph("Score Final", styles["kpi_label"]),
            Paragraph("Receita", styles["kpi_label"]),
            Paragraph("Crescimento", styles["kpi_label"]),
            Paragraph("Margem de Lucro", styles["kpi_label"]),
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


# ── Tabela de notas por categoria ────────────────────────────────────────────
def _build_category_table(categories: dict, styles):
    rows = [
        [
            Paragraph("<b>Categoria</b>", styles["small"]),
            Paragraph("<b>Nota</b>", styles["small"]),
            Paragraph("<b>Avaliação</b>", styles["small"]),
        ]
    ]
    for key, val in categories.items():
        v = float(val)
        label = key.replace("_", " ").title()
        if v >= 7.5:
            rating = Paragraph("● Forte", styles["tag_green"])
        elif v >= 5.0:
            rating = Paragraph("● Moderado", styles["tag_amber"])
        else:
            rating = Paragraph("● Fraco", styles["tag_red"])
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


# ── Tabela de tese para investidores ─────────────────────────────────────────
def _build_investor_table(investor_pitch: dict, styles):
    fields = [
        ("Tese de Investimento",   investor_pitch.get("investment_thesis", "N/A")),
        ("Prontidão para Captação", investor_pitch.get("funding_readiness", "N/A")),
        ("Ticket Sugerido",         investor_pitch.get("suggested_ticket", "N/A")),
        ("Riscos para o Investidor", investor_pitch.get("key_risks_for_investor", "N/A")),
        ("Perfil de Retorno Esperado", investor_pitch.get("expected_return_profile", "N/A")),
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


# ── Seção com lista de bullets coloridos ─────────────────────────────────────
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


# ── Cover inline (sem canvas) ─────────────────────────────────────────────────
def _build_cover_block(analysis, styles):
    story = []
    startup_name = (analysis.metadata or {}).get("startup_name", "") if analysis.metadata else ""
    score = float(analysis.success_score or 0)
    fg, bg = _score_color(score)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Cabeçalho azul como tabela de fundo
    header_data = [[
        Paragraph(
            f"<b>{'StartupScan — Relatório de Avaliação de Pitch'}</b>",
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

    # Linha de meta-dados
    meta_parts = [f"<b>Análise #{analysis.id}</b>"]
    if startup_name:
        meta_parts.append(f"Startup: <b>{startup_name}</b>")
    meta_parts.append(f"Gerado em: {now_str}")
    story.append(Paragraph("  |  ".join(meta_parts), styles["small"]))
    story.append(_hr(C_BLUE, thickness=1.2))
    story.append(Spacer(1, 0.3 * cm))

    # Score destaque
    score_label = "Excelente" if score >= 8 else ("Bom" if score >= 6.5 else ("Regular" if score >= 5 else "Fraco"))
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


# ── Exportação principal ──────────────────────────────────────────────────────
def export_analysis_pdf(analysis, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    styles = _build_styles()
    story = []

    # ── Capa / cabeçalho ─────────────────────────────────────────────────────
    story.extend(_build_cover_block(analysis, styles))

    report = analysis.report or {}
    metadata = analysis.metadata or {}
    category_scores = report.get("category_scores", {})
    startup_name = str(metadata.get("startup_name", "") or "").strip() or "Startup"

    # ── KPIs financeiros ─────────────────────────────────────────────────────
    story.append(Paragraph("<b>Indicadores Financeiros</b>", styles["section_h"]))
    story.append(_build_kpi_table(analysis, styles))
    story.append(Spacer(1, 0.5 * cm))

    # ── Resumo executivo ─────────────────────────────────────────────────────
    story.append(_hr())
    story.append(Paragraph("<b>Resumo Executivo</b>", styles["section_h"]))
    summary = report.get("summary", "Resumo não disponível.")
    for para in str(summary).split("\n\n"):
        para = para.strip()
        if para:
            story.append(Paragraph(para, styles["body"]))
    story.append(Spacer(1, 0.4 * cm))

    # ── Oportunidade de mercado ───────────────────────────────────────────────
    market_opp = report.get("market_opportunity", "")
    if market_opp:
        story.append(_hr())
        story.append(Paragraph("<b>Oportunidade de Mercado</b>", styles["section_h"]))
        story.append(Paragraph(str(market_opp), styles["body"]))
        story.append(Spacer(1, 0.3 * cm))

    # ── Posicionamento competitivo ────────────────────────────────────────────
    comp_pos = report.get("competitive_position", "")
    if comp_pos:
        story.append(Paragraph("<b>Posicionamento Competitivo</b>", styles["section_h"]))
        story.append(Paragraph(str(comp_pos), styles["body"]))
        story.append(Spacer(1, 0.3 * cm))

    # ── Avaliação por categoria ───────────────────────────────────────────────
    if category_scores:
        story.append(PageBreak())
        story.append(Paragraph("<b>Avaliação Detalhada por Categoria</b>", styles["section_h"]))
        story.append(_build_category_table(category_scores, styles))
        story.append(Spacer(1, 0.4 * cm))
        story.append(_build_category_chart(category_scores))
        story.append(Spacer(1, 0.5 * cm))

    # ── Pontos fortes ────────────────────────────────────────────────────────
    strengths = report.get("strengths", [])
    weaknesses = report.get("weaknesses", [])
    recommendations = report.get("recommendations", [])

    if strengths or weaknesses or recommendations:
        story.append(_hr())
        story.append(Paragraph("<b>Análise Qualitativa</b>", styles["section_h"]))

    if strengths:
        story.append(Paragraph("<b>Pontos Fortes</b>", styles["sub_h"]))
        for item in strengths:
            story.append(Paragraph(f"✔ {item}", styles["bullet"]))
        story.append(Spacer(1, 0.3 * cm))

    if weaknesses:
        story.append(Paragraph("<b>Riscos e Pontos a Melhorar</b>", styles["sub_h"]))
        for item in weaknesses:
            story.append(Paragraph(f"✘ {item}", styles["bullet"]))
        story.append(Spacer(1, 0.3 * cm))

    if recommendations:
        story.append(Paragraph("<b>Recomendações Acionáveis</b>", styles["sub_h"]))
        for i, item in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {item}", styles["bullet"]))
        story.append(Spacer(1, 0.4 * cm))

    # ── Tese para investidores ────────────────────────────────────────────────
    investor_pitch = report.get("investor_pitch", {})
    if investor_pitch:
        story.append(PageBreak())
        story.append(Paragraph("<b>Perspectiva para Investidores</b>", styles["section_h"]))
        story.append(_hr(C_BLUE, 0.8))

        thesis = investor_pitch.get("investment_thesis", "")
        if thesis:
            story.append(Paragraph("<b>Tese de Investimento</b>", styles["sub_h"]))
            story.append(Paragraph(str(thesis), styles["body"]))
            story.append(Spacer(1, 0.3 * cm))

        inv_table = _build_investor_table(investor_pitch, styles)
        if inv_table:
            story.append(inv_table)
            story.append(Spacer(1, 0.4 * cm))

    # ── Legado (fallback: investor_pitch antigo sem campos ricos) ────────────
    elif report.get("investor_pitch") and isinstance(report["investor_pitch"], dict):
        old = report["investor_pitch"]
        if old.get("investment_thesis"):
            story.append(Paragraph("<b>Tese para Investidores</b>", styles["section_h"]))
            story.append(Paragraph(old.get("investment_thesis", ""), styles["body"]))
            story.append(Paragraph(f"<b>Prontidão:</b> {old.get('funding_readiness', 'N/A')}", styles["body"]))
            story.append(Paragraph(f"<b>Ticket sugerido:</b> {old.get('suggested_ticket', 'N/A')}", styles["body"]))

    # ── Rodapé de metadados ───────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(_hr())
    engine_used = metadata.get("analysis_engine_used", "local")
    engine_req  = metadata.get("analysis_engine_requested", "local")
    story.append(
        Paragraph(
            f"Motor utilizado: <b>{engine_used}</b> | Solicitado: {engine_req} | "
            f"Startup: {startup_name} | "
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')} | StartupScan.AI",
            styles["footer"],
        )
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    doc.build(story)
    return output_path

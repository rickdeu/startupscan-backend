import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _build_category_chart_native(categories: dict):
    """Returns a ReportLab Drawing — no matplotlib required."""
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing, String

    labels = [k.replace("_", " ").title() for k in categories.keys()]
    values = [[float(v) for v in categories.values()]]

    d = Drawing(420, 170)
    chart = VerticalBarChart()
    chart.x = 55
    chart.y = 30
    chart.width = 340
    chart.height = 120
    chart.data = values
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.dy = -12
    chart.categoryAxis.labels.fontSize = 7.5
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 10
    chart.valueAxis.valueStep = 2
    chart.bars[0].fillColor = colors.HexColor("#2563eb")
    chart.bars[0].strokeColor = colors.HexColor("#1d4ed8")
    chart.bars[0].strokeWidth = 0.5

    title = String(210, 162, "Pontuação por categoria", textAnchor="middle",
                   fontSize=9, fillColor=colors.HexColor("#0f172a"))
    d.add(chart)
    d.add(title)
    return d


def export_analysis_pdf(analysis, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )

    story = []
    story.append(Paragraph("Relatório de Avaliação de Pitch", title_style))
    story.append(
        Paragraph(
            f"Startup #{analysis.id} | Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            subtitle_style,
        )
    )

    report = analysis.report or {}
    metadata = analysis.metadata or {}
    category_scores = report.get("category_scores", {})

    summary = report.get("summary", "Resumo não disponível.")
    story.append(Paragraph("<b>Resumo Executivo</b>", styles["Heading3"]))
    story.append(Paragraph(summary, styles["BodyText"]))
    story.append(Spacer(1, 0.4 * cm))

    kpi_table = Table(
        [
            ["Score Final", f"{float(analysis.success_score or 0):.1f}/10"],
            ["Receita", f"AOA {float(analysis.revenue or 0):,.2f}"],
            ["Crescimento", f"{float(analysis.growth_rate or 0):.2f}%"],
            ["Margem", f"{float(analysis.profit_margin or 0):.2f}%"],
        ],
        colWidths=[6 * cm, 8 * cm],
    )
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 0.5 * cm))

    if category_scores:
        story.append(Paragraph("<b>Avaliação por Categoria</b>", styles["Heading3"]))
        cat_table_data = [["Categoria", "Nota (0-10)"]]
        for key, val in category_scores.items():
            cat_table_data.append([key.replace("_", " ").title(), f"{float(val):.1f}"])
        cat_table = Table(cat_table_data, colWidths=[9 * cm, 5 * cm])
        cat_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(cat_table)
        story.append(Spacer(1, 0.3 * cm))

        story.append(_build_category_chart_native(category_scores))
        story.append(Spacer(1, 0.4 * cm))

    investor_pitch = report.get("investor_pitch", {})
    if investor_pitch:
        story.append(Paragraph("<b>Tese para Investidores</b>", styles["Heading3"]))
        story.append(Paragraph(investor_pitch.get("investment_thesis", "N/A"), styles["BodyText"]))
        story.append(Paragraph(f"<b>Prontidão:</b> {investor_pitch.get('funding_readiness', 'N/A')}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Ticket sugerido:</b> {investor_pitch.get('suggested_ticket', 'N/A')}", styles["BodyText"]))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("<b>Pontos Fortes</b>", styles["Heading4"]))
    for item in report.get("strengths", []):
        story.append(Paragraph(f"• {item}", styles["BodyText"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("<b>Pontos a Melhorar</b>", styles["Heading4"]))
    for item in report.get("weaknesses", []):
        story.append(Paragraph(f"• {item}", styles["BodyText"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("<b>Recomendações</b>", styles["Heading4"]))
    for item in report.get("recommendations", []):
        story.append(Paragraph(f"• {item}", styles["BodyText"]))

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"<i>Motor utilizado: {metadata.get('analysis_engine_used', 'local')} | "
            f"Solicitado: {metadata.get('analysis_engine_requested', 'local')}</i>",
            styles["Normal"],
        )
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    doc.build(story)
    return output_path

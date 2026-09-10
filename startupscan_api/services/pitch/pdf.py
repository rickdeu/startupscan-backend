import math
import os
import re
from datetime import datetime

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "static", "img", "icon.png",
)
_LOGO_ASPECT = None
if os.path.exists(LOGO_PATH):
    try:
        from PIL import Image as _PILImage
        with _PILImage.open(LOGO_PATH) as _im:
            _LOGO_ASPECT = _im.width / _im.height
    except Exception:
        _LOGO_ASPECT = 0.75

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .design import _build_pitch_design_profile, _mix_colors, _palette_for_slide, _with_alpha
from .enricher import _safe_str, _truncate_text, _wrap_text_lines


# DejaVu Sans ships inside matplotlib (a pinned dependency), so it's always
# available without bundling extra font assets. Unlike the base-14 Helvetica
# this used to draw with, it covers Cyrillic — Helvetica has none, so every
# Russian-language deck was silently rendering with invisible body text.
#
# Simplified Chinese needs a different fix: no TrueType font bundled with
# this project (DejaVu included) carries Han glyphs, so zh-hans decks were
# *also* rendering blank. ReportLab ships a built-in, non-embedded reference
# to the standard Adobe "STSong-Light" CJK font instead — every PDF viewer
# has a substitute for it, so no font file needs bundling for this either.
def _register_deck_fonts():
    try:
        import matplotlib

        base = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
        pdfmetrics.registerFont(TTFont("DejaVuSans", os.path.join(base, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(base, "DejaVuSans-Bold.ttf")))
        reg, bold = "DejaVuSans", "DejaVuSans-Bold"
    except Exception:
        reg, bold = "Helvetica", "Helvetica-Bold"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    except Exception:
        pass
    return reg, bold


F_REG, F_BOLD = _register_deck_fonts()
_CJK_FONT = "STSong-Light"


def _font_for(language: str, bold: bool = False) -> str:
    """STSong-Light has no distinct bold weight; every other language uses DejaVu Sans."""
    if (language or "").strip().lower() == "zh-hans":
        return _CJK_FONT
    return F_BOLD if bold else F_REG


# ─────────────────────────────────────────────────────────────
#  Per-template style profile.
#
#  _draw_template_bg (below) already gives each of the 6 manual templates a
#  distinct decorative background. This profile makes the rest of the deck
#  look genuinely different per template too — corner rounding, the bullet
#  marker shape, the section-header treatment, the cover badge shape and
#  the title alignment — while every renderer still shares one code path
#  (so a future content/quality fix still applies identically everywhere).
# ─────────────────────────────────────────────────────────────

_TEMPLATE_STYLES = {
    "orbit":    {"corner": 16, "marker": "circle",  "badge": "circle",  "header": "band",   "title_align": "left"},
    "grid":     {"corner": 0,  "marker": "square",  "badge": "square",  "header": "rule",   "title_align": "left"},
    "wave":     {"corner": 28, "marker": "circle",  "badge": "circle",  "header": "band",   "title_align": "left"},
    "diagonal": {"corner": 0,  "marker": "diamond", "badge": "diamond", "header": "tag",    "title_align": "left"},
    "aurora":   {"corner": 22, "marker": "hex",     "badge": "circle",  "header": "band",   "title_align": "center"},
    "ribbon":   {"corner": 10, "marker": "circle",  "badge": "circle",  "header": "ribbon", "title_align": "left"},
}


def _style_for(template: str) -> dict:
    return _TEMPLATE_STYLES.get((template or "orbit").strip().lower(), _TEMPLATE_STYLES["orbit"])


def _draw_marker_shape(pdf: canvas.Canvas, cx: float, cy: float, r: float, shape: str, fill_color=None,
                        stroke_color=None, stroke_width: float = 1.0) -> None:
    """Draws the bullet/badge marker in the shape the current template calls for.
    Pass fill_color for a filled marker, stroke_color (with fill_color=None) for an outline-only ring."""
    do_fill = fill_color is not None
    do_stroke = stroke_color is not None
    if not do_fill and not do_stroke:
        return
    if do_fill:
        pdf.setFillColor(fill_color)
    if do_stroke:
        pdf.setStrokeColor(stroke_color)
        pdf.setLineWidth(stroke_width)
    shape = (shape or "circle").lower()
    fill_flag, stroke_flag = int(do_fill), int(do_stroke)
    if shape == "square":
        pdf.roundRect(cx - r, cy - r, r * 2, r * 2, r * 0.25, stroke=stroke_flag, fill=fill_flag)
    elif shape == "diamond":
        p = pdf.beginPath()
        p.moveTo(cx, cy + r)
        p.lineTo(cx + r, cy)
        p.lineTo(cx, cy - r)
        p.lineTo(cx - r, cy)
        p.close()
        pdf.drawPath(p, stroke=stroke_flag, fill=fill_flag)
    elif shape == "hex":
        p = pdf.beginPath()
        pts = [(cx + r * math.cos(math.radians(60 * i - 30)), cy + r * math.sin(math.radians(60 * i - 30)))
               for i in range(6)]
        p.moveTo(*pts[0])
        for pt in pts[1:]:
            p.lineTo(*pt)
        p.close()
        pdf.drawPath(p, stroke=stroke_flag, fill=fill_flag)
    else:  # circle
        pdf.circle(cx, cy, r, stroke=stroke_flag, fill=fill_flag)


# ─────────────────────────────────────────────────────────────
#  Static chrome copy (labels, defaults, slide titles) per UI language.
#  Kept local to this module - like REPORT_STRINGS in utils/report.py and
#  _TEMPLATES in utils/business_canvas.py - because this is pitch-deck
#  chrome text, not general UI copy, and not the generated pitch content
#  itself (which already arrives pre-translated inside pitch_payload).
# ─────────────────────────────────────────────────────────────

_DEFAULT_LANGUAGE = "en"

_DECK_STRINGS = {
    "pt": {
        "cover_subtitle_default": "Apresentação executiva para investidores",
        "elevator_title": "Elevator Pitch",
        "elevator_subtitle": "Mensagem central em até 90 segundos",
        "slide_no_info": "Informação não disponível para este slide.",
        "slide_default_title": "Slide",
        "slide_word": "Slide",
        "section_no_content": "Sem conteúdo.",
        "section_default_title": "Seção",
        "section_subtitle": "Resumo estratégico",
        "roadmap_title": "Roteiro de Apresentação",
        "roadmap_subtitle": "Sequência sugerida para apresentação ao vivo",
        "funding_goal_prefix": "Meta de captação",
        "allocation_prefix": "Alocação",
        "investment_title": "Captação e Uso de Capital",
        "investment_subtitle": "Plano financeiro para execução e escala",
        "investment_default_title": "Captação",
        "closing_default": "Obrigado. Estamos prontos para os próximos passos da captação.",
        "closing_title": "Conclusão",
        "closing_subtitle": "Mensagem final ao investidor",
        "closing_cta": "Vamos conversar",
        "deck_default_title": "Pitch de Negocio",
        "deck_default_slogan": "Proposta de valor em evolucao.",
        "context_label": "Contexto",
        "generated_label": "Gerado em",
        "engine_label": "Motor",
        "exec_confidential_tag": "PITCH DECK EXECUTIVO  ·  CONFIDENCIAL",
        "col_theses": "PRINCIPAIS TESES",
        "col_execution_notes": "NOTAS DE EXECUÇÃO",
        "narrative_flow": "FLUXO DA NARRATIVA",
        "key_points": "PONTOS-CHAVE",
        "kpi_goal": "META",
        "kpi_runway": "RUNWAY",
        "kpi_allocation": "ALOCAÇÃO",
        "allocation_chart_title": "USO DO CAPITAL",
        "timeline_phase_deploy": "Alocar capital",
        "timeline_phase_execute": "Executar plano",
        "timeline_phase_milestone": "Atingir marcos",
        "timeline_phase_raise": "Próxima rodada",
    },
    "en": {
        "cover_subtitle_default": "Executive presentation for investors",
        "elevator_title": "Elevator Pitch",
        "elevator_subtitle": "Core message in under 90 seconds",
        "slide_no_info": "Information not available for this slide.",
        "slide_default_title": "Slide",
        "slide_word": "Slide",
        "section_no_content": "No content.",
        "section_default_title": "Section",
        "section_subtitle": "Strategic summary",
        "roadmap_title": "Presentation Roadmap",
        "roadmap_subtitle": "Suggested sequence for a live presentation",
        "funding_goal_prefix": "Funding goal",
        "allocation_prefix": "Allocation",
        "investment_title": "Fundraising & Use of Capital",
        "investment_subtitle": "Financial plan for execution and scale",
        "investment_default_title": "Fundraising",
        "closing_default": "Thank you. We are ready for the next steps of the fundraising process.",
        "closing_title": "Conclusion",
        "closing_subtitle": "Final message to the investor",
        "closing_cta": "Let's talk",
        "deck_default_title": "Business Pitch",
        "deck_default_slogan": "An evolving value proposition.",
        "context_label": "Context",
        "generated_label": "Generated on",
        "engine_label": "Engine",
        "exec_confidential_tag": "EXECUTIVE PITCH DECK  ·  CONFIDENTIAL",
        "col_theses": "KEY THESES",
        "col_execution_notes": "EXECUTION NOTES",
        "narrative_flow": "NARRATIVE FLOW",
        "key_points": "KEY POINTS",
        "kpi_goal": "GOAL",
        "kpi_runway": "RUNWAY",
        "kpi_allocation": "ALLOCATION",
        "allocation_chart_title": "USE OF CAPITAL",
        "timeline_phase_deploy": "Deploy capital",
        "timeline_phase_execute": "Execute plan",
        "timeline_phase_milestone": "Hit milestones",
        "timeline_phase_raise": "Next round",
    },
    "ru": {
        "cover_subtitle_default": "Презентация для инвесторов",
        "elevator_title": "Elevator Pitch",
        "elevator_subtitle": "Ключевое сообщение менее чем за 90 секунд",
        "slide_no_info": "Информация для этого слайда недоступна.",
        "slide_default_title": "Слайд",
        "slide_word": "Слайд",
        "section_no_content": "Нет содержания.",
        "section_default_title": "Раздел",
        "section_subtitle": "Стратегическое резюме",
        "roadmap_title": "План презентации",
        "roadmap_subtitle": "Рекомендуемая последовательность для живой презентации",
        "funding_goal_prefix": "Цель привлечения капитала",
        "allocation_prefix": "Распределение",
        "investment_title": "Привлечение капитала и использование средств",
        "investment_subtitle": "Финансовый план для реализации и масштабирования",
        "investment_default_title": "Привлечение капитала",
        "closing_default": "Спасибо. Мы готовы к следующим шагам привлечения инвестиций.",
        "closing_title": "Заключение",
        "closing_subtitle": "Заключительное сообщение инвестору",
        "closing_cta": "Давайте поговорим",
        "deck_default_title": "Бизнес-питч",
        "deck_default_slogan": "Развивающееся ценностное предложение.",
        "context_label": "Контекст",
        "generated_label": "Создано",
        "engine_label": "Движок",
        "exec_confidential_tag": "PITCH DECK ДЛЯ ИНВЕСТОРОВ  ·  КОНФИДЕНЦИАЛЬНО",
        "col_theses": "КЛЮЧЕВЫЕ ТЕЗИСЫ",
        "col_execution_notes": "ЗАМЕТКИ ПО РЕАЛИЗАЦИИ",
        "narrative_flow": "ХОД ПОВЕСТВОВАНИЯ",
        "key_points": "КЛЮЧЕВЫЕ МОМЕНТЫ",
        "kpi_goal": "ЦЕЛЬ",
        "kpi_runway": "RUNWAY",
        "kpi_allocation": "РАСПРЕДЕЛЕНИЕ",
        "allocation_chart_title": "ИСПОЛЬЗОВАНИЕ КАПИТАЛА",
        "timeline_phase_deploy": "Вложить капитал",
        "timeline_phase_execute": "Реализовать план",
        "timeline_phase_milestone": "Достичь целей",
        "timeline_phase_raise": "Следующий раунд",
    },
    "de": {
        "cover_subtitle_default": "Investorenpräsentation",
        "elevator_title": "Elevator Pitch",
        "elevator_subtitle": "Kernbotschaft in unter 90 Sekunden",
        "slide_no_info": "Für diese Folie sind keine Informationen verfügbar.",
        "slide_default_title": "Folie",
        "slide_word": "Folie",
        "section_no_content": "Kein Inhalt.",
        "section_default_title": "Abschnitt",
        "section_subtitle": "Strategische Zusammenfassung",
        "roadmap_title": "Präsentationsablauf",
        "roadmap_subtitle": "Empfohlene Reihenfolge für eine Live-Präsentation",
        "funding_goal_prefix": "Finanzierungsziel",
        "allocation_prefix": "Mittelverwendung",
        "investment_title": "Finanzierung und Mittelverwendung",
        "investment_subtitle": "Finanzplan für Umsetzung und Skalierung",
        "investment_default_title": "Finanzierung",
        "closing_default": "Vielen Dank. Wir sind bereit für die nächsten Schritte der Finanzierungsrunde.",
        "closing_title": "Fazit",
        "closing_subtitle": "Abschließende Botschaft an den Investor",
        "closing_cta": "Lassen Sie uns sprechen",
        "deck_default_title": "Business Pitch",
        "deck_default_slogan": "Ein sich entwickelndes Wertversprechen.",
        "context_label": "Kontext",
        "generated_label": "Erstellt am",
        "engine_label": "Engine",
        "exec_confidential_tag": "PITCH DECK FÜR INVESTOREN  ·  VERTRAULICH",
        "col_theses": "KERNTHESEN",
        "col_execution_notes": "UMSETZUNGSHINWEISE",
        "narrative_flow": "ABLAUF DER PRÄSENTATION",
        "key_points": "KERNPUNKTE",
        "kpi_goal": "ZIEL",
        "kpi_runway": "RUNWAY",
        "kpi_allocation": "ALLOKATION",
        "allocation_chart_title": "MITTELVERWENDUNG",
        "timeline_phase_deploy": "Kapital einsetzen",
        "timeline_phase_execute": "Plan ausführen",
        "timeline_phase_milestone": "Meilensteine erreichen",
        "timeline_phase_raise": "Nächste Runde",
    },
    "es": {
        "cover_subtitle_default": "Presentación ejecutiva para inversores",
        "elevator_title": "Elevator Pitch",
        "elevator_subtitle": "Mensaje central en menos de 90 segundos",
        "slide_no_info": "Información no disponible para esta diapositiva.",
        "slide_default_title": "Diapositiva",
        "slide_word": "Diapositiva",
        "section_no_content": "Sin contenido.",
        "section_default_title": "Sección",
        "section_subtitle": "Resumen estratégico",
        "roadmap_title": "Guion de la Presentación",
        "roadmap_subtitle": "Secuencia sugerida para una presentación en vivo",
        "funding_goal_prefix": "Meta de captación",
        "allocation_prefix": "Asignación",
        "investment_title": "Captación y Uso de Capital",
        "investment_subtitle": "Plan financiero para la ejecución y escalado",
        "investment_default_title": "Captación",
        "closing_default": "Gracias. Estamos listos para los próximos pasos de la captación.",
        "closing_title": "Conclusión",
        "closing_subtitle": "Mensaje final al inversor",
        "closing_cta": "Hablemos",
        "deck_default_title": "Pitch de Negocio",
        "deck_default_slogan": "Una propuesta de valor en evolución.",
        "context_label": "Contexto",
        "generated_label": "Generado el",
        "engine_label": "Motor",
        "exec_confidential_tag": "PITCH DECK EJECUTIVO  ·  CONFIDENCIAL",
        "col_theses": "TESIS PRINCIPALES",
        "col_execution_notes": "NOTAS DE EJECUCIÓN",
        "narrative_flow": "FLUJO NARRATIVO",
        "key_points": "PUNTOS CLAVE",
        "kpi_goal": "META",
        "kpi_runway": "RUNWAY",
        "kpi_allocation": "ASIGNACIÓN",
        "allocation_chart_title": "USO DEL CAPITAL",
        "timeline_phase_deploy": "Desplegar capital",
        "timeline_phase_execute": "Ejecutar el plan",
        "timeline_phase_milestone": "Alcanzar hitos",
        "timeline_phase_raise": "Próxima ronda",
    },
    "zh-hans": {
        "cover_subtitle_default": "面向投资者的高管演示",
        "elevator_title": "Elevator Pitch",
        "elevator_subtitle": "90秒内传达核心信息",
        "slide_no_info": "此幻灯片暂无信息。",
        "slide_default_title": "幻灯片",
        "slide_word": "幻灯片",
        "section_no_content": "无内容。",
        "section_default_title": "章节",
        "section_subtitle": "战略摘要",
        "roadmap_title": "演示流程",
        "roadmap_subtitle": "现场演示的建议顺序",
        "funding_goal_prefix": "融资目标",
        "allocation_prefix": "资金分配",
        "investment_title": "融资与资金使用",
        "investment_subtitle": "执行与扩张的财务计划",
        "investment_default_title": "融资",
        "closing_default": "谢谢。我们已准备好进入融资的下一步。",
        "closing_title": "结语",
        "closing_subtitle": "致投资者的结束语",
        "closing_cta": "期待与您交流",
        "deck_default_title": "商业路演",
        "deck_default_slogan": "不断演进的价值主张。",
        "context_label": "背景",
        "generated_label": "生成于",
        "engine_label": "引擎",
        "exec_confidential_tag": "高管路演  ·  保密",
        "col_theses": "核心论点",
        "col_execution_notes": "执行说明",
        "narrative_flow": "叙述流程",
        "key_points": "要点",
        "kpi_goal": "目标",
        "kpi_runway": "RUNWAY",
        "kpi_allocation": "分配",
        "allocation_chart_title": "资金使用情况",
        "timeline_phase_deploy": "投入资金",
        "timeline_phase_execute": "执行计划",
        "timeline_phase_milestone": "达成里程碑",
        "timeline_phase_raise": "下一轮融资",
    },
    "umb": {
        "cover_subtitle_default": "Apresentação yokolele ku investidores",
        "elevator_title": "Elevator Pitch",
        "elevator_subtitle": "Esapo lyokole ha 90 segundos",
        "slide_no_info": "Ka kuli elombolwilo pa slide yayi.",
        "slide_default_title": "Slide",
        "slide_word": "Slide",
        "section_no_content": "Ka kuli conteúdo.",
        "section_default_title": "Onepo",
        "section_subtitle": "Elomboluilo lyestratégia",
        "roadmap_title": "Onjila Yapresentação",
        "roadmap_subtitle": "Onjila yalombolwiwa oku apresentação yokolele",
        "funding_goal_prefix": "Ombiliko yokuandiwa",
        "allocation_prefix": "Okuavela",
        "investment_title": "Okuandiwa lo Okuavela kwa Kapital",
        "investment_subtitle": "Elongiso lyombongo oku okulinga lo okukula",
        "investment_default_title": "Okuandiwa",
        "closing_default": "Tuasakidila. Twapongoluka oku olondaka yokukuavo yokuandiwa.",
        "closing_title": "Esukilo",
        "closing_subtitle": "Esapo lyokusukila ku investidor",
        "closing_cta": "Tuvangule",
        "deck_default_title": "Pitch Yombiliko",
        "deck_default_slogan": "Etyulo lyoku eyi lyina lyalinga oku kula.",
        "context_label": "Contexto",
        "generated_label": "Yalingiwa",
        "engine_label": "Motor",
        "exec_confidential_tag": "PITCH DECK YOKOLELE  ·  CONFIDENCIAL",
        "col_theses": "OYIPILAMO YOKOLELE",
        "col_execution_notes": "OSAPO YOKULINGA",
        "narrative_flow": "ONJILA YOKAMBA",
        "key_points": "OYIPILAMO",
        "kpi_goal": "OMBILIKO",
        "kpi_runway": "RUNWAY",
        "kpi_allocation": "OKUAVELA",
        "allocation_chart_title": "OKUAVELA KWA KAPITAL",
        "timeline_phase_deploy": "Yikola ombongo",
        "timeline_phase_execute": "Linga upange",
        "timeline_phase_milestone": "Wana oyipimo",
        "timeline_phase_raise": "Rodada yakwavo",
    },
}


def _deck_strings(language: str) -> dict:
    return _DECK_STRINGS.get(language) or _DECK_STRINGS[_DEFAULT_LANGUAGE]


# ─────────────────────────────────────────────────────────────
#  Low-level drawing primitives
# ─────────────────────────────────────────────────────────────

def _draw_template_bg(pdf: canvas.Canvas, width: float, height: float,
                      palette: dict, template: str, seed: int) -> None:
    """Draw decorative template-specific background layer (called after solid fill)."""
    t = (template or "orbit").strip().lower()
    shift = (seed % 37) - 18

    if t == "grid":
        pdf.setStrokeColor(_with_alpha(palette["shape1"], 0.25))
        pdf.setLineWidth(0.5)
        step = 28 + (seed % 8)
        for y in range(0, int(height) + step, step):
            pdf.line(0, y, width, y + shift * 0.2)
        for x in range(0, int(width) + step, step):
            pdf.line(x, 0, x + shift * 0.2, height)

    elif t == "wave":
        for idx in range(6):
            r = 220 + idx * 58
            cx = width * 0.15 + idx * 80 + shift * 0.7
            cy = -50 + idx * 30
            pdf.setFillColor(_with_alpha(palette["shape1"], 0.18 - idx * 0.02))
            pdf.circle(cx, cy, r, stroke=0, fill=1)
        for idx in range(4):
            r = 200 + idx * 66
            cx = width - 60 - idx * 68
            cy = height + 30 - idx * 20
            pdf.setFillColor(_with_alpha(palette["shape2"], 0.14 - idx * 0.02))
            pdf.circle(cx, cy, r, stroke=0, fill=1)

    elif t == "diagonal":
        pdf.saveState()
        pdf.translate(-160 + shift, -90)
        pdf.rotate(16 + (seed % 6))
        for idx in range(10):
            pdf.setFillColor(_with_alpha(palette["shape1"], 0.20 - idx * 0.015))
            pdf.roundRect(0, idx * 62, width + 300, 36, 8, stroke=0, fill=1)
        pdf.restoreState()
        pdf.saveState()
        pdf.translate(width * 0.38, -130)
        pdf.rotate(16 + (seed % 6))
        for idx in range(7):
            pdf.setFillColor(_with_alpha(palette["shape2"], 0.14 - idx * 0.01))
            pdf.roundRect(0, idx * 70, width + 140, 22, 6, stroke=0, fill=1)
        pdf.restoreState()

    elif t == "aurora":
        for idx in range(7):
            r = 310 - idx * 26
            cx = width * 0.08 + idx * 84 + shift * 0.35
            cy = height - 30 - idx * 16
            pdf.setFillColor(_with_alpha(palette["shape1"], 0.13 - idx * 0.01))
            pdf.circle(cx, cy, r, stroke=0, fill=1)
        for idx in range(5):
            r = 270 - idx * 22
            cx = width - 30 - idx * 78
            cy = 20 + idx * 20
            pdf.setFillColor(_with_alpha(palette["shape2"], 0.12 - idx * 0.01))
            pdf.circle(cx, cy, r, stroke=0, fill=1)

    elif t == "ribbon":
        for idx in range(11):
            y = 18 + idx * 58
            wobble = shift * 0.55 + (idx % 3) * 7
            pdf.setFillColor(_with_alpha(palette["shape1"], 0.22 - idx * 0.015))
            pdf.roundRect(-44 + wobble, y, width + 88, 20, 9, stroke=0, fill=1)
        for idx in range(8):
            y = 44 + idx * 68
            wobble = shift * 0.45 - (idx % 4) * 8
            pdf.setFillColor(_with_alpha(palette["shape2"], 0.16 - idx * 0.01))
            pdf.roundRect(-64 + wobble, y, width + 128, 13, 7, stroke=0, fill=1)

    else:  # orbit (default)
        # Large outer glow circles top-right
        for idx, alpha in enumerate([0.10, 0.14, 0.09]):
            r = 290 - idx * 44
            pdf.setFillColor(_with_alpha(palette["band"], alpha))
            pdf.circle(width * 0.88 + (seed % 20) - 10, height * 0.78 + (seed % 15) - 7, r, stroke=0, fill=1)
        # Accent ring (stroke only) bottom-left
        pdf.setStrokeColor(_with_alpha(palette["accent"], 0.12))
        pdf.setLineWidth(18)
        pdf.circle(width * 0.06 + shift, height * 0.22 + shift, 160, stroke=1, fill=0)
        pdf.setStrokeColor(_with_alpha(palette["accent"], 0.07))
        pdf.setLineWidth(32)
        pdf.circle(width * 0.06 + shift, height * 0.22 + shift, 220, stroke=1, fill=0)

    # Reset to a sane default: several branches above set a large line
    # width for their own decorative rings and never restore it, which
    # would otherwise leak into whatever gets stroked next on this page.
    pdf.setLineWidth(1)


def _draw_left_stripe(pdf: canvas.Canvas, height: float, palette: dict) -> None:
    pdf.setFillColor(palette["band"])
    pdf.rect(0, 0, 7, height, stroke=0, fill=1)
    pdf.setFillColor(_with_alpha(palette["accent"], 0.6))
    pdf.rect(0, 0, 3, height, stroke=0, fill=1)


def _draw_top_band(pdf: canvas.Canvas, width: float, height: float,
                   palette: dict, label: str, language: str = _DEFAULT_LANGUAGE,
                   style: dict | None = None) -> None:
    """
    Renders the section header. Keeps a fixed 54pt height across every
    template (so title placement below it never has to shift), but the
    visual treatment itself — a solid band, a minimalist double rule, an
    angled corner tag, or a notched ribbon — comes from the template's
    style profile (_style_for), which is the main thing that makes each
    template read as a genuinely different design rather than just a
    different background pattern.
    """
    style = style or _TEMPLATE_STYLES["orbit"]
    header = style.get("header", "band")
    band_h = 54
    top = height - band_h
    font = _font_for(language, True)

    if header == "rule":
        pdf.setStrokeColor(_with_alpha(palette["accent"], 0.7))
        pdf.setLineWidth(1.2)
        pdf.line(20, height - 15, width - 20, height - 15)
        pdf.setStrokeColor(_with_alpha(palette["band"], 0.5))
        pdf.setLineWidth(0.6)
        pdf.line(20, top + 8, width - 20, top + 8)
        if label:
            pdf.setFillColor(palette["accent"])
            pdf.setFont(font, 10.5)
            pdf.drawString(20, top + 20, label.upper())

    elif header == "tag":
        tag_w = min(width * 0.44, 90 + (stringWidth(label.upper(), font, 10.5) if label else 0))
        p = pdf.beginPath()
        p.moveTo(0, top)
        p.lineTo(tag_w, top)
        p.lineTo(tag_w - 24, height)
        p.lineTo(0, height)
        p.close()
        pdf.setFillColor(palette["band"])
        pdf.drawPath(p, stroke=0, fill=1)
        pdf.setFillColor(_with_alpha(palette["accent"], 0.6))
        pdf.rect(0, height - 3, tag_w, 3, stroke=0, fill=1)
        if label:
            pdf.setFillColor(colors.white)
            pdf.setFont(font, 10.5)
            pdf.drawString(20, top + 20, label.upper())

    elif header == "ribbon":
        notch = 18
        p = pdf.beginPath()
        p.moveTo(0, top)
        p.lineTo(width - notch, top)
        p.lineTo(width, top + band_h / 2)
        p.lineTo(width - notch, height)
        p.lineTo(0, height)
        p.close()
        pdf.setFillColor(palette["band"])
        pdf.drawPath(p, stroke=0, fill=1)
        pdf.setFillColor(_with_alpha(palette["accent"], 0.5))
        pdf.rect(0, height - 3, width - notch, 3, stroke=0, fill=1)
        if label:
            pdf.setFillColor(colors.white)
            pdf.setFont(font, 11)
            pdf.drawString(20, top + 20, label.upper())

    else:  # band (default: orbit / wave / aurora)
        pdf.setFillColor(palette["band"])
        pdf.rect(0, top, width, band_h, stroke=0, fill=1)
        pdf.setFillColor(_with_alpha(palette["accent"], 0.5))
        pdf.rect(0, height - 3, width, 3, stroke=0, fill=1)
        if label:
            pdf.setFillColor(colors.white)
            pdf.setFont(font, 11)
            if style.get("title_align") == "center":
                pdf.drawCentredString(width / 2, top + 20, label.upper())
            else:
                pdf.drawString(20, top + 20, label.upper())


def _draw_slide_number_watermark(pdf: canvas.Canvas, width: float, height: float,
                                  number: int, palette: dict, language: str = _DEFAULT_LANGUAGE) -> None:
    txt = str(number).zfill(2)
    font = _font_for(language, True)
    pdf.setFillColor(_with_alpha(palette["shape2"], 0.55))
    pdf.setFont(font, 120)
    tw = stringWidth(txt, font, 120)
    pdf.drawString(width - tw - 22, 14, txt)


# ─────────────────────────────────────────────────────────────
#  Slide topic icons — simple abstract vector glyphs (no external
#  image/font assets) drawn with plain canvas primitives, so every
#  content slide gets a visual anchor instead of being a wall of text.
# ─────────────────────────────────────────────────────────────
_TOPIC_ICON_KEYWORDS = [
    ("problem", ("problem", "problema")),
    ("solution", ("solution", "solução", "solucao", "diferencial")),
    ("market", ("market", "mercado", "segmenta")),
    ("business_model", ("business model", "modelo de negócio", "modelo de negocio", "unit economics")),
    ("traction", ("traction", "tração", "tracao", "validation", "validação", "validacao")),
    ("team", ("team", "time", "equipe")),
    ("gtm", ("go-to-market", "gtm", "estratégia", "estrategia")),
    ("competitive", ("competitive", "vantagem", "moat")),
    ("funding", ("fundraising", "captação", "captacao", "capital", "investment", "investimento")),
    ("vision", ("vision", "visão", "visao", "roadmap")),
    ("conclusion", ("conclusion", "conclusão", "conclusao", "call to action")),
]


def _infer_topic_icon(title: str) -> str:
    low = (title or "").strip().lower()
    for icon_key, keywords in _TOPIC_ICON_KEYWORDS:
        if any(kw in low for kw in keywords):
            return icon_key
    return "generic"


def _poly(pdf: canvas.Canvas, points: list[tuple[float, float]], *, fill: bool = True, stroke: bool = False) -> None:
    path = pdf.beginPath()
    path.moveTo(*points[0])
    for pt in points[1:]:
        path.lineTo(*pt)
    path.close()
    pdf.drawPath(path, fill=fill, stroke=stroke)


def _draw_topic_icon(pdf: canvas.Canvas, cx: float, cy: float, r: float,
                      icon_key: str, badge_color, glyph_color) -> None:
    """Draws a circular badge of radius r centered at (cx, cy) with a
    small abstract glyph representing the slide's topic."""
    pdf.setFillColor(badge_color)
    pdf.circle(cx, cy, r, stroke=0, fill=1)

    pdf.setFillColor(glyph_color)
    pdf.setStrokeColor(glyph_color)
    # Some branches below stroke a shape before setting their own line
    # width (or never set one at all, e.g. "funding"/"competitive"/the
    # generic fallback). Without a reset here they inherit whatever width
    # a *previous, unrelated* shape left on the canvas — on the "orbit"
    # template's 18-32pt accent rings that turns a thin glyph outline into
    # a stroke thick enough to blot out the entire badge as a solid blob.
    pdf.setLineWidth(1.4)
    g = r * 0.5  # glyph half-extent

    if icon_key == "problem":
        _poly(pdf, [(cx, cy + g), (cx - g, cy - g * 0.7), (cx + g, cy - g * 0.7)], fill=False, stroke=True)
        pdf.setLineWidth(1.6)
        pdf.line(cx, cy + g * 0.25, cx, cy - g * 0.15)
        pdf.circle(cx, cy - g * 0.45, 1.4, stroke=0, fill=1)
    elif icon_key == "solution":
        pdf.circle(cx, cy + g * 0.15, g * 0.55, stroke=1, fill=0)
        pdf.setLineWidth(1.4)
        for dx, dy in ((0, 1), (0.85, 0.55), (-0.85, 0.55), (0.85, -0.2), (-0.85, -0.2)):
            pdf.line(cx + dx * g * 0.85, cy + g * 0.15 + dy * g * 0.85,
                      cx + dx * g * 1.25, cy + g * 0.15 + dy * g * 1.25)
        pdf.rect(cx - g * 0.22, cy - g * 0.65, g * 0.44, g * 0.3, stroke=1, fill=0)
    elif icon_key == "market":
        pdf.circle(cx, cy, g * 0.85, stroke=1, fill=0)
        pdf.setLineWidth(1.1)
        pdf.line(cx - g * 0.85, cy, cx + g * 0.85, cy)
        pdf.ellipse(cx - g * 0.4, cy - g * 0.85, cx + g * 0.4, cy + g * 0.85, stroke=1, fill=0)
    elif icon_key == "business_model":
        pdf.setLineWidth(1.3)
        pdf.circle(cx - g * 0.35, cy, g * 0.55, stroke=1, fill=0)
        pdf.circle(cx + g * 0.35, cy, g * 0.55, stroke=1, fill=0)
    elif icon_key == "traction":
        bar_w = g * 0.4
        for i, h in enumerate((0.5, 0.85, 1.2)):
            bx = cx - g * 0.9 + i * (bar_w + 4)
            pdf.rect(bx, cy - g * 0.7, bar_w, g * h, stroke=0, fill=1)
        pdf.setLineWidth(1.4)
        pdf.line(cx - g * 0.9, cy - g * 0.75, cx + g * 0.95, cy + g * 0.55)
        _poly(pdf, [(cx + g * 0.95, cy + g * 0.55), (cx + g * 0.55, cy + g * 0.5),
                    (cx + g * 0.85, cy + g * 0.2)], fill=True)
    elif icon_key == "team":
        for dx in (-0.55, 0, 0.55):
            pdf.circle(cx + dx * g, cy + g * 0.25, g * 0.32, stroke=0, fill=1)
        pdf.setLineWidth(1.1)
        pdf.line(cx - g * 0.55, cy + g * 0.05, cx + g * 0.55, cy + g * 0.05)
    elif icon_key == "gtm":
        pdf.setLineWidth(1.2)
        for rad in (g * 0.9, g * 0.55):
            pdf.circle(cx, cy, rad, stroke=1, fill=0)
        pdf.circle(cx, cy, g * 0.2, stroke=0, fill=1)
    elif icon_key == "competitive":
        _poly(pdf, [(cx, cy + g), (cx + g * 0.85, cy + g * 0.45), (cx + g * 0.6, cy - g * 0.8),
                    (cx, cy - g), (cx - g * 0.6, cy - g * 0.8), (cx - g * 0.85, cy + g * 0.45)],
              fill=False, stroke=True)
    elif icon_key == "funding":
        for i, dy in enumerate((-0.35, 0, 0.35)):
            pdf.ellipse(cx - g * 0.75, cy + dy * g - g * 0.15, cx + g * 0.75, cy + dy * g + g * 0.15,
                        stroke=1, fill=(i == 1))
    elif icon_key == "vision":
        pdf.setLineWidth(1.4)
        prev = None
        for i, (dx, dy) in enumerate(((-0.8, -0.6), (-0.3, -0.1), (0.3, 0.3), (0.8, 0.7))):
            pt = (cx + dx * g, cy + dy * g)
            if prev:
                pdf.line(*prev, *pt)
            pdf.circle(pt[0], pt[1], 2.2, stroke=0, fill=1)
            prev = pt
        _poly(pdf, [(cx + 0.8 * g, cy + 0.7 * g), (cx + 0.8 * g + 8, cy + 0.7 * g + 4),
                    (cx + 0.8 * g, cy + 0.7 * g + 8)], fill=True)
    elif icon_key == "conclusion":
        pdf.setLineWidth(1.8)
        pdf.line(cx - g * 0.5, cy, cx - g * 0.1, cy - g * 0.4)
        pdf.line(cx - g * 0.1, cy - g * 0.4, cx + g * 0.6, cy + g * 0.5)
    else:  # generic
        pdf.circle(cx, cy, g * 0.4, stroke=1, fill=0)
        pdf.circle(cx, cy, g * 0.85, stroke=1, fill=0)


def _draw_progress_dots(pdf: canvas.Canvas, width: float, page: int,
                         total: int, palette: dict) -> None:
    if total <= 1:
        return
    dot_r = 3.5
    gap = 10
    total_w = total * (dot_r * 2) + (total - 1) * gap
    start_x = (width - total_w) / 2
    y = 14
    for i in range(total):
        cx = start_x + i * (dot_r * 2 + gap) + dot_r
        if i + 1 == page:
            pdf.setFillColor(palette["accent"])
            pdf.circle(cx, y, dot_r + 1, stroke=0, fill=1)
        else:
            pdf.setFillColor(_with_alpha(palette["muted"], 0.45))
            pdf.circle(cx, y, dot_r, stroke=0, fill=1)


def _draw_footer_bar(pdf: canvas.Canvas, width: float, page: int, total: int,
                      engine: str, key: str, palette: dict,
                      language: str = _DEFAULT_LANGUAGE) -> None:
    t = _deck_strings(language)
    bar_h = 28
    pdf.setFillColor(_with_alpha(palette["bg"], 0.92))
    pdf.rect(0, 0, width, bar_h, stroke=0, fill=1)
    # thin separator line
    pdf.setStrokeColor(_with_alpha(palette["band"], 0.4))
    pdf.setLineWidth(0.5)
    pdf.line(0, bar_h, width, bar_h)

    font = _font_for(language)
    pdf.setFillColor(_with_alpha(palette["muted"], 0.7))
    pdf.setFont(font, 7.5)
    engine_label = t.get("engine_label", "Engine")
    pdf.drawString(20, 9, f"StartupScan · {engine_label}: {engine} · ID: {key or '—'}")
    slide_txt = f"{page} / {total}"
    tw = stringWidth(slide_txt, font, 7.5)
    pdf.drawString(width - tw - 20, 9, slide_txt)


def _draw_single_bullet(pdf: canvas.Canvas, text: str, x: float, y: float,
                         max_width: float, palette: dict, font_size: float = 10.5,
                         language: str = _DEFAULT_LANGUAGE, index: int | None = None,
                         max_lines: int = 3, marker_shape: str = "circle") -> float:
    """
    Draw one bullet item (numbered circle when `index` is given, plain dot
    otherwise). Returns new y.

    `max_lines` bounds how much of `text` gets shown — it is NOT a fixed
    220-character/3-line cap regardless of content, because the enrichment
    step (services/pitch/enricher.py) deliberately writes full, detailed
    sentences (up to ~340 chars); cutting them short here just to fit an
    arbitrary limit undoes that work and leaves slides looking terse. The
    truncation budget instead scales with how many lines the caller has
    room for, so short bullet lists (bigger font, more line budget) show
    their full text, and only genuinely long content ever gets an ellipsis.
    """
    marker_r = 8.0 if index is not None else 2.6
    text_x = x + marker_r * 2 + (10 if index is not None else 7)
    max_chars = max(20, int(max_width / (font_size * 0.58)))
    char_budget = max(220, max_lines * max_chars + 40)
    wrapped = _wrap_text_lines(_truncate_text(_safe_str(text, ""), char_budget), max_chars=max_chars)[:max_lines]
    if not wrapped:
        return y

    marker_cy = y + font_size * 0.38
    if index is not None:
        _draw_marker_shape(pdf, x + marker_r, marker_cy, marker_r, marker_shape, palette["band"])
        pdf.setFillColor(colors.white)
        pdf.setFont(_font_for(language, True), 7.5)
        pdf.drawCentredString(x + marker_r, marker_cy - 2.6, str(index))
    else:
        _draw_marker_shape(pdf, x + marker_r, marker_cy, marker_r, marker_shape, palette["accent"])

    pdf.setFillColor(palette["text"])
    pdf.setFont(_font_for(language), font_size)
    for i, line in enumerate(wrapped):
        pdf.drawString(text_x, y - i * (font_size + 2), line)
    return y - len(wrapped) * (font_size + 2) - 7


_ALLOCATION_RE = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*%\s*([^,;.]+)")


def _parse_allocation(text: str) -> list[tuple[float, str]]:
    """Best-effort split of a free-text allocation summary ('60% tech, 25% marketing...')
    into (percent, label) pairs, for a visual breakdown bar. Language-agnostic: it only
    looks for a number followed by '%', so it works the same across all 7 UI languages."""
    items = []
    for m in _ALLOCATION_RE.finditer(text or ""):
        try:
            pct = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        label = m.group(2).strip(" -–—:")
        if pct > 0 and label:
            items.append((pct, label))
    return items[:5]


def _draw_allocation_bar(pdf: canvas.Canvas, x: float, y: float, width_box: float,
                          items: list[tuple[float, str]], palette: dict, language: str) -> float:
    """Draws a stacked horizontal capital-allocation bar with a legend below it.
    Returns the y coordinate right below the legend, for the caller to keep drawing from."""
    bar_h = 20
    total = sum(p for p, _ in items) or 1.0
    swatches = [
        palette["band"],
        palette["accent"],
        _mix_colors(palette["band"], palette["muted"], 0.5),
        _with_alpha(palette["accent"], 0.55),
        palette["muted"],
    ]

    pdf.setFillColor(_with_alpha(palette["muted"], 0.18))
    pdf.roundRect(x, y, width_box, bar_h, bar_h / 2, stroke=0, fill=1)
    cx = x
    for i, (pct, _label) in enumerate(items):
        seg_w = width_box * (pct / total)
        pdf.setFillColor(swatches[i % len(swatches)])
        pdf.rect(cx, y, max(1.0, seg_w), bar_h, stroke=0, fill=1)
        cx += seg_w

    font = _font_for(language)
    legend_y = y - 17
    lx = x
    row_start_x = x
    pdf.setFont(font, 7.6)
    for i, (pct, label) in enumerate(items):
        txt = f"{pct:.0f}% {_truncate_text(label, 24)}"
        seg_w = 12 + stringWidth(txt, font, 7.6) + 20
        if lx + seg_w > x + width_box and lx > row_start_x:
            lx = x
            legend_y -= 15
        pdf.setFillColor(swatches[i % len(swatches)])
        pdf.rect(lx, legend_y + 1, 8, 8, stroke=0, fill=1)
        pdf.setFillColor(palette["muted"])
        pdf.drawString(lx + 12, legend_y, txt)
        lx += seg_w
    return legend_y - 14


# ─────────────────────────────────────────────────────────────
#  Slide renderers
# ─────────────────────────────────────────────────────────────

def _render_cover(pdf: canvas.Canvas, width: float, height: float,
                  slide: dict, palette: dict, template: str, seed: int,
                  page: int, total: int, engine: str, key: str,
                  language: str = _DEFAULT_LANGUAGE) -> None:
    t = _deck_strings(language)
    style = _style_for(template)
    # Solid background
    pdf.setFillColor(palette["bg"])
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    _draw_template_bg(pdf, width, height, palette, template, seed)

    # Left accent stripe (thicker on cover)
    pdf.setFillColor(palette["band"])
    pdf.rect(0, 0, 10, height, stroke=0, fill=1)
    pdf.setFillColor(palette["accent"])
    pdf.rect(0, 0, 4, height, stroke=0, fill=1)

    # Top accent bar
    pdf.setFillColor(_with_alpha(palette["band"], 0.9))
    pdf.rect(0, height - 10, width, 10, stroke=0, fill=1)

    # ── Platform logo (top-left, every deck carries the brand mark) ──
    if _LOGO_ASPECT:
        logo_h = 22
        logo_w = logo_h * _LOGO_ASPECT
        pdf.drawImage(LOGO_PATH, 24, height - 24 - logo_h, width=logo_w, height=logo_h,
                       mask="auto", preserveAspectRatio=True)

    # ── Company initials badge (top-right circle) ──
    startup_name = _safe_str(slide.get("startup_name"), "ST")
    initials = (startup_name[:2]).upper()
    badge_cx = width - 90
    badge_cy = height - 74
    badge_shape = style["badge"]
    _draw_marker_shape(pdf, badge_cx, badge_cy, 52, badge_shape, fill_color=palette["band"])
    _draw_marker_shape(pdf, badge_cx, badge_cy, 52, badge_shape, fill_color=_with_alpha(palette["accent"], 0.3))
    _draw_marker_shape(pdf, badge_cx, badge_cy, 52, badge_shape,
                        stroke_color=_with_alpha(palette["accent"], 0.7), stroke_width=2)
    pdf.setFillColor(colors.white)
    pdf.setFont(_font_for(language, True), 28)
    tw = stringWidth(initials, _font_for(language, True), 28)
    pdf.drawString(badge_cx - tw / 2, badge_cy - 10, initials)
    pdf.setFont(_font_for(language), 7.5)
    pdf.setFillColor(_with_alpha(colors.white, 0.6))
    pdf.drawCentredString(badge_cx, badge_cy - 24, "PITCH DECK")

    # ── Main title ──
    title = _safe_str(slide.get("title"), startup_name)
    # Remove boilerplate prefix
    for prefix in ("Pitch de Negócio - ", "Pitch de Negocio - "):
        if title.startswith(prefix):
            title = title[len(prefix):]
    centered = style.get("title_align") == "center"
    pdf.setFillColor(colors.white)
    pdf.setFont(_font_for(language, True), 40)
    title_y = height - 110
    for line in _wrap_text_lines(title, max_chars=28)[:2]:
        if centered:
            pdf.drawCentredString(width / 2, title_y, line)
        else:
            pdf.drawString(28, title_y, line)
        title_y -= 50

    # Accent underline
    pdf.setFillColor(palette["accent"])
    underline_x = (width - 80) / 2 if centered else 28
    pdf.rect(underline_x, title_y + 8, 80, 3, stroke=0, fill=1)
    title_y -= 18

    # ── Tagline / slogan ──
    slogan = _safe_str((slide.get("bullets") or [""])[0], "")
    pdf.setFillColor(palette["muted"])
    pdf.setFont(_font_for(language), 14)
    for line in _wrap_text_lines(_truncate_text(slogan, 160), max_chars=62)[:3]:
        if centered:
            pdf.drawCentredString(width / 2, title_y, line)
        else:
            pdf.drawString(28, title_y, line)
        title_y -= 20

    # ── Info card (lower section) ──
    card_w = width * 0.58
    card_x = (width - card_w) / 2 if centered else 28
    card_y, card_h = 46, 112
    corner = style["corner"]

    # ── Funding snapshot chips: fills the gap between the tagline and the
    # info card with a preview of the ask, using whatever room the (variable
    # length) tagline left behind. Skipped gracefully if there isn't enough
    # vertical room, or if the deck has no investment data yet. ──
    investment = slide.get("investment") or {}
    stat_chips = []
    funding = _safe_str(investment.get("funding_goal"), "")
    runway = _safe_str(investment.get("runway_months"), "") or _safe_str(investment.get("key_milestones"), "")
    if funding:
        stat_chips.append((t.get("kpi_goal", "GOAL"), funding))
    if runway:
        stat_chips.append((t.get("kpi_runway", "RUNWAY"), runway))

    card_top = card_y + card_h
    strip_top = title_y - 6
    if stat_chips and strip_top - card_top > 40:
        strip_h = min(46, strip_top - card_top - 8)
        strip_y = card_top + 8
        n = len(stat_chips)
        gap = 8
        chip_w = (card_w - gap * (n - 1)) / n
        chip_corner = min(8, corner) if corner else 0
        for i, (label, value) in enumerate(stat_chips):
            cx0 = card_x + i * (chip_w + gap)
            pdf.setFillColor(_with_alpha(palette["card"], 0.6))
            pdf.roundRect(cx0, strip_y, chip_w, strip_h, chip_corner, stroke=0, fill=1)
            pdf.setStrokeColor(_with_alpha(palette["accent"], 0.35))
            pdf.setLineWidth(0.8)
            pdf.roundRect(cx0, strip_y, chip_w, strip_h, chip_corner, stroke=1, fill=0)
            pdf.setFillColor(palette["accent"])
            pdf.setFont(_font_for(language, True), 7.5)
            pdf.drawString(cx0 + 10, strip_y + strip_h - 16, label)
            pdf.setFillColor(colors.white)
            value_font = 9.5 if strip_h >= 40 else 10.5
            pdf.setFont(_font_for(language), value_font)
            max_lines = 2 if strip_h >= 40 else 1
            val_lines = _wrap_text_lines(_truncate_text(value, 90), max_chars=max(10, int(chip_w / 4.6)))[:max_lines]
            base_y = strip_y + strip_h - 30
            for li, vline in enumerate(val_lines):
                pdf.drawString(cx0 + 10, base_y - li * (value_font + 2), vline)

    pdf.setFillColor(_with_alpha(palette["card"], 0.9))
    pdf.roundRect(card_x, card_y, card_w, card_h, corner, stroke=0, fill=1)
    pdf.setStrokeColor(_with_alpha(palette["band"], 0.5))
    pdf.setLineWidth(1)
    pdf.roundRect(card_x, card_y, card_w, card_h, corner, stroke=1, fill=0)

    # "PITCH DECK EXECUTIVO" tag
    tag_w = 180
    pdf.setFillColor(palette["tag_bg"])
    pdf.roundRect(card_x + 14, card_y + card_h - 28, tag_w, 22, min(11, corner), stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont(_font_for(language, True), 8.5)
    pdf.drawString(card_x + 22, card_y + card_h - 18, t.get("exec_confidential_tag", "EXECUTIVE PITCH DECK  ·  CONFIDENTIAL"))

    # Metadata lines
    pdf.setFont(_font_for(language), 10)
    pdf.setFillColor(palette["muted"])
    meta_y = card_y + card_h - 52
    pdf.drawString(card_x + 14, meta_y, f"Startup:  {startup_name}")
    meta_y -= 18
    pdf.setFillColor(_with_alpha(palette["text"], 0.7))
    subtitle = _safe_str(slide.get("subtitle"), t.get("cover_subtitle_default", "Executive presentation for investors"))
    pdf.drawString(card_x + 14, meta_y, f"{subtitle}")
    meta_y -= 18
    pdf.setFillColor(_with_alpha(palette["muted"], 0.8))
    context_label = _safe_str(slide.get("context_label"), "")
    template_label = template.upper() if template else "ORBIT"
    context_word = t.get("context_label", "Context")
    pdf.drawString(card_x + 14, meta_y, f"{context_word}: {context_label}  ·  Template: {template_label}")
    meta_y -= 18
    generated_word = t.get("generated_label", "Generated on")
    pdf.drawString(card_x + 14, meta_y, f"{generated_word}: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    _draw_footer_bar(pdf, width, page, total, engine, key, palette, language)


def _render_investment_slide(pdf: canvas.Canvas, width: float, height: float,
                              slide: dict, palette: dict, template: str, seed: int,
                              page: int, total: int, engine: str, key: str,
                              language: str = _DEFAULT_LANGUAGE) -> None:
    """Dedicated layout for investment/funding slides with KPI boxes."""
    t = _deck_strings(language)
    style = _style_for(template)
    pdf.setFillColor(palette["bg"])
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    _draw_template_bg(pdf, width, height, palette, template, seed)
    _draw_left_stripe(pdf, height, palette)
    _draw_top_band(pdf, width, height, palette,
                    slide.get("subtitle") or t.get("investment_title", "Fundraising & Use of Capital"),
                    language, style=style)
    _draw_slide_number_watermark(pdf, width, height, page, palette, language)

    title = _safe_str(slide.get("title"), t.get("investment_default_title", "Fundraising"))
    pdf.setFillColor(palette["text"])
    pdf.setFont(_font_for(language, True), 26)
    pdf.drawString(22, height - 82, title)
    pdf.setFillColor(palette["accent"])
    pdf.rect(22, height - 90, min(120, len(title) * 8), 3, stroke=0, fill=1)
    _draw_topic_icon(pdf, width - 52, height - 82, 26, "funding", palette["band"], colors.white)

    bullets = slide.get("bullets") or []
    investment = slide.get("investment") or {}

    # ── KPI boxes row ──
    kpi_items = []
    funding = _safe_str(investment.get("funding_goal"), "")
    runway = _safe_str(investment.get("runway_months"), "")
    milestones = _safe_str(investment.get("key_milestones"), "")
    if funding:
        kpi_items.append((t.get("kpi_goal", "GOAL"), funding))
    if runway:
        kpi_items.append((t.get("kpi_runway", "RUNWAY"), runway))
    elif bullets:
        kpi_items.append((t.get("kpi_allocation", "ALLOCATION"), _truncate_text(bullets[0], 60)))

    n_kpis = max(1, len(kpi_items))
    kpi_w = (width - 44 - (n_kpis - 1) * 14) / n_kpis
    kpi_y = height - 180
    kpi_h = 68
    kpi_corner = min(10, style["corner"]) if style["corner"] else 0
    for i, (label, value) in enumerate(kpi_items):
        kx = 22 + i * (kpi_w + 14)
        pdf.setFillColor(_with_alpha(palette["card"], 0.95))
        pdf.roundRect(kx, kpi_y, kpi_w, kpi_h, kpi_corner, stroke=0, fill=1)
        pdf.setFillColor(palette["band"])
        pdf.roundRect(kx, kpi_y + kpi_h - 28, kpi_w, 28, min(kpi_corner, 11), stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont(_font_for(language, True), 9)
        pdf.drawCentredString(kx + kpi_w / 2, kpi_y + kpi_h - 12, label)
        pdf.setFillColor(palette["text"])
        pdf.setFont(_font_for(language), 9.5)
        for j, vline in enumerate(_wrap_text_lines(_truncate_text(value, 90), max_chars=int(kpi_w / 6))[:2]):
            pdf.drawCentredString(kx + kpi_w / 2, kpi_y + kpi_h - 46 - j * 13, vline)

    # ── Capital allocation: a real stacked bar when the free-text use-of-funds
    # summary parses into percentages; otherwise a decorative 4-phase
    # deployment timeline gives the slide the same illustrative rhythm
    # either way, instead of just falling back to a plain bullet list. ──
    use_of_funds_text = _safe_str(investment.get("use_of_funds"), "")
    allocation_items = _parse_allocation(use_of_funds_text)
    allocation_label = t.get("allocation_prefix", "Allocation")
    funding_label = t.get("funding_goal_prefix", "Funding goal")

    # `bullets` already carries every investment field as plain text
    # (funding/allocation/runway/milestones); drop whichever of those are
    # about to be shown again as a KPI box, the allocation chart, or the
    # milestones highlight below, so nothing repeats twice on the slide.
    already_shown = {v for v in (funding, runway) if v}
    alloc_bullets = [
        b for b in bullets
        if _safe_str(b, "") not in already_shown
        and not _safe_str(b, "").startswith(f"{funding_label}:")
    ]

    body_y = kpi_y - 24
    if len(allocation_items) >= 2:
        alloc_bullets = [b for b in alloc_bullets if not _safe_str(b, "").startswith(f"{allocation_label}:")]
        pdf.setFillColor(palette["accent"])
        pdf.setFont(_font_for(language, True), 9)
        pdf.drawString(22, kpi_y - 16, t.get("allocation_chart_title", "USE OF CAPITAL"))
        body_y = _draw_allocation_bar(pdf, 22, kpi_y - 40, width - 44, allocation_items, palette, language) - 6
    else:
        # ── Decorative capital-deployment timeline (illustrative, not a
        #    literal projection of exact dates) — shown only when there is no
        #    real percentage breakdown to chart instead. ──
        timeline_y = kpi_y - 22
        timeline_x0, timeline_x1 = 26, width - 26
        pdf.setStrokeColor(_with_alpha(palette["accent"], 0.4))
        pdf.setLineWidth(1.6)
        pdf.line(timeline_x0, timeline_y, timeline_x1, timeline_y)
        phase_labels = [
            t.get("timeline_phase_deploy", "Deploy capital"),
            t.get("timeline_phase_execute", "Execute plan"),
            t.get("timeline_phase_milestone", "Hit milestones"),
            t.get("timeline_phase_raise", "Next round"),
        ]
        n_phases = len(phase_labels)
        for i, label in enumerate(phase_labels):
            px = timeline_x0 + (timeline_x1 - timeline_x0) * (i / (n_phases - 1))
            _draw_marker_shape(pdf, px, timeline_y, 4.5, style["marker"],
                                fill_color=palette["accent"] if i == 0 else palette["band"])
            pdf.setFillColor(_with_alpha(palette["text"], 0.85))
            pdf.setFont(_font_for(language), 7.5)
            pdf.drawCentredString(px, timeline_y - 13, label)
        body_y = timeline_y - 30

    if milestones:
        alloc_bullets = [b for b in alloc_bullets if _safe_str(b, "") != milestones]
        alloc_bullets = [milestones] + alloc_bullets

    for i, bullet in enumerate(alloc_bullets[:6], start=1):
        if body_y < 46:
            break
        body_y = _draw_single_bullet(pdf, bullet, 22, body_y, width - 44, palette, 10.5,
                                      language=language, index=i, max_lines=4, marker_shape=style["marker"])

    _draw_progress_dots(pdf, width, page, total, palette)
    _draw_footer_bar(pdf, width, page, total, engine, key, palette, language)


def _render_content_slide(pdf: canvas.Canvas, width: float, height: float,
                           slide: dict, palette: dict, layout: str, template: str, seed: int,
                           page: int, total: int, engine: str, key: str,
                           language: str = _DEFAULT_LANGUAGE) -> None:
    t = _deck_strings(language)
    style = _style_for(template)
    pdf.setFillColor(palette["bg"])
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    _draw_template_bg(pdf, width, height, palette, template, seed)
    _draw_left_stripe(pdf, height, palette)

    title = _safe_str(slide.get("title"), t.get("slide_default_title", "Slide"))
    subtitle = _safe_str(slide.get("subtitle"), "")
    bullets = [str(b).strip() for b in (slide.get("bullets") or []) if str(b).strip()]

    band_label = subtitle or title
    _draw_top_band(pdf, width, height, palette, band_label, language, style=style)
    _draw_slide_number_watermark(pdf, width, height, page, palette, language)

    # Title
    centered = style["title_align"] == "center"
    pdf.setFillColor(palette["text"])
    pdf.setFont(_font_for(language, True), 28)
    title_y = height - 82
    for line in _wrap_text_lines(title, max_chars=44)[:1]:
        if centered:
            pdf.drawCentredString(width / 2, title_y, line)
        else:
            pdf.drawString(22, title_y, line)

    # Accent underline
    pdf.setFillColor(palette["accent"])
    underline_x = (width - 60) / 2 if centered else 22
    pdf.rect(underline_x, title_y - 9, 60, 2.5, stroke=0, fill=1)

    # Topic icon badge, top-right of the title band
    _draw_topic_icon(pdf, width - 52, height - 82, 26, _infer_topic_icon(title), palette["band"], colors.white)

    # ── Main content card ──
    card_x = 22
    card_y = 46
    card_w = width - 44
    card_h = height - 150
    corner = style["corner"]
    pdf.setFillColor(_with_alpha(palette["card"], 0.85))
    pdf.roundRect(card_x, card_y, card_w, card_h, corner, stroke=0, fill=1)
    pdf.setStrokeColor(_with_alpha(palette["band"], 0.3))
    pdf.setLineWidth(0.8)
    pdf.roundRect(card_x, card_y, card_w, card_h, corner, stroke=1, fill=0)

    mode = (layout or "focus").strip().lower()

    if mode == "split" and len(bullets) >= 2:
        divider_x = card_x + card_w * 0.54
        pdf.setStrokeColor(_with_alpha(palette["accent"], 0.35))
        pdf.setLineWidth(1.0)
        pdf.line(divider_x, card_y + 16, divider_x, card_y + card_h - 36)

        # Column headers
        pdf.setFillColor(palette["accent"])
        pdf.setFont(_font_for(language, True), 9.5)
        pdf.drawString(card_x + 16, card_y + card_h - 26, t.get("col_theses", "KEY THESES"))
        pdf.drawString(divider_x + 14, card_y + card_h - 26, t.get("col_execution_notes", "EXECUTION NOTES"))

        half = max(1, (len(bullets) + 1) // 2)
        left_bullets = bullets[:half]
        right_bullets = bullets[half:]

        left_body_w = divider_x - card_x - 30
        right_body_w = card_x + card_w - divider_x - 30

        def _column_tier(count: int) -> tuple[float, int]:
            if count <= 1:
                return 12.5, 7
            if count <= 2:
                return 11.5, 5
            return 10.0, 3

        left_font, left_lines = _column_tier(len(left_bullets[:5]))
        right_font, right_lines = _column_tier(len(right_bullets[:5]))

        ly = card_y + card_h - 46
        for i, b in enumerate(left_bullets[:5], start=1):
            if ly < card_y + 26:
                break
            ly = _draw_single_bullet(pdf, b, card_x + 16, ly, left_body_w, palette, left_font,
                                      language=language, index=i, max_lines=left_lines, marker_shape=style["marker"])

        ry = card_y + card_h - 46
        for i, b in enumerate(right_bullets[:5], start=1):
            if ry < card_y + 26:
                break
            ry = _draw_single_bullet(pdf, b, divider_x + 14, ry, right_body_w, palette, right_font,
                                      language=language, index=i, max_lines=right_lines, marker_shape=style["marker"])

    elif mode == "cards" and bullets:
        # A grid of individually-boxed cards instead of one stacked list —
        # chunking each point into its own tile reads as more explicit and
        # naturally fills a wide card even with just a handful of points.
        n = min(6, len(bullets))
        cols = 1 if n == 1 else 2
        rows = max(1, math.ceil(n / cols))
        gap = 10
        grid_x = card_x + 14
        grid_top = card_y + card_h - 18
        grid_w = card_w - 28
        grid_h = card_h - 30
        cell_w = (grid_w - gap * (cols - 1)) / cols
        cell_h = (grid_h - gap * (rows - 1)) / rows
        cell_corner = min(10, corner) if corner else 0
        marker_r = 10.0

        for idx, b in enumerate(bullets[:6]):
            col = idx % cols
            row = idx // cols
            bx = grid_x + col * (cell_w + gap)
            by = grid_top - (row + 1) * cell_h - row * gap
            pdf.setFillColor(_with_alpha(palette["bg"], 0.35))
            pdf.roundRect(bx, by, cell_w, cell_h, cell_corner, stroke=0, fill=1)
            pdf.setStrokeColor(_with_alpha(palette["accent"], 0.3))
            pdf.setLineWidth(0.7)
            pdf.roundRect(bx, by, cell_w, cell_h, cell_corner, stroke=1, fill=0)

            marker_cx, marker_cy = bx + 20, by + cell_h - 20
            _draw_marker_shape(pdf, marker_cx, marker_cy, marker_r, style["marker"], fill_color=palette["band"])
            pdf.setFillColor(colors.white)
            pdf.setFont(_font_for(language, True), 8.5)
            pdf.drawCentredString(marker_cx, marker_cy - 3, str(idx + 1))

            text_x = bx + 38
            text_w = cell_w - 48
            font_sz = 9.3
            max_chars = max(14, int(text_w / (font_sz * 0.55)))
            lines_avail = max(2, int((cell_h - 24) / (font_sz + 3)))
            char_budget = max(160, lines_avail * max_chars + 30)
            wrapped = _wrap_text_lines(_truncate_text(_safe_str(b, ""), char_budget), max_chars=max_chars)[:lines_avail]
            pdf.setFillColor(palette["text"])
            pdf.setFont(_font_for(language), font_sz)
            ty = by + cell_h - 24
            for line in wrapped:
                pdf.drawString(text_x, ty, line)
                ty -= font_sz + 3

    elif mode == "timeline":
        line_x = card_x + 74
        top_y = card_y + card_h - 50
        bot_y = card_y + 28
        # Vertical timeline line
        pdf.setStrokeColor(_with_alpha(palette["accent"], 0.45))
        pdf.setLineWidth(2.5)
        pdf.line(line_x, bot_y, line_x, top_y)

        pdf.setFillColor(palette["accent"])
        pdf.setFont(_font_for(language, True), 9.5)
        pdf.drawString(card_x + 16, card_y + card_h - 28, t.get("narrative_flow", "NARRATIVE FLOW"))

        # Steps are spaced into even slots across the whole available height
        # (not just stacked tightly from the top), so a short list of steps
        # still uses the full card instead of leaving its lower half empty.
        n_steps = max(1, min(6, len(bullets)))
        available_h = (top_y - 10) - bot_y
        slot_h = available_h / n_steps
        text_w = (card_x + card_w - 18) - (line_x + 18)
        text_font = 10.5
        max_chars = max(30, int(text_w / (text_font * 0.52)))
        slot_lines = max(1, int((slot_h - 6) / 13))

        for idx, raw in enumerate(bullets[:n_steps], start=1):
            step_y = top_y - 10 - (idx - 1) * slot_h
            # Step marker with number
            _draw_marker_shape(pdf, line_x, step_y + 5, 9, style["marker"], fill_color=palette["band"])
            pdf.setFillColor(colors.white)
            pdf.setFont(_font_for(language, True), 7.5)
            pdf.drawCentredString(line_x, step_y + 2, str(idx))
            # Text — wrapped to the card's actual remaining width, and to as
            # many lines as its even-height slot allows, so the timeline
            # uses the whole slide instead of just its left third.
            pdf.setFillColor(palette["text"])
            pdf.setFont(_font_for(language), text_font)
            txt = _truncate_text(_safe_str(raw, ""), max(240, max_chars * slot_lines + 40))
            step_lines = _wrap_text_lines(txt, max_chars=max_chars)[:slot_lines]
            for i, line in enumerate(step_lines):
                pdf.drawString(line_x + 18, step_y - i * 13, line)
            step_y -= max(30, len(step_lines) * 13 + 14)

    else:  # focus (default)
        pdf.setFillColor(palette["accent"])
        pdf.setFont(_font_for(language, True), 9.5)
        pdf.drawString(card_x + 16, card_y + card_h - 26, t.get("key_points", "KEY POINTS"))

        # Fewer bullets get a larger type size AND a bigger per-bullet line
        # budget — the enrichment step writes full, detailed sentences, so
        # a short bullet list should show them in full rather than clipping
        # to a fixed line count that leaves the card looking sparse.
        n = max(1, len(bullets[:7]))
        if n == 1:
            bullet_font, max_lines = 16.5, 11
        elif n == 2:
            bullet_font, max_lines = 14.0, 7
        elif n <= 4:
            bullet_font, max_lines = 12.0, 4
        else:
            bullet_font, max_lines = 10.5, 3

        if n <= 2:
            # A slide carrying only one or two big ideas gets a large
            # translucent quote mark anchored to the card's corner so it
            # doesn't read as empty, drawn first so bullet text sits on top.
            pdf.setFillColor(_with_alpha(palette["shape2"], 0.5))
            pdf.setFont(_font_for(language, True), 170)
            pdf.drawString(card_x + card_w - 150, card_y + 6, "”")

        top_y = card_y + card_h - 50
        bottom_y = card_y + 26
        body_y = top_y
        if n == 1:
            # A single paragraph rarely fills the whole card even at a
            # large size; centering it in the available area (instead of
            # pinning it to the top) reads as a deliberate layout rather
            # than a slide that ran out of content.
            preview_w = card_w - 32
            preview_chars = max(20, int(preview_w / (bullet_font * 0.58)))
            preview_budget = max(220, max_lines * preview_chars + 40)
            preview_lines = _wrap_text_lines(_truncate_text(_safe_str(bullets[0], ""), preview_budget),
                                              max_chars=preview_chars)[:max_lines]
            text_h = len(preview_lines) * (bullet_font + 2)
            body_y = min(top_y, bottom_y + (top_y - bottom_y + text_h) / 2)

        for i, b in enumerate(bullets[:7], start=1):
            if body_y < card_y + 26:
                break
            body_y = _draw_single_bullet(pdf, b, card_x + 16, body_y, card_w - 32, palette,
                                          bullet_font, language=language, index=i, max_lines=max_lines,
                                          marker_shape=style["marker"])

    _draw_progress_dots(pdf, width, page, total, palette)
    _draw_footer_bar(pdf, width, page, total, engine, key, palette, language)


def _render_closing_slide(pdf: canvas.Canvas, width: float, height: float,
                           slide: dict, palette: dict, template: str, seed: int,
                           page: int, total: int, engine: str, key: str,
                           language: str = _DEFAULT_LANGUAGE) -> None:
    """A dedicated, centered 'thank you' finale instead of one more bulleted card."""
    t = _deck_strings(language)
    style = _style_for(template)
    pdf.setFillColor(palette["bg"])
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    _draw_template_bg(pdf, width, height, palette, template, seed)
    _draw_left_stripe(pdf, height, palette)

    if _LOGO_ASPECT:
        logo_h = 26
        logo_w = logo_h * _LOGO_ASPECT
        pdf.drawImage(LOGO_PATH, (width - logo_w) / 2, height - 70, width=logo_w, height=logo_h,
                       mask="auto", preserveAspectRatio=True)

    title = _safe_str(slide.get("title"), t.get("closing_title", "Conclusion"))
    pdf.setFillColor(palette["text"])
    pdf.setFont(_font_for(language, True), 34)
    pdf.drawCentredString(width / 2, height * 0.62, title)

    pdf.setFillColor(palette["accent"])
    pdf.rect(width / 2 - 40, height * 0.62 - 16, 80, 3, stroke=0, fill=1)

    body_lines = []
    for b in (slide.get("bullets") or []):
        body_lines.extend(_wrap_text_lines(_truncate_text(_safe_str(b, ""), 500), max_chars=72)[:7])
    y = height * 0.62 - 40
    pdf.setFillColor(palette["muted"])
    pdf.setFont(_font_for(language), 12.5)
    for line in body_lines[:7]:
        pdf.drawCentredString(width / 2, y, line)
        y -= 20

    cta = t.get("closing_cta", "Let's talk")
    cta_w = stringWidth(cta.upper(), _font_for(language, True), 10) + 48
    cta_x = width / 2 - cta_w / 2
    cta_y = max(70, y - 20)
    pdf.setFillColor(palette["tag_bg"])
    pdf.roundRect(cta_x, cta_y, cta_w, 30, min(15, style["corner"] + 4) if style["corner"] else 4, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont(_font_for(language, True), 10)
    pdf.drawCentredString(width / 2, cta_y + 11, cta.upper())

    _draw_footer_bar(pdf, width, page, total, engine, key, palette, language)


# ─────────────────────────────────────────────────────────────
#  Slide list builder
# ─────────────────────────────────────────────────────────────

def _build_pitch_slides(pitch_payload: dict, language: str = _DEFAULT_LANGUAGE) -> list[dict]:
    t = _deck_strings(language)
    title = _safe_str(pitch_payload.get("title"), t.get("deck_default_title", "Business Pitch"))
    slogan = _safe_str(pitch_payload.get("slogan"), t.get("deck_default_slogan", "An evolving value proposition."))
    startup_name = title
    for prefix in ("Pitch de Negócio - ", "Pitch de Negocio - "):
        if startup_name.startswith(prefix):
            startup_name = startup_name[len(prefix):]
    startup_name = startup_name.strip() or "Startup"

    investment = pitch_payload.get("investment") or {}

    slides = [{"kind": "cover", "title": title, "slogan": slogan,
                "startup_name": startup_name,
                "subtitle": t.get("cover_subtitle_default", "Executive presentation for investors"),
                "investment": investment}]

    elevator = _safe_str(pitch_payload.get("elevator_pitch"), "")
    if elevator:
        # Kept as a single full-text item (not pre-split into wrapped-line
        # fragments) so the renderer treats it as one coherent paragraph
        # with one number, instead of chopping it into several arbitrarily
        # numbered "bullets" at whatever column a line-wrap happened to end.
        slides.append({"kind": "content", "title": t.get("elevator_title", "Elevator Pitch"),
                        "subtitle": t.get("elevator_subtitle", "Core message in under 90 seconds"),
                        "bullets": [_truncate_text(elevator, 600)]})

    deck = pitch_payload.get("pitch_deck") or []
    if deck:
        for item in deck[:12]:
            if not isinstance(item, dict):
                continue
            bullets = [str(b).strip() for b in (item.get("bullets") or []) if str(b).strip()]
            if not bullets:
                bullets = [t.get("slide_no_info", "Information not available for this slide.")]
            slide_word = t.get("slide_word", "Slide")
            slides.append({"kind": "content",
                            "title": _safe_str(item.get("title"), t.get("slide_default_title", "Slide")),
                            "subtitle": f"{slide_word} {item.get('slide', '')}".strip(),
                            "bullets": bullets})
    else:
        for sec in (pitch_payload.get("sections") or [])[:10]:
            if not isinstance(sec, dict):
                continue
            content = _safe_str(sec.get("content"), t.get("section_no_content", "No content."))
            slides.append({"kind": "content",
                            "title": _safe_str(sec.get("title"), t.get("section_default_title", "Section")),
                            "subtitle": t.get("section_subtitle", "Strategic summary"),
                            "bullets": [_truncate_text(content, 600)]})

    # Script / roadmap slide
    script = pitch_payload.get("script_3min") or []
    if script:
        slides.append({"kind": "content",
                        "title": t.get("roadmap_title", "Presentation Roadmap"),
                        "subtitle": t.get("roadmap_subtitle", "Suggested sequence for a live presentation"),
                        "bullets": [f"{idx}. {item}" for idx, item in enumerate(script[:6], 1)]})

    # Investment slide (dedicated kind)
    funding = _safe_str(investment.get("funding_goal"), "")
    use_of_funds = _safe_str(investment.get("use_of_funds"), "")
    inv_bullets = []
    if funding:
        inv_bullets.append(f"{t.get('funding_goal_prefix', 'Funding goal')}: {funding}")
    if use_of_funds:
        inv_bullets.append(f"{t.get('allocation_prefix', 'Allocation')}: {use_of_funds}")
    for extra in ["runway_months", "key_milestones"]:
        val = _safe_str(investment.get(extra), "")
        if val:
            inv_bullets.append(val)
    slides.append({"kind": "investment",
                    "title": t.get("investment_title", "Fundraising & Use of Capital"),
                    "subtitle": t.get("investment_subtitle", "Financial plan for execution and scale"),
                    "bullets": inv_bullets,
                    "investment": investment})

    # Closing slide
    closing = _safe_str(pitch_payload.get("closing"),
                        t.get("closing_default", "Thank you. We are ready for the next steps of the fundraising process."))
    slides.append({"kind": "closing",
                    "title": t.get("closing_title", "Conclusion"),
                    "subtitle": t.get("closing_subtitle", "Final message to the investor"),
                    "bullets": [_truncate_text(closing, 500)]})

    return slides


# ─────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────

def export_pitch_pdf(
    pitch_payload: dict,
    output_path: str,
    *,
    design_mode: str = "auto_context",
    manual_template: str | None = None,
    language: str = _DEFAULT_LANGUAGE,
) -> str:
    from .constants import PITCH_DESIGN_MODE_AUTO
    from .design import normalize_pitch_design_options

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    slides = _build_pitch_slides(pitch_payload, language=language)
    page_size = landscape(A4)
    width, height = page_size
    total = len(slides)

    selected_mode, selected_template = normalize_pitch_design_options(design_mode, manual_template)
    design_profile = _build_pitch_design_profile(
        pitch_payload,
        design_mode=selected_mode,
        manual_template=selected_template,
    )
    template_name = str(design_profile.get("template_name", "orbit"))
    seed = int(design_profile.get("seed", 0))
    layout_options = design_profile.get("layout_options") or ["focus"]
    layout_seed = int(design_profile.get("layout_seed", 0))

    engine_used = _safe_str(pitch_payload.get("engine_used"), "local")
    uniqueness_key = _safe_str(pitch_payload.get("narrative_uniqueness_key"), "")
    context_label = _safe_str(design_profile.get("context_label"), "BusinessTech")

    pdf = canvas.Canvas(output_path, pagesize=page_size)

    for idx, slide in enumerate(slides, start=1):
        palette = _palette_for_slide(idx - 1, design_profile)
        kind = slide.get("kind", "content")

        if kind == "cover":
            slide["context_label"] = context_label
            _render_cover(pdf, width, height, slide, palette,
                          template_name, seed, idx, total, engine_used, uniqueness_key,
                          language=language)

        elif kind == "investment":
            _render_investment_slide(pdf, width, height, slide, palette,
                                     template_name, seed, idx, total, engine_used, uniqueness_key,
                                     language=language)

        elif kind == "closing":
            _render_closing_slide(pdf, width, height, slide, palette,
                                   template_name, seed, idx, total, engine_used, uniqueness_key,
                                   language=language)

        else:
            layout = layout_options[(layout_seed + idx - 1) % len(layout_options)]
            _render_content_slide(pdf, width, height, slide, palette, layout,
                                  template_name, seed, idx, total, engine_used, uniqueness_key,
                                  language=language)

        pdf.showPage()

    pdf.save()
    return output_path

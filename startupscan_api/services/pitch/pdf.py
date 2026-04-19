import hashlib
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .design import _build_pitch_design_profile, _mix_colors, _palette_for_slide, _with_alpha
from .enricher import _safe_str, _truncate_text, _wrap_text_lines

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


def _draw_left_stripe(pdf: canvas.Canvas, height: float, palette: dict) -> None:
    pdf.setFillColor(palette["band"])
    pdf.rect(0, 0, 7, height, stroke=0, fill=1)
    pdf.setFillColor(_with_alpha(palette["accent"], 0.6))
    pdf.rect(0, 0, 3, height, stroke=0, fill=1)


def _draw_top_band(pdf: canvas.Canvas, width: float, height: float,
                   palette: dict, label: str) -> None:
    band_h = 54
    pdf.setFillColor(palette["band"])
    pdf.rect(0, height - band_h, width, band_h, stroke=0, fill=1)
    # Accent highlight strip at top edge
    pdf.setFillColor(_with_alpha(palette["accent"], 0.5))
    pdf.rect(0, height - 3, width, 3, stroke=0, fill=1)
    # Label text inside band
    if label:
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(20, height - band_h + 20, label.upper())


def _draw_slide_number_watermark(pdf: canvas.Canvas, width: float, height: float,
                                  number: int, palette: dict) -> None:
    txt = str(number).zfill(2)
    pdf.setFillColor(_with_alpha(palette["shape2"], 0.55))
    pdf.setFont("Helvetica-Bold", 120)
    tw = stringWidth(txt, "Helvetica-Bold", 120)
    pdf.drawString(width - tw - 22, 14, txt)


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
                      engine: str, key: str, palette: dict) -> None:
    bar_h = 28
    pdf.setFillColor(_with_alpha(palette["bg"], 0.92))
    pdf.rect(0, 0, width, bar_h, stroke=0, fill=1)
    # thin separator line
    pdf.setStrokeColor(_with_alpha(palette["band"], 0.4))
    pdf.setLineWidth(0.5)
    pdf.line(0, bar_h, width, bar_h)

    pdf.setFillColor(_with_alpha(palette["muted"], 0.7))
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(20, 9, f"StartupScan · Motor: {engine} · ID: {key or '—'}")
    slide_txt = f"{page} / {total}"
    tw = stringWidth(slide_txt, "Helvetica", 7.5)
    pdf.drawString(width - tw - 20, 9, slide_txt)


def _draw_single_bullet(pdf: canvas.Canvas, text: str, x: float, y: float,
                         max_width: float, palette: dict, font_size: float = 10.5) -> float:
    """Draw one bullet item. Returns new y position after drawing."""
    dot_r = 2.6
    text_x = x + dot_r * 2 + 7
    max_chars = max(20, int(max_width / (font_size * 0.58)))
    wrapped = _wrap_text_lines(_truncate_text(_safe_str(text, ""), 220), max_chars=max_chars)[:3]
    if not wrapped:
        return y

    pdf.setFillColor(palette["accent"])
    pdf.circle(x + dot_r, y + font_size * 0.38, dot_r, stroke=0, fill=1)
    pdf.setFillColor(palette["text"])
    pdf.setFont("Helvetica", font_size)
    for i, line in enumerate(wrapped):
        pdf.drawString(text_x, y - i * (font_size + 2), line)
    return y - len(wrapped) * (font_size + 2) - 7


# ─────────────────────────────────────────────────────────────
#  Slide renderers
# ─────────────────────────────────────────────────────────────

def _render_cover(pdf: canvas.Canvas, width: float, height: float,
                  slide: dict, palette: dict, template: str, seed: int,
                  page: int, total: int, engine: str, key: str) -> None:
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

    # ── Company initials badge (top-right circle) ──
    startup_name = _safe_str(slide.get("startup_name"), "ST")
    initials = (startup_name[:2]).upper()
    badge_cx = width - 90
    badge_cy = height - 74
    pdf.setFillColor(palette["band"])
    pdf.circle(badge_cx, badge_cy, 52, stroke=0, fill=1)
    pdf.setFillColor(_with_alpha(palette["accent"], 0.3))
    pdf.circle(badge_cx, badge_cy, 52, stroke=0, fill=1)
    pdf.setStrokeColor(_with_alpha(palette["accent"], 0.7))
    pdf.setLineWidth(2)
    pdf.circle(badge_cx, badge_cy, 52, stroke=1, fill=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 28)
    tw = stringWidth(initials, "Helvetica-Bold", 28)
    pdf.drawString(badge_cx - tw / 2, badge_cy - 10, initials)
    pdf.setFont("Helvetica", 7.5)
    pdf.setFillColor(_with_alpha(colors.white, 0.6))
    pdf.drawCentredString(badge_cx, badge_cy - 24, "PITCH DECK")

    # ── Main title ──
    title = _safe_str(slide.get("title"), startup_name)
    # Remove boilerplate prefix
    for prefix in ("Pitch de Negócio - ", "Pitch de Negocio - "):
        if title.startswith(prefix):
            title = title[len(prefix):]
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 40)
    title_y = height - 110
    for line in _wrap_text_lines(title, max_chars=28)[:2]:
        pdf.drawString(28, title_y, line)
        title_y -= 50

    # Accent underline
    pdf.setFillColor(palette["accent"])
    pdf.rect(28, title_y + 8, 80, 3, stroke=0, fill=1)
    title_y -= 18

    # ── Tagline / slogan ──
    slogan = _safe_str((slide.get("bullets") or [""])[0], "")
    pdf.setFillColor(palette["muted"])
    pdf.setFont("Helvetica", 14)
    for line in _wrap_text_lines(_truncate_text(slogan, 160), max_chars=62)[:3]:
        pdf.drawString(28, title_y, line)
        title_y -= 20

    # ── Info card (lower section) ──
    card_x, card_y, card_w, card_h = 28, 46, width * 0.58, 112
    pdf.setFillColor(_with_alpha(palette["card"], 0.9))
    pdf.roundRect(card_x, card_y, card_w, card_h, 12, stroke=0, fill=1)
    pdf.setStrokeColor(_with_alpha(palette["band"], 0.5))
    pdf.setLineWidth(1)
    pdf.roundRect(card_x, card_y, card_w, card_h, 12, stroke=1, fill=0)

    # "PITCH DECK EXECUTIVO" tag
    tag_w = 180
    pdf.setFillColor(palette["tag_bg"])
    pdf.roundRect(card_x + 14, card_y + card_h - 28, tag_w, 22, 5, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(card_x + 22, card_y + card_h - 18, "PITCH DECK EXECUTIVO  ·  CONFIDENCIAL")

    # Metadata lines
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(palette["muted"])
    meta_y = card_y + card_h - 52
    pdf.drawString(card_x + 14, meta_y, f"Startup:  {startup_name}")
    meta_y -= 18
    pdf.setFillColor(_with_alpha(palette["text"], 0.7))
    subtitle = _safe_str(slide.get("subtitle"), "Apresentação executiva para investidores")
    pdf.drawString(card_x + 14, meta_y, f"{subtitle}")
    meta_y -= 18
    pdf.setFillColor(_with_alpha(palette["muted"], 0.8))
    context_label = _safe_str(slide.get("context_label"), "")
    template_label = template.upper() if template else "ORBIT"
    pdf.drawString(card_x + 14, meta_y, f"Contexto: {context_label}  ·  Template: {template_label}")
    meta_y -= 18
    pdf.drawString(card_x + 14, meta_y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    _draw_footer_bar(pdf, width, page, total, engine, key, palette)


def _render_investment_slide(pdf: canvas.Canvas, width: float, height: float,
                              slide: dict, palette: dict, template: str, seed: int,
                              page: int, total: int, engine: str, key: str) -> None:
    """Dedicated layout for investment/funding slides with KPI boxes."""
    pdf.setFillColor(palette["bg"])
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    _draw_template_bg(pdf, width, height, palette, template, seed)
    _draw_left_stripe(pdf, height, palette)
    _draw_top_band(pdf, width, height, palette, slide.get("subtitle") or "Captação e Uso de Capital")
    _draw_slide_number_watermark(pdf, width, height, page, palette)

    title = _safe_str(slide.get("title"), "Captação")
    pdf.setFillColor(palette["text"])
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawString(22, height - 82, title)
    pdf.setFillColor(palette["accent"])
    pdf.rect(22, height - 90, min(120, len(title) * 8), 3, stroke=0, fill=1)

    bullets = slide.get("bullets") or []
    investment = slide.get("investment") or {}

    # ── KPI boxes row ──
    kpi_items = []
    funding = _safe_str(investment.get("funding_goal"), "")
    runway = _safe_str(investment.get("runway_months"), "")
    milestones = _safe_str(investment.get("key_milestones"), "")
    if funding:
        kpi_items.append(("META", funding))
    if runway:
        kpi_items.append(("RUNWAY", runway))
    elif bullets:
        kpi_items.append(("ALOCAÇÃO", _truncate_text(bullets[0], 60)))

    n_kpis = max(1, len(kpi_items))
    kpi_w = (width - 44 - (n_kpis - 1) * 14) / n_kpis
    kpi_y = height - 180
    kpi_h = 68
    for i, (label, value) in enumerate(kpi_items):
        kx = 22 + i * (kpi_w + 14)
        pdf.setFillColor(_with_alpha(palette["card"], 0.95))
        pdf.roundRect(kx, kpi_y, kpi_w, kpi_h, 10, stroke=0, fill=1)
        pdf.setFillColor(palette["band"])
        pdf.roundRect(kx, kpi_y + kpi_h - 28, kpi_w, 28, 10, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(kx + kpi_w / 2, kpi_y + kpi_h - 12, label)
        pdf.setFillColor(palette["text"])
        pdf.setFont("Helvetica", 9.5)
        for j, vline in enumerate(_wrap_text_lines(_truncate_text(value, 90), max_chars=int(kpi_w / 6))[:2]):
            pdf.drawCentredString(kx + kpi_w / 2, kpi_y + kpi_h - 46 - j * 13, vline)

    # ── Remaining bullets as allocation list ──
    alloc_bullets = bullets if not kpi_items else bullets[1:]
    if milestones:
        alloc_bullets = [milestones] + list(alloc_bullets)
    body_y = kpi_y - 24
    for bullet in alloc_bullets[:6]:
        if body_y < 46:
            break
        body_y = _draw_single_bullet(pdf, bullet, 22, body_y, width - 44, palette, 10.5)

    _draw_progress_dots(pdf, width, page, total, palette)
    _draw_footer_bar(pdf, width, page, total, engine, key, palette)


def _render_content_slide(pdf: canvas.Canvas, width: float, height: float,
                           slide: dict, palette: dict, layout: str, template: str, seed: int,
                           page: int, total: int, engine: str, key: str) -> None:
    pdf.setFillColor(palette["bg"])
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    _draw_template_bg(pdf, width, height, palette, template, seed)
    _draw_left_stripe(pdf, height, palette)

    title = _safe_str(slide.get("title"), "Slide")
    subtitle = _safe_str(slide.get("subtitle"), "")
    bullets = [str(b).strip() for b in (slide.get("bullets") or []) if str(b).strip()]

    band_label = subtitle or title
    _draw_top_band(pdf, width, height, palette, band_label)
    _draw_slide_number_watermark(pdf, width, height, page, palette)

    # Title
    pdf.setFillColor(palette["text"])
    pdf.setFont("Helvetica-Bold", 28)
    title_y = height - 82
    for line in _wrap_text_lines(title, max_chars=44)[:1]:
        pdf.drawString(22, title_y, line)

    # Accent underline
    pdf.setFillColor(palette["accent"])
    pdf.rect(22, title_y - 6, 60, 2.5, stroke=0, fill=1)

    # ── Main content card ──
    card_x = 22
    card_y = 46
    card_w = width - 44
    card_h = height - 150
    pdf.setFillColor(_with_alpha(palette["card"], 0.85))
    pdf.roundRect(card_x, card_y, card_w, card_h, 14, stroke=0, fill=1)
    pdf.setStrokeColor(_with_alpha(palette["band"], 0.3))
    pdf.setLineWidth(0.8)
    pdf.roundRect(card_x, card_y, card_w, card_h, 14, stroke=1, fill=0)

    mode = (layout or "focus").strip().lower()

    if mode == "split" and len(bullets) >= 2:
        divider_x = card_x + card_w * 0.54
        pdf.setStrokeColor(_with_alpha(palette["accent"], 0.35))
        pdf.setLineWidth(1.0)
        pdf.line(divider_x, card_y + 16, divider_x, card_y + card_h - 36)

        # Column headers
        pdf.setFillColor(palette["accent"])
        pdf.setFont("Helvetica-Bold", 9.5)
        pdf.drawString(card_x + 16, card_y + card_h - 26, "PRINCIPAIS TESES")
        pdf.drawString(divider_x + 14, card_y + card_h - 26, "NOTAS DE EXECUÇÃO")

        half = max(1, (len(bullets) + 1) // 2)
        left_bullets = bullets[:half]
        right_bullets = bullets[half:]

        left_body_w = divider_x - card_x - 30
        right_body_w = card_x + card_w - divider_x - 30

        ly = card_y + card_h - 46
        for b in left_bullets[:5]:
            if ly < card_y + 26:
                break
            ly = _draw_single_bullet(pdf, b, card_x + 16, ly, left_body_w, palette, 10)

        ry = card_y + card_h - 46
        for b in right_bullets[:5]:
            if ry < card_y + 26:
                break
            ry = _draw_single_bullet(pdf, b, divider_x + 14, ry, right_body_w, palette, 10)

    elif mode == "timeline":
        line_x = card_x + 74
        top_y = card_y + card_h - 50
        bot_y = card_y + 28
        # Vertical timeline line
        pdf.setStrokeColor(_with_alpha(palette["accent"], 0.45))
        pdf.setLineWidth(2.5)
        pdf.line(line_x, bot_y, line_x, top_y)

        pdf.setFillColor(palette["accent"])
        pdf.setFont("Helvetica-Bold", 9.5)
        pdf.drawString(card_x + 16, card_y + card_h - 28, "FLUXO DA NARRATIVA")

        step_y = top_y - 10
        for idx, raw in enumerate(bullets[:6], start=1):
            if step_y < bot_y + 8:
                break
            # Step circle with number
            pdf.setFillColor(palette["band"])
            pdf.circle(line_x, step_y + 5, 9, stroke=0, fill=1)
            pdf.setFillColor(colors.white)
            pdf.setFont("Helvetica-Bold", 7.5)
            pdf.drawCentredString(line_x, step_y + 2, str(idx))
            # Text
            pdf.setFillColor(palette["text"])
            pdf.setFont("Helvetica", 10)
            txt = _truncate_text(_safe_str(raw, ""), 170)
            for i, line in enumerate(_wrap_text_lines(txt, max_chars=55)[:2]):
                pdf.drawString(line_x + 18, step_y - i * 13, line)
            step_y -= max(30, len(_wrap_text_lines(txt, max_chars=55)[:2]) * 13 + 14)

    else:  # focus (default)
        pdf.setFillColor(palette["accent"])
        pdf.setFont("Helvetica-Bold", 9.5)
        pdf.drawString(card_x + 16, card_y + card_h - 26, "PONTOS-CHAVE")

        body_y = card_y + card_h - 48
        for b in bullets[:7]:
            if body_y < card_y + 26:
                break
            body_y = _draw_single_bullet(pdf, b, card_x + 16, body_y, card_w - 32, palette, 10.5)

    _draw_progress_dots(pdf, width, page, total, palette)
    _draw_footer_bar(pdf, width, page, total, engine, key, palette)


# ─────────────────────────────────────────────────────────────
#  Slide list builder
# ─────────────────────────────────────────────────────────────

def _build_pitch_slides(pitch_payload: dict) -> list[dict]:
    title = _safe_str(pitch_payload.get("title"), "Pitch de Negocio")
    slogan = _safe_str(pitch_payload.get("slogan"), "Proposta de valor em evolucao.")
    startup_name = title
    for prefix in ("Pitch de Negócio - ", "Pitch de Negocio - "):
        if startup_name.startswith(prefix):
            startup_name = startup_name[len(prefix):]
    startup_name = startup_name.strip() or "Startup"

    slides = [{"kind": "cover", "title": title, "slogan": slogan,
                "startup_name": startup_name,
                "subtitle": "Apresentação executiva para investidores"}]

    elevator = _safe_str(pitch_payload.get("elevator_pitch"), "")
    if elevator:
        slides.append({"kind": "content", "title": "Elevator Pitch",
                        "subtitle": "Mensagem central em até 90 segundos",
                        "bullets": _wrap_text_lines(_truncate_text(elevator, 480), max_chars=100)[:5]})

    deck = pitch_payload.get("pitch_deck") or []
    if deck:
        for item in deck[:12]:
            if not isinstance(item, dict):
                continue
            bullets = [str(b).strip() for b in (item.get("bullets") or []) if str(b).strip()]
            if not bullets:
                bullets = ["Informação não disponível para este slide."]
            slides.append({"kind": "content",
                            "title": _safe_str(item.get("title"), "Slide"),
                            "subtitle": f"Slide {item.get('slide', '')}".strip(),
                            "bullets": bullets})
    else:
        for sec in (pitch_payload.get("sections") or [])[:10]:
            if not isinstance(sec, dict):
                continue
            content = _safe_str(sec.get("content"), "Sem conteúdo.")
            slides.append({"kind": "content",
                            "title": _safe_str(sec.get("title"), "Seção"),
                            "subtitle": "Resumo estratégico",
                            "bullets": _wrap_text_lines(_truncate_text(content, 460), max_chars=100)[:5]})

    # Script / roadmap slide
    script = pitch_payload.get("script_3min") or []
    if script:
        slides.append({"kind": "content",
                        "title": "Roteiro de Apresentação",
                        "subtitle": "Sequência sugerida para apresentação ao vivo",
                        "bullets": [f"{idx}. {item}" for idx, item in enumerate(script[:6], 1)]})

    # Investment slide (dedicated kind)
    investment = pitch_payload.get("investment") or {}
    funding = _safe_str(investment.get("funding_goal"), "")
    use_of_funds = _safe_str(investment.get("use_of_funds"), "")
    inv_bullets = []
    if funding:
        inv_bullets.append(f"Meta de captação: {funding}")
    if use_of_funds:
        inv_bullets.append(f"Alocação: {use_of_funds}")
    for extra in ["runway_months", "key_milestones"]:
        val = _safe_str(investment.get(extra), "")
        if val:
            inv_bullets.append(val)
    slides.append({"kind": "investment",
                    "title": "Captação e Uso de Capital",
                    "subtitle": "Plano financeiro para execução e escala",
                    "bullets": inv_bullets,
                    "investment": investment})

    # Closing slide
    closing = _safe_str(pitch_payload.get("closing"),
                        "Obrigado. Estamos prontos para os próximos passos da captação.")
    slides.append({"kind": "content",
                    "title": "Conclusão",
                    "subtitle": "Mensagem final ao investidor",
                    "bullets": _wrap_text_lines(_truncate_text(closing, 460), max_chars=100)[:5]})

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
) -> str:
    from .constants import PITCH_DESIGN_MODE_AUTO
    from .design import normalize_pitch_design_options

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    slides = _build_pitch_slides(pitch_payload)
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
                          template_name, seed, idx, total, engine_used, uniqueness_key)

        elif kind == "investment":
            _render_investment_slide(pdf, width, height, slide, palette,
                                     template_name, seed, idx, total, engine_used, uniqueness_key)

        else:
            layout = layout_options[(layout_seed + idx - 1) % len(layout_options)]
            _render_content_slide(pdf, width, height, slide, palette, layout,
                                  template_name, seed, idx, total, engine_used, uniqueness_key)

        pdf.showPage()

    pdf.save()
    return output_path

import colorsys
import hashlib
import json

from reportlab.lib import colors

from .constants import PITCH_DESIGN_MODE_AUTO, PITCH_DESIGN_MODE_CHOICES, PITCH_DESIGN_MODE_MANUAL, PITCH_MANUAL_TEMPLATE_CHOICES
from .enricher import _safe_str

# ──────────────────────────────────────────────────────────────
# Brand-quality hex palettes per industry context.
# All palettes stay within the StartupScanAI brand family (near-black
# backgrounds, warm orange/gold/bronze accents) instead of the previous
# per-industry hues (blue, green, violet, cyan, pink...), which read as
# off-brand once the product identity moved to orange/black/white.
# Each entry: (bg, card, band, accent, shape1, shape2, highlight)
# ──────────────────────────────────────────────────────────────
_CONTEXT_PALETTES = {
    "fintech": {
        "bg":        colors.HexColor("#0D0E12"),
        "card":      colors.HexColor("#15171B"),
        "band":      colors.HexColor("#F5580D"),
        "accent":    colors.HexColor("#FF8A4D"),
        "highlight": colors.HexColor("#FFD9BC"),
        "shape1":    colors.HexColor("#1C1310"),
        "shape2":    colors.HexColor("#241505"),
        "text":      colors.HexColor("#FFF6F0"),
        "muted":     colors.HexColor("#C99B7E"),
        "tag_bg":    colors.HexColor("#F5580D"),
    },
    "saude": {
        "bg":        colors.HexColor("#0D0E12"),
        "card":      colors.HexColor("#171310"),
        "band":      colors.HexColor("#D4931F"),
        "accent":    colors.HexColor("#FCD34D"),
        "highlight": colors.HexColor("#FEF3C7"),
        "shape1":    colors.HexColor("#1C1A00"),
        "shape2":    colors.HexColor("#282400"),
        "text":      colors.HexColor("#FFFBEB"),
        "muted":     colors.HexColor("#C6AC72"),
        "tag_bg":    colors.HexColor("#D4931F"),
    },
    "educacao": {
        "bg":        colors.HexColor("#0D0E12"),
        "card":      colors.HexColor("#181310"),
        "band":      colors.HexColor("#B8720A"),
        "accent":    colors.HexColor("#E0A845"),
        "highlight": colors.HexColor("#F0D8A8"),
        "shape1":    colors.HexColor("#1C1310"),
        "shape2":    colors.HexColor("#241505"),
        "text":      colors.HexColor("#FDF3E5"),
        "muted":     colors.HexColor("#C4A170"),
        "tag_bg":    colors.HexColor("#B8720A"),
    },
    "energia": {
        "bg":        colors.HexColor("#0D0E12"),
        "card":      colors.HexColor("#201B00"),
        "band":      colors.HexColor("#D97706"),
        "accent":    colors.HexColor("#FCD34D"),
        "highlight": colors.HexColor("#FEF3C7"),
        "shape1":    colors.HexColor("#1C1A00"),
        "shape2":    colors.HexColor("#282400"),
        "text":      colors.HexColor("#FFFBEB"),
        "muted":     colors.HexColor("#B8A060"),
        "tag_bg":    colors.HexColor("#D97706"),
    },
    "logistica": {
        "bg":        colors.HexColor("#0D0E12"),
        "card":      colors.HexColor("#171410"),
        "band":      colors.HexColor("#C23F08"),
        "accent":    colors.HexColor("#FF8A4D"),
        "highlight": colors.HexColor("#FFD9BC"),
        "shape1":    colors.HexColor("#1C1310"),
        "shape2":    colors.HexColor("#241505"),
        "text":      colors.HexColor("#FFF3EA"),
        "muted":     colors.HexColor("#BB9376"),
        "tag_bg":    colors.HexColor("#C23F08"),
    },
    "agro": {
        "bg":        colors.HexColor("#0D0E12"),
        "card":      colors.HexColor("#161710"),
        "band":      colors.HexColor("#C2410C"),
        "accent":    colors.HexColor("#FB923C"),
        "highlight": colors.HexColor("#FED7AA"),
        "shape1":    colors.HexColor("#1B1610"),
        "shape2":    colors.HexColor("#241C05"),
        "text":      colors.HexColor("#FFF4EA"),
        "muted":     colors.HexColor("#C39A6E"),
        "tag_bg":    colors.HexColor("#C2410C"),
    },
    "retail": {
        "bg":        colors.HexColor("#0D0E12"),
        "card":      colors.HexColor("#181210"),
        "band":      colors.HexColor("#EA580C"),
        "accent":    colors.HexColor("#FDBA74"),
        "highlight": colors.HexColor("#FFEDD5"),
        "shape1":    colors.HexColor("#1C1310"),
        "shape2":    colors.HexColor("#251603"),
        "text":      colors.HexColor("#FFF5EC"),
        "muted":     colors.HexColor("#CBA07C"),
        "tag_bg":    colors.HexColor("#EA580C"),
    },
    "geral": {
        "bg":        colors.HexColor("#0D0E12"),
        "card":      colors.HexColor("#15171B"),
        "band":      colors.HexColor("#F5580D"),
        "accent":    colors.HexColor("#FF8A4D"),
        "highlight": colors.HexColor("#FFD9BC"),
        "shape1":    colors.HexColor("#171920"),
        "shape2":    colors.HexColor("#1C1310"),
        "text":      colors.HexColor("#FFF6F0"),
        "muted":     colors.HexColor("#C0A090"),
        "tag_bg":    colors.HexColor("#F5580D"),
    },
}


def normalize_pitch_design_options(design_mode: str | None, manual_template: str | None) -> tuple[str, str]:
    mode = _safe_str(design_mode, PITCH_DESIGN_MODE_AUTO).lower()
    valid_modes = {choice[0] for choice in PITCH_DESIGN_MODE_CHOICES}
    if mode not in valid_modes:
        mode = PITCH_DESIGN_MODE_AUTO

    template = _safe_str(manual_template, PITCH_MANUAL_TEMPLATE_CHOICES[0][0]).lower()
    valid_templates = {choice[0] for choice in PITCH_MANUAL_TEMPLATE_CHOICES}
    if template not in valid_templates:
        template = PITCH_MANUAL_TEMPLATE_CHOICES[0][0]
    return mode, template


def _hsv_color(hue_deg: float, saturation: float, value: float) -> colors.Color:
    h = (float(hue_deg) % 360.0) / 360.0
    s = max(0.0, min(1.0, float(saturation)))
    v = max(0.0, min(1.0, float(value)))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return colors.Color(r, g, b)


def _mix_colors(color_a: colors.Color, color_b: colors.Color, ratio: float) -> colors.Color:
    r = max(0.0, min(1.0, float(ratio)))
    return colors.Color(
        (color_a.red * (1 - r)) + (color_b.red * r),
        (color_a.green * (1 - r)) + (color_b.green * r),
        (color_a.blue * (1 - r)) + (color_b.blue * r),
    )


def _with_alpha(color: colors.Color, alpha: float) -> colors.Color:
    return colors.Color(color.red, color.green, color.blue, alpha)


def _collect_pitch_text_blob(pitch_payload: dict) -> str:
    bits = [
        _safe_str(pitch_payload.get("title"), ""),
        _safe_str(pitch_payload.get("slogan"), ""),
        _safe_str(pitch_payload.get("elevator_pitch"), ""),
        _safe_str(pitch_payload.get("closing"), ""),
    ]
    for section in (pitch_payload.get("sections", []) or []):
        bits.append(_safe_str(section.get("title"), ""))
        bits.append(_safe_str(section.get("content"), ""))
    for deck in (pitch_payload.get("pitch_deck", []) or []):
        bits.append(_safe_str(deck.get("title"), ""))
        for bullet in (deck.get("bullets", []) or []):
            bits.append(_safe_str(bullet, ""))
    return " ".join(bit for bit in bits if bit).lower()


def _infer_pitch_context(pitch_payload: dict) -> str:
    blob = _collect_pitch_text_blob(pitch_payload)
    contexts = {
        "fintech": ["fintech", "finance", "pagamento", "credito", "banco", "wallet", "fatura", "financeiro"],
        "saude": ["saude", "health", "clinica", "hospital", "medico", "paciente", "telemedicina", "terapia"],
        "educacao": ["educacao", "ensino", "aluno", "universidade", "escola", "edtech", "curso", "aprendizagem"],
        "energia": ["energia", "solar", "eletrica", "bateria", "sustentavel", "renovavel", "grid", "carbono"],
        "logistica": ["logistica", "supply", "cadeia", "transporte", "entrega", "estoque", "warehouse", "frete"],
        "agro": ["agro", "fazenda", "agricola", "agritech", "campo", "safra", "produtor", "colheita"],
        "retail": ["retail", "ecommerce", "loja", "consumidor", "varejo", "marketplace", "cliente final", "moda"],
    }
    scores = {name: sum(blob.count(w) for w in words) for name, words in contexts.items()}
    winner = max(scores, key=lambda k: scores[k]) if scores else "geral"
    return winner if scores.get(winner, 0) > 0 else "geral"


def _context_display_name(context_name: str) -> str:
    labels = {
        "fintech": "Fintech",
        "saude": "HealthTech",
        "educacao": "EdTech",
        "energia": "EnergyTech",
        "logistica": "LogTech",
        "agro": "AgriTech",
        "retail": "RetailTech",
        "geral": "BusinessTech",
    }
    return labels.get(context_name, "BusinessTech")


def _build_pitch_design_profile(
    pitch_payload: dict,
    *,
    design_mode: str = PITCH_DESIGN_MODE_AUTO,
    manual_template: str | None = None,
) -> dict:
    mode, normalized_template = normalize_pitch_design_options(design_mode, manual_template)
    context = _infer_pitch_context(pitch_payload)
    raw_signature = _safe_str(pitch_payload.get("narrative_uniqueness_key"), "")
    if not raw_signature:
        raw_signature = hashlib.sha256(
            json.dumps(pitch_payload or {}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:14]
    seed = int(hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:12], 16)

    template_by_context = {
        "fintech": ["grid", "orbit", "diagonal", "ribbon"],
        "saude": ["wave", "aurora", "orbit", "grid"],
        "educacao": ["diagonal", "grid", "wave", "ribbon"],
        "energia": ["wave", "diagonal", "aurora", "orbit"],
        "logistica": ["grid", "diagonal", "ribbon", "orbit"],
        "agro": ["wave", "grid", "aurora", "orbit"],
        "retail": ["orbit", "diagonal", "grid", "ribbon"],
        "geral": ["orbit", "grid", "wave", "diagonal", "aurora", "ribbon"],
    }
    layout_options = ["focus", "split", "timeline"]

    template_list = template_by_context.get(context, template_by_context["geral"])
    template_name = normalized_template if mode == PITCH_DESIGN_MODE_MANUAL else template_list[seed % len(template_list)]
    context_label = (
        f"{_context_display_name(context)} · Premium Manual"
        if mode == PITCH_DESIGN_MODE_MANUAL
        else _context_display_name(context)
    )

    base_palette = _CONTEXT_PALETTES.get(context, _CONTEXT_PALETTES["geral"])

    return {
        "context": context,
        "context_label": context_label,
        "seed": seed,
        "template_name": template_name,
        "layout_seed": seed % len(layout_options),
        "layout_options": layout_options,
        "design_mode": mode,
        "manual_template": normalized_template,
        "palette": base_palette,
    }


def _palette_for_slide(index: int, design_profile: dict) -> dict:
    base = design_profile.get("palette", _CONTEXT_PALETTES["geral"])
    seed = int(design_profile.get("seed", 0))
    # Slightly shift accent hue per slide for visual variety while keeping brand identity
    hue_shift = (index * 3 + (seed % 11)) / 360.0
    accent = base["accent"]
    shifted_accent = colors.Color(
        min(1.0, accent.red + hue_shift * 0.06),
        min(1.0, accent.green + hue_shift * 0.04),
        min(1.0, accent.blue + hue_shift * 0.02),
    )
    return {**base, "accent": shifted_accent}

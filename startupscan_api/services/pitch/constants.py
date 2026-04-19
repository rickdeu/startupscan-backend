PITCH_DESIGN_MODE_AUTO = "auto_context"
PITCH_DESIGN_MODE_MANUAL = "manual_premium"

PITCH_DESIGN_MODE_CHOICES = [
    (PITCH_DESIGN_MODE_AUTO, "Design automático por contexto (atual)"),
    (PITCH_DESIGN_MODE_MANUAL, "Design premium manual (template escolhido pelo usuário)"),
]

PITCH_MANUAL_TEMPLATE_CHOICES = [
    ("orbit", "Orbit Premium"),
    ("grid", "Grid Executive"),
    ("wave", "Wave Smooth"),
    ("diagonal", "Diagonal Corporate"),
    ("aurora", "Aurora Glass"),
    ("ribbon", "Ribbon Stage"),
]


def get_pitch_design_mode_choices() -> list[tuple[str, str]]:
    return list(PITCH_DESIGN_MODE_CHOICES)


def get_pitch_design_template_choices() -> list[tuple[str, str]]:
    return list(PITCH_MANUAL_TEMPLATE_CHOICES)

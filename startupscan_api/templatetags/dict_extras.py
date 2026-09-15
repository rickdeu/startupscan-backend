from django import template

from startupscan_api.utils.currency import format_currency_str, get_display_currency

register = template.Library()


@register.filter
def dict_get(mapping, key):
    if not isinstance(mapping, dict):
        return None
    return mapping.get(key)


@register.filter
def currency_display(amount_eur, language):
    """Formats an EUR-stored amount for display in the viewer's currency (see utils/currency.py)."""
    try:
        return format_currency_str(amount_eur, language)
    except (TypeError, ValueError):
        return amount_eur


@register.filter
def currency_code(language):
    """The 3-letter currency code shown for this viewer's language (see utils/currency.py)."""
    return get_display_currency(language)


@register.filter
def engine_label(ui_text, engine_code):
    """Resolves the analysis-page 'pitch_form_engine_<code>' i18n key for an engine."""
    if not isinstance(ui_text, dict):
        return engine_code
    return ui_text.get(f"pitch_form_engine_{engine_code}", engine_code)


@register.filter
def engine_desc(ui_text, engine_code):
    """Resolves the analysis-page 'pitch_form_engine_<code>_desc' i18n key for an engine."""
    if not isinstance(ui_text, dict):
        return ""
    return ui_text.get(f"pitch_form_engine_{engine_code}_desc", "")


@register.filter
def idea_engine_label(ui_text, engine_code):
    """Resolves the idea-builder 'idea_form_engine_<code>' i18n key for an engine."""
    if not isinstance(ui_text, dict):
        return engine_code
    return ui_text.get(f"idea_form_engine_{engine_code}", engine_code)

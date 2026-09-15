"""
Currency display helpers.

All financial figures (PitchAnalysis.revenue, burn_rate, ...) are stored in
EUR — the platform's canonical base currency. Reports/PDFs/pages display
that amount converted into whichever currency fits the viewer's UI
language:

  - "de" (German)                -> EUR  (Europe)
  - "pt" / "umb" (Angola market) -> AOA  (Kwanza)
  - everything else              -> USD

Exchange rates come from a free, keyless public API (open.er-api.com,
EUR-based, covers AOA unlike ECB-only feeds such as Frankfurter) and are
cached in-process for a few hours. If the API is unreachable, a static
fallback keeps report/PDF generation working without ever raising.
"""

import json
import logging
import time
import urllib.request

logger = logging.getLogger(__name__)

BASE_CURRENCY = "EUR"

CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "AOA": "Kz",
}

# Static, roughly-current EUR-based rates used only when the live API call
# fails and no cached rate is available yet.
_FALLBACK_RATES = {
    "EUR": 1.0,
    "USD": 1.16,
    "AOA": 1107.6,
}

_FX_API_URL = "https://open.er-api.com/v6/latest/EUR"
_CACHE_TTL_SECONDS = 12 * 60 * 60  # 12h

_cache = {"rates": None, "fetched_at": 0.0}

_LANGUAGE_CURRENCY_MAP = {
    "de": "EUR",
    "pt": "AOA",
    "umb": "AOA",
    "es": "USD",
    "en": "USD",
    "ru": "USD",
    "zh-hans": "USD",
}
_DEFAULT_DISPLAY_CURRENCY = "USD"


def _fetch_live_rates() -> dict | None:
    try:
        req = urllib.request.Request(_FX_API_URL, headers={"User-Agent": "StartupScanAI/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("result") != "success":
            return None
        rates = data.get("rates") or {}
        if "USD" not in rates or "AOA" not in rates:
            return None
        return {"EUR": 1.0, "USD": float(rates["USD"]), "AOA": float(rates["AOA"])}
    except Exception:
        logger.warning("Failed to fetch live exchange rates; using cached/fallback values.", exc_info=True)
        return None


def get_exchange_rates() -> dict:
    """EUR-based {currency: rate} for EUR/USD/AOA, cached in-process."""
    now = time.time()
    if _cache["rates"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL_SECONDS:
        return _cache["rates"]
    rates = _fetch_live_rates()
    if rates is None:
        return _cache["rates"] or _FALLBACK_RATES
    _cache["rates"] = rates
    _cache["fetched_at"] = now
    return rates


def get_display_currency(language: str | None) -> str:
    code = str(language or "").strip().lower().replace("_", "-")
    if code.startswith("zh"):
        code = "zh-hans"
    return _LANGUAGE_CURRENCY_MAP.get(code, _DEFAULT_DISPLAY_CURRENCY)


def convert_from_eur(amount_eur: float, currency: str) -> float:
    rates = get_exchange_rates()
    rate = rates.get(currency, rates.get(_DEFAULT_DISPLAY_CURRENCY, 1.0))
    return float(amount_eur or 0) * float(rate)


def format_currency(amount_eur: float, language: str | None) -> tuple[str, float]:
    """Returns (symbol, converted_amount) for an EUR amount shown to a viewer of `language`."""
    currency = get_display_currency(language)
    converted = convert_from_eur(amount_eur, currency)
    return CURRENCY_SYMBOLS.get(currency, currency), converted


def format_currency_str(amount_eur: float, language: str | None, decimals: int = 0) -> str:
    symbol, converted = format_currency(amount_eur, language)
    return f"{symbol} {converted:,.{decimals}f}"

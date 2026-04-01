from __future__ import annotations

from pathlib import Path


APP_NAME = "Coreo-Flow"
APP_NAME_ADMIN = f"{APP_NAME} – Admin"
APP_TAGLINE = "Arbeitszeitverwaltung"
COMPANY_NAME = "Steakhouse Piccolo"

_ROOT = Path(__file__).resolve().parents[1]
_ASSETS = _ROOT / "assets"

LOGO_PRIMARY = _ASSETS / "crewbase_logo_optimized.png"
LOGO_FALLBACK = _ASSETS / "piccolo_logo.jpeg"
ICON_PRIMARY = _ASSETS / "favicon.png"


def get_logo_path() -> str:
    for candidate in (LOGO_PRIMARY, LOGO_FALLBACK):
        if candidate.exists():
            return str(candidate)
    return ""


def get_icon_path() -> str:
    for candidate in (ICON_PRIMARY, LOGO_PRIMARY, LOGO_FALLBACK):
        if candidate.exists():
            return str(candidate)
    return "🔘"


# Backward-compatible aliases for existing modules.
BRAND_APP_NAME = APP_NAME
BRAND_APP_NAME_ADMIN = APP_NAME_ADMIN
BRAND_COMPANY_NAME = COMPANY_NAME
BRAND_NAME_FULL = COMPANY_NAME
BRAND_TAGLINE = APP_TAGLINE
BRAND_LOGO_IMAGE = get_logo_path()
BRAND_ICON_IMAGE = get_icon_path()


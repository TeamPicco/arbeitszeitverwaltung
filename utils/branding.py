from __future__ import annotations

from pathlib import Path


APP_NAME = "Coreo-Flow"
APP_NAME_ADMIN = f"{APP_NAME} – Admin"
APP_TAGLINE = "Integrated Business"
COMPANY_NAME = "Steakhouse Piccolo"

_ROOT = Path(__file__).resolve().parents[1]
_ASSETS = _ROOT / "assets"

LOGO_PRIMARY = _ASSETS / "coreo_flow_logo.png"
LOGO_PRIMARY_ALT_JPG = _ASSETS / "coreo_flow_logo.jpg"
LOGO_PRIMARY_ALT_JPEG = _ASSETS / "coreo_flow_logo.jpeg"
LOGO_FALLBACK = _ASSETS / "crewbase_logo_optimized.png"
LOGO_FALLBACK_LEGACY = _ASSETS / "piccolo_logo.jpeg"
ICON_PRIMARY = _ASSETS / "coreo_flow_icon.png"
ICON_FALLBACK = _ASSETS / "favicon.png"


def get_logo_path() -> str:
    for candidate in (
        LOGO_PRIMARY,
        LOGO_PRIMARY_ALT_JPG,
        LOGO_PRIMARY_ALT_JPEG,
        LOGO_FALLBACK,
        LOGO_FALLBACK_LEGACY,
    ):
        if candidate.exists():
            return str(candidate)
    return ""


def get_icon_path() -> str:
    for candidate in (
        ICON_PRIMARY,
        ICON_FALLBACK,
        LOGO_PRIMARY,
        LOGO_PRIMARY_ALT_JPG,
        LOGO_PRIMARY_ALT_JPEG,
        LOGO_FALLBACK,
        LOGO_FALLBACK_LEGACY,
    ):
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


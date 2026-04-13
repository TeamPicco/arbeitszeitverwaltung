from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "Complio"
APP_NAME_ADMIN = f"{APP_NAME} – Admin"
APP_TAGLINE = "Rechtssicher. Organisiert. Geschützt."
COMPANY_NAME = "Complio"

_ROOT = Path(__file__).resolve().parents[1]
_ASSETS = _ROOT / "assets"

LOGO_PRIMARY = _ASSETS / "coreo_flow_logo.png"
LOGO_PRIMARY_ALT_JPG = _ASSETS / "coreo_flow_logo.jpg"
LOGO_PRIMARY_ALT_JPEG = _ASSETS / "coreo_flow_logo.jpeg"
LOGO_PRIMARY_DASH = _ASSETS / "coreo-flow-logo.png"
LOGO_PRIMARY_GENERIC = _ASSETS / "logo.png"
LOGO_PRIMARY_GENERIC_JPG = _ASSETS / "logo.jpg"
LOGO_FALLBACK = _ASSETS / "crewbase_logo_optimized.png"
LOGO_FALLBACK_LEGACY = _ASSETS / "piccolo_logo.jpeg"
ICON_PRIMARY = _ASSETS / "coreo_flow_icon.png"
ICON_FALLBACK = _ASSETS / "favicon.png"


def get_logo_path() -> str:
    env_logo = (os.getenv("COREO_LOGO_PATH") or "").strip()
    if env_logo:
        return env_logo
    for candidate in (
        LOGO_PRIMARY,
        LOGO_PRIMARY_ALT_JPG,
        LOGO_PRIMARY_ALT_JPEG,
        LOGO_PRIMARY_DASH,
        LOGO_PRIMARY_GENERIC,
        LOGO_PRIMARY_GENERIC_JPG,
        LOGO_FALLBACK,
        LOGO_FALLBACK_LEGACY,
    ):
        if candidate.exists():
            return str(candidate)
    return ""


def get_icon_path() -> str:
    env_icon = (os.getenv("COREO_ICON_PATH") or "").strip()
    if env_icon:
        return env_icon
    for candidate in (
        ICON_PRIMARY,
        ICON_FALLBACK,
        LOGO_PRIMARY,
        LOGO_PRIMARY_ALT_JPG,
        LOGO_PRIMARY_ALT_JPEG,
        LOGO_PRIMARY_DASH,
        LOGO_PRIMARY_GENERIC,
        LOGO_PRIMARY_GENERIC_JPG,
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


from __future__ import annotations

import streamlit as st


def clear_app_caches() -> None:
    """
    Zentraler Cache-Reset für App-weite Daten-Caches.

    Wird nach mutierenden Schreibvorgängen aufgerufen, damit UI-Zustände
    nicht mit veralteten Cache-Snapshots weiterlaufen.
    """
    st.cache_data.clear()

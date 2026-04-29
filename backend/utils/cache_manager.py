from __future__ import annotations

import streamlit as st
from utils.planning_tables import clear_planning_table_cache


def clear_app_caches() -> None:
    """
    Zentraler Cache-Reset für App-weite Daten-Caches.

    Wird nach mutierenden Schreibvorgängen aufgerufen, damit UI-Zustände
    nicht mit veralteten Cache-Snapshots weiterlaufen.
    """
    clear_planning_table_cache()
    st.cache_data.clear()

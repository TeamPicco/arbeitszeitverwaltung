#!/usr/bin/env python3
"""Monatliche DSGVO-Löschroutine — wird von Render Cron Job aufgerufen."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import get_service_role_client

sb = get_service_role_client()
result = sb.rpc("pseudonymisiere_ausgeschiedene_mitarbeiter").execute()
print("DSGVO-Löschung abgeschlossen:", result.data)

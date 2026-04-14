"""
Quick runtime check for Render/Supabase latency alignment.

Usage (on Render shell or locally with env vars):
  python scripts/check_region_latency.py

Required env:
  SUPABASE_URL

Optional env:
  RENDER_REGION
  LATENCY_SAMPLES (default: 5)
"""

from __future__ import annotations

import os
import statistics
import time
from urllib.parse import urlparse

import requests


def main() -> None:
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    render_region = os.getenv("RENDER_REGION", "").strip() or "unknown"
    samples = int(os.getenv("LATENCY_SAMPLES", "5"))

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL fehlt.")

    parsed = urlparse(supabase_url)
    host = parsed.netloc
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/"

    latencies_ms: list[float] = []
    for _ in range(max(1, samples)):
        start = time.perf_counter()
        try:
            requests.get(endpoint, timeout=10)
        except Exception:
            # Auch bei 401/404 ist RTT valide; nur harte Netzwerkfehler werden übersprungen.
            pass
        elapsed = (time.perf_counter() - start) * 1000.0
        latencies_ms.append(elapsed)
        time.sleep(0.15)

    median_ms = statistics.median(latencies_ms) if latencies_ms else float("nan")
    p95_ms = max(latencies_ms) if latencies_ms else float("nan")

    print("=== Render/Supabase Latency Check ===")
    print(f"Render region      : {render_region}")
    print(f"Supabase host      : {host}")
    print(f"Samples            : {len(latencies_ms)}")
    print(f"Median RTT (ms)    : {median_ms:.1f}")
    print(f"Worst RTT (ms)     : {p95_ms:.1f}")
    print("")
    if median_ms <= 45:
        print("Result: Good regional proximity likely.")
    elif median_ms <= 90:
        print("Result: Acceptable but can be improved by region alignment.")
    else:
        print("Result: High latency. Strongly consider co-locating Render and Supabase regions.")


if __name__ == "__main__":
    main()

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, stempel, zeiten, urlaub, mitarbeiter, admin, lohn, dokumente

app = FastAPI(title="Complio API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://app.getcomplio.de",
        "https://complio-frontend.vercel.app",
        "https://complio-fro-teampicccos-projects.vercel.app",
    ],
    allow_origin_regex=r"https://complio-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router, prefix, tag in [
    (auth.router,        "/auth",        "Auth"),
    (stempel.router,     "/stempel",     "Stempel"),
    (zeiten.router,      "/zeiten",      "Zeiten"),
    (urlaub.router,      "/urlaub",      "Urlaub"),
    (mitarbeiter.router, "/mitarbeiter", "Mitarbeiter"),
    (admin.router,       "/admin",       "Admin"),
    (lohn.router,        "/lohn",        "Lohn"),
    (dokumente.router,   "/dokumente",   "Dokumente"),
]:
    app.include_router(router, prefix=prefix, tags=[tag])


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/debug/env")
def debug_env():
    import os, socket
    url = os.getenv("SUPABASE_URL", "NICHT_GESETZT")
    key_set = bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY"))
    host = url.replace("https://", "").replace("http://", "").split("/")[0]
    try:
        ip = socket.gethostbyname(host)
        dns = f"OK → {ip}"
    except Exception as e:
        dns = f"FEHLER: {e}"
    return {
        "supabase_url": url,
        "supabase_url_len": len(url),
        "service_key_set": key_set,
        "dns_check": dns,
        "host": host,
    }

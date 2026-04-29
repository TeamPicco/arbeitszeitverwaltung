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
    ],
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

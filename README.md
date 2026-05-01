# Complio – HR-Software

## Architektur

| Komponente | Technologie | Hosting |
|---|---|---|
| Backend (API) | FastAPI + Python | Railway (`arbeitszeitverwaltung`) |
| Frontend | React + Vite + TypeScript | Vercel |
| Datenbank | Supabase (PostgreSQL) | Supabase |

## Verzeichnisstruktur

```
/
├── backend/          FastAPI-Backend (Railway)
│   ├── main.py
│   ├── routers/
│   └── utils/
├── frontend/         React-Frontend (Vercel)
│   ├── src/
│   └── public/
├── migrations/       SQL-Migrations für Supabase
├── railway.toml      Railway-Konfiguration
└── vercel.json       Vercel-Konfiguration
```

## Deployment

- **Backend**: Push auf `master` → Railway baut automatisch aus `backend/`
- **Frontend**: Push auf `master` → Vercel baut automatisch aus `frontend/`
- **Legacy Streamlit-App**: Branch `legacy/streamlit`

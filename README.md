# Arbeitszeitverwaltung

Eine vollwertige, DSGVO-konforme Web-Anwendung zur Arbeitszeitverwaltung für kleine Unternehmen (6 Mitarbeiter + 1 Administrator). Die Anwendung erfüllt die Anforderungen des deutschen Arbeitsrechts und des Nachweisgesetzes.

## 🎯 Funktionen

### Für Administratoren

- **Mitarbeiterverwaltung:** Anlegen, Bearbeiten und Verwalten von Mitarbeiterstammdaten
- **Vertragsverwaltung:** Upload und Verwaltung von Arbeitsverträgen (PDF)
- **Lohnparameter:** Konfiguration von Soll-Stunden, Stundenlohn, Urlaubstagen und Zuschlägen
- **Urlaubsgenehmigung:** Bearbeitung und Genehmigung von Urlaubsanträgen
- **Zeiterfassung:** Einsicht in alle Zeiterfassungen
- **Lohnabrechnung:** Automatische Berechnung und PDF-Export von Lohnabrechnungen
- **Zuschläge:** 50% Sonntagszuschlag und 100% Feiertagszuschlag

### Für Mitarbeiter

- **Dashboard:** Übersicht über Arbeitszeitkonto und Urlaubstage
- **Zeiterfassung:** Erfassung von Arbeitszeiten mit Start, Ende und Pause
- **Urlaubsanträge:** Beantragung von Urlaub mit Status-Tracking
- **Dokumente:** Einsicht in den eigenen Arbeitsvertrag
- **Arbeitszeitkonto:** Transparente Darstellung von Soll/Ist-Stunden

## 🔒 DSGVO & Rechtssicherheit

- ✅ **DSGVO-konform:** Server-Standort Frankfurt (EU), verschlüsselte Übertragung
- ✅ **Nachweisgesetz:** Erfüllt Anforderungen des deutschen Arbeitsrechts
- ✅ **EuGH-Urteil:** Objektive, verlässliche und zugängliche Zeiterfassung
- ✅ **Datenschutz:** Row Level Security (RLS), bcrypt-Passwort-Hashing
- ✅ **Audit-Trail:** Vollständige Nachvollziehbarkeit durch Timestamps

## 🛠️ Technologie-Stack

- **Frontend:** Streamlit
- **Backend:** Python 3.11+
- **Datenbank:** PostgreSQL (Supabase)
- **Storage:** Supabase Storage (für PDFs)
- **PDF-Generierung:** ReportLab
- **Authentifizierung:** bcrypt
- **Deployment:** Streamlit Cloud

## 📋 Voraussetzungen

- Python 3.11 oder höher
- Supabase-Account (kostenlos)
- GitHub-Account (für Deployment)

## 🚀 Installation & Setup

### 1. Repository klonen

```bash
git clone https://github.com/IHR-USERNAME/arbeitszeitverwaltung.git
cd arbeitszeitverwaltung
```

### 2. Virtuelle Umgebung erstellen

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. Supabase-Datenbank einrichten

1. Erstellen Sie ein neues Projekt auf [supabase.com](https://supabase.com)
2. Öffnen Sie den SQL-Editor
3. Führen Sie die Datei `supabase_schema.sql` aus
4. Erstellen Sie die Storage-Buckets (siehe `SUPABASE_SETUP.md`)

### 5. Umgebungsvariablen konfigurieren

Kopieren Sie `.env.example` zu `.env` und tragen Sie Ihre Supabase-Credentials ein:

```bash
cp .env.example .env
```

Bearbeiten Sie `.env`:

```
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 6. Anwendung starten

```bash
streamlit run app.py
```

Die Anwendung ist nun unter `http://localhost:8501` erreichbar.

## 🔐 Standard-Anmeldedaten

**Administrator:**
- Benutzername: `admin`
- Passwort: `admin123`

⚠️ **WICHTIG:** Ändern Sie das Admin-Passwort sofort nach dem ersten Login!

## 📦 Deployment auf Streamlit Cloud

### 1. GitHub-Repository erstellen

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/IHR-USERNAME/arbeitszeitverwaltung.git
git push -u origin main
```

### 2. Streamlit Cloud konfigurieren

1. Gehen Sie zu [share.streamlit.io](https://share.streamlit.io)
2. Verbinden Sie Ihr GitHub-Repository
3. Wählen Sie `app.py` als Main-Datei
4. Fügen Sie die Secrets hinzu:

```toml
SUPABASE_URL = "https://xxxxxxxxxxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
BUNDESLAND = "NW"
SESSION_TIMEOUT_MINUTES = "480"
```

5. Klicken Sie auf "Deploy"

## 📁 Projektstruktur

```
arbeitszeitverwaltung/
├── app.py                          # Hauptanwendung
├── requirements.txt                # Python-Abhängigkeiten
├── .env.example                    # Beispiel-Umgebungsvariablen
├── .gitignore                      # Git-Ignore-Datei
├── README.md                       # Diese Datei
├── SUPABASE_SETUP.md              # Supabase-Setup-Anleitung
├── supabase_schema.sql            # SQL-Schema für Datenbank
├── database_schema_design.md      # Detailliertes Schema-Design
├── utils/
│   ├── __init__.py
│   ├── database.py                # Datenbank-Funktionen
│   ├── session.py                 # Session-Management
│   ├── calculations.py            # Berechnungs-Funktionen
│   └── lohnabrechnung.py          # Lohnabrechnung & PDF
└── pages/
    ├── __init__.py
    ├── admin_dashboard.py         # Administrator-Dashboard
    └── mitarbeiter_dashboard.py   # Mitarbeiter-Dashboard
```

## 📖 Dokumentation

- **[SUPABASE_SETUP.md](SUPABASE_SETUP.md):** Detaillierte Anleitung zur Supabase-Einrichtung
- **[database_schema_design.md](database_schema_design.md):** Vollständiges Datenbankschema-Design

## 🧪 Testdaten erstellen

Um Testdaten zu erstellen, führen Sie folgende SQL-Abfragen in Supabase aus:

```sql
-- Beispiel-Mitarbeiter erstellen (siehe SUPABASE_SETUP.md)
```

## 🔧 Konfiguration

### Bundesland für Feiertage

In der `.env`-Datei können Sie das Bundesland für die Feiertags-Berechnung festlegen:

```
BUNDESLAND=NW  # Nordrhein-Westfalen
```

Verfügbare Optionen: BW, BY, BE, BB, HB, HH, HE, MV, NI, NW, RP, SL, SN, ST, SH, TH

### Session-Timeout

Standard: 480 Minuten (8 Stunden)

```
SESSION_TIMEOUT_MINUTES=480
```

## 🐛 Troubleshooting

### Problem: Verbindung zu Supabase schlägt fehl

**Lösung:** Prüfen Sie, ob die Supabase-URL und der API-Key korrekt in der `.env`-Datei eingetragen sind.

### Problem: PDF-Upload funktioniert nicht

**Lösung:** Stellen Sie sicher, dass die Storage-Buckets in Supabase korrekt erstellt und die RLS-Policies gesetzt sind.

### Problem: Passwort-Login funktioniert nicht

**Lösung:** Prüfen Sie, ob der Benutzer in der `users`-Tabelle existiert und `is_active = TRUE` gesetzt ist.

## 📝 Lizenz

Dieses Projekt ist für den privaten und kommerziellen Gebrauch freigegeben.

## 🤝 Support

Bei Fragen oder Problemen erstellen Sie bitte ein Issue im GitHub-Repository.

## 📊 Features nach deutschem Arbeitsrecht

### Nachweisgesetz (NachwG)

Die Anwendung erfüllt die Anforderungen des Nachweisgesetzes:

- ✅ Schriftliche Niederlegung der Arbeitsbedingungen
- ✅ Dokumentation der Arbeitszeit
- ✅ Nachweis über Urlaubsanspruch
- ✅ Vergütungsnachweis

### Bundesurlaubsgesetz (BUrlG)

- ✅ Mindestens 20 Tage Urlaub (konfigurierbar)
- ✅ Urlaubsübertragung ins Folgejahr
- ✅ Dokumentation von Urlaubsanträgen

### Arbeitszeitgesetz (ArbZG)

- ✅ Dokumentation der täglichen Arbeitszeit
- ✅ Pausenzeiten-Erfassung
- ✅ Sonntags- und Feiertagsarbeit gekennzeichnet

## 🎨 Screenshots

*(Screenshots können hier eingefügt werden)*

## 🔄 Updates & Wartung

Die Anwendung wird regelmäßig aktualisiert. Prüfen Sie das Repository auf neue Versionen.

## 🙏 Danksagungen

- Streamlit für das exzellente Framework
- Supabase für die Backend-Infrastruktur
- ReportLab für die PDF-Generierung

---

**Entwickelt mit ❤️ für kleine Unternehmen in Deutschland**

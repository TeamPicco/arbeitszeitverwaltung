# Supabase Setup-Anleitung

## Übersicht

Diese Anleitung beschreibt die vollständige Einrichtung der Supabase-Datenbank und des Storage für die Arbeitszeitverwaltungs-Anwendung.

## Schritt 1: Supabase-Projekt erstellen

1. Gehen Sie zu [https://supabase.com](https://supabase.com)
2. Melden Sie sich an oder erstellen Sie ein kostenloses Konto
3. Klicken Sie auf **"New Project"**
4. Geben Sie folgende Informationen ein:
   - **Name:** `arbeitszeitverwaltung` (oder einen Namen Ihrer Wahl)
   - **Database Password:** Wählen Sie ein sicheres Passwort (notieren Sie es!)
   - **Region:** Wählen Sie `Europe (Frankfurt)` für DSGVO-Konformität
   - **Pricing Plan:** Free (ausreichend für 6 Mitarbeiter)
5. Klicken Sie auf **"Create new project"**
6. Warten Sie ca. 2 Minuten, bis das Projekt bereitgestellt ist

## Schritt 2: SQL-Schema importieren

1. Öffnen Sie in Ihrem Supabase-Projekt die **SQL Editor**-Seite (linkes Menü)
2. Klicken Sie auf **"New query"**
3. Öffnen Sie die Datei `supabase_schema.sql` auf Ihrem Computer
4. Kopieren Sie den **gesamten Inhalt** der Datei
5. Fügen Sie den Inhalt in den SQL-Editor ein
6. Klicken Sie auf **"Run"** (oder drücken Sie `Ctrl+Enter`)
7. Warten Sie, bis die Ausführung abgeschlossen ist (grünes Häkchen)

**Erwartetes Ergebnis:** Alle Tabellen, Indizes, Trigger, Views und RLS-Policies werden erstellt.

### Verifizierung

Führen Sie folgende Abfrage aus, um zu prüfen, ob alle Tabellen erstellt wurden:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

**Erwartete Tabellen:**
- `arbeitszeitkonto`
- `lohnabrechnungen`
- `mitarbeiter`
- `urlaubsantraege`
- `users`
- `zeiterfassung`

## Schritt 3: Storage Buckets erstellen

### Bucket 1: arbeitsvertraege

1. Öffnen Sie die **Storage**-Seite im linken Menü
2. Klicken Sie auf **"Create a new bucket"**
3. Geben Sie folgende Informationen ein:
   - **Name:** `arbeitsvertraege`
   - **Public bucket:** ❌ **NEIN** (deaktiviert lassen für Datenschutz)
4. Klicken Sie auf **"Create bucket"**

#### RLS-Policies für arbeitsvertraege

1. Klicken Sie auf den Bucket `arbeitsvertraege`
2. Wechseln Sie zum Tab **"Policies"**
3. Klicken Sie auf **"New policy"**

**Policy 1: Admin kann alle Verträge hochladen und lesen**

```sql
-- Policy Name: Admin Vollzugriff
-- Allowed operation: SELECT, INSERT, UPDATE, DELETE
-- Policy definition:
EXISTS (
    SELECT 1 FROM users 
    WHERE users.id = auth.uid() 
    AND users.role = 'admin'
)
```

**Policy 2: Mitarbeiter können nur eigenen Vertrag lesen**

```sql
-- Policy Name: Mitarbeiter können eigenen Vertrag lesen
-- Allowed operation: SELECT
-- Policy definition:
EXISTS (
    SELECT 1 FROM mitarbeiter 
    WHERE mitarbeiter.user_id = auth.uid()
    AND storage.foldername(name) = mitarbeiter.id::text
)
```

### Bucket 2: lohnabrechnungen

1. Klicken Sie erneut auf **"Create a new bucket"**
2. Geben Sie folgende Informationen ein:
   - **Name:** `lohnabrechnungen`
   - **Public bucket:** ❌ **NEIN** (deaktiviert lassen)
3. Klicken Sie auf **"Create bucket"**

#### RLS-Policies für lohnabrechnungen

**Policy 1: Admin kann alle Abrechnungen hochladen und lesen**

```sql
-- Policy Name: Admin Vollzugriff
-- Allowed operation: SELECT, INSERT, UPDATE, DELETE
-- Policy definition:
EXISTS (
    SELECT 1 FROM users 
    WHERE users.id = auth.uid() 
    AND users.role = 'admin'
)
```

**Policy 2: Mitarbeiter können nur eigene Abrechnungen lesen**

```sql
-- Policy Name: Mitarbeiter können eigene Abrechnungen lesen
-- Allowed operation: SELECT
-- Policy definition:
EXISTS (
    SELECT 1 FROM mitarbeiter 
    WHERE mitarbeiter.user_id = auth.uid()
    AND storage.foldername(name) = mitarbeiter.id::text
)
```

## Schritt 4: API-Credentials abrufen

1. Öffnen Sie die **Settings**-Seite (linkes Menü, ganz unten)
2. Klicken Sie auf **"API"**
3. Notieren Sie folgende Werte (Sie benötigen diese für die Streamlit-App):

   - **Project URL:** `https://xxxxxxxxxxxxx.supabase.co`
   - **API Key (anon, public):** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**WICHTIG:** Diese Credentials müssen in der `.env`-Datei der Streamlit-App hinterlegt werden!

## Schritt 5: Admin-Passwort ändern (WICHTIG!)

Das SQL-Schema erstellt automatisch einen Admin-Benutzer mit folgenden Anmeldedaten:

- **Benutzername:** `admin`
- **Passwort:** `admin123`

⚠️ **SICHERHEITSWARNUNG:** Dieses Passwort MUSS sofort nach dem ersten Login geändert werden!

### Passwort manuell ändern (vor dem ersten Login)

1. Öffnen Sie den **SQL Editor** in Supabase
2. Generieren Sie einen neuen bcrypt-Hash für Ihr gewünschtes Passwort:
   - Nutzen Sie einen Online-Generator: [https://bcrypt-generator.com/](https://bcrypt-generator.com/)
   - Wählen Sie **Rounds: 12**
   - Geben Sie Ihr neues Passwort ein
   - Kopieren Sie den generierten Hash
3. Führen Sie folgende SQL-Abfrage aus:

```sql
UPDATE users 
SET password_hash = 'IHR_NEUER_BCRYPT_HASH'
WHERE username = 'admin';
```

**Beispiel:**

```sql
UPDATE users 
SET password_hash = '$2b$12$abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOP'
WHERE username = 'admin';
```

## Schritt 6: Testdaten erstellen (Optional)

Für Testzwecke können Sie einen Beispiel-Mitarbeiter anlegen:

```sql
-- 1. Benutzer erstellen (Passwort: test123)
INSERT INTO users (username, password_hash, role) 
VALUES (
    'max.mustermann',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYfQYvmixxO',
    'mitarbeiter'
);

-- 2. Mitarbeiter-Stammdaten erstellen
INSERT INTO mitarbeiter (
    user_id,
    vorname,
    nachname,
    geburtsdatum,
    strasse,
    plz,
    ort,
    email,
    telefon,
    personalnummer,
    eintrittsdatum,
    monatliche_soll_stunden,
    stundenlohn_brutto,
    jahres_urlaubstage,
    sonntagszuschlag_aktiv,
    feiertagszuschlag_aktiv
)
SELECT 
    id,
    'Max',
    'Mustermann',
    '1990-05-15',
    'Musterstraße 123',
    '12345',
    'Musterstadt',
    'max.mustermann@beispiel.de',
    '+49 123 456789',
    'MA-001',
    '2024-01-01',
    160.00,
    15.50,
    28,
    TRUE,
    TRUE
FROM users 
WHERE username = 'max.mustermann';
```

## Schritt 7: Verbindung testen

Nach der Einrichtung können Sie die Verbindung testen:

1. Öffnen Sie den **Table Editor** in Supabase
2. Wählen Sie die Tabelle `users`
3. Sie sollten mindestens den Admin-Benutzer sehen

## Zusammenfassung der Bucket-Namen

Für die Streamlit-Anwendung benötigen Sie folgende Bucket-Namen:

| Bucket-Name | Zweck | Public |
|-------------|-------|--------|
| `arbeitsvertraege` | Speicherung von Arbeitsverträgen (PDF) | Nein |
| `lohnabrechnungen` | Speicherung von Lohnabrechnungen (PDF) | Nein |

## Pfad-Schema für Dateien

### Arbeitsverträge

```
arbeitsvertraege/
└── {mitarbeiter_id}/
    └── {personalnummer}_vertrag.pdf
```

**Beispiel:** `arbeitsvertraege/a1b2c3d4-e5f6-7890-abcd-ef1234567890/MA-001_vertrag.pdf`

### Lohnabrechnungen

```
lohnabrechnungen/
└── {mitarbeiter_id}/
    └── {jahr}/
        └── {monat}_abrechnung.pdf
```

**Beispiel:** `lohnabrechnungen/a1b2c3d4-e5f6-7890-abcd-ef1234567890/2025/01_abrechnung.pdf`

## Troubleshooting

### Problem: RLS-Policies blockieren Zugriff

**Lösung:** Stellen Sie sicher, dass Sie in der Streamlit-App mit einem gültigen Benutzer authentifiziert sind. Die RLS-Policies nutzen `auth.uid()`, das nur funktioniert, wenn ein Benutzer eingeloggt ist.

### Problem: Storage-Upload schlägt fehl

**Lösung:** 
1. Prüfen Sie, ob die Buckets korrekt erstellt wurden
2. Prüfen Sie, ob die RLS-Policies für Storage gesetzt sind
3. Stellen Sie sicher, dass der Dateipfad dem Schema entspricht

### Problem: SQL-Schema-Import schlägt fehl

**Lösung:**
1. Prüfen Sie, ob die UUID-Extension aktiviert ist
2. Führen Sie das Schema in kleineren Abschnitten aus
3. Prüfen Sie die Fehlermeldungen im SQL-Editor

## Nächste Schritte

Nach erfolgreicher Einrichtung von Supabase:

1. ✅ Notieren Sie die API-Credentials (URL + API Key)
2. ✅ Ändern Sie das Admin-Passwort
3. ✅ Erstellen Sie die `.env`-Datei für die Streamlit-App
4. ✅ Testen Sie die Verbindung mit der Streamlit-App

## DSGVO-Hinweise

- ✅ Server-Standort: Frankfurt (EU)
- ✅ Daten werden verschlüsselt übertragen (TLS)
- ✅ Row Level Security (RLS) aktiviert
- ✅ Passwörter mit bcrypt gehasht
- ✅ Keine öffentlichen Buckets
- ✅ Audit-Trail durch Timestamps

## Support

Bei Fragen zur Supabase-Einrichtung:
- Supabase-Dokumentation: [https://supabase.com/docs](https://supabase.com/docs)
- Supabase-Community: [https://github.com/supabase/supabase/discussions](https://github.com/supabase/supabase/discussions)

# Datenbankschema-Design: Arbeitszeitverwaltung

## Übersicht

Dieses Dokument beschreibt das vollständige Datenbankschema für die DSGVO-konforme Arbeitszeitverwaltungs-Anwendung nach deutschem Arbeitsrecht.

## Tabellen-Struktur

### 1. users (Benutzer-Authentifizierung)

**Zweck:** Verwaltung von Anmeldedaten für Mitarbeiter und Administrator

| Spalte | Typ | Beschreibung | Constraints |
|--------|-----|--------------|-------------|
| id | UUID | Primärschlüssel | PRIMARY KEY, DEFAULT gen_random_uuid() |
| username | VARCHAR(100) | Benutzername (eindeutig) | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | Bcrypt-gehashtes Passwort | NOT NULL |
| role | VARCHAR(20) | Rolle: 'admin' oder 'mitarbeiter' | NOT NULL, CHECK (role IN ('admin', 'mitarbeiter')) |
| is_active | BOOLEAN | Account-Status | DEFAULT TRUE |
| created_at | TIMESTAMP | Erstellungszeitpunkt | DEFAULT NOW() |
| last_login | TIMESTAMP | Letzter Login | NULL |

### 2. mitarbeiter (Stammdaten & Vertragswesen)

**Zweck:** Detaillierte Mitarbeiterprofile mit allen vertragsrelevanten Daten

| Spalte | Typ | Beschreibung | Constraints |
|--------|-----|--------------|-------------|
| id | UUID | Primärschlüssel | PRIMARY KEY, DEFAULT gen_random_uuid() |
| user_id | UUID | Referenz zu users | FOREIGN KEY REFERENCES users(id) ON DELETE CASCADE, UNIQUE |
| vorname | VARCHAR(100) | Vorname | NOT NULL |
| nachname | VARCHAR(100) | Nachname | NOT NULL |
| geburtsdatum | DATE | Geburtsdatum | NOT NULL |
| strasse | VARCHAR(200) | Straße und Hausnummer | NOT NULL |
| plz | VARCHAR(10) | Postleitzahl | NOT NULL |
| ort | VARCHAR(100) | Ort | NOT NULL |
| email | VARCHAR(255) | E-Mail-Adresse | NOT NULL |
| telefon | VARCHAR(50) | Telefonnummer | NULL |
| personalnummer | VARCHAR(50) | Personalnummer (eindeutig) | UNIQUE, NOT NULL |
| eintrittsdatum | DATE | Eintrittsdatum | NOT NULL |
| austrittsdatum | DATE | Austrittsdatum (optional) | NULL |
| vertrag_pdf_path | TEXT | Pfad zum Vertrag in Supabase Storage | NULL |
| monatliche_soll_stunden | DECIMAL(6,2) | Monatliche Soll-Arbeitsstunden | NOT NULL, CHECK (monatliche_soll_stunden > 0) |
| stundenlohn_brutto | DECIMAL(8,2) | Stundenlohn in Euro (brutto) | NOT NULL, CHECK (stundenlohn_brutto > 0) |
| jahres_urlaubstage | INTEGER | Jährlicher Urlaubsanspruch in Tagen | NOT NULL, CHECK (jahres_urlaubstage >= 20) |
| resturlaub_vorjahr | DECIMAL(5,2) | Resturlaub aus Vorjahr | DEFAULT 0, CHECK (resturlaub_vorjahr >= 0) |
| sonntagszuschlag_aktiv | BOOLEAN | 50% Sonntagszuschlag aktiviert | DEFAULT FALSE |
| feiertagszuschlag_aktiv | BOOLEAN | 100% Feiertagszuschlag aktiviert | DEFAULT FALSE |
| created_at | TIMESTAMP | Erstellungszeitpunkt | DEFAULT NOW() |
| updated_at | TIMESTAMP | Letzte Aktualisierung | DEFAULT NOW() |

### 3. zeiterfassung (Arbeitszeiterfassung)

**Zweck:** Objektive und verlässliche Zeiterfassung gemäß EuGH-Urteil

| Spalte | Typ | Beschreibung | Constraints |
|--------|-----|--------------|-------------|
| id | UUID | Primärschlüssel | PRIMARY KEY, DEFAULT gen_random_uuid() |
| mitarbeiter_id | UUID | Referenz zu mitarbeiter | FOREIGN KEY REFERENCES mitarbeiter(id) ON DELETE CASCADE, NOT NULL |
| datum | DATE | Arbeitstag | NOT NULL |
| start_zeit | TIME | Arbeitsbeginn | NOT NULL |
| ende_zeit | TIME | Arbeitsende | NULL |
| pause_minuten | INTEGER | Pausenzeit in Minuten | DEFAULT 0, CHECK (pause_minuten >= 0) |
| ist_sonntag | BOOLEAN | Ist Sonntag (für Zuschlag) | DEFAULT FALSE |
| ist_feiertag | BOOLEAN | Ist Feiertag (für Zuschlag) | DEFAULT FALSE |
| notiz | TEXT | Optionale Notiz | NULL |
| erstellt_am | TIMESTAMP | Erfassungszeitpunkt | DEFAULT NOW() |
| geaendert_am | TIMESTAMP | Letzte Änderung | DEFAULT NOW() |

**Indizes:**
- INDEX idx_zeiterfassung_mitarbeiter_datum ON zeiterfassung(mitarbeiter_id, datum)

### 4. urlaubsantraege (Urlaubsverwaltung)

**Zweck:** Verwaltung von Urlaubsanträgen mit Genehmigungsworkflow

| Spalte | Typ | Beschreibung | Constraints |
|--------|-----|--------------|-------------|
| id | UUID | Primärschlüssel | PRIMARY KEY, DEFAULT gen_random_uuid() |
| mitarbeiter_id | UUID | Referenz zu mitarbeiter | FOREIGN KEY REFERENCES mitarbeiter(id) ON DELETE CASCADE, NOT NULL |
| von_datum | DATE | Urlaubsbeginn | NOT NULL |
| bis_datum | DATE | Urlaubsende | NOT NULL, CHECK (bis_datum >= von_datum) |
| anzahl_tage | DECIMAL(4,2) | Anzahl Urlaubstage | NOT NULL, CHECK (anzahl_tage > 0) |
| status | VARCHAR(20) | Status: 'beantragt', 'genehmigt', 'abgelehnt' | NOT NULL, DEFAULT 'beantragt', CHECK (status IN ('beantragt', 'genehmigt', 'abgelehnt')) |
| bemerkung_mitarbeiter | TEXT | Bemerkung des Mitarbeiters | NULL |
| bemerkung_admin | TEXT | Bemerkung des Administrators | NULL |
| beantragt_am | TIMESTAMP | Antragszeitpunkt | DEFAULT NOW() |
| bearbeitet_am | TIMESTAMP | Bearbeitungszeitpunkt | NULL |
| bearbeitet_von | UUID | Referenz zu users (Admin) | FOREIGN KEY REFERENCES users(id), NULL |

**Indizes:**
- INDEX idx_urlaubsantraege_mitarbeiter ON urlaubsantraege(mitarbeiter_id)
- INDEX idx_urlaubsantraege_status ON urlaubsantraege(status)

### 5. arbeitszeitkonto (Zeitkonto-Salden)

**Zweck:** Monatliche Zusammenfassung des Arbeitszeitkontos (Plus/Minus-Stunden)

| Spalte | Typ | Beschreibung | Constraints |
|--------|-----|--------------|-------------|
| id | UUID | Primärschlüssel | PRIMARY KEY, DEFAULT gen_random_uuid() |
| mitarbeiter_id | UUID | Referenz zu mitarbeiter | FOREIGN KEY REFERENCES mitarbeiter(id) ON DELETE CASCADE, NOT NULL |
| monat | INTEGER | Monat (1-12) | NOT NULL, CHECK (monat BETWEEN 1 AND 12) |
| jahr | INTEGER | Jahr | NOT NULL, CHECK (jahr >= 2020) |
| soll_stunden | DECIMAL(6,2) | Soll-Stunden im Monat | NOT NULL |
| ist_stunden | DECIMAL(6,2) | Ist-Stunden im Monat | NOT NULL, DEFAULT 0 |
| differenz_stunden | DECIMAL(7,2) | Differenz (Ist - Soll) | GENERATED ALWAYS AS (ist_stunden - soll_stunden) STORED |
| urlaubstage_genommen | DECIMAL(4,2) | Genommene Urlaubstage | DEFAULT 0 |
| sonntagsstunden | DECIMAL(6,2) | Stunden mit Sonntagszuschlag | DEFAULT 0 |
| feiertagsstunden | DECIMAL(6,2) | Stunden mit Feiertagszuschlag | DEFAULT 0 |
| berechnet_am | TIMESTAMP | Berechnungszeitpunkt | DEFAULT NOW() |

**Indizes:**
- UNIQUE INDEX idx_arbeitszeitkonto_unique ON arbeitszeitkonto(mitarbeiter_id, monat, jahr)

### 6. lohnabrechnungen (Monatliche Entgeltaufstellungen)

**Zweck:** Gespeicherte Lohnabrechnungen für PDF-Export

| Spalte | Typ | Beschreibung | Constraints |
|--------|-----|--------------|-------------|
| id | UUID | Primärschlüssel | PRIMARY KEY, DEFAULT gen_random_uuid() |
| mitarbeiter_id | UUID | Referenz zu mitarbeiter | FOREIGN KEY REFERENCES mitarbeiter(id) ON DELETE CASCADE, NOT NULL |
| monat | INTEGER | Abrechnungsmonat (1-12) | NOT NULL, CHECK (monat BETWEEN 1 AND 12) |
| jahr | INTEGER | Abrechnungsjahr | NOT NULL, CHECK (jahr >= 2020) |
| arbeitszeitkonto_id | UUID | Referenz zu arbeitszeitkonto | FOREIGN KEY REFERENCES arbeitszeitkonto(id), NOT NULL |
| grundlohn | DECIMAL(10,2) | Grundlohn (Stundenlohn × Ist-Stunden) | NOT NULL |
| sonntagszuschlag | DECIMAL(10,2) | Sonntagszuschlag (50%) | DEFAULT 0 |
| feiertagszuschlag | DECIMAL(10,2) | Feiertagszuschlag (100%) | DEFAULT 0 |
| gesamtbetrag | DECIMAL(10,2) | Gesamtbetrag brutto | NOT NULL |
| pdf_path | TEXT | Pfad zum PDF in Supabase Storage | NULL |
| erstellt_am | TIMESTAMP | Erstellungszeitpunkt | DEFAULT NOW() |

**Indizes:**
- UNIQUE INDEX idx_lohnabrechnungen_unique ON lohnabrechnungen(mitarbeiter_id, monat, jahr)

## DSGVO-Konformität

### Datenschutzmaßnahmen

1. **Passwort-Sicherheit:** Alle Passwörter werden mit bcrypt gehasht (Faktor 12)
2. **Datentrennung:** Row Level Security (RLS) in Supabase für strikte Datentrennung
3. **Zugriffskontrolle:** Mitarbeiter sehen nur eigene Daten, Admin hat Vollzugriff
4. **Verschlüsselung:** TLS-Verschlüsselung für alle Datenübertragungen
5. **Audit-Trail:** Timestamps für alle Änderungen (created_at, updated_at)

### Rechtliche Anforderungen (Nachweisgesetz)

1. **Objektive Zeiterfassung:** Tabelle `zeiterfassung` erfasst alle Arbeitszeiten
2. **Verlässlichkeit:** Timestamps und Unveränderbarkeit durch Audit-Logs
3. **Zugänglichkeit:** Mitarbeiter können jederzeit eigene Daten einsehen
4. **Aufbewahrung:** Verträge und Abrechnungen werden dauerhaft gespeichert

## Supabase Storage-Struktur

### Buckets

1. **arbeitsvertraege**
   - Zweck: Speicherung von Arbeitsverträgen (PDF)
   - Pfad-Schema: `{mitarbeiter_id}/{personalnummer}_vertrag.pdf`
   - Zugriff: Admin (RW), Mitarbeiter (R, nur eigene)

2. **lohnabrechnungen**
   - Zweck: Speicherung von Lohnabrechnungen (PDF)
   - Pfad-Schema: `{mitarbeiter_id}/{jahr}/{monat}_abrechnung.pdf`
   - Zugriff: Admin (RW), Mitarbeiter (R, nur eigene)

## Berechnungslogik

### Arbeitsstunden-Berechnung

```
Ist-Stunden = (Ende-Zeit - Start-Zeit) - (Pause-Minuten / 60)
Differenz = Ist-Stunden - Soll-Stunden
```

### Urlaubsberechnung

```
Verfügbarer Urlaub = Jahres-Urlaubstage + Resturlaub-Vorjahr - Genommene-Tage
Resturlaub Jahresende = Verfügbarer Urlaub (max. 1/3 übertragbar nach BUrlG)
```

### Lohnberechnung

```
Grundlohn = Stundenlohn × Ist-Stunden
Sonntagszuschlag = Stundenlohn × Sonntagsstunden × 0,50 (wenn aktiviert)
Feiertagszuschlag = Stundenlohn × Feiertagsstunden × 1,00 (wenn aktiviert)
Gesamtbetrag = Grundlohn + Sonntagszuschlag + Feiertagszuschlag
```

## Feiertags-Erkennung

Deutsche Feiertage werden programmatisch erkannt:
- Neujahr (1.1.)
- Karfreitag (variabel)
- Ostermontag (variabel)
- Tag der Arbeit (1.5.)
- Christi Himmelfahrt (variabel)
- Pfingstmontag (variabel)
- Tag der Deutschen Einheit (3.10.)
- 1. Weihnachtstag (25.12.)
- 2. Weihnachtstag (26.12.)

Zusätzlich ggf. bundeslandspezifische Feiertage (konfigurierbar).

# CrewBase - Feature-Dokumentation

## Übersicht

CrewBase ist eine professionelle, mandantenfähige Arbeitszeitverwaltung für Restaurants und Betriebe mit mehreren Standorten oder Außendienst-Mitarbeitern.

## Hauptfeatures

### 1. Multi-Tenancy (Mandantenfähigkeit)

**Beschreibung:** Mehrere Betriebe können dieselbe Anwendung nutzen, mit vollständiger Datentrennung.

**Features:**
- Login mit Betriebsnummer, Benutzername und Passwort
- Jeder Betrieb hat eine eindeutige Betriebsnummer (z.B. 20262204 für Piccolo)
- Absolute Datenisolation zwischen Betrieben
- Betriebsspezifische Logos und Einstellungen

**Verwendung:**
- Piccolo-Betriebsnummer: `20262204`
- Admin-Login: `admin` / `RangeRover2026`

---

### 2. Progressive Web App (PWA)

**Beschreibung:** CrewBase kann auf Smartphones und Tablets wie eine native App installiert werden.

**Features:**
- Installierbar auf Homescreen (iOS & Android)
- Offline-Funktionalität
- App-Icon (nur CrewBase-Symbol)
- Vollbild-Modus ohne Browser-Leiste
- Service Worker für schnellere Ladezeiten

**Installation:**
1. Öffne CrewBase im Browser
2. Tippe auf "Zum Homescreen hinzufügen" (iOS) oder "App installieren" (Android)
3. App erscheint auf dem Homescreen

---

### 3. Zeiterfassung mit Mastergeräten

**Beschreibung:** Zeiterfassung kann auf bestimmte Geräte (Terminals) beschränkt werden.

**Features:**
- **Mastergeräte:** Registrierte Terminals (z.B. am Eingang)
- **Mobile Berechtigung:** Pro Mitarbeiter einstellbar
- **Zwei Modi:**
  - Nur Mastergerät (Standard für Restaurant-Mitarbeiter)
  - Mobile Zeiterfassung (für Außendienst-Mitarbeiter)

**Admin-Funktionen:**
- Mastergeräte registrieren (Name, Standort, Beschreibung)
- Registrierungscode generieren
- Geräte aktivieren/deaktivieren
- Mobile Berechtigung pro Mitarbeiter festlegen

**Mitarbeiter-Funktionen:**
- Ein-/Ausstempeln am Mastergerät
- Ein-/Ausstempeln per App (nur mit Berechtigung)
- Zeiterfassungen einsehen

---

### 4. Zeiterfassung-Korrektur (Admin)

**Beschreibung:** Administrator kann Zeiterfassungen nachträglich korrigieren.

**Features:**
- Check-In/Check-Out-Zeiten ändern
- Pausenzeiten anpassen
- Pflichtfeld: Grund der Korrektur
- Automatische Neuberechnung der Arbeitsstunden
- Protokollierung aller Änderungen
- Zeiterfassungen löschen (mit Bestätigung)

**Verwendung:**
1. Admin-Dashboard → Zeiterfassung
2. Filter nach Mitarbeiter und Zeitraum
3. Zeiterfassung öffnen → Korrigieren
4. Grund angeben → Speichern

---

### 5. Mitarbeiter-Stammdaten-Bearbeitung

**Beschreibung:** Mitarbeiter können ihre eigenen Stammdaten bearbeiten.

**Mitarbeiter können ändern:**
- E-Mail-Adresse
- Telefonnummer
- Adresse (Straße, PLZ, Ort)
- Nachname (nur mit Admin-Genehmigung, z.B. nach Heirat)

**Admin-Funktionen:**
- Benachrichtigung über alle Änderungen
- Änderungsanfragen genehmigen/ablehnen
- Audit-Log aller Änderungen

---

### 6. Plauderecke (Interner Chat)

**Beschreibung:** Interner Chat für alle Mitarbeiter und Admin.

**Features:**
- Alle können Nachrichten senden
- Chronologische Anzeige
- Eigene Nachrichten rechts (grün), andere links (grau)
- Eigene Nachrichten löschen
- Echtzeit-Updates

**Verwendungszwecke:**
- Diensttausch-Anfragen
- Urlaubsbekanntgaben
- Lob/Kritik
- Allgemeine Kommunikation

---

### 7. Push-Benachrichtigungen

**Beschreibung:** Browser-Benachrichtigungen für wichtige Ereignisse.

**Benachrichtigungstypen:**
- **Urlaubsanträge:** Admin wird über neue Anträge informiert
- **Urlaubsgenehmigungen:** Mitarbeiter wird über Genehmigung/Ablehnung informiert
- **Dienstpläne:** Mitarbeiter wird über neue Dienstpläne informiert
- **Stammdaten-Änderungen:** Admin wird über Änderungen informiert
- **Chat-Nachrichten:** Alle werden über neue Nachrichten informiert

**Features:**
- Benachrichtigungs-Widget in Sidebar
- Ungelesene Benachrichtigungen zählen
- Als gelesen markieren
- Direkt zum relevanten Tab springen

---

### 8. Urlaubsverwaltung

**Beschreibung:** Vollständige Verwaltung von Urlaubsanträgen.

**Mitarbeiter:**
- Urlaubsantrag stellen (Von/Bis-Datum, Grund)
- Status einsehen (Offen, Genehmigt, Abgelehnt)
- Verfügbare Urlaubstage sehen
- Benachrichtigung bei Genehmigung/Ablehnung

**Admin:**
- Alle Urlaubsanträge einsehen
- Genehmigen/Ablehnen mit Kommentar
- Urlaubsübersicht aller Mitarbeiter
- Benachrichtigung bei neuen Anträgen

---

### 9. Dienstplanung

**Beschreibung:** Erstellung und Verwaltung von Dienstplänen.

**Admin:**
- Dienstpläne erstellen (Monat, Mitarbeiter, Schichten)
- Dienstpläne bearbeiten
- Dienstpläne veröffentlichen
- Benachrichtigung an Mitarbeiter senden

**Mitarbeiter:**
- Eigene Schichten einsehen (nur eigene!)
- Keine Einsicht in Schichten anderer Mitarbeiter
- Benachrichtigung bei neuen Dienstplänen

---

### 10. Lohnabrechnung

**Beschreibung:** Automatische Berechnung und PDF-Generierung.

**Features:**
- Auswahl Mitarbeiter und Zeitraum (Monat/Jahr)
- Automatische Berechnung:
  - Arbeitsstunden
  - Bruttolohn
  - Sonntags-/Feiertagszuschläge
  - Urlaubstage
- PDF-Generierung
- Download und Speicherung

---

### 11. Mitarbeiterverwaltung (Admin)

**Beschreibung:** Vollständige Verwaltung aller Mitarbeiter.

**Features:**
- Mitarbeiter anlegen (alle Stammdaten)
- Mitarbeiter bearbeiten
- Mitarbeiter deaktivieren
- Arbeitsvertrag hochladen (PDF)
- Arbeitsvertrag anzeigen und herunterladen
- Mobile Zeiterfassung pro Mitarbeiter aktivieren
- Passwort zurücksetzen

**Pflichtfelder:**
- Name, Vorname
- Geburtsdatum
- Eintrittsdatum (ab 1995)
- Stundenlohn
- Soll-Stunden
- Urlaubstage

---

### 12. Sicherheit & Datenschutz

**Features:**
- DSGVO-konform
- Passwort-Hashing (bcrypt)
- Session-Management
- Datenisolation zwischen Betrieben
- Audit-Logs für Änderungen
- Sichere Dateiuploads
- HTTPS-Verschlüsselung

---

### 13. Deutsches Datumsformat

**Beschreibung:** Alle Daten werden im deutschen Format angezeigt.

**Format:** TT.MM.JJJJ (z.B. 01.02.2026)

---

## Technische Details

### Datenbank

**Supabase (PostgreSQL)**

**Haupttabellen:**
- `betriebe` - Betriebsdaten
- `users` - Benutzer-Accounts
- `mitarbeiter` - Mitarbeiterdaten
- `zeiterfassungen` - Zeiterfassungen
- `urlaubsantraege` - Urlaubsanträge
- `dienstplaene` - Dienstpläne
- `mastergeraete` - Registrierte Terminals
- `benachrichtigungen` - Push-Benachrichtigungen
- `plauderecke` - Chat-Nachrichten

### Deployment

**Hosting:** Render.com  
**URL:** https://arbeitszeitverwaltung.onrender.com

### Umgebungsvariablen

Erforderlich in `.env` oder Render.com:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

---

## Roadmap (Optional)

### Zukünftige Features

- [ ] Echte Push-Benachrichtigungen (Web Push API)
- [ ] E-Mail-Benachrichtigungen (SMTP)
- [ ] GPS-Standort bei mobiler Zeiterfassung
- [ ] Schichtplanung mit Drag & Drop
- [ ] Statistiken und Reports
- [ ] Export nach Excel/CSV
- [ ] Mehrsprachigkeit
- [ ] Dark Mode

---

## Support

Bei Fragen oder Problemen: piccolo_leipzig@yahoo.de

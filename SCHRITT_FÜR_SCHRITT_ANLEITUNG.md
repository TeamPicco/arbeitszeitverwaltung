# 🎯 SCHRITT-FÜR-SCHRITT-ANLEITUNG
## Complio - Finale Einrichtung

**WICHTIG:** Folgen Sie dieser Anleitung Schritt für Schritt. Überspringen Sie NICHTS!

---

## ✅ TEIL 1: SUPABASE-DATENBANK EINRICHTEN (10 Minuten)

### Schritt 1.1: SQL-Datei öffnen

1. **Öffnen Sie diesen Link in einem neuen Tab:**  
   https://github.com/TeamPicco/arbeitszeitverwaltung/blob/master/supabase_schema_final.sql

2. **Sie sehen jetzt eine Seite mit SQL-Code**

3. **Klicken Sie oben rechts auf den Button "Raw"**  
   (Der Button steht rechts neben "Blame" und "Edit")

4. **Es öffnet sich eine neue Seite mit nur Text (kein GitHub-Design mehr)**

5. **Markieren Sie ALLES:**
   - Windows: Drücken Sie `Strg + A`
   - Mac: Drücken Sie `Cmd + A`

6. **Kopieren Sie ALLES:**
   - Windows: Drücken Sie `Strg + C`
   - Mac: Drücken Sie `Cmd + C`

---

### Schritt 1.2: Supabase öffnen

1. **Öffnen Sie in einem neuen Tab:** https://supabase.com

2. **Klicken Sie oben rechts auf "Sign in"**

3. **Melden Sie sich mit Ihrem GitHub-Account an**

4. **Sie sehen jetzt Ihr Supabase-Dashboard**

5. **Klicken Sie auf Ihr Projekt "arbeitszeitverwaltung"**  
   (Falls Sie mehrere Projekte haben)

---

### Schritt 1.3: SQL-Editor öffnen

1. **Schauen Sie auf die LINKE Seite** - dort ist ein Menü mit Icons

2. **Klicken Sie auf das Icon "SQL Editor"**  
   (Es sieht aus wie `</>` oder ein Code-Symbol)

3. **Sie sehen jetzt den SQL-Editor**

---

### Schritt 1.4: SQL einfügen und ausführen

1. **Klicken Sie auf den grünen Button "New query"**  
   (oben links)

2. **Es öffnet sich ein leeres Textfeld**

3. **Fügen Sie die kopierte SQL ein:**
   - Windows: Drücken Sie `Strg + V`
   - Mac: Drücken Sie `Cmd + V`

4. **Sie sollten jetzt viel SQL-Code sehen**  
   (Beginnt mit "-- ============================================")

5. **Klicken Sie UNTEN RECHTS auf den Button "Run"**

6. **Es erscheint eine Warnung:**  
   "Potential issue detected with your query"  
   "Query has destructive operation"

7. **Das ist NORMAL! Klicken Sie auf "Run this query"**  
   (Der orange Button)

8. **Warten Sie 5-10 Sekunden**

9. **✅ Sie sollten GRÜNE HÄKCHEN sehen!**  
   Wenn Sie rote Fehler sehen, machen Sie einen Screenshot und schicken Sie ihn mir!

---

## ✅ TEIL 2: RENDER.COM ENVIRONMENT VARIABLES SETZEN (5 Minuten)

### Schritt 2.1: Supabase API Key kopieren

**WICHTIG:** Lassen Sie Supabase geöffnet!

1. **In Supabase: Klicken Sie links unten auf "Settings"**  
   (Zahnrad-Symbol ⚙️)

2. **Klicken Sie auf "API"**

3. **Sie sehen jetzt zwei wichtige Dinge:**

   **A) Project URL:**
   - Steht ganz oben
   - Sieht aus wie: `https://xxxxxxxxxx.supabase.co`
   - **Kopieren Sie diese URL** (Klicken Sie auf das Kopieren-Symbol rechts daneben)
   - **Öffnen Sie Notepad/Editor** und fügen Sie sie ein (Strg+V)
   - Schreiben Sie davor: `URL: `

   **B) API Key (anon public):**
   - Scrollen Sie etwas runter zu "Project API keys"
   - Suchen Sie die Zeile **"anon public"**
   - **Kopieren Sie den langen Key** (Klicken Sie auf das Kopieren-Symbol)
   - **Fügen Sie ihn in Notepad ein** (neue Zeile)
   - Schreiben Sie davor: `KEY: `

**Ihr Notepad sollte jetzt so aussehen:**
```
URL: https://jehomjeanbmkoptknutx.supabase.co
KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ey... (sehr lang)
```

**Lassen Sie Notepad geöffnet!**

---

### Schritt 2.2: Render.com öffnen

1. **Öffnen Sie in einem neuen Tab:** https://dashboard.render.com

2. **Melden Sie sich an** (falls noch nicht geschehen)

3. **Sie sehen Ihre Apps**

4. **Klicken Sie auf "arbeitszeitverwaltung"**

---

### Schritt 2.3: Environment Variables hinzufügen

1. **Schauen Sie auf die LINKE Seite** - dort ist ein Menü

2. **Klicken Sie auf "Environment"**

3. **Sie sehen jetzt "Environment Variables"**

4. **Klicken Sie auf "Add Environment Variable"**

---

### Schritt 2.4: Variablen einzeln hinzufügen

**Variable 1:**
1. **Key:** Tippen Sie `SUPABASE_URL`
2. **Value:** Kopieren Sie die URL aus Ihrem Notepad (NUR die URL, OHNE "URL: ")
3. **Klicken Sie auf "Add"**

**Variable 2:**
1. **Klicken Sie nochmal auf "Add Environment Variable"**
2. **Key:** Tippen Sie `SUPABASE_KEY`
3. **Value:** Kopieren Sie den KEY aus Ihrem Notepad (NUR den Key, OHNE "KEY: ")
4. **Klicken Sie auf "Add"**

**Variable 3:**
1. **Klicken Sie nochmal auf "Add Environment Variable"**
2. **Key:** Tippen Sie `BUNDESLAND`
3. **Value:** Tippen Sie `SN` (Sachsen)
4. **Klicken Sie auf "Add"**

**Variable 4:**
1. **Klicken Sie nochmal auf "Add Environment Variable"**
2. **Key:** Tippen Sie `SESSION_TIMEOUT_MINUTES`
3. **Value:** Tippen Sie `480`
4. **Klicken Sie auf "Add"**

---

### Schritt 2.5: Speichern und App neu starten

1. **Klicken Sie auf "Save Changes"** (oben oder unten auf der Seite)

2. **Klicken Sie oben rechts auf "Manual Deploy"**

3. **Wählen Sie "Clear build cache & deploy"**  
   (NICHT nur "Deploy latest commit"!)

4. **Warten Sie 2-3 Minuten**  
   Sie sehen Logs - warten Sie bis "Your service is live" erscheint

---

## ✅ TEIL 3: LOGIN TESTEN (1 Minute)

1. **Öffnen Sie in einem neuen Tab:** https://app.getcomplio.de

2. **Warten Sie bis die Login-Seite erscheint**  
   (Kann 30-60 Sekunden dauern beim ersten Aufruf)

3. **Geben Sie ein:**
   - **Benutzername:** `admin`
   - **Passwort:** Das beim Setup generierte Einmal-Passwort (siehe Onboarding-E-Mail)

4. **Klicken Sie auf "Anmelden"**

---

## 🎉 WENN DER LOGIN FUNKTIONIERT:

**Glückwunsch! Die App ist einsatzbereit!**

### ⚠️ SOFORT NACH DEM LOGIN:

1. **Klicken Sie auf den Tab "⚙️ Einstellungen"**
2. **Ändern Sie das Admin-Passwort**
3. **Notieren Sie sich das neue Passwort sicher!**

---

## ❌ WENN DER LOGIN NICHT FUNKTIONIERT:

**Schicken Sie mir:**
1. Einen Screenshot der Fehlermeldung
2. Einen Screenshot der Environment Variables in Render.com
3. Einen Screenshot des SQL-Editor-Ergebnisses in Supabase

**Dann helfe ich Ihnen sofort weiter!**

---

## 📞 FERTIG?

**Wenn Sie alle Schritte durchgeführt haben, schreiben Sie mir:**

✅ "Fertig - Login funktioniert!"  
oder  
❌ "Problem bei Schritt X.Y" + Screenshot

**Dann teste ich alle Funktionen der App für Sie!**

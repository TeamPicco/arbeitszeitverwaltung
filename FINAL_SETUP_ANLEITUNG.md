# 🎯 FINALE SETUP-ANLEITUNG - Arbeitszeitverwaltung

## ✅ SCHRITT 1: Supabase-Datenbank einrichten

### 1.1 SQL-Datei herunterladen

1. Gehen Sie zu: https://github.com/TeamPicco/arbeitszeitverwaltung/blob/master/supabase_schema_final.sql
2. Klicken Sie auf den Button **"Raw"** (oben rechts)
3. Kopieren Sie den **gesamten Inhalt** (Strg+A, dann Strg+C)

### 1.2 SQL in Supabase ausführen

1. Öffnen Sie: https://supabase.com
2. Melden Sie sich an und öffnen Sie Ihr Projekt **"arbeitszeitverwaltung"**
3. Klicken Sie links im Menü auf **"SQL Editor"**
4. Klicken Sie auf **"New query"**
5. **Fügen Sie die kopierte SQL ein** (Strg+V)
6. Klicken Sie auf **"Run"** (unten rechts)
7. Bestätigen Sie die Warnung mit **"Run this query"**
8. ✅ Sie sollten mehrere grüne Häkchen sehen

---

## ✅ SCHRITT 2: Environment Variables in Render.com setzen

### 2.1 Render.com öffnen

1. Gehen Sie zu: https://dashboard.render.com
2. Klicken Sie auf Ihre App **"arbeitszeitverwaltung"**

### 2.2 Environment Variables hinzufügen

1. Klicken Sie links im Menü auf **"Environment"**
2. Klicken Sie auf **"Add Environment Variable"**
3. Fügen Sie folgende Variablen hinzu:

**Variable 1:**
```
Key: SUPABASE_URL
Value: https://jehomjeanbmkoptknutx.supabase.co
```

**Variable 2:**
```
Key: SUPABASE_KEY
Value: [IHR SUPABASE API KEY - siehe unten]
```

**Variable 3:**
```
Key: BUNDESLAND
Value: NW
```

**Variable 4:**
```
Key: SESSION_TIMEOUT_MINUTES
Value: 480
```

4. Klicken Sie auf **"Save Changes"**

### 2.3 Supabase API Key finden

1. Gehen Sie zu Supabase: https://supabase.com
2. Öffnen Sie Ihr Projekt **"arbeitszeitverwaltung"**
3. Klicken Sie links auf **"Settings"** (Zahnrad-Symbol)
4. Klicken Sie auf **"API"**
5. Kopieren Sie den **"anon public"** Key
6. Fügen Sie ihn als `SUPABASE_KEY` in Render.com ein

---

## ✅ SCHRITT 3: App neu starten

1. In Render.com klicken Sie oben rechts auf **"Manual Deploy"**
2. Wählen Sie **"Clear build cache & deploy"**
3. ⏳ Warten Sie 2-3 Minuten

---

## ✅ SCHRITT 4: Login testen

1. Öffnen Sie: https://arbeitszeitverwaltung.onrender.com
2. Melden Sie sich an mit:
   - **Benutzername:** `admin`
   - **Passwort:** `admin123`

---

## 🎉 FERTIG!

Wenn der Login funktioniert, ist die App einsatzbereit!

### ⚠️ WICHTIG: Passwort ändern!

Nach dem ersten Login:
1. Gehen Sie zum Tab **"⚙️ Einstellungen"**
2. Ändern Sie das Admin-Passwort
3. Notieren Sie sich das neue Passwort sicher

---

## 📋 Nächste Schritte

1. **Mitarbeiter anlegen** (Tab "👥 Mitarbeiterverwaltung")
2. **Benutzerkonten erstellen** für jeden Mitarbeiter
3. **Arbeitsverträge hochladen** (optional)
4. **Zeiterfassung testen**

---

## 🆘 Bei Problemen

Falls der Login nicht funktioniert:
1. Überprüfen Sie, ob die SQL wirklich ausgeführt wurde (grüne Häkchen in Supabase)
2. Überprüfen Sie, ob alle Environment Variables in Render.com gesetzt sind
3. Starten Sie die App neu mit "Clear build cache & deploy"

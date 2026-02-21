# E-Mail-Benachrichtigungen einrichten

## Übersicht

CrewBase sendet automatisch E-Mails für:
- **Urlaubsanträge** → an piccolo_leipzig@yahoo.de
- **Dienstplan-Fertigstellung** → an jeweiligen Mitarbeiter
- **Urlaubsgenehmigungen** → an jeweiligen Mitarbeiter

## SMTP-Konfiguration

### Schritt 1: E-Mail-Anbieter wählen

Sie können einen der folgenden SMTP-Anbieter verwenden:

#### Option A: Gmail (empfohlen für kleine Teams)
1. Gmail-Konto erstellen oder bestehendes verwenden
2. App-Passwort erstellen:
   - Google-Konto → Sicherheit → 2-Faktor-Authentifizierung aktivieren
   - App-Passwörter → "Mail" auswählen → Passwort generieren

#### Option B: Yahoo Mail
1. Yahoo-Konto verwenden
2. App-Passwort erstellen:
   - Kontoeinstellungen → Sicherheit → App-Passwörter generieren

#### Option C: Professioneller SMTP-Service
- **SendGrid** (kostenlos bis 100 E-Mails/Tag)
- **Mailgun** (kostenlos bis 5.000 E-Mails/Monat)
- **Amazon SES** (sehr günstig, technisch)

### Schritt 2: Umgebungsvariablen auf Render.com setzen

1. Gehen Sie zu Render.com Dashboard
2. Wählen Sie Ihre App "arbeitszeitverwaltung"
3. Gehen Sie zu **Environment**
4. Fügen Sie folgende Variablen hinzu:

#### Für Gmail:
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=ihre-email@gmail.com
SMTP_PASSWORD=ihr-app-passwort
SMTP_FROM_EMAIL=ihre-email@gmail.com
```

#### Für Yahoo:
```
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=ihre-email@yahoo.de
SMTP_PASSWORD=ihr-app-passwort
SMTP_FROM_EMAIL=ihre-email@yahoo.de
```

#### Für SendGrid:
```
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=ihr-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@ihr-domain.de
```

### Schritt 3: App neu starten

Nach dem Hinzufügen der Umgebungsvariablen:
1. Klicken Sie auf "Save Changes"
2. Render.com startet die App automatisch neu
3. E-Mail-Benachrichtigungen sind jetzt aktiv

## Testen

### Test 1: Urlaubsantrag
1. Als Mitarbeiter einloggen
2. Urlaubsantrag stellen
3. Prüfen Sie piccolo_leipzig@yahoo.de auf E-Mail

### Test 2: Urlaubsgenehmigung
1. Als Admin einloggen
2. Urlaubsantrag genehmigen
3. Mitarbeiter erhält E-Mail-Benachrichtigung

## Fehlerbehebung

### E-Mails werden nicht gesendet

1. **Prüfen Sie die Logs auf Render.com:**
   - Dashboard → Logs
   - Suchen Sie nach "Fehler beim Senden der E-Mail"

2. **Häufige Probleme:**
   - App-Passwort statt normales Passwort verwenden
   - 2-Faktor-Authentifizierung aktiviert?
   - SMTP-Port korrekt? (587 für TLS)
   - Firewall-Einstellungen

3. **Gmail-spezifisch:**
   - "Weniger sichere Apps" ist veraltet, verwenden Sie App-Passwörter
   - Prüfen Sie, ob Google den Login blockiert hat

## Sicherheit

⚠️ **Wichtig:**
- Verwenden Sie IMMER App-Passwörter, nie Ihr Haupt-Passwort
- Teilen Sie SMTP-Zugangsdaten niemals öffentlich
- Umgebungsvariablen auf Render.com sind verschlüsselt gespeichert

## Support

Bei Problemen mit der E-Mail-Konfiguration:
1. Prüfen Sie die Logs auf Render.com
2. Testen Sie SMTP-Zugangsdaten mit einem E-Mail-Client
3. Kontaktieren Sie Ihren E-Mail-Anbieter bei Authentifizierungsproblemen

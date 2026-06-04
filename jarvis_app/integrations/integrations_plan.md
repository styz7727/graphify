# Jarvis Integrations — Planungsdokument (v5)

Dieses Dokument beschreibt geplante externe Integrationen. Kein ausführbarer Code.

---

## 1. Microsoft Teams (v5)

**Technologie:** Microsoft Graph API  
**Authentifizierung:** OAuth2 mit Azure App-Registrierung (MSAL)  
**Benötigte Scopes:** `Chat.ReadWrite`, `ChannelMessage.Send`, `Calendars.Read`  
**Schritte:**
1. App in Azure Portal registrieren (portal.azure.com)
2. `msal` Python-Paket installieren
3. Token sicher in Windows Credential Manager speichern (nie in .env)
4. Read-only zuerst implementieren, Senden nur mit CONFIRM

**Sicherheitsregel:** Nachrichten werden niemals automatisch gesendet.

---

## 2. Google Calendar (v5)

**Technologie:** Google Calendar API v3  
**Authentifizierung:** OAuth2 (google-auth-oauthlib)  
**Scopes:** `https://www.googleapis.com/auth/calendar.readonly` (v5a), dann `.events` (v5b)  
**Schritte:**
1. Google Cloud Console: Projekt + OAuth2-Credentials anlegen
2. `google-auth-oauthlib` installieren
3. Token sicher lokal speichern (nicht in Klartext)
4. v1: nur lesen; v5b: schreiben nur mit CONFIRM + Vorschau

---

## 3. Outlook Calendar (v5)

**Technologie:** Microsoft Graph API (gleicher Weg wie Teams)  
**Scope:** `Calendars.Read`, `Calendars.ReadWrite`  
**Besonderheit:** Termine immer als Vorschau zeigen, nie automatisch erstellen.

---

## 4. WhatsApp (v5)

**Offizielle Option:** WhatsApp Business Platform API (Meta)  
**Voraussetzung:** Business Account, verifizierte Telefonnummer  
**Wichtig:** Inoffizielle Bibliotheken (z.B. yowsup, whatsapp-web.js) sind ToS-widrig und unsicher. Nur offizielle API verwenden.  
**Sicherheitsregel:** Nachrichten niemals automatisch senden. Nur mit CONFIRM.

---

## 5. TradingView (dauerhaft Browser-only)

TradingView hat keine öffentliche Daten-API für Privatkunden.  
→ Jarvis öffnet Charts immer im Browser (wie implementiert).  
→ Keine Automatisierung über inoffizielle APIs.

---

## 6. Open-Meteo Wetter (v1 — bereits implementiert)

- Kostenlos, kein API-Key erforderlich
- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Keine Registrierung nötig

---

## Empfohlene Reihenfolge

| Priorität | Integration          | Aufwand | Risiko |
|-----------|----------------------|---------|--------|
| 1         | Google Calendar Read | mittel  | niedrig |
| 2         | Outlook Calendar     | mittel  | niedrig |
| 3         | Teams Read           | hoch    | mittel |
| 4         | Teams Send           | hoch    | hoch — nur mit CONFIRM |
| 5         | WhatsApp             | hoch    | hoch — nur offiziell |

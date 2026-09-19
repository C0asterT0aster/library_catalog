# iOS Scanner - Korrigierte Automation für UI

## Problem
Die Automation im QUICK_START_TEST.md hat YAML-Liste-Format (`- id:`), aber die Home Assistant UI braucht ein einzelnes Automation-Objekt ohne den führenden Bindestrich.

## Lösung

### Option 1: Über die UI (Empfohlen)

1. Gehe zu **Einstellungen** → **Automationen & Szenen**
2. Klicke **Automation erstellen** → **Neue Automation erstellen**
3. Klicke die **⋮** (drei Punkte) oben rechts
4. Klicke **In YAML bearbeiten**
5. **Lösche alles** was dort steht
6. Kopiere das folgende (OHNE den führenden Bindestrich!):

```yaml
id: process_scanned_book_from_ios_test
alias: "Process Scanned Book from iOS (Test)"
description: "Test automation for book scanning"
trigger:
  - platform: webhook
    webhook_id: ios_book_scanner
    local_only: false
condition:
  - condition: state
    entity_id: input_boolean.book_scanning_active
    state: "on"
action:
  - variables:
      scanned_isbn: "{{ trigger.json.isbn }}"
  - service: library_catalog.add_book
    data:
      isbn: "{{ scanned_isbn }}"
      location:
        room: "{{ states('input_text.book_scan_room') }}"
        shelf: "{{ states('input_text.book_scan_shelf') }}"
        compartment: "{{ states('input_text.book_scan_compartment') }}"
    continue_on_error: true
  - service: input_number.increment
    target:
      entity_id: input_number.books_scanned_today
  - service: input_datetime.set_datetime
    target:
      entity_id: input_datetime.last_book_scan_time
    data:
      timestamp: "{{ now().timestamp() }}"
  - service: notify.mobile_app_DEIN_GERÄTENAME
    data:
      title: "✅ Book Added"
      message: "ISBN {{ scanned_isbn }} added to {{ states('input_text.book_scan_room') }}"
mode: single
```

**WICHTIG:** Ersetze `notify.mobile_app_DEIN_GERÄTENAME` mit deinem echten Gerätenamen!

### Option 2: Über automations.yaml Datei

Wenn du die `automations.yaml` Datei direkt bearbeitest, brauchst du den Bindestrich:

1. Öffne **File Editor** oder **Studio Code Server**
2. Öffne `automations.yaml`
3. Gehe ans Ende der Datei
4. Füge hinzu (MIT Bindestrich am Anfang):

```yaml
- id: process_scanned_book_from_ios_test
  alias: "Process Scanned Book from iOS (Test)"
  description: "Test automation for book scanning"
  trigger:
    - platform: webhook
      webhook_id: ios_book_scanner
      local_only: false
  condition:
    - condition: state
      entity_id: input_boolean.book_scanning_active
      state: "on"
  action:
    - variables:
        scanned_isbn: "{{ trigger.json.isbn }}"
    - service: library_catalog.add_book
      data:
        isbn: "{{ scanned_isbn }}"
        location:
          room: "{{ states('input_text.book_scan_room') }}"
          shelf: "{{ states('input_text.book_scan_shelf') }}"
          compartment: "{{ states('input_text.book_scan_compartment') }}"
      continue_on_error: true
    - service: input_number.increment
      target:
        entity_id: input_number.books_scanned_today
    - service: input_datetime.set_datetime
      target:
        entity_id: input_datetime.last_book_scan_time
      data:
        timestamp: "{{ now().timestamp() }}"
    - service: notify.mobile_app_DEIN_GERÄTENAME
      data:
        title: "✅ Book Added"
        message: "ISBN {{ scanned_isbn }} added to {{ states('input_text.book_scan_room') }}"
  mode: single
```

## Gerätenamen finden

Dein Gerätenamen findest du hier:
1. **Einstellungen** → **Geräte & Dienste**
2. Klicke auf **Mobile App**
3. Finde dein iPhone in der Liste
4. Der Name steht oben, z.B.:
   - `mobile_app_iphone`
   - `mobile_app_iphone_von_malte`

## Häufige Fehler

❌ **"not a valid option at '['0']"**
- Ursache: Führender Bindestrich `-` in der UI
- Lösung: Bindestrich entfernen wenn du über UI erstellst

❌ **"Entity not found"**
- Ursache: Input helpers nicht erstellt
- Lösung: Gehe zurück zu Schritt 1 und erstelle die Helpers

❌ **"Service not found"**
- Ursache: Library Catalog nicht installiert
- Lösung: Installiere die Integration zuerst

## Test nach dem Erstellen

Nach dem Speichern teste mit:

```bash
curl -X POST http://DEINE_HA_IP:8123/api/webhook/ios_book_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"9780451524935"}'
```

Du solltest eine Benachrichtigung auf deinem iPhone bekommen!

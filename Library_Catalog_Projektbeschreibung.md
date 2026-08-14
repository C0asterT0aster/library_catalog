# Library Catalog -- Projektbeschreibung und Entwickler-Prompt

## Ziel

Entwickle eine HACS-kompatible Home-Assistant-Custom-Integration
**Library Catalog** zur Verwaltung physischer Bücher.

## Funktionen

-   ISBN per Barcode scannen
-   Open Library API, Google Books als Fallback
-   SQLite-Datenbank `/config/library_catalog.db`
-   Speicherung von ISBN, Titel, Untertitel, Autoren, Verlag, Jahr,
    Beschreibung, Cover, Sprache, Seiten, Raum, Regal, Fach,
    Zeitstempeln
-   Suche nach Titel, Autor oder ISBN
-   Dashboard mit Cover und Standort

## Architektur

    custom_components/library_catalog/
    ...

## Services

-   library_catalog.add_book
-   library_catalog.search
-   library_catalog.delete_book

## Barcode

Webhook `/api/webhook/library_scanner`

## Entwicklungsreihenfolge

1.  Grundintegration
2.  SQLite
3.  APIs
4.  Services
5.  Barcode
6.  Dashboard
7.  HACS

# Prompt

Du bist ein erfahrener Home-Assistant-Entwickler. Erstelle eine
vollständig funktionsfähige, HACS-kompatible Custom Integration namens
Library Catalog. Nutze Config Entries, async_setup_entry,
DataUpdateCoordinator, SQLite, Open Library mit Google Books als
Fallback. Implementiere alle beschriebenen Funktionen. Erstelle
sämtliche Dateien (README, hacs.json, manifest.json, Python-Dateien,
Übersetzungen, Dashboard-Beispiele) vollständig und liefere das Projekt
commitweise, sodass es jederzeit lauffähig bleibt.

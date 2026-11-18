# Fragen und Fehlerbehebung

[Deutsch](./faq.md) | [English](../en/faq.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Produkt und Zugang

### Was ist das Produkt?

Ein Plugin mit Coaching-Skill und lokalem Python-Helfer. Es bringt weder ein eigenes Modell noch Chat-Anwendung oder gehostetes Backend mit.

### Welche Lizenz gilt?

[MIT](../../LICENSE), auch in [plugin.json](../../plugin.json) hinterlegt. Das MVP hat keine Zahlungen, Kundenkonten oder Lizenzdurchsetzung. Host-Zugang und Modellnutzung unterliegen eigenen Bedingungen.

## Voraussetzungen

Für die Installation füge den Marketplace `https://github.com/draftm0de/ai.plugins` hinzu und wähle Interview Coach. Kein ZIP oder lokaler Checkout ist nötig. Der lokale Speicherhelfer benötigt Python 3.10+, aber kein Git. Host-Ausführung und dauerhafte Speicherung müssen verfügbar und geprüft sein.

## Datenschutz und Speicherung

### Erinnert sich der Coach im nächsten Chat?

Nur wenn der Host den bestätigten privaten Speicher wieder lesen kann. Lokale Pfade existieren nicht automatisch in der Cloud, und Anhänge sind kein beschreibbarer Zustand.

### Was bedeutet „Nicht speichern“?

Keine Skill-Dateien, Einstellungen, Recherchearchive, Berichte oder automatischen Exporte. Der Host kann den Chat unabhängig davon aufbewahren.

### Wohin gehört mein Lebenslauf?

In einen separaten privaten Arbeitsbereich oder als privat bereitgestellte Datei. Keine echten Lebensläufe, Gesprächsprotokolle, Tokens oder privaten Dateien in diesem Repository oder in öffentlichen Issues.

## Fehlerbehebung

### Plugin fehlt oder alte Version aktiv?

Prüfe den Marketplace Draftmode AI Plugins, Repository-Zugriff und Berechtigungen. Synchronisiere den Katalog, wähle Interview Coach und öffne eine neue Sitzung. Siehe [Installation](installation.md). Eine lokale CLI-Installation belegt keine Sichtbarkeit in der Web- oder Kontooberfläche.

### ChatGPT-Upload fehlt?

Für diesen Installationsweg wird kein Upload verwendet. Füge das Marketplace-Repository hinzu; ist diese Option gesperrt, kläre die Konto- und Arbeitsbereichsfreigaben mit deiner Administration.

### „busy“, „stale state“ oder „pending transaction“?

Warte bei einer Sperre auf den anderen Prozess, ohne die Lock-Datei zu löschen. Lies bei veraltetem Zustand neu und gleiche Änderungen ab. Verwende bei ausstehender Transaktion `recover`; erhalte das Journal und löse externe Konflikte manuell. Ein fehlgeschlagener Befehl belegt keinen gespeicherten Bericht/Zustand.

### Warum wird die Fortsetzung abgelehnt?

Nur strukturierte `paused`-Checkpoints ohne bereits gespeicherte Fortsetzung sind fortsetzbar. Abgeschlossene, gestoppte und alte Markdown-Läufe erfordern eine neue Sitzung oder manuelle Sichtung. Siehe [Speicherung](storage.md).

## Grenzen der Prüfung

Eine höhere Note bewertet eine konkrete Antwort, nicht stabile Kompetenz oder Einstellungschancen. Ein überarbeiteter Versuch nach Coaching ist kein unabhängiger Kompetenznachweis.

Die [Beispiele](screens.md) enthalten gerenderte Auszüge eines fiktiven CLI-Tests, keine Host-Screenshots. Deterministische Tests decken Paketierung, Installer und lokale Speicherung samt Nebenläufigkeit, Fehlerwiederherstellung und paketiertem Helfer ab. Optionale Modelltests prüfen heuristisch Gesprächsverhalten. Native Oberfläche, Berechtigungen und Speicherung über neue Chats hinweg bleiben separat abzunehmen.

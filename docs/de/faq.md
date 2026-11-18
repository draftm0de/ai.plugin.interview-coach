# Fragen und Fehlerbehebung

[Deutsch](./faq.md) | [English](../en/faq.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Produkt und Zugang

### Was ist das Produkt?

Ein Plugin mit Coaching-Skill und lokalem Python-Helfer. Es bringt weder ein eigenes Modell noch Chat-Anwendung oder gehostetes Backend mit.

### Welche Lizenz gilt?

[MIT](../../LICENSE), auch in [plugin.json](../../plugin.json) hinterlegt. Das MVP hat keine Zahlungen, Kundenkonten oder Lizenzdurchsetzung. Host-Zugang und Modellnutzung unterliegen eigenen Bedingungen.

## Voraussetzungen

Zum Bauen und Installieren brauchst du Git für den Clone, Bash und Python 3.10+; Make ist optional. Ein bereits gebautes ZIP kannst du ohne Repository hochladen, sofern dein Host das erlaubt. Der lokale Speicherhelfer benötigt Python, aber kein Git. Host-Ausführung und dauerhafte Speicherung müssen verfügbar und geprüft sein.

## Datenschutz und Speicherung

### Erinnert sich der Coach im nächsten Chat?

Nur wenn der Host den bestätigten privaten Speicher wieder lesen kann. Lokale Pfade existieren nicht automatisch in der Cloud, und Anhänge sind kein beschreibbarer Zustand.

### Was bedeutet „Nicht speichern“?

Keine Skill-Dateien, Einstellungen, Recherchearchive, Berichte oder automatischen Exporte. Der Host kann den Chat unabhängig davon aufbewahren.

### Wohin gehört mein Lebenslauf?

In einen separaten privaten Arbeitsbereich oder als privat bereitgestellte Datei. Keine echten Lebensläufe, Gesprächsprotokolle, Tokens oder privaten Dateien in diesem Repository oder in öffentlichen Issues.

## Fehlerbehebung

### Plugin fehlt oder alte Version aktiv?

Prüfe Zielhost, ausgegebenen Installationsort und Berechtigungen. Plugin-Upload, frühere Einzel-Skills und lokale Projektquellen sind verschiedene Wege. Öffne eine neue Sitzung und folge der [Installation](installation.md). Eine lokale Installation erscheint nicht automatisch im Web. Aktualisiere den gewünschten Quellstand unter Erhalt eigener Änderungen, baue/installiere erneut beziehungsweise lade das neue ZIP hoch. Das MVP richtet keine automatischen Katalog-Updates ein.

### ChatGPT-Upload fehlt?

Die Option hängt von Konto, Arbeitsbereich und Berechtigungen ab. Ein ZIP-Build schaltet sie nicht frei; prüfe die offiziellen Host-Hinweise mit deiner Administration.

### „busy“, „stale state“ oder „pending transaction“?

Warte bei einer Sperre auf den anderen Prozess, ohne die Lock-Datei zu löschen. Lies bei veraltetem Zustand neu und gleiche Änderungen ab. Verwende bei ausstehender Transaktion `recover`; erhalte das Journal und löse externe Konflikte manuell. Ein fehlgeschlagener Befehl belegt keinen gespeicherten Bericht/Zustand.

### Warum wird die Fortsetzung abgelehnt?

Nur strukturierte `paused`-Checkpoints ohne bereits gespeicherte Fortsetzung sind fortsetzbar. Abgeschlossene, gestoppte und alte Markdown-Läufe erfordern eine neue Sitzung oder manuelle Sichtung. Siehe [Speicherung](storage.md).

## Grenzen der Prüfung

Eine höhere Note bewertet eine konkrete Antwort, nicht stabile Kompetenz oder Einstellungschancen. Ein überarbeiteter Versuch nach Coaching ist kein unabhängiger Kompetenznachweis.

Die [Beispiele](screens.md) enthalten gerenderte Auszüge eines fiktiven CLI-Tests, keine Host-Screenshots. Deterministische Tests decken Paketierung, Installer und lokale Speicherung samt Nebenläufigkeit, Fehlerwiederherstellung und paketiertem Helfer ab. Optionale Modelltests prüfen heuristisch Gesprächsverhalten. Native Oberfläche, Berechtigungen und Speicherung über neue Chats hinweg bleiben separat abzunehmen.

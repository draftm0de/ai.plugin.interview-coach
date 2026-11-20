# Fragen und Fehlerbehebung

[Deutsch](./faq.md) | [English](../en/faq.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Produkt und Zugang

### Was ist das Produkt?

Ein Plugin mit fünf Coaching-Skills und einer lokalen Python-Runtime für Claude Code und Codex. Es bringt weder ein eigenes Modell noch Chat-Anwendung oder gehostetes Backend mit.

### Welche Lizenz gilt?

[MIT](../../LICENSE), auch in [plugin.json](../../plugin.json) hinterlegt. Das MVP hat keine Zahlungen, Kundenkonten oder Lizenzdurchsetzung. Host-Zugang und Modellnutzung unterliegen eigenen Bedingungen.

## Voraussetzungen

Für die Installation füge den Marketplace `https://github.com/draftm0de/ai.plugins` hinzu und wähle Interview Coach. Kein ZIP oder lokaler Checkout ist nötig. Die Runtime benötigt Python 3.10+; Git nur für den Git-Speicher. Host-Ausführung und dauerhafte Speicherung müssen verfügbar und geprüft sein.

## Datenschutz und Speicherung

### Erinnert sich der Coach im nächsten Chat?

Nur wenn der Host den bestätigten privaten Speicher wieder lesen kann. Lokale Pfade existieren nicht automatisch in der Cloud, und Anhänge sind kein beschreibbarer Zustand.

### Was bedeutet „Nicht speichern“?

Nichts wird persistiert: keine Dateien, Zeiger, Sperren, Journale, Exporte, CV-Kopien, Stellen, Runs oder Lernstände. Mehrere Bewerber und Stellen bleiben nur im Chat unterscheidbar; ein späterer Chat kennt sie nicht. Der Host kann den Chat unabhängig davon aufbewahren.

### Welche Speicheroptionen gibt es?

Genau drei: **Lokal**, **Git** (nur privates GitHub/GitLab-Repository) und **Nicht speichern**. „Dateien selbst verwalten“ gibt es nicht mehr; bei Speicherfehlern bietet der Coach Wiederherstellung oder eine neue Speicherwahl an.

### Wann ist etwas „remote gespeichert“?

Nur nach einem erfolgreichen Push ohne Force, dessen Remote-Stand geprüft wurde. Eine lokale Änderung oder ein Commit allein ist kein Remote-Erfolg. Bei Konflikten, Rechte- oder Übertragungsfehlern bleibt alles lokal erhalten und der Coach meldet das offen.

### Kann ich mehrere Bewerber in einem Projekt verwalten?

Ja, auch mit gleichem Namen. Jeder Bewerber hat eine eigene ID und eigene Daten; bei Mehrdeutigkeit fragt der Coach nach. Lernstände werden nie gemischt.

### Warum wird mein vorhandener Ordner abgelehnt?

Nur das aktuelle Format 3 wird unterstützt (auch das frühere Format 2 mit Kontrollordner `.zyris` wird abgelehnt). Ältere Layouts oder fremde Dateien werden vor jedem Schreibzugriff abgelehnt und bleiben unverändert; es gibt keine Migration. Wähle ein leeres Ziel.

### Warum meldet der CV-Import „partial“ oder fehlende Werkzeuge?

Bilder, nicht lesbare Seiten, Kopf-/Fußzeilen oder eine fehlende Textebene werden offengelegt. Für PDF braucht die Runtime `pdftotext`, `mutool` oder `pypdf`; sie installiert nichts und erfindet keine Extraktion.

### Wohin gehört mein Lebenslauf?

In einen separaten privaten Arbeitsbereich oder als privat bereitgestellte Datei. Keine echten Lebensläufe, Gesprächsprotokolle, Tokens oder privaten Dateien in diesem Repository oder in öffentlichen Issues.

## Fehlerbehebung

### Plugin fehlt oder alte Version aktiv?

Prüfe den Marketplace Draftmode AI Plugins, Repository-Zugriff und Berechtigungen. Synchronisiere den Katalog, wähle Interview Coach und öffne eine neue Sitzung. Siehe [Installation](installation.md). Eine lokale CLI-Installation belegt keine Sichtbarkeit in der Web- oder Kontooberfläche.

### Unterstützt das Plugin ChatGPT oder Claude Chat?

Nein. Unterstützt werden Claude Code und Codex mit lokalen Projektordnern. Ein gehosteter Sandbox-Pfad ist nicht automatisch dein Rechner; der Coach behauptet keine Dauerhaftigkeit, die er nicht prüfen kann.

### „busy“, „stale state“ oder „pending transaction“?

Warte bei einer Sperre auf den anderen Prozess, ohne die Lock-Datei zu löschen. Lies bei veraltetem Zustand neu und gleiche Änderungen ab. Verwende bei ausstehender Transaktion `recover`; erhalte das Journal und löse externe Konflikte manuell. Ein fehlgeschlagener Befehl belegt keinen gespeicherten Bericht/Zustand.

### Warum wird die Fortsetzung abgelehnt?

Nur strukturierte `paused`-Checkpoints ohne bereits gespeicherte Fortsetzung sind fortsetzbar. Abgeschlossene und gestoppte Runs sind nicht fortsetzbar. Nicht unterstützte Run-Formate blockieren Workspace-Operationen vor Schreibzugriffen; sie bleiben unverändert und werden nicht migriert. Siehe [Speicherung](storage.md).

## Grenzen der Prüfung

Eine höhere Note bewertet eine konkrete Antwort, nicht stabile Kompetenz oder Einstellungschancen. Ein überarbeiteter Versuch nach Coaching ist kein unabhängiger Kompetenznachweis.

Die [Beispiele](screens.md) enthalten gerenderte Auszüge eines fiktiven CLI-Tests, keine Host-Screenshots. Deterministische Tests decken Manifeste, Paketierung, Bewerber-/Stellen-/Run-Logik, Extraktion, Wiederherstellung und den Git-Ablauf gegen lokale Bare-Repositories ab – **nicht** GitHub/GitLab live. Modellszenarien sind heuristisch. Isolierte Claude-Code-/Codex-Läufe und Live-Git bleiben offen; siehe die [Abnahmematrix](../acceptance.md).

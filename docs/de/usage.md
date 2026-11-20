# Den Coach nutzen

[Deutsch](./usage.md) | [English](../en/usage.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Einstiegspunkte je Host

Alle Fähigkeiten liegen in fünf Skills desselben Plugins. Natürliche Sprache funktioniert in beiden Hosts („Lege einen Bewerber an“, „Bereite die Stelle bei ACME vor“). Zusätzlich gibt es host-spezifische Aufrufe:

| Aufgabe | Skill | Claude Code | Codex |
|---|---|---|---|
| Einrichtung, Status, Weiterleitung | `interview-coach` | `/interview-coach:interview-coach setup` | `$interview-coach` bzw. Skill-Auswahl |
| Bewerber anlegen | `candidate-create` | `/interview-coach:candidate-create` | `$candidate-create` |
| Allgemeines Training | `candidate-training` | `/interview-coach:candidate-training` | `$candidate-training` |
| Stelle vorbereiten | `job-create` | `/interview-coach:job-create` | `$job-create` |
| Training für eine gespeicherte Stelle | `job-training` | `/interview-coach:job-training` | `$job-training` |

Die Schreibweisen folgen der jeweiligen Host-Dokumentation und sind in den isolierten Host-Läufen dieses Repositories **nicht** nachgewiesen (siehe [Abnahme](../acceptance.md)). Ein nativer Befehl `:job-create` ohne Hostunterstützung wird nicht behauptet. Es gibt keine automatische Aktivierung beim Öffnen eines Projekts: Die Einrichtung startet bei der ersten Nutzung oder mit ausdrücklichem `setup`.

## 1. Einrichten

> Starte die Einrichtung von interview-coach. Verwende Deutsch.

Der Coach bietet genau zwei Speicheroptionen an: **Lokal**, **Nicht speichern**. Danach fragt er nach lokalem Pfad und bestätigt das Ziel. Details: [Speicherung](storage.md).

## 2. Bewerber anlegen (`candidate-create`)

Name erfragen → eindeutige ID → „Gibt es einen Lebenslauf?“.

- **Mit CV** (PDF, DOCX, Markdown): Datei bereitstellen. Das Original bleibt bytegleich, daraus entsteht eine Markdown-Übertragung und ein Profil. Lücken (Bilder, nicht lesbare Seiten, fehlende Textebene) werden offengelegt, Teilimporte nicht als fertig gemeldet. Fehlt ein Werkzeug (z. B. für PDF: `pdftotext`, `mutool` oder Python-`pypdf`), nennt der Coach genau, was fehlt; es wird nichts installiert und nichts erfunden.
- **Ohne CV**: Der Coach stellt jeweils eine Frage (Erfahrung, Ausbildung, Fähigkeiten, Projekte, Ziele), erstellt einen als Entwurf gekennzeichneten CV und ein Profil und lässt dich die Angaben bestätigen. Erst dann gelten sie als verifizierte Grundlage; ein Entwurf kann gespeichert und angezeigt werden, dient aber nicht als verlässliche Evidenz. Der stellenbezogene Abgleich und profilbasiertes Training warten auf deine Bestätigung (Stellenaufnahme, Unternehmensrecherche und allgemeines Training nicht).

Am Ende siehst du Ergebnis, offene Punkte und den tatsächlichen Speicherort. Mehrere Bewerber pro Projekt sind möglich, auch gleichnamige; bei Mehrdeutigkeit fragt der Coach nach.

## 3. Allgemeines Training (`candidate-training`)

Bewerber wählen → Profil, Lernstand und frühere Runs werden geladen → eine Frage pro Turn, ausgerichtet an Fähigkeiten, Erfahrung, Rolle und Zielen. Du erhältst **Gesamtbewertung x/10**, passende Einzelkriterien, Stärken und Verbesserungen; Formulierungsvorschläge nutzen nur deine belegten Angaben. Jeder gespeicherte Durchlauf ist ein eigener unveränderlicher Run, der Lernstand ändert sich nur beim gewählten Bewerber.

## 4. Stelle vorbereiten (`job-create`)

Bewerber wählen → Stellenlink oder Upload (Link mit Abrufdatum; ist der Link nicht erreichbar, bittest du den Text/Upload nach) → Unternehmen (falls unklar) → bekannte Interviewteilnehmer („unbekannt“ ist erlaubt und blockiert nichts) → öffentliche, berufliche Recherche mit Quellen und Datum, Namensgleichheiten werden vor der Zuordnung geklärt, keine psychologischen Profile → Abgleich Anforderungen ↔ Belege/Lücken → gespeicherte Vorbereitung mit Themen und offenen Fragen. Eine Stelle gehört einem Bewerber und ist für mehrere Trainings wiederverwendbar.

## 5. Training für eine Stelle (`job-training`)

Bewerber und Stelle wählen → vorhandene Recherche wird wiederverwendet, zeitabhängige Fakten werden bei Bedarf aktualisiert → Fragen und Bewertung richten sich nach Anforderungen, Seniorität und Lücken → jeder Durchlauf ist ein eigener Run mit Bewerber- und Stellenzuordnung. Der bewerberübergreifende Lernstand bleibt getrennt von stellenspezifischen Passungslücken.

## Modi und Steuerung

| Modus | Zweck | Rückmeldung |
|---|---|---|
| `general` | Allgemeines Training | nach jeder Antwort |
| `targeted` | Gespeicherte Stelle | nach jeder Antwort |
| `drill` | Einzelne Lernlücke, zweiter Versuch | gezielt |
| `mock` | Ununterbrochene Simulation | am Ende |
| `briefing` | Kompakte Vorbereitung | ohne Antwortbewertung |

- **Nachfragen:** Fehlt in deiner Antwort eine wesentliche, tatsächlich gestellte Anforderung oder ist etwas mehrdeutig, stellt der Interviewer genau eine konkrete Nachfrage zur selben Hauptfrage – ohne vorher Lösung, Musterantwort, Bewertung oder Verbesserungsliste zu geben. Du musst nicht die ganze Antwort wiederholen. Bei vollständigen Antworten gibt es keine künstliche Nachfrage; es gibt keine feste Quote und keine endlose Schleife. Die Bewertung trennt Erstantwort und Ergänzungen (spontan, nach Nachfrage selbst konkretisiert, offen, mit Hilfe); die Anzahl der Nachfragen allein kostet keine Punkte. Im Mock-Modus gibt es natürliche Nachfragen, Bewertung erst am Ende. Details: `skills/_shared/references/followup.md`.
- `stop` / `beenden` / `abbrechen` beendet sofort ohne zweite Bestätigung; bei gespeichertem Bewerber entsteht ein Teilrun (`stopped_early`).
- `pause` speichert einen Checkpoint; die Fortsetzung läuft unter neuer Run-ID, nur beim selben Bewerber und derselben Stelle.
- Die Bediensprache gilt für das Projekt. Die Interviewsprache wird pro Bewerber bestätigt; jede Stelle kann eine eigene Abweichung verwenden. Ohne Abweichung gilt der Bewerberstandard. Andere Sprachen als Deutsch/Englisch sind möglich.
- Fortschritt: nur unabhängige Antworten zählen; `improving` nach zwei spontanen erfolgreichen Antworten in verschiedenen Szenarien, `stable` erst nach Bestätigung in einem späteren Lauf ohne Coaching. Modellantworten sind keine Kompetenznachweise.

Technische Rollen können Coding, Debugging, Review und Systemdesign üben; Code wird nur in sicherer, autorisierter Isolation ausgeführt, sonst als „nicht ausgeführt“ bewertet.

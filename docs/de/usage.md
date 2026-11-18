# Den Coach nutzen

[Deutsch](./usage.md) | [English](../en/usage.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Einrichten

Nach der [Installation](installation.md) kannst du schreiben:

> Nutze zyris-interview-coach und starte die Einrichtung. Ich möchte für eine Team-Lead-Rolle im ERP-Umfeld üben. Verwende Deutsch. Nicht speichern.

Der Coach fragt zuerst nach der Speicherart, dann nach einem passenden Ort. Er bestätigt Bedien- und Interviewsprache und fragt nach deinem aktuellen Lebenslauf oder freigegebenen Profil. Ohne Lebenslauf ist allgemeines Training möglich; gezielte Vorbereitung braucht ein bestätigtes Profil und die Stellenanzeige. Bekannte Interviewer sind optional. Originalunterlagen werden nur mit deiner Zustimmung im privaten Arbeitsbereich abgelegt.

## Ablauf auswählen

| Modus | Beispiel | Rückmeldung |
|---|---|---|
| `general` | „Übe allgemeine Fragen für eine Junior-Entwicklerrolle.“ | Nach jeder Antwort |
| `targeted` | „Bereite mich anhand meines Lebenslaufs auf diese Stelle vor.“ | Nach jeder Antwort |
| `drill` | „Trainiere klare Entscheidungsverantwortung mit mir.“ | Gezielte Rückmeldung und eigener zweiter Versuch |
| `mock` | „Simuliere ein Interview ohne Unterbrechungen durch Coaching.“ | Am Ende |
| `briefing` | „Fasse Arbeitgeberfakten, passende Beispiele und meine Rückfragen zusammen.“ | Vorbereitung ohne Antwortbewertung |

Der Coach fragt jeweils eine Frage und passt Tiefe und Kriterien an Rolle und Erfahrung an. Öffentliche Recherche setzt Browserzugriff voraus. Fakten, begründete Annahmen und Unbekanntes bleiben getrennt; Interviewerrecherche beschränkt sich auf beruflich relevante öffentliche Informationen.

## Ausgabe verstehen

In begleiteten Modi erhältst du eine qualitative **Gesamtbewertung x/10**, etwa drei bis sechs passende Einzelkriterien, belegte Stärken, konkrete Verbesserungen und bei Bedarf einen Formulierungsvorschlag. Die Gesamtnote ist kein mechanischer Mittelwert und keine Einstellungswahrscheinlichkeit. Bei zu wenig Inhalt soll der Coach nachfragen statt eine sichere Bewertung zu erfinden.

Deine Originalantwort bleibt von Vorschlägen getrennt. Ein besserer zweiter Versuch nach Coaching belegt noch keine stabile Kompetenz. Laut [Bewertungsregeln](../../skills/zyris-interview-coach/references/evaluation.md) braucht `improving` zwei spontane erfolgreiche Antworten in unterschiedlichen Szenarien; `stable` eine Bestätigung in einer späteren Sitzung ohne Coaching. Eignungslücken für eine Stelle sind von Kommunikationsschwächen getrennt.

## Sitzung steuern

- `stop`, `end`, `beenden` oder `abbrechen` beendet Fragen sofort. Bereits beantwortete Fragen werden zusammengefasst; mit vorher bestätigter Speicherung entsteht ein Teilbericht mit `stopped_early`.
- `finish` beendet vorzeitig, solange Fragen offen sind; nach der letzten geplanten Antwort gilt `completed`.
- `pause` oder `unterbrechen` ermöglicht bei verfügbarer Speicherung einen Checkpoint mit `paused`.
- **Nicht speichern** verhindert Arbeitsbereich, Dateien, Einstellungen, Recherchearchive und automatische Exporte. Die Chat-Aufbewahrung des Hosts bleibt davon getrennt.
- Bedien- und Interviewsprache dürfen verschieden sein. Vor dauerhaften Änderungen der Sprachpräferenz wird eine Bestätigung benötigt.

Diese Wörter gelten als Steuerung, wenn du sie als Befehl verwendest, nicht wenn du sie in einer Antwort zitierst. Ein Speicherversprechen ersetzt keinen bestätigten Schreibvorgang. Bei Fehlern gilt die [Wiederherstellung](storage.md).

## Später fortsetzen

Lass den Coach im bestätigten privaten Arbeitsbereich Einstellungen, Lernstand und frühere Berichte lesen. Einen pausierten lokalen Lauf wählst du ausdrücklich aus; `resume` liefert Checkpoint und aktuellen Zustand. Abgeschlossene oder gestoppte Läufe bleiben Historie.

Ohne Speicherung musst du Kontext erneut bereitstellen. Ein alter Chat, Anhang oder temporärer Cloud-Arbeitsbereich garantiert keine dauerhafte Speicherung.

## Spezialisierte Abläufe

Technische Interviews können Coding, Debugging, Code Review, SQL, Tests, Sicherheit, CI/CD, Betrieb und Systemdesign umfassen. Aufgaben sollen Ein-/Ausgaben, Grenzen, Laufzeit, Zeitrahmen und Bewertungskriterien nennen. Lösungen werden nicht vor deinem Versuch verraten.

Code darf nur in einer geeigneten autorisierten isolierten Umgebung ausgeführt werden. Ohne sicheren Runner wird statisch geprüft und ausdrücklich „nicht ausgeführt“ vermerkt. Ein Modellurteil ersetzt keinen bestandenen Test.

Für wiederholte gezielte Vorbereitung werden `jobs/<job-id>/job.md`, `research.md` und `preparation.md` wiederverwendet. Recherche enthält Quellen, Abrufdatum und `verified | inferred | unknown`; veraltete Fakten werden aktualisiert. Ein LinkedIn-Import ist nur als zukünftige Option beschrieben, nicht implementiert.

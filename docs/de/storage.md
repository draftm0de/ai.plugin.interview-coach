# Speicherung und Wiederherstellung

[Deutsch](./storage.md) | [English](../en/storage.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

Die maßgebliche Beschreibung steht in [storage.md der Skills](../../skills/_shared/references/storage.md); diese Seite erklärt sie für Nutzer.

## Zwei Speicheroptionen

Beim ersten Gebrauch (oder mit `setup`) fragt der Coach zuerst nach der Speicherart und danach nach dem konkreten Ziel. Der aktuelle Projektordner darf vorgeschlagen werden, wird aber nie ungefragt Speicherziel.

| Option | Bedeutung |
|---|---|
| **Lokal** | Ein von dir benanntes, dauerhaft zugängliches Verzeichnis. Lese-/Schreibrechte werden vor der Einrichtung geprüft. |
| **Nicht speichern** | Nichts wird persistiert: keine Dateien, Zeiger, Sperren, Journale, Exporte, CV-Kopien, Stellen, Runs oder Lernstände. Mehrere Bewerber und Stellen bleiben nur im Chat unterscheidbar; ein späterer Chat kennt sie nicht. `stop` liefert eine Zusammenfassung im Chat. |

„Dateien selbst verwalten“ gibt es nicht mehr, weder als Modus noch als Fallback. Bei Speicherfehlern zeigt der Coach den Fehler und bietet Wiederherstellung oder eine neue Speicherwahl an; er exportiert nichts ungefragt und wechselt den Modus nicht.

## Projektbezogene Zuordnung

Jeder Projektordner hat einen eigenen Zeiger auf sein Speicherziel (`~/.config/zyris/interview-coach/projects/<hash>.json` bzw. unter `$XDG_CONFIG_HOME`). Zwei Projekte schalten einander nicht um, ein Wechsel des Ziels braucht eine ausdrückliche Bestätigung (`--switch`). Alte globale Zeiger werden weder gesucht noch gelesen.

## Datenstruktur (Format 3)

```text
<Speicherziel>/
  workspace.json  preferences.json  README.md  .gitignore
  candidates/<candidate-id>/
    candidate.json  profile.md  profile-history/NNN.md  state.md
    cv/cv-NNN/{original.<ext>, extracted.md, source.json}
    jobs/<job-id>/{job.json, postings/, research/, match/, preparation/}
    runs/<run-id>.md
  .journal/      (Sperren/Journale/Staging, geschützt, nicht in Git)
```

- **Bewerber-IDs** (`c-erika-beispiel-3f9a1c2b`) sind stabil und eindeutig; gleiche Namen sind erlaubt. Namen sind Daten und werden nie zu Pfaden.
- **CV**: Das Original bleibt bytegleich (SHA-256 in `source.json`); `extracted.md` bildet den Inhalt ab, nicht das Layout. Status `complete` oder `partial` (Lücken wie Bilder, nicht lesbare Seiten, Kopf-/Fußzeilen, fehlende Textebene). Teilimporte gelten nicht als fertig.
- **Profil**: `missing`, `draft` oder `confirmed`. Bestätigt gilt es erst, nachdem du die fachlichen Angaben bestätigt hast. Quelle der Aussagen (CV, Nutzerangabe, Modellvorschlag) bleibt erkennbar.
- **Stellen** gehören genau einem Bewerber. Ausschreibung, Recherche (mit Quellen und Abrufdatum), Abgleich und Vorbereitung sind fortlaufend nummerierte Snapshots; frühere Stände und die Original-Ausschreibung bleiben erhalten.
- **Runs** sind unveränderlich (Run-Format 4); der Kopf nennt `candidate_id`, optional `job_id` und je Hauptfrage `q-N` den Dialog: Originalantwort, Nachfragen (`q-N-fM`, Wortlaut, Art, Anlass, Antwort, Hinweis-Flag, Lücken) und Wiederholungsversuche. `answered_count` zählt nur Hauptfragen; `followup_count`, `followup_answered_count` und `retry_count` werden getrennt geführt. Runs im Format 3 (ohne Dialogdaten) werden vor Schreibzugriffen abgelehnt und nicht migriert. Der **Lernstand** (`state.md`) gilt pro Bewerber und bewerberübergreifend über Stellen; stellenspezifische Passungslücken stehen im `match`-Snapshot der Stelle.

## Entfernte Speicherart

Git-Speicherung wird nicht mehr angeboten. Bestehende Git-Konfigurationen werden ohne Änderungen abgelehnt; es gibt keine automatische Migration in lokalen Speicher.

## Fehler und Wiederherstellung (lokal)

Jeder Bewerber hat eigene Sperre und eigenes Journal. Ein Lauf wird erst nach Inhaltsprüfung als gespeichert gemeldet. Bericht und Lernstand sind keine gemeinsam atomare Mehrdatei-Transaktion; `.journal/pending.json` hält die Absicht fest.

- Ausstehendes Journal → `recover`; Konflikte mit externen Änderungen manuell lösen, Journal behalten.
- Kein Journal, Schreibfehler → Ursache beheben, gleiche Run-ID mit ursprünglichem State-Hash wiederholen.
- Inhalte vorhanden, Dauerhaftigkeit unbestätigt → prüfen, nicht überschreiben, keinen zweiten Lauf anlegen.
- „busy“ → warten, `.journal/lock` nicht löschen. „stale state“ → neu lesen und inhaltlich abgleichen.
- Unterbrochene Bewerber- oder Stellenanlage bleibt ein nicht nutzbarer Entwurf (`creating`); `candidate-recover` schließt ihn ab, ohne Vorhandenes zu überschreiben. Unterbrochenes CV-Staging unter `.journal/stage-*` wird nie automatisch gelöscht.

## Das Verzeichnis `.journal`

`.journal/` ist geschützte interne Verwaltungs- und Wiederherstellungsdaten (Sperren, ausstehende Transaktionen, Import-Staging); sie können Trainingsantworten oder Lebenslauftext enthalten. Nicht manuell löschen oder verschieben; nie in Git veröffentlichen.

## Formatgrenzen

Es wird nur das aktuelle Format 3 unterstützt. Verzeichnisse mit dem früheren Layout (`state.md`, `candidate/profile.md`, `runs/` im Stamm), fremde Dateien, falsche Schema-Versionen, doppelte JSON-Schlüssel, Run-Dateien ohne aktuelle Metadaten oder mit fremder Bewerber-/Stellenzuordnung werden **vor jedem Schreibzugriff** mit konkretem Grund abgelehnt. Vorhandene Daten werden weder migriert noch gelöscht noch überschrieben; wähle für neue Daten ein leeres Ziel oder gleiche manuell ab.

Garantien gelten für kooperierende Prozesse auf lokalen Dateisystemen; Netzwerk- oder Cloud-Sync-Verzeichnisse sind kein unterstütztes Transaktionsbackend.

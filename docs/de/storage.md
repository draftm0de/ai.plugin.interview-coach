# Speicherung und Wiederherstellung

[Deutsch](./storage.md) | [English](../en/storage.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Speichermodell

Der Python-Helfer implementiert ausschließlich lokale Speicherung. Der private Arbeitsbereich enthält:

```text
workspace/
  README.md
  state.md
  candidate/profile.md
  jobs/<job-id>/job.md
  jobs/<job-id>/research.md
  jobs/<job-id>/preparation.md
  runs/
  preferences.json
```

`preferences.json` entsteht bei bestätigter Sprachspeicherung. Ein Original-Lebenslauf ist optional und benötigt Zustimmung. Vorhandene `workspace.yaml`-Dateien können Pfade zuordnen. Reale Kandidatendaten gehören nie in dieses öffentliche Repository.

Für private GitHub-/GitLab-Arbeitsbereiche braucht der Agent einen autorisierten Connector oder eine separat authentifizierte Git-CLI. Schreibvorgänge müssen ausdrücklich ausgeführt und verifiziert werden; der Python-Helfer bietet keine entfernte Git-Speicherung.

In ChatGPT können Dateien als Anhänge oder Projektdateien bereitgestellt werden. Fehlt eine dauerhaft beschreibbare Schnittstelle, muss der Agent vollständige aktualisierte Dateien zum manuellen Speichern liefern. Ein Anhang ist kein automatisch beschreibbarer Speicher.

## Einrichtung und Konfiguration

Für lokale Speicherung brauchst du Python 3.10+ und ein beschreibbares lokales Verzeichnis; Git ist nicht erforderlich. Ersetze `<installed-skill-directory>` durch das tatsächliche Skill-Verzeichnis:

```bash
python3 <installed-skill-directory>/scripts/interview_workspace.py init --path ~/interview-workspace
python3 <installed-skill-directory>/scripts/interview_workspace.py status
python3 <installed-skill-directory>/scripts/interview_workspace.py validate
```

Der Zeiger liegt in `~/.config/zyris/zyris-interview-coach/config.json` oder unter `$XDG_CONFIG_HOME/zyris/zyris-interview-coach/config.json`. Er wird nicht zu ChatGPT synchronisiert. `init` erhält vorhandene Dateien; `init --path NEW_PATH --force` wechselt nur den Zeiger. Die globale Option `--config PATH` steht vor dem Unterbefehl, und ihre Datei muss außerhalb des Arbeitsbereichs liegen.

Nach Bestätigung speichert `set-language --interface de --interview en` die Bedien- und Interviewsprache; andere Einstellungsschlüssel bleiben erhalten.

## Speichern und fortsetzen

Lies vor dem Vorbereiten eines neuen Lernstands `status` und bewahre dessen `state_sha256` zusammen mit dem gelesenen Zustand auf. Erstelle einen vollständigen Markdown-Bericht und aktualisierten Zustand. Die folgenden Platzhalter musst du durch tatsächliche Werte ersetzen:

```bash
python3 <installed-skill-directory>/scripts/interview_workspace.py finish \
  --run-id 2026-11-17-example \
  --expected-state-sha256 <hash-from-status-before-editing> \
  --status stopped_early --answered-count 2 --planned-count 3 \
  --run-file /path/to/new-run.md \
  --state-file /path/to/new-state.md
```

Hash und Lebenszyklusargumente sind verpflichtend; ältere `finish`-Aufrufe müssen angepasst werden. Ein Checkpoint verwendet `--status paused`:

```bash
python3 <installed-skill-directory>/scripts/interview_workspace.py resume --run-id <checkpoint-id>
```

`resume` liest Bericht, Metadaten und aktuellen Zustand samt Hash, ohne den Checkpoint zu verändern. Speichere die Fortsetzung unter einer neuen ID mit `--resume-from <checkpoint-id>`. Antwortzahlen sind kumulativ; eine geplante Anzahl bleibt erhalten. `completed` setzt bei bekanntem Plan alle Antworten voraus. Bereits fortgesetzte, gestoppte oder abgeschlossene Checkpoints sind nicht fortsetzbar. Alte Markdown-Berichte bleiben manuell lesbar, bekommen aber keine erfundenen Lebenszyklusdaten. Neue Berichte erhalten einen maschinenlesbaren HTML-Kommentar vor dem unveränderten Berichtstext.

## Fehler und Wiederherstellung

Die CLI sperrt kooperierende Schreibprozesse mit einer Betriebssystem-Dateisperre und lehnt veraltete Zustände ab. Berichte überschreiben keine vorhandenen Läufe. Temporäre Dateien werden vor Veröffentlichung geschrieben und synchronisiert; vorhandene Dateirechte bleiben erhalten. Verwaltete Symlinks und ungültige Pfadtypen werden abgelehnt.

Bericht und Lernstand sind **keine gemeinsam atomare Mehrdatei-Transaktion**. `.zyris/pending.json` hält die Wiederherstellungsabsicht fest. Bei einem unvollständigen Vorgang darf kein Erfolg gemeldet werden:

```bash
python3 <installed-skill-directory>/scripts/interview_workspace.py recover
```

Wiederherstellung prüft vorhandene Inhalte und vollendet denselben Vorgang. Externe Konflikte müssen manuell abgeglichen werden. Journal bis zum Erfolg erhalten; keinen zweiten Lauf als Umgehung anlegen. Bis zur Wiederherstellung schlagen weitere Schreibvorgänge sowie `status` und `resume` ausdrücklich fehl.

Bei „busy“ auf das Ende des anderen Prozesses warten; `.zyris/lock` nicht löschen. Das Betriebssystem gibt die Sperre bei Prozessende frei. Bei „stale state“ Zustand neu lesen und Änderungen inhaltlich abgleichen; nicht bloß den Hash austauschen.

## Einschränkungen

Diese Garantien gelten für kooperierende CLI-Prozesse auf lokalen Dateisystemen. Direkte externe Änderungen nehmen nicht an der Sperre teil. Netzwerk- und Cloud-Sync-Dateisysteme sind kein unterstütztes Transaktionsbackend. Tests mit fiktiven Daten prüfen Prozesse, unterbrochene Schreibvorgänge, Wiederherstellung und den paketierten Helfer, aber keine dauerhafte Speicherung in gehosteten Plattformen.

Bei **Nicht speichern** wird kein Workspace-Befehl aufgerufen: keine Initialisierung, Sperre, Checkpoint, Präferenz, Journal oder Exportdatei. Anpassung und Feedback bleiben im aktiven Gespräch; Host-Chat-Aufbewahrung ist separat.

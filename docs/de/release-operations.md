# Veröffentlichung

1. Im Coach-Repository `make test check-plugin` ausführen und den Diff prüfen.
2. Mit `publish` (Plugin Manager) einen konkreten Plan für dieses Repository vorbereiten: Dateien, Prüfungen, Commit-/PR-Text, GitHub-Ziel und aussagekräftiger Feature-Branch ohne `claude/` oder `codex/`.
3. Nach ausdrücklicher Freigabe: genehmigten Branch anlegen → Commit → Push → PR → Checks → kontrollierter Merge. Nie regulär direkt auf dem Default-Branch veröffentlichen. Bei Wiederaufnahme denselben überprüften Branch des Journals verwenden.
4. Für neue Katalogeinträge zuerst die Plugin-Quelle veröffentlichen und prüfen, danach einen separaten Plan für `ai.plugins` freigeben. Eine reine Plugin-Änderung benötigt keinen künstlichen Katalog-Commit.
5. **Draftmode AI Plugins** synchronisieren und Installation, Verhalten und Aktualisierung im Host separat prüfen.

Publish unterstützt GitHub: ausreichend leistungsfähiger GitHub-Connector oder alternativ authentifiziertes `gh`. Vor Freigabe Remote-/Default-Branch-Lesen, Push, PR-Erstellung/-Lesen, Checks, Regeln und kontrolliertes Mergen samt Rechten prüfen. Fehlende Fähigkeiten konkret melden; keine Werkzeuge automatisch installieren und keine Regeln umgehen. GitLab-MRs werden nicht unterstützt.

Ein PR benötigt einen vorhandenen Basisbranch. Nur vollständig leere lokale und entfernte Repositories dürfen den separaten Bootstrap verwenden: konkreter Plan und ausdrückliche Freigabe für ersten Commit und direkten Push, einschließlich `--confirm-initial-publication`. Kein automatischer Initial-Commit. Dieses bestehende Repository benötigt keinen Bootstrap.

Keine Plugin-ZIPs, Manifest-Versionen, Tags, Release-Actions oder GitHub Releases erforderlich. Dokumentationsupdate und lokale Tests erteilen keine Veröffentlichungsfreigabe. [Installation](installation.md) · [Prüfstand](release-evidence.md).

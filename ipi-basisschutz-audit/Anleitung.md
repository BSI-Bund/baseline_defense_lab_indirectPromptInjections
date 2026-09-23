# Anleitung: IPI-Basisschutz-Audit benutzen

Diese Anleitung zeigt, wie du ein **lokal vorliegendes Projekt** auditierst  mit Claude, mit GPT oder mit einem lokalen Modell.

## Das Wichtigste zuerst: das Modell **ist** der Auditor

Dieses Audit ist kein Muster-Scanner. Es gibt **keinen modelllosen Weg** und keine deterministisch reproduzierbare Zahl. Das Modell liest den Code, kartiert den Datenfluss bis zum LLM-Aufruf und **fällt das Urteil** über die fünf Maßnahmen.

Daraus folgt ehrlich:

* **Die Qualität des Audits ist die Qualität des Modells.** Ein starkes Modell zieht die Belegkette von der Quelle bis zum LLM-Aufruf sauber durch; ein schwaches Modell verliert den Faden, verwechselt Nähe mit Verdrahtung und vergibt Status auf Verdacht.
* **Der Report ist nicht deterministisch reproduzierbar.** Zwei Läufe können im Wortlaut abweichen. Dafür trägt **jede** Aussage eine Belegkette (`Datei:Zeile → Datei:Zeile`), die du von Hand nachprüfen und widerlegen kannst. Der Report tauscht Reproduzierbarkeit gegen **Falsifizierbarkeit**  für ein sicherheitskritisches Publikum das stärkere Angebot als eine Zahl, die zuverlässig immer dasselbe Falsche sagt.

Wenn du eine bit-stabile Zahl brauchst, ist dieses Werkzeug das falsche. Wenn du eine **nachprüfbare Begründung** brauchst, ist es das richtige.

---

## 1 · Mit Claude (Claude Code / Cowork)

Claude lädt `SKILL.md` **nativ als Skill**  du musst nichts konfigurieren, nur den Ordner an die richtige Stelle legen.

| Zweck | Ort |
|-------|-----|
| Nur in diesem Projekt | `.claude/skills/ipi-basisschutz-audit/` |
| In allen deinen Projekten | `~/.claude/skills/ipi-basisschutz-audit/` (Windows: `%USERPROFILE%\.claude\skills\…`) |

In den Ordner gehört der **komplette Skill** (`SKILL.md`, `references/`); `SKILL.md` muss direkt darin liegen. Claude erkennt am `description`-Feld selbst, wann der Skill passt  es reicht, in normaler Sprache nach einer IPI-Prüfung zu fragen.

**Beispiel-Prompt:**

```
Auditiere mein Projekt unter <Pfad zum Projekt> auf die fünf BSI-Basisschutzmaßnahmen
gegen Indirect Prompt Injection. Kartiere zuerst die Übergabestelle, bewerte dann jede Maßnahme
mit Status, Konfidenz und Belegkette (Datei:Zeile), und schreibe den Report nach
reports/. Fasse ihn danach auf Deutsch zusammen: Disclaimer, Gesamtscore (❓ getrennt
von ❌), je Maßnahme die fehlende/unvollständige Verdrahtung priorisiert.
```

---

## 2 · Mit GPT (Codex / ChatGPT / API)

### 2.1 Codex (CLI / IDE-Erweiterung)  der empfohlene Weg

Codex durchsucht `.agents/skills` vom Arbeitsverzeichnis bis zur Repo-Wurzel sowie den Benutzer-Ordner:

| Zweck | Ort |
|-------|-----|
| Nur in diesem Projekt | `<repo>/.agents/skills/ipi-basisschutz-audit/` |
| In allen deinen Projekten | `~/.agents/skills/ipi-basisschutz-audit/` (Windows: `%USERPROFILE%\.agents\skills\…`) |

Der ältere Pfad `~/.codex/skills/` wird weiterhin unterstützt. Wie bei Claude reicht eine Frage in normaler Sprache; explizit aufrufen kannst du den Skill mit `$` oder über `/skills`. Codex hat Lesezugriff auf das Repo  genau das, was dieses Audit braucht.

### 2.2 ChatGPT

Eigenständige Skills stehen in der **ChatGPT-Desktop-App** und der IDE-Erweiterung zur Verfügung; im Chat rufst du sie mit `@` auf (in Chat/Work im Web kommen Skills über Plugins herein). Der begrenzende Faktor ist hier nicht das Format, sondern der **Projektzugriff**: Ohne Lesezugriff auf das Verzeichnis kann das Modell die Übergabestelle nicht kartieren  dann ist es kein Audit. Für ein reines Web-ChatGPT heißt das: Projekt in den Kontext hochladen (Code Interpreter) oder auf Codex wechseln.

### 2.3 API / eigene Integration

Über die API gibt es keinen Skill-Mechanismus dort nimmst du den Skill-Text direkt:

1. `SKILL.md` öffnen, den YAML-Kopf (`---` … `---`) weglassen, den Rest als System-Prompt einsetzen. Die `references/`-Dateien bei Bedarf mitgeben (in den Kontext legen oder als Dateien bereitstellen).
2. Read-only-Werkzeuge (`list_files`, `read_file`, `grep`) per Function Calling registrieren, mit denen das Modell den Code exploriert. **Keine** Schreib-/ Ausführungs-Werkzeuge auf Projektinhalten.

**Ehrlicher Hinweis:** Das Urteil ist nur so gut wie das Modell  daran ändert die native Skill-Unterstützung nichts. Ein kleineres GPT-Modell zieht die Belegketten schwächer durch; prüfe die im Report genannten `Datei:Zeile`-Belege stichprobenartig selbst nach.

---

## 3 · Mit lokalen Modellen (Ollama, LM Studio, llama.cpp, Continue, Open WebUI)

**Zuerst prüfen, ob deine Umgebung Skills nativ lädt:** Der Agent-Skills-Standard wird inzwischen von etlichen Agenten-Umgebungen gelesen. Wenn deine `SKILL.md` nativ unterstützt, gilt Abschnitt 1/2 sinngemäß  Ordner an die dokumentierte Stelle legen, fertig.

Nur wenn es **keine** Skill-Unterstützung gibt, greift der Handbetrieb: `SKILL.md` (ohne YAML-Kopf) als **System-Prompt**, Projekt-Lesezugriff über ein Tool-/Datei-Plugin der jeweiligen Umgebung.

**Ungeschönter Hinweis  das ist der große Unterschied zu früher:** Ein kleines lokales Modell konnte einen fertigen Report früher bestenfalls **schlecht vorlesen**. Jetzt **fällt es selbst das Urteil**  und ein schlechtes Urteil ist qualitativ etwas anderes als eine schlechte Zusammenfassung. Kleine Modelle:

* verwechseln **Nähe mit Verdrahtung** (sehen eine Bereinigungsfunktion und vergeben ✅, ohne die Aufrufkette bis zum LLM zu lesen  genau der Fehler, den das Audit vermeiden soll),
* finden die Übergabestelle in verschachteltem/Framework-Code oft gar nicht,
* halluzinieren Belegketten, die im Code nicht stehen.

Nimm für ein belastbares Audit ein **starkes, reasoning-fähiges Modell**. Mit einem kleinen lokalen Modell ist das Ergebnis eine grobe Orientierung, kein Audit  und die `Datei:Zeile`-Belege sind dann Pflichtprüfung, nicht Kür.

| Umgebung | Weg zum Projektzugriff |
|----------|------------------------|
| Continue (VS Code/JetBrains) | System-Prompt in `config.json`, Datei-/Terminal-Lesezugriff |
| Open WebUI | System-Prompt im Modell-Preset, Tools-/Code-Plugin (nur lesend) |
| LM Studio | System-Prompt im Chat-Preset; Tool-Calling nur mit passendem Modell |
| Ollama / llama.cpp (nackt) | kein Tool-Zugriff  Dateien manuell in den Kontext geben |

---

## 4 · Report lesen

Der Report (`reports/<projekt>.md`) folgt [`references/report-vorlage.md`](references/report-vorlage.md):

* **Disclaimer (oben):** heuristische Einschätzung, **kein Sicherheitsnachweis**.
* **Die Übergabestelle** als Belegkette  die Grundlage aller fünf Bewertungen.
* **Gesamtscore** `X/5` gewichtet, mit **❓ sichtbar getrennt von ❌**. Ein hoher Score heißt nicht „sicher"  die fünf Maßnahmen wirken nur im Zusammenspiel.
* **Status je Maßnahme:** ✅ umgesetzt · ⚠️ unvollständig · ❌ nicht gefunden · ❓ nicht bewertbar. Dazu Konfidenz und die konkrete Belegkette.
* **Auffälligkeiten:** im Projekt gefundene Injektionsversuche gegen den Auditor.
* **Empfehlungen:** die priorisiert fehlende/unvollständige Verdrahtung.

Der nützlichste Teil ist meist die je Maßnahme **fehlende Verdrahtung** plus die **Belegketten**  dort schaust du nach, wenn du eine Aussage widerlegen willst. Der geschriebene Report ist die Quelle der Wahrheit; erfinde beim Zusammenfassen keine Fundstellen dazu.

---

## Weiterführend

* [`README.md`](README.md)  Methodik, Bewertungsregeln, Sicherheitseigenschaften.
* [`SKILL.md`](SKILL.md)  die Skill-Definition selbst: nativ ladbar in Claude, Codex und ChatGPT; ohne YAML-Kopf zugleich der System-Prompt-Text für API-Integrationen und Umgebungen ohne Skill-Unterstützung.
* [`references/`](references/)  Vertrauensgrenze-Kartierung, Bewertungsrubrik, die fünf Maßnahmen-Referenzen, Report-Vorlage.

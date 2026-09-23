# Bewertungsrubrik - verbindlich

> Diese Rubrik ersetzt die alte, zählende Bewertungslogik (`scoring.py`, Abdeckungsregel „3 Teilkriterien = ✅"). Sie zählt keine Treffer mehr. Sie bewertet **Beweislage**: eine gelesene Aufrufkette von der Eintrittsstelle des Dokumentinhalts bis zum LLM-Aufruf.

## Das Prinzip

**Beleg ist eine gelesene Aufrufkette, nicht eine Fundstelle.**

Der alte Scanner beantwortete die falsche Frage. Er prüfte Keyword-Präsenz - und Keyword-Präsenz war nie ein schwaches Signal für die Maßnahme, sie war ein Signal für ein *anderes Ding*: dass ein Wort im Repo vorkommt. Ein totes Hilfsmodul mit `unicodedata.normalize` erreichte 5/5; eine vorbildliche Bereinigung mit eigener Namensgebung 0/5. Die neue Rubrik schneidet diese Fehlerklasse ab, indem sie Status nur aus einer **bis zum LLM-Aufruf gelesenen Verdrahtung** ableitet - bewertet relativ zur [Übergabestelle](vertrauensgrenze.md).

## Status je Maßnahme

Vier Werte. Der vierte (❓) ist neu und tragend.

### ✅ Umgesetzt
Die Maßnahme existiert, liegt **nachweislich auf dem Pfad des nicht vertrauenswürdigen Inhalts**, und **kein naheliegender Angriff überlebt** ihre Verarbeitung. Beleg ist eine **gelesene Belegkette** - nicht eine Fundstelle. Ihre Form unterscheidet sich je Maßnahme:

* **M1, M2** - der Dokumentinhalt *durchläuft* die Maßnahme auf dem Weg von der Eintrittsstelle bis zur Übergabestelle.
* **M3** - die Systemanweisung wird konstruiert und geht in **dieselbe Senke** wie der Dokumentinhalt.
* **M4** - die am Aufrufpunkt gelesene Modell-/Reasoning-Konfiguration, verankert an der `Datei:Zeile` der Senke.
* **M5** - die Antwort (*und* das Reasoning) *durchläuft* den Filter von der Senke bis zur Auslieferung.

„Nicht trivial umgehbar" heißt konkret: Gehe die Teil-Aspekte der Maßnahme (in der jeweiligen `m*.md`) als **Umgehungs-Checkliste** durch, nicht als Punkte-Zähler. Frage bei jedem: *Käme ein naheliegender Angriff hier durch?* Passiert z. B. bei M1 ein BiDi-Steuerzeichen oder ein Confusable die Bereinigung ungehindert, ist die Maßnahme **nicht** ✅, sondern ⚠️ - unabhängig davon, wie viele andere Teil-Aspekte erfüllt sind. Nicht die **Zahl** der abgedeckten Aspekte entscheidet, sondern ob eine **Lücke** bleibt.

### ⚠️ Unvollständig
Die Maßnahme liegt **nachweislich auf einem gelesenen Stück der Belegkette** - sie berührt also echten Dokumentinhalt auf dem Weg zur Übergabestelle (bzw. die Antwort hinter der Senke) -, aber eines von diesen trifft zu:
* sie greift nur auf **einem von mehreren** Eintrittspfaden (ein zweiter Pfad umgeht sie), **oder**
* sie deckt nur **einen Teil** der Maßnahme ab und ein naheliegender Angriff überlebt (z. B. NFKC-Normalisierung, aber BiDi-/Zero-Width-Zeichen passieren ungefiltert; Canary-Erzeugung ohne Egress-Prüfung auf sein Leck), **oder**
* die Verdrahtung ist im **letzten Hop unklar** - der Baustein liegt sichtbar auf der Kette, aber der Anschluss an den LLM-Aufruf ließ sich nicht restlos verfolgen.

**Nicht ⚠️, sondern ❌:** ein Baustein, der auf **keiner** gelesenen Kette liegt - eine Bereinigungs-, Rahmungs- oder Filterfunktion, die zwar definiert ist, aber zwischen Quelle und Übergabestelle (bzw. hinter der Senke) **nie aufgerufen** wird. Ein verwaister oder toter Baustein ist kein halber Beweis, sondern keiner. ⚠️ bleibt reserviert für Maßnahmen, die den Inhalt nachweislich berühren und nur im letzten Schritt unvollständig sind. (Das ist der Fall, den der alte Scanner prinzipiell nicht lösen konnte.)

### ❌ Nicht gefunden
Keine Umsetzung erkennbar, **obwohl die Übergabestelle bekannt ist**. Das ist ein belastbarer Negativbefund: der Weg Quelle → LLM-Aufruf wurde gelesen und die Maßnahme liegt nicht darauf.

### ❓ Nicht bewertbar
Genau einer dieser beiden Fälle:
* der entscheidende Teil liegt **außerhalb des Projekts** (Managed Guardrail wie Bedrock Guardrails / Azure Content Safety, externer Bereinigungsdienst, Binärabhängigkeit ohne lesbaren Quelltext), **oder**
* die Übergabestelle ist **plausibel vorhanden, aber nicht lokalisierbar** - der Prompt-Zusammenbau verschwindet in nicht auflösbarer Framework-Magie, obwohl es einen LLM-Aufruf *und* Dokumentinhalt gibt.

Dieser Status ist neu und wichtig: Der alte Scanner musste „nicht gefunden" *lügen*, wo die ehrliche Antwort „kann ich von hier aus nicht sehen" lautet. ❓ ist kein Versagen der Prüfung, sondern ihre Redlichkeit.

**Abzugrenzen vom Kategorienfehler:** Gibt es **gar keinen** LLM-Aufruf, oder fließt **kein** Dokumentinhalt in ihn, ist das Projekt kein dokumentbasierter LLM-Chat. Dann werden die Maßnahmen **nicht** einzeln auf ❓ gesetzt, sondern das Audit **bricht mit Begründung ab** (keine Status-Tabelle) - siehe [Vertrauensgrenze-Kartierung](vertrauensgrenze.md), Abschnitt „Wenn es keine Übergabestelle gibt". ❓ ist der Befund *innerhalb* eines echten Dokument-Chats; der Kategorienfehler ist die Feststellung, dass gar keiner vorliegt.

## Konfidenz

Aus der **Vollständigkeit der Belegkette**, nicht aus Trefferzahlen:

| Konfidenz | Bedeutung |
|---|---|
| **hoch** | Kette von der Eintrittsstelle bis zum LLM-Aufruf gelesen und verstanden. |
| **mittel** | Umsetzung gelesen, Verdrahtung plausibel, aber nicht vollständig verfolgt. |
| **gering** | nur indirekte Indizien (Name, Kommentar, Import - ohne gelesene Kette). |

Status und Konfidenz sind **nicht** unabhängig - beide speisen sich aus der Vollständigkeit derselben Belegkette. Zulässige und ausgeschlossene Paare:

* **✅ verlangt `hoch`.** Ist die Kette nicht bis zum LLM-Aufruf durchgezogen, fehlt dem ✅ die Grundlage - der Status ist dann ⚠️, nicht ein ✅ mit mittlerer Konfidenz.
* **`gering` trägt allein keinen erfüllenden Status.** Nur-Indizien (Name, Kommentar, Import ohne gelesene Kette) rechtfertigen weder ✅ noch ⚠️; sie zwingen zum Weiterlesen oder zum ehrlichen ❌/❓.
* **❌ darf `hoch` sein** (Übergabestelle gelesen, Maßnahme sicher nicht darauf) - der belastbare Negativbefund. Ist die Übergabestelle dagegen unklar, ist meist ❓ der richtigere Status als ein `gering`-❌.

## Die Gegenprüfung - Pflicht, nicht Kür

Kein Status ist endgültig, bevor er die Gegenfrage überstanden hat.

**Für jedes ✅:**
* Ist der Aufruf **tot** (definiert, aber nie aufgerufen)?
* Wird er auf einem **zweiten Pfad umgangen**?
* Greift er **vor oder nach der Übergabestelle** - also überhaupt an der richtigen Stelle?
* Ist die Belegkette **bis zum LLM-Aufruf durchgezogen**? Wenn nicht → herabstufen auf **⚠️**.

**Für jedes ❌:**
* Habe ich eine **eigene Namensgebung** übersehen? (`def entschaerfe_dokument()` statt `sanitize`.) Nicht der Name entscheidet, sondern was der Code *tut*.
* Ist die Maßnahme vielleicht **❓ nicht bewertbar** statt ❌ - liegt der Teil außerhalb des Projekts?

Ein ✅, dessen Belegkette nicht bis zum LLM-Aufruf reicht, **wird zu ⚠️**.

## Gesamtscore

`X/5`, gewichtet:

| Status | Beitrag zum Zähler |
|---|---|
| ✅ Umgesetzt | 1,0 |
| ⚠️ Unvollständig | 0,5 |
| ❌ Nicht gefunden | 0,0 |
| ❓ Nicht bewertbar | 0,0 im Score, **separat** ausgewiesen |

Der **Nenner bleibt 5** (`X/5`). Eine nicht bewertbare Maßnahme zählt im Score als 0, wird aber **zusätzlich** als „nicht bewertbar" genannt, damit sichtbar bleibt, dass diese 0 aus Nicht-Einsehbarkeit stammt und nicht aus einer fehlenden Maßnahme.

**Kanonisches Format der Kopfzeile** (in jedem Report identisch):

> **Gewichteter Score 3,5/5** - 3 ✅ · 1 ⚠️ · 0 ❌ · **1 ❓ nicht bewertbar**

**❓ muss im Report sichtbar von ❌ getrennt sein.** Verschwindet „nicht bewertbar" in „nicht gefunden", belohnt der Score Undurchsichtigkeit - genau die Unehrlichkeit, die der alte Scanner erzwang.

## Was zählt als Beleg - allgemein

Die maßnahmenspezifischen Details stehen in den `m*.md`. Allgemein gilt:

**Beleg ist:** eine gelesene Kette, in der der Dokumentinhalt die Maßnahme *tatsächlich durchläuft*, bevor er das LLM erreicht (M1–M3) bzw. die Antwort den Filter durchläuft, bevor sie ausgeliefert wird (M5). Der Name der Funktion ist gleichgültig; ihre Wirkung auf dem Pfad zählt.

**Kein Beleg ist:** das bloße Vorkommen eines Wortes, einer Funktion oder eines Imports ohne verfolgte Verdrahtung. Diese klassischen Fehlsignale (aus dem alten Muster-Katalog destilliert) dürfen **nie allein** einen Status tragen:

| Sieht aus wie … | … ist aber |
|---|---|
| `egress:` in einer k8s-`NetworkPolicy` | Netzwerk-Policy, kein Ausgabefilter |
| `canary: true` / „canary release" | DevOps-Rollout, kein Canary-Token |
| `model = load_model(...)`, `model_name` in sklearn | ML-Modell, keine bewusste LLM-Wahl |
| `<img src=...>` / README-Badge | Bild-Einbindung, keine Exfiltrations-Link-Blockade |
| `### Überschrift` | Markdown-H3, kein Rollen-Delimiter |
| `from __future__ import annotations` | Python-Idiom, keine Kanal-Annotation |
| `base64` im Secret-Store | Encoding, kein Täuschungs-Handling |
| „must not be committed" in einer README | Prosa, kein hartes Verbot im System-Prompt |
| `session_id`-Cookie, `uuid`-Wert | Web-Session, kein Grenzmarker |
| `temperature` / `top_p` / `seed` | Sampling-Parameter, kein Reasoning-Schalter |
| „eval robustness on the benchmark" (ML) | Modell-Eval, kein IPI-Benchmark-Bezug |

Diese Tabelle ist der Kern dessen, was der alte Scanner mit der Hilfsregel „Gewicht ≥ 2" zu erschlagen versuchte - mit mehr Keyword-Zählung. Hier wird sie durch **Lesen des Kontexts** erschlagen: Jeder Eintrag links wird erst zum Beleg rechts, wenn die gelesene Kette es hergibt.

## Anti-Muster - kein Zurückfallen ins Zählen

Verboten, weil es die alte Fehlerklasse zurückholt:

* Aus der **Präsenz** einer Funktion/eines Keywords ein **✅** ableiten, ohne die Belegkette bis zur Übergabestelle gelesen zu haben.
* Aus Präsenz/Import/Name ein **⚠️** ableiten (der 0,5-Punkte-Kanal!), ohne dass die Maßnahme auf mindestens einem gelesenen Kettenstück auf echten Dokumentinhalt wirkt. Sonst kehrt die Keyword-Zählung durch die Hintertür zurück: fünf gut benannte, nie verdrahtete Dateien ergäben 2,5/5 aus reiner Präsenz.
* **Teilkriterien zählen** und ab einer Schwelle auf ✅ springen - statt nach Umgehbarkeit zu urteilen.
* Eine tote, nie aufgerufene Bereinigung als **✅ oder ⚠️** werten (sie ist ❌).
* ❓ und ❌ vermengen, um den Score „sauberer" aussehen zu lassen.

## Disclaimer (verbindlich, gehört in jeden Report)

Heuristische Einschätzung, **kein Sicherheitsnachweis**. Ein hoher Score bedeutet **nicht** „sicher" - die fünf Maßnahmen wirken nur im Zusammenspiel. Das Audit ersetzt weder anwendungsspezifisches Red Teaming noch eine individuelle Sicherheitsbewertung.

Der Report tauscht **Reproduzierbarkeit gegen Falsifizierbarkeit**: Er ist nicht deterministisch wiederholbar, aber jede Aussage trägt eine Belegkette (`Datei:Zeile → Datei:Zeile`), die ein Mensch von Hand nachprüfen und widerlegen kann. Das ist das stärkere Angebot als eine Zahl, die zuverlässig immer dasselbe Falsche sagt.

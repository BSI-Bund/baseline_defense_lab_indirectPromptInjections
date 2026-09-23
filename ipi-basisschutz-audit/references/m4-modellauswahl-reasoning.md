# M4 - Modellauswahl & Reasoning-Schalter (im Modell, das die Übergabestelle verarbeitet)

> M4 ist die einzige Maßnahme, die nicht *neben* der [Übergabestelle](vertrauensgrenze.md) wirkt, sondern *in ihr*: an der Senke selbst - dem LLM-Aufruf, der den dokumenttragenden Prompt verarbeitet. Beleg ist die am Aufrufpunkt gelesene Modell- und Reasoning-Konfiguration, verankert an der `Datei:Zeile` der Senke, bewertet nach der [Bewertungsrubrik](bewertungsrubrik.md).

## Was die Maßnahme verlangt (BSI)

Alle anderen Maßnahmen umranden die Übergabestelle: sie bereinigen davor (M1), rahmen an ihr (M2), härten oberhalb (M3), filtern dahinter (M5). M4 greift an der einzigen Stelle, die keine dieser Maßnahmen berührt - am verarbeitenden Modell selbst. Die Maßnahme verlangt, dass die Senke nicht beliebig, sondern **bewusst robust** gewählt und betrieben wird: ein Modell, dessen Widerstand gegen Instruktionsübernahme aus dem Dokument belegt ist, ein vorgeschalteter Denkschritt, der die injizierte Anweisung als solche erkennen kann, bevor er handelt - und ein Ausgabeformat, das diesen Denkschritt für den Egress-Filter (M5) genauso prüfbar macht wie die eigentliche Antwort. Der Denkkanal ist kein sicherer Nebenraum: Was das Modell „denkt", kann selbst exfiltrieren und selbst der Anweisung des Dokuments folgen.

## Wo an der Übergabestelle sie wirkt

M4 sitzt **in der Senke** - am Punkt, an dem der fertig gebaute Prompt (Dokumentinhalt + System-Prompt) an das Modell übergeben wird. Anders als bei M1/M2/M5 „durchläuft" der Inhalt hier nichts; belegt wird nicht ein Durchlauf, sondern eine **Konfiguration am Aufrufpunkt**. Auf der Belegkette muss an der `Datei:Zeile` der Senke lesbar sein: welches Modell aufgerufen wird (`model=`), mit welchen Reasoning-Parametern, und in welches Ausgabeformat Denk- und Antwortkanal geschrieben werden. Liegt die Reasoning-/Format-Konfiguration nicht am selben Aufruf, der den Dokumentinhalt verarbeitet, sondern an einem anderen, harmlosen LLM-Call (Zusammenfassung, Titelgenerierung), liegt sie **nicht auf der Kette** und trägt keinen Status.

## Teil-Aspekte (Umgehungs-Checkliste)

Diese Punkte sind eine **Checkliste gegen Umgehung**, kein Punktezähler. Nicht ihre Anzahl entscheidet ✅ vs. ⚠️, sondern ob ein naheliegender Angriff eine **Lücke** findet.

- **Bewusste Modellauswahl nach Robustheits-Benchmarks.** Leistet: die Senke ist ein gegen IPI nachweislich widerstandsfähiges Modell, dokumentiert/begründet über einschlägige Benchmarks (BIPIA, InjecAgent). Fehlt sie: ein schwaches Modell befolgt die im Dokument versteckte Anweisung direkt - jede Umrandung (M1–M3, M5) muss dann eine Lücke der Senke kompensieren. *Das bloße Nennen eines Modellnamens ist noch keine robustheitsgetriebene Wahl.*
- **Reasoning/Denkschritt aktiviert.** Leistet: ein vorgeschalteter Denkschritt gibt dem Modell die Chance, die injizierte Instruktion als Dokument-Inhalt statt als Auftrag einzuordnen. Idiome: `reasoning=True`, `extended_thinking`, `reasoning_effort=…`, `thinking={…}`, `<think>`-Tags, Chain-of-Thought-Vorspann, eine `-thinking`-Modellfamilie. Fehlt er: das Modell reagiert reflexartig auf die stärkste Anweisung im Kontext - oft die des Angreifers am Dokumentende.
- **Einheitliches Ausgabeformat mit festen Trennmarkern.** Leistet: Reasoning und Antwort landen in *einem* Format mit festen Markern (`THINK_OPEN`/`THINK_CLOSE`, `ANSWER_MARKER`), damit M5 **beide Kanäle gleich** prüfen kann. Fehlt es: der Denkkanal wird ungeprüft an M5 vorbei ausgeliefert - Exfiltration und Canary-Leck über das Reasoning bleiben unsichtbar (siehe Häufige Lücken).
- **Kommunikation, falls kein Reasoning genutzt wird** *(Nachvollziehbarkeits-Hinweis, kein Umgehungspunkt).* Leistet: ein expliziter Fallback-Hinweis macht die bewusste Entscheidung gegen Reasoning nachvollziehbar (Latenz, Kosten). Sein Fehlen senkt **nicht** die Robustheit und ist keine Sicherheitslücke - es macht nur die Bewertung des Reasoning-Aspekts zur Vermutung (bewusst weggelassen oder schlicht vergessen?).

## Was zählt als Beleg

Die am Aufrufpunkt gelesene Konfiguration, verankert an der `Datei:Zeile` der Senke
- **nicht** ein „Durchlaufen". Beleg ist: das `model=`/`model_id`-Argument des LLM-Aufrufs, der den dokumenttragenden Prompt verarbeitet; die daneben stehenden Reasoning-Parameter; das Format-Template, in das Denk- und Antwortkanal geschrieben werden. **Wirkung auf dem Pfad zählt, nicht der Name.** Eine selbst benannte Konstante `DENK_MODUS = True`, die am Aufruf ausgewertet wird, ist Beleg genauso wie `reasoning_effort`; ein eigenes `<gedanke>…</gedanke>`-Markerpaar zählt wie `THINK_OPEN`. Für die Modellwahl-Rationale gilt: Beleg ist eine gelesene Begründung (Kommentar, Config-Doc, ADR) mit Bezug auf BIPIA/InjecAgent oder gleichwertige IPI-Robustheitsdaten - nicht der Modellname allein.

## Was sieht so aus, ist es aber nicht

Nicht abschließend - False-Positive-Fallen genau dieser Maßnahme:

| Täuschendes Idiom | Was es wirklich ist |
|---|---|
| `model = load_model(...)`, `model_name=` in sklearn/keras, `torch.load` | ML-Modell-Laden, keine bewusste LLM-Senkenwahl |
| `temperature=…`, `top_p=…`, `seed=…` | Sampling-Parameter, kein Reasoning-Schalter |
| „eval robustness on the benchmark" in einem ML-Trainingsskript | Modell-Eval auf ML-Metrik, kein IPI-Benchmark-Bezug (BIPIA/InjecAgent) |
| `reasoning`/`thinking` als Variablenname in fremder Domäne (z. B. UI-Text, Logging) | gleiches Wort, kein aktivierter Denkschritt am Aufruf |
| `<think>`-Tag nur im System-Prompt-Text erwähnt, aber vom Aufruf nicht erzeugt/geparst | Prosa über Reasoning, kein wirksames Ausgabeformat |
| Modellname als String irgendwo im Repo (README, Beispiel, Default-Konstante) | Nennung, keine robustheitsgetriebene Wahl an der Senke |

## Häufige Lücken → ⚠️ / ❓

- **Reasoning aktiv, aber Denkkanal ohne feste Trennmarker an M5 übergeben.** Der Denkschritt läuft, doch sein Ausgabeformat kennt keine `THINK_OPEN`/ `THINK_CLOSE`-Marker, sodass der Egress-Filter das Reasoning nicht als eigenen Kanal prüft. Durchkommender Angriff: Exfiltrations-Link oder geleaktes Canary reist im ungeprüften Denkkanal nach außen. → **⚠️**, weil die Senke die Maßnahme nachweislich berührt, aber eine Umgehung offen lässt.
- **Modellname genannt, aber ohne Robustheits-Begründung.** Reasoning und Format sind im Code sichtbar und bewertbar; die *Rationale* der Modellwahl nach BIPIA/InjecAgent steht jedoch typischerweise **nicht im Code** - nur ein Modellname ist lesbar. Dieser Auswahl-Teil ist dann in der Regel **❓ Nicht bewertbar**, nicht pauschal ❌: er liegt außerhalb des einsehbaren Materials, nicht nachweislich neben der Kette.
- **Reasoning-Konfiguration an einem anderen LLM-Call.** Der Denkschritt ist konfiguriert - aber am Aufruf für Zusammenfassung/Titel, nicht an der Senke, die den Dokumentinhalt verarbeitet. Ein toter, nie am dokumenttragenden Aufruf ausgewerteter Reasoning-Schalter ist **❌**, nicht ⚠️.

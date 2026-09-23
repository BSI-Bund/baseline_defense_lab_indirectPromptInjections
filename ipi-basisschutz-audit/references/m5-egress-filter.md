# M5 - Egress-Filter (nach der Antwort)

> M5 wirkt als letzte, modellunabhängige Verteidigung **hinter der Senke**: sie prüft die fertige Antwort - und das Reasoning - bevor beides den Nutzer erreicht. Position und Belegform ergeben sich aus der [Vertrauensgrenze-Kartierung](vertrauensgrenze.md); der Status folgt der [Bewertungsrubrik](bewertungsrubrik.md).

## Was die Maßnahme verlangt (BSI)

M1–M4 setzen alle *vor* oder *im* Modell an und vertrauen darauf, dass das Modell die Rahmung respektiert. M5 gibt diese Annahme auf: Sie behandelt die Modellausgabe selbst als potenziell kompromittiert und filtert sie, nachdem das Modell fertig ist. Damit fängt sie genau die Fälle, in denen eine Injektion alle vorgelagerten Maßnahmen überstanden hat - der Canary ist geleakt, der System-Prompt wird ausgeplaudert, die Antwort trägt einen Compliance-Marker („PWNED") oder einen Exfiltrations-Link. Die Maßnahme leistet zweierlei: sie **erkennt** verräterische Muster in Antwort und Denkkanal und **ersetzt** im Befund die gesamte Ausgabe durch einen neutralen Text, statt kompromittierten Output auszuliefern. Sie ist Nachweis von Datenabfluss, nicht dessen Verhinderung an der Quelle - deshalb „letzte" Verteidigung.

## Wo an der Übergabestelle sie wirkt

M5 liegt **hinter der Senke**, auf dem Rückweg. Auf der Belegkette muss zu lesen sein, dass die vom LLM-Aufruf zurückgegebene Antwort (und, falls das Modell Reasoning/Thinking liefert, auch dieses) durch eine Prüf-/Filterfunktion läuft, **bevor** sie zurückgegeben, gestreamt oder gerendert wird. Die Kette endet also nicht am `messages.create(...)`, sondern erst an der Auslieferung: `return gefiltert`, `yield`, `print`, HTTP-Response. Ein Filter, der zwar definiert ist, aber zwischen Modellantwort und Auslieferung **nie aufgerufen** wird, liegt nicht auf der Kette und ist ❌ - nicht ⚠️ (Rubrik: toter Baustein). Bei Streaming muss der Filter den zusammengesetzten Text sehen; ein Token-für-Token-Passthrough, der die Antwort schon ausgeliefert hat, bevor das Muster vollständig ist, greift zu spät.

## Teil-Aspekte (Umgehungs-Checkliste)

Keine Punkteliste - eine Liste von Umgehungen. Fehlt einer dieser Aspekte und kommt der zugehörige Angriff durch, ist die Maßnahme ⚠️, egal wie viele andere erfüllt sind.

- **Prüft Antwort *und* Reasoning** (`egress_filter(output, reasoning, …)`). Fehlt der Denkkanal, leakt das Modell die Geheimnisse (Canary, System-Prompt) im sichtbaren Thinking-Block, während die „Antwort" sauber bleibt - der Filter sieht am falschen Ort hin.
- **Canary-Leck inkl. Umkodierungen.** Der Canary muss auch nach Dekodierung gesucht werden: Base64 (`base64.b64encode`/`b64decode`), Hex (`binascii.hexlify`), und nach Entfernen eingestreuter Trennzeichen (`re.sub(r"[\s\-]", "", text)` vor dem Vergleich). Ein naiver Substring-Check `if canary in output` ist umgehbar: das Modell gibt den Canary base64-kodiert oder als `C-A-N-A-R-Y` mit Bindestrichen aus und schlüpft durch.
- **System-Prompt-Leak mit Schwellwert.** Charakteristische Formulierungen des System-Prompts (`LEAK_PHRASES`) werden gezählt, ab `LEAK_THRESHOLD` wird geblockt. Ohne Schwellwert entweder False Positives bei Einzeltreffer oder - bei zu naivem Ein-Phrasen-Check - ein umschriebenes Ausplaudern, das keine Phrase wörtlich trifft.
- **Injektions-/Compliance-Marker.** `PWNED`, `I have been PWNED`, `ignore (all) previous instructions`, `jailbreak` - und **`DAN` case-SENSITIV**. Die Case-Sensitivität ist bewusst: `\bDAN\b` case-insensitiv träfe den Namen „Dan" und das indonesische Wort „dan" (= „und") und produzierte Dauer-False-Positives. Fehlt der Marker-Abgleich, wird der klassische Beleg einer gelungenen Injektion ausgeliefert.
- **Exfiltrations-Link-Blockade mit Default-Deny.** Erkannt werden Markdown-Bilder `![…](url)`, HTML `<img src=…>` und URLs außerhalb einer Allowlist. Entscheidend ist Default-Deny: alles nicht ausdrücklich Erlaubte wird geblockt. Eine reine Bad-URL-Blockliste lässt jede neue Exfil-Domain durch. Der Grund für Default-Deny: eine eingebettete Bildreferenz wird beim Rendern der Antwort automatisch abgerufen — der Abruf geht an einen fremden Server, ohne Zutun der Nutzenden.
- **Neutraler Ersatz-Output.** Bei kritischem Befund wird die **gesamte** Antwort durch neutralen Text ersetzt (`NEUTRAL_REPLACEMENT`), nicht nur die Fundstelle geschwärzt. Partielles Redigieren lässt Rest-Kontext stehen, aus dem sich das Geheimnis rekonstruieren lässt, und verrät dem Angreifer, dass und wo gefiltert wurde.

## Was zählt als Beleg

Beleg ist die **gelesene Kette von der Senke bis zur Auslieferung**, in der Antwort und Reasoning den Filter tatsächlich durchlaufen. Der **Name der Funktion ist gleichgültig** - `egress_filter`, `pruefe_ausgabe`, `sanitize_response`, `guard_output` zählen gleich, wenn ihre Wirkung auf dem Pfad liegt. Konkrete Code-Formen, die als Beleg gelten:

- eine Funktion, die `output` (und `reasoning`) entgegennimmt und deren Rückgabe an der Auslieferung steht: `return egress(resp.content, resp.thinking, canary)`.
- Canary-Vergleich, der vor dem Test **umkodiert/normalisiert**: `b64decode(...)`, `re.sub(r"[\s\-]+","",t)`, dann `canary in bereinigt`.
- Muster**erkennungs**-Code für Links: ein Regex mit **escaptem** `!\[` bzw. `<img[^>]+src=`, der gegen eine Allowlist prüft - nicht ein gerendertes Bild.
- Marker-/Phrasen-Konstanten (`LEAK_PHRASES`, Marker-Liste), die in einem **laufenden Abgleich** gegen die Ausgabe benutzt werden - der Abgleich, nicht die Konstante allein, ist der Beleg.
- Ersetzungspfad: `if kritisch: antwort = NEUTRAL_REPLACEMENT` vor dem `return`.

## Was sieht so aus, ist es aber nicht

Nicht abschließend - typische False-Positive-Fallen genau dieser Maßnahme:

| Täuschendes Idiom | Was es wirklich ist |
|---|---|
| `egress:` in einer k8s-`NetworkPolicy` | Netzwerk-Egress-Regel, kein Ausgabefilter |
| gerendertes `<img src=…>` / README-Badge / `![](…)` | Bild-Einbindung, kein Erkennungs-Regex |
| nacktes `allowlist` / `whitelist` / `redact` / `moderation` | Alltagsvokabular ohne verdrahteten Abgleich |
| `"PWNED"` / `"ignore previous instructions"` als Testkonstante/Fixture | Testdatum ohne laufenden Abgleich auf die echte Antwort |
| `canary: true` / „canary release" | DevOps-Rollout, kein Canary-Token-Check |
| `base64` im Secret-/Config-Store | Encoding, kein Umkodierungs-Handling im Canary-Vergleich |
| Content-Moderation-SDK-Import ohne einsehbaren Aufruf am Rückweg | Import ≠ Kette; erst der verfolgte Aufruf zählt |

Jeder Eintrag links wird erst zum Beleg, wenn die gelesene Kette den Abgleich auf die reale Antwort zeigt. Präsenz allein trägt weder ✅ noch ⚠️.

## Häufige Lücken → ⚠️ / ❓

Typische Teilabdeckungen, die zu ⚠️ führen (mit dem durchkommenden Angriff):

- **Nur Antwort, nicht Reasoning** geprüft → der Denkkanal leckt Canary und System-Prompt ungefiltert.
- **Canary-Check ohne Umkodierungen** → das base64- oder bindestrich-gestreute Canary-Leck kommt durch; naiver Substringtest reicht nicht.
- **DAN-Marker case-insensitiv** → False Positives auf „Dan"/„dan"; oder umgekehrt Marker so naiv, dass Umschreibungen des Compliance-Belegs durchrutschen.
- **URL-Prüfung ohne Default-Deny** → nur bekannte Bad-URLs geblockt, jede neue Exfil-Domain passiert.
- **Partielles Schwärzen statt neutralem Gesamt-Ersatz** → aus dem stehengebliebenen Kontext lässt sich das Geheimnis rekonstruieren.
- **Filter greift nur auf einem von mehreren Rückwegen** (z. B. Chat-Antwort ja, Tool-/Function-Call- Rückgabe nein) → ⚠️ nach der Mehrpfad-Regel der Kartierung.

Wann **❓** statt ⚠️/❌: Läuft die Ausgabefilterung über eine **externe Managed-Moderation** (z. B. Bedrock Guardrails, Azure Content Safety) oder einen Fremddienst, dessen Regeln von hier aus nicht einsehbar sind, ist M5 **nicht bewertbar** - der entscheidende Teil liegt außerhalb des Projekts. Das ist kein ❌: die Übergabestelle existiert, nur der Beleg ist von hier aus nicht lesbar.

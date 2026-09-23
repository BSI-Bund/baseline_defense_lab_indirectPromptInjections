# M1 - Eingabe-Bereinigung (vor der Übergabestelle, auf Zeichen- UND Kanalebene)

> Die Maßnahme sitzt auf dem Kettenstück zwischen Quelle und Übergabestelle: Dokumentinhalt wird bereinigt, bevor er in den Prompt eintritt. Definiert ist sie ausschließlich relativ zu dieser Stelle - siehe [Vertrauensgrenze-Kartierung](vertrauensgrenze.md) und [Bewertungsrubrik](bewertungsrubrik.md).

## Was die Maßnahme verlangt (BSI)

M1 entfernt oder entschärft die Tarn- und Steuermechanismen, mit denen ein Angreifer Anweisungen im Dokumentinhalt versteckt, **bevor** dieser Inhalt Teil des Prompts wird. Der Angriff nutzt aus, dass ein LLM Zeichenströme sieht, die für das menschliche Auge unsichtbar oder harmlos wirken: Kompatibilitäts-Varianten, unsichtbare Codepoints, visuell identische Fremdschrift, eingebettete Rollen-Delimiter und Nutzlasten in Nebenkanälen (Metadaten, Outline, Annotationen). M1 wirkt auf zwei Ebenen zugleich - **Zeichenebene** (was steht im Text?) und **Kanalebene** (aus welchem Teil des Dokuments stammt er, und wird jeder Teil überhaupt bereinigt?). Beides muss auf dem Pfad liegen; eine Zeichenbereinigung, die nur den sichtbaren Body sieht, ist auf der Kanalebene blind.

## Wo an der Übergabestelle sie wirkt

M1 wirkt **vor** der Übergabestelle. Auf der gelesenen Belegkette muss zwischen der Quelle (dem Einlesen des Dokuments) und dem Einfügepunkt in den Prompt eine Verarbeitung stehen, die den Dokumentinhalt **tatsächlich durchläuft** - der bereinigte String, nicht der rohe, muss in die Konkatenation / das Template / das `messages.append(...)` gehen. Zu lesen sein muss: (a) welcher String aus der Bereinigung herauskommt, (b) dass **genau dieser** an die Übergabestelle weitergereicht wird. Eine Funktion, die zwar existiert, aber deren Rückgabe nie an der Übergabestelle ankommt (verwaist/tot), liegt nicht auf dem Pfad und ist **❌**, nicht ⚠️. Bei RAG existieren zwei Übergabestellen (Indexierungs- und Abfragezeit) - Bereinigung auf **einem** der beiden Pfade zählt, muss aber beide Pfade prüfen.

## Teil-Aspekte (Umgehungs-Checkliste)

Dies ist eine **Checkliste gegen Umgehung, kein Punktezähler.** Nicht die Zahl der Häkchen entscheidet ✅ vs. ⚠️, sondern ob ein naheliegender Angriff eine Lücke findet.

- **Unicode-Normalisierung (NFKC):** `unicodedata.normalize("NFKC", …)`. Faltet Kompatibilitäts- Varianten auf die kanonische Form. *Fehlt sie:* Ziffern-/Buchstaben-Varianten, Ligaturen und Voll-/Halbbreiten-Formen (z. B. „ｉｇｎｏｒｅ" U+FF49…) tarnen Trigger-Wörter an jedem Keyword-Filter vorbei.
- **Entfernen gefährlicher Zeichenbereiche:** BiDi-Steuerzeichen **U+202A–U+202E** und **U+2066–U+2069** (drehen die sichtbare Reihenfolge gegen die logische - Beleg liest anders als Modell verarbeitet); Zero-Width **U+200B–U+200D** und BOM **U+FEFF** (unsichtbare Trenner zerhacken Wörter unter Filtern hindurch); TAG-Block **U+E0000–U+E007F** (unsichtbare ASCII-Kopie, klassischer Smuggling-Kanal); Variation Selectors **U+FE00–U+FE0F**; Kategorie **Cf** allgemein (`unicodedata.category(ch) == "Cf"`); C0/C1-Steuerzeichen. *Fehlt einer davon:* der zugehörige Kanal transportiert eine vollständige, verdeckte Instruktion ungehindert bis ins Modell.
- **Confusables/Homoglyph-Mapping:** visuell gleiche Fremdzeichen auf ASCII abbilden (kyrillisch а U+0430 → a, griechisch ο U+03BF → o) via `confusable_homoglyphs`, Skeleton-Ansatz, `CONFUSABLE_MAP`. *Fehlt es:* „systеm:" mit kyrillischem е passiert jeden Delimiter-Filter.
- **Rollen-Delimiter neutralisieren:** Chat-Template-Marker im Dokumentinhalt entschärfen - `<|im_start|>`, `<|im_end|>`, `[INST]`, `### instruction`, `system:`/`user:`/`assistant:`. *Fehlt es:* das Dokument bricht aus seinem Datenblock aus und simuliert eine neue Rolle.
- **Whitespace-/Längen-Handling:** Whitespace kollabieren (`re.sub(r"\s{2,}", " ", …)`), pro Kanal längenbegrenzen mit Kürzungsmarker (`"[...]"`). *Fehlt es:* Padding-/Flooding-Angriffe drücken den System-Prompt aus dem Kontext.
- **Kanaltrennung:** Body, Metadaten, Outline und Annotationen **getrennt auslesen UND je Kanal bereinigen** - `pypdf`/`pdfplumber`/`pymupdf`/`fitz`, `reader.metadata`, `/Annots`, `reader.outline`, `/Outlines`, XMP. *Fehlt sie:* die Injektion sitzt im Autor-Feld oder in einer Annotation und wird ungeprüft in den Prompt gehängt, obwohl der Body sauber ist.
- **Trigger markieren & protokollieren, NICHT löschen (Human-in-the-Loop):** verdächtige Muster melden (`logger.warning("suspicious trigger …")`), statt still zu entfernen. *Fehlt es:* Forensik geht verloren, und stilles Löschen kann legitimen Text zerstören.

## Was zählt als Beleg

Die **gelesene Kette** Quelle → Bereinigung → Übergabestelle, in der der Dokumentinhalt die Bereinigung tatsächlich durchläuft. **Die Wirkung auf dem Pfad zählt, nicht der Name der Funktion** - `entschaerfe_dokument()`, `clean_channels()`, `INVISIBLE_RE.sub("", …)`, `strip_invisible_chars(…)`, eine `str.translate`-Tabelle oder eine handgeschriebene Zeichenklasse mit den obigen Codepoints sind gleichwertige Belege, sofern ihr Ergebnis an der Übergabestelle ankommt. Für die Kanalebene gilt: die Kette muss zeigen, dass **jeder** eingelesene Kanal (nicht nur `extract_text()`) durch die Bereinigung läuft - sonst ist die Zeichenbereinigung zwar vorhanden, aber nur teilweise verdrahtet.

## Was sieht so aus, ist es aber nicht

Falsch-Positiv-Fallen genau dieser Maßnahme (**nicht abschließend**) - Präsenz allein trägt nie ✅ oder ⚠️:

| Täuschendes Idiom | Was es wirklich ist |
|---|---|
| `from __future__ import annotations` | Python-Idiom - keine Kanal-Annotation |
| `normalize(...)` / `StandardScaler` / Vektor-Normalisierung | numerische Normalisierung - kein NFKC |
| `### Überschrift` | Markdown-H3 - kein Rollen-Delimiter |
| CSS `outline:` / Slack-„channel" / RGB-Channel | Styling/Chat/Farbkanal - keine PDF-Outline, keine Kanaltrennung |
| nacktes `truncate` / `max_len` | Alltags-Kürzung - kein bewusstes IPI-Längen-Handling |
| `bleach` / `html.escape` / `DOMPurify` | XSS-/HTML-Schutz - keine IPI-Zeichenbereinigung |

Jeder Eintrag links wird erst zum Beleg, wenn die gelesene Kette es hergibt (Wirkung auf dem Pfad).

## Häufige Lücken → ⚠️ / ❓

- **NFKC vorhanden, aber BiDi/Zero-Width/TAG bleiben.** Die auffälligste Teilabdeckung: ein `normalize("NFKC")` steht auf dem Pfad, doch U+202E, U+200B oder der TAG-Block werden nicht entfernt. Ein naheliegender Angriff kommt durch → **⚠️**, unabhängig davon, wie sauber die Normalisierung ist.
- **Nur Body bereinigt, Nebenkanäle nicht.** Zeichenbereinigung greift auf `extract_text()`, aber `reader.metadata`, `/Annots` und die Outline gehen roh in den Prompt → Kanal-Lücke → **⚠️**.
- **Greift nur auf einem von mehreren Eintrittspfaden** (Upload bereinigt, RAG-Chunk oder URL-Abruf nicht) → **⚠️**.
- **Trigger werden gelöscht statt markiert+protokolliert** → Human-in-the-Loop-Aspekt fehlt; je nach Restabdeckung ⚠️.
- **Bereinigung liegt in einem externen Dienst / managed Guardrail** (außerhalb des Projekts nicht lesbar) oder im RAG-Indexierungspfad zu einem fremden Vektor-Store → **❓ nicht bewertbar**, nicht ❌.
- Zur Erinnerung: eine definierte, aber **nie auf dem Pfad aufgerufene** Bereinigung ist **❌** - kein halber Beweis.

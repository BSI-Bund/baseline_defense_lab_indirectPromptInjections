# Hinweise zu Drittinhalten

<!-- Diese Datei zitiert durchgehend fremde Copyright- und Lizenzvermerke. Sie selbst steht, wie das ganze Repository, unter EUPL-1.2. -->
Baseline-Defense-Lab steht unter der **EUPL-1.2** (siehe [`LICENSE`](LICENSE)). Diese Datei sammelt die Lizenz- und Attributionshinweise für Inhalte Dritter, die das Projekt nutzt oder mitausliefert.

**Grundsatz:** Dieses Repository *vendort keinen Fremdcode*. Alle Bibliotheken werden zur Installationszeit über `pip` bzw. `npm` bezogen und behalten ihre eigene Lizenz; sie werden nicht verändert. Der Quellbaum enthält Eigencode unter EUPL-1.2 — mit den unten einzeln aufgeführten Ausnahmen.

## 1. Mitausgelieferte Abhängigkeiten in den Container-Images

### Angular-Frontend-Bundle

Welche Pakete tatsächlich im gebauten SPA-Bundle landen, ist autoritativ in der Datei **`3rdpartylicenses.txt`** festgehalten, die der Angular-Produktionsbuild erzeugt; sie enthält zu jedem Paket den vollständigen Copyright-Vermerk und Lizenztext. Zum Stand dieses Dokuments sind das zehn Pakete: `@angular/animations`, `@angular/cdk`, `@angular/common`, `@angular/core`, `@angular/forms`, `@angular/material`, `@angular/platform-browser` (alle MIT, Copyright © 2010–2024 Google LLC), `rxjs` (Apache-2.0), `zone.js` (MIT) und `tslib` (0BSD).

Beide Container-Images liefern diese Datei mit aus und stellen sie über HTTP bereit:

| Image | Pfad im Dateisystem | HTTP |
| --- | --- | --- |
| Frontend (nginx) | `/usr/share/nginx/html/3rdpartylicenses.txt` | `/3rdpartylicenses.txt` |
| Backend (FastAPI + gebündeltes SPA) | `/app/frontend_dist/3rdpartylicenses.txt` | `/3rdpartylicenses.txt` |

Dasselbe gilt für `LICENSE` und diese Datei: beide sind in beiden Images unter `/LICENSE` bzw. `/THIRD-PARTY-NOTICES.md` abrufbar. Damit sind die Weitergabepflichten der MIT-Lizenz ("in all copies or substantial portions of the Software") und von Apache-2.0 Abschnitt 4 für die Auslieferung erfüllt.

### Python-Abhängigkeiten

Die Kerninstallation zieht `pypdf` (BSD-3-Clause), `requests` (Apache-2.0) und `pydantic` (MIT) samt deren Abhängigkeiten. Nahezu jedes per `pip` installierte Paket bringt seinen Lizenztext in seinem `*.dist-info/`-Verzeichnis mit; in den Images ist er dort vorhanden. Eine Bestandsaufnahme mit Lizenzangabe liefert `pip list` bzw. `pip show <paket>`.

Es gibt Ausreißer: `langsmith` und `langchain-core` legen in den eingesetzten Versionen **keinen** Lizenztext ins `dist-info` (beide MIT, Copyright LangChain, Inc.). Wer diese Pakete weiterverteilt, muss den Lizenztext selbst beischaffen — er steht in den jeweiligen Upstream-Repositories unter <https://github.com/langchain-ai/langchain> bzw.
<https://github.com/langchain-ai/langsmith-sdk>.

**Wichtig zum Umfang:** beide gehören zwar zum Extra `[langchain]` und nicht zur Kerninstallation — das **Backend-Container-Image liefert sie aber mit**, weil `docker/backend.Dockerfile` dort `./backend[server,langchain]` installiert. Aufgelöst sind das 51 Pakete im Image gegenüber 12 in der Kerninstallation. Wer das Image weitergibt, verteilt also MIT-lizenzierten Code, dessen Erlaubnisvermerk im Paket fehlt, und muss ihn beilegen. Dasselbe gilt für `orjson` (MPL-2.0, siehe Tabelle unten), das ebenfalls nur über dieses Extra hereinkommt und im Image landet.

Besonders hinzuweisen ist auf:

| Paket | Lizenz | Hinweis |
| --- | --- | --- |
| `certifi` | MPL-2.0 | Schwaches, dateibezogenes Copyleft. Das Paket wird unverändert und als Quellcode ausgeliefert, der Lizenztext liegt im `dist-info` — damit ist MPL-2.0 Abschnitt 3.1 erfüllt. Upstream: <https://github.com/certifi/python-certifi>. |
| `orjson` | MPL-2.0 AND (Apache-2.0 OR MIT) | Nur im Extra `[langchain]`. Wird als vorkompiliertes Wheel, also in Executable Form, ausgeliefert; hier greift MPL-2.0 Abschnitt 3.2, der den Hinweis auf die Quelle verlangt: <https://github.com/ijl/orjson>. |
| `requests`, `tenacity`, `distro`, `requests-toolbelt` | Apache-2.0 | Unverändert eingebunden, daher ist kein Änderungsvermerk nach Abschnitt 4(b) erforderlich. Etwaige `NOTICE`-Dateien werden mit dem jeweiligen Paket weitergegeben. |
| `typing-extensions` | PSF-2.0 | Python Software Foundation License. |

## 2. Übernommene Datenbestände im Eigencode

`backend/src/baseline_defense_lab/toolbox/input_sanitizer/sanitizer.py` leitet die Bereichsliste `_DEFAULT_IGNORABLE_RANGES` aus der Unicode-Eigenschaft `Default_Ignorable_Code_Point` ab (Datei `DerivedCoreProperties.txt` der Unicode Character Database). Die Auswahl der Zeichenzuordnungen in `_ASCII_CONFUSABLES_MAP` ist an die Confusables-Daten von Unicode UTS #39 angelehnt, bildet sie aber nicht ab: die Ziele sind dort durchgängig ASCII-Zeichen, nicht die Prototypen des Standards.

Die Unicode-Lizenz erlaubt ausdrücklich, ihren Vermerk statt in jeder Kopie in der zugehörigen Dokumentation wiederzugeben (Variante (b) des Permission-Grants). Das geschieht hier. Der Vermerk lautet im Wortlaut:

> **UNICODE LICENSE V3** COPYRIGHT AND PERMISSION NOTICE Copyright © 1991-2026 Unicode, Inc. NOTICE TO USER: Carefully read the following legal agreement. BY DOWNLOADING, INSTALLING, COPYING OR OTHERWISE USING DATA FILES, AND/OR SOFTWARE, YOU UNEQUIVOCALLY ACCEPT, AND AGREE TO BE BOUND BY, ALL OF THE TERMS AND CONDITIONS OF THIS AGREEMENT. IF YOU DO NOT AGREE, DO NOT DOWNLOAD, INSTALL, COPY, DISTRIBUTE OR USE THE DATA FILES OR SOFTWARE. Permission is hereby granted, free of charge, to any person obtaining a copy of data files and any associated documentation (the "Data Files") or software and any associated documentation (the "Software") to deal in the Data Files or Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, and/or sell copies of the Data Files or Software, and to permit persons to whom the Data Files or Software are furnished to do so, provided that either (a) this copyright and permission notice appear with all copies of the Data Files or Software, or (b) this copyright and permission notice appear in associated Documentation. THE DATA FILES AND SOFTWARE ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF THIRD PARTY RIGHTS. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR HOLDERS INCLUDED IN THIS NOTICE BE LIABLE FOR ANY CLAIM, OR ANY SPECIAL INDIRECT OR CONSEQUENTIAL DAMAGES, OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THE DATA FILES OR SOFTWARE. Except as contained in this notice, the name of a copyright holder shall not be used in advertising or otherwise to promote the sale, use or other dealings in these Data Files or Software without prior written authorization of the copyright holder.

Quelle: <https://www.unicode.org/license.txt>. Die Lizenz ist permissiv und mit der EUPL-1.2 vereinbar.

**Zur Einordnung.** Übernommen sind dreizehn Zeilen Bereichsangaben — Anfangs- und Endcodepunkte einer im Standard definierten Zeicheneigenschaft —, kein Programmtext. Solche Codepunktbereiche sind Tatsachenangaben und nach hiesiger Einschätzung keine persönliche geistige Schöpfung; an ihnen besteht kein eigenes Urheberrecht, das lizenziert werden müsste. Der vorstehende Vermerk wird daher als Höflichkeit und zur Nachvollziehbarkeit der Herkunft wiedergegeben — die Unicode-Lizenz lässt genau das ausdrücklich zu (Variante (b) des Permission Grants) —, **ohne für die betroffene Datei eine zweite SPDX-Lizenzkennung zu beanspruchen.** Die Datei bleibt als Ganzes EUPL-1.2.

Das ist auch der saubere Weg gegenüber Werkzeugen, die Lizenzkennungen gegen eine Positivliste prüfen: `Unicode-3.0` ist dort vielfach noch nicht geführt. Würde man die Kennung für eine Datei dieses Repositorys deklarieren, entstünde eine Lizenzangabe, der kein lizenzierungsbedürftiger Schutzgegenstand gegenübersteht.

## 3. Container-Basisimages

Die Images bauen auf `node:20-alpine` (nur Build-Stage), `nginx:1.27-alpine` (Frontend) und `python:3.12-slim` (Backend) auf. Diese Basisimages enthalten Betriebssystembestandteile unter eigenen Lizenzen, darunter GPL-2.0-lizenzierte Komponenten (`busybox`, `apk-tools` bzw. die Debian-Basiswerkzeuge) und nginx selbst (BSD-2-Clause).

Diese Bestandteile sind vom Werk dieses Projekts getrennt; sie werden im Image lediglich zusammengestellt und nicht mit dem Eigencode zu einem abgeleiteten Werk verbunden ("mere aggregation"). Die EUPL-1.2-Lizenzierung des Eigencodes bleibt davon unberührt.

**Wer selbst gebaute Images weiterverteilt, muss die Pflichten dieser Bestandteile aber selbst erfüllen — und die beiden Basissysteme sind dabei unterschiedlich gut ausgestattet:**

- Das **Debian-basierte Backend-Image** bringt sie mit: 85 Dateien `/usr/share/doc/*/copyright` und die vollständige Sammlung `/usr/share/common-licenses/` (GPL, GPL-2, GPL-3, LGPL, Apache-2.0, MPL-2.0 und weitere).
- Das **Alpine-basierte Frontend-Image** bringt sie **nicht** mit. Alpine-Pakete installieren keine Lizenztexte; im Image liegen nur fünf nginx-eigene `COPYRIGHT`-Dateien unter `/usr/share/licenses/`, und `/usr/share/common-licenses/` existiert dort nicht. Wer dieses Image weitergibt, verteilt GPL-2.0-Binärdateien (unter anderem `busybox` und `apk-tools`) ohne Lizenztext und ohne Quellangebot. Beides ist in diesem Fall selbst beizulegen; die Quellen liegen unter <https://gitlab.alpinelinux.org/alpine/aports>.

Wer nur dieses Repository (Quellcode und Dockerfiles) veröffentlicht und keine gebauten Images verteilt, ist von diesen Pflichten nicht betroffen.

## 4. Modellgewichte

Die Sprachmodelle sind **nicht Teil dieses Werks** und werden nicht mitausgeliefert. Der `ollama-init`-Container lädt sie zur Laufzeit von <https://ollama.com> herunter. Die Voreinstellung `OLLAMA_MODEL=gemma3:12b` unterliegt den **Gemma Terms of Use** — das ist *keine* Open-Source-Lizenz, sie enthält Nutzungsbeschränkungen. Andere Modelle haben eigene, teils ebenfalls einschränkende Bedingungen.

Wer das Labor betreibt, muss die Bedingungen des gewählten Modells selbst prüfen und einhalten. Das Modell lässt sich über `OLLAMA_MODEL` frei wechseln.

## 5. Nicht enthalten

Zur Klarstellung, weil beides oft vermutet wird: Das Frontend liefert **keine Bild-Assets** aus. Es sind **keine Schriftarten** eingebettet; es nutzt ausschließlich Fallback-Schriftstapel des Systems und lädt keine entfernten Schriften.


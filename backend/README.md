# baseline-defense-lab (Python-Distribution)

Backend-Distribution des **Baseline-Defense-Lab** — eines Lehr- und Testlabors, das zeigt, wie Basis-Abwehrmaßnahmen gegen indirekte Prompt Injection im Dokumenten-Chat implementiert und kombiniert werden und wo ihre ehrlichen Grenzen liegen.

Das Paket enthält die fünf Basis-Werkzeuge (`toolbox/`), denselben Satz Maßnahmen als LangChain-Middleware (`langchain_defenses/`) sowie die FastAPI-Anwendung (`server/`).

- **Vollständige Dokumentation, Aufbau und Sicherheitshinweise:** siehe `README.md` im Wurzelverzeichnis des Projekt-Repositorys.
- **Installation:** aus dem Quellbaum, `pip install -e "backend[server]"` für die HTTP-API, zusätzlich `[langchain]` für den zweiten Pipeline-Pfad (Einzelheiten in `INSTALL.md`). Eine Veröffentlichung auf PyPI existiert bislang nicht.
- **Lizenz:** EUPL-1.2. Der vollständige Lizenztext liegt als `LICENSE` bei; die Lizenzhinweise der Abhängigkeiten stehen in `THIRD-PARTY-NOTICES.md` im Repository.

> Dieser Stack hat keine Authentifizierung und ist für den lokalen Loopback-Betrieb zum Lernen gedacht, nicht für den Produktivbetrieb.

## Hinweis zu Drittinhalten

`toolbox/input_sanitizer/sanitizer.py` leitet die Bereichsliste `_DEFAULT_IGNORABLE_RANGES` aus der Unicode-Eigenschaft `Default_Ignorable_Code_Point` der Unicode Character Database ab. Die Unicode-Lizenz erlaubt, ihren Vermerk in der zugehörigen Dokumentation wiederzugeben; da diese Datei mit jedem Wheel und jedem sdist ausgeliefert wird, steht er hier:

> **UNICODE LICENSE V3** — COPYRIGHT AND PERMISSION NOTICE Copyright © 1991-2026 Unicode, Inc. NOTICE TO USER: Carefully read the following legal agreement. BY DOWNLOADING, INSTALLING, COPYING OR OTHERWISE USING DATA FILES, AND/OR SOFTWARE, YOU UNEQUIVOCALLY ACCEPT, AND AGREE TO BE BOUND BY, ALL OF THE TERMS AND CONDITIONS OF THIS AGREEMENT. IF YOU DO NOT AGREE, DO NOT DOWNLOAD, INSTALL, COPY, DISTRIBUTE OR USE THE DATA FILES OR SOFTWARE. Permission is hereby granted, free of charge, to any person obtaining a copy of data files and any associated documentation (the "Data Files") or software and any associated documentation (the "Software") to deal in the Data Files or Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, and/or sell copies of the Data Files or Software, and to permit persons to whom the Data Files or Software are furnished to do so, provided that either (a) this copyright and permission notice appear with all copies of the Data Files or Software, or (b) this copyright and permission notice appear in associated Documentation. THE DATA FILES AND SOFTWARE ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF THIRD PARTY RIGHTS. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR HOLDERS INCLUDED IN THIS NOTICE BE LIABLE FOR ANY CLAIM, OR ANY SPECIAL INDIRECT OR CONSEQUENTIAL DAMAGES, OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THE DATA FILES OR SOFTWARE. Except as contained in this notice, the name of a copyright holder shall not be used in advertising or otherwise to promote the sale, use or other dealings in these Data Files or Software without prior written authorization of the copyright holder.

Die vollständige Aufstellung aller Drittinhalte steht in `THIRD-PARTY-NOTICES.md` im Projekt-Repository.


# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""The defense toolbox - one folder per tool from the 5-tool toolbox.

Each tool's code is bundled in its own subpackage so a reader can find
everything for a tool in one place:

* ``trust_separation/`` - Tool 1: structural document wrap, session-scoped
  delimiters, datamarking, sandwich defense, typed-channel rendering, plus
  the instruction-hierarchy rule written into the system prompt in the same
  step. With the tool off there is NO wrap at all - the pipeline falls back
  to naive prompt concatenation.
* ``input_sanitizer/``  - Tool 2: NFKC/BiDi/confusables ``sanitize_text`` and
  the channel parser.
* ``hardened_prompt/``  - Tool 3: the 8-section hardened system prompt and the
  encoding-aware canary (TEIL 2 is the same hierarchy rule Tool 1 sets -
  rendered exactly once when both are active).
* ``reasoning/``        - Tool 4: the think/answer merge.
* ``egress_guard/``     - Tool 5: the shared egress scan and history hygiene.

``pipeline.py`` composes the active tools into one request/response flow;
``mechanisms.py`` holds the internal gate set that the public
``baseline_defense_lab.tools.DefenseTools`` folds to (5 tools -> 13 gates).

The submodules are imported explicitly by consumers; this package ``__init__``
stays import-light on purpose.
"""

# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""The five-tool defense model  the only defense surface the API/UI expose.

Instead of a dozen fine-grained flags this lab presents exactly **five
tools**, each a single boolean. Internally a tool folds one or more of the
mechanism gates in :class:`baseline_defense_lab.toolbox.mechanisms.DefenseMechanisms`,
but the API (``/api/tools``) and the frontend only ever see these five:

================  ===================================================  ==============================================
Tool (API key)    Pipeline stage                                       Folds (internal mechanisms)
================  ===================================================  ==============================================
trust_separation  Prompt assembly + system prompt                      structural wrap (envelope, typed 4-channel
                                                                       split, <user_message> framing, hierarchy rule
                                                                       in the system prompt), session-scoped
                                                                       delimiters, boundary datamarking, sandwich
                                                                       defense  OFF ⇒ naive prompt concatenation
input_sanitizer   Ingest                                               sanitize_input (+ always-on BiDi strip),
                                                                       confusables map
hardened_prompt   System prompt                                        8-section hardened prompt, embedded canary
reasoning         Model call                                           Ollama ``think`` channel + merge
egress_guard      Response                                             shared egress scan + history hygiene
================  ===================================================  ==============================================

Honesty discipline: every description names the *limit* of each tool,
not just its benefit. The
footgun combination (``hardened_prompt`` without ``egress_guard``) is
**allowed**  it is pedagogically the documented net-harmful shape  but it
is surfaced via :meth:`DefenseTools.dependency_warnings`, never hidden.

The class is frozen so a request cannot mutate the tool set mid-pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from .toolbox.mechanisms import DefenseMechanisms

#: The canonical tool order. Single source of truth for the API list and the
#: frontend rendering order.
TOOL_ORDER: tuple[str, ...] = (
    "trust_separation",
    "input_sanitizer",
    "hardened_prompt",
    "reasoning",
    "egress_guard",
)

#: Human-facing German descriptions (was / warum / Grenze), used by
#: ``GET /api/tools`` and the UI tooltips. Honest by design: every entry
#: names the limit of the tool, not only its upside.
TOOL_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "trust_separation": {
        "title": "Vertrauenstrennung (Struktur)",
        "stage": "Prompt-Assembly + System-Prompt",
        "what": (
            "Teilt den Prompt erst mit diesem Tool in System/Nutzer/"
            "unvertrauenswürdig auf: Dokumentinhalt in einer getypten, klar "
            "als unvertrauenswürdig markierten Struktur (frischer Per-Request-"
            "Delimiter sec-<hex>, getypte Kanäle BODY/METADATA/OUTLINE/"
            "ANNOTATIONS, Datamarking der Ränder, Sandwich-Preamble/"
            "Postamble, escapte Schließ-Tags), die Nutzerfrage in "
            "<user_message>-Rahmung  und im selben Schritt die Instruktions-"
            "Hierarchie-Regel (System > Nutzer > Dokument) im Systemprompt. "
            "Ohne dieses Tool wird der Prompt naiv konkateniert (keine "
            "Struktur, keine Hierarchie-Regel)."
        ),
        "why": (
            "Struktur ist der stärkste Einzelhebel: das Modell liest die "
            "Vertrauensstufe aus der Prompt-Struktur selbst ab  und die "
            "Hierarchie-Regel benennt genau diese Struktur im Systemprompt."
        ),
        "limit": (
            "Verhindert keinen Leak einer bereits erzeugten Antwort und keine "
            "Exfiltration  dafür ist der Egress-Guard zuständig. Ein "
            "hinreichend manipulierbares Modell kann Struktur ignorieren."
        ),
    },
    "input_sanitizer": {
        "title": "Eingabe-Sanitisierung",
        "stage": "Ingest",
        "what": (
            "NFKC-Normalisierung, immer-an BiDi-Strip (BiDi-Override-/Isolate-"
            "Spannen werden samt verborgenem Inhalt redigiert, nicht nur "
            "enttarnt), Whitespace-Fold, kontextsensitiver Zero-Width-/Format-"
            "Strip, per-Token Confusables-Mapping (Kyrillisch/Griechisch/"
            "Mathematisch → ASCII), Rollen-Token-Neutralisierung und "
            "Längenkappe auf allen untrusted Kanälen."
        ),
        "why": (
            "Neutralisiert Unicode-Tarnung (BiDi-Spoofing, Zero-Width-Splits, "
            "Confusables, TAG-Block), BEVOR detektiert wird  sonst umgeht ein "
            "Zero-Width-Split jede spätere Erkennung."
        ),
        "limit": (
            "Verborgene BiDi-Override-/Isolate-Spannen werden entfernt; eine "
            "*unverhüllt* im Klartext formulierte Injektion ist jedoch keine "
            "Tarnung und bleibt für das Modell lesbar."
        ),
    },
    "hardened_prompt": {
        "title": "Gehärteter Prompt + Canary",
        "stage": "System-Prompt",
        "what": (
            "Ergänzt die restlichen Abschnitte des 8-Teile-Sicherheitsprompts "
            "(Identität, Daten-/Instruktions-Trennung, Wissensstand, harte "
            "Verbote, Canary, Output-Regeln, Fail-Safe) mit eingebettetem "
            "128-bit-Canary und dem echten Session-Delimiter. Die "
            "Instruktions-Hierarchie (TEIL 2) ist dieselbe Regel, die bereits "
            "die Vertrauenstrennung setzt  sie erscheint genau einmal."
        ),
        "why": (
            "Gibt dem Modell eine explizite Instruktions-Hierarchie "
            "(System > Nutzer > Dokument = keine Autorität) und legt mit dem "
            "Canary ein leakbares Geheimnis als Stolperdraht aus."
        ),
        "limit": (
            "Prompt-Text allein ist schwach. OHNE Egress-Guard ist der Canary "
            "ein leakbares Geheimnis ohne Detektor  die dokumentierte "
            "net-schädliche V4-Form (siehe Warnung)."
        ),
    },
    "reasoning": {
        "title": "Reasoning (Denk-Kanal)",
        "stage": "Model-Call",
        "what": (
            "Aktiviert den Ollama-think-Kanal vor der sichtbaren Antwort; "
            "Gedankengang und Antwort werden zu einer Oberfläche gemergt, "
            "damit der Egress-Guard auf jeder Engine dasselbe bewertet."
        ),
        "why": (
            "Kann helfen, wo das Modell den Denkkanal unterstützt: das Modell "
            "bekommt Gelegenheit, die Anweisung als Dokumentinhalt zu erkennen, "
            "bevor es antwortet. Um wie viel, wird hier nicht beziffert."
        ),
        "limit": (
            "Nur bei Modellen wirksam, die Ollamas think-Kanal unterstützen. "
            "Modelle ohne diesen Kanal (z. B. gemma3) lehnen think mit HTTP 400 "
            "ab; der Lauf wird dann ohne Reasoning ausgeführt und mit "
            "reasoning_active=false ausgewiesen - das Werkzeug ist in diesem "
            "Fall wirkungslos (keine Schein-Sicherheit)."
        ),
    },
    "egress_guard": {
        "title": "Egress-Guard (Ausgangskontrolle)",
        "stage": "Response",
        "what": (
            "Geteilter Egress-Scan auf Canary-Leak (enkodierungsbewusst), "
            "System-Prompt-Leak (F1a/F1c/F1d, CoT-kalibriert), Injection-/"
            "Compliance-Marker und jede Exfiltration (Bilder, "
            "Referenz-Definitionen, nicht-allowlistete URLs  fail-closed) "
            "plus History-Hygiene. Blockiert statt zu strippen."
        ),
        "why": (
            "Modellunabhängige letzte Linie. Dieselbe Bibliothek misst und "
            "liefert aus ('measured = shipped')  sie greift unabhängig davon, "
            "ob das Modell der Injektion gefolgt ist."
        ),
        "limit": (
            "Greift erst nach der Generierung. Marker-basiert und damit eine "
            "untere Schranke: was keinen bekannten Marker trägt, sieht er nicht."
        ),
    },
}


@dataclass(frozen=True, slots=True)
class DefenseTools:
    """The five defense tools. The only defense surface exposed to API + UI."""

    #: Tool 1  structural trust separation (wrap/delimiter/datamark/sandwich
    #: + the instruction-hierarchy rule in the system prompt). Off ⇒ naive
    #: prompt concatenation.
    trust_separation: bool = False
    #: Tool 2  Unicode/length input sanitisation on all untrusted channels.
    input_sanitizer: bool = False
    #: Tool 3  hardened 8-section system prompt with embedded canary.
    hardened_prompt: bool = False
    #: Tool 4  Ollama reasoning/think channel before the visible answer.
    reasoning: bool = False
    #: Tool 5  shared egress guard + history hygiene on the response.
    egress_guard: bool = False

    # ---- folding into the internal mechanism gates --------------------

    def to_mechanisms(self) -> DefenseMechanisms:
        """Expand the five tools into the fine-grained internal gates.

        This is the single place where the 5→13 folding lives. The defense
        helpers and LangChain middlewares consume the returned mechanism set
        unchanged.
        """
        return DefenseMechanisms(
            # Tool 2
            sanitize_input=self.input_sanitizer,
            wp5_confusables_map=self.input_sanitizer,
            # wp1 is a deprecated no-op (BiDi strip is always-on in the base
            # sanitizer); kept False so a single sanitize_text pass matches.
            wp1_bidi_normalize=False,
            # Tool 1
            structural_wrap=self.trust_separation,
            datamark_document_boundaries=self.trust_separation,
            datamark_full_text=False,  # code constant, never a UI switch
            sandwich_defense=self.trust_separation,
            session_scoped_delimiters=self.trust_separation,
            # Tool 3
            hardened_system_prompt=self.hardened_prompt,
            canary_token=self.hardened_prompt,
            # Tool 5
            output_filter=self.egress_guard,
            sanitize_history=self.egress_guard,
            # Tool 4
            reasoning=self.reasoning,
        )

    # ---- introspection -------------------------------------------------

    def dependency_warnings(self) -> list[str]:
        """Return human-readable warnings for net-harmful tool combinations.

        The one documented footgun: ``hardened_prompt`` (which embeds a
        canary secret) without ``egress_guard`` (which detects the leak) is
        the net-harmful V4 shape  a leakable secret with no detector. The
        combination is *allowed* (teaching value) but always surfaced, never
        hidden, and logged server-side.
        """
        warnings: list[str] = []
        if self.hardened_prompt and not self.egress_guard:
            warnings.append(
                "Canary ohne Egress-Detektor  leakbares Geheimnis ohne "
                "Schutz: 'Gehärteter Prompt + Canary' bettet ein Geheimnis ein, "
                "das ohne 'Egress-Guard' niemand auf Leaks prüft (dokumentierte "
                "net-schädliche V4-Form). Aktiviere zusätzlich den Egress-Guard."
            )
        if self.hardened_prompt and not self.trust_separation:
            warnings.append(
                "Gehärteter Prompt ohne Vertrauenstrennung  der Prompt "
                "beschreibt eine Struktur, die nicht existiert: TEIL 2/3 "
                "verweisen auf <user_message>- und <untrusted_document_context>-"
                "Grenzen, die nur die 'Vertrauenstrennung (Struktur)' rendert. "
                "Ohne sie wird der Prompt naiv konkateniert und die Regeln "
                "laufen ins Leere. Aktiviere zusätzlich die Vertrauenstrennung."
            )
        return warnings

    def as_dict(self) -> dict[str, bool]:
        """Materialise the five tools as an ordered dict (snapshot/logging)."""
        return {
            "trust_separation": self.trust_separation,
            "input_sanitizer": self.input_sanitizer,
            "hardened_prompt": self.hardened_prompt,
            "reasoning": self.reasoning,
            "egress_guard": self.egress_guard,
        }

    # ---- named compositions -------------------------------------------

    @classmethod
    def all_off(cls) -> DefenseTools:
        """The baseline with every tool off (the UI default).

        Truly unguarded: the prompt is naively concatenated  plain default
        system prompt, then the user question and the raw document joined
        into one user turn. No ``<untrusted_document_context>`` envelope, no
        typed-channel split, no ``<user_message>`` framing, no close-tag
        escaping. All structure (and the instruction-hierarchy rule in the
        system prompt) arrives only with ``trust_separation``. This
        supersedes the earlier always-on-scaffolding baseline (audit K-006).
        """
        return cls()


def tool_schema() -> list[dict[str, str]]:
    """Return the ordered ``/api/tools`` payload (name + description fields)."""
    schema: list[dict[str, str]] = []
    for name in TOOL_ORDER:
        d = TOOL_DESCRIPTIONS[name]
        schema.append(
            {
                "name": name,
                "title": d["title"],
                "stage": d["stage"],
                "what": d["what"],
                "why": d["why"],
                "limit": d["limit"],
                # Flat one-line description for tooltips that want a single string.
                "description": f"{d['what']}  Warum: {d['why']} Grenze: {d['limit']}",
            }
        )
    return schema

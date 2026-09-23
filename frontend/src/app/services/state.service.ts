// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2
import { Injectable, computed, inject, signal } from '@angular/core';

import { ApiService } from './api.service';
import {
  ChatRequestPayload,
  ChatResponse,
  Engine,
  HealthResponse,
  Tool,
  ToolName,
  ToolsState,
} from '../models/api-types';

/**
 * The lab's three active models, in default-pick order. The first one that
 * Ollama actually reports (GET /api/healthz → models) is auto-selected. The
 * dropdown itself only ever lists the models Ollama reports, so no inactive
 * tag can be picked.
 */
const PREFERRED_MODELS = ['gemma3:12b', 'qwen3:14b', 'qwen3:30b'];

/** The canonical tool order - mirrors the backend ``TOOL_ORDER``. */
const TOOL_ORDER: ToolName[] = [
  'trust_separation',
  'input_sanitizer',
  'hardened_prompt',
  'reasoning',
  'egress_guard',
];

/** Every tool off - the unguarded baseline (also the UI default). */
function allOff(): ToolsState {
  return {
    trust_separation: false,
    input_sanitizer: false,
    hardened_prompt: false,
    reasoning: false,
    egress_guard: false,
  };
}

/**
 * Central signal-backed state container for the teaching UI.
 *
 * Child components react automatically when the sidebar or workspace mutates
 * the shared state. The service does its own HTTP work via {@link ApiService}
 * to keep components thin.
 */
@Injectable({ providedIn: 'root' })
export class StateService {
  private readonly api = inject(ApiService);

  // ---- inputs ---------------------------------------------------------

  readonly model = signal<string>('');
  // Generation parameters are no longer user-editable in the UI - they are
  // fixed to the backend's GENERATION_DEFAULTS (fetched in initialise()).
  // These compiled-in values are only fallbacks if GET /api/defaults fails.
  readonly seed = signal<number>(17);
  readonly numPredict = signal<number>(4096);
  readonly temperature = signal<number>(0);
  readonly topP = signal<number>(1);

  readonly userQuestion = signal<string>('Was steht im Dokument?');
  readonly documentText = signal<string>('');
  readonly fileName = signal<string>('dokument.pdf');

  /**
   * Pipeline path. ``direct`` calls POST /api/chat; ``langchain`` calls
   * POST /api/chat_langchain. Same envelope - only the engine differs.
   */
  readonly engine = signal<Engine>('direct');

  // ---- schema / tools -------------------------------------------------

  /** The five tool descriptors fetched from GET /api/tools (never hardcoded). */
  readonly tools = signal<Tool[]>([]);

  /** Current per-tool toggle state (the five booleans). */
  readonly toolState = signal<ToolsState>(allOff());

  readonly activeToolCount = computed<number>(
    () => Object.values(this.toolState()).filter(Boolean).length,
  );

  readonly totalToolCount = computed<number>(() => this.tools().length || TOOL_ORDER.length);

  // ---- health ---------------------------------------------------------

  readonly health = signal<HealthResponse | null>(null);
  readonly models = computed<string[]>(() => this.health()?.models ?? []);

  // ---- run state ------------------------------------------------------

  readonly running = signal<boolean>(false);
  readonly lastError = signal<string | null>(null);
  readonly lastResponse = signal<ChatResponse | null>(null);

  /**
   * Server-authoritative warnings for the last run (backend
   * ``DefenseTools.dependency_warnings``). The one documented footgun - a
   * hardened prompt embeds a canary secret without the egress guard to detect
   * a leak - is surfaced here from the response, never re-derived client-side,
   * so the warning text has a single source of truth. Empty before the first
   * run and whenever no net-harmful combination is active.
   */
  readonly warnings = computed<string[]>(() => this.lastResponse()?.warnings ?? []);

  // ---- lifecycle ------------------------------------------------------

  initialise(): void {
    this.refreshHealth();

    // Generation defaults come from the backend (single source of truth).
    this.api.defaults().subscribe({
      next: (d) => {
        this.seed.set(d.seed);
        this.numPredict.set(d.num_predict);
        this.temperature.set(d.temperature);
        this.topP.set(d.top_p);
      },
      error: () => {
        // keep the compiled-in fallbacks; not fatal
      },
    });

    // The five tools - fetched at runtime, never hardcoded.
    this.api.tools().subscribe({
      next: (schema) => this.tools.set(schema.tools),
      error: (err) =>
        this.lastError.set(
          'Werkzeug-Schema konnte nicht geladen werden: ' + this.describeError(err),
        ),
    });
  }

  refreshHealth(): void {
    this.api.health().subscribe({
      next: (data) => {
        this.health.set(data);
        if (!this.model() && data.models.length > 0) {
          const pick = PREFERRED_MODELS.find((m) => data.models.includes(m)) ?? data.models[0];
          this.model.set(pick);
        }
      },
      error: (err) => {
        this.health.set({
          ollama_url: '',
          ollama_reachable: false,
          models: [],
          error: this.describeError(err),
        });
        this.lastError.set('Ollama nicht erreichbar: ' + this.describeError(err));
      },
    });
  }

  // ---- tool manipulation ---------------------------------------------

  toggleTool(name: ToolName, value: boolean): void {
    this.toolState.set({ ...this.toolState(), [name]: value });
    // Toggling the input sanitizer re-runs PDF extraction so the document panel
    // reflects whether invisibly-rendered text is dropped at the source - but
    // only for an unedited, freshly-extracted PDF (never clobber user edits).
    if (
      name === 'input_sanitizer' &&
      this.lastPdfB64 !== null &&
      this.documentText() === this.lastExtractedText
    ) {
      this.runExtract(this.lastPdfB64, this.fileName());
    }
  }

  // ---- pipeline trip --------------------------------------------------

  runOnce(): void {
    if (!this.model()) {
      this.lastError.set('Bitte zuerst ein Modell wählen.');
      return;
    }
    const payload: ChatRequestPayload = {
      model: this.model(),
      user_question: this.userQuestion(),
      document_text: this.documentText(),
      file_name: this.fileName() || 'dokument.pdf',
      tools: { ...this.toolState() },
      history: [],
      seed: this.seed(),
      num_predict: this.numPredict(),
      temperature: this.temperature(),
      top_p: this.topP(),
    };
    this.running.set(true);
    this.lastError.set(null);
    this.lastResponse.set(null);
    this.api.chat(payload, this.engine()).subscribe({
      next: (resp) => {
        this.lastResponse.set(resp);
        this.running.set(false);
      },
      error: (err) => {
        this.lastError.set(this.describeError(err));
        this.running.set(false);
      },
    });
  }

  /** Base64 of the last uploaded PDF, kept so toggling the input sanitizer can
   * re-extract the same file with/without the invisible-render drop. */
  private lastPdfB64: string | null = null;
  /** The text the last extraction produced - used to detect user edits so a
   * re-extract never overwrites them. */
  private lastExtractedText: string | null = null;

  extractPdf(file: File): void {
    const reader = new FileReader();
    reader.onload = () => {
      // ``readAsDataURL`` yields "data:<mime>;base64,<payload>" and leaves the
      // base64 encoding to the browser, so the bytes are never handled here and
      // there is no argument-count limit to chunk around. Everything up to and
      // including the first comma is the data-URL header; ``POST /api/extract``
      // wants the payload alone (it rejects anything base64 cannot decode).
      const dataUrl = typeof reader.result === 'string' ? reader.result : '';
      const payloadStart = dataUrl.indexOf(',') + 1;
      if (payloadStart === 0) {
        this.lastError.set('Die Datei konnte nicht gelesen werden.');
        return;
      }
      const b64 = dataUrl.slice(payloadStart);
      this.lastPdfB64 = b64;
      this.runExtract(b64, file.name);
    };
    reader.onerror = () => this.lastError.set('Die Datei konnte nicht gelesen werden.');
    reader.readAsDataURL(file);
  }

  /**
   * Run extraction for an already-encoded PDF. The current ``input_sanitizer``
   * toggle gates the invisible-render drop, so the document panel mirrors the
   * defense: off ⇒ the hidden payload is visible (unguarded baseline), on ⇒ the
   * invisibly-rendered runs are stripped at the source.
   */
  private runExtract(b64: string, fileName: string): void {
    this.api.extract(fileName, b64, this.toolState().input_sanitizer).subscribe({
      next: (resp) => {
        this.documentText.set(resp.text);
        this.fileName.set(resp.file_name);
        this.lastExtractedText = resp.text;
      },
      error: (err) =>
        this.lastError.set('PDF-Extraktion fehlgeschlagen: ' + this.describeError(err)),
    });
  }

  // ---- helpers --------------------------------------------------------

  /** Pull the most useful message out of an HttpErrorResponse-ish object. */
  private describeError(err: unknown): string {
    const e = err as { error?: { detail?: string }; message?: string };
    return e?.error?.detail ?? e?.message ?? String(err);
  }
}

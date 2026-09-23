// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2

/**
 * Typed mirror of the FastAPI backend contract
 * (``baseline_defense_lab.server.app`` + ``baseline_defense_lab.tools``).
 *
 * The defense surface is exactly FIVE tools (not a flag list). The five
 * tool keys, in canonical order, are:
 *   trust_separation, input_sanitizer, hardened_prompt, reasoning, egress_guard
 */

/**
 * Pipeline path discriminator. ``direct`` hits ``POST /api/chat``
 * (``DefensePipeline`` + native Ollama client); ``langchain`` hits
 * ``POST /api/chat_langchain`` (AgentMiddleware via ``create_agent``).
 * Both endpoints return the same response envelope - only
 * ``pipeline_metadata.engine`` differs. The LangChain path answers HTTP 501
 * when the ``[langchain]`` extra is not installed.
 */
export type Engine = 'direct' | 'langchain';

/** Canonical key of one of the five defense tools. */
export type ToolName =
  | 'trust_separation'
  | 'input_sanitizer'
  | 'hardened_prompt'
  | 'reasoning'
  | 'egress_guard';

/** The five per-tool boolean toggles (request + snapshot shape). */
export interface ToolsState {
  trust_separation: boolean;
  input_sanitizer: boolean;
  hardened_prompt: boolean;
  reasoning: boolean;
  egress_guard: boolean;
}

/** GET /api/healthz */
export interface HealthResponse {
  ollama_url: string;
  ollama_reachable: boolean;
  models: string[];
  error?: string;
}

/** One entry from GET /api/tools - was / warum / Grenze. */
export interface Tool {
  name: ToolName;
  title: string;
  stage: string;
  what: string;
  why: string;
  limit: string;
  /** Flat one-line description for tooltips ("… - Warum: … Grenze: …"). */
  description: string;
}

/** GET /api/tools */
export interface ToolsSchema {
  tools: Tool[];
}

/** GET /api/defaults - generation defaults (single source of truth). */
export interface GenerationDefaults {
  seed: number;
  num_predict: number;
  temperature: number;
  top_p: number;
}

/** POST /api/chat and POST /api/chat_langchain request body. */
export interface ChatRequestPayload {
  model: string;
  user_question: string;
  document_text: string;
  file_name: string;
  /**
   * The five tool toggles. ``null`` ⇒ backend treats every tool as off -
   * the truly naive baseline (plain concatenation, no structural wrap).
   */
  tools: ToolsState | null;
  history: ChatMessage[];
  seed: number;
  num_predict: number;
  temperature: number;
  top_p: number;
  num_ctx?: number;
}

/** One prior chat turn sent in the request `history` array. */
export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

/**
 * ``filter_metadata`` from the egress guard. Mirrors the backend
 * ``FilterResult`` dataclass plus the computed ``blocked`` property.
 * ``null`` when the egress_guard tool was off for the run.
 */
export interface FilterMetadata {
  canary_leak_detected: boolean;
  system_prompt_leak_detected: boolean;
  injection_marker_detected: boolean;
  compliance_indicator_detected: boolean;
  exfiltration_detected: boolean;
  external_markdown_removed: boolean;
  output_filtered: boolean;
  system_prompt_fragment_hits: number;
  verbatim_system_prompt_sentences: number;
  hierarchy_structure_hits: number;
  sandwich_reminder_hits: number;
  removed_external_references: number;
  findings: string[];
  /**
   * Hits found only in the chain-of-thought, never in the answer. Reported
   * for transparency, but they do not block: reasoning *about* an injection
   * is the model resisting it.
   */
  cot_only_findings: string[];
  blocked: boolean;
}

/** POST /api/chat[_langchain] response envelope. */
export interface ChatResponse {
  messages: ChatMessage[];
  canary_token: string | null;
  raw_text: string;
  visible_text: string;
  filter_metadata: FilterMetadata | null;
  tools_snapshot: ToolsState;
  pipeline_metadata: Record<string, string | number>;
  duration_ms: number;
  model_metadata: Record<string, string | number | boolean | null>;
  /** Server-authoritative footgun warnings (DefenseTools.dependency_warnings). */
  warnings: string[];
}

/** POST /api/extract response. */
export interface ExtractResponse {
  file_name: string;
  text: string;
  surface_lens: Record<string, number>;
  bytes: number;
}

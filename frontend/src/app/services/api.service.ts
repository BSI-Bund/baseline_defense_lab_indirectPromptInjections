// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  ChatRequestPayload,
  ChatResponse,
  Engine,
  ExtractResponse,
  GenerationDefaults,
  HealthResponse,
  ToolsSchema,
} from '../models/api-types';

/**
 * Thin, typed HTTP client for the FastAPI backend.
 *
 * The base path is relative (`/api/...`) so the same build works both behind
 * the FastAPI static-files mount in production and through the Angular
 * dev-server proxy during development.
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  /** GET /api/healthz - Ollama reachability + locally available models. */
  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>('/api/healthz');
  }

  /** GET /api/tools - the five defense tools with their descriptions. */
  tools(): Observable<ToolsSchema> {
    return this.http.get<ToolsSchema>('/api/tools');
  }

  /** GET /api/defaults - generation defaults (single source of truth). */
  defaults(): Observable<GenerationDefaults> {
    return this.http.get<GenerationDefaults>('/api/defaults');
  }

  /** GET /api/models - list of locally available Ollama models. */
  models(): Observable<{ models: string[] }> {
    return this.http.get<{ models: string[] }>('/api/models');
  }

  /** POST /api/extract - multi-surface text extraction from an uploaded PDF.
   *
   * ``inputSanitizer`` gates the invisible-render drop (text render mode 3/7 or
   * zero font size) at the source: off ⇒ faithful raw upload, on ⇒ hidden runs
   * removed during extraction.
   */
  extract(
    fileName: string,
    contentBase64: string,
    inputSanitizer = false,
  ): Observable<ExtractResponse> {
    return this.http.post<ExtractResponse>('/api/extract', {
      file_name: fileName,
      content_base64: contentBase64,
      input_sanitizer: inputSanitizer,
    });
  }

  /**
   * POST /api/chat or POST /api/chat_langchain depending on the engine.
   * Both endpoints share the request body and response envelope.
   */
  chat(payload: ChatRequestPayload, engine: Engine = 'direct'): Observable<ChatResponse> {
    const endpoint = engine === 'langchain' ? '/api/chat_langchain' : '/api/chat';
    return this.http.post<ChatResponse>(endpoint, payload);
  }
}

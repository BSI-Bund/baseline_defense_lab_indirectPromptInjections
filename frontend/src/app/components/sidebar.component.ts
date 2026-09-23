// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';

import { StateService } from '../services/state.service';
import { IconComponent } from './icon.component';

/**
 * Left control column: model picker, engine toggle, and the five
 * runtime-fetched defense-tool toggles plus the server-reported footgun
 * warning chip. The lab deliberately does NOT prescribe a recommended set - the
 * operator chooses the tools. Generation parameters (seed, num_predict,
 * temperature, top_p) are intentionally NOT exposed here: they are fixed to
 * generous, deterministic defaults on the server (``GENERATION_DEFAULTS``) so
 * the teaching focus stays on the tools, and reasoning-by-default models are
 * not truncated mid-think by a small budget.
 */
@Component({
  selector: 'bdl-sidebar',
  standalone: true,
  imports: [
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonToggleModule,
    MatSlideToggleModule,
    MatTooltipModule,
    IconComponent,
  ],
  template: `
    <mat-card class="bdl-card section">
      <header class="section-head">
        <bdl-icon name="tune" [size]="18"></bdl-icon>
        <span>Modell &amp; Engine</span>
      </header>

      <mat-form-field appearance="outline" class="full-width">
        <mat-label>Ollama-Modell</mat-label>
        <mat-select
          [ngModel]="state.model()"
          (ngModelChange)="state.model.set($event)"
          [disabled]="!state.models().length"
        >
          @for (m of state.models(); track m) {
            <mat-option [value]="m">{{ m }}</mat-option>
          }
        </mat-select>
      </mat-form-field>

      <div class="engine-toggle">
        <span
          class="engine-label"
          matTooltip="Direct = POST /api/chat (DefensePipeline, nativer Ollama-Client). LangChain = POST /api/chat_langchain (AgentMiddleware via create_agent). Identisches Antwortschema; nur pipeline_metadata.engine unterscheidet sich. Ohne [langchain]-Extra antwortet die LangChain-Route mit HTTP 501."
        >
          <bdl-icon name="engine" [size]="15"></bdl-icon>
          Engine
        </span>
        <mat-button-toggle-group
          class="engine-group"
          [value]="state.engine()"
          (change)="state.engine.set($event.value)"
          appearance="legacy"
          name="engine"
        >
          <mat-button-toggle value="direct">Direct</mat-button-toggle>
          <mat-button-toggle value="langchain">LangChain</mat-button-toggle>
        </mat-button-toggle-group>
      </div>
    </mat-card>

    <mat-card class="bdl-card section">
      <header class="section-head">
        <bdl-icon name="toggle" [size]="18"></bdl-icon>
        <span>Die 5 Werkzeuge</span>
        <span class="counter">{{ state.activeToolCount() }} / {{ state.totalToolCount() }} aktiv</span>
      </header>

      <p class="hint">
        Jedes Werkzeug ist ein einzelner Schalter. Halte den Mauszeiger darüber,
        um Was / Warum / Grenze zu sehen.
      </p>

      <div class="tool-list">
        @for (t of state.tools(); track t.name) {
          <label
            class="tool-row"
            [matTooltip]="t.what + ' - Warum: ' + t.why + ' Grenze: ' + t.limit"
            matTooltipClass="bdl-tip"
          >
            <mat-slide-toggle
              [checked]="state.toolState()[t.name]"
              (change)="state.toggleTool(t.name, $event.checked)"
              color="primary"
            ></mat-slide-toggle>
            <span class="tool-meta">
              <span class="tool-title">{{ t.title }}</span>
              <span class="tool-stage">{{ t.stage }} · {{ t.name }}</span>
            </span>
          </label>
        }
        @if (state.tools().length === 0) {
          <div class="empty">Werkzeug-Schema wird geladen …</div>
        }
      </div>

      @for (w of state.warnings(); track w) {
        <div class="footgun" role="alert">
          <bdl-icon name="warning" [size]="18"></bdl-icon>
          <span>{{ w }}</span>
        </div>
      }

      @if (state.toolState().reasoning) {
        <div class="reasoning-hint">
          <bdl-icon name="brain" [size]="16"></bdl-icon>
          <span>
            Reasoning wirkt nur bei Modellen, die Ollamas think-Kanal
            unterstützen (z. B. qwen3, deepseek-r1). Viele verbreitete
            Reasoning-Modelle lehnen ihn mit HTTP 400 ab; der Lauf wird dann
            <strong>ohne</strong> Reasoning ausgeführt und als „Reasoning:
            nicht unterstützt“ ausgewiesen. Das Werkzeug ist in diesem Fall
            wirkungslos - es schützt nichts.
          </span>
        </div>
      }
    </mat-card>
  `,
  styleUrls: ['./sidebar.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SidebarComponent {
  protected readonly state = inject(StateService);
}

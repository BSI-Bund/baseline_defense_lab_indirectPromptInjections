// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { MatTooltipModule } from '@angular/material/tooltip';

import { StateService } from '../services/state.service';
import { IconComponent } from './icon.component';

/**
 * Compact Ollama-status pill. The polling cadence (every 30 s) is driven by
 * the root {@link AppComponent}; this component only renders the latest
 * health snapshot from the {@link StateService}.
 */
@Component({
  selector: 'bdl-health-pill',
  standalone: true,
  imports: [MatTooltipModule, IconComponent],
  template: `
    <span
      class="pill"
      [class.pill-ok]="status() === 'ok'"
      [class.pill-err]="status() === 'err'"
      [class.pill-pending]="status() === 'pending'"
      [matTooltip]="tooltip()"
    >
      <span class="dot"></span>
      <bdl-icon name="server" [size]="15"></bdl-icon>
      <span class="label">{{ label() }}</span>
    </span>
  `,
  styles: [
    `
      .pill {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.3rem 0.75rem;
        border-radius: 999px;
        font-family: var(--bdl-sans);
        font-size: 0.78rem;
        font-weight: 600;
        border: 1px solid var(--bdl-border);
        background: var(--bdl-surface);
        color: var(--bdl-text-muted);
      }
      .pill .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: currentColor;
      }
      .pill-ok {
        color: var(--bdl-ok);
        border-color: rgba(46, 125, 50, 0.45);
        background: rgba(46, 125, 50, 0.08);
      }
      .pill-err {
        color: var(--bdl-danger);
        border-color: rgba(176, 0, 32, 0.45);
        background: rgba(176, 0, 32, 0.07);
      }
      .pill-pending {
        color: #8a6d00;
        border-color: rgba(230, 194, 0, 0.5);
        background: var(--bdl-warn-bg);
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HealthPillComponent {
  private readonly state = inject(StateService);

  readonly status = computed<'ok' | 'err' | 'pending'>(() => {
    const h = this.state.health();
    if (h === null) return 'pending';
    return h.ollama_reachable ? 'ok' : 'err';
  });

  readonly label = computed<string>(() => {
    const h = this.state.health();
    if (h === null) return 'Lade …';
    if (h.ollama_reachable) return `Ollama OK  ${h.models.length} Modelle`;
    return 'Ollama offline';
  });

  readonly tooltip = computed<string>(() => {
    const h = this.state.health();
    if (!h) return 'Status wird geladen';
    if (h.ollama_reachable) {
      return `Erreichbar via ${h.ollama_url}\nVerfügbare Modelle:\n${h.models.join('\n')}`;
    }
    return `Ollama nicht erreichbar: ${h.error ?? 'unbekannt'}`;
  });
}

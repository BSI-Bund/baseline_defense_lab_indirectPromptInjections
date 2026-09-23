// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';

import { StateService } from '../services/state.service';
import { IconComponent } from './icon.component';

/**
 * Right-hand result panel. Renders the metric chips driven by
 * ``filter_metadata``, a prominent "Egress-Guard blockiert" banner when the
 * guard blocked the turn, and seven tabs over the most recent run.
 */
@Component({
  selector: 'bdl-output-panel',
  standalone: true,
  imports: [MatCardModule, MatTabsModule, MatTooltipModule, IconComponent],
  template: `
    <mat-card class="bdl-card output-card">
      <header class="card-head">
        <bdl-icon name="output" [size]="18"></bdl-icon>
        <span>Pipeline-Ergebnis</span>

        @if (resp(); as r) {
          <div class="counters">
            @if (r.filter_metadata; as fm) {
              <span
                class="metric-chip"
                [class.danger]="fm.canary_leak_detected"
                [class.ok]="!fm.canary_leak_detected"
                matTooltip="Canary-Leak (enkodierungsbewusst) erkannt?"
              >
                <bdl-icon name="shield" [size]="14"></bdl-icon>
                Canary-Leak: {{ fm.canary_leak_detected ? 'ja' : 'nein' }}
              </span>

              <span
                class="metric-chip"
                [class.warn]="fm.verbatim_system_prompt_sentences > 0"
                matTooltip="F1a - verbatim übernommene System-Prompt-Sätze"
              >
                <bdl-icon name="quote" [size]="14"></bdl-icon>
                F1a {{ fm.verbatim_system_prompt_sentences }}
              </span>

              <span
                class="metric-chip"
                [class.warn]="fm.hierarchy_structure_hits > 0"
                matTooltip="F1c - Hierarchie-/Struktur-Marker"
              >
                <bdl-icon name="tree" [size]="14"></bdl-icon>
                F1c {{ fm.hierarchy_structure_hits }}
              </span>

              <span
                class="metric-chip"
                [class.warn]="fm.sandwich_reminder_hits > 0"
                matTooltip="F1d - Sandwich-Reminder-Marker"
              >
                <bdl-icon name="fence" [size]="14"></bdl-icon>
                F1d {{ fm.sandwich_reminder_hits }}
              </span>

              <span
                class="metric-chip"
                [class.danger]="fm.injection_marker_detected"
                matTooltip="Injection-/Compliance-Marker (PWNED, JAILBROKEN, …)"
              >
                <bdl-icon name="bug" [size]="14"></bdl-icon>
                Injection-Marker: {{ fm.injection_marker_detected ? 'ja' : 'nein' }}
              </span>

              <span
                class="metric-chip"
                [class.warn]="fm.removed_external_references > 0"
                matTooltip="Gestrippte / blockierte Exfil-URLs (removed_external_references)"
              >
                <bdl-icon name="link_off" [size]="14"></bdl-icon>
                Exfil-URLs {{ fm.removed_external_references }}
              </span>

              @if (fm.cot_only_findings.length > 0) {
                <span
                  class="metric-chip info"
                  [matTooltip]="cotOnlyTip()"
                >
                  <bdl-icon name="brain" [size]="14"></bdl-icon>
                  Nur im Gedankengang: {{ fm.cot_only_findings.length }}
                </span>
              }
            }

            @if (r.canary_token) {
              <span class="metric-chip info" matTooltip="Aktiver Session-Canary dieses Laufs">
                <bdl-icon name="shield" [size]="14"></bdl-icon>
                Canary {{ r.canary_token }}
              </span>
            }

            @if (reasoningStatus() !== 'off') {
              <span
                class="metric-chip"
                [class.ok]="reasoningStatus() === 'active'"
                [class.warn]="reasoningStatus() === 'unsupported'"
                [matTooltip]="reasoningTip()"
              >
                <bdl-icon name="brain" [size]="14"></bdl-icon>
                Reasoning: {{ reasoningStatus() === 'active' ? 'aktiv' : 'nicht unterstützt' }}
              </span>
            }
          </div>
        }
      </header>

      @if (!resp()) {
        <div class="empty">
          <bdl-icon name="play" [size]="34"></bdl-icon>
          <div>
            <strong>Noch kein Lauf.</strong>
            <p>Wähle ein Modell, lade ein Dokument und klicke <em>Pipeline ausführen</em>.</p>
          </div>
        </div>
      } @else {
        @if (resp()!.filter_metadata?.blocked) {
          <div class="blocked-banner" role="alert">
            <bdl-icon name="block" [size]="20"></bdl-icon>
            <div>
              <strong>Egress-Guard blockiert</strong>
              <span>
                Die Antwort wurde durch die Ausgangskontrolle ersetzt
                (Befunde: {{ findingsList() }}).
              </span>
            </div>
          </div>
        }

        <mat-tab-group animationDuration="150ms" mat-stretch-tabs="false">
          <mat-tab>
            <ng-template mat-tab-label>
              <bdl-icon name="eye" [size]="16"></bdl-icon>
              <span class="tab-text">Sichtbare Antwort</span>
            </ng-template>
            <pre class="pane">{{ resp()!.visible_text }}</pre>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <bdl-icon name="brain" [size]="16"></bdl-icon>
              <span class="tab-text">Gedankengang</span>
            </ng-template>
            <pre class="pane" [class.muted-pane]="!thinking()">{{ thinkingPane() }}</pre>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <bdl-icon name="code" [size]="16"></bdl-icon>
              <span class="tab-text">Rohantwort</span>
            </ng-template>
            <pre class="pane">{{ resp()!.raw_text }}</pre>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <bdl-icon name="policy" [size]="16"></bdl-icon>
              <span class="tab-text">System-Prompt</span>
            </ng-template>
            <pre class="pane">{{ systemMessage() }}</pre>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <bdl-icon name="person" [size]="16"></bdl-icon>
              <span class="tab-text">User-Turn</span>
            </ng-template>
            <pre class="pane">{{ userMessage() }}</pre>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <bdl-icon name="policy" [size]="16"></bdl-icon>
              <span class="tab-text">Filter-Metadaten</span>
            </ng-template>
            <pre class="pane">{{ filterJson() }}</pre>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <bdl-icon name="toggle" [size]="16"></bdl-icon>
              <span class="tab-text">Werkzeug-Snapshot</span>
            </ng-template>
            <pre class="pane">{{ snapshotJson() }}</pre>
          </mat-tab>
        </mat-tab-group>
      }
    </mat-card>
  `,
  styleUrls: ['./output-panel.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OutputPanelComponent {
  protected readonly state = inject(StateService);
  protected readonly resp = computed(() => this.state.lastResponse());

  protected readonly systemMessage = computed<string>(() => {
    const r = this.resp();
    if (!r) return '';
    const sys = r.messages.find((m) => m.role === 'system');
    return sys ? sys.content : '(kein System-Prompt)';
  });

  protected readonly userMessage = computed<string>(() => {
    const r = this.resp();
    if (!r) return '';
    const usr = r.messages.find((m) => m.role === 'user');
    return usr ? usr.content : '(kein User-Turn)';
  });

  protected readonly filterJson = computed<string>(() => {
    const r = this.resp();
    if (!r) return '';
    if (!r.filter_metadata) {
      return '(Egress-Guard ist in dieser Werkzeug-Kombination deaktiviert)';
    }
    return JSON.stringify(r.filter_metadata, null, 2);
  });

  protected readonly snapshotJson = computed<string>(() => {
    const r = this.resp();
    if (!r) return '';
    return JSON.stringify(
      {
        tools_snapshot: r.tools_snapshot,
        canary_token: r.canary_token,
        pipeline_metadata: r.pipeline_metadata,
        model_metadata: r.model_metadata,
        duration_ms: r.duration_ms,
      },
      null,
      2,
    );
  });

  protected readonly findingsList = computed<string>(() => {
    const fm = this.resp()?.filter_metadata;
    if (!fm || fm.findings.length === 0) return '–';
    return fm.findings.join(', ');
  });

  protected readonly cotOnlyTip = computed<string>(() => {
    const hits = this.resp()?.filter_metadata?.cot_only_findings ?? [];
    return (
      'Im Gedankengang gefunden, aber nicht in der Antwort - das Modell hat ' +
      'über die Injektion nachgedacht, ihr aber nicht gehorcht. Blockiert ' +
      `deshalb nicht. Befunde: ${hits.join(', ')}`
    );
  });

  // ---- reasoning (Tool 4) status + Gedankengang -----------------------

  /** Whether the reasoning tool was requested for this run. */
  private readonly reasoningRequested = computed<boolean>(
    () => this.resp()?.tools_snapshot?.reasoning === true,
  );

  /**
   * Whether reasoning was actually active. ``model_metadata.reasoning_active``
   * is ``false`` when a non-reasoning model (e.g. gemma3) rejected the think
   * channel and the pipeline gracefully degraded.
   */
  private readonly reasoningActive = computed<boolean>(
    () => this.resp()?.model_metadata?.['reasoning_active'] === true,
  );

  protected readonly reasoningStatus = computed<'off' | 'active' | 'unsupported'>(() => {
    if (!this.reasoningRequested()) return 'off';
    return this.reasoningActive() ? 'active' : 'unsupported';
  });

  protected readonly reasoningTip = computed<string>(() =>
    this.reasoningStatus() === 'active'
      ? 'Das Modell hat einen Gedankengang erzeugt - siehe Tab „Gedankengang“.'
      : 'Reasoning war angefordert, aber dieses Modell unterstützt Ollamas ' +
        'think-Kanal nicht. Der Lauf wurde ohne Reasoning ausgeführt ' +
        '(reasoning_active=false) - Werkzeug 4 war also nicht wirksam. Nutze ein ' +
        'Modell mit think-Unterstützung, z. B. qwen3.',
  );

  /** The merged surface is ``=== Gedankengang === … === Antwort === …``. */
  protected readonly thinking = computed<string>(() => {
    const t = this.resp()?.visible_text ?? '';
    const HEAD = '=== Gedankengang ===';
    const SPLIT = '=== Antwort ===';
    if (!t.startsWith(HEAD)) return '';
    const end = t.indexOf(SPLIT);
    const body = end >= 0 ? t.slice(HEAD.length, end) : t.slice(HEAD.length);
    return body.trim();
  });

  protected readonly thinkingPane = computed<string>(() => {
    const got = this.thinking();
    if (got) return got;
    switch (this.reasoningStatus()) {
      case 'off':
        return '(Reasoning ist in dieser Werkzeug-Kombination ausgeschaltet.)';
      case 'unsupported':
        return (
          '(Das gewählte Modell unterstützt kein Thinking - die Pipeline lief ohne ' +
          'Reasoning. Wähle ein reasoning-fähiges Modell wie qwen3, ' +
          'um den Gedankengang zu sehen.)'
        );
      default:
        return '(Kein separater Gedankengang in dieser Antwort.)';
    }
  });
}

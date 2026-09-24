// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2
import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  OnInit,
  effect,
  inject,
} from '@angular/core';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { DISCLAIMER } from './disclaimer';
import { StateService } from './services/state.service';
import { SidebarComponent } from './components/sidebar.component';
import { WorkspaceComponent } from './components/workspace.component';
import { OutputPanelComponent } from './components/output-panel.component';
import { HealthPillComponent } from './components/health-pill.component';

@Component({
  selector: 'bdl-app',
  standalone: true,
  imports: [
    MatSnackBarModule,
    SidebarComponent,
    WorkspaceComponent,
    OutputPanelComponent,
    HealthPillComponent,
  ],
  template: `
    <!-- Header band -------------------------------------------------------- -->
    <header class="header-band">
      <div class="header-inner">
        <div class="header-right">
          <bdl-health-pill></bdl-health-pill>
        </div>
      </div>
    </header>

    <!-- Hero banner --------------------------------------------------------- -->
    <section class="hero" id="labor">
      <div class="hero-inner">
        <div class="hero-card">
          <h1>Baseline-Defense-Lab - Interaktive Lehr- und Test-Umgebung</h1>
          <p>
            Wie man LLM-Basisschutzmaßnahmen gegen indirekte Prompt-Injection implementiert
          </p>
        </div>
      </div>
    </section>

    <!-- 6. Content ---------------------------------------------------------- -->
    <main class="layout" id="werkzeuge">
      <aside class="layout-sidebar">
        <bdl-sidebar></bdl-sidebar>
      </aside>
      <section class="layout-main">
        <bdl-workspace></bdl-workspace>
        <bdl-output-panel></bdl-output-panel>
      </section>
    </main>

    <footer class="app-footer">
      <div class="footer-inner">
        <!--
          Disclaimer. Text lives in ./disclaimer.ts - edit it there, not here.
          An empty "paragraphs" array drops it entirely.
        -->
        @if (disclaimer.paragraphs.length > 0) {
          <section class="footer-disclaimer" role="note" aria-labelledby="disclaimer-title">
            <strong id="disclaimer-title">{{ disclaimer.title }}</strong>
            @for (p of disclaimer.paragraphs; track p) {
              <p>{{ p }}</p>
            }
          </section>
        }

        <span class="footer-meta"><strong>Baseline-Defense-Lab</strong> · EUPL-1.2</span>
      </div>
    </footer>
  `,
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
/**
 * Root shell component. Composes the header (health pill), the sidebar,
 * workspace and output panel, and the footer carrying the disclaimer;
 * surfaces state errors as a snackbar; and polls `/api/healthz` every
 * 30 seconds.
 */
export class AppComponent implements OnInit, OnDestroy {
  protected readonly disclaimer = DISCLAIMER;

  private readonly state = inject(StateService);
  private readonly snack = inject(MatSnackBar);
  private healthTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    // Surface backend errors as a snackbar message.
    effect(() => {
      const err = this.state.lastError();
      if (err) {
        this.snack.open(err, 'OK', { duration: 6000, panelClass: ['snack-error'] });
      }
    });
  }

  ngOnInit(): void {
    this.state.initialise();
    // Health pill polls every 30 s.
    this.healthTimer = setInterval(() => this.state.refreshHealth(), 30_000);
  }

  ngOnDestroy(): void {
    if (this.healthTimer) clearInterval(this.healthTimer);
  }
}

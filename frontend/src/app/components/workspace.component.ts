// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2
import { ChangeDetectionStrategy, Component, ElementRef, inject, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { StateService } from '../services/state.service';
import { IconComponent } from './icon.component';

/**
 * Centre column: the untrusted document (PDF upload via /api/extract or a
 * free-text editor), the user question, and the run control with the
 * duration / block indicator.
 */
@Component({
  selector: 'bdl-workspace',
  standalone: true,
  imports: [
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressBarModule,
    MatTooltipModule,
    IconComponent,
  ],
  template: `
    <mat-card class="bdl-card">
      <header class="card-head">
        <bdl-icon name="document" [size]="18"></bdl-icon>
        <span>Untrusted-Dokument</span>
        <span class="status-chip" [class.has-doc]="hasDocument()">
          {{ hasDocument() ? state.fileName() : 'Kein Dokument' }}
        </span>
      </header>

      <p class="card-hint">
        Der Dokumentinhalt ist die <strong>nicht vertrauenswürdige</strong> Quelle -
        hier wird die indirekte Prompt-Injection platziert.
      </p>

      <div class="upload-row">
        <button mat-stroked-button type="button" class="action" (click)="openFileDialog()">
          <bdl-icon name="upload" [size]="17"></bdl-icon>
          PDF hochladen
        </button>
        <button
          mat-button
          type="button"
          class="action"
          (click)="state.documentText.set('')"
          [disabled]="!hasDocument()"
        >
          <bdl-icon name="trash" [size]="17"></bdl-icon>
          Leeren
        </button>
        <input #fileInput type="file" accept=".pdf" hidden (change)="onFile($event)" />
      </div>

      <mat-form-field appearance="outline" class="full-width">
        <mat-label>Dokumentinhalt (editierbar)</mat-label>
        <textarea
          matInput
          rows="8"
          spellcheck="false"
          [ngModel]="state.documentText()"
          (ngModelChange)="state.documentText.set($event)"
        ></textarea>
      </mat-form-field>

      <mat-form-field appearance="outline" class="full-width">
        <mat-label>Dateiname (erscheint im Wrap, wenn Vertrauenstrennung aktiv ist)</mat-label>
        <input matInput [ngModel]="state.fileName()" (ngModelChange)="state.fileName.set($event)" />
      </mat-form-field>
    </mat-card>

    <mat-card class="bdl-card">
      <header class="card-head">
        <bdl-icon name="chat" [size]="18"></bdl-icon>
        <span>Nutzerfrage</span>
      </header>

      <mat-form-field appearance="outline" class="full-width">
        <mat-label>Was soll das Modell tun?</mat-label>
        <textarea
          matInput
          rows="3"
          [ngModel]="state.userQuestion()"
          (ngModelChange)="state.userQuestion.set($event)"
        ></textarea>
      </mat-form-field>

      <div class="run-row">
        <button
          mat-flat-button
          class="run-btn"
          (click)="state.runOnce()"
          [disabled]="state.running()"
        >
          @if (state.running()) {
            <bdl-icon name="spinner" [size]="18" [spin]="true"></bdl-icon>
            <span>Läuft …</span>
          } @else {
            <bdl-icon name="play" [size]="18"></bdl-icon>
            <span>Pipeline ausführen</span>
          }
        </button>

        @if (state.lastResponse(); as resp) {
          <span class="run-stats">
            <bdl-icon name="clock" [size]="15"></bdl-icon>
            {{ resp.duration_ms }} ms
            @if (resp.filter_metadata?.blocked) {
              <span class="blocked-tag">
                <bdl-icon name="block" [size]="14"></bdl-icon>
                Egress-Guard blockiert
              </span>
            }
          </span>
        }
      </div>

      @if (state.running()) {
        <mat-progress-bar mode="indeterminate"></mat-progress-bar>
      }
    </mat-card>
  `,
  styleUrls: ['./workspace.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceComponent {
  protected readonly state = inject(StateService);
  protected readonly fileInput = viewChild.required<ElementRef<HTMLInputElement>>('fileInput');

  /** Decoded-size limit mirroring the backend's 25-MiB extract cap. */
  private static readonly MAX_PDF_BYTES = 25 * 1024 * 1024;

  protected hasDocument(): boolean {
    return this.state.documentText().trim().length > 0;
  }

  /** Programmatically open the hidden file input. */
  protected openFileDialog(): void {
    this.fileInput().nativeElement.click();
  }

  protected onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      if (file.size > WorkspaceComponent.MAX_PDF_BYTES) {
        this.state.lastError.set(
          `Die Datei ist ${(file.size / 1024 / 1024).toFixed(1)} MB groß - ` +
            'das Upload-Limit liegt bei 25 MB.',
        );
      } else if (!file.name.toLowerCase().endsWith('.pdf')) {
        this.state.lastError.set('Bitte eine PDF-Datei auswählen.');
      } else {
        this.state.extractPdf(file);
      }
    }
    input.value = '';
  }
}

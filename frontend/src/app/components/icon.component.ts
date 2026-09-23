// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2
import {
  ChangeDetectionStrategy,
  Component,
  Input,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

/**
 * Tiny inline-SVG icon set.
 *
 * The reference UI used Angular Material's ``<mat-icon>``, which depends on a
 * remote ligature font (Material Icons). This project must build and run
 * fully offline (no remote/proprietary fonts), so we ship a handful of
 * inline-SVG glyphs instead. Each path is drawn on a 24×24 viewBox with
 * ``currentColor`` strokes so callers control colour via CSS ``color``.
 *
 * The markup is a fixed, code-local string set (never user input); it is
 * passed through ``bypassSecurityTrustHtml`` so the inline SVG renders.
 */
const ICON_BODIES: Record<string, string> = {
  shield:
    '<path d="M12 3l7 2.5V11c0 4.7-3.1 7.6-7 9-3.9-1.4-7-4.3-7-9V5.5z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>',
  tune:
    '<path d="M4 7h9M17 7h3M4 12h3M11 12h9M4 17h6M14 17h6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><circle cx="15" cy="7" r="2" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="9" cy="12" r="2" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="17" r="2" fill="none" stroke="currentColor" stroke-width="1.7"/>',
  toggle:
    '<rect x="3" y="8" width="18" height="8" rx="4" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="15" cy="12" r="2.4" fill="currentColor"/>',
  document:
    '<path d="M7 3h7l4 4v14H7z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M14 3v4h4M9 12h7M9 16h7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  chat:
    '<path d="M4 5h16v11H9l-4 3v-3H4z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>',
  output:
    '<rect x="5" y="4" width="14" height="16" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M8 9h8M8 13h8M8 17h5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  play: '<path d="M8 5l11 7-11 7z" fill="currentColor"/>',
  upload:
    '<path d="M12 16V5M8 9l4-4 4 4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 19h14" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  trash:
    '<path d="M5 7h14M9 7V5h6v2M7 7l1 13h8l1-13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  clock:
    '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M12 8v4l3 2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  block:
    '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M6.5 6.5l11 11" fill="none" stroke="currentColor" stroke-width="1.7"/>',
  warning:
    '<path d="M12 4l9 16H3z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M12 10v4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><circle cx="12" cy="17" r="1" fill="currentColor"/>',
  check:
    '<path d="M5 12l4 4 10-11" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>',
  recommend:
    '<path d="M9 11l3-7c1.6 0 2.6 1.2 2.3 2.8L13.8 10H19a2 2 0 012 2.3l-1 6A2 2 0 0118 20H9z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><rect x="4" y="11" width="4" height="9" rx="1" fill="none" stroke="currentColor" stroke-width="1.6"/>',
  engine:
    '<rect x="4" y="4" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/><rect x="14" y="14" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M10 7h4a3 3 0 013 3v4" fill="none" stroke="currentColor" stroke-width="1.7"/>',
  brain:
    '<path d="M11 5a2.5 2.5 0 00-4.6 1.2A2.5 2.5 0 005 11a2.5 2.5 0 001.5 4.3A2.3 2.3 0 0011 18z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M13 5a2.5 2.5 0 014.6 1.2A2.5 2.5 0 0119 11a2.5 2.5 0 01-1.5 4.3A2.3 2.3 0 0113 18z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M11 5v13M13 5v13" fill="none" stroke="currentColor" stroke-width="1.5"/>',
  spinner:
    '<path d="M12 4a8 8 0 018 8" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
  server:
    '<rect x="4" y="4" width="16" height="6" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.7"/><rect x="4" y="14" width="16" height="6" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="8" cy="7" r="0.9" fill="currentColor"/><circle cx="8" cy="17" r="0.9" fill="currentColor"/>',
  quote:
    '<path d="M9 7H5v5h4l-2 4M19 7h-4v5h4l-2 4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  tree:
    '<rect x="9" y="3" width="6" height="4" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/><rect x="3" y="14" width="6" height="4" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/><rect x="15" y="14" width="6" height="4" rx="1" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M12 7v3M6 14v-2h12v2" fill="none" stroke="currentColor" stroke-width="1.7"/>',
  fence:
    '<path d="M5 4v16M9 4v16M13 4v16M17 4v16M3 9h16M3 14h16" fill="none" stroke="currentColor" stroke-width="1.5"/>',
  link_off:
    '<path d="M9 12h6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M8 8H6a4 4 0 000 8h2M16 8h2a4 4 0 014 4 4 4 0 01-1.2 2.8" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M4 4l16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  bug:
    '<rect x="8" y="8" width="8" height="9" rx="4" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M9 6l2 2M15 6l-2 2M5 11h3M16 11h3M5 16h3M16 16h3M12 17v3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  person:
    '<circle cx="12" cy="8" r="3.2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M5 20a7 7 0 0114 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  eye:
    '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="12" r="2.6" fill="none" stroke="currentColor" stroke-width="1.7"/>',
  code:
    '<path d="M9 7l-5 5 5 5M15 7l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  policy:
    '<path d="M12 3l7 2.5V11c0 4.7-3.1 7.6-7 9-3.9-1.4-7-4.3-7-9V5.5z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M9 11l2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
  external:
    '<path d="M14 5h5v5M19 5l-7 7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M18 13v5a1 1 0 01-1 1H6a1 1 0 01-1-1V7a1 1 0 011-1h5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
};

@Component({
  selector: 'bdl-icon',
  standalone: true,
  template: `
    <span
      class="bdl-icon-wrap"
      [class.spin]="spin"
      [style.width.px]="dim()"
      [style.height.px]="dim()"
      [innerHTML]="svg()"
      aria-hidden="true"
    ></span>
  `,
  styles: [
    `
      :host {
        display: inline-flex;
        line-height: 0;
        color: inherit;
      }
      .bdl-icon-wrap {
        display: inline-flex;
      }
      .bdl-icon-wrap ::ng-deep svg {
        display: block;
        width: 100%;
        height: 100%;
      }
      .spin {
        animation: bdl-icon-spin 1s linear infinite;
        transform-origin: 50% 50%;
      }
      @keyframes bdl-icon-spin {
        to {
          transform: rotate(360deg);
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IconComponent {
  private readonly sanitizer = inject(DomSanitizer);

  private readonly nameSig = signal<string>('shield');
  private readonly sizeSig = signal<number>(20);

  @Input({ required: true })
  set name(value: string) {
    this.nameSig.set(value);
  }

  @Input()
  set size(value: number) {
    this.sizeSig.set(value);
  }

  /** Decorative spin (e.g. a loading indicator). */
  @Input() spin = false;

  protected readonly dim = computed<number>(() => this.sizeSig());

  protected readonly svg = computed<SafeHtml>(() => {
    const body = ICON_BODIES[this.nameSig()] ?? ICON_BODIES['shield'];
    return this.sanitizer.bypassSecurityTrustHtml(
      `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">${body}</svg>`,
    );
  });
}

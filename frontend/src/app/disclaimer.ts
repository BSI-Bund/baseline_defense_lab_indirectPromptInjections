// SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
// SPDX-License-Identifier: EUPL-1.2

/**
 * Der in der Anwendung angezeigte Disclaimer.
 *
 * Dies ist die einzige Stelle, an der der Disclaimer-Text steht: Titel und
 * Absätze hier überschreiben, sonst nichts anfassen. Die Darstellung (Footer)
 * liegt in ``app.component.ts`` / ``app.component.scss``.
 *
 * Die Absätze werden als reiner Text gerendert - kein HTML, keine Links. Wird
 * ``DISCLAIMER.paragraphs`` auf ein leeres Array gesetzt, verschwindet der
 * Hinweis vollständig.
 */
export const DISCLAIMER: { readonly title: string; readonly paragraphs: readonly string[] } = {
  title: 'Hinweis zum Schutzumfang',

  paragraphs: [
    'Diese Anwendung bietet einen Basisschutz gegen Indirect Prompt Injections ' +
      'in dokumentbasierten LLM-Chats. Die fünf Maßnahmen reduzieren das Risiko ' +
      'solcher Angriffe, bieten jedoch keinen vollständigen Schutz. Nach ' +
      'derzeitigem Stand der Technik lassen sich Indirect Prompt Injections ' +
      'nicht abschließend verhindern.',

    'Die Maßnahmen ersetzen weder ein anwendungsspezifisches Red Teaming noch ' +
      'eine individuelle Sicherheitsbewertung. Sie dienen zur Sensibilisierung ' +
      'und als Fundament, auf dem weitere, an den konkreten Einsatzzweck ' +
      'angepasste Schutzmaßnahmen ansetzen können.',

    'Für Vollständigkeit, Richtigkeit und Wirksamkeit im Einzelfall wird keine ' +
      'Gewähr übernommen.',
  ],
};

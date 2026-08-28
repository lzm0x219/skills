"""Static print styles for the China Commerce Asset Pack PDF report."""

from __future__ import annotations


FONT_STACK = (
    'system-ui, -apple-system, BlinkMacSystemFont, "Noto Sans CJK SC", '
    '"Source Han Sans SC", "PingFang SC", "Hiragino Sans GB", '
    '"Microsoft YaHei", "Droid Sans Fallback", sans-serif'
)


CSS_TEMPLATE = r"""
:root {
    --color-page: #FFFFFF;
    --color-ink: #111111;
    --color-text-body: #2C2C2E;
    --color-text-secondary: #48484A;
    --color-text-muted: #636366;
    --color-surface: #F5F5F7;
    --color-surface-cool: #EDF2F4;
    --color-border: #D1D1D6;
    --color-border-strong: #8E8E93;
    --space-1: 2mm;
    --space-2: 4mm;
    --space-3: 6mm;
    --space-4: 10mm;
    --space-5: 16mm;
    --space-6: 24mm;
    --type-caption: 8.6pt;
    --type-source: 9.2pt;
    --type-body: 10.8pt;
    --type-h3: 12pt;
    --type-h2: 16pt;
    --type-h1: 30pt;
    --type-display: 42pt;
}

/* Paged-media margin boxes do not reliably inherit custom properties. */
@page {
    size: A4;
    margin: 25mm 21mm 22mm 21mm;
    background: #FFFFFF;

    @top-left {
        content: "HEADER_TEXT";
        padding-bottom: 3mm;
        color: #636366;
        font-family: FONT_STACK;
        font-size: 8.6pt;
        font-weight: 450;
    }

    @top-right {
        content: "DECISION REPORT";
        padding-bottom: 3mm;
        color: #636366;
        font-family: FONT_STACK;
        font-size: 8.6pt;
        font-weight: 650;
        letter-spacing: 1.2pt;
    }

    @bottom-left {
        content: "SELL PRODUCT IN CHINA";
        padding-top: 2.6mm;
        border-top: 0.5pt solid #D1D1D6;
        color: #636366;
        font-family: FONT_STACK;
        font-size: 8.6pt;
        font-weight: 600;
        letter-spacing: 0.9pt;
    }

    @bottom-right {
        content: counter(page, decimal-leading-zero);
        padding-top: 2.6mm;
        border-top: 0.5pt solid #D1D1D6;
        color: #111111;
        font-family: FONT_STACK;
        font-size: 8.6pt;
        font-weight: 650;
    }
}

@page :first {
    @top-left { content: none; }
    @top-right { content: none; }
    @bottom-left { content: none; }
    @bottom-right { content: none; }
}

html,
body {
    background: var(--color-page);
}

html {
    color: var(--color-ink);
    font-family: FONT_STACK;
}

body {
    margin: 0;
    color: var(--color-text-body);
    font-family: FONT_STACK;
    font-size: var(--type-body);
    font-variant-numeric: tabular-nums;
    line-height: 1.8;
    text-align: left;
    -webkit-font-smoothing: antialiased;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

.page-kicker,
.cover-eyebrow,
.guide-label {
    color: var(--color-text-muted);
    font-family: FONT_STACK;
    font-size: var(--type-caption);
    font-weight: 650;
    letter-spacing: 1.5pt;
    line-height: 1.4;
    text-transform: uppercase;
}

.cover {
    position: relative;
    min-height: 238mm;
    overflow: hidden;
    page-break-after: always;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    padding-left: 22mm;
}

.cover::before {
    position: absolute;
    top: -25mm;
    bottom: -22mm;
    left: 0;
    width: 12mm;
    background: var(--color-ink);
    content: "";
}

.cover::after {
    position: absolute;
    top: 0;
    right: 0;
    width: 32mm;
    border-top: 1.2pt solid var(--color-ink);
    content: "";
}

.cover-eyebrow {
    margin-top: 3mm;
}

.cover .cover-title {
    max-width: 126mm;
    margin: 43mm 0 0;
    padding: 0;
    border: 0;
    color: var(--color-ink);
    font-size: var(--type-display);
    font-weight: 650;
    letter-spacing: -1.1pt;
    line-height: 1.18;
    page-break-before: avoid;
    page-break-after: avoid;
}

.cover-subtitle {
    max-width: 112mm;
    margin-top: 8mm;
    color: var(--color-text-secondary);
    font-size: 13pt;
    font-weight: 450;
    line-height: 1.58;
}

.cover-divider {
    width: 28mm;
    margin: 15mm 0 0;
    border: 0;
    border-top: 1pt solid var(--color-ink);
}

.cover-meta {
    width: 124mm;
    margin-top: auto;
    padding-top: 5mm;
    border-top: 0.7pt solid var(--color-ink);
    color: var(--color-text-body);
    font-size: var(--type-source);
    line-height: 1.58;
}

.cover-meta-row {
    display: grid;
    grid-template-columns: 29mm 1fr;
    column-gap: 5mm;
    margin: 1.6mm 0;
}

.cover-meta-label {
    color: var(--color-text-muted);
}

.cover-footer {
    margin: 7mm 0 1mm;
    color: var(--color-text-muted);
    font-size: var(--type-caption);
    letter-spacing: 0.25pt;
}

.reading-guide {
    position: relative;
    min-height: 215mm;
    padding: 9mm 0 0 22mm;
    page-break-after: always;
    box-sizing: border-box;
}

.reading-guide::before {
    position: absolute;
    top: 9mm;
    bottom: 0;
    left: 0;
    width: 12mm;
    background: var(--color-ink);
    content: "";
}

.reading-guide h1 {
    max-width: 112mm;
    margin: 8mm 0 6mm;
    padding: 0;
    border: 0;
    color: var(--color-ink);
    font-size: 34pt;
    font-weight: 650;
    letter-spacing: -0.8pt;
    line-height: 1.18;
    page-break-before: avoid;
}

.guide-note {
    max-width: 116mm;
    margin: 0 0 10mm;
    color: var(--color-text-secondary);
    font-size: 11.2pt;
    line-height: 1.72;
}

.guide-axis {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 5mm;
    margin: 0 0 11mm;
    padding: 4mm 0;
    border-top: 0.6pt solid var(--color-border);
    border-bottom: 0.6pt solid var(--color-border);
    color: var(--color-text-muted);
    font-size: var(--type-caption);
    font-weight: 650;
    letter-spacing: 0.8pt;
}

.guide-axis > div::before {
    display: block;
    margin-bottom: 1mm;
    color: var(--color-ink);
    font-size: 10.5pt;
    font-weight: 650;
    letter-spacing: 0;
}

.guide-axis > div:nth-child(1)::before { content: "判断"; }
.guide-axis > div:nth-child(2)::before { content: "证据"; }
.guide-axis > div:nth-child(3)::before { content: "行动"; }

.toc {
    margin: 0;
    padding: 0;
    list-style: none;
    counter-reset: guide-item;
}

.toc li {
    min-height: 10mm;
    margin: 0;
    padding: 2.2mm 0 2mm;
    border-top: 0.7pt solid var(--color-border);
    display: grid;
    grid-template-columns: 13mm 1fr;
    column-gap: 4mm;
    counter-increment: guide-item;
    break-inside: avoid;
}

.toc li:last-child {
    border-bottom: 0.7pt solid var(--color-border);
}

.toc li::before {
    padding-top: 0.6mm;
    color: var(--color-text-muted);
    content: counter(guide-item, decimal-leading-zero);
    font-size: var(--type-caption);
    font-weight: 650;
}

.toc a {
    color: var(--color-ink);
    font-size: 11.8pt;
    font-weight: 600;
    line-height: 1.45;
    text-decoration: none;
}

.report-body {
    counter-reset: report-chapter;
}

.executive-summary {
    position: relative;
    min-height: 212mm;
    padding: 8mm 0 0 18mm;
    page-break-after: always;
    box-sizing: border-box;
}

.executive-summary::before {
    position: absolute;
    top: 8mm;
    bottom: 0;
    left: 0;
    width: 2mm;
    background: var(--color-ink);
    content: "";
}

.executive-summary > h2:first-child {
    max-width: 122mm;
    margin: 0 0 8mm;
    padding: 0;
    color: var(--color-ink);
    font-size: 32pt;
    font-weight: 650;
    letter-spacing: -0.8pt;
    line-height: 1.2;
}

.executive-summary > h2:first-child::before {
    display: block;
    margin-bottom: 5mm;
    color: var(--color-text-muted);
    content: "EXECUTIVE SUMMARY";
    font-size: var(--type-caption);
    font-weight: 650;
    letter-spacing: 1.5pt;
}

.executive-summary > p:first-of-type {
    max-width: 135mm;
    margin: 0 0 9mm;
    color: var(--color-ink);
    font-size: 13.6pt;
    font-weight: 500;
    line-height: 1.68;
}

.executive-summary table {
    margin: 0 0 8mm;
    background: var(--color-surface-cool);
}

.executive-summary thead th,
.executive-summary tbody td {
    padding-right: 3.6mm;
    padding-left: 3.6mm;
}

.report-body > h1 {
    margin: 0 0 11mm;
    padding: 6mm 0 0;
    border-top: 1pt solid var(--color-ink);
    color: var(--color-ink);
    counter-increment: report-chapter;
    font-size: var(--type-h1);
    font-weight: 650;
    letter-spacing: -0.7pt;
    line-height: 1.2;
    page-break-before: always;
    break-after: avoid;
}

.report-body > h1::before {
    display: block;
    margin-bottom: 4mm;
    color: var(--color-text-muted);
    content: "EVIDENCE / " counter(report-chapter, decimal-leading-zero);
    font-size: var(--type-caption);
    font-weight: 650;
    letter-spacing: 1.3pt;
}

h2,
h3,
h4 {
    color: var(--color-ink);
    text-align: left;
    break-after: avoid;
}

h2 {
    margin: 11mm 0 4mm;
    padding-top: 4mm;
    border-top: 0.6pt solid var(--color-border);
    font-size: var(--type-h2);
    font-weight: 650;
    letter-spacing: -0.2pt;
    line-height: 1.4;
}

h3 {
    margin: 7mm 0 2.5mm;
    font-size: var(--type-h3);
    font-weight: 650;
    line-height: 1.5;
}

h4 {
    margin: 5mm 0 2mm;
    font-size: 10.8pt;
    font-weight: 650;
    line-height: 1.55;
}

p {
    margin: 0 0 3.6mm;
    color: var(--color-text-body);
    orphans: 3;
    widows: 3;
}

strong,
b {
    color: var(--color-ink);
    font-weight: 680;
}

blockquote {
    margin: 7mm 0;
    padding: 6mm 7mm;
    border: 0;
    background: var(--color-surface);
    box-shadow: inset 1.4pt 0 0 var(--color-ink);
    color: var(--color-text-body);
    font-size: 10.6pt;
    line-height: 1.75;
    break-inside: avoid;
}

blockquote p {
    margin: 1.4mm 0;
}

blockquote h1 {
    margin: 0 0 3mm;
    padding: 0;
    border: 0;
    color: var(--color-ink);
    font-size: 14pt;
    font-weight: 650;
    line-height: 1.45;
    page-break-before: avoid;
}

ul,
ol {
    margin: 3mm 0 5mm;
    padding-left: 7mm;
}

li {
    margin: 0 0 2mm;
    padding-left: 1mm;
    color: var(--color-text-body);
    line-height: 1.7;
}

li::marker {
    color: var(--color-text-secondary);
}

hr {
    margin: 8mm 0;
    border: 0;
    border-top: 0.5pt solid var(--color-border);
}

table {
    width: 100%;
    margin: 5mm 0 8mm;
    border-collapse: collapse;
    table-layout: auto;
    background: transparent;
    font-size: var(--type-source);
    font-variant-numeric: tabular-nums;
    text-align: left;
}

thead {
    display: table-header-group;
}

tr {
    break-inside: avoid;
}

thead th {
    padding: 3mm 2.6mm;
    border-top: 1pt solid var(--color-ink);
    border-bottom: 0.6pt solid var(--color-border-strong);
    color: var(--color-ink);
    font-size: var(--type-caption);
    font-weight: 680;
    line-height: 1.42;
    vertical-align: bottom;
    overflow-wrap: anywhere;
    word-break: break-word;
}

tbody td {
    padding: 3.1mm 2.6mm;
    border-bottom: 0.5pt solid var(--color-border);
    color: var(--color-text-body);
    line-height: 1.5;
    vertical-align: top;
    overflow-wrap: anywhere;
    word-break: break-word;
}

tbody tr:last-child td {
    border-bottom: 0.8pt solid var(--color-border-strong);
}

table.cols-5 {
    font-size: 8.8pt;
    table-layout: fixed;
}

table.cols-6,
table.cols-7,
table.cols-8 {
    font-size: 8.6pt;
    table-layout: fixed;
}

table.cols-5 th,
table.cols-5 td,
table.cols-6 th,
table.cols-6 td,
table.cols-7 th,
table.cols-7 td,
table.cols-8 th,
table.cols-8 td {
    padding: 2.4mm 1.8mm;
    line-height: 1.42;
}

img {
    display: block;
    max-width: 100%;
    height: auto;
    border-radius: 3mm;
}

p > img:only-child {
    margin: 6mm auto 8mm;
}

figure {
    margin: 7mm 0 9mm;
    break-inside: avoid;
}

figcaption {
    margin-top: 2.5mm;
    color: var(--color-text-muted);
    font-size: var(--type-caption);
    line-height: 1.55;
}

code {
    padding: 0.5mm 1.2mm;
    border-radius: 2pt;
    background: var(--color-surface);
    color: var(--color-text-body);
    font-family: ui-monospace, "Noto Sans Mono", Menlo, Monaco, Consolas, monospace;
    font-size: var(--type-source);
}

pre {
    margin: 5mm 0;
    padding: 5mm;
    border-radius: 2mm;
    background: var(--color-surface);
    color: var(--color-text-body);
    font-family: ui-monospace, "Noto Sans Mono", Menlo, Monaco, Consolas, monospace;
    font-size: var(--type-caption);
    line-height: 1.62;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

pre code {
    padding: 0;
    background: transparent;
}

a {
    color: var(--color-ink);
    text-decoration-color: var(--color-border-strong);
    text-underline-offset: 1.5pt;
    overflow-wrap: anywhere;
}

.final-decision {
    min-height: 211mm;
    display: grid;
    grid-template-columns: 48mm 1fr;
    column-gap: 13mm;
    page-break-before: always;
    box-sizing: border-box;
}

.final-decision-header {
    min-height: 188mm;
    padding: 13mm 8mm;
    background: var(--color-ink);
    color: #FFFFFF;
    box-sizing: border-box;
}

.final-decision-header .page-kicker {
    color: #C7C7CC;
    letter-spacing: 1.2pt;
}

.final-decision-header h1 {
    margin: 13mm 0 0;
    padding: 0;
    border: 0;
    color: #FFFFFF;
    font-size: 28pt;
    font-weight: 600;
    letter-spacing: -0.7pt;
    line-height: 1.22;
    page-break-before: avoid;
}

.final-decision-body {
    padding-top: 13mm;
}

.final-decision-body > p:first-child {
    margin-bottom: 9mm;
    color: var(--color-ink);
    font-size: 13pt;
    font-weight: 550;
    line-height: 1.7;
}

.final-decision blockquote {
    margin: 0;
    padding: 6mm 0 0;
    border-top: 1pt solid var(--color-ink);
    background: transparent;
    box-shadow: none;
    color: var(--color-text-body);
    font-size: 11.2pt;
    line-height: 1.75;
}

.sources-appendix {
    min-height: 207mm;
    color: var(--color-text-secondary);
    font-size: var(--type-source);
    page-break-before: always;
}

.sources-appendix h1 {
    margin: 0 0 10mm;
    padding: 6mm 0 4mm;
    border-top: 1pt solid var(--color-ink);
    border-bottom: 0.5pt solid var(--color-border);
    color: var(--color-ink);
    font-size: 19pt;
    font-weight: 650;
    letter-spacing: -0.25pt;
}

.sources-appendix h1::before {
    display: block;
    margin-bottom: 3mm;
    color: var(--color-text-muted);
    content: "SOURCES";
    font-size: var(--type-caption);
    font-weight: 650;
    letter-spacing: 1.5pt;
}

.sources-appendix h2 {
    margin: 8mm 0 3mm;
    padding: 0;
    color: var(--color-text-secondary);
    font-size: 11pt;
    font-weight: 650;
    line-height: 1.55;
}

.sources-appendix ul {
    margin: 1.5mm 0 5mm;
    padding: 0;
    list-style: none;
}

.sources-appendix li {
    margin: 0 0 3mm;
    padding: 0;
    color: var(--color-text-secondary);
    font-size: var(--type-source);
    line-height: 1.52;
    break-inside: avoid;
}

.sources-appendix a {
    color: var(--color-ink);
    font-weight: 550;
    text-decoration: underline;
    text-decoration-color: var(--color-border-strong);
    text-underline-offset: 1.5pt;
}

.sources-appendix a[href^="http"]::after {
    display: block;
    margin-top: 0.5mm;
    color: var(--color-text-muted);
    content: attr(href);
    font-size: var(--type-caption);
    font-weight: 400;
    line-height: 1.35;
    text-decoration: none;
    overflow-wrap: anywhere;
    word-break: break-all;
}

.tool-signature {
    margin-top: 9mm;
    padding-top: 4mm;
    border-top: 0.5pt solid var(--color-border);
    color: var(--color-text-muted);
    font-size: var(--type-caption);
    line-height: 1.5;
    break-inside: avoid;
}

.tool-signature p {
    margin: 0.8mm 0;
    color: var(--color-text-muted);
}

.tool-signature a {
    color: var(--color-text-muted);
    text-decoration: underline;
}
"""

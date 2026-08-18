// Detail-tab export helpers: PDF (expo-print) + rich-HTML copy (expo-clipboard).
//
// The detail tab contains a 10-block engineering "note de calcul". Users want:
//   • a shareable/printable PDF (uses expo-print + expo-sharing)
//   • a rich-text copy that Word / Google Docs can paste as a real table
//     (uses expo-clipboard with StringFormat.HTML)

import * as Clipboard from "expo-clipboard";
import * as Print from "expo-print";
import * as Sharing from "expo-sharing";
import { Platform } from "react-native";

// Kept lightweight so we don't drag the module screen's types into src/.
export type ExportDetailRow = {
  label: string;
  unit?: string | null;
  value: string;
  formula?: string | null;
};
export type ExportDetailBlock = {
  title: string;
  rows: ExportDetailRow[];
  subBlocks?: ExportDetailBlock[];
};
export type ExportDetailPayload = { blocks: ExportDetailBlock[] };

export type ExportInputRow = {
  label: string;
  value: string;
  unit?: string | null;
};

export type ExportOptions = {
  moduleName: string;
  categoryLabel: string; // e.g. "ACIER • EC3"
  inputs: ExportInputRow[];
  detail: ExportDetailPayload;
  results?: ExportInputRow[];
};

// ---------------------------------------------------------------------------
// HTML rendering — designed to look decent both when printed as A4 PDF and
// when pasted into Word / Google Docs / Outlook.
// ---------------------------------------------------------------------------

function escape(s: unknown): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderBlock(block: ExportDetailBlock, depth = 0): string {
  const titleTag = depth === 0 ? "h2" : "h3";
  const rows = block.rows
    .map(
      (r) => `
        <tr>
          <td class="lbl">${escape(r.label)}${
            r.unit ? ` <span class="unit">[${escape(r.unit)}]</span>` : ""
          }</td>
          <td class="val">${escape(r.value)}</td>
          <td class="frm">${r.formula ? escape(r.formula) : "&mdash;"}</td>
        </tr>`,
    )
    .join("");
  const sub = (block.subBlocks ?? [])
    .map((sb) => renderBlock(sb, depth + 1))
    .join("");
  return `
    <section class="block block-depth-${depth}">
      <${titleTag}>${escape(block.title)}</${titleTag}>
      <table class="detail">
        <thead>
          <tr>
            <th class="lbl">Paramètre</th>
            <th class="val">Valeur</th>
            <th class="frm">Formule</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      ${sub}
    </section>`;
}

function renderKeyValueTable(
  title: string,
  rows: ExportInputRow[],
): string {
  if (!rows.length) return "";
  const trs = rows
    .map(
      (r) => `
        <tr>
          <td class="lbl">${escape(r.label)}</td>
          <td class="val">${escape(r.value)}${
            r.unit ? ` <span class="unit">${escape(r.unit)}</span>` : ""
          }</td>
        </tr>`,
    )
    .join("");
  return `
    <section class="block">
      <h2>${escape(title)}</h2>
      <table class="kv">
        <tbody>${trs}</tbody>
      </table>
    </section>`;
}

function todayFR(): string {
  const d = new Date();
  return d.toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

export function buildDetailHtml(opts: ExportOptions): string {
  const inputs = renderKeyValueTable("Données d'entrée", opts.inputs);
  const results = opts.results
    ? renderKeyValueTable("Résultats de vérification", opts.results)
    : "";
  const blocks = opts.detail.blocks
    .map((b) => renderBlock(b, 0))
    .join("");

  return `<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>Note de calcul — ${escape(opts.moduleName)}</title>
  <style>
    @page { size: A4; margin: 18mm 14mm; }
    body {
      font-family: "Helvetica Neue", Arial, sans-serif;
      color: #111;
      font-size: 11px;
      line-height: 1.4;
      margin: 0;
    }
    header {
      border-bottom: 2px solid #C74E0A;
      padding-bottom: 10px;
      margin-bottom: 18px;
    }
    header .eyebrow {
      color: #C74E0A;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 2px;
      text-transform: uppercase;
    }
    header h1 {
      margin: 4px 0 2px 0;
      font-size: 22px;
      color: #111;
    }
    header .date {
      color: #666;
      font-size: 10px;
    }
    section.block { margin-bottom: 16px; page-break-inside: avoid; }
    section.block h2 {
      background: #F4E7DA;
      color: #6B2A00;
      font-size: 12px;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      padding: 6px 10px;
      margin: 0 0 6px 0;
      border-left: 4px solid #C74E0A;
    }
    section.block h3 {
      color: #333;
      font-size: 11px;
      margin: 10px 0 6px 8px;
      padding-left: 8px;
      border-left: 3px solid #999;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }
    table.detail thead th {
      background: #F5F5F5;
      text-align: left;
      color: #444;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 5px 8px;
      border-bottom: 1px solid #DDD;
    }
    table td, table th { padding: 5px 8px; vertical-align: top; border-bottom: 1px solid #EEE; }
    table td.lbl, table th.lbl { width: 42%; }
    table td.val, table th.val {
      width: 22%; font-family: "Courier New", monospace;
      color: #6B2A00; font-weight: 700; text-align: right;
    }
    table td.frm, table th.frm {
      width: 36%; font-family: "Courier New", monospace;
      color: #555; font-size: 10px; text-align: right;
    }
    table.kv td.lbl { width: 55%; color: #333; }
    table.kv td.val { text-align: right; width: 45%; }
    .unit {
      color: #999; font-family: "Courier New", monospace; font-size: 10px;
      margin-left: 4px; text-transform: none; letter-spacing: 0.2px;
    }
    footer {
      margin-top: 24px; padding-top: 8px; border-top: 1px solid #DDD;
      color: #999; font-size: 9px; text-align: center;
    }
  </style>
</head>
<body>
  <header>
    <div class="eyebrow">${escape(opts.categoryLabel)}</div>
    <h1>Note de calcul — ${escape(opts.moduleName)}</h1>
    <div class="date">Généré le ${escape(todayFR())} • C-Lab</div>
  </header>
  ${inputs}
  ${results}
  ${blocks}
  <footer>Généré par C-Lab — moteur Str-lib.</footer>
</body>
</html>`;
}

// ---------------------------------------------------------------------------
// Export actions
// ---------------------------------------------------------------------------

/**
 * Generate a PDF from the note de calcul and prompt the OS share sheet.
 * On web the PDF is downloaded / opened by the browser (expo-print handles).
 */
export async function exportDetailPdf(opts: ExportOptions): Promise<void> {
  const html = buildDetailHtml(opts);
  const filename =
    `note-calcul-${slugify(opts.moduleName)}-${todayFileStamp()}`.slice(0, 60);

  const { uri } = await Print.printToFileAsync({
    html,
    base64: false,
  });

  if (Platform.OS === "web") {
    // expo-print on web triggers a print dialog directly, but we can also
    // open the generated URI for preview/download.
    try {
      if (typeof window !== "undefined") window.open(uri, "_blank");
    } catch {
      /* ignore */
    }
    return;
  }

  const canShare = await Sharing.isAvailableAsync();
  if (canShare) {
    await Sharing.shareAsync(uri, {
      mimeType: "application/pdf",
      dialogTitle: "Partager la note de calcul",
      UTI: "com.adobe.pdf",
    });
  } else {
    // Fallback — just log the path; iOS/Android always have Sharing.
    console.log("PDF written to", uri, "filename would be", filename);
  }
}

/**
 * Copy a rich-HTML version of the note de calcul to the clipboard so users
 * can paste directly into Word / Google Docs / Outlook and get real tables
 * with headings and formatting.
 */
export async function copyDetailForWord(
  opts: ExportOptions,
): Promise<boolean> {
  const html = buildDetailHtml(opts);
  try {
    return await Clipboard.setStringAsync(html, {
      inputFormat: Clipboard.StringFormat.HTML,
    });
  } catch {
    // Fallback: plain-text copy of the HTML.
    return Clipboard.setStringAsync(html);
  }
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function todayFileStamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`;
}

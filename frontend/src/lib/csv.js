/** Tiny CSV helpers (quoted fields, commas and new lines inside quotes). */
export function parseCsv(text) {
  const rows = []; let row = []; let field = ""; let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.some((f) => f.trim()));
}

const REVIEW_COLUMNS = ["review_text", "review", "text", "comment", "content", "feedback"];

/** Pull the review texts out of a CSV: a column named like "review", else the first column. */
export function reviewsFromCsv(text) {
  const rows = parseCsv(text.replace(/^﻿/, ""));
  if (!rows.length) return [];
  const header = rows[0].map((h) => h.trim().toLowerCase());
  const col = header.findIndex((h) => REVIEW_COLUMNS.includes(h));
  const body = col >= 0 ? rows.slice(1) : rows;
  return body.map((r) => (r[col >= 0 ? col : 0] || "").trim()).filter(Boolean);
}

export function toCsv(rows) {
  const esc = (v) => {
    const s = String(v ?? "");
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return "﻿" + rows.map((r) => r.map(esc).join(",")).join("\r\n");
}

// Build HIGH/MEDIUM-split review CSVs + Amazon flat file from rewritten.json
const fs = require("fs");
const path = require("path");
const out = JSON.parse(fs.readFileSync(path.join(__dirname, "rewritten.json"), "utf8"));
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "catalog.json"), "utf8"));
const origByAsin = new Map(catalog.map(c => [c.asin, c.title]));
const esc = s => `"${String(s == null ? "" : s).replace(/"/g, '""')}"`;
const H = ["#","ASIN","SKUs","Family","30d Sales","Conf","Original Title","Orig Ch","New Title","New Ch","Item Highlights","Notes"];
const row = (r, i) => [i+1, r.asin, r.skus.join("/"), r.family, r.sales, r.conf, origByAsin.get(r.asin)||"", (origByAsin.get(r.asin)||"").length, r.title, r.title.length, r.ih, r.notes].map(esc).join(",");

const high = out.filter(r => r.conf === "HIGH");
const med = out.filter(r => r.conf === "MEDIUM" || r.conf === "REVIEW");
fs.writeFileSync(path.join(__dirname, "review-HIGH.csv"), [H.map(esc).join(","), ...high.map(row)].join("\n"));
fs.writeFileSync(path.join(__dirname, "review-MEDIUM-and-REVIEW.csv"), [H.map(esc).join(","), ...med.map(row)].join("\n"));

const T = ["item_sku","external_product_id","external_product_id_type","item_name","item_highlights","update_delete"];
const trows = [T.join("\t")]; const noSku = [];
let n = 0;
for (const r of high) {
  if (!r.skus.length) { noSku.push(r.asin + "\t" + r.title); continue; }
  for (const sku of r.skus) { trows.push([sku, r.asin, "ASIN", r.title, r.ih, "PartialUpdate"].join("\t")); n++; }
}
fs.writeFileSync(path.join(__dirname, "flatfile-HIGH.tsv"), trows.join("\n"));
fs.writeFileSync(path.join(__dirname, "needs-sku-HIGH.tsv"), "asin\tnew_title\n" + noSku.join("\n"));
console.log("HIGH:", high.length, "→", n, "SKU rows | no-SKU:", noSku.length, "| MEDIUM+REVIEW:", med.length);

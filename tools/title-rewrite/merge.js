// Merge all persisted catalog pages + page18.json → catalog.json (deduped by ASIN)
const fs = require("fs");
const path = require("path");
const TOOLS = "/root/.claude/projects/-home-user-amazn-scraper/c052fe2b-2f11-5c6e-a047-b52bd63f873b/tool-results";
const SCRATCH = __dirname;

const pages = {};
for (const f of fs.readdirSync(TOOLS)) {
  if (!f.includes("get_product_data")) continue;
  try {
    const j = JSON.parse(fs.readFileSync(path.join(TOOLS, f), "utf8"));
    if (j.success && j.pagination) pages[j.pagination.page] = j.data;
  } catch (e) { /* skip non-JSON */ }
}
const p18 = JSON.parse(fs.readFileSync(path.join(SCRATCH, "page18.json"), "utf8"));
pages[18] = p18.data;

const missing = [];
for (let p = 1; p <= 29; p++) if (!pages[p]) missing.push(p);
if (missing.length) { console.log("MISSING PAGES:", missing.join(",")); process.exit(1); }

// Flatten: by ASIN, collect all SKUs and best (highest-sales) row
const byAsin = new Map();
function addRow(asin, sku, title, sales) {
  if (!asin || !title) return;
  if (!byAsin.has(asin)) byAsin.set(asin, { asin, title, sales: 0, skus: new Set() });
  const rec = byAsin.get(asin);
  rec.sales += sales || 0;
  if (sku) rec.skus.add(sku);
  if (title.length > rec.title.length) rec.title = title; // keep fullest title
}
let rowCount = 0;
for (let p = 1; p <= 29; p++) {
  for (const node of pages[p]) {
    rowCount++;
    addRow(node.asin, node.sku, node.title, node.total_sales);
    for (const c of node.children || []) addRow(c.asin, c.sku, c.title, 0); // child sales already in parent sum? keep separate skus
  }
}

const catalog = [...byAsin.values()].map(r => ({ asin: r.asin, title: r.title, sales: Math.round(r.sales * 100) / 100, skus: [...r.skus] }));
catalog.sort((a, b) => b.sales - a.sales);
fs.writeFileSync(path.join(SCRATCH, "catalog.json"), JSON.stringify(catalog));

// Stats
const over75 = catalog.filter(r => r.title.length > 75);
const withSales = catalog.filter(r => r.sales > 0);
console.log("root rows scanned:", rowCount);
console.log("unique ASINs:", catalog.length);
console.log("ASINs with sales (30d):", withSales.length);
console.log("titles > 75 chars:", over75.length);
console.log("titles <= 75 chars:", catalog.length - over75.length);
console.log("ASINs with no SKU mapped:", catalog.filter(r => r.skus.length === 0).length);

// Family clustering by title keywords (rough)
const fams = [
  ["flag", /flag/i],
  ["cruise", /cruise|stateroom|porthole|anchor magnet|ship wheel/i],
  ["custom/personalized", /custom|personaliz|upload/i],
  ["driver/novelty-car", /driver|baby on board|caution/i],
  ["dog/paw", /dog|paw|puppy|bone magnet/i],
  ["photo magnet", /photo magnet|picture magnet/i],
  ["business card", /business card/i],
];
const counts = {};
for (const r of catalog) {
  let matched = "other";
  for (const [name, re] of fams) if (re.test(r.title)) { matched = name; break; }
  counts[matched] = (counts[matched] || 0) + 1;
}
console.log("family counts (first-match):", JSON.stringify(counts, null, 1));

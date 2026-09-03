# MMU Catalog Title Rewrite Pipeline

Rewrites all catalog titles to the July 27, 2026 Amazon 75-character limit
using the rules in `.claude/skills/amazon-title-compress` (comma separators,
capitalized Inch with `in` fallback, comma-flow Item Highlights, family
keyword templates validated against ads search-term + SQP data).

## Run order
1. Pull the catalog via Aakar `get_product_data` (100 rows/page, all pages)
   and save the raw page JSON responses to a working directory.
2. `node merge.js` — merges pages, dedupes by ASIN → `catalog.json`.
3. `node rewrite.js` — generates titles + highlights → `rewritten.json`.
   Verifies every title ≤75 and highlights ≤125; disambiguates duplicate
   titles; assigns HIGH / MEDIUM / REVIEW confidence.
4. `node outputs-split.js` — writes `review-HIGH.csv`,
   `review-MEDIUM-and-REVIEW.csv`, `flatfile-HIGH.tsv` (SKU-level,
   PartialUpdate), and `needs-sku-HIGH.tsv`.

Paths in the scripts assume the data files sit next to them — adjust
`__dirname` references or copy the scripts into the working directory.

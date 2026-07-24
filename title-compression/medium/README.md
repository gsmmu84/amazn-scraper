# MEDIUM Batch — Title Compression (Jovelove Review Applied)

Final titles for the MEDIUM-difficulty title-compression batch, produced by applying
Jovelove's review feedback (sheet: "MEDIUM Batch — Jovelove Review Sheet (Jul 2026)",
reviewed 2026-07-23) to the previously generated compressed titles.

## Files

| File | Contents |
| --- | --- |
| `jovelove_review_raw.csv` | Verbatim export of the review sheet (158 rows), markdown escaping removed |
| `medium_final_titles.csv` | Final title + item highlights per ASIN, with provenance and flags |
| `flags_needs_attention.csv` | Subset of rows where the reviewer's text needed an automated fix — verify before upload |

## How feedback was applied

For each of the 158 rows:

1. **Reviewer proposed a corrected title** (`proposed title/correction` column) → that title is final
   (`title_source = REVIEWER_TITLE`, 80 rows).
2. **Reviewer marked "ok"** (in the verdict or proposed column) → the compressed `new_title` is final
   (`APPROVED_OK`, 14 rows).
3. **Only the highlights were corrected** → compressed title kept, reviewer's highlights used
   (`KEPT_NEW_TITLE`, 56 rows).
4. **No feedback at all** → compressed title and highlights kept unchanged, flagged
   `NO_REVIEWER_FEEDBACK` (`NO_FEEDBACK`, 8 rows: B0DMQKV8HY, B0G6GDGW17, B0BMJHHM68,
   B0DSQ9S86T, B0CVSF79VC, B0D94RGB4Q, B0G357LQZY, B0G6GDCNL5).

Item highlights: the reviewer's corrected highlights (second `item highlights` column, 127 rows)
replace the originals; otherwise the original highlights are kept (`highlights_source` column).

All markdown escape artifacts from the sheet (`\!`, `\-`, `\"`) were removed, and every final
title was validated against the 75-character limit (max in the batch is now exactly 75).

## Manual resolutions (see `flags_needs_attention.csv`)

Four reviewer titles in the `1-CRUISE_PLACEHOLDER` group needed fixes:

- **B0GPRTFYFK / B0GLHYCFSX** — reviewer titles were 76 chars (over the 75 limit). Dropped the
  duplicated "Custom" ("Custom Birthday Custom Cruise…" → "Custom Birthday Cruise…") to fit.
  For B0GLHYCFSX the reviewer's deliberate size simplification (9x10 → 10 Inch) was kept.
- **B0GPRLBPFX (5 Inch) / B0GPRLLKBL (6 Inch)** — reviewer titles both said "8 Inch"
  (copy-paste from the 8-inch row); the correct size from the listing was restored.

One typo in reviewer highlights was fixed: "mad in USA" → "made in USA" (B0DCGW5K99, noted in
`processing_notes`).

## Upload files

- `medium_flatfile_title_update.txt` — tab-delimited PartialUpdate flat file with the **good rows
  only**: 124 ASINs / 158 SKU rows (FBA + FBM SKUs both included). Good = reviewer signed off,
  no processing flags, and a seller SKU was found. Title updates only — highlights are not
  included because their flat-file field mapping is unverified.
  - SKUs were mapped from the account's advertising data (`advertised_products`), since the
    catalog sync has no SKUs. Spot-check a few before upload.
  - `feed_product_type` is set to `auto_accessory` (listings sit in Automotive Magnets). If your
    category template uses a different product type or header version, paste the `item_sku` /
    `item_name` / `update_delete` columns into your downloaded template instead.
- `whats_left.csv` — the 34 ASINs NOT in the flat file, with a `why_left_out` reason:
  - 4 × `AUTO_FIXED_NEEDS_CONFIRM` — the cruise rows where the reviewer's title was auto-fixed
    (over 75 chars / wrong size); confirm the fix, then they're ready (SKUs included).
  - 8 × `NOT_REVIEWED` — rows with no Jovelove feedback at all.
  - 22 × `NO_SKU_FOUND` — ASIN never advertised, so no SKU in ad data; needs a Seller Central
    SKU lookup.

## Batch composition

| check_group | rows |
| --- | --- |
| 1-CRUISE_PLACEHOLDER | 17 |
| 2-TOP25_BY_SALES | 25 |
| 3-RANDOM_SAMPLE_GENERAL | 40 |
| 4-EXCLUDED_RULE_VIOLATION | 26 |
| 5-EXCLUDED_NO_SKU_MATCH | 50 |

Note: groups 4 and 5 were excluded from the original automated push (rule violations /
no SKU match in the report); they now carry reviewer-corrected titles here, but their
original `status` (`SKIPPED_VALIDATION` / `NO_MATCH_IN_REPORT`) is preserved in
`jovelove_review_raw.csv` — route them through whatever manual upload path applies.

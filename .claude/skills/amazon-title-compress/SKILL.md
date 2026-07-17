---
name: amazon-title-compress
description: Compress Amazon product titles to 75 characters or less (July 27, 2026 limit) with a matching 125-character Item Highlights string, validated against the seller's real keyword performance data (ad search-term reports + Search Query Performance). Use whenever the user wants to shorten, rewrite, or audit Amazon titles, prep for the 75-char limit, or asks about title keyword optimization. Accepts single or batch input; front-loads titles so the full sales message survives 70-character truncation.
---

# Amazon Title Compress

Rewrite Amazon product titles to meet the July 27, 2026 75-character limit while retaining the highest-value keywords, differentiators, and conversion signals. Route overflow to Item Highlights (125 chars), which is searchable and visible in search results and on product detail pages.

Two principles drive every rewrite, both learned from live testing on real catalogs:

1. **Assume shoppers see only the first ~70 characters.** Mobile search results truncate titles. The complete sales message (keyword + size/spec + pack + hook) must land by roughly character 60; only the lowest-value element may sit in the truncation zone.
2. **Validate keywords with data, not judgment.** When the seller's ad search-term data and SQP (Brand Analytics Search Query Performance) are available, the words in the title are chosen by what actually converts and where market volume sits — not by what sounds right. Judgment-only compression missed a 23,000-volume query on a real listing that data caught immediately.

## Inputs

**Single mode:** original title + Amazon listing URL or ASIN.

**Batch mode:** a pasted list (`Title | URL` per line, or CSV with title,url columns), a spreadsheet, or — if a catalog analytics MCP is connected — pull titles directly from the seller's catalog (e.g., top sellers by revenue).

If only a title is given with no URL/ASIN, ask for the URL or category — category drives prioritization.

## Step 1 — Category

For each listing, determine the category group (see Step 4 tables):
1. If a catalog/analytics tool is connected, use its category data.
2. Otherwise fetch the listing page (WebFetch) and read the breadcrumb.
3. If blocked, infer from the title when unambiguous (e.g. "car magnet" → Automotive); ask only when genuinely uncertain.

## Step 2 — Pull Keyword Performance Data

This step separates a good rewrite from a guess. Gather two views per product (or product family — siblings sharing a keyword universe, like size variants, can share one pull):

**A. Ad search terms (what converts):** top search terms by orders, last 30 days, from Sponsored Products search term reports. If an ads analytics MCP (e.g. Aakar) is connected, query it — filter campaigns by family (`campaign_name ILIKE '%flag%'`), aggregate orders/sales per search term. Otherwise ask the user to paste their Seller Central > Advertising > Search Term Report export.

**B. SQP (where the market is):** Brand Analytics Search Query Performance for the ASIN — search query, weekly volume, the ASIN's impression share, market purchases, ASIN purchases. Via MCP if available; otherwise ask for the Brand Analytics SQP export. Note SQP weeks adjacent to a holiday inflate seasonal terms — judge rankings, not raw volumes.

If the user has neither, proceed on category rules alone but say plainly that keywords are unvalidated.

**How to use the data:**
- The highest-converting phrase for the product opens the title.
- Every distinct converting **token** (word) must appear somewhere across title + Item Highlights. Watch for near-miss tokens: "magnet" in the title does not cover searches for "magnetic"; dropping "decal" abandons every "car decal" query. Check tokens, not phrases — Amazon matches on words.
- High-volume queries with low impression share (under ~1%) are white space: work the missing token into the title if it fits, otherwise into Item Highlights, and flag it to the user as a PPC opportunity too.
- Word order within a phrase doesn't need mirroring ("frequent stops car magnet" vs "car magnets frequent stops" — same tokens).

## Step 3 — Parse the Original Title

Break the original into components: Brand, Model, Core ID (what it is), Key Spec (size/dose/capacity/count), Ingredients/Materials, Benefit Claim, Variant (color/flavor), Trust Signal (Made in USA, certifications), Category Descriptor (generic label duplicating the browse node — almost always droppable).

## Step 4 — Category Priority Rules

Priority order: **Must-Keep → High-Value → Item Highlights → Drop**.

### Apparel & Accessories
**Must-Keep:** Gender/Age group, Core item type, Primary material (if distinctive), Size indicator
**High-Value:** Color/pattern, Fit type, Quantity
**Item Highlights:** Care instructions, Additional colors, Style details, Season
**Drop:** Generic descriptors ("Comfortable", "High Quality"), redundant category label
**Abbreviations OK:** XS–3XL, oz, in, ft

### Automotive
**Must-Keep:** Product name, Key spec/grade, Size/quantity
**High-Value:** Compatibility note (if short), Certification
**Item Highlights:** Full vehicle compatibility list, Additional specs, Bundle contents
**Drop:** Generic restatements, "High Performance"
**Abbreviations OK:** qt, gal, oz, PSI, RPM, V, W, Ah

### Baby Products
**Must-Keep:** Product name, Key feature/mode count, Color/pattern
**High-Value:** Age/weight range, Size stage
**Item Highlights:** Weight limits, Safety certifications, Machine washable, Included accessories
**Drop:** Generic reassurance ("Safe", "Comfortable")
**Abbreviations OK:** lbs, oz, in

### Beauty & Personal Care
**Must-Keep:** Product name, Skin/hair type if specific, Size/count
**High-Value:** Key active ingredient, Dermatologist tested, Fragrance-free
**Item Highlights:** Full ingredient callouts, Certifications, Regimen placement
**Drop:** "Natural", "Clean Beauty", redundant category label
**Abbreviations OK:** oz, fl oz, mL, g

### Electronics & Computers
**Must-Keep:** Model number/name, Primary function, Key spec
**High-Value:** Color/finish, Compatibility signal, Generation/version
**Item Highlights:** Battery life, Included accessories, OS compatibility, Warranty
**Drop:** Marketing ("Next-Gen", "Ultra"), redundant "Smart"
**Abbreviations OK:** GB, TB, GHz, W, mAh, in, mm, Hz, USB, HDMI, 4K, 8K

### Grocery & Gourmet Food
**Must-Keep:** Product name, Flavor/variety, Net weight or count, Pack size
**High-Value:** Dietary claim (only if primary purchase driver)
**Item Highlights:** Certifications, Allergen info, Nutrition, Storage
**Drop:** "Delicious", "All-Natural" without certification, "Artisan"
**Abbreviations OK:** oz, fl oz, lb, g, kg, mL, L, pk, ct

### Health & Household / Supplements
**Must-Keep:** Active ingredient + form (form specificity matters for search), Dose, Count
**High-Value:** Primary benefit — keep if space allows
**Item Highlights:** Additional ingredients, Origin, Certifications (NSF, USP, GMP), Dietary callouts
**Drop:** "Herbal Supplement", "Dietary Supplement", "All Natural", "Pure"
**Abbreviations OK:** mg, mcg, IU, g, ct, cap, tab, oz

### Home & Kitchen
**Must-Keep:** Product name, Key feature or mode count, Capacity/size
**High-Value:** Material, Color if primary driver
**Item Highlights:** Dishwasher safe, Oven safe temp, Included accessories, Warranty
**Drop:** "Perfect For", "Ideal For", "Kitchen Essential"
**Abbreviations OK:** qt, oz, in, ft, sq ft, W, V, lb

### Office Products & Stationery
**Must-Keep:** Product name, Key spec (yield, count, capacity), Count/pack size
**High-Value:** Compatibility (if short), Color
**Item Highlights:** Full compatibility list, ISO yield, Coverage spec
**Drop:** "Office Essential", "Professional Quality"
**Abbreviations OK:** pk, ct, in, mm, lb, XL, HY

### Pet Supplies
**Must-Keep:** Product name, Target animal + life stage, Primary protein/ingredient, Size/weight
**High-Value:** Special formula callout if it's the purchase reason
**Item Highlights:** Guaranteed analysis, AAFCO statement, Ingredients, Certifications
**Drop:** "Premium", "Gourmet", "Wholesome", redundant category label
**Abbreviations OK:** lb, lbs, oz, kg, ct

### Sports & Outdoors / Exercise & Fitness
**Must-Keep:** Product name, Key spec (capacity, resistance, volume), Size/color if it drives purchase
**High-Value:** Distinctive material, Gender/age if targeted
**Item Highlights:** Dimensions, Weight, Warranty, Compatible accessories
**Drop:** "High Performance", "Professional Grade"
**Abbreviations OK:** lbs, kg, oz, L, gal, in, ft, cm, mm

### Tools & Home Improvement
**Must-Keep:** Model number OR product name, Type, Key spec (voltage, torque, PSI)
**High-Value:** Chuck/bit size, Speed, Battery-included flag
**Item Highlights:** Accessories/battery info, Kit contents, Warranty, Platform compatibility
**Drop:** "Powerful", "Professional", "Heavy-Duty" unless technically specified
**Abbreviations OK:** V, Ah, in, ft, lbs, RPM, PSI, CFM, HP, W

### Toys & Games
**Must-Keep:** Product/set name, Piece count or key feature, Age range
**High-Value:** Theme/character if it drives purchase, Battery requirements
**Item Highlights:** Dimensions, Battery specs, Choking hazard note, Educational callouts
**Drop:** "Fun", "Educational" as standalone words
**Abbreviations OK:** pc, pcs, in, cm

## Step 5 — Title Layout

Build the title in this order, and keep the complete message inside the first ~60 characters:

```
[Top converting keyword phrase] [size/spec] [pack] | [hook] | [trust signal]
```

- **Open with the highest-converting search phrase** from Step 2 (or the Must-Keep core from Step 4 if no data). Never open with the brand.
- **Brand leaves the title entirely.** Amazon displays the Brand field on its own line under the title, so brand-in-title pays 12–16 characters for information the shopper already sees. Spend those characters on a converting keyword or trust signal instead. Exception: keep the brand only if the user says branded searches matter for this product or the data shows the brand name itself converts.
- **The hook** is the conversion driver: variant/color for standard products, the action for customs ("Upload Logo"), the audience for novelty ("Funny Student Driver").
- **Trust signal closes the title** — for most US catalogs that's "Made in USA" (11 chars). If it pushes the title past 70, use "USA Made" (8 chars) so nothing is clipped. Only claim origin the listing actually claims.
- Separate components with ` | ` or single spaces. No em dashes, no hyphens-as-separators, no commas between major components.

## Step 6 — Compression Rules (Universal)

**Counting:** every character counts, including spaces. 75 max title, 125 max Item Highlights — but treat 70 as the visibility budget for the title's message.

**Safe abbreviations:** units (oz, fl oz, lb, lbs, g, kg, mg, mcg, mL, L, qt, gal, in, ft, cm, mm, W, V, Ah, mAh), counts (ct, pk, ea, pc, pcs), sizes (XS–3XL), common acronyms (USB, HDMI, LED, LCD, AC, DC, AI, UV, IR, BPA, NSF, GMP, USDA). Write dimensions compactly: `18x24 in`, not `18" x 24"`.

**Never:** truncate mid-word, keyword-stuff synonyms, ALL CAPS (except acronyms/stylized brands), promotional language ("Best", "#1", "Sale"), special characters other than `+ & / # | % ( )`.

**Compression order:** drop the category descriptor → move trust signals to Item Highlights (unless one closes the title per Step 5) → abbreviate units → consolidate benefit claims → move compatibility details to Item Highlights → trim variant attributes already handled by a variation page.

## Step 7 — Item Highlights

- Carry every still-searchable token that left the title; never repeat a token already in the title (wasted characters).
- Cover the near-miss tokens from Step 2 ("magnetic", "decal", "personalized"-type words).
- Read as natural, useful text — not a keyword dump. Lead with the highest-conversion overflow.

## Step 8 — Verify by Script

Character counts done by eye are wrong often enough to matter — a title that's 71 chars clips at 70. Before presenting results, run a quick script (node/python) that checks every row: title ≤ 75, Item Highlights ≤ 125, brand not present in title (unless the exception applies), and computes the exact 70-char truncation preview. Fix violations and re-run until clean.

## Step 9 — Output

**Single listing:**
```
TITLE ([X]/75 chars):
[New title]

ITEM HIGHLIGHTS ([X]/125 chars):
[Item Highlights string]

KEYWORD EVIDENCE:
- [term]: [orders/volume/share data that justified it]

WHAT MOVED AND WHY:
- [Component]: moved to Item Highlights — [reason]
- [Component]: dropped — [reason]

ORIGINAL ([X] chars):
[Original title]
```

**Batch:** deliver as a spreadsheet (Google Sheet or xlsx) with columns:
`# | ASIN | SKU | Category | Sales | Units | Original Title | Orig Chars | New Title | New Chars | What Shoppers See at 70 Chars | Item Highlights | IH Chars | Keyword Evidence & Notes`

The 70-char preview column shows the literal truncated view (with `…` if clipped) so the user can eyeball each row as a mobile shopper would see it. The evidence column cites the specific data behind each choice (e.g. `"custom car magnet" 28 ad orders; "personalized" 3.2% SQP share`).

Flag separately any white-space findings (high-volume, low-share queries) — they're PPC opportunities beyond the title work.

## When to Ask Questions

Ask only if: the category can't be determined; a key spec is missing that would change decisions; batch input can't be parsed; or the user has no performance data and you need them to choose between proceeding unvalidated or pasting exports. Do not ask permission to proceed.

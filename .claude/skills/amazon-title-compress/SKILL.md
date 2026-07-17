---
name: amazon-title-compress
description: Compress an Amazon product title to 75 characters or less and produce a matching 125-character Item Highlights string, using category-specific priority rules. Accepts single (title + URL) or batch (multiple title + URL pairs) input. Preserves the highest-value SEO and conversion elements in the title; routes supporting claims to Item Highlights where they remain searchable.
---

# Amazon Title Compress

Rewrite Amazon product titles to meet the July 27, 2026 75-character limit while retaining the highest-value keywords, differentiators, and conversion signals. Route overflow to Item Highlights (125 chars), which is searchable and visible in search results and on product detail pages.

## Inputs

**Single mode:**
- Original title (pasted)
- Amazon listing URL or ASIN

**Batch mode:** paste a list using either format — auto-detect:
```
Title 1 | https://www.amazon.com/dp/ASIN1
Title 2 | https://www.amazon.com/dp/ASIN2
```
or CSV:
```
title,url
"Product Title 1",https://www.amazon.com/dp/ASIN1
"Product Title 2",https://www.amazon.com/dp/ASIN2
```

If only a title is pasted with no URL, ask for the URL or category before proceeding — category is required for correct prioritization.

## Step 1 — Fetch Category from Listing

For each listing:
1. Extract the ASIN from the URL.
2. Fetch the listing page (WebFetch) to capture:
   - Category breadcrumb (this is the primary category signal)
   - Existing bullet points / About This Item
   - Product details section (materials, dimensions, variants, certifications)
3. If the page is blocked or returns no breadcrumb, ask the user: "I couldn't read the category from the listing — what category is this listed under?"
4. Map the breadcrumb to one of the Category Groups below. Use the deepest matching level (e.g. "Tools & Home Improvement > Power & Hand Tools > Drills" maps to Tools).

## Step 2 — Parse the Original Title

Break the original title into components:
- **Brand** — registered brand/trade name
- **Model** — model number or product line name (Electronics, Tools, Automotive)
- **Core ID** — the thing it is (e.g. "Drill Driver", "Moisturizing Cream", "Dog Food")
- **Key Spec** — primary measurable differentiator (dose, capacity, wattage, size, count, weight)
- **Ingredients / Materials** — specific substances or materials (Berberine HCL, 100% Cotton, Stainless Steel)
- **Benefit Claim** — functional benefit (GLP-1 Support, Noise Canceling, Waterproof)
- **Variant** — color, flavor, scent, size variant
- **Trust Signal** — certifications, origin (Made in USA, USDA Organic, NSF Certified, UL Listed)
- **Category Descriptor** — generic category label that duplicates the browse node (e.g. "Herbal Supplements", "Power Tool", "Skincare Product") — almost always droppable

## Step 3 — Apply Category Priority Rules

Use the category group detected in Step 1. Follow the priority order: **Must-Keep → High-Value → Item Highlights → Drop**.

---

### Apparel & Accessories
**Must-Keep:** Brand, Gender/Age group, Core item type, Primary material (if distinctive — "Merino Wool", "100% Cotton"), Size indicator if in the title
**High-Value:** Color/pattern, Fit type (Slim Fit, Relaxed), Quantity (3-Pack)
**Item Highlights:** Care instructions, Additional colors, Style details, Season
**Drop:** Generic descriptors ("Comfortable", "High Quality", "Fashion"), Category label ("Shirt", "Pants" when the item type already covers it)
**Abbreviations OK:** XS, S, M, L, XL, XXL, 2XL, 3XL, oz, in, ft

---

### Automotive
**Must-Keep:** Brand, Product name, Key spec/grade (5W-30, SAE 30, 2000 PSI), Size/quantity
**High-Value:** Compatibility note (if short — "for Toyota", "Universal Fit"), Certification (API SN)
**Item Highlights:** Full vehicle compatibility list, Additional specs, Bundle contents
**Drop:** Generic ("Motor Oil", "Tire Inflator" when already in product name), "High Performance"
**Abbreviations OK:** qt, gal, oz, PSI, RPM, V, W, Ah

---

### Baby Products
**Must-Keep:** Brand, Product name, Key feature/mode count ("4-in-1"), Color/pattern
**High-Value:** Age/weight range, Size stage (Newborn, Infant, Toddler)
**Item Highlights:** Weight limits, Safety certifications (JPMA, ASTM), Machine washable, Included accessories
**Drop:** Generic reassurance ("Safe", "Comfortable", "Soft")
**Abbreviations OK:** lbs, oz, in

---

### Beauty & Personal Care
**Must-Keep:** Brand, Product name, Skin/hair type if specific (Dry Skin, Oily Skin), Size/count
**High-Value:** Key active ingredient if it's the point of the product (Vitamin C, Hyaluronic Acid, Retinol), Dermatologist tested, Fragrance-free
**Item Highlights:** Full ingredient callouts, Certifications (EWG, Cruelty-Free, Vegan), For use with instructions, Regimen placement (AM/PM)
**Drop:** Generic ("Natural", "Clean Beauty", "Best Seller"), redundant category label
**Abbreviations OK:** oz, fl oz, mL, g

---

### Electronics & Computers
**Must-Keep:** Brand, Model number/name, Primary function (Noise Canceling Headphones, 4K Monitor), Key spec (resolution, storage, wattage, connectivity)
**High-Value:** Color/finish, Compatibility signal (USB-C, Bluetooth 5.3), Generation/version
**Item Highlights:** Battery life, Included accessories, OS compatibility, Warranty details
**Drop:** Marketing ("Next-Gen", "Ultra", "Pro" unless it's the official product name), redundant "Smart" unless it distinguishes from a dumb version
**Abbreviations OK:** GB, TB, MB, GHz, MHz, W, V, Ah, mAh, in, mm, ms, Hz, USB, HDMI, 4K, 8K

---

### Grocery & Gourmet Food
**Must-Keep:** Brand, Product name, Flavor/variety, Net weight or count, Pack size
**High-Value:** Dietary claim (Gluten-Free, Keto, Non-GMO, Organic) — only if it's a primary purchase driver for this product
**Item Highlights:** Full certifications, Allergen info, Nutritional highlights, Storage/preparation
**Drop:** Generic ("Delicious", "All-Natural" without certification, "Artisan")
**Abbreviations OK:** oz, fl oz, lb, g, kg, mL, L, pk, ct

---

### Health & Household / Supplements
**Must-Keep:** Brand, Active ingredient + form (Berberine HCL, Magnesium Glycinate — form specificity matters for search), Dose (1500mg), Count (60ct, 90ct)
**High-Value:** Primary benefit (GLP-1 Support, Sleep Support) — keep if space allows
**Item Highlights:** Additional ingredients, Origin (Made in USA), Certifications (NSF, USP, GMP), Usage instructions, Dietary callouts (Vegan, Non-GMO)
**Drop:** Generic category label ("Herbal Supplement", "Dietary Supplement", "Vitamin"), "All Natural", "Pure"
**Abbreviations OK:** mg, mcg, IU, g, ct, cap, tab, soft, oz

---

### Home & Kitchen
**Must-Keep:** Brand, Product name, Key feature or mode count ("7-in-1", "Self-Cleaning"), Capacity/size
**High-Value:** Material (Stainless Steel, Cast Iron, BPA-Free), Color if it's a primary driver
**Item Highlights:** Dishwasher safe, Oven safe temp, Included accessories, Warranty, Compatible appliances
**Drop:** "Perfect For", "Ideal For", generic "Kitchen Essential"
**Abbreviations OK:** qt, oz, in, ft, sq ft, W, V, lb

---

### Office Products & Stationery
**Must-Keep:** Brand, Product name, Key spec (yield, page count, capacity), Count/pack size
**High-Value:** Compatibility (printer model series if short), Color
**Item Highlights:** Full compatibility list, ISO yield, Page coverage spec
**Drop:** Generic ("Office Essential", "Professional Quality")
**Abbreviations OK:** pk, ct, in, mm, lb (paper weight), XL, HY (High Yield)

---

### Pet Supplies
**Must-Keep:** Brand, Product name, Target animal + life stage (Adult Dog, Senior Cat, Puppy), Primary protein/main ingredient, Size/weight
**High-Value:** Special formula callout (Grain-Free, Limited Ingredient, Sensitive Stomach) if it's the purchase reason
**Item Highlights:** Guaranteed analysis, AAFCO statement, Full ingredient list, Certifications
**Drop:** "Premium", "Gourmet", "Wholesome", generic "Dog Food" when "Chicken & Rice Dog Food" already covers it
**Abbreviations OK:** lb, lbs, oz, kg, ct

---

### Sports & Outdoors / Exercise & Fitness
**Must-Keep:** Brand, Product name, Key spec (weight capacity, resistance level, volume, distance rating), Size/color if it drives the purchase
**High-Value:** Material (if distinctive — Titanium, Carbon Fiber, 600D Polyester), Gender/age if targeted
**Item Highlights:** Dimensions, Weight, Warranty, Compatible accessories, Activity-specific callouts
**Drop:** "High Performance", "Professional Grade" (unless it's a certified pro product)
**Abbreviations OK:** lbs, kg, oz, L, gal, in, ft, cm, mm

---

### Tools & Home Improvement
**Must-Keep:** Brand, Model number (if well-known) OR product name, Type (Cordless Drill Driver, Impact Wrench), Key spec (voltage, torque, PSI, CFM)
**High-Value:** Chuck size or bit size, Speed/variable speed, Battery included flag (if a major differentiator)
**Item Highlights:** Included accessories and battery/charger info, Kit contents, Warranty, Compatibility (FLEXVOLT, POWERSTATE)
**Drop:** "Powerful", "Professional", "Heavy-Duty" unless technically specified
**Abbreviations OK:** V, Ah, in, ft, lbs, RPM, PSI, CFM, HP, W

---

### Toys & Games
**Must-Keep:** Brand, Product/set name, Piece count (for LEGO-type sets) or Key feature, Age range
**High-Value:** Theme or character name if it drives purchase, Battery requirements (Battery-Free is a selling point)
**Item Highlights:** Dimensions (assembled/box), Battery specs and count, Choking hazard note if relevant, Educational skill callouts
**Drop:** "Fun", "Educational" as standalone words (show it, don't say it)
**Abbreviations OK:** pc, pcs, in, cm

---

## Step 4 — Compression Rules (Universal)

Apply to all categories after priority mapping:

**Character counting:** Count every character including spaces. The limit is 75 for the title, 125 for Item Highlights.

**Safe abbreviations (all categories):**
- Units: oz, fl oz, lb, lbs, g, kg, mg, mcg, mL, L, qt, gal, in, ft, cm, mm, W, V, Ah, mAh
- Count: ct, pk, ea, pc, pcs
- Size: XS, S, M, L, XL, XXL, 2XL, 3XL
- Common: USB, HDMI, LED, LCD, AC, DC, AI, UV, IR, BPA, NSF, GMP, USDA

**Separators:** Use a single space or ` | ` (pipe with spaces) between components. Do not use em dashes, hyphens as separators, or commas to separate major components (commas OK within a component list like "Magnesium Glycinate, Ceylon Cinnamon").

**Never do:**
- Truncate mid-word to hit the limit
- Keyword-stuff with synonyms ("Weight Loss Supplement Fat Burner Diet Pills")
- Use ALL CAPS except for established acronyms and brand names that are stylized that way
- Include promotional language: "Best", "#1", "Top Rated", "Sale", "Free Shipping"
- Repeat the brand in the title if it's already in the Brand field on Amazon (though in practice, leading with brand in the title is still common and acceptable)
- Include special characters other than: `+`, `&`, `/`, `#`, `|`, `%`, `(`, `)`

**Compression tactics (use in order):**
1. Drop the category descriptor first — it duplicates the browse node
2. Move trust signals and certifications to Item Highlights
3. Use abbreviations for units and counts
4. Consolidate benefit claims — keep the strongest one, move secondary claims to Item Highlights
5. Move compatibility details to Item Highlights unless they are the primary search filter (e.g., "for iPhone 15")
6. Trim flavor/color from title if the product has a variation page with that attribute already (but keep it if it's a single-variant listing)

## Step 5 — Build Item Highlights

Item Highlights should:
- Pick up everything dropped from the title that is still searchable and conversion-relevant
- Not repeat what is already in the title
- Read as a natural, useful string — not a keyword dump
- Stay at or under 125 characters
- Lead with the highest-conversion overflow content (certifications, origin, secondary ingredients, key claims)

## Step 6 — Output

**Single listing:**
```
TITLE ([X]/75 chars):
[New title]

ITEM HIGHLIGHTS ([X]/125 chars):
[Item Highlights string]

WHAT MOVED AND WHY:
- [Component]: moved to Item Highlights — [reason]
- [Component]: dropped — [reason]

ORIGINAL ([X] chars):
[Original title]
```

**Batch:**
Output a numbered block per listing using the same format, then a summary table:

```
| # | ASIN | Category | Orig Chars | New Title Chars | IH Chars |
|---|------|----------|------------|-----------------|----------|
| 1 | ... | ... | 162 | 71 | 98 |
```

## When to Ask Questions

Ask only if:
- The listing URL is blocked, returns no breadcrumb, and the category cannot be inferred from the title
- The original title is missing a key piece of information that would materially change compression choices (e.g., no count/size visible anywhere)
- A batch input has formatting that cannot be auto-parsed into title + URL pairs

Do not ask permission to proceed. Do not ask the user to verify the category if you can read it from the breadcrumb.

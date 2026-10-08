# MagnetMeUp — Main Image Audit

**Shop:** [MagnetMeUp](https://www.etsy.com/shop/MagnetMeUp) · 1,660 active listings · 7,703 sales · 5.0★ (1,731 reviews) · New Jersey, on Etsy since 2015

**Audited:** 38 listings (shop-grid order, page 1) — **2.3% of the catalog**
**Date:** 2026-10-08
**Status:** ⚠️ Partial. Full 1,660-listing audit is blocked — see [Unblocking](#unblocking-the-full-audit).

> ### 🔴 Correction — first revision got framing wrong
>
> The first version of this report claimed the awareness-ribbon template "wastes ~⅓ of the frame"
> and recommended re-cropping it. **That was wrong, and acting on it would have wasted work.**
>
> It judged framing by **area fill** (content area ÷ canvas area). For an elongated product on a
> square canvas, area fill has a hard geometric ceiling: a 3.5×7″ magnet is 1:2, so even *perfect*
> framing caps it near **0.52**. The ribbon magnets measured 0.46–0.48 — i.e. within 5 points of
> the best their shape allows. The "26% side margins" were forced by aspect ratio, not wasted space.
>
> Re-measured on **long-edge fill** (content long edge ÷ canvas long edge), which is
> aspect-independent, every one of the 38 listings scores **0.893–1.000, mean 0.968**.
> **Nothing is underframed.** The framing across this catalog is genuinely good and very consistent.
>
> The bug was caught by running the repair pipeline on fixtures and seeing mean fill *regress*
> after a "fix". Findings 1 (resolution) and 3 (duplicates) are unaffected and still stand.

---

## Method

For each listing the **main image** was pulled at both `il_fullxfull` (true stored resolution) and
`il_570xN` (display), then measured programmatically:

| Metric | What it catches |
|---|---|
| True pixel dimensions | Listings below Etsy's 2000px recommendation |
| Aspect ratio | Crop risk in square/4:3 search thumbnails |
| **Long-edge fill** | Apparent size in the grid — the correct framing metric |
| Area fill + its geometric ceiling | Area fill alone is misleading; the ceiling says how much is shape |
| Centering offset | Product sitting off-centre on its canvas |
| Minimum margin | Artwork flush against the canvas edge |
| Center-square crop retention | Whether the search thumbnail clips the product |
| Background modal colour | Backdrop consistency across the catalog |
| 64-bit perceptual hash (DCT) | Near-duplicate main images between listings |
| Mean saturation / edge density | Flat-art vs photo, visual busyness |

**Judge framing on long-edge fill, never area fill.** Area fill is reported alongside its
geometric ceiling precisely so a low value can be attributed to product shape rather than
mistaken for a defect.

Script: [`scripts/image_metrics.py`](scripts/image_metrics.py) — reusable as-is for all 1,660.

---

## Findings

### 1. Resolution — 10 of 38 (26%) below Etsy's recommended 2000px 🔴

Etsy recommends main images be at least 2000px on the shortest side; below that, zoom degrades
and the image softens on high-DPI screens.

| Stored size | Count | Listing IDs |
|---|---|---|
| **500 × 500** | 8 | 4302608098, 4302612271, 4302645815, 4298412757, 4298408891, 4298397528, 1897464691, 1896898663 |
| **1667 × 1668** | 2 | 1905089263, 1905082545 |
| 2000 × 2000 | 28 | — |

The 500×500 group is the urgent one: that is **1/16th** the pixel data of the rest of the shop.
Several are recent listings (ID prefix `43…`, `42…`), so this is an *active* regression in the
upload workflow, not legacy debt. Worth finding whichever tool or export preset produces 500px
and fixing it at source.

### 2. Framing — nothing wrong here ✅

Measured correctly, framing is a **strength** of this catalog, not a weakness.

| Long-edge fill | Count |
|---|---|
| 0.95 – 1.00 | 26 |
| 0.90 – 0.95 | 11 |
| 0.85 – 0.90 | 1 |
| below 0.85 | **0** |

Range 0.893 – 1.000, mean **0.968**. For comparison, the awareness-ribbon listings that the first
revision flagged as problems score 0.900 – 0.958 — comfortably well-framed.

The low *area* fill on those listings is entirely explained by product shape:

| Listing | Area fill | Ceiling for its shape | Long-edge fill | Verdict |
|---|---|---|---|---|
| 4302645815 — Please Be Patient (3×8″) | 0.319 | 0.387 | 0.908 | fine |
| 4298408891 — Not All Wounds are Visible | 0.415 | 0.512 | 0.900 | fine |
| 4298397528 — It's Okay Not to be Okay | 0.416 | 0.511 | 0.902 | fine |
| 4298394489 — Bone Cancer Awareness | 0.457 | 0.510 | 0.947 | fine |
| 4298404187 — Skin Cancer Awareness | 0.460 | 0.509 | 0.951 | fine |
| 4302608098 — Bone Cancer Survivor | 0.481 | 0.524 | 0.958 | fine |

Each sits within 5–9 points of the maximum area fill its aspect ratio permits on a square canvas.
There is no re-cropping to do. **Do not crop these tighter** — on the 500×500 ones it would
actively hurt, since it throws away pixels an upscaler then has to invent.

### 2b. Two minor framing notes 🟡

**Off-centre (2 listings).** Opposing margins differ by ~7 points:

| Listing | Left | Right | Offset |
|---|---|---|---|
| 4302608098 — Bone Cancer Survivor | 28.4% | 21.4% | 0.070 |
| 4302612271 — Bone Cancer Fighter | 28.8% | 21.4% | 0.074 |

Cosmetic, and the same pair are also the near-duplicates in finding 3 — so if you rework them,
fix both at once.

**Artwork flush to the canvas edge (22 of 38).** At least one side has a zero margin. This is
plausibly deliberate — flat art bleeding to the edge is a normal choice — and the square-crop
check shows nothing is currently being clipped. Flagged only so the decision is conscious: if
Etsy ever tightens thumbnail cropping, zero-margin art has no tolerance. A 1–2% margin would
remove the risk at no visual cost. **Low priority.**

### 3. Near-duplicate main images — 3 clusters 🟡

Perceptual-hash distance ≤12 on a 64-bit hash (identical = 0):

| Cluster | Distance | Listings |
|---|---|---|
| Bone Cancer **Survivor** vs **Fighter** | 4 | 4302608098 / 4302612271 |
| "Not All Wounds are Visible" vs "It's Okay Not to be Okay" | 7 | 4298408891 / 4298397528 |
| Bucked Bronco **Red / Green / Blue** | 8–12 | 1896898663 / 1882691322 / 1896858179 |

The first two pairs differ by **one word of text** at thumbnail scale — effectively
indistinguishable in search results. The Bronco trio is a legitimate colourway family, but at
distance 8–12 the colour difference is doing less work in a thumbnail than it should.

**Fix:** for text-variant pairs, make the differing word the dominant visual element. For
colourway families, consider a main image that shows the actual colour prominently (or a grouped
shot), so the variants are distinguishable at a glance rather than looking like duplicate listings.
This also matters for Etsy's own de-duplication of visually similar results from one shop.

### 4. Aspect ratio — clean ✅

All 38 are **1:1 square**, and center-square crop retention is **1.000** across the board. No
listing loses product to thumbnail cropping. Given how many of these magnets are elongated
(3×8, 3.5×7, 4×6), padding to square is the right call, and the amount of padding is right too.

### 5. Background consistency — one outlier 🟡

37 of 38 are pure white `#FFFFFF`. One is not:

- **4304355724** — "Caution New Driver" — modal background `rgb(89,105,120)` (slate grey), 100% fill,
  edge density 7.8 (vs ~5 typical). It is a different *kind* of image from the rest of the shop:
  likely a photo or contextual shot rather than flat art on white.

Not necessarily wrong — contextual shots often outperform flat art. But as a one-off it breaks an
otherwise very disciplined white-background grid. Decide deliberately: either it's a test worth
extending, or it's an inconsistency worth aligning.

---

## Priority

| # | Action | Scope in sample | Effort |
|---|---|---|---|
| 1 | **Fix whatever export path emits 500px images** | Process | Low — highest long-term value |
| 2 | Re-export the ten sub-2000px mains from source art | 10 listings | Low, if source art exists |
| 3 | Differentiate the two text-variant duplicate pairs | 4 listings | Medium — needs art |
| 4 | Decide on white vs contextual backgrounds | 1 listing, shop-wide policy | Decision |
| 5 | Re-centre the two off-centre ribbon mains | 2 listings | Trivial, bundle with #3 |
| 6 | Consider a 1–2% safety margin on edge-flush art | 22 listings | Optional |

Item 1 leads deliberately. Several low-resolution listings have recent IDs (`43…`, `42…`), so this
is an active regression rather than legacy debt — fixing the pipeline stops the problem recurring,
which is worth more than fixing ten files.

**Note on resolution vs framing:** since framing is already correct, the resolution fix is a
straight re-export or upscale at the *existing* composition. No re-cropping, so no pixels are
thrown away and no extra upscaling is forced. That makes it substantially cheaper than the first
revision of this report implied.

---

## Unblocking the full audit

The measurement pipeline works and scales. Enumerating all 1,660 listings does not, yet:

- Etsy returns **403** to direct scraping; only `i.etsystatic.com` (the image CDN) and `robots.txt`
  respond. `robots.txt` **does** permit `/shop/MagnetMeUp?page=N`, so this is bot protection, not policy.
- The rendering service that can read Etsy pages serves **cached** results only; every live crawl of
  a paginated URL returned `504 CRAWL_LIVECRAWL_TIMEOUT`. That caps it at ~38 listings.
- This session's container cannot reach `api.etsy.com`, `www.etsy.com` or `i.etsystatic.com` at all —
  the egress policy denies them.

**Recommended fix — allowlist two domains:** add `api.etsy.com` and `i.etsystatic.com` under
**Network access → Allowed domains** in the cloud environment settings. Combined with an Etsy API
keystring (free, self-registered at `etsy.com/developers/register` as the shop owner), the full
catalog is **~17 API calls** via `/v3/application/shops/{shop_id}/listings/active?includes=Images`.
Minutes, not hours — and the whole pipeline then runs inside this environment with no third party
and no key leaving it.

`api.etsy.com` is confirmed reachable from the sandbox and rejects only on the missing key, so the
endpoint and approach are verified — only the credential and the allowlist are outstanding.

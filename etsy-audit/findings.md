# MagnetMeUp — Main Image Audit

**Shop:** [MagnetMeUp](https://www.etsy.com/shop/MagnetMeUp) · 1,660 active listings · 7,703 sales · 5.0★ (1,731 reviews) · New Jersey, on Etsy since 2015

**Audited:** 38 listings (shop-grid order, page 1) — **2.3% of the catalog**
**Date:** 2026-10-08
**Status:** ⚠️ Partial. Full 1,660-listing audit is blocked — see [Unblocking](#unblocking-the-full-audit).

---

## Method

For each listing the **main image** was pulled at both `il_fullxfull` (true stored resolution) and
`il_570xN` (display), then measured programmatically:

| Metric | What it catches |
|---|---|
| True pixel dimensions | Listings below Etsy's 2000px recommendation |
| Aspect ratio | Crop risk in square/4:3 search thumbnails |
| Content bounding box ÷ canvas (`fill`) | Wasted dead space — product reads small in the grid |
| Per-side margins (T/R/B/L) | *Which* direction the dead space sits |
| Center-square crop retention | Whether the search thumbnail clips the product |
| Background modal colour | Backdrop consistency across the catalog |
| 64-bit perceptual hash (DCT) | Near-duplicate main images between listings |
| Mean saturation / edge density | Flat-art vs photo, visual busyness |

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

### 2. Dead space — the awareness-ribbon template wastes ~⅓ of the frame 🔴

Eight listings fill under 55% of their canvas. Seven of those eight are the **3.5×7″ awareness
ribbon** design, and they share a near-identical signature of ~26% empty margin on *both* sides:

| # | Listing | Fill | Left margin | Right margin |
|---|---|---|---|---|
| 6 | 4302645815 — "Please Be Patient I'm Only 8 Years Old" (3×8″) | **31.9%** | 4.6% | 4.6% (⚠️ 30%/34% top/bottom) |
| 9 | 4298408891 — "Not All Wounds are Visible" | 41.5% | 27.2% | 26.7% |
| 10 | 4298397528 — "It's Okay Not to be Okay" | 41.6% | 27.2% | 26.7% |
| 8 | 4298412757 — Mental Health green ribbon heart | 45.8% | 25.6% | 26.1% |
| 11 | 4298394489 — Bone Cancer Awareness | 45.7% | 25.6% | 26.1% |
| 7 | 4298404187 — Skin Cancer Awareness | 46.0% | 25.8% | 25.8% |
| 5 | 4302612271 — Bone Cancer Fighter | 47.7% | 28.8% | 21.4% |
| 4 | 4302608098 — Bone Cancer Survivor | 48.1% | 28.4% | 21.4% |

**Why it matters:** Etsy search renders main images as small thumbnails. A product occupying 42%
of its canvas appears roughly *half the size* of a competitor's that fills 95% — in the same grid,
at the same price. This is the single highest-leverage fix in the audit, because it costs nothing
but a re-crop.

**Fix:** scale the artwork up so the long edge sits at ~92–95% of the canvas, keeping a small even
margin. For an elongated 3.5×7 or 3×8 magnet on a square canvas, either rotate it slightly to use
the diagonal, or shoot/compose it at an angle so it spans more of the frame.

**#6 is the worst case in the set** and fails on a different axis — 30% top *and* 34% bottom
margin, meaning a wide 3×8 bumper magnet is floating in a letterboxed band with only ~32% of the
frame used.

**Extrapolation (unverified):** if this is template-level rather than per-listing, the
**Awareness Ribbons** category (73 listings) is likely affected wholesale, and the 4×6 oval
geometry in **Country Flags and Ovals** (91 listings) may share it. Confirming that is exactly
what the full run is for.

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
(3×8, 3.5×7, 4×6), padding to square is the right call — the issue is *how much* padding, which
is finding #2, not the aspect itself.

### 5. Background consistency — one outlier 🟡

37 of 38 are pure white `#FFFFFF`. One is not:

- **4304355724** — "Caution New Driver" — modal background `rgb(89,105,120)` (slate grey), 100% fill,
  edge density 7.8 (vs ~5 typical). It is a different *kind* of image from the rest of the shop:
  likely a photo or contextual shot rather than flat art on white.

Not necessarily wrong — contextual shots often outperform flat art. But as a one-off it breaks an
otherwise very disciplined white-background grid. Decide deliberately: either it's a test worth
extending, or it's an inconsistency worth aligning.

### 6. Highest-performing framing, for reference ✅

Listings already filling the frame well, useful as the internal standard to copy:

| Listing | Fill |
|---|---|
| 4304355724 — Caution New Driver | 100% |
| 1890426588 — Bucked Bronco 4-pack | 100% |
| 1888851442 — No Elon Face | 98.6% |
| 1897464691 — Cat/Dog Photo Magnet | 98.9% |
| 1905089263 / 1905082545 — Caution Teen Driver | 92.4% |

---

## Priority

| # | Action | Scope in sample | Effort |
|---|---|---|---|
| 1 | Re-crop awareness-ribbon template to ~93% frame fill | 8 listings | Low — one template |
| 2 | Re-upload the eight 500×500 mains at 2000px | 8 listings | Low |
| 3 | Differentiate the two text-variant duplicate pairs | 4 listings | Medium — needs art |
| 4 | Decide on white vs contextual backgrounds | 1 listing, shop-wide policy | Decision |
| 5 | Fix whatever export path emits 500px images | Process | Low, highest long-term value |

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

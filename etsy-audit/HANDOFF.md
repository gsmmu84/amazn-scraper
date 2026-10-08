# Handoff — MagnetMeUp main-image audit

Read this first. It carries the context from a prior cloud session that could not reach
`api.etsy.com` or the user's network share. **You are running on the user's Windows PC and can
reach both**, which is the whole point of the move.

---

## Goal

Audit the main (first) listing image of every active listing in the Etsy shop
**MagnetMeUp** (shop_id `11307494`), find mechanical quality problems, and fix the ones that can
be fixed mechanically. Then help the user test an angled-layout design concept.

The user owns the shop. They are a magnet printing business — they hold print-ready source art
for their designs.

## User context

- On Windows, PowerShell, comfortable copy-pasting commands but **not a developer**.
  Explain what a command does before giving it, and say what good output looks like.
- They asked to "slow down" once already. One step at a time, wait for results.
- Python 3.14.6, `pillow` and `numpy` already installed.

---

## Status

| Done | Not done |
|---|---|
| Tooling written and tested (`scripts/`) | Full catalogue fetch (`--max 5` smoke test passed) |
| Etsy credentials working, ping verified | Image download + `scan` over the catalogue |
| 38-listing sample audited (cloud session) | Local art scan of `\\server\SHARE\...` |
| Angle-variant generator built and tested | Angle test on real art |

### Immediate next step

```powershell
py scripts\etsy_fetch.py --shop MagnetMeUp --out data\listings.tsv
```

~60 requests, 1–3 minutes. Writes `listings.tsv`, `listings.json` (titles, views, favourites,
price, taxonomy, alt text, image dimensions) and `listings-low-res.csv`.

Then:

```powershell
py scripts\image_metrics.py scan --tsv data\listings.tsv --out before.json
```

This downloads ~2,913 images — the slow step. It caches to `.img-cache\` so re-runs are cheap.

### Analysis the user explicitly wants

Using `data\listings.json`:

1. **How many main images are below 2000px**, bucketed by dimension.
2. **Does low resolution correlate with fewer views/favourites?** Same shop, same pricing, so
   it is a reasonable natural experiment. Normalise engagement by listing age
   (`original_creation_timestamp`) — older listings accumulate more views regardless of quality.
   If there is no effect, say so; that result is just as useful and saves them the re-export work.
3. **Does low resolution cluster by age or category** (`taxonomy_id`)? That shows *when* the
   export path broke and whether it is still broken for new listings.
4. **Alt text coverage.** 5 of 5 were empty in the smoke test; likely catalogue-wide.

Be careful with causation here. Low-res listings may be older or in weaker categories. Check
confounders before claiming resolution drives engagement.

---

## Traps — read before writing any analysis

**1. Never judge framing by area fill.** This is the mistake the previous session made and had to
retract. Area fill (content area ÷ canvas area) has a hard geometric ceiling for elongated
products on a square canvas — a 3.5×7″ magnet (1:2) cannot exceed ~0.52 however well it is
framed. Judging by area fill produced a false "the ribbon template wastes a third of the frame"
finding and a recommendation to re-crop ~73 listings that were already correct. Acting on it
would also have *hurt* the 500px ones, since cropping discards pixels an upscaler must invent.

Use **`long_edge_fill`** (content long edge ÷ canvas long edge). It is aspect-independent.
On the 38-listing sample every listing scored 0.893–1.000, mean 0.968. Framing is a **strength**
of this catalogue.

**2. `/shops/{id}/listings/active` silently ignores `includes=Images`.** It returns no image
field at all. Images must come from `/listings/batch?listing_ids=...&includes=Images`, 100 ids
per call. `etsy_fetch.py` already does this in a second pass.

**3. `x-api-key` must be `keystring:shared_secret`**, both halves joined by a colon. A bare
keystring returns *"Shared secret is required in x-api-key header."*

**4. The listing JPGs have drop shadows baked in.** The user's workflow is: print file → delete
cut lines → add drop shadow → export JPG. Consequences:
   - `content_bbox` treats the shadow as product, so measured margins and centering are slightly
     off. Resolution checks are unaffected.
   - **For the angle experiment this matters a lot.** Rotating a flattened image rotates the
     baked-in shadow, so a 45° variant appears lit from a different direction than every other
     listing. Correct order is: unshadowed art → rotate → apply shadow at the standard angle.
     The `angle` command cannot do this; treat its output as a layout mockup, not a shippable file.

**5. The catalogue is ~2,913 active listings, not 1,660.** The lower figure came from a stale
cached shop page. The API is authoritative.

---

## Credentials

Set per PowerShell window (does not persist):

```powershell
$env:ETSY_KEYSTRING = "<keystring>:<shared_secret>"
```

Verify:

```powershell
Invoke-RestMethod -Uri "https://api.etsy.com/v3/application/openapi-ping" -Headers @{"x-api-key"=$env:ETSY_KEYSTRING}
```

An `application_id` means it works.

**Security note to raise with the user.** They pasted a screenshot showing the keystring in full
during the prior session, so it is in that transcript. The app is named
`backend-info-production`, suggesting something live depends on it — so regenerating the key may
break that system. Recommended: create a *separate* app for this audit, and rotate the production
key only after identifying what uses it. Risk is modest (read access to public data plus rate
limit consumption, not account access), so this is "handle it deliberately", not an emergency.
The shared secret was masked and is still safe — keep it that way.

---

## Findings so far (38-listing sample, ~1.3% of catalogue)

Measurement only — nobody has visually reviewed these images. The prior session could not see them.

1. **10 of 38 main images below 2000px** — 8 at 500×500, 2 at 1667×1668. Several have recent
   listing IDs (`43…`, `42…`), so this is an active regression, not legacy debt. Confirmed live:
   listing `1123930616` (Mississippi state flag) is 500×500. **Finding the broken export preset
   is worth more than fixing the files.**
2. **Framing is good.** See trap 1. Nothing underframed.
3. **3 near-duplicate clusters** by DCT perceptual hash. Two pairs differ by a single word of
   text and are indistinguishable at thumbnail size: Bone Cancer *Survivor*/*Fighter*
   (distance 4), "Not All Wounds are Visible"/"It's Okay Not to be Okay" (distance 7).
4. **All 1:1 square, zero crop loss.** Correct for elongated products.
5. **One non-white background** — listing `4304355724`, slate grey, also the busiest image.
   Likely a photo rather than flat art. Possibly their best image; worth a deliberate decision.
6. **2 off-centre** (~7% margin asymmetry), both in the duplicate pair above.

Full detail in `findings.md`. Sample data in `data/metrics.csv`.

---

## The angle experiment

The user wants to test putting elongated magnets on a 45° angle to (a) fill more of the canvas
and (b) stand out in search. Geometry, already worked out and verified empirically:

For a rectangle of aspect *r* inscribed in a square, axis-aligned area is `1/r` and rotated-45
area is `2r/(r+1)²`. These cross at **r ≈ 2.414**. Area dips between 0° and 45°, so only those
two angles are candidates.

| Product | Aspect | Rotation helps area? |
|---|---|---|
| 3×8″ bumper | 2.67 | yes, ~+6% theoretical, +13.5% measured |
| 3.5×7″ ribbon | 2.00 | no, ~9–11% worse |
| 4×6″ oval | 1.50 | no, much worse |
| 5″ round | 1.00 | no |

So it is a bumper-and-longer play, not catalogue-wide. **But area is not the only motive** — at
45° the whitespace becomes four corner triangles instead of two side slabs, which is more
distinctive in a grid of axis-aligned competitors. That can justify less area.

Two observations from rendered comparisons: 15–30° is the worst of both worlds (less area *and*
reads as accidentally crooked), and rotated text is harder to read at thumbnail size — which is
the real risk, since these designs are mostly type.

**Suggested test design:** the catalogue has many near-identical colourway and text variants, which
`scan` already groups as `near_duplicate_clusters`. Rotate one member of a cluster, leave the
other axis-aligned, compare views and favourites over several weeks. Near-identical designs mean
the difference isolates layout rather than artwork. Run several pairs; discard the first week,
since editing a listing disturbs its placement.

---

## Files

```
etsy-audit/
  HANDOFF.md              this file
  README.md               usage, the long-edge-fill explanation, known limits
  findings.md             the audit write-up, including the retracted finding
  data/
    listings.tsv          index / listing_id / main_image_url  (produced by etsy_fetch)
    metrics.csv           38-listing sample measurements
  scripts/
    etsy_fetch.py         enumerate listings + main images via Etsy API v3
    image_metrics.py      scan | crop | compose | angle | compare
```

The user's local copy is a ZIP download at
`C:\Users\Gavriel2\Downloads\amazn-scraper-claude-etsy-main-images-review-s1qbt0\amazn-scraper-claude-etsy-main-images-review-s1qbt0\etsy-audit`.
Working branch is `claude/etsy-main-images-review-s1qbt0` in `gsmmu84/amazn-scraper`. If you clone
fresh, check out that branch — `main` does not have any of this.

Their artwork share: `\\server\SHARE\MagnetMeUp\Magnet Me Up-ALL\` — organised by product size,
e.g. `5 inch round\Image File` holds 90 JPGs. These are post-shadow export files, not raw print
files. Scanning them answers whether source material is good enough to fix the low-res listings.

## Working agreement

Commit to `claude/etsy-main-images-review-s1qbt0`. Do not open a PR unless asked.
Verify before claiming — the area-fill mistake was caught only by running the repair pipeline on
fixtures and noticing the metric got *worse* after a "fix". Test on a handful before a full run;
`--max 5` exists for that reason.

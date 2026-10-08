# Etsy main-image audit

Measures Etsy main images for listing-quality problems, and repairs the ones that are fixable
mechanically. Built for [MagnetMeUp](https://www.etsy.com/shop/MagnetMeUp) but shop-agnostic.

See [`findings.md`](findings.md) for the audit results.

## Install

```bash
pip install pillow numpy
```

`etsy_fetch.py` is stdlib-only. Tested on Python 3.11.

## The one metric that matters

**Judge framing by long-edge fill, not area fill.**

Area fill (content area ÷ canvas area) is misleading for elongated products. A 3.5×7″ magnet is
1:2, so on a square canvas its area fill cannot exceed ~0.52 no matter how well it is framed. Read
area fill as a defect and you will "fix" images that were already correct — and on low-resolution
art, cropping tighter actively makes things worse, because it discards pixels an upscaler must then
invent.

`scan` reports `long_edge_fill` as the primary signal, and prints `area_fill` beside
`area_fill_ceiling` so a low area value can be attributed to shape rather than mistaken for a fault.

## Audit a catalog

Register an app at `etsy.com/developers/create-app` (free). You need **both** values it gives
you — the `x-api-key` header must be `keystring:shared_secret`, joined by a colon. A bare
keystring is rejected with *"Shared secret is required in x-api-key header."* No OAuth is needed
for reading your own shop's public active listings, but the shared secret is.

```bash
export ETSY_KEYSTRING='keystring:shared_secret'
# or, equivalently:
#   export ETSY_KEYSTRING=keystring
#   export ETSY_SHARED_SECRET=shared_secret

python3 scripts/etsy_fetch.py --shop MagnetMeUp --out data/listings.tsv
python3 scripts/image_metrics.py scan --tsv data/listings.tsv --out before.json
```

Windows PowerShell:

```powershell
$env:ETSY_KEYSTRING = "keystring:shared_secret"
py scripts\etsy_fetch.py --shop MagnetMeUp --out data\listings.tsv
```

Check the credentials before a long run:

```bash
curl -s -H "x-api-key: $ETSY_KEYSTRING" https://api.etsy.com/v3/application/openapi-ping
```

An `application_id` in the response means you are good.

1,660 listings is ~17 requests. `etsy_fetch.py` prints sub-2000px listings straight from the API
response, so the worst offenders are visible before anything is downloaded.

**The shared secret is the sensitive half.** Keep it out of screenshots, chat logs, and the
repository. `.gitignore` covers `*.key`, `.env` and the cache/output directories, but prefer an
environment variable or `--key-file` over `--key`, since a value passed on the command line is
written to your shell history.

Or audit local source art directly, which needs no credentials at all:

```bash
python3 scripts/image_metrics.py scan --dir ./art --out before.json
```

## Repair underframed or low-resolution art

Three steps, with your own upscaler in the middle — it will beat anything in this repo.

```bash
# 1. cut away dead margin, keeping native pixels, lossless PNG
python3 scripts/image_metrics.py crop --dir ./art --out ./crops

# 2. run YOUR upscaler on ./crops -> ./crops-up
#    (copy crop-manifest.json across so background colours are preserved)

# 3. rebuild square canvases at the target fill
python3 scripts/image_metrics.py compose --dir ./crops-up --out ./final --size 2000 --fill 0.93

# 4. prove it worked
python3 scripts/image_metrics.py scan --dir ./final --out after.json
python3 scripts/image_metrics.py compare before.json after.json
```

`crop` reports the upscale factor each image needs and marks anything above 3× as aggressive.
`compose` refuses to downscale art that already exceeds the target fill unless you pass
`--allow-shrink`, so running it over a whole folder cannot quietly degrade your good images.

Always run step 4. It is what caught the area-fill bug described in `findings.md`.

## Angled-layout experiment

Renders each design at several rotations so a designer reviews options instead of producing them:

```bash
python3 scripts/image_metrics.py angle --dir ./art --out ./angles --angles 0,15,30,45
```

Writes one JPEG per design per angle, a side-by-side `__compare.jpg` per design, and
`angle-report.json`. Rotation happens at native resolution before downscaling, so edges stay clean.

### Does rotating actually make the product bigger?

Only for genuinely long products. For a rectangle of aspect *r* inscribed in a square:

- axis-aligned area = `1/r`
- rotated 45° area = `2r/(r+1)²`

These cross at **r ≈ 2.414**. Area also *dips* between 0° and 45°, so only those two are
real candidates — intermediate angles are strictly worse on area.

| Product | Aspect | Rotation helps area? |
|---|---|---|
| 3×8″ bumper | 2.67 | ✅ yes |
| 3.5×7″ ribbon | 2.00 | ❌ no, ~9–11% worse |
| 4×6″ oval | 1.50 | ❌ no, much worse |
| Round / square | 1.00 | ❌ no |

Measured on real art the tool reports `+13.5%` ink for a 2.57-aspect bumper at 45°, and `0°` best
for every ribbon — matching the theory. `rotation_predicted_to_help` in the report flags which
designs are even worth testing.

**Area is not the only reason to rotate.** At 45° the whitespace becomes four corner triangles
instead of two side slabs, which reads as more dynamic and more distinctive in a grid of
axis-aligned competitors. That can justify accepting less area — the tool gives you the number so
the trade is explicit rather than assumed.

Two things the sheets make obvious:

- **15°–30° is the worst of both worlds** — less area *and* it reads as accidentally crooked.
  If you angle, commit to 45°.
- **Rotated text is harder to read at thumbnail size.** These designs are mostly type, so this is
  the real risk, not the geometry. Judge legibility on the compare sheets at actual thumbnail
  size before shipping anything.

### Testing it without guessing

Etsy has no native image A/B test, but this catalog has something better: lots of near-identical
colourway and text variants. `scan` already groups them as `near_duplicate_clusters`.

Use them as matched pairs — rotate one member of a cluster, leave the other axis-aligned, and
compare views and favourites over several weeks. Because the designs are near-identical, the
difference isolates the layout rather than the artwork. Run several pairs at once; a single pair
will not clear the noise.

Give it time. Editing a listing can disturb its search placement briefly, so discard the first
week or so rather than reading it as a result.

## Commands

| Command | Purpose |
|---|---|
| `scan --dir` / `scan --tsv` | Measure local images, or download and measure from a listings TSV |
| `crop` | Tight content crops at native resolution, ready for an external upscaler |
| `compose` | Pad crops onto a square canvas at a target long-edge fill |
| `angle` | Render rotated variants + compare sheets for the scroll-stopping test |
| `compare` | Diff two `metrics.json` files, before vs after |

`scan` writes `metrics.json` (full per-image data plus flag sets) and a flat `metrics.csv`.

## Flags `scan` raises

| Flag | Meaning |
|---|---|
| `low_resolution` | Short edge below 2000px (`--min-px`) |
| `underframed` | Long-edge fill below 0.85 (`--fill`) — genuinely badly framed |
| `needs_crop_and_upscale` | Underframed *and* low-res; reports the upscale factor required |
| `off_centre` | Opposing margins differ by more than 0.05 |
| `touching_edge` | Artwork flush to a canvas edge, no cropping tolerance |
| `aspect_constrained` | Low area fill explained by product shape — **not a defect** |
| `crop_loss` | Content lost to a centre-square crop |
| `near_duplicate_clusters` | Main images within pHash Hamming distance 12 |
| `background_colours` | Distinct backdrop colours, for consistency checking |

## Known limits

- **Measurement, not art direction.** It can tell you an image is soft, off-centre or duplicated.
  It cannot tell you the typography is bad. Look at the images yourself.
- **Background detection assumes a flat backdrop.** Content bounds come from the median border
  colour, which is reliable for product art on white and unreliable for busy photographic
  backgrounds. `area_fill` near 1.0 with high `edge_density` usually means a photo, not a tight crop.
- **pHash flags visual similarity, not wrongness.** Colourway families legitimately cluster;
  judge each cluster on whether the variants are distinguishable at thumbnail size.
- Alpha channels are flattened onto the detected background before measuring, so transparent PNG
  source art measures the same as the exported JPEG.

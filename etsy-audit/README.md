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

With an Etsy API keystring (free, self-registered at `etsy.com/developers/create-app`; reading a
shop's public active listings needs no OAuth and no shared secret):

```bash
export ETSY_KEYSTRING=xxxxxxxxxxxxxxxxxxxxxxxx

python3 scripts/etsy_fetch.py --shop MagnetMeUp --out data/listings.tsv
python3 scripts/image_metrics.py scan --tsv data/listings.tsv --out before.json
```

1,660 listings is ~17 requests. `etsy_fetch.py` prints sub-2000px listings straight from the API
response, so the worst offenders are visible before anything is downloaded.

Never commit the keystring — `.gitignore` covers `*.key`, `.env` and the cache/output directories.

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

## Commands

| Command | Purpose |
|---|---|
| `scan --dir` / `scan --tsv` | Measure local images, or download and measure from a listings TSV |
| `crop` | Tight content crops at native resolution, ready for an external upscaler |
| `compose` | Pad crops onto a square canvas at a target long-edge fill |
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

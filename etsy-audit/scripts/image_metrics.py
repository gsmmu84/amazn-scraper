#!/usr/bin/env python3
"""Measure Etsy main images for listing-quality problems.

Reads a TSV of `index<TAB>listing_id<TAB>image_url`, downloads each main image at
full and display resolution, and emits per-listing metrics plus flagged outliers.

Designed to scale to a full catalog: the only per-listing input is the main image
URL, which the Etsy API returns directly via
    /v3/application/shops/{shop_id}/listings/active?includes=Images

Usage:
    python3 image_metrics.py listings.tsv --out metrics.json [--workers 8]

Requires: pillow, numpy
"""
import argparse
import itertools
import json
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

# Etsy recommends main images be >= 2000px on the short side.
MIN_RECOMMENDED_PX = 2000
# Below this fraction of canvas filled, the product reads small in search.
LOW_FILL_THRESHOLD = 0.55
# A single side margin above this is wasted frame.
WIDE_MARGIN_THRESHOLD = 0.18
# Perceptual-hash Hamming distance at or below which two mains are near-duplicates.
DUPE_DISTANCE = 12


def dct2(a):
    """2-D DCT-II, normalised on the DC row (avoids a scipy dependency)."""
    n = a.shape[0]
    k = np.arange(n)
    basis = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
    basis[0] *= 1 / np.sqrt(2)
    return basis @ a @ basis.T


def phash(im, size=8):
    """64-bit DCT perceptual hash as a bit string."""
    grey = np.asarray(im.convert("L").resize((32, 32), Image.LANCZOS), dtype=float)
    low = dct2(grey)[:size, :size]
    # Exclude the DC term from the median so flat-vs-busy doesn't dominate.
    median = np.median(low.flatten()[1:])
    return "".join("1" if b else "0" for b in (low > median).flatten())


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def content_bbox(arr, tol=12):
    """Bounding box of non-background content.

    Background is the median colour of the 1px border, which is reliable for
    product art composited on a flat backdrop.
    """
    h, w, _ = arr.shape
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    bg = np.median(border, axis=0)
    mask = np.abs(arr.astype(int) - bg.astype(int)).sum(axis=2) > tol * 3
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if not len(rows) or not len(cols):
        return (0, 0, w, h), bg, 0.0
    return (cols[0], rows[0], cols[-1] + 1, rows[-1] + 1), bg, float(mask.mean())


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 2048:
        return True
    r = subprocess.run(
        ["curl", "-sS", "-m", "30", "-o", str(dest), url],
        capture_output=True,
    )
    return r.returncode == 0 and dest.exists() and dest.stat().st_size > 2048


def measure(idx, listing_id, url, cache):
    """Download one listing's main image and measure it."""
    # il_fullxfull gives true stored resolution; il_570xN is cheap to analyse.
    full_url = url.replace("il_340x270.", "il_fullxfull.")
    disp_url = url.replace("il_340x270.", "il_570xN.")
    full_p = cache / "full" / f"{idx:05d}.jpg"
    disp_p = cache / "disp" / f"{idx:05d}.jpg"

    if not (fetch(full_url, full_p) and fetch(disp_url, disp_p)):
        return {"i": idx, "listing_id": listing_id, "error": "download_failed"}

    try:
        with Image.open(full_p) as imf:
            true_w, true_h = imf.size
        im = Image.open(disp_p).convert("RGB")
    except Exception as exc:  # corrupt or non-image payload
        return {"i": idx, "listing_id": listing_id, "error": f"decode: {exc}"}

    arr = np.asarray(im)
    (x0, y0, x1, y1), bg, ink = content_bbox(arr)
    w, h = im.size
    cw, ch = x1 - x0, y1 - y0

    # Etsy search crops toward a square; measure how much content survives.
    side = min(w, h)
    sx, sy = (w - side) // 2, (h - side) // 2
    keep_x = max(0, min(x1, sx + side) - max(x0, sx))
    keep_y = max(0, min(y1, sy + side) - max(y0, sy))
    sq_kept = (keep_x * keep_y) / max(1, cw * ch)

    hsv = np.asarray(im.convert("HSV"), dtype=float)
    grey = np.asarray(im.convert("L"), dtype=float)
    edge = (np.abs(np.diff(grey, axis=1)).mean() + np.abs(np.diff(grey, axis=0)).mean()) / 2

    return {
        "i": idx,
        "listing_id": listing_id,
        "true_w": true_w,
        "true_h": true_h,
        "aspect": round(true_w / true_h, 3),
        "megapixels": round(true_w * true_h / 1e6, 2),
        "bbox_fill": round((cw * ch) / (w * h), 3),
        "ink_fraction": round(ink, 3),
        "margins": {
            "top": round(y0 / h, 3),
            "right": round((w - x1) / w, 3),
            "bottom": round((h - y1) / h, 3),
            "left": round(x0 / w, 3),
        },
        "square_crop_kept": round(sq_kept, 3),
        "saturation": round(hsv[:, :, 1].mean() / 255, 3),
        "brightness": round(hsv[:, :, 2].mean() / 255, 3),
        "edge_density": round(float(edge), 1),
        "bg_rgb": [int(v) for v in bg],
        "phash": phash(im),
    }


def flag(rows):
    """Reduce per-listing metrics to the actionable outlier sets."""
    ok = [r for r in rows if "error" not in r]

    clusters = []
    pairs = [
        (hamming(a["phash"], b["phash"]), a["listing_id"], b["listing_id"])
        for a, b in itertools.combinations(ok, 2)
        if hamming(a["phash"], b["phash"]) <= DUPE_DISTANCE
    ]
    if pairs:
        parent = {r["listing_id"]: r["listing_id"] for r in ok}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for _, a, b in pairs:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        groups = defaultdict(list)
        for r in ok:
            groups[find(r["listing_id"])].append(r["listing_id"])
        clusters = [sorted(v) for v in groups.values() if len(v) > 1]

    return {
        "audited": len(rows),
        "failed": [r for r in rows if "error" in r],
        "low_resolution": [
            {"listing_id": r["listing_id"], "size": f"{r['true_w']}x{r['true_h']}"}
            for r in ok
            if min(r["true_w"], r["true_h"]) < MIN_RECOMMENDED_PX
        ],
        "low_frame_fill": [
            {"listing_id": r["listing_id"], "fill": r["bbox_fill"]}
            for r in sorted(ok, key=lambda r: r["bbox_fill"])
            if r["bbox_fill"] < LOW_FILL_THRESHOLD
        ],
        "wide_margins": [
            {"listing_id": r["listing_id"], "margins": r["margins"]}
            for r in ok
            if max(r["margins"].values()) > WIDE_MARGIN_THRESHOLD
        ],
        "crop_loss": [
            {"listing_id": r["listing_id"], "kept": r["square_crop_kept"]}
            for r in ok
            if r["square_crop_kept"] < 0.98
        ],
        "background_colours": sorted({tuple(r["bg_rgb"]) for r in ok}),
        "near_duplicate_pairs": sorted(pairs),
        "near_duplicate_clusters": sorted(clusters),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tsv", help="index<TAB>listing_id<TAB>main_image_url per line")
    ap.add_argument("--out", default="metrics.json")
    ap.add_argument("--cache", default=".img-cache")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    cache = Path(args.cache)
    jobs = []
    for line in Path(args.tsv).read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        idx, listing_id, url = line.split(None, 2)
        jobs.append((int(idx), listing_id, url.strip()))

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda j: measure(*j, cache), jobs))
    rows.sort(key=lambda r: r["i"])

    report = {"metrics": rows, "flags": flag(rows)}
    Path(args.out).write_text(json.dumps(report, indent=1))

    f = report["flags"]
    print(f"audited={f['audited']} failed={len(f['failed'])}", file=sys.stderr)
    print(f"low_resolution={len(f['low_resolution'])}", file=sys.stderr)
    print(f"low_frame_fill={len(f['low_frame_fill'])}", file=sys.stderr)
    print(f"near_duplicate_clusters={len(f['near_duplicate_clusters'])}", file=sys.stderr)


if __name__ == "__main__":
    main()

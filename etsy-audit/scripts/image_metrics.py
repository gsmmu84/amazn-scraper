#!/usr/bin/env python3
"""Audit and repair Etsy main images.

Subcommands
-----------
scan      Measure images (local folder, or a TSV of listing_id/URL) -> metrics.json + CSV
crop      Emit tight content crops at native resolution, ready for an external upscaler
compose   Pad (optionally upscaled) crops back onto a square canvas at a target frame fill
compare   Diff two metrics.json files, before vs after

Typical local workflow for the low-frame-fill / low-resolution findings:

    # 1. measure what you have
    python3 image_metrics.py scan --dir ./art --out before.json

    # 2. cut away the dead margin, keeping native pixels
    python3 image_metrics.py crop --dir ./art --out ./crops

    # 3. run YOUR upscaler on ./crops -> ./crops-2x  (better than anything here)

    # 4. rebuild square 2000px canvases at 93% fill
    python3 image_metrics.py compose --dir ./crops-2x --out ./final --size 2000 --fill 0.93

    # 5. confirm it worked
    python3 image_metrics.py scan --dir ./final --out after.json
    python3 image_metrics.py compare before.json after.json

Requires: pillow, numpy
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None  # print-resolution source art is legitimately huge

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}

# Etsy recommends main images be >= 2000px on the short side.
MIN_RECOMMENDED_PX = 2000
# Primary framing metric: content's long edge as a fraction of the canvas's long edge.
#
# NOTE: do NOT judge framing by area fill. An elongated product on a square canvas
# has a hard geometric ceiling -- a 3.5x7in magnet (1:2) tops out near 0.43 area fill
# even when perfectly framed, because the side margins are forced by its aspect ratio.
# Long-edge fill is aspect-independent and is what actually drives apparent size in
# the search grid.
LOW_LONG_EDGE_FILL = 0.85
# Opposing margins differing by more than this means the product sits off-centre.
OFF_CENTRE_THRESHOLD = 0.05
# A margin below this means content is touching the canvas edge, with no breathing room.
TOUCHING_EDGE_THRESHOLD = 0.005
# Perceptual-hash Hamming distance at or below which two mains are near-duplicates.
DUPE_DISTANCE = 12
# Analysis is done at this size; full-resolution pixel counts come from the header.
ANALYSIS_PX = 570


# ---------------------------------------------------------------- measurement


def dct2(a: np.ndarray) -> np.ndarray:
    """2-D DCT-II, normalised on the DC row (avoids a scipy dependency)."""
    n = a.shape[0]
    k = np.arange(n)
    basis = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
    basis[0] *= 1 / np.sqrt(2)
    return basis @ a @ basis.T


def phash(im: Image.Image, size: int = 8) -> str:
    """64-bit DCT perceptual hash as a bit string."""
    grey = np.asarray(im.convert("L").resize((32, 32), Image.LANCZOS), dtype=float)
    low = dct2(grey)[:size, :size]
    # Exclude the DC term so flat-vs-busy doesn't dominate the comparison.
    median = np.median(low.flatten()[1:])
    return "".join("1" if b else "0" for b in (low > median).flatten())


def hamming(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


def flatten_alpha(im: Image.Image, bg=(255, 255, 255)) -> Image.Image:
    """Composite transparency onto a flat background.

    Source art is often PNG with an alpha channel; measuring it without
    flattening makes the whole canvas read as 'content'.
    """
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        canvas = Image.new("RGB", im.size, bg)
        canvas.paste(im, mask=im.split()[-1])
        return canvas
    return im.convert("RGB")


def content_bbox(arr: np.ndarray, tol: int = 12):
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
    return (int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1), bg, float(mask.mean())


def measure_image(path: Path, label: str) -> dict:
    """Measure one image file. Returns a metrics dict, or an error dict."""
    try:
        with Image.open(path) as probe:
            true_w, true_h = probe.size
            probe.load()
            im = flatten_alpha(probe)
    except Exception as exc:
        return {"id": label, "path": str(path), "error": f"decode: {exc}"}

    # Analyse at a consistent size so thresholds mean the same thing everywhere.
    if max(im.size) > ANALYSIS_PX:
        scale = ANALYSIS_PX / max(im.size)
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)

    arr = np.asarray(im)
    (x0, y0, x1, y1), bg, ink = content_bbox(arr)
    w, h = im.size
    cw, ch = x1 - x0, y1 - y0

    # Etsy crops toward a square in search; measure how much content survives.
    side = min(w, h)
    sx, sy = (w - side) // 2, (h - side) // 2
    keep_x = max(0, min(x1, sx + side) - max(x0, sx))
    keep_y = max(0, min(y1, sy + side) - max(y0, sy))
    sq_kept = (keep_x * keep_y) / max(1, cw * ch)

    hsv = np.asarray(im.convert("HSV"), dtype=float)
    grey = np.asarray(im.convert("L"), dtype=float)
    edge = (np.abs(np.diff(grey, axis=1)).mean() + np.abs(np.diff(grey, axis=0)).mean()) / 2

    # Native pixels actually occupied by artwork -- what an upscaler has to work with.
    content_native_w = round(cw / w * true_w)
    content_native_h = round(ch / h * true_h)

    mt, mr = y0 / h, (w - x1) / w
    mb, ml = (h - y1) / h, x0 / w

    # Aspect-independent framing: how much of the canvas's long edge the product spans.
    long_edge_fill = max(cw, ch) / max(w, h)
    # The best area fill this product's aspect ratio permits on this canvas.
    content_aspect = cw / ch if ch else 1.0
    canvas_aspect = w / h if h else 1.0
    ratio = (content_aspect / canvas_aspect) if content_aspect > canvas_aspect else (canvas_aspect / content_aspect)
    area_fill_ceiling = 1.0 / ratio if ratio else 1.0

    return {
        "id": label,
        "path": str(path),
        "true_w": true_w,
        "true_h": true_h,
        "aspect": round(true_w / true_h, 3),
        "megapixels": round(true_w * true_h / 1e6, 2),
        "long_edge_fill": round(long_edge_fill, 3),
        "bbox_fill": round((cw * ch) / (w * h), 3),
        "area_fill_ceiling": round(area_fill_ceiling, 3),
        "content_aspect": round(content_aspect, 3),
        "centering_offset": round(max(abs(ml - mr), abs(mt - mb)), 3),
        "min_margin": round(min(mt, mr, mb, ml), 3),
        "ink_fraction": round(ink, 3),
        "margins": {
            "top": round(mt, 3),
            "right": round(mr, 3),
            "bottom": round(mb, 3),
            "left": round(ml, 3),
        },
        "content_native": [content_native_w, content_native_h],
        "square_crop_kept": round(sq_kept, 3),
        "saturation": round(float(hsv[:, :, 1].mean()) / 255, 3),
        "brightness": round(float(hsv[:, :, 2].mean()) / 255, 3),
        "edge_density": round(float(edge), 1),
        "bg_rgb": [int(v) for v in bg],
        "phash": phash(im),
    }


# --------------------------------------------------------------------- inputs


def iter_local(directory: Path):
    for p in sorted(directory.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES:
            yield p, p.relative_to(directory).as_posix()


def fetch_url(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 2048:
        return True
    subprocess.run(["curl", "-sS", "-m", "30", "-o", str(dest), url], capture_output=True)
    return dest.exists() and dest.stat().st_size > 2048


def iter_tsv(tsv: Path, cache: Path, workers: int):
    """TSV lines: index<TAB>listing_id<TAB>main_image_url."""
    jobs = []
    for line in tsv.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        idx, listing_id, url = parts
        # Ask the CDN for the largest stored rendition.
        url = url.strip().replace("il_340x270.", "il_fullxfull.").replace("il_570xN.", "il_fullxfull.")
        jobs.append((listing_id, url, cache / f"{listing_id}.jpg"))

    def pull(job):
        listing_id, url, dest = job
        return (dest, listing_id) if fetch_url(url, dest) else (None, listing_id)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for dest, listing_id in pool.map(pull, jobs):
            if dest is None:
                print(f"  download failed: {listing_id}", file=sys.stderr)
                continue
            yield dest, listing_id


# ---------------------------------------------------------------------- flags


def build_flags(rows: list[dict], min_px: int, fill_threshold: float, target_fill: float = 0.93) -> dict:
    ok = [r for r in rows if "error" not in r]

    pairs = []
    for a, b in itertools.combinations(ok, 2):
        d = hamming(a["phash"], b["phash"])
        if d <= DUPE_DISTANCE:
            pairs.append([d, a["id"], b["id"]])

    clusters = []
    if pairs:
        parent = {r["id"]: r["id"] for r in ok}

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
            groups[find(r["id"])].append(r["id"])
        clusters = sorted([sorted(v) for v in groups.values() if len(v) > 1])

    low_res = [r for r in ok if min(r["true_w"], r["true_h"]) < min_px]
    # Framing is judged on long-edge fill, which is aspect-independent.
    underframed = sorted(
        [r for r in ok if r["long_edge_fill"] < fill_threshold],
        key=lambda r: r["long_edge_fill"],
    )

    # Where the two fixes fight: cropping tighter costs pixels an upscaler must invent.
    both = sorted(
        [r for r in underframed if min(r["true_w"], r["true_h"]) < min_px],
        key=lambda r: r["long_edge_fill"],
    )

    return {
        "audited": len(rows),
        "failed": [r for r in rows if "error" in r],
        "low_resolution": [
            {"id": r["id"], "size": f"{r['true_w']}x{r['true_h']}"} for r in low_res
        ],
        "underframed": [
            {
                "id": r["id"],
                "long_edge_fill": r["long_edge_fill"],
                "headroom": round(target_fill - r["long_edge_fill"], 3),
            }
            for r in underframed
        ],
        "needs_crop_and_upscale": [
            {
                "id": r["id"],
                "long_edge_fill": r["long_edge_fill"],
                "content_native": r["content_native"],
                # Upscale factor to reach target fill of a min_px canvas from real pixels.
                "upscale_needed": round(
                    (min_px * target_fill) / max(1, max(r["content_native"])), 2
                ),
            }
            for r in both
        ],
        "off_centre": [
            {"id": r["id"], "offset": r["centering_offset"], "margins": r["margins"]}
            for r in sorted(ok, key=lambda r: -r["centering_offset"])
            if r["centering_offset"] > OFF_CENTRE_THRESHOLD
        ],
        "touching_edge": [
            {"id": r["id"], "min_margin": r["min_margin"]}
            for r in ok
            if r["min_margin"] < TOUCHING_EDGE_THRESHOLD
        ],
        "aspect_constrained": [
            # Area fill looks bad here purely because of product shape -- not a defect.
            {
                "id": r["id"],
                "content_aspect": r["content_aspect"],
                "area_fill": r["bbox_fill"],
                "area_fill_ceiling": r["area_fill_ceiling"],
                "long_edge_fill": r["long_edge_fill"],
            }
            for r in ok
            if r["bbox_fill"] < 0.55 and r["long_edge_fill"] >= fill_threshold
        ],
        "crop_loss": [
            {"id": r["id"], "kept": r["square_crop_kept"]} for r in ok if r["square_crop_kept"] < 0.98
        ],
        "background_colours": sorted({tuple(r["bg_rgb"]) for r in ok}),
        "near_duplicate_pairs": sorted(pairs),
        "near_duplicate_clusters": clusters,
    }


def write_csv(rows: list[dict], dest: Path) -> None:
    ok = [r for r in rows if "error" not in r]
    if not ok:
        return
    cols = [
        "id", "true_w", "true_h", "aspect", "megapixels",
        "long_edge_fill", "area_fill", "area_fill_ceiling", "content_aspect",
        "centering_offset", "min_margin", "square_crop_kept",
        "saturation", "brightness", "edge_density",
        "margin_top", "margin_right", "margin_bottom", "margin_left",
        "content_native_w", "content_native_h", "bg_rgb",
    ]
    with dest.open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(cols)
        for r in ok:
            wr.writerow([
                r["id"], r["true_w"], r["true_h"], r["aspect"], r["megapixels"],
                r["long_edge_fill"], r["bbox_fill"], r["area_fill_ceiling"],
                r["content_aspect"], r["centering_offset"], r["min_margin"],
                r["square_crop_kept"], r["saturation"], r["brightness"],
                r["edge_density"], r["margins"]["top"], r["margins"]["right"],
                r["margins"]["bottom"], r["margins"]["left"],
                r["content_native"][0], r["content_native"][1],
                ";".join(str(v) for v in r["bg_rgb"]),
            ])


# ----------------------------------------------------------------- subcommands


def cmd_scan(args) -> None:
    rows = []
    if args.dir:
        sources = list(iter_local(Path(args.dir)))
        print(f"scanning {len(sources)} local images", file=sys.stderr)
    else:
        cache = Path(args.cache)
        sources = list(iter_tsv(Path(args.tsv), cache, args.workers))
        print(f"scanning {len(sources)} downloaded images", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda s: measure_image(s[0], s[1]), sources))

    flags = build_flags(rows, args.min_px, args.fill, args.target_fill)
    out = Path(args.out)
    out.write_text(json.dumps({"metrics": rows, "flags": flags}, indent=1))
    write_csv(rows, out.with_suffix(".csv"))

    print(f"\n  audited                     {flags['audited']}", file=sys.stderr)
    print(f"  decode failures             {len(flags['failed'])}", file=sys.stderr)
    print(f"  below {args.min_px}px                {len(flags['low_resolution'])}", file=sys.stderr)
    print(f"  underframed (<{args.fill} long edge) {len(flags['underframed'])}", file=sys.stderr)
    print(f"  need crop + upscale         {len(flags['needs_crop_and_upscale'])}", file=sys.stderr)
    print(f"  off-centre                  {len(flags['off_centre'])}", file=sys.stderr)
    print(f"  content touching edge       {len(flags['touching_edge'])}", file=sys.stderr)
    print(f"  duplicate clusters          {len(flags['near_duplicate_clusters'])}", file=sys.stderr)
    if flags["aspect_constrained"]:
        print(
            f"  low area fill BY SHAPE      {len(flags['aspect_constrained'])}  "
            "(framed fine; elongated product on a square canvas -- not a defect)",
            file=sys.stderr,
        )
    print(f"\nwrote {out} and {out.with_suffix('.csv')}", file=sys.stderr)

    worst = flags["needs_crop_and_upscale"][:10]
    if worst:
        print("\ngenuinely underframed AND low-res (crop tighter + upscale):", file=sys.stderr)
        for r in worst:
            cw, ch = r["content_native"]
            print(
                f"  {r['id']:<40} long_edge={r['long_edge_fill']:<6} "
                f"art={cw}x{ch}px  needs ~{r['upscale_needed']}x",
                file=sys.stderr,
            )
    if flags["off_centre"][:8]:
        print("\noff-centre (opposing margins differ):", file=sys.stderr)
        for r in flags["off_centre"][:8]:
            m = r["margins"]
            print(
                f"  {r['id']:<40} offset={r['offset']:<6} "
                f"T{m['top']} R{m['right']} B{m['bottom']} L{m['left']}",
                file=sys.stderr,
            )


def cmd_crop(args) -> None:
    """Emit tight content crops at native resolution for external upscaling."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    n = 0

    for path, label in iter_local(Path(args.dir)):
        try:
            with Image.open(path) as probe:
                probe.load()
                full = flatten_alpha(probe)
        except Exception as exc:
            print(f"  skip {label}: {exc}", file=sys.stderr)
            continue

        small = full
        if max(full.size) > ANALYSIS_PX:
            s = ANALYSIS_PX / max(full.size)
            small = full.resize((round(full.width * s), round(full.height * s)), Image.LANCZOS)
        (x0, y0, x1, y1), bg, _ = content_bbox(np.asarray(small))

        # Map the bbox back to full resolution, with a small safety pad.
        fx, fy = full.width / small.width, full.height / small.height
        pad = args.pad
        bx0 = max(0, int(x0 * fx) - pad)
        by0 = max(0, int(y0 * fy) - pad)
        bx1 = min(full.width, int(x1 * fx) + pad)
        by1 = min(full.height, int(y1 * fy) + pad)
        if bx1 - bx0 < 8 or by1 - by0 < 8:
            print(f"  skip {label}: no content found", file=sys.stderr)
            continue

        crop = full.crop((bx0, by0, bx1, by1))
        dest = out / (Path(label).stem + ".png")
        crop.save(dest, "PNG")  # lossless, so the upscaler sees no JPEG artefacts
        target = round(args.size * args.fill)
        manifest[dest.name] = {
            "source": label,
            "crop_px": [crop.width, crop.height],
            "bg_rgb": [int(v) for v in bg],
            "upscale_needed": round(target / max(crop.size), 2),
        }
        n += 1

    (out / "crop-manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {n} crops to {out}", file=sys.stderr)

    hot = sorted(manifest.items(), key=lambda kv: -kv[1]["upscale_needed"])[:10]
    if hot:
        print(f"\nupscale factor needed to reach {args.fill:.0%} of {args.size}px:", file=sys.stderr)
        for name, m in hot:
            w, h = m["crop_px"]
            warn = "  <-- aggressive" if m["upscale_needed"] > 3 else ""
            print(f"  {name:<40} {w}x{h}px  ~{m['upscale_needed']}x{warn}", file=sys.stderr)
    print("\nnext: run your upscaler on these, then `compose` the results.", file=sys.stderr)


def cmd_compose(args) -> None:
    """Pad crops onto a square canvas at a target frame fill."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.dir) / "crop-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    size, fill = args.size, args.fill
    n = 0

    for path, label in iter_local(Path(args.dir)):
        try:
            with Image.open(path) as probe:
                probe.load()
                crop = flatten_alpha(probe)
        except Exception as exc:
            print(f"  skip {label}: {exc}", file=sys.stderr)
            continue

        meta = manifest.get(Path(label).name, {})
        bg = tuple(meta.get("bg_rgb", [255, 255, 255]))

        target = size * fill
        scale = target / max(crop.size)
        # Never silently throw away detail from art that is already big enough.
        if scale < 0.98 and not args.allow_shrink:
            print(
                f"  keep {label}: already {max(crop.size)}px on the long edge; "
                f"scaling to {fill:.0%} would shrink it {scale:.2f}x (--allow-shrink to force)",
                file=sys.stderr,
            )
            scale = min(1.0, size / max(crop.size))
        elif scale > 1.02:
            print(
                f"  note {label}: scaling up {scale:.2f}x in Pillow -- "
                "run your upscaler first for better results",
                file=sys.stderr,
            )
        new = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
        resized = crop.resize(new, Image.LANCZOS)

        canvas = Image.new("RGB", (size, size), bg)
        canvas.paste(resized, ((size - new[0]) // 2, (size - new[1]) // 2))
        dest = out / (Path(label).stem + ".jpg")
        canvas.save(dest, "JPEG", quality=args.quality, optimize=True, subsampling=0)
        n += 1

    print(f"composed {n} images at {size}x{size}, {fill:.0%} fill -> {out}", file=sys.stderr)


def cmd_compare(args) -> None:
    before = json.loads(Path(args.before).read_text())
    after = json.loads(Path(args.after).read_text())

    def index(doc):
        return {Path(r["id"]).stem: r for r in doc["metrics"] if "error" not in r}

    b, a = index(before), index(after)
    shared = sorted(set(b) & set(a))
    if not shared:
        print("no matching ids between the two files", file=sys.stderr)
        return

    print(f"{'id':<38} {'long-edge fill':>18}  {'short edge':>18}", file=sys.stderr)
    print("-" * 78, file=sys.stderr)
    gained = regressed = 0
    for k in shared:
        bf, af = b[k]["long_edge_fill"], a[k]["long_edge_fill"]
        bp, ap = min(b[k]["true_w"], b[k]["true_h"]), min(a[k]["true_w"], a[k]["true_h"])
        mark = "+" if af > bf + 0.02 else ("-" if af < bf - 0.02 else " ")
        gained += af > bf + 0.02
        regressed += af < bf - 0.02
        print(
            f"{k[:37]:<38} {bf:>7.3f} -> {af:<7.3f} {mark}  {bp:>7} -> {ap:<7}",
            file=sys.stderr,
        )

    bavg = sum(b[k]["long_edge_fill"] for k in shared) / len(shared)
    aavg = sum(a[k]["long_edge_fill"] for k in shared) / len(shared)
    blow = sum(1 for k in shared if min(b[k]["true_w"], b[k]["true_h"]) < MIN_RECOMMENDED_PX)
    alow = sum(1 for k in shared if min(a[k]["true_w"], a[k]["true_h"]) < MIN_RECOMMENDED_PX)
    print("-" * 78, file=sys.stderr)
    print(f"mean long-edge fill  {bavg:.3f} -> {aavg:.3f}   ({aavg - bavg:+.3f})", file=sys.stderr)
    print(f"below {MIN_RECOMMENDED_PX}px      {blow} -> {alow}", file=sys.stderr)
    print(f"improved {gained}, regressed {regressed}, unchanged {len(shared) - gained - regressed}", file=sys.stderr)


# ------------------------------------------------------------------------ CLI


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="measure images and flag problems")
    src = s.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="folder of local images (recursive)")
    src.add_argument("--tsv", help="TSV: index<TAB>listing_id<TAB>main_image_url")
    s.add_argument("--out", default="metrics.json")
    s.add_argument("--cache", default=".img-cache", help="download cache for --tsv")
    s.add_argument("--min-px", type=int, default=MIN_RECOMMENDED_PX)
    s.add_argument("--fill", type=float, default=LOW_LONG_EDGE_FILL,
                   help="flag below this LONG-EDGE fill (not area fill)")
    s.add_argument("--target-fill", type=float, default=0.93,
                   help="long-edge fill you intend to reach, for headroom/upscale maths")
    s.add_argument("--workers", type=int, default=8)
    s.set_defaults(func=cmd_scan)

    c = sub.add_parser("crop", help="emit tight content crops for external upscaling")
    c.add_argument("--dir", required=True)
    c.add_argument("--out", default="./crops")
    c.add_argument("--pad", type=int, default=4, help="safety pixels around the bbox")
    c.add_argument("--size", type=int, default=2000, help="eventual canvas size")
    c.add_argument("--fill", type=float, default=0.93, help="eventual frame fill")
    c.set_defaults(func=cmd_crop)

    p = sub.add_parser("compose", help="pad crops onto a square canvas at target fill")
    p.add_argument("--dir", required=True, help="folder of (upscaled) crops")
    p.add_argument("--out", default="./final")
    p.add_argument("--size", type=int, default=2000)
    p.add_argument("--fill", type=float, default=0.93)
    p.add_argument("--quality", type=int, default=92)
    p.add_argument("--allow-shrink", action="store_true",
                   help="permit downscaling art that already exceeds the target fill")
    p.set_defaults(func=cmd_compose)

    d = sub.add_parser("compare", help="diff two metrics.json files")
    d.add_argument("before")
    d.add_argument("after")
    d.set_defaults(func=cmd_compare)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

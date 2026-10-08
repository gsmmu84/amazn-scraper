#!/usr/bin/env python3
"""Enumerate a shop's active listings and their main image URLs via the Etsy API.

Writes a TSV that `image_metrics.py scan --tsv` consumes, plus a JSON sidecar
with titles, prices and every image rendition.

Credentials: pass --key, set ETSY_KEYSTRING, or put the keystring in a file and
use --key-file. Only the keystring is needed -- reading a shop's public active
listings requires no OAuth and no shared secret.

    export ETSY_KEYSTRING=xxxxxxxxxxxxxxxxxxxxxxxx
    python3 etsy_fetch.py --shop MagnetMeUp --out ../data/listings.tsv

1,660 listings is ~17 requests at the API's 100-per-page maximum.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.etsy.com/v3/application"
PAGE_LIMIT = 100
# Etsy allows 10 requests/second; stay well under it.
REQUEST_SPACING_S = 0.25


def get(path: str, key: str, params: dict | None = None, retries: int = 4) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"x-api-key": key, "Accept": "application/json"})

    delay = 2.0
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            # 401/403 are credential problems; retrying will not fix them.
            if exc.code in (401, 403):
                sys.exit(
                    f"\nEtsy rejected the key ({exc.code}).\n  {body}\n\n"
                    "Check the keystring is correct and the app is approved."
                )
            if exc.code == 404:
                raise
            if attempt == retries:
                sys.exit(f"\n{exc.code} after {retries} retries: {body}")
            print(f"  {exc.code}, retrying in {delay:.0f}s", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries:
                sys.exit(f"\nnetwork error after {retries} retries: {exc}")
            print(f"  network error, retrying in {delay:.0f}s", file=sys.stderr)
        time.sleep(delay)
        delay *= 2
    raise AssertionError("unreachable")


def resolve_shop_id(name: str, key: str) -> int:
    data = get("/shops", key, {"shop_name": name, "limit": 20})
    for shop in data.get("results", []):
        if shop.get("shop_name", "").lower() == name.lower():
            print(
                f"shop {shop['shop_name']} id={shop['shop_id']} "
                f"active_listings={shop.get('listing_active_count', '?')}",
                file=sys.stderr,
            )
            return int(shop["shop_id"])
    names = ", ".join(s.get("shop_name", "?") for s in data.get("results", [])) or "none"
    sys.exit(f"shop {name!r} not found. Close matches: {names}")


def main_image(listing: dict) -> dict | None:
    """The main image is the lowest-rank image on the listing."""
    images = listing.get("images") or []
    if not images:
        return None
    return sorted(images, key=lambda im: im.get("rank", 1))[0]


def fetch_listings(shop_id: int, key: str, max_listings: int | None) -> list[dict]:
    out: list[dict] = []
    offset = 0
    total = None

    while True:
        params = {
            "limit": PAGE_LIMIT,
            "offset": offset,
            "includes": "Images",
            "state": "active",
        }
        page = get(f"/shops/{shop_id}/listings/active", key, params)
        if total is None:
            total = page.get("count", 0)
            print(f"{total} active listings to fetch", file=sys.stderr)

        results = page.get("results", [])
        if not results:
            break
        out.extend(results)
        print(f"  {len(out)}/{total}", file=sys.stderr)

        if max_listings and len(out) >= max_listings:
            out = out[:max_listings]
            break
        offset += PAGE_LIMIT
        if offset >= total:
            break
        time.sleep(REQUEST_SPACING_S)

    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shop", default="MagnetMeUp")
    ap.add_argument("--shop-id", type=int, help="skip the name lookup")
    ap.add_argument("--out", default="listings.tsv")
    ap.add_argument("--json-out", help="sidecar with titles/prices/all renditions")
    ap.add_argument("--key", help="Etsy keystring (prefer ETSY_KEYSTRING or --key-file)")
    ap.add_argument("--key-file", help="file containing the keystring")
    ap.add_argument("--max", type=int, help="stop after N listings (for a smoke test)")
    args = ap.parse_args()

    key = args.key or os.environ.get("ETSY_KEYSTRING")
    if not key and args.key_file:
        key = Path(args.key_file).read_text().strip()
    if not key:
        sys.exit("no keystring: pass --key, --key-file, or set ETSY_KEYSTRING")
    key = key.strip()

    shop_id = args.shop_id or resolve_shop_id(args.shop, key)
    listings = fetch_listings(shop_id, key, args.max)

    rows, sidecar, missing = [], [], []
    for i, lst in enumerate(listings, 1):
        img = main_image(lst)
        if not img:
            missing.append(lst.get("listing_id"))
            continue
        url = img.get("url_fullxfull") or img.get("url_570xN")
        if not url:
            missing.append(lst.get("listing_id"))
            continue
        rows.append((i, lst["listing_id"], url))
        price = lst.get("price") or {}
        sidecar.append({
            "listing_id": lst["listing_id"],
            "title": lst.get("title"),
            "url": lst.get("url"),
            "state": lst.get("state"),
            "created": lst.get("creation_timestamp"),
            "views": lst.get("views"),
            "num_favorers": lst.get("num_favorers"),
            "price": (
                f"{int(price.get('amount', 0)) / int(price.get('divisor', 1) or 1):.2f} "
                f"{price.get('currency_code', '')}".strip()
                if price else None
            ),
            "taxonomy": lst.get("taxonomy_id"),
            "main_image": url,
            "image_count": len(lst.get("images") or []),
            "main_image_px": [img.get("full_width"), img.get("full_height")],
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        fh.write(f"# {args.shop} main images via Etsy API v3 — {len(rows)} listings\n")
        fh.write("# index\tlisting_id\tmain_image_url\n")
        for idx, lid, url in rows:
            fh.write(f"{idx}\t{lid}\t{url}\n")

    json_out = Path(args.json_out) if args.json_out else out.with_suffix(".json")
    json_out.write_text(json.dumps(sidecar, indent=1))

    print(f"\nwrote {len(rows)} listings -> {out}", file=sys.stderr)
    print(f"wrote metadata -> {json_out}", file=sys.stderr)
    if missing:
        print(f"{len(missing)} listings had no usable main image: {missing[:10]}", file=sys.stderr)

    # The API reports stored dimensions, so low-res listings are visible before download.
    small = [s for s in sidecar if s["main_image_px"][0] and min(s["main_image_px"]) < 2000]
    if small:
        print(f"\n{len(small)} of {len(sidecar)} main images are below 2000px:", file=sys.stderr)
        for s in sorted(small, key=lambda s: min(s["main_image_px"]))[:15]:
            w, h = s["main_image_px"]
            print(f"  {s['listing_id']}  {w}x{h}  {(s['title'] or '')[:58]}", file=sys.stderr)
        print("\nnext: image_metrics.py scan --tsv "
              f"{out} --out before.json", file=sys.stderr)


if __name__ == "__main__":
    main()

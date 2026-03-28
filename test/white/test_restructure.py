#!/usr/bin/env python3
"""
White-box tests for file restructure and gzip compression.
Tests:
  1. New files exist (index.html, index.js, style.css)
  2. Old files removed (preview.html, preview.js)
  3. Gzip data files exist and are valid gzip
  4. Gzip data files decompress to valid GeoJSON
  5. index.html references style.css and index.js
  6. index.js uses DecompressionStream and .geojson.gz paths
  7. download.py uses gzip module and outputs .geojson.gz
  8. docs/spec-preview.md reflects new structure
"""

import gzip
import json
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name} -- {detail}")
        failed += 1


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# --- Test 1: New files exist ---
print("[Test 1] New files exist")
for fname in ["index.html", "index.js", "style.css"]:
    path = os.path.join(BASE_DIR, fname)
    check(f"{fname} exists", os.path.isfile(path), f"{path} not found")

# --- Test 2: Old files removed ---
print("[Test 2] Old files removed")
for fname in ["preview.html", "preview.js"]:
    path = os.path.join(BASE_DIR, fname)
    check(f"{fname} removed", not os.path.exists(path), f"{path} still exists")

# --- Test 3: Gzip data files exist ---
print("[Test 3] Gzip data files exist")
for fname in ["data/rivers.geojson.gz", "data/coastline.geojson.gz"]:
    path = os.path.join(BASE_DIR, fname)
    check(f"{fname} exists", os.path.isfile(path), f"{path} not found")
    if os.path.isfile(path):
        # Check gzip magic number
        with open(path, "rb") as f:
            magic = f.read(2)
        check(f"{fname} has gzip magic", magic == b'\x1f\x8b', f"got {magic!r}")

# --- Test 4: Gzip files decompress to valid GeoJSON ---
print("[Test 4] Gzip files decompress to valid GeoJSON")
for fname in ["data/rivers.geojson.gz", "data/coastline.geojson.gz"]:
    path = os.path.join(BASE_DIR, fname)
    if not os.path.isfile(path):
        check(f"{fname} decompress", False, "file missing")
        continue
    try:
        with gzip.open(path, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
        check(f"{fname} is valid GeoJSON", data.get("type") == "FeatureCollection",
              f"type={data.get('type')}")
        check(f"{fname} has features", len(data.get("features", [])) > 0,
              "no features")
    except Exception as e:
        check(f"{fname} decompress", False, str(e))

# --- Test 5: index.html references ---
print("[Test 5] index.html references")
html = read_file(os.path.join(BASE_DIR, "index.html"))
check("links style.css", 'href="style.css"' in html, "style.css link not found")
check("links index.js", 'src="index.js"' in html, "index.js script not found")
check("no inline <style>", "<style>" not in html, "inline <style> found")
check("no preview.js ref", "preview.js" not in html, "still references preview.js")

# --- Test 6: index.js uses DecompressionStream ---
print("[Test 6] index.js uses DecompressionStream")
js = read_file(os.path.join(BASE_DIR, "index.js"))
check("uses DecompressionStream", "DecompressionStream" in js,
      "DecompressionStream not found")
check('uses "gzip"', '"gzip"' in js, '"gzip" string not found')
check("fetches rivers.geojson.gz", "rivers.geojson.gz" in js,
      "rivers.geojson.gz not found")
check("fetches coastline.geojson.gz", "coastline.geojson.gz" in js,
      "coastline.geojson.gz not found")
check("no plain .geojson fetch", 'fetch("data/rivers.geojson")' not in js,
      "still fetches uncompressed rivers")

# --- Test 7: download.py outputs gzip ---
print("[Test 7] download.py outputs gzip")
py = read_file(os.path.join(BASE_DIR, "download.py"))
check("imports gzip", "import gzip" in py, "gzip import not found")
check("writes rivers.geojson.gz", "rivers.geojson.gz" in py,
      "rivers.geojson.gz not in output")
check("writes coastline.geojson.gz", "coastline.geojson.gz" in py,
      "coastline.geojson.gz not in output")
check("uses gzip.open", "gzip.open" in py, "gzip.open not found")

# --- Test 8: spec-preview.md updated ---
print("[Test 8] docs/spec-preview.md updated")
spec = read_file(os.path.join(BASE_DIR, "docs", "spec-preview.md"))
check("mentions index.html", "index.html" in spec, "index.html not mentioned")
check("mentions index.js", "index.js" in spec, "index.js not mentioned")
check("mentions style.css", "style.css" in spec, "style.css not mentioned")
check("mentions .geojson.gz", ".geojson.gz" in spec, ".geojson.gz not mentioned")
check("mentions DecompressionStream", "DecompressionStream" in spec,
      "DecompressionStream not mentioned")
check("no preview.html ref", "preview.html" not in spec,
      "still references preview.html")
check("no preview.js ref", "preview.js" not in spec,
      "still references preview.js")

# --- Summary ---
print()
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
sys.exit(1 if failed > 0 else 0)

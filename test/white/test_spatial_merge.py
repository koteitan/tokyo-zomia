#!/usr/bin/env python3
"""
White-box tests for spatial node merging (Maebashi river bug fix).
Tests:
  1. download.py uses Union-Find for node merging
  2. Output contains rivers near Maebashi (lat>36.3, lon<139.3)
  3. Tone River (830303) has segments spanning the Maebashi area
  4. High-elevation segments near Akagi-yama are included
  5. Total segment count increased after fix
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


# --- Test 1: download.py uses Union-Find ---
print("[Test 1] download.py uses Union-Find for node merging")
py = read_file(os.path.join(BASE_DIR, "download.py"))
check("uf_find defined", "def uf_find" in py, "uf_find not found")
check("uf_union defined", "def uf_union" in py, "uf_union not found")
check("BRIDGE_THRESHOLD defined", "BRIDGE_THRESHOLD" in py, "threshold not found")
check("spatial_grid used", "spatial_grid" in py, "spatial grid not found")

# --- Test 2: Output contains Maebashi rivers ---
print("[Test 2] Maebashi rivers in output")
gz_path = os.path.join(BASE_DIR, "data", "rivers.geojson.gz")
with gzip.open(gz_path, "rb") as f:
    data = json.loads(f.read().decode("utf-8"))

maebashi = [f for f in data["features"]
            if any(c[1] > 36.3 and c[0] < 139.3 for c in f["geometry"]["coordinates"])]
check("Maebashi segments > 0", len(maebashi) > 0,
      f"got {len(maebashi)}")
check("Maebashi segments > 1000", len(maebashi) > 1000,
      f"got {len(maebashi)}, expected many more")

# --- Test 3: Tone River spans Maebashi ---
print("[Test 3] Tone River (830303) covers Maebashi area")
tone = [f for f in data["features"]
        if f["properties"]["suikei_code"] == "830303"]
check("Tone has > 5000 segments", len(tone) > 5000,
      f"got {len(tone)}")

tone_maeb = [f for f in tone
             if any(c[1] > 36.3 and c[0] < 139.3 for c in f["geometry"]["coordinates"])]
check("Tone has Maebashi segments", len(tone_maeb) > 0,
      f"got {len(tone_maeb)}")

tone_lats = [c[1] for f in tone for c in f["geometry"]["coordinates"]]
check("Tone reaches lat > 36.5", max(tone_lats) > 36.5,
      f"max lat = {max(tone_lats):.2f}")

# --- Test 4: High-elevation segments near Akagi ---
print("[Test 4] High-elevation Akagi-area segments")
akagi = [f for f in data["features"]
         if any(c[1] > 36.5 and c[0] < 139.25 and c[2] > 300
                for c in f["geometry"]["coordinates"])]
check("Akagi high-elev segments > 0", len(akagi) > 0,
      f"got {len(akagi)}")
check("Akagi high-elev segments > 500", len(akagi) > 500,
      f"got {len(akagi)}")

# --- Test 5: Total segment count ---
print("[Test 5] Total segment count increased")
total = len(data["features"])
check("total > 10000", total > 10000,
      f"got {total}, expected > 10000 after spatial merge fix")

# --- Summary ---
print()
total_tests = passed + failed
print(f"Results: {passed}/{total_tests} passed, {failed} failed")
sys.exit(1 if failed > 0 else 0)

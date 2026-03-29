#!/usr/bin/env python3
"""
White-box tests for mouse hover tooltip and highlight feature.
Tests:
  1. index.js contains adjacency graph construction (nodeToSegs, nodeDegree)
  2. index.js contains findNearestSegment function with screen-space projection
  3. index.js contains floodFillSegments function with degree!=2 stop condition
  4. index.js uses #tooltip element for river name display
  5. index.js highlight uses white color (1,1,1)
  6. index.js has highlightDirty flag for efficient redraw
  7. GeoJSON data has start_node, end_node, river_name properties
  8. index.html title is "東京ゾミア"
  9. docs/spec-preview.md documents hover/highlight feature
"""

import gzip
import json
import os
import re
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


js = read_file(os.path.join(BASE_DIR, "index.js"))
html = read_file(os.path.join(BASE_DIR, "index.html"))
spec = read_file(os.path.join(BASE_DIR, "docs", "spec-preview.md"))

# --- Test 1: Adjacency graph construction ---
print("[Test 1] Adjacency graph construction")
check("nodeToSegs defined", "nodeToSegs" in js, "nodeToSegs not found")
check("nodeDegree defined", "nodeDegree" in js, "nodeDegree not found")
check("reads start_node", "start_node" in js, "start_node not referenced")
check("reads end_node", "end_node" in js, "end_node not referenced")

# --- Test 2: findNearestSegment ---
print("[Test 2] findNearestSegment function")
check("findNearestSegment exists", "function findNearestSegment" in js,
      "function not found")
check("uses projectToScreen", "projectToScreen" in js,
      "projectToScreen not found")
check("uses distPointToSegment2D", "distPointToSegment2D" in js,
      "distPointToSegment2D not found")
check("has pixel threshold", re.search(r'bestDist\s*<\s*\d+', js) is not None,
      "no pixel threshold found")

# --- Test 3: floodFillSegments ---
print("[Test 3] floodFillSegments function")
check("floodFillSegments exists", "function floodFillSegments" in js,
      "function not found")
check("checks nodeDegree !== 2",
      re.search(r'nodeDegree\[.*\]\s*!==?\s*2', js) is not None,
      "degree!=2 check not found")
check("uses BFS/DFS queue", "queue" in js, "queue not found in flood fill")

# --- Test 4: Tooltip ---
print("[Test 4] Tooltip display")
check("uses #tooltip element", 'getElementById("tooltip")' in js,
      "tooltip element not accessed")
check("shows river_name", "river_name" in js, "river_name not used")
check("tooltip display block", '"block"' in js, "tooltip not shown")
check("tooltip display none", '"none"' in js or "display = 'none'" in js,
      "tooltip not hidden")
check("fallback name", "(名称不明)" in js, "fallback text not found")

# --- Test 5: Highlight color ---
print("[Test 5] Highlight color")
check("highlightSet used", "highlightSet" in js, "highlightSet not found")
# Check white highlight: colors.push(1, 1, 1, 1, 1, 1)
check("white highlight color",
      re.search(r'colors\.push\(1,\s*1,\s*1,\s*1,\s*1,\s*1\)', js) is not None,
      "white color push not found")

# --- Test 6: Efficient redraw ---
print("[Test 6] Efficient redraw with dirty flag")
check("highlightDirty flag", "highlightDirty" in js, "dirty flag not found")
check("dirty flag triggers rebuild",
      "if (highlightDirty)" in js, "dirty flag check in draw not found")

# --- Test 7: GeoJSON data has required properties ---
print("[Test 7] GeoJSON data properties")
gz_path = os.path.join(BASE_DIR, "data", "rivers.geojson.gz")
if os.path.isfile(gz_path):
    with gzip.open(gz_path, "rb") as f:
        data = json.loads(f.read().decode("utf-8"))
    feat = data["features"][0]
    props = feat["properties"]
    check("has start_node", "start_node" in props,
          f"keys: {list(props.keys())}")
    check("has end_node", "end_node" in props,
          f"keys: {list(props.keys())}")
    check("has river_name", "river_name" in props,
          f"keys: {list(props.keys())}")
    check("start_node is string", isinstance(props["start_node"], str),
          f"type: {type(props['start_node'])}")
    check("end_node is string", isinstance(props["end_node"], str),
          f"type: {type(props['end_node'])}")
else:
    check("rivers.geojson.gz exists", False, "file missing")

# --- Test 8: Title changed ---
print("[Test 8] Title is 東京ゾミア")
check("HTML title", "<title>東京ゾミア</title>" in html,
      "title not updated")
check("no old title in HTML", "河川水系 3D Preview" not in html,
      "old title still present")

# --- Test 9: Spec updated ---
print("[Test 9] docs/spec-preview.md documents hover feature")
check("mentions hover", "ホバー" in spec or "hover" in spec.lower(),
      "hover not mentioned")
check("mentions highlight", "ハイライト" in spec or "highlight" in spec.lower(),
      "highlight not mentioned")
check("mentions floodFill or adjacency",
      "フラッドフィル" in spec or "flood" in spec.lower() or "隣接" in spec,
      "flood fill / adjacency not mentioned")
check("mentions tooltip", "ツールチップ" in spec or "tooltip" in spec.lower(),
      "tooltip not mentioned")
check("mentions degree", "degree" in spec or "次数" in spec,
      "degree not mentioned")

# --- Summary ---
print()
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
sys.exit(1 if failed > 0 else 0)
